#!.venv/bin/python3
import os
import uuid
import threading
import subprocess
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename

from process_audio import convert_to_mp3, transcribe_audio

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory dictionary to track task status
# Format: { task_id: {"status": "Processing...", "result_file": None, "error": None} }
tasks = {}

def process_file_in_background(task_id, file_path, notes, not_swedish):
    try:
        tasks[task_id]['status'] = 'Converting to MP3...'
        
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}.mp3")
        md_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}.md")
        
        if not file_path.lower().endswith('.mp3'):
            success = convert_to_mp3(file_path, mp3_path)
            if not success:
                raise Exception("Failed to convert audio to MP3.")
            audio_to_transcribe = mp3_path
        else:
            audio_to_transcribe = file_path

        tasks[task_id]['status'] = 'Transcribing audio (this may take a while)...'
        # Call the transcription function
        transcription_text = transcribe_audio(audio_to_transcribe, None, not_swedish=not_swedish)

        tasks[task_id]['status'] = 'Generating summary with Antigravity AI...'
        
        # Build prompt for agy
        prompt = (
            "Summarize the following notes and transcription. "
            "Write the summary as minutes from a meeting, making it structured and easy to read. "
            "Start the response with a fitting H1 title (# Title) based on the content instead of using a generic summary headline. "
            "Use clear headings, bullet points, and highlight key decisions or action items. "
            "Write the output in Swedish:\n\n"
            f"Notes:\n{notes}\n\n"
            f"Transcription:\n{transcription_text}"
        )
        
        # Call the agy CLI tool
        result = subprocess.run(
            ['agy', '--print', prompt],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Antigravity CLI failed: {result.stderr}")
            
        summary_text = result.stdout
        
        # Combine transcript and summary in the md file
        final_content = (
            f"{summary_text}\n\n"
            "---\n"
            "# Original Notes\n\n"
            f"{notes}\n\n"
            "---\n"
            "# Full Transcription\n\n"
            f"{transcription_text}\n"
        )
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        # Generate PDF using md-to-pdf via npx
        pdf_path = md_path.replace('.md', '.pdf')
        subprocess.run(['npx', '-y', 'md-to-pdf', md_path], check=True)
            
        tasks[task_id]['status'] = 'Completed'
        tasks[task_id]['result_file_md'] = md_path
        tasks[task_id]['result_file_pdf'] = pdf_path
        
    except Exception as e:
        tasks[task_id]['status'] = 'Error'
        tasks[task_id]['error'] = str(e)
        print(f"Task {task_id} failed: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
        
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    notes = request.form.get('notes', '')
    not_swedish = request.form.get('not_swedish') == 'true'
    
    task_id = str(uuid.uuid4())
    filename = f"{task_id}_{secure_filename(file.filename)}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    tasks[task_id] = {
        'status': 'Uploaded, waiting to start...',
        'result_file_md': None,
        'result_file_pdf': None,
        'error': None
    }
    
    # Start background thread
    thread = threading.Thread(
        target=process_file_in_background,
        args=(task_id, file_path, notes, not_swedish)
    )
    thread.start()
    
    return jsonify({'task_id': task_id}), 202

@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(tasks[task_id])

@app.route('/download/md/<task_id>', methods=['GET'])
def download_md(task_id):
    if task_id not in tasks:
        return "Task not found", 404
        
    task = tasks[task_id]
    if task['status'] != 'Completed' or not task['result_file_md']:
        return "File not ready yet", 400
        
    return send_file(
        task['result_file_md'],
        as_attachment=True,
        download_name=f"summary_{task_id}.md"
    )

@app.route('/download/pdf/<task_id>', methods=['GET'])
def download_pdf(task_id):
    if task_id not in tasks:
        return "Task not found", 404
        
    task = tasks[task_id]
    if task['status'] != 'Completed' or not task['result_file_pdf']:
        return "File not ready yet", 400
        
    return send_file(
        task['result_file_pdf'],
        as_attachment=True,
        download_name=f"summary_{task_id}.pdf"
    )

if __name__ == '__main__':
    app.run(debug=True, port=5001)

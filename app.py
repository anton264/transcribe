#!.venv/bin/python3
import os
import re
import uuid
import threading
import asyncio
import subprocess
import datetime
import glob
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

from google.antigravity import Agent, LocalAgentConfig

from process_audio import convert_to_mp3, transcribe_audio

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory dictionary to track task status
# Format: { task_id: {"status": ..., "original_name": ..., "created_at": ..., ...} }
tasks = {}


def _make_output_basename(original_filename):
    """Generate a date-stamped, human-readable base name from the original filename."""
    date_str = datetime.date.today().isoformat()  # e.g. 2026-06-06
    # Strip extension, make filesystem-safe
    name = os.path.splitext(original_filename)[0]
    name = secure_filename(name)
    # Replace underscores/multiple dashes with single dash for readability
    name = re.sub(r'[_]+', '-', name)
    name = re.sub(r'-+', '-', name).strip('-')
    return f"{date_str}_{name}"


def _scan_output_files():
    """Scan the outputs/ directory and return a list of completed file records."""
    output_dir = app.config['OUTPUT_FOLDER']
    files = []
    seen = set()

    for filepath in sorted(glob.glob(os.path.join(output_dir, '*.md'))):
        basename = os.path.basename(filepath)
        stem = os.path.splitext(basename)[0]

        if stem in seen:
            continue
        seen.add(stem)

        pdf_path = os.path.join(output_dir, f"{stem}.pdf")
        has_pdf = os.path.exists(pdf_path)

        stat = os.stat(filepath)
        # Try to extract date from filename (YYYY-MM-DD_name)
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_(.+)$', stem)
        if date_match:
            date_str = date_match.group(1)
            display_name = date_match.group(2).replace('-', ' ').title()
        else:
            date_str = datetime.date.fromtimestamp(stat.st_mtime).isoformat()
            display_name = stem.replace('-', ' ').replace('_', ' ').title()

        # Check if PDF is currently being generated
        converting = False
        for tid, task in tasks.items():
            if task.get('output_basename') == stem and task.get('status') == 'Generating PDF...':
                converting = True
                break

        files.append({
            'filename': stem,
            'display_name': display_name,
            'date': date_str,
            'size_bytes': stat.st_size,
            'has_md': True,
            'has_pdf': has_pdf,
            'converting': converting,
        })

    # Sort newest first
    files.sort(key=lambda f: f['date'], reverse=True)
    return files


def process_file_in_background(task_id, file_path, notes, not_swedish, include_notes=True, include_transcription=True):
    try:
        # Check cancellation before each step
        if tasks[task_id].get('cancelled'):
            tasks[task_id]['status'] = 'Cancelled'
            return

        tasks[task_id]['status'] = 'Converting to MP3...'

        original_name = tasks[task_id]['original_name']
        output_basename = _make_output_basename(original_name)
        mp3_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}.mp3")
        md_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{output_basename}.md")
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{output_basename}.pdf")

        if not file_path.lower().endswith('.mp3'):
            success = convert_to_mp3(file_path, mp3_path)
            if not success:
                raise Exception("Failed to convert audio to MP3.")
            audio_to_transcribe = mp3_path
        else:
            audio_to_transcribe = file_path

        if tasks[task_id].get('cancelled'):
            tasks[task_id]['status'] = 'Cancelled'
            return

        tasks[task_id]['status'] = 'Transcribing audio (this may take a while)...'
        # Call the transcription function
        transcription_text = transcribe_audio(audio_to_transcribe, None, not_swedish=not_swedish)

        if tasks[task_id].get('cancelled'):
            tasks[task_id]['status'] = 'Cancelled'
            return

        tasks[task_id]['status'] = 'Generating summary with Antigravity AI...'

        # Build prompt for the Antigravity SDK
        prompt = (
            "Summarize the following notes and transcription. "
            "Write the summary as minutes from a meeting, making it structured and easy to read. "
            "Start the response with a fitting H1 title (# Title) based on the content instead of using a generic summary headline. "
            "Use clear headings, bullet points, and highlight key decisions or action items. "
            "Write the output in Swedish:\n\n"
            f"Notes:\n{notes}\n\n"
            f"Transcription:\n{transcription_text}"
        )

        # Call the Antigravity SDK
        async def _generate_summary():
            config = LocalAgentConfig(
                system_instructions=(
                    "You are a helpful assistant that summarizes meeting notes "
                    "and transcriptions into structured, readable minutes in Swedish."
                ),
            )
            async with Agent(config) as agent:
                response = await agent.chat(prompt)
                return await response.text()

        summary_text = asyncio.run(_generate_summary())

        if tasks[task_id].get('cancelled'):
            tasks[task_id]['status'] = 'Cancelled'
            return

        tasks[task_id]['status'] = 'Generating markdown...'

        # Combine transcript and summary in the md file
        final_content = f"{summary_text}\n\n"

        if include_notes and notes.strip():
            final_content += (
                "---\n"
                "# Original Notes\n\n"
                f"{notes}\n\n"
            )

        if include_transcription:
            final_content += (
                "---\n"
                "# Full Transcription\n\n"
                f"{transcription_text}\n"
            )

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        # Stop here — user reviews/edits MD before PDF generation
        tasks[task_id]['status'] = 'Review Ready'
        tasks[task_id]['result_file_md'] = md_path
        tasks[task_id]['output_basename'] = output_basename

    except Exception as e:
        tasks[task_id]['status'] = 'Error'
        tasks[task_id]['error'] = str(e)
        print(f"Task {task_id} failed: {e}")


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ─── Upload & Status (existing, updated) ──────────────────────────────────────

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400

    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    notes = request.form.get('notes', '')
    not_swedish = 'not_swedish' in request.form
    include_notes = 'include_notes' in request.form
    include_transcription = 'include_transcription' in request.form

    task_id = str(uuid.uuid4())
    original_filename = file.filename
    safe_filename = f"{task_id}_{secure_filename(file.filename)}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    file.save(file_path)

    tasks[task_id] = {
        'status': 'Uploaded, waiting to start...',
        'original_name': original_filename,
        'created_at': datetime.datetime.now().isoformat(),
        'result_file_md': None,
        'result_file_pdf': None,
        'output_basename': None,
        'error': None,
        'cancelled': False,
    }

    # Start background thread
    thread = threading.Thread(
        target=process_file_in_background,
        args=(task_id, file_path, notes, not_swedish, include_notes, include_transcription)
    )
    thread.start()

    return jsonify({'task_id': task_id}), 202


@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(tasks[task_id])


# ─── Queue Endpoints ──────────────────────────────────────────────────────────

@app.route('/queue', methods=['GET'])
def get_queue():
    """Return all active (non-completed, non-error, non-cancelled) tasks."""
    queue_items = []
    for tid, task in tasks.items():
        if task['status'] not in ('Completed', 'Error', 'Cancelled'):
            queue_items.append({
                'task_id': tid,
                'status': task['status'],
                'original_name': task.get('original_name', 'Unknown'),
                'created_at': task.get('created_at', ''),
            })
    # Sort oldest first (FIFO)
    queue_items.sort(key=lambda t: t['created_at'])
    return jsonify(queue_items)


@app.route('/queue/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """Mark a task as cancelled. Best-effort — can't interrupt a running model."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404

    task = tasks[task_id]
    if task['status'] in ('Completed', 'Error', 'Cancelled'):
        return jsonify({'error': 'Task already finished'}), 400

    task['cancelled'] = True
    task['status'] = 'Cancelling...'
    return jsonify({'success': True})


# ─── File Management Endpoints ────────────────────────────────────────────────

@app.route('/files', methods=['GET'])
def list_files():
    """Return all completed output files."""
    return jsonify(_scan_output_files())


@app.route('/files/<filename>/content', methods=['GET'])
def get_file_content(filename):
    """Return raw markdown content of a file."""
    output_dir = app.config['OUTPUT_FOLDER']
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    md_path = os.path.join(output_dir, f"{safe_name}.md")
    if not os.path.exists(md_path):
        return jsonify({'error': 'File not found'}), 404

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({'content': content, 'filename': safe_name})


@app.route('/files/<filename>/content', methods=['PUT'])
def save_file_content(filename):
    """Save edited markdown content back to file."""
    output_dir = app.config['OUTPUT_FOLDER']
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    md_path = os.path.join(output_dir, f"{safe_name}.md")
    if not os.path.exists(md_path):
        return jsonify({'error': 'File not found'}), 404

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'No content provided'}), 400

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(data['content'])

    return jsonify({'success': True})


def _generate_pdf_background(filename):
    """Generate PDF from an existing MD file in background."""
    output_dir = app.config['OUTPUT_FOLDER']
    safe_name = secure_filename(filename)
    md_path = os.path.join(output_dir, f"{safe_name}.md")
    pdf_path = os.path.join(output_dir, f"{safe_name}.pdf")

    try:
        # Read first line to extract title
        with open(md_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        title = first_line.lstrip('# ').strip() or safe_name

        subprocess.run([
            'pandoc',
            'template.md',
            md_path,
            '-o', pdf_path,
            '--template', 'eisvogel',
            '--pdf-engine', 'xelatex',
            '--metadata', f'title={title}',
            '--metadata', f'date={datetime.date.today().isoformat()}',
        ], check=True)

        # Update any task that references this file
        for tid, task in tasks.items():
            if task.get('output_basename') == safe_name:
                task['status'] = 'Completed'
                task['result_file_pdf'] = pdf_path

    except Exception as e:
        print(f"PDF generation failed for {safe_name}: {e}")
        for tid, task in tasks.items():
            if task.get('output_basename') == safe_name:
                task['status'] = 'PDF Error'
                task['error'] = str(e)


@app.route('/files/<filename>/convert', methods=['POST'])
def convert_file(filename):
    """Trigger PDF generation from an existing MD file."""
    output_dir = app.config['OUTPUT_FOLDER']
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    md_path = os.path.join(output_dir, f"{safe_name}.md")
    if not os.path.exists(md_path):
        return jsonify({'error': 'File not found'}), 404

    # Mark any related task as converting
    for tid, task in tasks.items():
        if task.get('output_basename') == safe_name:
            task['status'] = 'Generating PDF...'

    thread = threading.Thread(
        target=_generate_pdf_background,
        args=(filename,)
    )
    thread.start()

    return jsonify({'success': True})


@app.route('/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a .md and .pdf pair from outputs/."""
    output_dir = app.config['OUTPUT_FOLDER']
    # Sanitize — prevent path traversal
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({'error': 'Invalid filename'}), 400

    md_path = os.path.join(output_dir, f"{safe_name}.md")
    pdf_path = os.path.join(output_dir, f"{safe_name}.pdf")

    deleted = False
    for path in (md_path, pdf_path):
        if os.path.exists(path):
            os.remove(path)
            deleted = True

    if not deleted:
        return jsonify({'error': 'File not found'}), 404

    return jsonify({'success': True})


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Serve a file from the outputs/ directory."""
    output_dir = os.path.abspath(app.config['OUTPUT_FOLDER'])
    return send_from_directory(output_dir, filename, as_attachment=True)


# ─── Legacy download endpoints (kept for backward compat) ─────────────────────

@app.route('/download/md/<task_id>', methods=['GET'])
def download_md(task_id):
    if task_id not in tasks:
        return "Task not found", 404

    task = tasks[task_id]
    if task['status'] != 'Completed' or not task['result_file_md']:
        return "File not ready yet", 400

    return send_from_directory(
        os.path.abspath(app.config['OUTPUT_FOLDER']),
        os.path.basename(task['result_file_md']),
        as_attachment=True,
    )


@app.route('/download/pdf/<task_id>', methods=['GET'])
def download_pdf(task_id):
    if task_id not in tasks:
        return "Task not found", 404

    task = tasks[task_id]
    if task['status'] != 'Completed' or not task['result_file_pdf']:
        return "File not ready yet", 400

    return send_from_directory(
        os.path.abspath(app.config['OUTPUT_FOLDER']),
        os.path.basename(task['result_file_pdf']),
        as_attachment=True,
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

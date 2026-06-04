#!.venv/bin/python3
import argparse
import os
import torch
import datetime
from pydub import AudioSegment
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

def convert_to_mp3(input_file, output_file):
    try:
        print(f"Converting {input_file} to mp3...")
        # Load the audio file
        audio = AudioSegment.from_file(input_file)

        # Export as mp3
        audio.export(output_file, format="mp3", bitrate="192k")
        
        print(f"Success! Converted {input_file} to {output_file}")
        return True
    except Exception as e:
        print(f"Error converting file: {e}")
        return False

def transcribe_audio(file_path, output_md_path, not_swedish=False):
    print("Loading model...")
    device = "cpu"
    if torch.cuda.is_available():
        print("CUDA is available")
        device = "cuda:0"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print("MPS is available")
        device = "mps"
    elif device == "cpu":
        print("CPU is available. It will be slow.")
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    if not_swedish:
        model_id = "openai/whisper-large-v3"
    else:
        model_id = "KBLab/kb-whisper-large"

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, use_safetensors=True, cache_dir="cache"
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )

    print(f"Transcribing {file_path}...")
    timebefore = datetime.datetime.now()
    
    generate_kwargs = {"task": "transcribe"}
    if not not_swedish:
        generate_kwargs["language"] = "sv"

    res = pipe(file_path, 
               chunk_length_s=30,
               generate_kwargs=generate_kwargs)
    print("Time after pipeline: ", datetime.datetime.now())
    print("Time to transcribe: ", datetime.datetime.now() - timebefore)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        if isinstance(res, dict) and "text" in res:
            f.write(res["text"])
        else:
            f.write(str(res))
    print(f"Transcription saved to {output_md_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert an audio file to mp3 and transcribe it.")
    parser.add_argument("input_file", help="Path to the input audio file")
    parser.add_argument("--non-swedish", action="store_true", help="Indicates the sound file is not Swedish. Uses openai/whisper-large-v3 model.")
    args = parser.parse_args()

    input_file = args.input_file
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found.")
        return

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    mp3_file = f"{base_name}.mp3"
    md_file = f"{base_name}.md"

    # Convert to mp3 if it's not already an mp3
    if not input_file.lower().endswith(".mp3"):
        success = convert_to_mp3(input_file, mp3_file)
        if not success:
            return
        audio_to_transcribe = mp3_file
    else:
        audio_to_transcribe = input_file

    transcribe_audio(audio_to_transcribe, md_file, not_swedish=args.non_swedish)

if __name__ == "__main__":
    main()

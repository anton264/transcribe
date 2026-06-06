# Transcribe

A Python script to convert audio files to MP3 format and transcribe them using the Hugging Face Whisper pipeline. Specifically, it uses the `KBLab/kb-whisper-large` model, which is optimized for Swedish transcription.

## Requirements

The script requires several Python packages to run. You can install them using the provided `requirements.txt` file:

```bash
pip install -r requirements.txt
```

Additionally, `pydub` requires `ffmpeg` to be installed on your system to handle audio conversion.

- **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
- **macOS (using Homebrew):** `brew install ffmpeg`

## Usage

Run the script from the command line, passing the path to the audio file you want to transcribe as an argument:

```bash
python process_audio.py <path_to_audio_file>
```

### What the script does:

1. **Audio Conversion**: If the input file is not already an MP3, it will be converted to a 192k bitrate MP3 file (saved as `<original_filename>.mp3`).
2. **Transcription**: The audio is processed using the `KBLab/kb-whisper-large` model. The transcription task is configured for the Swedish language (`"language": "sv"`).
3. **Output**: The transcribed text is saved to a markdown file named `<original_filename>.md`.

## Hardware Acceleration

The script will automatically detect and use hardware acceleration if available (CUDA for NVIDIA GPUs or MPS for Apple Silicon), falling back to the CPU otherwise. Using a GPU significantly decreases transcription time.

## Running with podman

### Build the image

```bash
podman build -t transcribe .
```

### Run with GPU support (NVIDIA)

```bash
podman run --gpus all -p 8001:5001 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/cache:/app/cache \
  transcribe
```

### Run without GPU (CPU-only)

> **Note:** CPU transcription is disabled by default in `process_audio.py`. Remove the GPU check or adjust the code if you want CPU fallback.

```bash
podman run -p 5001:5001 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/cache:/app/cache \
  transcribe
```

The app will be available at `http://localhost:5001`.

### Volume mounts

| Mount | Purpose |
|-------|---------|
| `outputs/` | Generated markdown and PDF files |
| `uploads/` | Uploaded audio files |
| `cache/` | Hugging Face model cache (avoids re-downloading) |

## Pandoc conversion

```sh
podman run --rm --volume "$(pwd):/data:Z" --userns=keep-id podman.io/pandoc/extra template.md -o example.pdf --template eisvogel --syntax-highlighting idiomatic
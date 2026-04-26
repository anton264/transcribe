from pydub import AudioSegment
import os

def convert_qta_to_mp3(input_file, output_file):
    try:
        # Load the .qta file
        # If pydub struggles, we explicitly tell it to use ffmpeg
        audio = AudioSegment.from_file(input_file)

        # Export as mp3
        # bitrate="192k" is a good balance of quality and size
        audio.export(output_file, format="mp3", bitrate="192k")
        
        print(f"Success! Converted {input_file} to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")

# Usage
convert_qta_to_mp3("recording.m4a", "converted_audi2.mp3")
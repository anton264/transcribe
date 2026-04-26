# Source - https://stackoverflow.com/a/38110429
# Posted by Pritam Banerjee, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-23, License - CC BY-SA 3.0

from pydub import AudioSegment

wav_audio = AudioSegment.from_file("recording.m4a", format="m4a")

wav_audio.export("audio1.mp3", format="mp3")
#raw_audio.export("audio2.mp3", format="mp3")

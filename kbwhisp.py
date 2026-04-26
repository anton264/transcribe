import torch
import datetime
from datasets import load_dataset
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

device = "cpu"
if torch.cuda.is_available():
    device = "cuda:0"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
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

timebefore = datetime.datetime.now()
generate_kwargs = {"task": "transcribe", "language": "sv"}
# Add return_timestamps=True for output with timestamps
res = pipe("recording.m4a", 
           chunk_length_s=30,
           generate_kwargs={"task": "transcribe", "language": "sv"})
print("Time after pipeline: ", datetime.datetime.now())
# display the time it took to transcribe
print("Time to transcribe: ", datetime.datetime.now() - timebefore)
# save res to md file
with open("transcript.md", "w", encoding="utf-8") as f:
    if isinstance(res, dict) and "text" in res:
        f.write(res["text"])
    else:
        f.write(str(res))
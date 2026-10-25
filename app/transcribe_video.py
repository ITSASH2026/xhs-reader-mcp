"""Offline speech recognition subprocess; result stays in parent process RAM."""
import json
import sys
import wave
import numpy as np
from faster_whisper import WhisperModel

model = WhisperModel('/app/models/whisper-base', device='cpu', compute_type='int8', cpu_threads=1, num_workers=1, local_files_only=True)
with wave.open(sys.argv[1], 'rb') as source:
    assert source.getnchannels()==1 and source.getsampwidth()==2 and source.getframerate()==16000
    audio=np.frombuffer(source.readframes(source.getnframes()), dtype=np.int16).astype(np.float32)/32768.0
segments, info = model.transcribe(audio, beam_size=3, condition_on_previous_text=False, vad_filter=True)
result = []
for segment in segments:
    result.append({'start':round(segment.start,2),'end':round(segment.end,2),'text':segment.text})
    if sum(len(s['text']) for s in result) > 24000:
        raise RuntimeError('Transcript exceeds response limit')
print(json.dumps({'language':info.language,'language_probability':info.language_probability,'segments':result,'model':'faster-whisper-base-int8','note':'自动语音识别，可能错字或误识别；无声视频请以画面为准。'},ensure_ascii=False))

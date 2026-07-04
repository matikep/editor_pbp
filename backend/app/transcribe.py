import os
from functools import lru_cache

from faster_whisper import WhisperModel

from .normalize import normalize
from .words import load_forbidden_words

MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "medium")


@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe_audio(audio_path: str, on_progress=None) -> dict:
    model = get_model()
    forbidden = load_forbidden_words()

    segments_iter, info = model.transcribe(
        audio_path, word_timestamps=True, language="es"
    )
    duration = info.duration or 0.0

    segments = []
    words = []
    for seg_idx, segment in enumerate(segments_iter):
        segments.append(
            {
                "id": seg_idx,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
        )
        for word in segment.words or []:
            clean = word.word.strip()
            words.append(
                {
                    "index": len(words),
                    "segment_id": seg_idx,
                    "word": clean,
                    "start": word.start,
                    "end": word.end,
                    "flagged": normalize(clean) in forbidden,
                }
            )
        if on_progress and duration:
            on_progress(min(segment.end / duration, 1.0))

    return {"segments": segments, "words": words}

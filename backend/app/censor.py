from pydub import AudioSegment
from pydub.generators import Sine


def censor_audio(input_path: str, ranges: list[dict], mode: str = "beep") -> AudioSegment:
    """Replace each [start, end] range (seconds) in the audio with a beep
    tone or silence, preserving the original duration/offsets."""
    audio = AudioSegment.from_file(input_path)

    for r in sorted(ranges, key=lambda r: r["start"]):
        start_ms = int(r["start"] * 1000)
        end_ms = int(r["end"] * 1000)
        duration = max(end_ms - start_ms, 0)

        if mode == "silence":
            replacement = AudioSegment.silent(duration=duration)
        else:
            replacement = Sine(1000).to_audio_segment(duration=duration).apply_gain(-3)

        audio = audio[:start_ms] + replacement + audio[end_ms:]

    return audio

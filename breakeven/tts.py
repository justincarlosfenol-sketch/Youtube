"""Narration: human takes when present, otherwise Kokoro-82M draft TTS.

Human-first by design: if `videos/<slug>/voice/<line_id>.wav` exists it is
used verbatim (record with `python -m breakeven teleprompter <slug>`).
Otherwise a draft line is synthesised with Kokoro (Apache-2.0 weights).
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24_000
MODELS = Path(os.environ.get("BREAKEVEN_MODELS", Path.home() / "models"))
if not (MODELS / "kokoro-v1.0.onnx").exists() and Path("/home/user/models/kokoro-v1.0.onnx").exists():
    MODELS = Path("/home/user/models")
VOICE = os.environ.get("BREAKEVEN_VOICE", "af_heart")
SPEED = float(os.environ.get("BREAKEVEN_SPEED", "1.0"))

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_words(n: int) -> str:
    if n < 0:
        return "minus " + num_words(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    if n < 1000:
        return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + num_words(n % 100))
    for div, word in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        if n >= div:
            rest = n % div
            return num_words(n // div) + " " + word + ("" if rest == 0 else (", " if rest >= 100 else " ") + num_words(rest))
    return str(n)


def _decimal_words(s: str) -> str:
    whole, _, frac = s.partition(".")
    w = num_words(int(whole.replace(",", "") or 0))
    if frac:
        w += " point " + " ".join(_ONES[int(d)] for d in frac)
    return w


def _year_words(cc: str, yy: str) -> str:
    n = int(yy)
    if cc == "20" and n < 10:
        return "two thousand" + ("" if n == 0 else " " + _ONES[n])
    head = "nineteen" if cc == "19" else "twenty"
    return head + " " + ("hundred" if n == 0 else ("oh " + _ONES[n]) if n < 10 else num_words(n))


def normalize(text: str) -> str:
    """Make numbers, currency and finance jargon speakable."""
    t = text.replace("*", "")
    t = re.sub(r"401\(k\)", "four-oh-one-k", t)
    t = re.sub(r"\$(\d+(?:\.\d+)?)\s(thousand|million|billion)\b",
               lambda m: _decimal_words(m.group(1)) + " " + m.group(2) + " dollars", t)
    t = re.sub(r"\$(\d[\d,]*)(\.\d+)?\s?([KkMm])\b",
               lambda m: _decimal_words(m.group(1) + (m.group(2) or "")) + (" thousand" if m.group(3) in "Kk" else " million") + " dollars", t)
    t = re.sub(r"\$(\d[\d,]*)(\.\d\d)?", lambda m: num_words(int(m.group(1).replace(",", ""))) + " dollars"
               + (f" and {num_words(int(m.group(2)[1:]))} cents" if m.group(2) else ""), t)
    t = re.sub(r"(\d+(?:\.\d+)?)%", lambda m: _decimal_words(m.group(1)) + " percent", t)
    t = re.sub(r"\b(19|20)(\d\d)\b", lambda m: _year_words(m.group(1), m.group(2)), t)
    t = re.sub(r"\d[\d,]*\.\d+", lambda m: _decimal_words(m.group(0)), t)
    t = re.sub(r"\d[\d,]*", lambda m: num_words(int(m.group(0).replace(",", ""))), t)
    t = t.replace("—", ", ").replace("–", ", ").replace(" vs ", " versus ").replace(" vs. ", " versus ")
    return re.sub(r"\s+", " ", t).strip()


_kokoro = None


def _engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        model, voices = MODELS / "kokoro-v1.0.onnx", MODELS / "voices-v1.0.bin"
        if not model.exists():
            raise FileNotFoundError(f"Kokoro model not found in {MODELS}. Run: python -m breakeven setup")
        _kokoro = Kokoro(str(model), str(voices))
    return _kokoro


def synth(text: str, cache_dir: Path, voice: str = VOICE, speed: float = SPEED) -> Path:
    spoken = normalize(text)
    key = hashlib.sha1(f"{voice}|{speed}|{spoken}".encode()).hexdigest()[:16]
    out = cache_dir / f"tts_{key}.wav"
    if out.exists():
        return out
    cache_dir.mkdir(parents=True, exist_ok=True)
    samples, sr = _engine().create(spoken, voice=voice, speed=speed, lang="en-us")
    samples = np.asarray(samples, dtype=np.float32)
    samples = _trim(samples, sr)
    if sr != SR:
        raise RuntimeError(f"unexpected sample rate {sr}")
    sf.write(out, samples, SR)
    return out


def _trim(x: np.ndarray, sr: int, thresh: float = 0.004, pad: float = 0.04) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(idx[0] - int(pad * sr), 0); b = min(idx[-1] + int(pad * sr), len(x))
    return x[a:b]


def load_line_audio(video_dir: Path, line_id: str, text: str) -> tuple[np.ndarray, str]:
    """Return (mono float32 @24k, origin) where origin is 'human' or 'tts'."""
    human = video_dir / "voice" / f"{line_id}.wav"
    if human.exists():
        x, sr = sf.read(human, dtype="float32", always_2d=True)
        x = x.mean(axis=1)
        if sr != SR:
            n = int(len(x) * SR / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        return _trim(x, SR), "human"
    p = synth(text, video_dir / "build" / "tts")
    x, _ = sf.read(p, dtype="float32")
    return x, "tts"

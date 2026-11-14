"""Titl iz govora (Ahmed 14.11.2026, bez Qt-a): kad video nema nijedan titl, program ga napravi sam.

Prepoznavanje govora radi na računaru korisnika (faster-whisper + CTranslate2, model Whisper large-v3-turbo,
licenca MIT); ništa se ne šalje na internet. Model (1,6 GB) NIJE u instalaciji: preuzima se jednom, tek kad
korisnik uključi postavku, provjeren po SHA-256, u folder podataka korisnika. Prekinuto preuzimanje nastavlja
od mjesta gdje je stalo.

Titl pravi računar, pa može imati grešaka (imena, strane riječi): fajl dobija oznaku „iz-govora" u imenu, a
prije upisa u sliku korisnik ga može pregledati i ispraviti (speech_dialogs.py).

VIDEODL_SPEECH_URL (testovi) zamjenjuje adresu modela drugim izvorom istog oblika (…/<ime fajla>).
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import types
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .runtime import find_tool, user_data_base

# Model: Whisper large-v3-turbo u CTranslate2 obliku (MIT), tačna verzija spremišta i SHA-256 svakog fajla.
MODEL_NAME = "whisper-large-v3-turbo"
MODEL_REPO = "dropbox-dash/faster-whisper-large-v3-turbo"
MODEL_REVISION = "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}"
MODEL_FILES = (  # ime, bajtova, SHA-256 (model.bin zadnji: najveći, a ostali su gotovi za tren)
    ("config.json", 2263, "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e"),
    ("preprocessor_config.json", 340, "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711"),
    ("tokenizer.json", 2710337, "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd"),
    ("vocabulary.json", 1068114, "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1"),
    ("model.bin", 1617884929, "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da"),
)
MODEL_BYTES = sum(size for _name, size, _digest in MODEL_FILES)
READY_MARK = "provjereno.txt"  # upisuje se tek kad su svi fajlovi provjereni po SHA-256
SPACE_MARGIN = 200 * 1024 * 1024  # toliko slobodnog mjesta mora ostati na disku poslije preuzimanja modela

SUFFIX = "iz-govora"  # „Naslov [id].bs.iz-govora.srt": vidi se da titl nije sa sajta
SAMPLE_RATE = 16000
MAX_SECONDS = 4 * 60 * 60  # duže od 4 sata: zvuk ne bi stao u memoriju (≈ 0,9 GB), titl se ne pravi
SOUTH_SLAVIC = ("bs", "hr", "sr")  # Whisper srpski piše ćirilicom; „bs" daje latinicu s našim slovima
# Kratak primjer na jeziku videa: model lakše pogodi pismo, slova i interpunkciju (ne utiče na sadržaj).
PROMPTS = {
    "bs": "Dobar dan. Ovo je razgovor na bosanskom jeziku, s rečenicama, zarezima i tačkama: č, ć, đ, š, ž.",
    "de": "Guten Tag. Dies ist ein Gespräch auf Deutsch, mit Sätzen, Kommas und Punkten.",
    "es": "Buenos días. Esta es una conversación en español, con frases, comas y puntos.",
    "fr": "Bonjour. Ceci est une conversation en français, avec des phrases, des virgules et des points.",
}


class SpeechError(Exception):
    """Titl iz govora nije napravljen (ili model nije preuzet); poruka je kratka, bez putanja korisnika.
    `key` je ključ prevoda kad postoji (prozor za preuzimanje modela ga pokaže na jeziku programa)."""

    def __init__(self, message: str, key: str | None = None):
        super().__init__(message)
        self.key = key


class SpeechCancelled(SpeechError):
    """Korisnik je prekinuo."""


@dataclass(frozen=True)
class Line:
    start: float  # sekunde
    end: float
    text: str


# ---------- model ----------

def model_dir() -> Path:
    override = os.environ.get("VIDEODL_DATA_DIR")
    base = Path(override) if override else user_data_base() / "VideoDownload"
    return base / "modeli" / MODEL_NAME


def engine_available() -> bool:
    """Biblioteke za prepoznavanje su u paketu (nema ih npr. u izvornom kodu bez `pip install faster-whisper`)."""
    import importlib.util

    return all(importlib.util.find_spec(name) is not None
               for name in ("faster_whisper", "ctranslate2", "onnxruntime", "tokenizers", "numpy"))


def model_ready(folder: Path | None = None) -> bool:
    folder = folder or model_dir()
    if not (folder / READY_MARK).is_file():
        return False
    return all((folder / name).is_file() and (folder / name).stat().st_size == size
               for name, size, _digest in MODEL_FILES)


def remaining_bytes(folder: Path | None = None) -> int:
    """Koliko još treba preuzeti (prekinuto preuzimanje nastavlja od .part fajla)."""
    folder = folder or model_dir()
    left = 0
    for name, size, _digest in MODEL_FILES:
        if (folder / name).is_file() and (folder / name).stat().st_size == size:
            continue
        part = folder / f"{name}.part"
        left += size - (min(part.stat().st_size, size) if part.is_file() else 0)
    return left


def delete_model(folder: Path | None = None) -> None:
    shutil.rmtree(folder or model_dir(), ignore_errors=True)


def download_model(on_progress: Callable[[int, int, float | None], None] | None = None,
                   cancel: threading.Event | None = None, folder: Path | None = None,
                   opener=urllib.request.urlopen, timeout: float = 60) -> None:
    """Preuzima model u `folder`; `on_progress(preuzeto, ukupno, bajtova_u_sekundi)`. Greška ili prekid
    ostavljaju .part fajl, pa sljedeći pokušaj nastavlja. SpeechCancelled kad korisnik prekine."""
    folder = folder or model_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / READY_MARK).unlink(missing_ok=True)
    left = remaining_bytes(folder)
    try:
        free = shutil.disk_usage(folder).free
    except OSError:
        free = None
    if free is not None and free < left + SPACE_MARGIN:
        raise SpeechError("Nema dovoljno mjesta na disku za model.", key="speech.error.space")
    base = os.environ.get("VIDEODL_SPEECH_URL") or MODEL_URL
    meter = _Meter(MODEL_BYTES - remaining_bytes(folder), on_progress)
    meter.report()
    for name, size, digest in MODEL_FILES:
        target = folder / name
        if target.is_file() and target.stat().st_size == size:
            continue
        _download_file(f"{base.rstrip('/')}/{name}", folder / f"{name}.part", size, meter, cancel, opener, timeout)
        part = folder / f"{name}.part"
        if _sha256(part) != digest:
            part.unlink(missing_ok=True)  # oštećen ili podmetnut fajl: sljedeći pokušaj kreće ispočetka
            raise SpeechError(f"Provjera fajla {name} nije uspjela (SHA-256).", key="speech.error.checksum")
        os.replace(part, target)
    meter.report()
    (folder / READY_MARK).write_text(f"{MODEL_REPO}@{MODEL_REVISION}\n", encoding="utf-8")


class _Meter:
    """Ukupan napredak svih fajlova modela i brzina (prosjek zadnjih ~5 s)."""

    def __init__(self, done: int, callback):
        self.done = done
        self.callback = callback
        self.samples: list[tuple[float, int]] = [(time.monotonic(), done)]
        self.last_report = 0.0
        self.reported = done

    def add(self, count: int) -> None:
        self.done += count
        now = time.monotonic()
        # Najviše 4 puta u sekundi, ali i na svakih 1 % (brza veza ili mali fajlovi u testovima)
        if now - self.last_report >= 0.25 or self.done - self.reported >= MODEL_BYTES / 100:
            self.samples = [(at, done) for at, done in self.samples if now - at <= 5] + [(now, self.done)]
            self.report(now)

    def report(self, now: float | None = None) -> None:
        now = now or time.monotonic()
        self.last_report = now
        self.reported = self.done
        first_at, first_done = self.samples[0]
        speed = (self.done - first_done) / (now - first_at) if now - first_at >= 0.5 else None
        if self.callback:
            self.callback(min(self.done, MODEL_BYTES), MODEL_BYTES, speed)


def _download_file(url: str, part: Path, size: int, meter: _Meter, cancel, opener, timeout) -> None:
    parts = urlsplit(url)
    local = parts.hostname in ("127.0.0.1", "localhost")
    if not (parts.scheme == "https" or (parts.scheme == "http" and local)):
        raise SpeechError("Nesiguran link za model.")
    have = part.stat().st_size if part.is_file() else 0
    if have > size:
        part.unlink()
        have = 0
    if have == size:
        return
    from . import __version__

    headers = {"User-Agent": f"VideoDownload/{__version__}"}
    if have:
        headers["Range"] = f"bytes={have}-"
    try:
        response = opener(urllib.request.Request(url, headers=headers), timeout=timeout)
    except OSError as exc:
        raise SpeechError(f"Model se ne može preuzeti: {exc}", key="speech.error.network") from exc
    with response:
        if have and getattr(response, "status", 200) != 206:
            have = 0  # server ne nastavlja: ispočetka
            meter.done -= part.stat().st_size if part.is_file() else 0
        with open(part, "ab" if have else "wb") as file:
            while True:
                if cancel is not None and cancel.is_set():
                    raise SpeechCancelled("Preuzimanje modela je prekinuto.")
                try:
                    chunk = response.read(1024 * 1024)
                except OSError as exc:
                    raise SpeechError(f"Preuzimanje modela je prekinuto: {exc}", key="speech.error.network") from exc
                if not chunk:
                    break
                file.write(chunk)
                have += len(chunk)
                if have > size:
                    raise SpeechError("Fajl modela je veći nego što treba.")
                meter.add(len(chunk))
    if have != size:
        raise SpeechError("Preuzimanje modela nije završeno (veza je prekinuta).", key="speech.error.network")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------- titl ----------

def subtitle_path(video: str, language: str) -> str:
    return f"{os.path.splitext(video)[0]}.{language}.{SUFFIX}.srt"


def is_speech_subtitle(path: str) -> bool:
    return path.lower().endswith(f".{SUFFIX}.srt")


def choose_language(site_language: str | None, detected: list[str]) -> str | None:
    """Jezik titla: onaj koji sajt javlja, inače onaj koji model najčešće prepozna u dijelovima videa.
    Bosanski, hrvatski i srpski idu kao „bs" (latinica s našim slovima)."""
    code = str(site_language or "").strip().lower().split("-")[0]
    if not code and detected:
        code = max(dict.fromkeys(detected), key=detected.count)  # najčešći; kod izjednačenja prvi viđen
    if not code:
        return None
    return "bs" if code in SOUTH_SLAVIC else code


def keep_line(text: str, start: float, end: float, no_speech: float, avg_logprob: float) -> bool:
    """Izbacuje tekst koji model izmisli preko tišine, muzike ili učenja: npr. jedna riječ preko 30 s."""
    words = len(text.split())
    if not words:
        return False
    if no_speech > 0.6 and avg_logprob < -1.0:
        return False
    # Govor ima bar ~1 riječ u 3 s; nekoliko riječi preko 10 i više sekundi je izmišljeno (npr. „Al-Fatiha" preko
    # cijelog učenja ili poznata fraza „prevod: …" preko tišine).
    return not (end - start > 10 and words / (end - start) < 0.34)


def format_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def parse_time(stamp: str) -> float:
    match = re.fullmatch(r"\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*", stamp)
    if not match:
        raise ValueError(stamp)
    hours, minutes, secs, ms = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(ms.ljust(3, "0")) / 1000


def write_srt(lines: list[Line], path: str) -> None:
    blocks = [f"{n}\n{format_time(line.start)} --> {format_time(line.end)}\n{line.text.strip()}\n"
              for n, line in enumerate((line for line in lines if line.text.strip()), 1)]
    Path(path).write_text("\n".join(blocks), encoding="utf-8")


def read_srt(path: str) -> list[Line]:
    text = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    lines = []
    for block in re.split(r"\n\s*\n", text.strip()):
        rows = block.split("\n")
        timing = next((i for i, row in enumerate(rows) if "-->" in row), None)
        if timing is None:
            continue
        start, end = rows[timing].split("-->", 1)
        try:
            lines.append(Line(parse_time(start), parse_time(end.split()[0] if end.split() else end),
                              "\n".join(rows[timing + 1:]).strip()))
        except ValueError:
            continue
    return lines


def decode_audio(video: str, ffmpeg: str | None = None, cancel: threading.Event | None = None):
    """Zvuk videa kao niz brojeva (16 kHz, mono) preko ffmpeg-a iz paketa; bez PyAV biblioteke (−70 MB)."""
    import numpy as np

    ffmpeg = ffmpeg or find_tool("ffmpeg")
    if not ffmpeg:
        raise SpeechError("ffmpeg nije pronađen.")
    command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-i", video, "-vn", "-ac", "1",
               "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise SpeechError(f"ffmpeg se nije pokrenuo: {exc}") from exc
    chunks = []
    total = 0
    with process:
        while True:
            if cancel is not None and cancel.is_set():
                process.kill()
                raise SpeechCancelled("Prekinuto.")
            chunk = process.stdout.read(SAMPLE_RATE * 2 * 30)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SECONDS * SAMPLE_RATE * 2:
                process.kill()
                raise SpeechError("Video je predug za titl iz govora (više od 4 sata).")
            chunks.append(chunk)
    if process.returncode != 0 or not total:
        raise SpeechError("Video nema zvuk koji se može pročitati.")
    data = b"".join(chunks)
    chunks.clear()
    samples = np.frombuffer(data, dtype=np.int16, count=len(data) // 2).astype(np.float32)
    del data
    samples /= 32768.0  # u istom nizu: bez još jedne kopije
    return samples


def _import_engine():
    """faster-whisper uvozi PyAV i huggingface_hub čak i kad ih ne koristi; program ih ne pakuje (zvuk čita
    ffmpeg, model preuzima ovaj modul), pa se umjesto njih podmetnu prazni moduli."""
    import importlib.util

    for name in ("av", "huggingface_hub"):
        if name not in sys.modules and importlib.util.find_spec(name) is None:
            sys.modules[name] = types.ModuleType(name)
    from faster_whisper import WhisperModel

    return WhisperModel


def transcribe(video: str, target: str | None = None, site_language: str | None = None,
               on_progress: Callable[[float | None], None] | None = None,
               cancel: threading.Event | None = None, folder: Path | None = None,
               model_factory=None, audio=None) -> str:
    """Napravi titl iz govora za `video`; vraća putanju .srt fajla („… .bs.iz-govora.srt" pored videa)."""
    folder = folder or model_dir()
    if model_factory is None:
        if not model_ready(folder):
            raise SpeechError("Model za prepoznavanje govora nije preuzet.")
        WhisperModel = _import_engine()
        threads = max(1, (os.cpu_count() or 2) - 1)

        def model_factory():
            return WhisperModel(str(folder), device="cpu", compute_type="int8", cpu_threads=threads)

    report = on_progress or (lambda fraction: None)
    report(None)
    # Jedno prepoznavanje u isto vrijeme (više preuzimanja odjednom): model zauzima ~2 GB memorije i sve jezgre.
    while not _ONE_AT_A_TIME.acquire(timeout=0.2):
        if cancel is not None and cancel.is_set():
            raise SpeechCancelled("Prekinuto.")
    try:
        return _transcribe(video, target, site_language, report, cancel, model_factory, audio)
    finally:
        _ONE_AT_A_TIME.release()


_ONE_AT_A_TIME = threading.Lock()


def _transcribe(video, target, site_language, report, cancel, model_factory, audio) -> str:
    samples = decode_audio(video, cancel=cancel) if audio is None else audio
    duration = len(samples) / SAMPLE_RATE
    if duration < 1:
        raise SpeechError("Video nema govora.")
    model = model_factory()
    language = choose_language(site_language, [] if site_language else _detect(model, samples, cancel))
    known = _languages(model)
    if language and known and language not in known:
        language = None  # jezik koji model ne zna: neka ga sam prepozna
    segments, info = model.transcribe(samples, language=language, task="transcribe", beam_size=5, vad_filter=True,
                                      condition_on_previous_text=False, initial_prompt=PROMPTS.get(language or ""))
    language = language or getattr(info, "language", None) or "und"
    lines = []
    for segment in segments:
        if cancel is not None and cancel.is_set():
            raise SpeechCancelled("Prekinuto.")
        text = segment.text.strip()
        if keep_line(text, segment.start, segment.end, segment.no_speech_prob, segment.avg_logprob):
            lines.append(Line(segment.start, segment.end, text))
        report(min(1.0, segment.end / duration))
    if not lines:
        raise SpeechError("U videu nije prepoznat govor.")
    target = target or subtitle_path(video, "bs" if language in SOUTH_SLAVIC else language)
    write_srt(lines, target)
    report(1.0)
    return target


def _languages(model) -> set[str]:
    try:
        return set(model.supported_languages)
    except AttributeError:
        return set()


def _detect(model, samples, cancel) -> list[str]:
    """Jezik iz četiri dijela od po 30 s raspoređena kroz video (uvod je često muzika ili drugi jezik); svaki
    dio na procesoru traje ~5–15 s, pa ih nema više."""
    window = 30 * SAMPLE_RATE
    if len(samples) <= window:
        starts = [0]
    else:
        last = len(samples) - window
        starts = sorted({int(last * share) for share in (0.2, 0.4, 0.6, 0.8)})
    found = []
    for start in starts:
        if cancel is not None and cancel.is_set():
            raise SpeechCancelled("Prekinuto.")
        try:
            language, probability, _all = model.detect_language(samples[start:start + window])
        except Exception:  # dio bez govora: preskače se
            continue
        if probability >= 0.5:
            found.append(language)
    return found

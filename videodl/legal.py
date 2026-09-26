"""Pravni dokumenti programa i spisak komponenti trećih strana (bez Qt-a).

Jedan izvor za tri mjesta: instaler (stranica ugovora i napomena o privatnosti), aplikaciju
(Pomoć → Ugovori i licence) i build (THIRD-PARTY-NOTICES.txt i folder „licenses").
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from .runtime import PROJECT_ROOT, bundle_dir, is_frozen

ASSETS = Path(__file__).resolve().parent / "assets"
# (vrsta, ključ prevoda za naslov); isti redoslijed kao kartice u aplikaciji
DOCUMENTS = (("eula", "legal.eula"), ("terms", "legal.terms"), ("privacy", "legal.privacy"))


def document_path(kind: str, language: str) -> Path:
    path = ASSETS / f"{kind}_{language}.txt"
    return path if path.is_file() else ASSETS / f"{kind}_en.txt"


def document_text(kind: str, language: str) -> str:
    return document_path(kind, language).read_text(encoding="utf-8-sig")


def agreement_text(language: str) -> str:
    """Stranica u instaleru: licencni ugovor pa uslovi korištenja, jedno ispod drugog."""
    return document_text("eula", language).rstrip() + "\n\n\n" + document_text("terms", language)


@dataclass(frozen=True)
class Component:
    name: str
    license: str
    url: str
    license_files: tuple[str, ...]  # imena u folderu „licenses"
    note: str = ""


# Python paketi čije licence build kopira iz *.dist-info (ime distribucije → prefiks fajla)
PYTHON_DISTRIBUTIONS = ("yt-dlp", "yt-dlp-ejs", "curl_cffi", "certifi", "brotli", "requests", "urllib3",
                        "pycryptodomex")

# FFmpeg u paketu zavisi od sistema: Windows koristi gyan.dev build, Mac (beta) build Martina Riedla.
FFMPEG_WINDOWS = Component(
    "FFmpeg 9.0.2 (essentials build by gyan.dev)", "GPL-3.0", "https://ffmpeg.org/", ("GPL-3.0.txt",),
    "Bundled binaries: ffmpeg/ffprobe version 9.0.2-essentials_build-www.gyan.dev (SHA-256 in "
    "BUILD-MANIFEST.json). Source code of this release: https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz ; "
    "build configuration: https://www.gyan.dev/ffmpeg/builds/ and https://github.com/GyanD/codexffmpeg . "
    "A copy of the complete corresponding source code is available on request for three years.")
FFMPEG_MAC = Component(
    "FFmpeg 9.0.2 (macOS arm64 build by Martin Riedl)", "GPL-3.0", "https://ffmpeg.org/", ("GPL-3.0.txt",),
    "Bundled binaries: ffmpeg/ffprobe 9.0.2 from https://ffmpeg.martin-riedl.de/ (SHA-256 in BUILD-MANIFEST.json). "
    "Source code of this release: https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz ; build script: "
    "https://git.martin-riedl.de/ffmpeg/build-script . "
    "A copy of the complete corresponding source code is available on request for three years.")
FFMPEG = FFMPEG_MAC if sys.platform == "darwin" else FFMPEG_WINDOWS
FFMPEG_BUILDS = (FFMPEG_WINDOWS, FFMPEG_MAC)

COMPONENTS = (
    Component("yt-dlp", "Unlicense", "https://github.com/yt-dlp/yt-dlp", ("yt-dlp-LICENSE",)),
    Component("yt-dlp-ejs", "Unlicense, MIT, ISC", "https://github.com/yt-dlp/ejs", ("yt-dlp-ejs-LICENSE",)),
    FFMPEG,
    Component("Qt for Python (PySide6, Shiboken6)", "LGPL-3.0", "https://doc.qt.io/qtforpython/",
              ("LGPL-3.0.txt", "GPL-3.0.txt"),
              "Source code: https://code.qt.io/ . The Qt libraries are separate files and can be replaced."),
    Component("Node.js", "MIT and the licenses of its dependencies", "https://nodejs.org/", ("Node.js-LICENSE.txt",)),
    Component("curl_cffi", "MIT", "https://github.com/lexiforest/curl_cffi", ("curl_cffi-LICENSE",)),
    Component("certifi", "MPL-2.0", "https://github.com/certifi/python-certifi", ("certifi-LICENSE",)),
    Component("Brotli", "MIT", "https://github.com/google/brotli", ("brotli-LICENSE",)),
    Component("Requests", "Apache-2.0", "https://github.com/psf/requests", ("requests-LICENSE", "requests-NOTICE")),
    Component("urllib3", "MIT", "https://github.com/urllib3/urllib3", ("urllib3-LICENSE",)),
    Component("PyCryptodome (pycryptodomex)", "BSD-2-Clause, Public Domain", "https://www.pycryptodome.org/",
              ("pycryptodomex-LICENSE",)),
    Component("Python", "PSF-2.0", "https://www.python.org/", ("Python-LICENSE.txt",)),
)


def site_components(published_mac: bool = False) -> tuple[Component, ...]:
    """Komponente za stranicu licenci na sajtu: ista lista bez obzira na kom sistemu se sajt pravi.
    Mac build ffmpeg-a se dodaje tek kad Mac verzija bude javno objavljena."""
    builds = FFMPEG_BUILDS if published_mac else (FFMPEG_WINDOWS,)
    result = []
    for component in COMPONENTS:
        result.extend(builds if component is FFMPEG else (component,))
    return tuple(result)


def license_files(component: Component, folder: Path | None) -> list[str]:
    """Stvarna imena fajlova u folderu „licenses" (ime bez tačke je prefiks, npr. yt-dlp-LICENSE*)."""
    if folder is None or not folder.is_dir():
        return [name if "." in name else f"{name}*" for name in component.license_files]
    present = sorted(path.name for path in folder.iterdir() if path.is_file())
    return [name for wanted in component.license_files for name in present
            if name == wanted or ("." not in wanted and name.startswith(wanted))]


def notices_text(folder: Path | None = None) -> str:
    lines = ["Video Download includes the following third-party software.",
             "Their licenses apply to them; the full texts are in the \"licenses\" folder.", ""]
    for component in COMPONENTS:
        lines.append(f"- {component.name} — {component.license} — {component.url}")
        files = ", ".join(f"licenses/{name}" for name in license_files(component, folder)) or "—"
        lines.append(f"  License text: {files}")
        if component.note:
            lines.append(f"  {component.note}")
    return "\n".join(lines) + "\n"


def licenses_dir() -> Path:
    """Instalirana verzija: pored .exe-a (Mac: u paketu, Contents/Frameworks); razvoj: installer/licenses."""
    return bundle_dir() / "licenses" if is_frozen() else PROJECT_ROOT / "installer" / "licenses"


def python_license_path() -> Path:
    # Windows ga drži u korijenu instalacije, Mac/Linux u lib/pythonX.Y.
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    for candidate in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "lib" / version / "LICENSE.txt"):
        if candidate.is_file():
            return candidate
    return Path(sys.base_prefix) / "LICENSE.txt"

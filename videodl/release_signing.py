"""Potpisan opis izdanja (Ed25519), bez Qt-a.

Uz svako izdanje ide `release.json` (verzija, ime instalera, veličina, SHA-256) i `release.json.sig`.
Aplikacija instaler pokreće tek kad potpis odgovara jednom od ugrađenih javnih ključeva i kad se
instaler poklapa s opisom. SHA-256 sam po sebi nije dovoljan: i instaler i zbir dolaze sa istog mjesta.

Privatni ključ je SAMO kod vlasnika, van repoa i van OneDrive-a (VIDEODL_SIGNING_KEY ili
%USERPROFILE%\\.videodl\\release-signing-key.pem). Bez njega se ne mogu objaviti ažuriranja koja
postojeće instalacije prihvataju — zato mora postojati sigurnosna kopija.
"""

import hashlib
import json
import os
from pathlib import Path

from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import eddsa

MANIFEST_NAME = "release.json"
SIGNATURE_NAME = "release.json.sig"
# Javni ključevi kojima aplikacija vjeruje (više njih = moguća zamjena ključa bez prekida ažuriranja).
PUBLIC_KEYS = ("8ce3563b3c8ba4bbba778fc6c6f1cd3e569a13f94ffdae2a7e61b293344347f2",)  # 26.9.2026


class SignatureError(Exception):
    """Opis izdanja nije potpisan našim ključem ili se instaler ne poklapa s njim."""


def key_path() -> Path:
    override = os.environ.get("VIDEODL_SIGNING_KEY")
    return Path(override) if override else Path.home() / ".videodl" / "release-signing-key.pem"


def generate_key(path: Path | None = None) -> str:
    """Pravi novi privatni ključ (samo ako ga još nema); vraća javni ključ (hex)."""
    path = path or key_path()
    if path.exists():
        raise FileExistsError(f"Ključ već postoji: {path}")
    key = ECC.generate(curve="ed25519")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.export_key(format="PEM"), encoding="ascii")
    return public_key_hex(key)


def load_key(path: Path | None = None) -> ECC.EccKey:
    path = path or key_path()
    if not path.is_file():
        raise SignatureError(f"Privatni ključ za potpis izdanja nije pronađen: {path}")
    return ECC.import_key(path.read_text(encoding="ascii"))


def public_key_hex(key: ECC.EccKey) -> str:
    return key.public_key().export_key(format="raw").hex()


def manifest_bytes(version: str, installer: Path) -> bytes:
    digest = hashlib.sha256()
    with open(installer, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    data = {"app": "Video Download", "version": version, "installer": installer.name,
            "size": installer.stat().st_size, "sha256": digest.hexdigest()}
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(data: bytes, key: ECC.EccKey) -> bytes:
    return eddsa.new(key, "rfc8032").sign(data)


def write_signed_manifest(version: str, installer: Path, key: ECC.EccKey | None = None) -> tuple[Path, Path]:
    key = key or load_key()
    data = manifest_bytes(version, installer)
    manifest = installer.with_name(MANIFEST_NAME)
    signature = installer.with_name(SIGNATURE_NAME)
    manifest.write_bytes(data)
    signature.write_text(sign(data, key).hex() + "\n", encoding="ascii")
    return manifest, signature


def verify_manifest(data: bytes, signature_text: str, public_keys=None) -> dict:
    """Vraća opis izdanja ako ga je potpisao jedan od naših ključeva; inače SignatureError."""
    try:
        signature = bytes.fromhex(signature_text.strip())
    except ValueError as exc:
        raise SignatureError("Potpis nije ispravnog oblika.") from exc
    for public in public_keys if public_keys is not None else PUBLIC_KEYS:
        try:
            eddsa.new(eddsa.import_public_key(bytes.fromhex(public)), "rfc8032").verify(data, signature)
        except ValueError:
            continue
        try:
            manifest = json.loads(data.decode("utf-8"))
        except ValueError as exc:
            raise SignatureError("Opis izdanja nije ispravan JSON.") from exc
        if not isinstance(manifest, dict):
            raise SignatureError("Opis izdanja nije ispravan.")
        return manifest
    raise SignatureError("Opis izdanja nije potpisan ključem ovog programa.")


def check_installer(manifest: dict, version: str, installer: Path) -> None:
    """Instaler mora biti baš onaj iz potpisanog opisa: ista verzija, ime, veličina i SHA-256."""
    digest = hashlib.sha256()
    with open(installer, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    expected = (manifest.get("version"), manifest.get("installer"), manifest.get("size"), manifest.get("sha256"))
    actual = (version, installer.name, installer.stat().st_size, digest.hexdigest())
    if expected != actual:
        raise SignatureError("Instaler se ne poklapa s potpisanim opisom izdanja.")

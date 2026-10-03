"""Roditeljska zaštita (Ahmed 3.10.2026): kad je uključena, sadržaj 18+ se ne preuzima i ne nudi se potvrda.

Isto pravilo 18+ kao i inače (`probe.is_adult`, YouTube izuzet). PIN je opcion (4–8 cifara): ako postoji,
isključivanje zaštite ga traži. Čuva se samo otisak PBKDF2-SHA256 sa nasumičnom solju, nikad PIN.
Ovo štiti od slučajnog preuzimanja; nije brava koja se ne može zaobići (npr. ponovnom instalacijom).
Bez Qt-a; prozor je u dialogs.py, podešavanja (QSettings) u gui.py.
"""

import hashlib
import hmac
import os
import re

ITERATIONS = 200_000
_PIN = re.compile(r"\d{4,8}")


def valid_pin(pin: str) -> bool:
    return bool(_PIN.fullmatch(pin or ""))


def hash_pin(pin: str, salt: bytes | None = None, iterations: int = ITERATIONS) -> str:
    if not valid_pin(pin):
        raise ValueError("PIN mora imati 4 do 8 cifara")
    salt = salt if salt is not None else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("ascii"), salt, iterations)
    return f"pbkdf2-sha256${iterations}${salt.hex()}${digest.hex()}"


def check_pin(pin: str, stored: str) -> bool:
    """True ako `pin` odgovara sačuvanom otisku; pokvaren zapis nikad ne propušta."""
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != "pbkdf2-sha256" or not valid_pin(pin):
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", pin.encode("ascii"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, AttributeError):
        return False


def blocks(enabled: bool, item) -> bool:
    """Da li zaštita zaustavlja ovu stavku (označena kao 18+ po pravilima iz probe.py)."""
    return bool(enabled and getattr(item, "adult", False))

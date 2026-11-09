"""Normalización de respuestas escritas para la corrección determinista."""
import re
import unicodedata

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "´": "'", "`": "'"}
_SPACES = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\s.,;:!?\"'()]+|[\s.,;:!?\"'()]+$")
_WORD = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:['\-.,][A-Za-zÀ-ÿ0-9]+)*")


def normalize(text: str) -> str:
    """Minúsculas, comillas unificadas, espacios colapsados, sin puntuación en los bordes."""
    if text is None:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    for bad, good in _QUOTES.items():
        text = text.replace(bad, good)
    text = _SPACES.sub(" ", text).strip().lower()
    return _EDGE_PUNCT.sub("", text)


def tokens(text: str) -> list[str]:
    """Palabras normalizadas, conservando cifras como 3.5 o 4,0."""
    return [t.lower() for t in _WORD.findall(normalize(text))]


def word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


def parse_number(raw) -> float | None:
    """Acepta '15', '15%', '0,5', '0.5 pp', '1,234.5' o '1.234,5'. Devuelve None si no es número."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().lower()
    s = re.sub(r"[%a-z\s]+$", "", s).strip()
    s = s.replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        # El último separador es el decimal.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def contains_phrase(text: str, phrase: str) -> bool:
    """Coincidencia de frase completa (no subcadena dentro de otra palabra)."""
    t = " " + " ".join(tokens(text)) + " "
    p = " " + " ".join(tokens(phrase)) + " "
    return p.strip() != "" and p in t

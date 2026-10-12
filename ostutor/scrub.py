"""Secret scanning and PII redaction.

Two distinct policies, deliberately:

  SECRETS (API keys, private keys, credentials) -> the row is DESTROYED.
    Redaction is insufficient: a partly-redacted secret still teaches the shape
    of the secret.
  PII (email, phone, SSN, card) -> REDACTED to stable placeholders. The
    pedagogical content around an email address is usually fine; the address
    is not.

Two false-positive classes are handled explicitly, because both are common here
and both would destroy good data:
  * Shell rows are exempt from phone/card rules. `timeout 300 500 1000` and
    `ssh -p 5551234567` are lessons, not leaks.
  * Card numbers must pass a Luhn checksum. A 16-digit numeral in a maths word
    problem, or a page-table address, is not a payment card.
"""
import re

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "aws_secret": re.compile(r"\baws_secret_access_key\s*[=:]\s*\S{20,}", re.I),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    "generic_secret": re.compile(
        r"\b(?:password|passwd|api[_-]?key|secret|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]", re.I),
}

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
PHONE_RE = re.compile(r"(?<![\d.])(?:\+?\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\d.])")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")

PII_PATTERNS = [("ssn", SSN_RE, "<SSN>"), ("email", EMAIL_RE, "<EMAIL>"),
                ("phone", PHONE_RE, "<PHONE>"), ("cc", CARD_RE, "<CARD>")]

SAFE_EMAIL = re.compile(r"@(?:example|test|localhost|domain|email|mail|foo|bar)\.", re.I)
SHELL_EXEMPT = {"phone", "cc"}


def _luhn(digits: str) -> bool:
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def find_secrets(text: str):
    """Names of every secret pattern present. Non-empty => destroy the row."""
    return [name for name, rx in SECRET_PATTERNS.items() if rx.search(text)]


def redact_pii(text: str, category: str):
    """Redact PII in place. Returns (clean_text, {kind: count})."""
    hits = {}
    for name, rx, repl in PII_PATTERNS:
        if category == "shell" and name in SHELL_EXEMPT:
            continue

        def _sub(m, _name=name, _repl=repl):
            tok = m.group(0)
            if _name == "email" and SAFE_EMAIL.search(tok):
                return tok
            if _name == "cc" and not _luhn(re.sub(r"\D", "", tok)):
                return tok
            hits[_name] = hits.get(_name, 0) + 1
            return _repl

        text = rx.sub(_sub, text)
    return text, hits

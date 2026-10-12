"""Canonical record schema and strict validation.

Every record carries this shape from ingestion onward, so a malformed row cannot
travel silently. `lineage` records file, row index and generator seed, making any
row in the shipped dataset traceable to the byte it came from.
"""
import hashlib
import json
from dataclasses import asdict, dataclass, field

CATEGORIES = {"procedural", "conceptual", "tutoring", "shell", "replay"}
MODES = {"solve", "explain", "tutor", "shell"}
ROLES = {"system", "user", "assistant"}


@dataclass
class Record:
    category: str
    subcategory: str
    mode: str
    domain: str
    messages: list
    source: str
    license: str
    commercial_ok: bool
    attribution: bool = True
    quality: float = 0.0
    difficulty: float = 0.0          # curriculum signal, 0..1
    surprise: float = 0.0            # SuRe: base-model NLL, set for replay rows
    n_chars: int = 0
    n_tokens: int = 0
    order: int = -1
    template_id: str = ""            # solution skeleton, for template-share checks
    lineage: dict = field(default_factory=dict)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            blob = f"{self.source}|{json.dumps(self.messages, ensure_ascii=False)}"
            self.id = hashlib.blake2b(blob.encode(), digest_size=10).hexdigest()
        self.n_chars = sum(len(m["content"]) for m in self.messages)

    def dict(self):
        return asdict(self)


class ValidationError(Exception):
    pass


def validate(r, strict=True):
    """Return a list of problems. strict=True adds ship-ready invariants."""
    p = []
    if r["category"] not in CATEGORIES:
        p.append(f"bad category {r['category']}")
    if r["mode"] not in MODES:
        p.append(f"bad mode {r['mode']}")
    ms = r["messages"]
    if len(ms) < 2:
        p.append("fewer than 2 messages")
    for m in ms:
        if m["role"] not in ROLES:
            p.append(f"bad role {m['role']}")
        if not str(m.get("content", "")).strip():
            p.append("empty message content")
    body = [m for m in ms if m["role"] != "system"]
    if body:
        if body[0]["role"] != "user":
            p.append("conversation must open with user")
        if body[-1]["role"] != "assistant":
            p.append("conversation must close with assistant")
        for i in range(len(body) - 1):
            if body[i]["role"] == body[i + 1]["role"]:
                p.append("non-alternating roles")
                break
    if strict:
        if not r.get("commercial_ok"):
            p.append("non-commercial licence in shipped set")
        if any("<think>" in m["content"] for m in ms):
            p.append("<think> block present")
    return p


def assert_valid(r, strict=True):
    problems = validate(r, strict)
    if problems:
        raise ValidationError(f"{r.get('id', '?')}: " + "; ".join(problems))

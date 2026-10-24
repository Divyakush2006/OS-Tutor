"""Check shell commands in a Shell-mode answer before the student copies them.

Shell answers come from the model, and a command that runs without error can still do
the wrong thing. The recorded case: `ls -lh ... | sort -k 5 -r` sorts the human-readable
sizes as text, so 9.5M lands above 12M. Each rule below is one such pitfall. Where the
fix is mechanical the command is corrected in place and the change is explained; where
it is a matter of risk the student is warned.
"""
import re

_FENCE = re.compile(r"```[a-z]*\n(.*?)```", re.S)
_INLINE = re.compile(r"`([^`\n]+)`")

# Output in human-readable units (1.5K, 9.5M) piped into a sort that compares text.
_HUMAN = re.compile(r"\b(?:ls\s+-\w*h\w*|du\s+-\w*h\w*|df\s+-\w*h\w*|-exec\s+ls\s+-\w*h\w*)")
_SORT = re.compile(r"\|\s*sort\b([^|;&]*)")
_FIND_NAME = re.compile(r"(\s-i?name\s+)([^\s'\"]*[*?][^\s'\"]*)")
_RM_ROOT = re.compile(r"\brm\s+-\w*[rR]\w*f?\w*\s+(?:/|/\*|~|~/|\$HOME/?)(?=\s|$)")
_CHMOD_777 = re.compile(r"\bchmod\s+(?:-R\s+)?777\b")


def _fix_sort(cmd):
    """Add -h to a sort that orders human-readable sizes; (new command, note) or None."""
    if not _HUMAN.search(cmd):
        return None
    m = _SORT.search(cmd)
    if not m:
        return None
    flags = m.group(1)
    tokens = flags.split()
    # Single-letter option clusters only ("-rn"), not "-k5" or "-t,".
    plain = [t for t in tokens if re.fullmatch(r"-[A-Za-z]+", t)]
    if "--human-numeric-sort" in tokens or any("h" in t for t in plain):
        return None
    with_n = next((t for t in plain if "n" in t), None)
    with_r = next((t for t in plain if "r" in t), None)
    if with_n:
        new_flags = flags.replace(with_n, with_n.replace("n", "h"), 1)
    elif with_r:
        new_flags = flags.replace(with_r, with_r + "h", 1)
    else:
        new_flags = flags.rstrip() + " -h" + flags[len(flags.rstrip()):]
    new = cmd[:m.start(1)] + new_flags + cmd[m.end(1):]
    return new, ("`sort` compared the human-readable sizes as text, so 9.5M would sort above "
                 "12M; `-h` makes it compare 1K < 1M < 1G by value.")


def _fix_find(cmd):
    m = _FIND_NAME.search(cmd)
    if not m:
        return None
    new = cmd[:m.start(2)] + f'"{m.group(2)}"' + cmd[m.end(2):]
    return new, ("the pattern after `-name` was unquoted, so the shell could expand it against "
                 "the current directory before `find` saw it; it is now quoted.")


FIXES = [_fix_sort, _fix_find]
WARNINGS = [
    (_RM_ROOT, "this deletes from the root or home directory recursively and cannot be undone; "
               "check the path, and try it first with `ls` in place of `rm`."),
    (_CHMOD_777, "mode 777 lets every user write and execute the file; prefer the narrowest mode "
                 "that works, such as 755 for a script or 644 for a data file."),
]


def _commands(text):
    """The command strings in an answer: fenced blocks line by line, inline code, and a
    bare one-line answer."""
    found = []
    for block in _FENCE.findall(text):
        found += [l.strip() for l in block.splitlines() if l.strip()]
    found += [c.strip() for c in _INLINE.findall(_FENCE.sub("", text))]
    if not found and "\n" not in text.strip():
        found.append(text.strip())
    return found


def check_shell(text):
    """(answer with mechanical fixes applied, notes). An unchanged answer has no notes."""
    notes = []
    for cmd in _commands(text or ""):
        new = cmd
        for fix in FIXES:
            r = fix(new)
            if r:
                new, why = r
                notes.append(f"`{cmd}` → `{new}`: {why}")
        if new != cmd:
            text = text.replace(cmd, new)
        for pat, why in WARNINGS:
            if pat.search(new):
                notes.append(f"Caution with `{new}`: {why}")
    return text, notes

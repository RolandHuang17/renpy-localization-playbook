"""Extract translatable dialogue from a game that ships LOOSE .rpy sources.

Playbook mode B: no *.rpa archives, so tools/extract.py (which harvests compiled
ASTs out of archives) is not needed. Say statements are read straight from the
script files. Output uses the same JSON record shape, so tools/build_tl.py,
tools/qa.py and tools/uninstall.py work unchanged.

Scope rule: only dialogue that renders in the say box is collected. Statements
inside `screen` blocks (menus, HUD, preferences) and bare `define`/`_()` strings
are skipped on purpose - those boxes have fixed height and would overlap.

Usage:
    python tools/rpy_extract.py --game game --out localization/en-zh.json
"""

import argparse
import collections
import json
import os
import re
import sys

CHAR_DEF_RE = re.compile(
    r"^\s*(?:define\s+)?([A-Za-z_][\w.]*)\s*=\s*(?:Character|DynamicCharacter)\s*\("
)
# `define e = Character("Ava", ...)` - the display name lives in the first arg.
CHAR_NAME_RE = re.compile(
    r"(?:define\s+)?([A-Za-z_][\w.]*)\s*=\s*(?:Dynamic)?Character\s*\(\s*(\"(?:[^\"\\]|\\.)*\"|None)"
)
SAY_RE = re.compile(
    r'^(?P<ind> *)(?:(?P<who>[A-Za-z_][\w.]*)\s+)?"(?P<what>(?:[^"\\]|\\.)*)"(?P<tail>\s*:|\s+\S.*)?\s*$'
)
SCREEN_RE = re.compile(r"^\s*screen\s+\w+")
USE_RE = re.compile(r"^\s*(?:transclude|use)\s+")
BLOCK_KW = {
    "label", "menu", "screen", "init", "python", "if", "elif", "else", "for",
    "while", "try", "except", "finally", "transform", "style", "define",
    "default", "image", "placeholder", "test", "with", "use", "show", "add",
}
ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b",
    "f": "\f", "v": "\v", "\\": "\\", '"': '"', "'": "'", "u": "u", "U": "U",
}
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uF900-\uFAFF]")


def unescape(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "x":
                out.append(chr(int(s[i + 2 : i + 4], 16)))
                i += 4
                continue
            if nxt in ("u", "U"):
                n = 4 if nxt == "u" else 8
                out.append(chr(int(s[i + 2 : i + 2 + n], 16)))
                i += 2 + n
                continue
            out.append(ESCAPES.get(nxt, "\\" + nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def character_vars(game_dir, extra_paths):
    """Speaker variables the game defines. A say statement must use one of these."""
    names, display = set(), {}
    for path in extra_paths:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            src = f.read()
        for m in CHAR_DEF_RE.finditer(src):
            names.add(m.group(1))
        for m in CHAR_NAME_RE.finditer(src):
            var, raw = m.group(1), m.group(2)
            names.add(var)
            if raw != "None":
                display[var] = unescape(raw[1:-1])
    return names, display


def statement_context(code_lines):
    """Yield (line_number, code, contexts) where contexts = block keywords enclosing it.

    Dialogue only ever executes inside a `label`, so the enclosing-block stack is how
    we tell a say statement apart from a bare string in a screen or style block.
    """
    stack = []
    for num, raw in code_lines:
        indent = len(raw) - len(raw.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        yield num, raw, {kw for _, kw in stack}
        if raw.rstrip().endswith(":"):
            kw = raw.strip().split(None, 1)[0]
            if kw in BLOCK_KW or kw.endswith(":"):
                stack.append((indent, kw.rstrip(":")))


def strip_comment(line):
    out, in_q, esc = [], False, False
    for ch in line:
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\":
            esc = True
            out.append(ch)
            continue
        if ch == '"':
            in_q = not in_q
        if ch == "#" and not in_q:
            break
        out.append(ch)
    return "".join(out)


def harvest(game_dir, skip_dirs=("tl", "saves", "cache", "lib")):
    rpy = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fn in sorted(files):
            if fn.endswith(".rpy"):
                rpy.append(os.path.join(root, fn))
    rpy = sorted(rpy)
    chars, display = character_vars(game_dir, rpy)
    records, stats = collections.OrderedDict(), collections.Counter()

    for path in rpy:
        rel = os.path.relpath(path, os.curdir).replace("\\", "/")
        with open(path, encoding="utf-8-sig") as f:
            raw_lines = f.read().splitlines()
        code_lines = []
        for num, raw in enumerate(raw_lines, 1):
            code = strip_comment(raw).rstrip()
            if code.strip():
                code_lines.append((num, code))
        for num, code, ctx in statement_context(code_lines):
            if code.lstrip().startswith("$"):
                continue
            m = SAY_RE.match(code)
            if not m:
                continue
            who, tail = m.group("who"), (m.group("tail") or "").strip()
            if who is None:
                if "label" not in ctx:
                    stats["skipped_not_in_label"] += 1
                    continue
                kind = "menu" if tail == ":" else "say"
            elif who in chars:
                kind = "say"
            else:
                continue
            en = unescape(m.group("what"))
            stats["seen"] += 1
            if CJK_RE.search(en):
                stats["skipped_already_cjk"] += 1
                continue
            key = (kind, en)
            if key in records:
                records[key]["idents"].append("%s:%s" % (rel, num))
                stats["duplicate_old"] += 1
                continue
            records[key] = {
                "id": "r%06d" % (len(records) + 1),
                "kind": kind,
                "en": en,
                "file": rel,
                "line": num,
                "who": who,
                "idents": ["%s:%s" % (rel, num)],
                "zh": "",
            }
    stats["unique"] = len(records)
    return list(records.values()), chars, display, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="localization/en-zh.json")
    ap.add_argument("--speakers", default="localization/speakers.json")
    ap.add_argument("--report", default="localization/extract_report.txt")
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(args.game, "script.rpy")) and not any(
        fn.endswith(".rpy") for fn in os.listdir(args.game)
    ):
        raise SystemExit("no loose .rpy found - this is mode A, use tools/extract.py")

    recs, chars, display, stats = harvest(args.game)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    with open(args.speakers, "w", encoding="utf-8") as f:
        json.dump({"vars": sorted(chars), "display_names": display}, f,
                  ensure_ascii=False, indent=1)

    by = collections.Counter(r["kind"] for r in recs)
    ch = collections.Counter()
    for r in recs:
        ch[r["kind"]] += len(r["en"])
    lines = [
        "mode              : loose .rpy sources (no archives)",
        "character vars    : %s" % ", ".join(sorted(chars)),
        "display names     : %s" % json.dumps(display, ensure_ascii=False),
        "say statements    : %d (unique %d, duplicate-old %d)"
        % (stats["seen"], stats["unique"], stats["duplicate_old"]),
    ]
    for k in sorted(by):
        lines.append(
            "  %-6s : %d strings / %d chars" % (k, by[k], ch[k])
        )
    untranslated = sum(1 for r in recs if not r["zh"])
    lines.append("untranslated      : %d" % untranslated)
    report = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()

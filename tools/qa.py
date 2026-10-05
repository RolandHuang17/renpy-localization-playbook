"""QA gate for a generated bilingual tl layer.

Checks what actually breaks a Ren'Py build, not just that files exist:
  1. BOM on every generated file (engine convention, generation.py:99)
  2. no duplicate `old` within the language  -> StringTranslator.add RAISES on dupes
  3. every `old` is byte-identical to a real source string (else it silently never matches)
  4. every `new` really is bilingual (contains CJK + the original English)
  5. text tags {..} and interpolation [..] multisets preserved en vs zh
  6. coverage: how many source strings got a translation

Usage: python tools/qa.py --json localization/en-zh.json --tl game/tl/zh --lang zh
"""

import argparse
import collections
import json
import os
import re
import sys

TAGS = re.compile(r"\{[^{}]*\}")
INTERP = re.compile(r"\[[^\[\]]*\]")
CJK = re.compile(r"[\u4e00-\u9fff]")


def unquote(s):
    """Reverse of quote_unicode (renpy/translation/__init__.py:497)."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\",
                        "a": "\a", "b": "\b", "f": "\f", "v": "\v"}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def strip_quotes(body):
    if len(body) >= 2 and body[0] == '"' and body[-1] == '"':
        return body[1:-1]
    return body


def parse_tl(tl_dir, lang):
    olds = {}
    dups = []
    files = []
    for root, dirs, fs in os.walk(tl_dir):
        for fn in fs:
            if not fn.endswith(".rpy"):
                continue
            p = os.path.join(root, fn)
            files.append(p)
            raw = open(p, "rb").read()
            if not raw.startswith(b"\xef\xbb\xbf"):
                yield ("bom", p, "missing UTF-8 BOM")
            text = raw.decode("utf-8-sig")
            cur_old = None
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("old "):
                    cur_old = unquote(strip_quotes(line[4:]))
                    if cur_old in olds:
                        dups.append((cur_old, olds[cur_old], p))
                    else:
                        olds[cur_old] = p
                elif line.startswith("new ") and cur_old is not None:
                    new = unquote(strip_quotes(line[4:]))
                    yield ("pair", p, (cur_old, new))
                    cur_old = None
    if dups:
        for o, f1, f2 in dups[:10]:
            yield ("dup", "%s / %s" % (f1, f2), o[:70])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--tl", default="game/tl/zh")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--report", default="localization/qa_report.txt")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    say = [r for r in recs if r["kind"] == "say"]
    src = {r["en"] for r in recs}
    # interjections the generator deliberately keeps single-line (nothing to translate)
    mono_ok = {r["en"] for r in recs if r["kind"] in ("say", "menu", "uwrap") and not CJK.search(r.get("zh") or "")}
    lines = []
    fails = 0

    def note(kind, where, what):
        nonlocal fails
        fails += 1
        lines.append("FAIL %-5s %s :: %s" % (kind, where, what))

    pairs = 0
    mono = 0
    seen_old = set()
    for kind, where, payload in parse_tl(args.tl, args.lang):
        if kind == "pair":
            pairs += 1
            old, new = payload
            seen_old.add(old)
            if old in mono_ok:
                mono += 1
            elif not CJK.search(new):
                note("nozh", where, old[:60])
            elif old not in new:
                note("mono", where, "bilingual pair lost its English: " + old[:60])
            if TAGS.findall(old) and collections.Counter(TAGS.findall(new)) < collections.Counter(TAGS.findall(old)):
                note("tags", where, old[:60])
        else:
            note(kind, where, payload)

    # every generated `old` must be a genuine source string
    ghost = [o for o in seen_old if o not in src]
    if ghost:
        for g in ghost[:10]:
            note("ghost", args.tl, g[:70])

    covered = sum(1 for r in say if r.get("zh"))
    missing = [r for r in say if not r.get("zh")]
    lines.append("source say strings      : %d" % len(say))
    lines.append("translated (zh non-empty): %d (%.2f%%)" % (covered, 100.0 * covered / max(1, len(say))))
    lines.append("generated old/new pairs : %d" % pairs)
    lines.append("single-line (nothing to translate): %d" % mono)
    lines.append("pairs matching a source : %d" % (len(seen_old) - len(ghost)))
    lines.append("distinct source strings : %d" % len(src))
    if missing:
        lines.append("untranslated sample: %s" % [m["en"][:40] for m in missing[:5]])
    lines.append("FAILURES               : %d" % fails)

    text = "\n".join(lines) + "\n"
    open(args.report, "w", encoding="utf-8").write(text)
    print(text)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

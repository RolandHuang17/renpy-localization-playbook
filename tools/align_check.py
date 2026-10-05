"""Alignment + leak audit for a translation table.

Tag conservation (tools/apply_trans.py) cannot catch a translation that is
attached to the WRONG line, because a shifted pair still has matching tags. This
tool catches what that check cannot:

  1. MISSING-NAME  a proper noun present in the English is absent from the
     Chinese. Almost always means the pair is off by one line.
  2. LEAK          a lowercase English word survived inside the Chinese text,
     i.e. the sentence was left half-translated.
  3. EXTRA-NAME    the Chinese introduces a name the English does not contain
     (usually a legitimate choice, e.g. an untranslated title that reads
     "Ava 老师" in Chinese, so warn only).

Usage:
    python tools/align_check.py
    python tools/align_check.py --names Ava Noah Liam
"""

import argparse
import collections
import json
import re
import sys

TAGS = re.compile(r"\{[^{}]*\}")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
LOWERCASE_LEAK = re.compile(r"(?<![A-Za-z])[a-z]{4,}(?![A-Za-z])")
STOP = {
    "Miss", "Ms", "Mr", "Mrs", "Ma", "am", "God", "Lord", "He", "She", "It",
    "They", "I", "The", "This", "That", "There", "What", "Why", "How", "Yes",
    "No", "Oh", "Ah", "Damn", "Fuck", "Yeah", "Okay", "Now", "Then", "Maybe",
    "Really", "Careful", "Enough", "Alright", "Sorry", "Please", "Thank",
}


MID_SENTENCE = re.compile(r"[a-z][,;]?\s*$")


def proper_nouns(recs):
    """Names worth enforcing. Three filters, all needed:

    * seen more than once, so a one-off title case word cannot join
    * its lowercase form never appears, which drops But/See/Her/You
    * it sits mid-sentence at least once (right after a lowercase word, no
      sentence terminator between), which drops sentence-initial interjections
      like Honestly/Holy/Ugh/Mmm that pass the first two filters.
    """
    counts, lower, mid = (collections.Counter(), collections.Counter(),
                          collections.Counter())
    for r in recs:
        en = r["en"]
        for w in LATIN_WORD.findall(en):
            (counts if w[0].isupper() and len(w) >= 3 else lower)[
                w if w[0].isupper() else w.lower()] += 1
        for m in re.finditer(r"([A-Z][A-Za-z]{2,})", en):
            if MID_SENTENCE.search(en[: m.start()]):
                mid[m.group(1)] += 1
    return {
        w for w, c in counts.items()
        if c >= 2 and mid.get(w, 0) >= 1 and w.lower() not in lower and w not in STOP
    }


def has(text, name):
    """Word-boundary match that does not let 'Le' fire inside 'Leo'."""
    return re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![A-Za-z])", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--names", default="", help="extra names to enforce")
    ap.add_argument("--report", default="localization/align_report.txt")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    names = proper_nouns(recs) | {n for n in args.names.split() if n}
    hard, warn = [], []
    for r in recs:
        en, zh = r["en"], r.get("zh") or ""
        if not zh:
            continue
        for n in sorted(names):
            in_en = has(en, n)
            if in_en and not has(zh, n):
                hard.append(("MISSING-NAME", r["id"], r["line"], n, en[:60], zh[:60]))
            if has(zh, n) and not in_en:
                warn.append(("EXTRA-NAME", r["id"], r["line"], n, en[:60], zh[:60]))
        # {tags} are markup, not prose - never a translation leak
        for leak in LOWERCASE_LEAK.findall(TAGS.sub(" ", zh)):
            hard.append(("LEAK", r["id"], r["line"], leak, en[:60], zh[:60]))

    lines = ["enforced names: %s" % ", ".join(sorted(names))]
    for kind, rid, line, tok, en, zh in hard:
        lines.append("%s %s (script line %s) [%s]\n    en: %s\n    zh: %s"
                     % (kind, rid, line, tok, en, zh))
    for kind, rid, line, tok, en, zh in warn:
        lines.append("%s %s (script line %s) [%s] (warn only) en: %s"
                     % (kind, rid, line, tok, en))
    lines.append("checked=%d  FAILURES=%d  warnings=%d" % (len(recs), len(hard), len(warn)))
    text = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())

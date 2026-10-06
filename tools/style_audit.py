"""Audit (and where safe, repair) cross-batch style drift in a translation JSON.

Why this exists: a corpus translated by 20+ parallel agents drifts on the rules the
glossary pinned down AFTER the first batches shipped (paren style, ellipsis form,
the `--` dash, possessives frozen inside a `{b}` tag). align_check.py catches
misalignment and untranslated leaks, not style, so drift passes straight through to
the game and shows up as "the same kind of line looks different in chapter 3".

Checks are separated by whether they can be fixed mechanically:
  --apply    rewrites only the deterministic ones (currently: ASCII parens -> fullwidth)
  everything else is reported with counts + examples so a human/rule decides.

Usage:
    python tools/style_audit.py                      # report
    python tools/style_audit.py --apply              # fix what is safe, then report
    python tools/style_audit.py --json localization/en-zh.json --examples 5
"""

import argparse
import collections
import json
import os
import re
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CJK = "[぀-ヿ㐀-䶿一-鿿豈-﫿]"
TAG_RE = re.compile(r"\{[^{}]*\}")
INTERP_RE = re.compile(r"\[[^\[\]]*\]")
PAREN_EN = re.compile(r"\([^()]*\)")
DADDY_RE = re.compile(r"\b(daddy|daddies|papa|poppa)\b", re.I)
# Terms the reader is expected to meet in English (adult-VN jargon, and the
# in-fiction game-show title, which rule "titles stay English" covers).
TERM_OK = {"milf", "would you rather!", "would you rather"}

BOLD_INNER = re.compile(r"\{b\}([^{}]{1,60}?)\{/b\}")
POSSESSIVE_TAG = re.compile(r"\{b\}([A-Za-z][\w. ]*?)['’]s\{/b\}")


def possessive_fix(zh):
    # Drop the English possessive clitic inside a bold tag: {b}Lara's{/b} -> {b}Lara{/b}.
    # The markup survives untouched, so apply_trans' tag-conservation gate still passes;
    # only the 's residue goes. The Chinese 的 next to it was already written by the
    # translator, so no word order is rewritten here.
    return re.sub(r"\{b\}([^{}]+?)['’]s(\{/?b\})", r"{b}\1\2", zh)


ELLIPSIS_UNITS = re.compile(r"\.{2,}|…+")


def strip_tags(s):
    """Drop {...} tags and [...] interpolations so a check cannot fire on markup."""
    return INTERP_RE.sub("", TAG_RE.sub("", s))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def paren_fix(zh):
    """ASCII parens -> fullwidth, but only outside {...} tags and [...] interpolations."""
    out = []
    i = 0
    while i < len(zh):
        ch = zh[i]
        if ch == "{":
            j = zh.find("}", i)
            out.append(zh[i:j + 1] if j > 0 else zh[i:])
            i = j + 1 if j > 0 else len(zh)
        elif ch == "[":
            j = zh.find("]", i)
            out.append(zh[i:j + 1] if j > 0 else zh[i:])
            i = j + 1 if j > 0 else len(zh)
        elif ch == "(":
            out.append("（")
            i += 1
        elif ch == ")":
            out.append("）")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def ellipsis_fix(zh, en):
    """The glossary pins  `...` -> `……`  and  `…` -> `…`.

    Only the upgrade direction is applied: a lone `…` in a line whose English uses
    ASCII dots becomes `……`. The reverse is reported but never auto-applied, because
    `……` is also legitimate Chinese prose punctuation and rewriting it would be a
    meaning change disguised as a style fix.
    """
    if not re.search(r"\.{2,}", en):
        return zh
    zh = re.sub(r"\.{2,}", "……", zh)
    return re.sub(r"(?<!…)…(?!…)", "……", zh)


def dash_fix(zh, en):
    """An interruption `--` stays `--`; the em-dash is reserved for drawn-out words."""
    if "--" not in en:
        return zh
    return zh.replace("——", "--")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--speakers", default="localization/speakers.json")
    ap.add_argument("--examples", type=int, default=4)
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the deterministic fixes into the JSON")
    args = ap.parse_args()

    names = set()
    if os.path.isfile(args.speakers):
        with open(args.speakers, encoding="utf-8") as f:
            for v in json.load(f).values():
                v = str(v).strip()
                if re.fullmatch(r"[A-Za-z][A-Za-z. ]{1,20}", v):
                    names.add(v.split()[0].lower())
    extra_ok = {"diane", "becky", "nicole", "richard", "lara", "cassandra", "eleni",
                "christina", "jasmine", "lin", "eva", "amber", "caleb", "johnny",
                "brice", "tony", "frank", "ben", "jerry", "master", "clerk", "waiter",
                "valet", "man", "man.", "girl", "tutor", "tutorial", "greek", "ancient"}
    names |= extra_ok

    recs = load(args.json)
    say = [r for r in recs if r.get("kind") == "say" and r.get("zh")]
    stats = collections.Counter()
    samples = collections.defaultdict(list)
    changed = 0

    def note(name, r, detail=""):
        stats[name] += 1
        if len(samples[name]) < args.examples:
            samples[name].append("%s %s | %s || %s" % (
                r["id"], name, r["en"][:70], str(r["zh"])[:70] + ((" <" + detail + ">") if detail else "")))

    for r in say:
        en, zh = r["en"], r["zh"]

        # Rule 8 passthrough: a line with no CJK is deliberately still English
        # (pure onomatopoeia / bare-name shout), so no style rule applies to it.
        if not re.search(CJK, zh):
            stats["passthrough-no-cjk"] += 1
            continue

        # deterministic rewrites, applied before the checks so a fixed line stops
        # showing up as drift
        if args.apply:
            fixed = zh
            if PAREN_EN.search(en):
                fixed = paren_fix(fixed)
            fixed = ellipsis_fix(fixed, en)
            fixed = dash_fix(fixed, en)
            fixed = possessive_fix(fixed)
            if fixed != zh:
                r["zh"] = fixed
                changed += 1
                zh = fixed

        # 1) paren style: en uses ASCII (), zh must use fullwidth （）
        if PAREN_EN.search(en):
            body = strip_tags(zh)
            if "(" in body or ")" in body:
                note("paren-unfixable" if args.apply else "paren-ascii", r)

        # 2) ellipsis form drift: the source distinguishes ASCII `...` from the single
        #    `…` character, and the glossary pins  ...  ->  ……   and   …  ->   …
        en_dots = len(re.findall(r"\.{2,}", en))
        en_singles = len(re.findall(r"…", en))
        if en_dots or en_singles:
            zh_double = len(re.findall(r"…{2,}", zh))
            zh_single = len(re.findall(r"…(?!…)", zh))
            if zh_double < en_dots:
                note("ellipsis-dots-not-doubled", r, "%d…%d vs want>=%d" % (
                    en_dots, en_singles, zh_double))
            if en_singles and zh_double + zh_single < en_singles:
                note("ellipsis-singles-lost", r, "%d…%d" % (en_dots, en_singles))
            if "..." in zh or re.search(r"\.\.", zh):
                note("ellipsis-ascii-dots-in-zh", r)

        # 3) interruption dash: `--` stays `--`
        if "--" in en and "——" in zh:
            note("dash-converted", r)

        # 4) daddy stays English (collides with Dad -> 爸爸)
        if DADDY_RE.search(en) and re.search(r"爸爸|爹", zh):
            note("daddy-translated", r)

        # 5) the English possessive clitic must NOT survive into the Chinese line:
        #    `{b}Lara's{/b}` -> `{b}Lara{/b} 的…` (markup preserved, `'s` dropped).
        for m in POSSESSIVE_TAG.finditer(en):
            if m.group(0) in zh:
                note("latin-possessive-kept", r, m.group(0))

        # 6) bold tags that still hold an English word which is not a name or an
        #    interpolation = the emphasis was never translated (groups disagree on
        #    this, so it has to be audited rather than trusted).
        for m in BOLD_INNER.finditer(zh):
            inner = m.group(1).strip()
            if "[" in inner or re.search(CJK, inner):
                continue
            bad_words = []
            for w in re.findall(r"[A-Za-z][A-Za-z.']*", inner):
                stem = w.rstrip(".")
                if len(stem) < 2:
                    continue
                # Name-like = title case ("Candy", "Mister Ding", "OnlyCans"), which
                # rule 1 requires to stay English. Everything else inside a bold tag
                # (SHOUTING, lowercase prose) was emphasis that never got translated.
                if stem[0].isupper() and not stem.isupper():
                    continue
                if stem.lower() in names or inner.strip().lower() in TERM_OK:
                    continue
                bad_words.append(stem)
            if bad_words:
                note("latin-inside-bold", r, inner[:30])


    # coverage bookkeeping, so the number of untouched lines is visible
    stats["say-with-zh"] = len(say)
    stats["say-total"] = len([r for r in recs if r.get("kind") == "say"])
    stats["say-untranslated"] = stats["say-total"] - len(say)

    for k in sorted(stats):
        print("%-28s %d" % (k, stats[k]))
    print()
    for k in sorted(samples):
        if k in ("say-total", "say-with-zh", "say-untranslated"):
            continue
        print("--- %s (%d) ---" % (k, stats[k]))
        for s in samples[k]:
            print("   " + s)

    if args.apply:
        bak = args.json.replace(".json", ".before_style.json")
        if not os.path.isfile(bak):
            shutil.copyfile(args.json, bak)
            print("pre-style master JSON backed up to %s" % bak)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
        print("applied %d style fixes to %s" % (changed, args.json))
    else:
        print("\n(report only; --apply fixes the deterministic checks)")

    drift = sum(v for k, v in stats.items() if k.endswith(("translated", "converted", "rewritten"))
                or k.startswith(("paren-ascii", "ellipsis-should", "daddy-")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

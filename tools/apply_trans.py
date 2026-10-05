"""Merge translator output shards (localization/out_*.json) back into the master JSON.

Pre-checks each pair so a bad shard cannot silently corrupt the build:
  * Ren'Py text tags {i}...{/i} must survive as a matching multiset
  * interpolation [var] must survive unchanged
  * literal \n count must be preserved
  * the result must actually contain CJK and must not be a copy of the English

Usage:
    python tools/apply_trans.py            # merge everything found
    python tools/apply_trans.py --out-glob 'localization/out_*.json'
"""

import argparse
import collections
import glob
import json
import os
import re
import sys

CJK = re.compile(r"[\u4e00-\u9fff]")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TAGS = re.compile(r"\{[^{}]*\}")
INTERP = re.compile(r"\[[^\[\]]*\]")


def check(en, zh):
    problems = []
    if not zh or not zh.strip():
        problems.append("empty")
    # a line made only of proper names / numbers legitimately has no CJK in it
    names_only = not re.search(r"[a-z]{2,}", re.sub(r"\b[A-Z][A-Za-z]*\b", "", en))
    if not CJK.search(zh or "") and not names_only:
        problems.append("no-cjk")
    # moans, onomatopoeia and name-only lines are returned verbatim on purpose -
    # build_tl prints them as one line instead of showing the English twice
    if zh and zh.strip() == en.strip() and not names_only:
        problems.append("identical")
    for pat, label in ((TAGS, "tag"), (INTERP, "interp")):
        a = collections.Counter(pat.findall(en))
        b = collections.Counter(pat.findall(zh or ""))
        if a != b:
            problems.append("%s-mismatch %s!=%s" % (label, sorted(a.items()), sorted(b.items())))
    if en.count("\n") != (zh or "").count("\n"):
        problems.append("newline-count %d!=%d" % (en.count("\n"), (zh or "").count("\n")))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--glob", default="localization/out_*.json")
    ap.add_argument("--report", default="localization/apply_report.txt")
    ap.add_argument("--quarantine", default="localization/rejected")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    by_id = {r["id"]: r for r in recs}
    shards = sorted(glob.glob(args.glob))
    lines, applied, rejected, dup = [], 0, 0, 0
    if not os.path.isdir(args.quarantine):
        os.makedirs(args.quarantine)
    seen = {}
    for sh in shards:
        data = json.load(open(sh, encoding="utf-8"))
        bad = []
        for rid, zh in data.items():
            r = by_id.get(rid)
            if r is None:
                bad.append((rid, "unknown id", zh))
                continue
            if rid in seen:
                dup += 1
                if seen[rid] == zh:
                    continue
                # A later shard may deliberately replace an earlier value: the audit
                # that finds a problem runs after the merge, so the fix has to win.
                # Shards are read in sorted order, so name fixups out_9x.json.
                lines.append("   OVERRIDE %s by %s" % (rid, os.path.basename(sh)))
            seen[rid] = zh
            probs = check(r["en"], zh)
            if probs:
                bad.append((rid, "; ".join(probs), zh))
                continue
            r["zh"] = zh
            r["zh_from"] = "agent"
            applied += 1
        lines.append("%s: %d entries, %d rejected" % (os.path.basename(sh), len(data), len(bad)))
        if bad:
            rejected += len(bad)
            with open(os.path.join(args.quarantine, os.path.basename(sh)), "w", encoding="utf-8") as f:
                json.dump({b[0]: b[2] for b in bad}, f, ensure_ascii=False, indent=1)
            for rid, why, _zh in bad:
                lines.append("   REJECT %s: %s" % (rid, why))

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    todo = sum(1 for r in recs if r["kind"] == "say" and not r.get("zh"))
    lines.append("applied=%d rejected=%d duplicate=%d remaining untranslated say=%d" % (applied, rejected, dup, todo))
    text = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())

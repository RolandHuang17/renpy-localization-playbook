"""Split untranslated records into large ordered groups for batch translation.

Grouping keeps one source file's lines together and in line order, because a
translator must read them as a continuous scene (pronouns / tense / address terms).

Usage:
    python tools/dump_groups.py --json localization/en-zh.json --size 420
"""

import argparse
import json
import os
import shutil
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--outdir", default="localization/groups")
    ap.add_argument("--size", type=int, default=420)
    ap.add_argument("--chars", type=int, default=26000, help="soft cap per group")
    ap.add_argument("--kinds", default="say")
    ap.add_argument("--only-untranslated", action="store_true", default=True)
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    kinds = tuple(k.strip() for k in args.kinds.split(","))
    todo = [r for r in recs if r["kind"] in kinds and not r.get("zh")]
    todo.sort(key=lambda r: (r["file"], r["line"]))

    if os.path.isdir(args.outdir):
        shutil.rmtree(args.outdir)
    os.makedirs(args.outdir, exist_ok=True)

    group, groups, nchars = [], [], 0
    for r in todo:
        item = {
            "id": r["id"],
            "who": r.get("who") or "",
            "file": r["file"].split("/")[-1],
            "en": r["en"],
        }
        if group and (
            len(group) >= args.size or nchars + len(r["en"]) > args.chars
        ):
            groups.append(group)
            group, nchars = [], 0
        group.append(item)
        nchars += len(r["en"])
    if group:
        groups.append(group)

    for i, g in enumerate(groups, 1):
        with open(os.path.join(args.outdir, "group_%02d.json" % i), "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, indent=0)
    print("untranslated=%d -> %d groups (max %d entries / %d chars)" % (len(todo), len(groups), args.size, args.chars))
    print("wrote %s/group_01.json .. group_%02d.json" % (args.outdir, len(groups)))


if __name__ == "__main__":
    main()

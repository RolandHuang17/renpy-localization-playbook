"""One-click rollback: delete only the files we generated (tracked in a manifest).

Never modifies *.rpa, renpy/, game/saves/ or any original game file, so deleting the
manifest-listed paths fully restores the distribution.

Usage:
    python tools/uninstall.py            # delete generated .rpy/.rpyc
    python tools/uninstall.py --dry-run
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="localization/generated_files.txt")
    ap.add_argument("--gamedir", default="game")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = set()
    if os.path.exists(args.manifest):
        for line in open(args.manifest, encoding="utf-8"):
            line = line.strip()
            if line:
                targets.add(line)
    # sweep the language dir as well, in case the manifest is stale. Everything
    # under tl/<lang>/ is ours by construction - .rpy, .rpyc AND the copied font.
    tl_dir = os.path.join(args.gamedir, "tl", args.lang)
    for root, dirs, files in os.walk(tl_dir):
        for fn in files:
            targets.add(os.path.join(root, fn))

    removed = 0
    for p in sorted(targets):
        if os.path.exists(p):
            print(("would delete " if args.dry_run else "deleted ") + p)
            if not args.dry_run:
                os.remove(p)
            removed += 1
    if not args.dry_run:
        for root, dirs, files in os.walk(tl_dir, topdown=False):
            if os.path.isdir(root) and not os.listdir(root):
                try:
                    os.rmdir(root)
                except OSError:
                    pass
        if os.path.isdir(tl_dir) and not os.listdir(tl_dir):
            os.rmdir(tl_dir)
    print("%s %d files" % ("would remove" if args.dry_run else "removed", removed))


if __name__ == "__main__":
    main()

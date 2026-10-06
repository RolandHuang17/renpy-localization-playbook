"""Answer "which file does the engine actually load for this script name?".

Emulates the engine's real resolution rules so a mod/localization overlay can be
audited BEFORE launching the game. Every rule below was read off the engine source
(`renpy/loader.py`, `renpy/script.py`, `renpy/main.py`) and re-confirmed against a
live distribution that ships both loose files and archives.

The four rules:

1. Dedupe is by FULL relative path name (extension included), disk first, then
   archives. So a loose `update4.rpyc` shadows an archived `update4.rpyc`, but a
   loose `update4.rpy` does NOT shadow an archived `update4.rpyc` - those are two
   different names, so the same logical script ends up registered twice (once from
   disk, once from an archive) and the engine loads both. On a Python 3 engine the
   duplicate also makes `script_files.sort()` compare (name, str) against (name,
   None), which raises.
2. Archives are collected with `sorted(os.listdir)` then `.reverse()`, so the
   alphabetically LAST archive is searched FIRST. `zzscripts.rpa` beats `scripts.rpa`
   for the same entry - which is how official "update packs" work.
3. `.rpy` entries inside an archive are never loaded as scripts (`dir is None` ->
   `continue`); they are dead weight. Only `.rpyc`/`.rpymc` count there.
4. When a loose `.rpy` and a loose `.rpyc` share a name, the engine compares the md5
   of the `.rpy` against the LAST 16 BYTES of the `.rpyc`. Equal -> load the `.rpyc`.
   Different -> compile the `.rpy` and OVERWRITE that `.rpyc` in place. Modification
   times are never consulted. The hash input itself is version dependent: 8.x hashes
   the raw bytes (`script.py:737`), 7.4 hashes the text with newlines normalized
   (`open(fn, "rU")` + encode). This tool computes both and says which one matched.

Rule 4 is the one that quietly breaks "delete my files to revert": reusing a name the
game already ships means the first launch destroys the original compiled bytes.

Usage:
    python tools/override_audit.py --game game
    python tools/override_audit.py --game game --overlay /path/to/modpack --mark cc
"""

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R

SCRIPT_EXT = (".rpy", ".rpyc", ".rpym", ".rpymc")


def rpy_digests(path):
    """The digests the engine may compare against, keyed by which rule it uses."""
    with open(path, "rb") as f:
        raw = f.read()
    out = {"raw bytes, 8.x rule": hashlib.md5(raw).hexdigest()}
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    out["normalized, 7.x rule"] = hashlib.md5(text.encode("utf-8")).hexdigest()
    return out


def rpyc_digest(path):
    """The 16-byte md5 trailer the engine compares against."""
    try:
        with open(path, "rb") as f:
            f.seek(-hashlib.md5().digest_size, 2)
            return f.read().hex()
    except Exception:
        return None


def walk_disk(base):
    """Every file under `base`, as the archive-relative name the engine keys on."""
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("cache", "saves", "__pycache__")]
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base).replace("\\", "/")
            if rel.startswith("cache/") or rel.startswith("saves/"):
                continue
            out.append((rel, full))
    return out


def archive_order(game_dir):
    """config.archives: sorted by file name, then reversed -> searched in that order."""
    names = [fn for fn in os.listdir(game_dir)
             if os.path.splitext(fn)[1].lower() == ".rpa"]
    return sorted(names)[::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game", help="the game directory the engine opens")
    ap.add_argument("--overlay", action="append", default=[],
                    help="a directory whose files are about to be copied into --game "
                         "(repeatable); audits the state AFTER installing it")
    ap.add_argument("--mark", default="",
                    help="prefix (e.g. cc) selecting which of YOUR files the per-script "
                         "table lists; the problem lists always print")
    ap.add_argument("--show-all", action="store_true",
                    help="print every logical script and every capped list")
    args = ap.parse_args()

    game_dir = args.game
    if not os.path.isdir(game_dir):
        raise SystemExit("no such game dir: %s" % game_dir)

    # --- disk files, with --overlay dirs simulated as if installed --------------------
    disk = {}          # rel name -> (origin, absolute path); --game wins ties
    for tag, base in [("game", game_dir)] + [("overlay", o) for o in args.overlay]:
        for rel, full in walk_disk(base):
            if rel in disk:
                continue
            disk[rel] = (tag, os.path.abspath(full).replace("\\", "/"))

    # --- the engine's dedupe: by FULL relative name, disk first -----------------------
    # loader.py add(): `if fn in seen: return` -- `fn` still carries the extension, so
    # a loose `x.rpy` does NOT claim the archived `x.rpyc`.
    seen = {}
    dropped = []
    order = []
    for rel in sorted(disk):
        seen[rel] = disk[rel][0]
        order.append((disk[rel][0], rel, disk[rel][1]))

    arch_names = archive_order(game_dir)
    for an in arch_names:
        try:
            a = R.RPA3(os.path.join(game_dir, an))
        except Exception as e:
            print("WARN cannot index %s: %s" % (an, e))
            continue
        for rel in sorted(a.names()):
            if rel in seen:
                dropped.append((rel, seen[rel], "archive:" + an))
                continue
            seen[rel] = "archive:" + an
            order.append(("archive:" + an, rel, None))

    # --- register logical script names, exactly like script.py -----------------------
    scripts = {}
    dead_archive_rpy = []
    for origin, rel, path in order:
        base, ext = os.path.splitext(rel)
        if ext not in SCRIPT_EXT:
            continue
        if origin.startswith("archive:") and ext in (".rpy", ".rpym"):
            dead_archive_rpy.append((origin, rel))
            continue
        scripts.setdefault(base, []).append((origin, rel, path))

    pair = {}
    recompile = []     # loose .rpy whose .rpyc disagrees -> that .rpyc gets overwritten
    duplicate = []     # same logical name present on disk AND in an archive

    for logical, cands in sorted(scripts.items()):
        from_disk = [c for c in cands if not c[0].startswith("archive:")]
        from_arch = [c for c in cands if c[0].startswith("archive:")]
        if from_disk and from_arch:
            duplicate.append((logical,
                              [c[1] for c in from_disk],
                              [c[0] + "/" + c[1] for c in from_arch]))
        rpy = next((c for c in from_disk if c[1].endswith(".rpy")), None)
        rpyc = next((c for c in from_disk if c[1].endswith(".rpyc")), None)
        if rpy and rpyc:
            dig, tr = rpy_digests(rpy[2]), rpyc_digest(rpyc[2])
            hit = [k for k, v in dig.items() if v == tr]
            if hit:
                pair[logical] = (rpyc[0] + " " + rpyc[1],
                                 "loads compiled, source agrees (%s)" % hit[0])
            else:
                pair[logical] = (rpy[0] + " " + rpy[1],
                                 "digest DISAGREES -> compiles .rpy, overwrites .rpyc")
                recompile.append((logical, rpy[1], rpyc[1], tr, dig))
        elif rpyc:
            pair[logical] = (rpyc[0] + " " + rpyc[1], "compiled only")
        elif rpy:
            pair[logical] = (rpy[0] + " " + rpy[1], "source only -> compiled at first launch")
        elif from_arch:
            pair[logical] = (from_arch[0][0] + " " + from_arch[0][1], "archive .rpyc")
        else:
            pair[logical] = ("?", "module file")

    shadowed_scripts = [d for d in dropped if os.path.splitext(d[0])[1] in SCRIPT_EXT]

    # --- report ----------------------------------------------------------------------
    print("game dir        : %s" % os.path.abspath(game_dir))
    extra = (", ... (%d more)" % (len(arch_names) - 5)) if len(arch_names) > 5 else ""
    print("archives searched in this order (first hit claims the name): %s%s"
          % (", ".join(arch_names[:5]), extra))
    print("logical scripts : %d" % len(scripts))
    if args.overlay:
        print("overlay dirs    : %s  (simulated as if copied into the game dir)"
              % ", ".join(args.overlay))

    def block(title, items, fmt, empty, cap=None):
        print("\n=== %s: %d ===" % (title, len(items)))
        if not items:
            print("  " + empty)
        shown = items if (cap is None or args.show_all) else items[:cap]
        for it in shown:
            print(fmt(it))
        if len(items) > len(shown):
            print("  ... %d more (use --show-all)" % (len(items) - len(shown)))

    block("PROBLEM script entries present but NEVER read (name already claimed elsewhere)",
          shadowed_scripts,
          lambda t: "  %-52s claimed by %-8s skipped: %s" % (t[0], t[1], t[2]),
          "none - every archive script name is reachable")

    block("PROBLEM same logical script on disk AND in an archive (the engine registers BOTH)",
          duplicate,
          lambda t: "  %-30s disk=%s  archive=%s" % (t[0], ",".join(t[1]), ",".join(t[2])),
          "none")

    block("PROBLEM loose .rpy whose same-named .rpyc is about to be OVERWRITTEN in place",
          recompile,
          lambda t: "  %-30s %s vs %s (trailer %s) -> back up BOTH before editing" % (
              t[0], t[1], t[2], str(t[3])[:8]),
          "none - no loose source/compiled pair disagrees")

    block("INFO .rpy entries inside archives (dead: never loaded as script)",
          dead_archive_rpy,
          lambda t: "  %-30s %s" % (t[0], t[1]), "none", cap=6)

    if args.show_all or args.mark:
        print("\n=== per-script resolution ===")
        for logical, (winner, note) in sorted(pair.items()):
            if args.mark and not logical.startswith(args.mark):
                continue
            print("  %-30s %-30s %s" % (logical, winner, note))

    print("\naudit verdict   : never-read=%d  disk+archive duplicates=%d  to-overwrite=%d  "
          "over %d logical scripts" % (len(shadowed_scripts), len(duplicate),
                                       len(recompile), len(scripts)))
    print("rule recap      : disk beats archive BY FULL NAME (extension included); the "
          "last-named archive beats earlier ones; .rpy vs .rpyc is md5, never mtime.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

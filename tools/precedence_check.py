"""Coverage gate: does the translation table contain every say string the ENGINE will
actually load?

The resolution model is the one documented in playbook section 18 (read off
renpy/main.py, renpy/loader.py, renpy/script.py; re-confirmed on 7.4.10):

  1. dedupe is by FULL name including extension, disk first, then archives -- a loose
     `x.rpyc` shadows the archived `x.rpyc`, but a loose `x.rpy` does NOT shadow an
     archived `x.rpyc` (different names, both registered);
  2. archives are searched in reverse-alphabetical order (renpy/main.py builds
     config.archives from sorted(os.listdir) then .reverse()), so an "zz" overlay
     archive (zzscripts.rpa -- the usual mod / official update-pack name) wins over
     scripts.rpa for the same entry;
  3. `.rpy` entries INSIDE an archive are never loaded as scripts
     (script.py `if dir is None: continue`) -- only .rpyc counts there;
  4. a loose `.rpy` next to a loose `.rpyc` of the same stem is decided by md5: a
     matching digest means the .rpyc loads (and "delete my files to revert" no longer
     holds -- section 18.2, and tools/override_audit.py).

Why this gate exists: a distribution carrying an overlay archive holds TWO copies of the
same script with DIFFERENT dialogue text (mods inject their own interpolation tokens).
Extracting from whichever archive os.walk() happens to return first puts the loser's
strings in the table and leaves the winner's English on screen -- silently, because
everything else still validates.

Usage (run from the game root, like every other tool here):
    python tools/precedence_check.py --table localization/en-zh.json [--kinds say]
"""
import argparse, collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R  # noqa: E402
import override_audit as OA  # noqa: E402

DISK = "DISK"
CHILD_FIELDS = ("children", "block", "statements", "true", "false", "body", "items",
                "screen", "next", "child", "second", "code")
SAY_SUFFIXES = (".Say", ".TranslateSay")
RPY_SPEAK = re.compile(r'^\s*(?:choice\s+)?([a-z][\w.]{0,12})\s+"([^"]+)"', re.M)


def winners(game_dir):
    """loadable script name -> (source path or DISK, entry name); plus shadow count."""
    order = OA.archive_order(game_dir)
    arcs = {}
    for a in order:
        try:
            arcs[a] = R.RPA3(os.path.join(game_dir, a))
        except Exception:
            pass
    disk = dict(OA.walk_disk(game_dir))
    win = {}
    for rel in sorted(disk):
        if not (rel.endswith(".rpy") or rel.endswith(".rpyc")):
            continue
        # our OWN overlay lives in game/tl/<lang>/ and quotes the English inside old/new
        # lines -- counting it as source is the section 3 trap in reverse: it turns a real
        # coverage gap of ~260 strings into a screaming 13,000.
        if rel.startswith("tl/"):
            continue
        win[rel] = (DISK, rel)
    for a in order:
        if a not in arcs:
            continue
        for n in arcs[a].names():
            if n.endswith(".rpyc") and n not in win:
                win[n] = (os.path.join(game_dir, a), n)
    shadowed = 0
    for n in list(win):
        src, entry = win[n]
        if src != DISK or not n.endswith(".rpy"):
            continue
        twin = n[:-1]
        if twin not in disk:
            continue
        try:
            h_rpy, _ = OA.rpy_digests(os.path.join(game_dir, n))
            h_rpyc = OA.rpyc_digest(os.path.join(game_dir, twin))
        except Exception:
            continue
        if h_rpy == h_rpyc:
            del win[n]
            shadowed += 1
    for a in arcs.values():
        a.close()
    return win, shadowed


def read_blob(game_dir, src, entry):
    if src == DISK:
        with open(os.path.join(game_dir, entry), "rb") as f:
            return f.read()
    arc = R.RPA3(src)
    try:
        return arc.read(entry)
    finally:
        arc.close()


def say_strings(root, out):
    """Iterative -- 7.x hands back one flat statement list thousands deep."""
    stack = [root]
    seen = set()
    guard = 0
    while stack:
        node = stack.pop()
        guard += 1
        if guard > 4000000:
            break
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        if R.node_type(node).endswith(SAY_SUFFIXES):
            w = getattr(node, "what", None)
            if isinstance(w, str):
                out.append(w)
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, (list, tuple, set)):
            stack.extend(node)
        else:
            for fld in CHILD_FIELDS:
                v = getattr(node, fld, None)
                if v is not None:
                    stack.append(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game")
    ap.add_argument("--table", default="localization/en-zh.json")
    ap.add_argument("--kinds", default="say")
    ap.add_argument("--report", default="localization/precedence_report.txt")
    ap.add_argument("--exclude", default="",
                    help="comma list of substrings; scripts matching are NOT counted "
                         "(use it for a third-party mod's own UI files -- cheat panels and "
                         "hand-written gallery screens are UI text, and section 0.5 says UI stays English)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    kinds = set(k.strip() for k in args.kinds.split(","))
    d = json.load(open(args.table, encoding="utf-8"))
    recs = d["records"] if isinstance(d, dict) and "records" in d else d
    if isinstance(recs, dict):
        recs = list(recs.values())
    table = set(r["en"] for r in recs if r.get("kind") in kinds)
    print("table %s strings: %d" % (",".join(sorted(kinds)), len(table)))

    win, shadowed = winners(args.game)
    excl = [e.strip() for e in args.exclude.split(",") if e.strip()]
    if excl:
        before = len(win)
        win = {k: v for k, v in win.items() if not any(e in k for e in excl)}
        print("excluded by --exclude: %d scripts" % (before - len(win)))
    per_source = collections.Counter(
        (os.path.basename(win[n][0]) if win[n][0] != DISK else DISK) for n in win)
    by_ext = collections.Counter(n[-5:] for n in win)
    print("loadable scripts   : %d  (loose .rpy shadowed by its own .rpyc: %d)"
          % (len(win), shadowed))
    print("by ext             : %s" % dict(by_ext))
    print("winners by source  : %s" % per_source.most_common(8))

    total = 0
    missing = []
    unparsed = []
    for n in sorted(win):
        src, entry = win[n]
        blob = read_blob(args.game, src, entry)
        found = []
        if entry.endswith(".rpy"):
            # no compiled twin and not inside an archive -> the engine parses this source
            found = [m.group(2) for m in RPY_SPEAK.finditer(blob.decode("utf-8", "replace"))]
        else:
            obj = R.load_script(blob)
            if obj is None:
                unparsed.append(n)
                continue
            say_strings(obj, found)
        for s in found:
            total += 1
            if s not in table:
                missing.append((n, s))

    uniq = collections.Counter(s for _, s in missing)
    lines = ["loadable scripts             : %d" % len(win),
             "unparsed .rpyc winners       : %d  %s" % (len(unparsed), unparsed[:8]),
             "say strings in winners       : %d" % total,
             "say strings NOT in table     : %d unique / %d occurrences"
             % (len(uniq), len(missing)),
             "missing concentrated in      : %s"
             % collections.Counter(n for n, _ in missing).most_common(10),
             ""]
    for s, c in uniq.most_common(60):
        lines.append("%4d  %s" % (c, s[:160]))
    open(args.report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))
    print("wrote " + args.report)
    if uniq:
        print("GAP: the engine loads these strings with no table entry -> English stays on screen.")
        print("     fix: re-extract honoring archive precedence, or add the missing strings.")
        sys.exit(1)


main()

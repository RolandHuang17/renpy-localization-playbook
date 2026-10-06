"""Enumerate scene labels from the compiled AST and say which ones are safe to
enter cold, so a bookmark list can be built without playing the whole game.

Why this exists: Ren'Py's `Replay(label)` (renpy/common/00action_other.rpy ->
renpy/game.py:call_replay) gives a clean store, per-scene variable seeding and a
full state restore on exit - exactly the semantics a bookmark needs. The catch is
that a scene label must *stop* at its own boundary. Devs who bothered with the
gallery write `if _in_replay:` at the head (re-seed names) and
`if _in_replay: return` (or `$ renpy.end_replay()`) at the tail (don't fall through
into the next 600 lines).
Most labels have neither, so entering them cold plays on into unrelated story.

This tool reports, per label, the facts that decide that:

  head_guard / tail_guard   does the dev's own `_in_replay` scaffolding exist
  tail_jump                 the last jump in range and whether it leaves the range
  escapes                   jump/call targets in range that land outside it
  speakers, say/menu counts  what the scene is made of
  seed_lines                the dev's own `if _in_replay:` fix-ups (what state a
                          cold entry actually needs)
  exit_ramps                `if _in_replay: jump <trunk label>` - the dev's own way
                          of dropping a replayed scene back onto the main path

Nothing here guesses whether a scene is on-route; that is `bookmark_rules.json`
plus a content pass. Output is localization/scenes.json (metadata) and, with
--dump-candidates, batched scene texts for classification.

Usage:
    python tools/scan_bookmarks.py --game game --out localization/scenes.json
    python tools/scan_bookmarks.py --dump-candidates localization/bookmark_groups \
        --include "submissive|dominant|bjj|choke|triangle|on_top|wins|training" \
        --exclude "kidnap|arrest|escape|police|rescue"
"""

import argparse
import collections
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R

LABEL_T = "renpy.ast.Label"
SAY_T = ("renpy.ast.Say", "renpy.ast.TranslateSay")
MENU_T = ("renpy.ast.Menu",)
JUMP_T = ("renpy.ast.Jump",)
CALL_T = ("renpy.ast.Call",)
IF_T = ("renpy.ast.If",)
RETURN_T = ("renpy.ast.Return",)
PY_T = ("renpy.ast.Python",)
SKIP_DIRS = ("tl", "cache", "saves", "lib", "images", "audio", "movies", "gui")


def meta(node):
    d = getattr(node, "__dict__", {}) or {}
    fn = d.get("filename") if isinstance(d.get("filename"), str) else None
    ln = d.get("linenumber") if isinstance(d.get("linenumber"), int) else 0
    return fn, ln


def block_of(node):
    """The label's own statement list, if the stub kept it."""
    d = getattr(node, "__dict__", {}) or {}
    for key in ("block", "children", "statements"):
        v = d.get(key)
        if isinstance(v, list) and v:
            return v
    return []


def if_references_in_replay(node):
    """Does this If node test `_in_replay`?

    8.0.3 `renpy.ast.If` stores its branches as `entries` = [(condition, block), ...]
    - there is no `.condition` / `.true` - and the condition is a PyExpr whose source
    may only survive in the .rpy (playbook 2). So probe `entries` first, then any
    string reachable from the node, and treat "unknown" as False: the .rpy text scan
    in replay_guards() is the authoritative detection, this is only the AST-side hint.
    """
    d = getattr(node, "__dict__", {}) or {}
    for v in d.values():
        pairs = v if isinstance(v, list) else [v]
        for item in pairs:
            cand = item[0] if isinstance(item, tuple) and item else item
            for layer in (cand, getattr(cand, "_reduce_args", None)):
                seq = layer if isinstance(layer, (list, tuple)) else [layer]
                for x in seq:
                    if isinstance(x, str) and "_in_replay" in x:
                        return True
    src = R.pycode_source(getattr(node, "condition", None)) if hasattr(R, "pycode_source") else None
    return isinstance(src, str) and "_in_replay" in src


REPLAY_IF_RE = re.compile(r"^(\s*)if\s+_in_replay\s*:")
GUARD_SITES = set()   # (file, line) attributed by replay_guards


def replay_guards(text_lines, start, stop):
    """head/tail `_in_replay` guards, read off the loose .rpy source.

    Classify by what the guard block *does*, not where it sits. Three idioms exist in
    the wild and each means something different:

      `return` / `$ renpy.end_replay()`   the tail stop - the scene ends cleanly
      `$ var = persistent.x`              the dev re-seeds state a cold entry loses
      `jump <label>`                      an exit ramp back onto the main path

    The last two used to fall into the same bucket as "unknown", which under-reported
    `tail_guard` and threw away the ramp target. Position is unreliable anyway - some
    labels open with `$ renpy.dynamic(...)` before their guard.
    """
    head = tail = False
    seeds = []
    ramps = []
    body = list(text_lines[start:min(stop, start + 4000)])

    for idx, line in enumerate(body):
        m = REPLAY_IF_RE.match(line)
        if not m:
            continue
        GUARD_SITES.add((id(text_lines), start + idx + 1))
        indent = len(m.group(1))
        block = []
        for nxt in body[idx + 1:]:
            if not nxt.strip():
                continue
            if len(nxt) - len(nxt.lstrip()) <= indent:
                break
            block.append(nxt)
        stripped = [b.strip() for b in block]
        stops = [s for s in stripped
                 if re.match(r"^(return\b|(?:\$\s*)?renpy\.end_replay\(\s*\))", s)]
        jump_targets = [re.match(r"^(?:jump|call)\s+(?:expression\s+)?([A-Za-z_]\w*)", s)
                        for s in stripped]
        ramps_here = [(start + idx + 1, mt.group(1)) for mt in jump_targets if mt]
        ramps += ramps_here
        seed_lines = [s for s in stripped if s.startswith("$") and "end_replay" not in s]
        if stops:
            tail = True
        if seed_lines:
            head = True
            seeds += [s[:90] for s in seed_lines][:10]
        if not (stops or ramps_here or seed_lines):
            seeds.append("(mid-scene _in_replay branch at line %d)" % (start + idx + 1))
    return head, tail, seeds, ramps



def block_has_return(block):
    for n in block or []:
        if R.node_type(n) in RETURN_T:
            return True
        for g in R.iter_nodes(n):
            if R.node_type(g) in RETURN_T:
                return True
    return False


def collect(path):
    """All labels in one .rpyc, in file order, with their range and stats."""
    loaded = R.load_script(open(path, "rb").read())
    if not loaded:
        return []
    _, stmts = loaded
    nodes = list(R.iter_nodes(stmts))

    labels = []
    for n in nodes:
        if R.node_type(n) != LABEL_T:
            continue
        name = (getattr(n, "__dict__", {}) or {}).get("name")
        fn, ln = meta(n)
        if isinstance(name, str) and isinstance(ln, int):
            labels.append((name, fn, ln, n))
    labels.sort(key=lambda t: (t[1] or "", t[2]))

    # Ren'Py 7.x hands back a FLATTENED statement list: every `Label.block` is empty
    # and the statements live next to their label in linear order. Rebuild each
    # label's body by slicing that order, or every per-scene stat reads as zero and
    # the report looks like "a game with no dialogue".
    # Ren'Py 7.x hands back a FLATTENED statement list: `Label.block` is empty and the
    # statements sit next to their label in linear order. Rebuild those bodies by
    # slicing the order, or every per-scene stat reads as zero and the report looks
    # like "a game with no dialogue". Labels that do carry a block (8.x) are untouched.
    if labels and not all(getattr(n, "block", None) for _a, _b, _c, n in labels):
        pos = {id(n): i for i, n in enumerate(nodes)}
        label_pos = sorted(pos[id(n)] for _a, _b, _c, n in labels)
        rebuilt = []
        for name, fn, ln, node in labels:
            if getattr(node, "block", None):
                rebuilt.append((name, fn, ln, node))
                continue
            here = pos[id(node)]
            later = [p for p in label_pos if p > here]
            stop = later[0] if later else len(nodes)
            holder = R.Stub()
            holder.children = nodes[here + 1:stop]
            rebuilt.append((name, fn, ln, holder))
        labels = rebuilt

    out = []
    for i, (name, fn, ln, node) in enumerate(labels):
        nxt = None
        if i + 1 < len(labels) and labels[i + 1][1] == fn:
            nxt = labels[i + 1][2]
        out.append({"label": name, "file": fn, "line": ln,
                    "range_end": nxt if nxt else (1 << 30), "node": node})
    return out


def in_range(rec, other_line, other_file):
    return other_file == rec["file"] and rec["line"] <= other_line < rec["range_end"]


def analyse(rec, all_label_names, srclines):
    node = rec["node"]
    body = list(R.iter_nodes(node))

    speakers = collections.Counter()
    chars = menus = 0
    jumps = []          # (line, target) in file order, so the last one is the tail

    # rec["line"] is the `label foo:` statement's 1-based line; splitlines() index
    # rec["line"] is therefore the first line of its body.
    head_guard, tail_guard, seed_lines, exit_ramps = replay_guards(
        srclines, rec["line"], (rec["range_end"] or len(srclines)) - 1)

    for g in body:
        t = R.node_type(g)
        gfn, gl = meta(g)
        if t in SAY_T:
            what = (getattr(g, "__dict__", {}) or {}).get("what")
            if isinstance(what, str):
                chars += len(what)
                who = (getattr(g, "__dict__", {}) or {}).get("who")
                if isinstance(who, str):
                    speakers[who] += 1
                elif who is None:
                    speakers["(narration)"] += 1
                else:
                    src = R.pycode_source(who) if hasattr(R, "pycode_source") else None
                    speakers[src.strip() if isinstance(src, str) else R.node_type(who)] += 1
        elif t in MENU_T:
            menus += 1
        elif t in JUMP_T:
            tgt = (getattr(g, "__dict__", {}) or {}).get("target")
            if isinstance(tgt, str):
                jumps.append((gl, tgt))

    tail_jump = {"target": jumps[-1][1], "at": jumps[-1][0]} if jumps else None
    # A mid-scene detour is any out-of-range jump that is not the fall-through tail.
    escapes = []
    for gl, tgt in jumps[:-1] if jumps else []:
        tl = tgt_lines.get(tgt, -1)
        if tl < rec["line"] or tl >= rec["range_end"]:
            escapes.append({"target": tgt, "at": gl})

    return {
        "label": rec["label"],
        "file": rec["file"],
        "line": rec["line"],
        "range_end": rec["range_end"],
        "head_guard": head_guard,
        "tail_guard": tail_guard,
        "safe_cold_entry": head_guard and tail_guard,
        "tail_jump": tail_jump,
        "escapes": escapes[:12],
        "escape_count": len(escapes),
        "speakers": dict(speakers.most_common(12)),
        "say_chars": chars,
        "menus": menus,
        "seed_lines": seed_lines[:8],
        "exit_ramps": [{"at": a, "target": t} for a, t in exit_ramps][:8],
    }


tgt_lines = {}
SRC_CACHE = {}


GAME_DIR = "game"   # set from --game; guard text must be resolved against it, not cwd


def resolve_src(path):
    """The engine records `game/foo.rpy`; that is relative to *its* game dir, not ours.

    Resolving it against the current directory silently reads the wrong game (or
    nothing at all), and guard detection then reports "0 sites" as a clean result.
    """
    cands = []
    if path.startswith("game/"):
        cands.append(os.path.join(GAME_DIR, path[5:]))
    cands.append(os.path.join(GAME_DIR, path))
    cands.append(path)          # last: cwd-relative can name a *different* game
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def source_lines(path):
    """The loose .rpy the .rpyc was compiled from (guard detection reads text)."""
    if path not in SRC_CACHE:
        real = resolve_src(path)
        try:
            SRC_CACHE[path] = (open(real, encoding="utf-8-sig", errors="replace")
                               .read().splitlines() if real else [])
        except OSError:
            SRC_CACHE[path] = []
    return SRC_CACHE[path]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="localization/scenes.json")
    ap.add_argument("--report", default="localization/scenes_report.txt")
    ap.add_argument("--dump-candidates", default="", help="write per-scene text batches here")
    ap.add_argument("--include", default="", help="regex a label must match to become a candidate")
    ap.add_argument("--exclude", default="", help="regex a label must NOT match")
    ap.add_argument("--min-chars", type=int, default=400, help="candidate floor: dialogue size")
    ap.add_argument("--per-group", type=int, default=6, help="candidates per classification batch")
    ap.add_argument("--text-chars", type=int, default=9000, help="dialogue budget per candidate")
    args = ap.parse_args()

    global GAME_DIR
    GAME_DIR = args.game

    rpyc = []
    for root, dirs, files in os.walk(args.game):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for fn in sorted(files):
            if fn.endswith(".rpyc"):
                rpyc.append(os.path.join(root, fn))

    global tgt_lines
    recs, names = [], set()
    label_pos = {}
    for path in sorted(rpyc):
        try:
            found = collect(path)
        except Exception as exc:
            print("  !! %s: %r" % (path, exc))
            continue
        for r in found:
            names.add(r["label"])
            tgt_lines.setdefault(r["label"], r["line"])
            label_pos[r["label"]] = (r["file"], r["line"])
        recs.extend(found)

    for r in recs:
        names.add(r["label"])
    scenes = [analyse(r, names, source_lines(r["file"])) for r in recs]

    if rpyc and not scenes:
        raise SystemExit(
            "read %d .rpyc file(s) and found 0 labels. That is not a clean result: the "
            "reader returned None for every file (old .rpyc format, a packed engine, or "
            "a wrong --game). Fix the reader before trusting any count below." % len(rpyc))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=1)

    hard = [s for s in scenes if s["safe_cold_entry"]]
    leaky = [s for s in scenes if s["say_chars"] >= args.min_chars and not s["tail_guard"]]
    lines = [
        "mode              : .rpyc AST label enumeration (engine-loaded truth)",
        "files scanned     : %d" % len(rpyc),
        "labels total      : %d" % len(scenes),
        "with both guards  : %d  (safe to enter cold, no stop-guard needed)" % len(hard),
        "head-only         : %d" % sum(1 for s in scenes if s["head_guard"] and not s["tail_guard"]),
        "dialogue-bearing  : %d (>= %d chars)" % (sum(1 for s in scenes if s["say_chars"] >= args.min_chars), args.min_chars),
        "  ... and leaky   : %d  (no tail guard -> falls through into later story)" % len(leaky),
        "scenes w/ escapes : %d (jump/call out of their own range)" % sum(1 for s in scenes if s["escape_count"]),
        "written           : %s" % args.out,
    ]

    if args.dump_candidates:
        inc = re.compile(args.include, re.I) if args.include else None
        exc = re.compile(args.exclude, re.I) if args.exclude else None
        cand = [s for s in scenes
                if s["say_chars"] >= args.min_chars
                and (inc is None or inc.search(s["label"]))
                and not (exc and exc.search(s["label"]))]
        cand.sort(key=lambda s: (s["file"], s["line"]))
        texts = scene_texts(args.game, cand, label_pos)
        os.makedirs(args.dump_candidates, exist_ok=True)
        for old in os.listdir(args.dump_candidates):
            os.remove(os.path.join(args.dump_candidates, old))
        for gi in range(0, len(cand), args.per_group):
            chunk = cand[gi:gi + args.per_group]
            batch = []
            for s in chunk:
                batch.append({
                    "label": s["label"], "file": s["file"], "line": s["line"],
                    "safe_cold_entry": s["safe_cold_entry"], "tail_jump": s["tail_jump"],
                    "escape_count": s["escape_count"], "speakers": s["speakers"],
                    "menus": s["menus"], "text": texts.get(s["label"], "")[:args.text_chars],
                })
            n = gi // args.per_group + 1
            with open(os.path.join(args.dump_candidates, "group_%02d.json" % n), "w",
                      encoding="utf-8") as f:
                json.dump(batch, f, ensure_ascii=False, indent=1)
        lines.append("candidates        : %d -> %s/group_NN.json (%d batches)"
                     % (len(cand), args.dump_candidates,
                        (len(cand) + args.per_group - 1) // args.per_group))
        with open(args.out.replace(".json", ".candidates.json"), "w", encoding="utf-8") as f:
            json.dump(cand, f, ensure_ascii=False, indent=1)

    # Coverage self-check: guard detection is text-based, so a silent regex slip would
    # under-report and the caller would still trust `safe_cold_entry`. Compare against
    # the raw number of `_in_replay` mentions in the same files.
    raw = read_ok = 0
    for path in sorted({r["file"] for r in recs if r["file"]}):
        real = resolve_src(path)
        if not real:
            continue
        read_ok += 1
        try:
            raw += open(real, encoding="utf-8-sig", errors="replace").read().count("_in_replay")
        except OSError:
            read_ok -= 1
    found = len(GUARD_SITES)
    lines.append("_in_replay sites: %d mentioned in %d/%d .rpy read / %d matched as `if _in_replay:`"
                 % (raw, read_ok, len({r["file"] for r in recs if r["file"]}), found))
    if raw and not read_ok:
        lines.append("  !! WARNING: the guard text could not be read at all - head_guard/"
                     "tail_guard are meaningless here, pass --game pointing at the real game dir")
    if raw and found * 2 < raw:
        lines.append("  !! WARNING: the scanner sees far fewer guard sites than exist - "
                     "guard detection has slipped, do not trust safe_cold_entry")
    lines.append("safe cold entry   : %d both guards / %d seed-only / %d stop-only"
                 % (sum(1 for sc in scenes if sc["safe_cold_entry"]),
                    sum(1 for sc in scenes if sc["head_guard"] and not sc["tail_guard"]),
                    sum(1 for sc in scenes if sc["tail_guard"] and not sc["head_guard"])))
    lines.append("dev's own exit ramps: %d labels jump back to the trunk from inside "
                 "`if _in_replay:`" % sum(1 for sc in scenes if sc["exit_ramps"]))

    report = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


def scene_texts(game_dir, cand, all_labels):
    """Slice each candidate's script out of the loose .rpy text.

    Bounds must come from EVERY label in the file, not just the candidates: using the
    next candidate as the end let one scene's text bleed through several unrelated
    labels and get cut mid-line, which is exactly what a classifier must not see.
    The .rpy is byte-identical to what the .rpyc was compiled from in these builds,
    and the AST's `what` strings are the same bytes, so prose order here is honest.
    """
    out = {}
    byfile = collections.defaultdict(list)
    for name, (fn, ln) in all_labels.items():
        byfile[fn].append((ln, name))
    for fn in byfile:
        byfile[fn].sort()

    for s in cand:
        fn = s["file"]
        try:
            src = open(fn, encoding="utf-8-sig", errors="replace").read().splitlines()
        except OSError:
            continue
        bounds = byfile.get(fn, [])
        start = s["line"]
        stop = next((ln for ln, _ in bounds if ln > start), len(src))
        stop = min(stop, start + 900)
        out[s["label"]] = "\n".join(src[start - 1:stop - 1])
    return out


if __name__ == "__main__":
    main()

"""Build the bookmark data file the in-game menu reads, from scan + verdicts + rules.

Inputs
  localization/scenes.json          tools/scan_bookmarks.py  (label -> range, guards)
  localization/verdicts_*.json      per-scene route verdicts (yes / unsure / no)
  localization/bookmark_rules.json  this game's route rules

Output
  game/cc_bookmark_data.rpy         `define cc_bm_entries = [...]` + menu pick table

Why a separate tool and not `build_tl.py --bookmarks`: bookmarks write nothing into the
`translate <lang> strings:` namespace, and that namespace is exactly where a duplicate
`old` crashes the game at startup (playbook 16.4). Keeping the writer separate removes
that risk class instead of managing it.

The interesting piece is `picks`: inside a bookmarked scene, which menu option continues
on-route. That is derived, not guessed - for every paired branch declared in the rules
(one label she-leads, its twin he-leads) we find the menu whose items jump to them and
record the index of the she-leading item. Menus inside a bookmark with no derivable pick
are listed in bookmark_review.txt instead: the mod then stops and shows the real menu,
which is the user's stated rule for undecidable forks.

Usage:
    python tools/build_bookmarks.py --titles localization/bookmark_titles.json
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

SKIP_DIRS = ("tl", "cache", "saves", "lib", "images", "audio", "movies", "gui")


KIND_ZH = {"sex": "性场景", "denial": "禁止高潮", "bondage": "束缚", "grappling": "格斗压制",
           "command": "命令", "punishment": "惩罚", "service": "服侍", "none": "无"}


def load(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


MENU_RE = re.compile(r"^[ \t]*menu[ \t]*:.*$")
ITEM_RE = re.compile(r"^[ \t]+(\"[^\"].*\")[ \t]*:[ \t]*$")
JUMP_RE = re.compile(r"^[ \t]+jump[ \t]+([A-Za-z_]\w*)")


def menu_items_from_text(lines, menu_line):
    """[(index, caption, [jump targets])] for the `menu:` at 1-based `menu_line`.

    Read off the .rpy, not the AST: in the compiled form `Menu.items` is
    [(caption, condition)] and the item *bodies* are linked through `next` in the flat
    statement list, so a nested walk under the Menu node finds no Jump nodes at all
    (verified on chapter08.rpy:7055, the Dominant./Submissive. chooser).
    """
    head = lines[menu_line - 1]
    base = len(head) - len(head.lstrip())
    items = []
    for i in range(menu_line, min(len(lines), menu_line + 400)):
        ln = lines[i]
        if not ln.strip():
            continue
        ind = len(ln) - len(ln.lstrip())
        if ind <= base:
            break
        m = ITEM_RE.match(ln)
        if m and ind > base:
            cap = m.group(1)[1:-1]
            items.append({"index": len(items), "caption": cap, "jumps": []})
            continue
        if items:
            j = JUMP_RE.match(ln)
            if j:
                items[-1]["jumps"].append(j.group(1))
    return items


def file_menus(path):
    """1-based line numbers of every `menu:` statement in a file."""
    try:
        lines = open(path, encoding="utf-8-sig", errors="replace").read().splitlines()
    except OSError:
        return [], []
    return lines, [i + 1 for i, l in enumerate(lines) if MENU_RE.match(l)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="localization/scenes.json")
    ap.add_argument("--verdicts", default="localization/verdicts_*.json")
    ap.add_argument("--rules", default="localization/bookmark_rules.json")
    ap.add_argument("--titles", default="", help="optional {label: 中文标题} map")
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="game/cc_bookmark_data.rpy")
    ap.add_argument("--report", default="localization/bookmark_review.txt")
    args = ap.parse_args()

    scenes = {s["label"]: s for s in load(args.scenes)}
    rules = load(args.rules)
    verdicts = {}
    import glob as _glob
    for pat in _glob.glob(args.verdicts):
        for k, v in load(pat).items():
            verdicts[k] = v
    titles = load(args.titles) if args.titles and os.path.isfile(args.titles) else {}

    # an empty input list reads like "this game has no such content" but usually means
    # a wrong path, so refuse instead of writing a silently empty data file.
    if not scenes:
        raise SystemExit("no scenes loaded from %r - check --scenes" % args.scenes)
    if not verdicts:
        raise SystemExit("no verdicts matched %r - check --verdicts (paths are resolved "
                         "relative to the game root, so run this from there)" % args.verdicts)

    # vars the dev re-seeds inside `if _in_replay:` blocks -> a cold entry into a
    # NON-hardened label would otherwise keep the `define` default (e.g. the player's
    # chosen name shows up as "Dotty").
    game_seed = {}
    for sc in scenes.values():
        for line in sc.get("seed_lines") or []:
            m = re.match(r"\$\s*([A-Za-z_]\w*)\s*=\s*(.+)$", line.strip())
            if m and "persistent" in m.group(2):
                game_seed[m.group(1)] = m.group(2).strip()
    print("learned seed assignments from the game: %s" % (game_seed or "none"))

    menu_cache = {}

    # --- derive menu picks from the declared paired branches ------------------------
    picks = {}
    pair_notes = []
    for pair in rules.get("paired_branches", []):
        she, he = pair.get("she_leads"), pair.get("he_leads")
        if not (she in scenes and he in scenes):
            pair_notes.append("pair skipped (label missing from scenes.json): %r" % pair)
            continue
        path = scenes[she]["file"]
        if path not in menu_cache:
            menu_cache[path] = file_menus(path)
        lines, mlines = menu_cache[path]
        hit = None
        for ml in mlines:
            its = menu_items_from_text(lines, ml)
            i_she = next((x["index"] for x in its if she in x["jumps"]), None)
            i_he = next((x["index"] for x in its if he in x["jumps"]), None)
            if i_she is not None and i_he is not None:
                hit = ("%s:%d" % (path, ml), i_she, i_he, [x["caption"] for x in its])
                break
        if hit:
            picks[hit[0]] = hit[1]
            pair_notes.append("pair %s/%s -> menu %s picks #%d (%s); he-leads is #%d (%s)"
                              % (she, he, hit[0], hit[1], hit[3][hit[1]], hit[2], hit[3][hit[2]]))
        else:
            pair_notes.append("pair %s/%s NOT RESOLVED - no menu jumps to both" % (she, he))

    # --- assemble entries ------------------------------------------------------------
    keep = {"yes", "unsure"}
    entries = []
    for label, v in sorted(verdicts.items(), key=lambda kv: scenes.get(kv[0], {}).get("file", "")):
        if v.get("verdict") not in keep or label not in scenes:
            continue
        sc = scenes[label]
        own = {"file": sc["file"], "line": sc["line"], "range_end": sc["range_end"]}
        extend = []
        for ex in rules.get("stop_guard", {}).get("extend", {}).get(label, []):
            if ex in scenes:
                s2 = scenes[ex]
                extend.append({"file": s2["file"], "line": s2["line"], "range_end": s2["range_end"]})
        # picks that live inside this scene's own range
        lo, hi = sc["line"], sc["range_end"]
        scene_picks = {k: i for k, i in picks.items()
                       if k.startswith(sc["file"] + ":") and lo <= int(k.split(":")[1]) < hi}
        _cm = re.match(r"chapter0*(\d+)", os.path.basename(sc["file"]))
        e_chap = ("第" + _cm.group(1) + "章") if _cm else os.path.basename(sc["file"])
        entries.append({
            "label": label,
            "title": titles.get(label) or label,
            "chapter": e_chap,
            "verdict": v["verdict"],
            "glyph": "★" if v["verdict"] == "yes" else "？",
            "file": sc["file"], "line": sc["line"], "range_end": sc["range_end"],
            "extend": extend,
            "picks": scene_picks,
            "who_leads_zh": {"female": "她主导", "male": "他主导", "switches": "中途互换",
                             "none": ""}.get(str(v.get("who_leads")), ""),
            "meta": "%s · %s · %d 处选项%s" % (
                e_chap,
                "/".join(KIND_ZH.get(k, k) for k in
                         (v.get("kind") if isinstance(v.get("kind"), str)
                          else (v.get("kind") or []))),
                sc.get("menus", 0),
                "" if sc.get("tail_guard") else " · 需停车闸"),
            "note": v.get("note") or "",
            "seed": dict(game_seed),
            "reason": v.get("reason") or "",
        })

    body = ["## GENERATED by tools/build_bookmarks.py - do not hand-edit.",
            "## Delete this file together with game/cc_bookmarks.rpy to uninstall.",
            "",
            "define cc_bm_entries = ["]
    for e in entries:
        body.append("    {")
        for k in ("label", "title", "chapter", "verdict", "glyph", "file", "line", "range_end"):
            v = e[k]
            body.append("        %r: %s," % (k, json.dumps(v, ensure_ascii=False)
                                             if isinstance(v, str) else v))
        body.append("        'extend': %s," % json.dumps(e["extend"], ensure_ascii=False))
        body.append("        'picks': %s," % json.dumps(e["picks"], ensure_ascii=False))
        body.append("        'seed': %s," % json.dumps(e.get("seed", {}), ensure_ascii=False))
        for k in ("who_leads_zh", "meta", "note", "reason"):
            body.append("        %r: %s," % (k, json.dumps(e[k], ensure_ascii=False)))
        body.append("    },")
    body.append("]")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")

    lines = ["bookmarks written  : %d (%s)" % (
        len(entries), ", ".join("%d %s" % (n, k) for k, n in
                                sorted(collections.Counter(e["verdict"] for e in entries).items()))),
             "verdicts seen      : %d (yes/unsure kept, no dropped)" % len(verdicts),
             "menu picks derived : %d" % len(picks)]
    lines += ["  " + s for s in pair_notes]
    unmet = [e["label"] for e in entries
             if scenes[e["label"]]["menus"] and not e["picks"]]
    lines.append("bookmarks with menus but NO pick (auto-pick will stop and ask): %d" % len(unmet))
    for u in unmet:
        lines.append("   %s  menus=%d" % (u, scenes[u]["menus"]))
    noguard = [e["label"] for e in entries if not scenes[e["label"]]["tail_guard"]]
    lines.append("entries needing the stop guard: %d of %d" % (len(noguard), len(entries)))
    report = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    sys.exit(main())

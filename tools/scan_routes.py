"""Find the choices that advance a route the player cares about, and mark them.

Why this exists: the interesting choices in these games are buried in ~200 menus,
and the colour of an option is NOT a reliable signal (this game's own relationship
menu renames the same axis to "[mc]'s Submission" for three characters, and for one
of them the polarity is inverted - fighting her is what gets you dominated). This
tool reads the scripts, works out what each option actually DOES, applies a
declarative rules file, and emits the list of option strings to badge in-game.

    python tools/scan_routes.py --rules localization/route_rules.json
    python tools/scan_routes.py --rules ... --merge-json   # also add unseen screen strings to the json

Outputs:
    localization/route_marks.json   {en: {mark, prefix, sites, evidence, confidence}}
    localization/route_review.txt   what the rules could not decide - never guessed
"""
import argparse
import collections
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MENU_RE = re.compile(r'^(?P<ind> *)menu:\s*(?:"(?P<cap>[^"]*)")?\s*$')
ITEM_RE = re.compile(r'^(?P<ind> +)"(?P<en>(?:[^"\\]|\\.)*)":\s*$')
SCREEN_RE = re.compile(r'^screen\s+(?P<name>\w+)\s*(?:\([^)]*\))?\s*:\s*$')
TEXT_RE = re.compile(r'^\s*text\s+_\("(?P<en>(?:[^"\\]|\\.)*)"\)\s*:?\s*$')
JUMPACT_RE = re.compile(r'Jump\("(?P<label>[\w.]+)"\)')
ASSIGN_RE = re.compile(r'^\s*\$\s*(?P<var>[\w.]+)\s*(?P<op>\+=|-=|=)\s*(?P<val>-?\d+)\s*$')
JUMPCALL_RE = re.compile(r'^\s*(?:jump|call)\s+(?P<label>[\w.]+)')
UISTAT_RE = re.compile(r'_\("(?P<label>[^"]*?):\s*\[(?P<var>\w+)\]"\)')
IND = lambda s: len(s) - len(s.lstrip(" "))


def read(path):
    return open(path, encoding="utf-8-sig").read().splitlines()


def game_files(game_dir, only):
    if only:
        return [f for f in only if os.path.isfile(f)]
    out = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in ("tl", "saves", "cache", "images", "audio", "gui")]
        for fn in files:
            if fn.endswith(".rpy"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def parse_menus(path, lines):
    """[(en, file, line, deltas, jumps, conditional)] from `menu:` statements."""
    sites = []
    i = 0
    while i < len(lines):
        m = MENU_RE.match(lines[i])
        if not m:
            i += 1
            continue
        mind = IND(m.group("ind"))
        i += 1
        while i < len(lines):
            ln = lines[i]
            if not ln.strip() or IND(ln) <= mind and not ln.strip().startswith("#"):
                if IND(ln) <= mind and ln.strip():
                    break
            it = ITEM_RE.match(ln)
            if it and IND(it.group("ind")) > mind:
                iind = IND(it.group("ind"))
                en = it.group("en")
                j, deltas, jumps, cond = i + 1, [], [], False
                while j < len(lines):
                    b = lines[j]
                    if not b.strip():
                        j += 1
                        continue
                    if IND(b) <= iind:
                        break
                    if ITEM_RE.match(b) and IND(b) == iind:
                        break
                    if b.lstrip().startswith("if ") or b.lstrip().startswith("elif "):
                        cond = True
                    a = ASSIGN_RE.match(b)
                    if a:
                        deltas.append((a.group("var"), a.group("op"), int(a.group("val"))))
                    for jm in JUMPACT_RE.finditer(b):
                        jumps.append(jm.group("label"))
                    jc = JUMPCALL_RE.match(b)
                    if jc:
                        jumps.append(jc.group("label"))
                    j += 1
                sites.append({"en": en, "file": path, "line": i + 1, "deltas": deltas,
                              "jumps": jumps, "conditional": cond, "kind": "menu"})
                i = j
                continue
            i += 1
            if i < len(lines) and IND(lines[i]) <= mind and lines[i].strip():
                break
        continue
    return sites


def parse_choice_screens(path, lines, screens_re):
    """[(en, file, line, jumps, color)] from `screen choiceN()` else-branches.

    These games draw the English text into the button image when no language is set,
    and switch to blank buttons + `text _("...")` for every other language - which is
    exactly the case for a translated overlay, so this is the text the player sees.
    """
    sites = []
    scr = screens_re and re.compile(screens_re)
    i = 0
    while i < len(lines):
        sm = SCREEN_RE.match(lines[i])
        if not sm or (scr and not scr.match(sm.group("name"))):
            i += 1
            continue
        sind = 0
        i += 1
        while i < len(lines) and (not lines[i].strip() or IND(lines[i]) > sind):
            ln = lines[i]
            if re.match(r'^\s*(if|elif|else)\b', ln) and "_preferences.language" in ln:
                # the image-button branch shows baked-in art; only the else branch has text
                i += 1
                continue
            if re.match(r'^\s*(if|elif)\b', ln):
                i += 1
                continue
            grp = re.match(r'^(?P<ind> *)(?:fixed|frame|vbox| hbox)\s*:\s*$', ln)
            if not grp:
                i += 1
                continue
            gind = IND(grp.group("ind"))
            block = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or IND(lines[i]) > gind):
                block.append(lines[i])
                i += 1
            en = color = None
            jumps = []
            for b in block:
                t = TEXT_RE.match(b)
                if t:
                    en = t.group("en")
                c = re.match(r'^\s*color\s+"(#[0-9A-Fa-f]{6})"', b)
                if c:
                    color = c.group(1)
                for jm in JUMPACT_RE.finditer(b):
                    jumps.append(jm.group("label"))
            if en:
                sites.append({"en": en, "file": path, "line": i + 1, "deltas": [],
                              "jumps": jumps, "conditional": False, "kind": "screen",
                              "color": color})
        continue
    return sites


def submission_vars(files, rules):
    """Which stat variables the game itself calls the player's submission."""
    out = {}
    axes = rules.get("axis_ui_labels", [])
    if isinstance(axes, dict):
        axes = axes.get("patterns", [])
    pats = [(re.compile(a["re"]), a["mark"]) for a in axes]
    for path in files:
        for ln in read(path):
            m = UISTAT_RE.search(ln)
            if not m:
                continue
            label, var = m.group("label"), m.group("var")
            for rx, mark in pats:
                if rx.search(label):
                    out[var] = mark
    return out


def classify(site, rules, subvars, char_of_var):
    """-> (mark, evidence[], confidence) or (None, ...) when nothing applies."""
    ev, conf = [], "high"
    love_is_she = set(rules.get("love_is_she_leads", []))
    inverted = {k: v for k, v in (rules.get("characters", {}) or {}).items()}
    floor = rules.get("dev_delta_floor", 10)
    if any(abs(val) >= floor for _v, _o, val in site["deltas"]):
        return None, ["dev/gallery jump-setter (abs delta >= %d)" % floor], "dev"
    for var, op, val in site["deltas"]:
        if op == "-=" and any(re.search(p, var) for p in rules.get("penalty_re", [])):
            ev.append("penalty %s-=%d @%s:%d" % (var, val, site["file"], site["line"]))
            return "favor_loss", ev, "high"
        ch = char_of_var.get(var)
        # an explicitly declared polarity inversion outranks the axis label:
        # for Alex the DOMINANCE stat is what gets her on top.
        if ch in inverted and inverted[ch].get("she_leads_var") == var:
            ev.append("%s %s %d -> %s" % (var, op, val, inverted[ch]["why"]))
            return "she_leads", ev, "high"
        mark = subvars.get(var)
        if mark:
            ev.append("%s %s %d (%s axis) @%s:%d" % (var, op, val,
                      "submission" if mark == "she_leads" else "dominance",
                      site["file"], site["line"]))
            return mark, ev, "high" if not site["conditional"] else "medium"
        if var.lower().endswith("love") and ch in love_is_she:
            ev.append("%s %s %d (love path carries the femdom variant)" % (var, op, val))
            return "she_leads", ev, "medium"
        if var.lower().endswith("dom") or var.lower().endswith("love"):
            ev.append("%s %s %d (plain affection/dominance)" % (var, op, val))
            return None, ev, "low"
    low = site["en"].lower()
    for mark, pats in (rules.get("text_sense") or {}).items():
        for p in pats:
            if p.lower() in low:
                ev.append("option text says %r" % p)
                return mark, ev, "high"
    lex = rules.get("label_sense") or {}
    for lab in site["jumps"]:
        ll = lab.lower()
        for mark, pats in lex.items():
            if any(p.lower() in ll for p in pats):
                ev.append("jumps to %s" % lab)
                return mark, ev, "high"
    for fl in rules.get("flag_sense") or []:
        for var, op, val in site["deltas"]:
            if var == fl["flag"] and str(val) == str(fl.get("value", 1)):
                ev.append("sets %s -> %s" % (var, fl["why"]))
                return fl["mark"], ev, "high"
    return None, ev, "none"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="localization/route_rules.json")
    ap.add_argument("--json", default="localization/en-zh.json", help="真源 JSON，用来核对 en 是否逐字节存在")
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="localization/route_marks.json")
    ap.add_argument("--review", default="localization/route_review.txt")
    ap.add_argument("--merge-json", action="store_true", help="append option strings the extractor never saw")
    args = ap.parse_args()

    rules = json.load(open(args.rules, encoding="utf-8"))
    scope = rules.get("scope") or {}
    files = game_files(args.game, scope.get("files"))
    all_rpy = game_files(args.game, None)
    subvars = submission_vars(all_rpy, rules)
    char_of_var = {}
    for var in list(subvars) + [s["she_leads_var"] for s in (rules.get("characters") or {}).values() if s.get("she_leads_var")]:
        char_of_var[var] = re.sub(r"(Love|Dom|Domination|Submission|Sub)$", "", var).lower()
    for ch, spec in (rules.get("characters") or {}).items():
        for var in (spec.get("vars") or {}).values():
            char_of_var[var] = ch
        if spec.get("she_leads_var"):
            char_of_var[spec["she_leads_var"]] = ch

    sites = []
    for f in files:
        lines = read(f)
        sites += parse_menus(f, lines)
        sites += parse_choice_screens(f, lines, scope.get("screens_re"))

    recs = json.load(open(args.json, encoding="utf-8"))
    known = {r["en"] for r in recs}
    say_olds = {r["en"] for r in recs if r["kind"] == "say" and r.get("zh")}

    manual = rules.get("manual") or {}
    force = {m["en"]: m for m in manual.get("force") or []}
    deny = {m["en"]: m for m in manual.get("deny") or []}
    marks, review = {}, []
    for s in sites:
        if s["en"] in deny:
            review.append((s["en"], "denied", "high", "%s:%d" % (s["file"], s["line"]), deny[s["en"]].get("why", "")))
            continue
        if s["en"] in force:
            mark, ev, conf = force[s["en"]]["mark"], ["manual.force: " + force[s["en"]].get("why", "")], "high"
        else:
            mark, ev, conf = classify(s, rules, subvars, char_of_var)
        if not mark:
            if conf in ("none", "low", "dev") and s["en"] not in [r[0] for r in review]:
                review.append((s["en"], "unmarked", conf or "none", "%s:%d" % (s["file"], s["line"]), "; ".join(ev)))
            continue
        review.append((s["en"], mark, conf, "%s:%d" % (s["file"], s["line"]), "; ".join(ev)))
        cur = marks.get(s["en"])
        if cur is None:
            marks[s["en"]] = {"mark": mark, "prefix": rules["marks"][mark],
                              "sites": [], "evidence": ev, "confidence": conf}
        else:
            cur["sites"].append("%s:%d" % (s["file"], s["line"]))
            if cur["confidence"] != conf:
                cur["confidence"] = "medium"

    # a marked string that the dialogue layer already emits would duplicate `old` and crash the game
    clash = sorted(e for e in marks if e in say_olds)
    for e in clash:
        marks[e]["blocked"] = "already emitted by the say layer; marking it would duplicate `old`"
    missing = sorted(e for e in marks if e not in known)

    json.dump({"marks": marks, "blocked_clashes": clash, "not_in_json": missing},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    lines = ["submission axes detected from the game's own UI: %s" % (subvars or "none"),
             "sites scanned: %d   marked strings: %d   review rows: %d" % (len(sites), len(marks), len(review)),
             "blocked (say-layer clash): %s" % (clash or "none"),
             "not in en-zh.json yet (run with --merge-json): %d" % len(missing), ""]
    for en, mark, conf, where, ev in sorted(review, key=lambda r: (r[1] == "unmarked", r[1], r[0])):
        lines.append("%-11s %-9s %-26s %s" % (mark, conf, where, en[:60]))
        if ev:
            lines.append("              evidence: %s" % ev[:150])
    open(args.review, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))
    print("wrote %s and %s" % (args.out, args.review))

    if args.merge_json:
        add = [{"id": "s%06d" % (i + 1), "kind": "menu", "en": e,
                "file": next((r[3].split(":")[0] for r in review if r[0] == e), "game/Choices.rpy"),
                "line": 0, "who": None, "idents": [], "zh": "", "origin": "screen"}
               for i, e in enumerate(missing)]
        if add:
            base = max((int(r["id"][1:]) for r in recs if r["id"][1:].isdigit()), default=0)
            for i, a in enumerate(add):
                a["id"] = "r%06d" % (base + i + 1)
            recs.extend(add)
            json.dump(recs, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("merged %d new option strings into %s" % (len(add), args.json))


if __name__ == "__main__":
    main()

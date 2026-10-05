"""Extract translatable strings from a game that ships LOOSE .rpyc files.

Playbook mode B, AST path. Parsing the .rpy text with a regex silently drops every
say statement whose speaker variable the regex failed to recognise (measured on
Milfylicious 2: 2,541 of 20,090 strings missing, all of them spoken by `x`, the
protagonist). The compiled AST is byte-for-byte the string the engine looks up in
the `strings:` table, so an `old` taken from it can never go stale.

Reads the .rpyc that the engine will actually load; .rpy is only used as a fallback
for statements that have no compiled twin.

Usage:
    python tools/rpyc_extract.py --game game --out localization/en-zh.json
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R

SAY_TYPES = ("renpy.ast.Say", "renpy.ast.TranslateSay")
MENU_TYPES = ("renpy.ast.Menu",)
CODE_TYPES = ("renpy.ast.Define", "renpy.ast.Default", "renpy.ast.Python",
              "renpy.ast.Init", "renpy.ast.Label")
CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]")
NAME_DEF_RE = re.compile(
    r"([A-Za-z_]\w*)\s*=\s*(?:renpy\.)?(?:Dynamic)?Character\s*\(\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|None)"
)
SKIP_DIRS = ("tl", "cache", "saves", "lib", "images", "audio", "movies", "gui")


def who_name(node):
    """Speaker as source text: None, a literal name, or a variable expression."""
    who = getattr(node, "who", None)
    if who is None:
        return None
    if isinstance(who, str):
        return who
    src = R.pycode_source(who)
    if isinstance(src, str):
        return src.strip()
    return R.node_type(who)


def add(records, stats, kind, en, fname, line, who, ident):
    if not isinstance(en, str) or not en.strip():
        stats["skipped_empty"] += 1
        return
    if CJK_RE.search(en):
        stats["skipped_already_cjk"] += 1
        return
    key = en
    rec = records.get(key)
    if rec is None:
        records[key] = {
            "id": "r%06d" % (len(records) + 1),
            "kind": kind,
            "en": en,
            "who": who,
            "file": fname,
            "line": line,
            "occurrences": 1,
            "idents": [ident] if isinstance(ident, str) else [],
            "zh": "",
        }
    else:
        rec["occurrences"] += 1
        if isinstance(ident, str) and ident not in rec["idents"]:
            rec["idents"].append(ident)
        # `say` is the more informative context: keep its speaker/position.
        if kind == "say" and rec["kind"] != "say":
            rec["kind"], rec["who"], rec["file"], rec["line"] = kind, who, fname, line
        else:
            stats["duplicate_old"] += 1


def harvest(game_dir):
    rpyc = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if fn.endswith(".rpyc"):
                rpyc.append(os.path.join(root, fn))
    rpyc.sort()

    records, stats = collections.OrderedDict(), collections.Counter()
    speakers, files_scanned, failed = {}, [], 0

    for path in rpyc:
        rel = os.path.relpath(path, os.curdir).replace("\\", "/")
        try:
            loaded = R.load_script(open(path, "rb").read())
        except Exception as exc:
            loaded = None
            failed += 1
            print("  !! %s: %s" % (rel, exc))
        if not loaded:
            failed += 1
            continue
        data, stmts = loaded
        files_scanned.append((rel, 0))
        for node in R.iter_nodes(stmts):
            t = R.node_type(node)
            d = getattr(node, "__dict__", {}) or {}
            fname = d.get("filename") if isinstance(d.get("filename"), str) else rel[:-1]
            line = d.get("linenumber") if isinstance(d.get("linenumber"), int) else 0

            if t in SAY_TYPES:
                stats["say_nodes"] += 1
                files_scanned[-1] = (rel, files_scanned[-1][1] + 1)
                add(records, stats, "say", d.get("what"), fname, line,
                    who_name(node), d.get("identifier"))
            elif t in MENU_TYPES:
                stats["menu_nodes"] += 1
                for it in d.get("items") or []:
                    try:
                        add(records, stats, "menu", it[0], fname, line, None, None)
                    except Exception:
                        pass

    stats["files"] = len(rpyc)
    stats["files_failed"] = failed
    return list(records.values()), speakers, stats, files_scanned


def speakers_from_sources(game_dir):
    """Display names of the `Character` variables, read from the loose .rpy text.

    8.1.2 pickles `PyCode.source` as a lazy `renpy.ast.PyExpr(filename, linenumber, py)`
    and keeps the real source only in the .rpy, so the compiled AST cannot give us
    `define k = Character("Kendra")`. Say strings themselves are unaffected: `what`
    is stored there as a plain string.
    """
    names = {}
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(".rpy"):
                continue
            try:
                src = open(os.path.join(root, fn), encoding="utf-8-sig",
                           errors="replace").read()
            except OSError:
                continue
            for m in NAME_DEF_RE.finditer(src):
                var, raw = m.group(1), m.group(2)
                if raw == "None":
                    names.setdefault(var, None)
                    continue
                body = raw[1:-1]
                try:
                    body = body.encode("latin-1", "ignore").decode("unicode_escape")
                except Exception:
                    pass
                names[var] = body
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="localization/en-zh.json")
    ap.add_argument("--speakers", default="localization/speakers.json")
    ap.add_argument("--report", default="localization/extract_report.txt")
    ap.add_argument("--want", default="zh|chinese|han|zh_?Hans",
                    help="regex preferring which shipped language to reuse")
    ap.add_argument("--reuse", action="store_true",
                    help="attach official translations found in game/tl/<lang>/*.rpyc")
    args = ap.parse_args()

    recs, speakers, stats, scanned = harvest(args.game)
    speakers.update(speakers_from_sources(args.game))

    # Official translations, matched by identifier (playbook §3.5).
    tl_langs = collections.defaultdict(dict)
    if args.reuse:
        for root, dirs, files in os.walk(os.path.join(args.game, "tl")):
            for fn in sorted(files):
                if not fn.endswith(".rpyc"):
                    continue
                p = os.path.join(root, fn)
                lang = os.path.relpath(p, os.path.join(args.game, "tl")).replace("\\", "/").split("/")[0]
                loaded = R.load_script(open(p, "rb").read())
                if not loaded:
                    continue
                for node in R.iter_nodes(loaded[1]):
                    d = getattr(node, "__dict__", {}) or {}
                    t = R.node_type(node)
                    if t in SAY_TYPES and isinstance(d.get("identifier"), str):
                        tl_langs[lang].setdefault(d["identifier"], d.get("what"))
                    elif t == "renpy.ast.TranslateString" and isinstance(d.get("text"), str):
                        tl_langs[lang].setdefault("S:" + d["text"], d.get("translation"))

    by_ident = {}
    for r in recs:
        for ident in r["idents"]:
            for lang, table in tl_langs.items():
                if ident in table and isinstance(table[ident], str) and table[ident].strip():
                    by_ident.setdefault(r["en"], collections.Counter())[table[ident]] += 1

    chosen = None
    if tl_langs:
        scored = []
        for lang, table in tl_langs.items():
            bonus = 1000 if re.search(args.want, lang, re.I) else 0
            sample = [v for v in list(table.values())[:60] if isinstance(v, str)]
            scored.append((bonus + sum(1 for s in sample if CJK_RE.search(s)), lang))
        scored.sort(reverse=True)
        chosen = scored[0][1]

    for r in recs:
        cands = by_ident.get(r["en"])
        if chosen and cands:
            top = max(cands.values())
            r["zh"] = sorted([k for k, v in cands.items() if v == top])[0]
            r["zh_from"] = "official"
        else:
            r["zh"] = ""
            r["zh_from"] = ""

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    with open(args.speakers, "w", encoding="utf-8") as f:
        json.dump({"display_names": speakers}, f, ensure_ascii=False, indent=1)

    by = collections.Counter(r["kind"] for r in recs)
    ch = collections.Counter()
    for r in recs:
        ch[r["kind"]] += len(r["en"])
    untranslated = sum(1 for r in recs if not r["zh"])
    lines = [
        "mode              : loose .rpyc AST (engine-loaded source of truth)",
        "files scanned     : %d (%d failed to unpickle)" % (stats["files"], stats["files_failed"]),
        "say nodes         : %d / menu nodes: %d" % (stats["say_nodes"], stats["menu_nodes"]),
        "unique strings    : %d (duplicate-old %d, empty %d, already-cjk %d)"
        % (len(recs), stats["duplicate_old"], stats["skipped_empty"], stats["skipped_already_cjk"]),
    ]
    for k in sorted(by):
        lines.append("  %-6s : %d strings / %d chars" % (k, by[k], ch[k]))
    lines.append("shipped languages : %s" % (", ".join(sorted(tl_langs)) or "none"))
    lines.append("chosen for reuse  : %s" % (chosen or "none"))
    lines.append("untranslated      : %d" % untranslated)
    lines.append("speakers          : %s" % json.dumps(speakers, ensure_ascii=False))
    used = collections.Counter(r["who"] for r in recs if r["kind"] == "say")
    unmapped = {w: n for w, n in used.items() if w and w not in speakers}
    lines.append("unmapped speakers : %s" % json.dumps(unmapped, ensure_ascii=False))
    report = "\n".join(lines) + "\n"
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()

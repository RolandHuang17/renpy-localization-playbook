"""Extract translatable text + harvest any translations already shipped inside
the distribution's archives.

Two jobs, one pass:
  1. harvest source-side strings (Say / Menu / _("...")) from non-tl .rpyc files
  2. harvest (en -> target) pairs from tl/<lang>/**.rpyc, joining on the
     restructure-generated `identifier`, plus TranslateString (`strings:`) blocks

Usage:
    python tools/extract.py --game game --lang zh --out localization/en-zh.json
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R  # noqa: E402

SAY_TYPES = ("renpy.ast.TranslateSay", "renpy.ast.Say")
MENU_TYPES = ("renpy.ast.Menu",)
CODE_TYPES = ("renpy.ast.PyCode", "renpy.astsupport.PyExpr")
UWRAP_SIMPLE = re.compile(r"""_p?_?\(\s*(['"])(.*?)\1\s*\)""", re.S)
CJK_RE = re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]"
)
NAME_DEF_RE = re.compile(r"""([A-Za-z_][\w\.]*)\.name\s*=\s*(['"])(.*?)\2""")


def is_ascii_text(s):
    return all(ord(c) < 128 for c in s)


def looks_prose(s):
    """Keep things a reader would want translated; drop code-ish noise."""
    t = s.strip()
    if len(t) < 2:
        return False
    if not re.search(r"[A-Za-z]", t):
        return False
    if re.fullmatch(r"[\W_\d\s]+", t):
        return False
    if len(t) > 4 and not re.search(r"[a-z]{2}", t):
        return False
    return True


def classify(name):
    """('src'|'tl', language_or_None, normalized_rpy_path)"""
    parts = name.replace("\\", "/").split("/")
    if parts and parts[0] == "tl":
        lang = parts[1] if len(parts) > 2 else ""
        rest = "/".join(parts[2:])
        return "tl", lang, rest
    return "src", None, "/".join(parts)


def norm_rpy(path):
    """game/scripts/foo.rpy / scripts/foo.rpyc -> scripts/foo.rpy"""
    p = path.replace("\\", "/")
    if p.startswith("game/"):
        p = p[len("game/") :]
    if p.endswith(".rpyc"):
        p = p[: -len("rpy")] if False else p[:-1]
    return p


def open_archives(game_dir, verbose=True):
    rpa_paths = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in ("cache", "saves")]
        for fn in files:
            if fn.endswith(".rpa"):
                rpa_paths.append(os.path.join(root, fn))
    rpa_paths.sort(key=lambda p: os.path.getsize(p))
    archives = []
    for p in rpa_paths:
        try:
            archives.append(R.RPA3(p))
        except Exception as e:
            if verbose:
                print("  ! skip %s (%s)" % (p, e), file=sys.stderr)
    if verbose:
        print("archives: " + ", ".join(os.path.basename(a.path) for a in archives))
    return archives


def iter_rpyc(archives, verbose=True):
    for arc in archives:
        try:
            names = [n for n in arc.names() if n.endswith(".rpyc")]
        except Exception as e:
            print("  ! index fail %s: %s" % (arc.path, e), file=sys.stderr)
            continue
        for n in sorted(names):
            try:
                obj = R.load_script(arc.read(n))
            except Exception as e:
                print("  ! fail %s:%s (%s)" % (arc.path, n, e), file=sys.stderr)
                continue
            if obj is None:
                continue
            try:
                _data, stmts = obj
            except Exception:
                continue
            yield n, stmts


def harvest(archives, verbose=True):
    """Returns src_recs (ordered dict by (kind,en)), tl_maps, speakers, stats."""
    records = collections.OrderedDict()
    tl_by_ident = collections.defaultdict(dict)  # lang -> identifier -> text
    tl_strings = collections.defaultdict(dict)  # lang -> old -> new
    speakers = {}
    stats = collections.Counter()

    def add(kind, en, src_file, line, who, ident):
        if not isinstance(en, str) or not en:
            return
        if CJK_RE.search(en) or not looks_prose(en):
            return
        if not isinstance(who, str):
            who = None
        key = (kind, en)
        rec = records.get(key)
        if rec is None:
            records[key] = {
                "id": "r%06d" % (len(records) + 1),
                "kind": kind,
                "en": en,
                "who": who,
                "file": src_file if isinstance(src_file, str) else "?",
                "line": line if isinstance(line, int) else 0,
                "occurrences": 1,
                "idents": [ident] if isinstance(ident, str) else [],
            }
        else:
            rec["occurrences"] += 1
            if isinstance(ident, str) and ident not in rec["idents"]:
                rec["idents"].append(ident)

    for name, stmts in iter_rpyc(archives, verbose):
        kind_, lang, rest = classify(name)
        stats["files"] += 1
        for node in R.iter_nodes(stmts):
            t = R.node_type(node)
            d = getattr(node, "__dict__", {})
            fname = d.get("filename") if isinstance(d.get("filename"), str) else rest
            line = d.get("linenumber") if isinstance(d.get("linenumber"), int) else 0

            if kind_ == "tl":
                if t in SAY_TYPES and isinstance(d.get("identifier"), str):
                    tl_by_ident[lang][d["identifier"]] = d.get("what")
                elif t == "renpy.ast.TranslateString":
                    old, new = d.get("text"), d.get("translation")
                    if isinstance(old, str) and isinstance(new, str):
                        tl_strings[lang][old] = new
                continue

            if t in ("renpy.ast.Define", "renpy.ast.Default"):
                src = R.pycode_source(d.get("code"))
                if src:
                    for m in NAME_DEF_RE.finditer(src):
                        speakers.setdefault(m.group(1), m.group(3))
                    if "Character(" in src and isinstance(d.get("varname"), str):
                        speakers.setdefault("@" + d["varname"], src.strip())

            if t in SAY_TYPES:
                stats["say_nodes"] += 1
                add(
                    "say",
                    d.get("what"),
                    fname,
                    line,
                    d.get("who"),
                    d.get("identifier"),
                )
            elif t in MENU_TYPES:
                stats["menu_nodes"] += 1
                for i, it in enumerate(d.get("items") or []):
                    try:
                        cap = it[0]
                    except Exception:
                        continue
                    add("menu", cap, fname, line, None, None)
            elif t in CODE_TYPES:
                src = R.pycode_source(node)
                if src and "_(" in src:
                    stats["code_nodes"] += 1
                    for m in UWRAP_SIMPLE.finditer(src):
                        body = m.group(2)
                        try:
                            decoded = body.encode("latin1", "ignore").decode(
                                "unicode_escape"
                            )
                        except Exception:
                            decoded = body
                        add("uwrap", decoded, fname, line, None, None)

    for i, rec in enumerate(records.values()):
        rec["index"] = i
    if verbose:
        print("files scanned: %d" % stats["files"])
        print(" " + ", ".join("%s=%d" % kv for kv in sorted(stats.items())))
        print("tl languages: " + ", ".join(sorted(tl_by_ident)))
        for lang in sorted(tl_by_ident):
            print(
                "  %-22s id-blocks=%d strings=%d"
                % (lang, len(tl_by_ident[lang]), len(tl_strings[lang]))
            )
        print("source unique strings: %d" % len(records))
    return records, tl_by_ident, tl_strings, speakers, stats


def pick_language(langs, tl_by_ident, tl_strings, want=None):
    """Choose the best already-shipped translation to reuse."""
    scored = []
    for lang in langs:
        if want and re.search(want, lang, re.I):
            bonus = 1000
        else:
            bonus = 0
        sample = list(tl_by_ident[lang].values())[:60]
        cjk = sum(1 for s in sample if s and CJK_RE.search(s))
        scored.append((bonus + cjk, lang))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None


def merge(records, tl_by_ident, tl_strings, target_lang, stats):
    """Attach official translation to each record; majority-vote per EN string."""
    by_ident = tl_by_ident.get(target_lang, {})
    by_string = tl_strings.get(target_lang, {})
    for rec in records.values():
        cands = []
        for ident in rec["idents"]:
            v = by_ident.get(ident)
            if isinstance(v, str) and v.strip():
                cands.append(v)
        if not cands:
            v = by_string.get(rec["en"])
            if isinstance(v, str) and v.strip() and v != rec["en"]:
                cands.append(v)
        if cands:
            # deterministic majority vote
            best = collections.Counter(cands).most_common()
            top = max(c[1] for c in best)
            tied = sorted([c[0] for c in best if c[1] == top])
            rec["zh"] = tied[0]
            rec["zh_from"] = "official"
            rec["zh_variants"] = len(best)
            stats["official"] += 1
            stats["official_chars"] += len(rec["zh"])
            if len(best) > 1:
                stats["ambiguous"] += 1
        else:
            rec["zh"] = ""
            rec["zh_from"] = ""
            stats["gap"] += 1
            stats["gap_chars"] += len(rec["en"])
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="game")
    ap.add_argument("--out", default="localization/en-zh.json")
    ap.add_argument("--speakers", default="localization/speakers.json")
    ap.add_argument("--report", default="localization/extract_report.txt")
    ap.add_argument(
        "--target-lang",
        default="zh",
        help="language code we will generate (used only for the report)",
    )
    ap.add_argument(
        "--want",
        default="zh|chinese|han",
        help="regex preferring which shipped language to reuse",
    )
    args = ap.parse_args()

    archives = open_archives(args.game)
    records, tl_by_ident, tl_strings, speakers, stats = harvest(archives)
    langs = set(tl_by_ident) | set(tl_strings)
    chosen = pick_language(langs, tl_by_ident, tl_strings, args.want) if langs else None
    lines = []
    lines.append("shipped languages: %s" % (", ".join(sorted(langs)) or "(none)"))
    lines.append("chosen for reuse : %s" % (chosen or "(none - translate from scratch)"))
    if chosen:
        merge(records, tl_by_ident, tl_strings, chosen, stats)
    else:
        for rec in records.values():
            rec["zh"] = ""
            rec["zh_from"] = ""

    by = collections.Counter(r["kind"] for r in records.values())
    ch = collections.Counter()
    gap_by = collections.Counter()
    for r in records.values():
        ch[r["kind"]] += len(r["en"])
        if not r["zh"]:
            gap_by[r["kind"]] += 1
    lines.append("unique strings   : %d" % len(records))
    for k in sorted(by):
        lines.append(
            "  %-6s %6d strings %9d chars   untranslated=%d" % (k, by[k], ch[k], gap_by[k])
        )
    lines.append(
        "official reuse : %d (%d chars), gap=%d (%d chars), ambiguous=%d"
        % (stats["official"], stats["official_chars"], stats["gap"], stats["gap_chars"], stats["ambiguous"])
    )

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(list(records.values()), f, ensure_ascii=False, indent=1)
    with open(args.speakers, "w", encoding="utf-8") as f:
        json.dump(speakers, f, ensure_ascii=False, indent=1)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("wrote %s" % args.out)


if __name__ == "__main__":
    main()

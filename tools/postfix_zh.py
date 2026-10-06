"""Deterministic post-pass over the master table, run AFTER apply_trans and BEFORE build_tl.

Three things that batch agents cannot be trusted to keep consistent, and that re-running
batches to fix would cost an hour for:

1. **Monologue parentheses.** The source writes MC's thoughts as `( ... )`; several agents
   dropped the full-width `（）` (self-reported in 6 of 55 batches). Rule: if the English
   is fully wrapped in ASCII parentheses and the Chinese has none, wrap it. Anything else
   is left alone -- do not "helpfully" add parens to lines the source did not wrap.
2. **Whitespace.** Leading/trailing spaces inside values (one agent flagged a trailing
   space) survive into the rendered line and look like a layout bug.
3. **Named overrides.** Agents that were forbidden from editing after their single Write
   disclose exact defects with the intended text (`r021045 should read （…）`). Those are
   applied from `localization/zh_fixes.json` so the disclosure actually lands.

Usage:
    python tools/postfix_zh.py --dry-run      # counts only
    python tools/postfix_zh.py                # backup + rewrite
"""
import argparse, json, re, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--fixes", default="localization/zh_fixes.json")
    ap.add_argument("--report", default="localization/postfix_report.txt")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d = json.load(open(args.json, encoding="utf-8"))
    recs = d["records"] if isinstance(d, dict) and "records" in d else d
    by_id = {}
    for r in recs:
        by_id.setdefault(r["id"], r)

    WRAP = re.compile(r"^\s*\((.*)\)\s*$", re.S)
    n_wrap = n_trim = n_fix = 0
    lines = []
    for r in recs:
        zh = r.get("zh") or ""
        if not zh:
            continue
        new = zh.strip()
        if new != zh:
            n_trim += 1
        en = r.get("en") or ""
        m = WRAP.match(en)
        if m and ("（" not in new and "(" not in new):
            new = "（" + new + "）"
            n_wrap += 1
        r["zh"] = new

    try:
        fixes = json.load(open(args.fixes, encoding="utf-8"))
    except Exception:
        fixes = {}
    for rid, val in fixes.items():
        r = by_id.get(rid)
        if r is None:
            lines.append("MISSING ID %s (fix not applied)" % rid)
            continue
        if r.get("zh") != val:
            r["zh"] = val
            n_fix += 1

    rep = ["parentheses re-wrapped : %d" % n_wrap,
           "values trimmed         : %d" % n_trim,
           "named overrides applied: %d" % n_fix,
           ""] + lines
    open(args.report, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep[:4]))
    if lines:
        print("\n".join(lines))
    if args.dry_run:
        print("dry run: nothing written")
        return
    import shutil
    shutil.copyfile(args.json, args.json + ".bak-postfix")
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("wrote %s (backup .bak-postfix)" % args.json)


main()

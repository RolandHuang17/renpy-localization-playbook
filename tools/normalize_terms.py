"""Post-hoc term normalization across already-collected translation batches.

Why this exists: 20+ parallel agents cannot all see each other's coinages, so a term
that the glossary did not pin gets invented three times (this project: `cluck` ->
动态 / 破图 / 那桩啪啪事, and `glory hole` -> 隔墙洞 / 情趣墙洞 / 墙洞 / 厕洞).
Re-dispatching those batches to fix one word is the expensive wrong answer; the cheap
one is a deterministic rewrite over the master table, longest-variant-first, with counts.

Spec file (default localization/terms_normal.json):
  {"terms": [{"en": "glory hole", "zh": "隔墙洞",
              "variants": ["情趣墙洞", "厕洞", "墙洞"],
              "why": "glossary pinned after wave 1; earlier batches vary"}]}

Usage:
    python tools/normalize_terms.py --dry-run
    python tools/normalize_terms.py            # writes en-zh.json.bak-terms first
"""
import argparse, collections, json, os, shutil, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--spec", default="localization/terms_normal.json")
    ap.add_argument("--report", default="localization/terms_report.txt")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    spec = json.load(open(args.spec, encoding="utf-8"))["terms"]
    d = json.load(open(args.json, encoding="utf-8"))
    inline = isinstance(d, dict) and "records" in d
    recs = d["records"] if inline else d
    counts = collections.Counter()
    rows = []
    for t in spec:
        # longest first: 情趣墙洞 must be replaced before 墙洞 or we get 隔墙洞洞
        vs = sorted(set(t["variants"]) - {t["zh"]}, key=len, reverse=True)
        n = 0
        for r in recs:
            zh = r.get("zh") or ""
            if not zh:
                continue
            new = zh
            for v in vs:
                if v in new:
                    n += new.count(v)
                    new = new.replace(v, t["zh"])
            if new != zh:
                r["zh"] = new
        counts[t["en"]] = n
        rows.append("%-14s -> %-8s  replaced %4d variant hits  (variants: %s)"
                    % (t["en"], t["zh"], n, ", ".join(vs) or "-"))
    open(args.report, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print("\n".join(rows))
    if args.dry_run:
        print("dry run: nothing written")
        return
    shutil.copyfile(args.json, args.json + ".bak-terms")
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("wrote %s (backup %s)" % (args.json, args.json + ".bak-terms"))


main()

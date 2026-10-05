"""De-transliterate a reused official translation: turn 凯尔 back into Kyle.

Why: when a distribution already ships an official target-language translation it
usually transliterates character names. If the requirement is "keep proper names in
the original script", the reused translation must be post-processed.

Method (no external data, purely evidence based):
  1. candidate latin names  = capitalised tokens that appear mid-sentence in the EN
     side often enough to be a recurring referent
  2. for each candidate N, take A = zh lines whose EN contains N, B = the rest
  3. a CJK n-gram is the transliteration of N if it is frequent in A and essentially
     absent from B  (discriminative alignment)
  4. emit a proposal table; --apply rewrites the master JSON

Usage:
    python tools/denames.py --json localization/en-zh.json            # propose
    python tools/denames.py --json localization/en-zh.json --apply    # rewrite
"""

import argparse
import collections
import json
import os
import re
import sys

CJK_RUN = re.compile(r"[一-鿿]+")
LAT = re.compile(r"(?<![A-Za-z])([A-Z][a-z]{2,9})(?![A-Za-z])")

# Characters that are overwhelmingly used to *sound out* foreign names rather than
# to mean something. Requiring one of them is what stops 早上/妈妈/先生 from being
# mistaken for a transliteration of Morning/Mom/Sir.
TRANSLIT_CHARS = set(
    "尔娅莎琳茜丝蒂塔尼亚奥姆茨普拉雅基夫娃娜本贝雷兹古斯科丁斯坦芬莎尔玛曼"
    "洛蕾莉莱斯维文森班克内尔杜拉荷莉莎菲奥古斯特朱利安"
)

STOP = set(
    """The This That These Those There Here You Your Yours We They Their His Her Its What When
    Where Which Who Whom Why How All Any Some Many Most Few More Less Now Then Once Today
    Tomorrow Morning Evening Night Week Monday Tuesday Wednesday Thursday Friday Saturday Sunday
    January February March April May June July August September October November December
    Mr Mrs Ms Dr Sir Madam Hey Oh Wow Well Yeah Hmm Hmmm Ah Please Thanks Thank Sorry Yes No
    Maybe Really Sure Okay Ok Nope But And Or Because Since While After Before Until During
    With Without From Into Onto About Above Below Nobody Somebody Anybody Everybody Something
    Nothing Everything Anything First Second Third Next Last Same Other Another Every Each
    Game Day Time Moment Minute Hour Month Year House Home Room Office Street Town City School
    Work Job Class Party Event Phone Screen Message Call Photo Picture Camera Bed Shower
    Kitchen Door Window Mirror Closet Garden Pool Gym Bar Club Store Shop Mall Bank Hospital
    Hotel Airport Station Beach Lake Forest Park Alley Rooftop Basement Woman Man Guy Girl Boy
    People Person Friend Babe Lady Dude Mother Father Mom Dad Mommy Daddy Sister Brother Aunt
    Uncle Cousin Grandma Grandpa Son Daughter Family Wife Husband Boyfriend Girlfriend
    Professor Teacher Student Coach Doctor Nurse Boss Manager Chief Officer Detective Lawyer
    Agent Partner Rival Enemy Stranger Neighbor Look Listen Feel Think Know Say Tell Ask Want
    Need Hope Wish Seem Go Come Get Give Take Make Do Have Will Would Can Could Should Must
    Let Leave Stay Move Wait Start Finish Help Fuck Shit Damn Hell Ass Dick Cum Sex Nude
   """.split()
)


def cjk_grams(text, lo=2, hi=6):
    out = set()
    for run in CJK_RUN.findall(text):
        for n in range(lo, hi + 1):
            for i in range(len(run) - n + 1):
                out.add(run[i : i + n])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--kinds", default="say")
    ap.add_argument("--min-count", type=int, default=25)
    ap.add_argument("--min-in", type=float, default=0.30, help="freq inside A")
    ap.add_argument("--max-out", type=float, default=0.02, help="freq outside B")
    ap.add_argument("--report", default="localization/names_proposed.tsv")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument(
        "--manual",
        default="localization/names_manual.tsv",
        help="human-confirmed latin<TAB>cjk,comma-list rows merged into the mapping",
    )
    ap.add_argument("--backup", default="localization/en-zh.before_denames.json")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    kinds = tuple(k.strip() for k in args.kinds.split(","))
    pairs = [(r["en"], r["zh"]) for r in recs if r["kind"] in kinds and r.get("zh")]
    print("aligned pairs with official translation: %d" % len(pairs))

    # 1. candidate latin names (mid-sentence capitalised tokens)
    cand = collections.Counter()
    for en, _ in pairs:
        for m in LAT.finditer(en):
            w = m.group(1)
            if w in STOP:
                continue
            if m.start() == 0:
                continue  # sentence-initial capitalisation is not evidence
            cand[w] += 1
    cands = [w for w, c in cand.items() if c >= args.min_count]
    print("candidate names: %d" % len(cands))

    # 2/3. discriminative CJK n-grams
    gram_in = collections.defaultdict(collections.Counter)
    gram_out = collections.Counter()
    out_lines = 0
    for en, zh in pairs:
        grams = cjk_grams(zh)
        matched = [w for w in cands if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % w, en)]
        if matched:
            for w in matched:
                for g in grams:
                    gram_in[w][g] += 1
        else:
            out_lines += 1
            for g in grams:
                gram_out[g] += 1

    rows = []
    unfiltered = []
    for w in cands:
        a = sum(1 for en, _ in pairs if re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % w, en))
        scored = []
        for g, c in gram_in[w].items():
            fin = c / max(1, a)
            fout = gram_out[g] / max(1, out_lines)
            if fin >= args.min_in and fout <= args.max_out:
                scored.append((fin - fout, fin, fout, g, c))
        scored.sort(reverse=True)
        unfiltered.append((w, a, scored[:5]))
        best = [s for s in scored if any(ch in TRANSLIT_CHARS for ch in s[3])]
        # keep the longest mutually-covering grams only
        keep = []  # (gram, fin, fout, count)
        for score, fin, fout, g, c in best:
            if any(g in k[0] for k in keep):
                continue
            keep = [k for k in keep if k[0] not in g]
            keep.append((g, fin, fout, c))
        if keep:
            rows.append((w, a, keep[:4]))

    with open(args.report.replace(".tsv", "_all.tsv"), "w", encoding="utf-8") as f:
        f.write("latin\tlines\tCJK\tin_A\tout_B\thas_translit_char\n")
        for w, a, scored in unfiltered:
            for score, fin, fout, g, c in scored:
                f.write(
                    "%s\t%d\t%s\t%.2f\t%.3f\t%s\n"
                    % (w, a, g, fin, fout, any(ch in TRANSLIT_CHARS for ch in g))
                )

    with open(args.report, "w", encoding="utf-8") as f:
        f.write("latin\tlines\tCJK\tin_A\tout_B\thits\n")
        for w, a, keep in rows:
            for g, fin, fout, c in keep:
                f.write("%s\t%d\t%s\t%.2f\t%.3f\t%d\n" % (w, a, g, fin, fout, c))
    print("proposed mapping -> %s (%d candidates matched)" % (args.report, len(rows)))
    for w, a, keep in rows[:40]:
        print("  %-12s %4d  %s" % (w, a, ", ".join("%s(%.2f/%.3f)" % k[:3] for k in keep[:2])))

    if not args.apply:
        print("\nreview the tsv, then re-run with --apply")
        return

    # (cjk gram -> latin name) from the auto-detected set, restricted to the
    # unambiguous ones, plus whatever the human confirmed in the manual file.
    subs = {}
    for w, a, keep in rows:
        for g, fin, fout, c in keep:
            if fin >= 0.4 and fout <= 0.005:
                subs[g] = w
    if args.manual and os.path.exists(args.manual):
        for line in open(args.manual, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "\t" not in line:
                continue
            latin, grams = line.split("\t", 1)
            latin = latin.strip()
            for g in grams.split(","):
                g = g.strip()
                if not g:
                    continue
                if "~" in g:  # prefix~charsThatMustNotFollow  (bare 简 but not 简单)
                    pre, bad = g.split("~", 1)
                    subs.setdefault(pre + "~" + bad, latin)
                    subs[pre + "~" + bad] = latin
                else:
                    subs[g] = latin
    # "Ruby's" is often transliterated with a trailing 斯 -> 鲁比斯, so carry every
    # gram's 斯-variant too when the corpus actually contains it.
    corpus = "".join(z for _e, z in pairs)
    for g, w in list(subs.items()):
        if "~" not in g and g + "斯" in corpus:
            subs[g + "斯"] = w
    # longest gram first so 伊莎贝尔斯 wins over 伊莎贝尔 and 哈丁塔 over 哈丁;
    # every variant stays in the list (a shorter one still has to catch the lines
    # where the transliteration appears without the possessive 斯).
    ordered = sorted(subs.items(), key=lambda kv: -len(kv[0].split("~")[0]))
    ordered = [(g, g.split("~")[0], w) for g, w in ordered]

    if not os.path.exists(args.backup):
        with open(args.backup, "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
    changed = 0
    diff = []
    for r in recs:
        if not r.get("zh"):
            continue
        new = r["zh"]
        hit = False
        for g, pre, w in ordered:
            if "~" in g:
                pfx, bad = g.split("~", 1)
                pat = re.compile("(%s)(?![%s])" % (re.escape(pfx), re.escape(bad)))
                new, k = pat.subn(" %s " % w, new)
            else:
                k = new.count(g)
                if k:
                    new = new.replace(g, " %s " % w)
            if k:
                hit = True
        if not hit:
            continue
        new = re.sub(r"[ \t]{2,}", " ", new)
        # a latin name glued to CJK punctuation should not keep the padding space
        new = re.sub(r"([，。！？、；：））」”》)\]]) +", r"\1", new)
        new = re.sub(r" +([，。！？、；：））」”》])", r"\1", new)
        new = re.sub(r"([(（「“《\[]) +", r"\1", new)
        new = re.sub(r" +([（（「“《])", r"\1", new)
        new = new.strip()
        if new != r["zh"]:
            if len(diff) < 12:
                diff.append((r["zh"], new))
            r["zh"] = new
            r["zh_dename"] = 1
            changed += 1
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)
    print("replacements: %s" % ", ".join("%s->%s" % (g, w) for g, _pre, w in ordered))
    print("applied: %d lines rewritten, backup at %s" % (changed, args.backup))
    for a, b in diff:
        print("  - %s\n  + %s" % (a, b))


if __name__ == "__main__":
    main()

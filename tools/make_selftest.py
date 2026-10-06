"""Build the §9.0 in-game self-test harness (tools/selftest_template.rpy).

Probe strings and say statements are generated from the master JSON, never typed by
hand - a hand-copied curly apostrophe silently misses the `strings:` table and looks
like "the translation does not work".

Copy both files into the project, then:
    python tools/make_selftest.py localization/en-zh.json mix
    # launch the game; it writes localization/selftest_report.txt and shots/
    python tools/uninstall.py --dry-run   # the harness must show up here

Delete game/tl/<lang>/99zz_selftest.rpy AND its .rpyc before delivery.
`mix` takes one line per layout hazard (tallest block, inline {size=}, a namebox,
an interpolation, a moan that must stay on one line); no argument takes the longest.
"""
import json
import os
import sys

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "-h" in sys.argv or "--help" in sys.argv:
    # The tools/*.py --help sweep (playbook 14 step 0) runs every tool this way; without
    # this guard the script tries to open a file literally named "--help" and the sweep
    # reports a permanent false failure.
    print("usage: python tools/make_selftest.py <en-zh.json> [mix|long|tags|all]")
    raise SystemExit(0)

src = os.path.join(base, sys.argv[1] if len(sys.argv) > 1 else "localization/smoke.json")
mode = sys.argv[2] if len(sys.argv) > 2 else ""

tpl_path = next(x for x in (os.path.join(base, "tools", "selftest_template.rpy"),
                            os.path.join(base, "localization", "selftest_template.rpy"))
                if os.path.isfile(x))
tpl = open(tpl_path, encoding="utf-8-sig").read()
recs = json.load(open(src, encoding="utf-8"))
say = [r for r in recs if r.get("zh")]


def pick_mix(rows):
    """One representative of every layout hazard the say box can hit."""
    def first(pred):
        return next((r for r in rows if pred(r)), None)
    by_len = sorted(rows, key=lambda r: -len(r["en"]))
    picks = [
        first(lambda r: r["who"] in ("a", "a1")),         # namebox first: shot 1 catches it
        by_len[0],                                        # tallest bilingual block
        first(lambda r: "{size=26}" in r["en"]),          # inline size change mid-line
        first(lambda r: r["who"] == "x"),                 # namebox, protagonist
        first(lambda r: "[" in r["en"] and r["who"]),     # interpolation next to a name
        first(lambda r: not any("一" <= c <= "鿿" for c in r["zh"])),  # single-line output
        first(lambda r: 30 < len(r["en"]) < 60),          # a short exchange
    ]
    seen, uniq = set(), []
    for p in picks:
        if p and p["id"] not in seen:
            seen.add(p["id"])
            uniq.append(p)
    return uniq


pick = pick_mix(say) if mode == "mix" else sorted(say, key=lambda r: -len(r["en"]))[:9]
# The harness asserts translate_string over this exact list, so the screenshot and
# the assertion can never drift apart.
probes = os.path.join(base, "localization", "selftest_probes.json")
json.dump(pick, open(probes, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
rel = "localization/selftest_probes.json"

names = {}
sp = os.path.join(base, "localization", "speakers.json")
if os.path.isfile(sp):
    names = json.load(open(sp, encoding="utf-8")).get("display_names", {})

rows = []
for r in pick:
    rows.append("    $ zz_say(%s, %s)\n" % (json.dumps(r.get("who") or "", ),
                                            json.dumps(r["en"], ensure_ascii=False)))

out = tpl.replace("##JSON##", rel).replace("##NAMES##", json.dumps(names, ensure_ascii=False))
out = out.replace("##SAYS##", "".join(rows).rstrip("\n"))
dest = os.path.join(base, "game", "tl", "zh", "99zz_selftest.rpy")
os.makedirs(os.path.dirname(dest), exist_ok=True)
open(dest, "w", encoding="utf-8", newline="\n").write("\ufeff" + out)
print("wrote %s" % dest)
for r in pick:
    print("   who=%-5s len=%-4d %s" % (r.get("who"), len(r["en"]), r["en"][:60].replace("\n", " ")))

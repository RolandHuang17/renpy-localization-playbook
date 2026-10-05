"""Recommend the say-window geometry for a bilingual overlay (playbook §5.1).

Stacking Chinese over English roughly doubles the line count. A game whose
`style window` has a FIXED `ysize` therefore clips the second language, and the
value must be derived from the whole corpus rather than guessed.

Estimates use the engine's own metrics: a glyph is ~0.52em wide for latin and
~1.02em for CJK, and a line box is ~1.32x the point size.

Usage:
    python tools/textbox_fit.py --gui game/gui.rpy
    python tools/textbox_fit.py --width 1116 --size 38 --ypos 75 --height 278
"""

import argparse
import json
import math
import os
import re
import sys

TAGS = re.compile(r"\{[^{}]*\}")
GUI = {
    "textbox_height": re.compile(r"define gui\.textbox_height\s*=\s*(\d+)"),
    "dialogue_width": re.compile(r"define gui\.dialogue_width\s*=\s*(\d+)"),
    "dialogue_ypos": re.compile(r"define gui\.dialogue_ypos\s*=\s*(\d+)"),
    "text_size": re.compile(r"define gui\.text_size\s*=\s*(\d+)"),
}


def read_gui(path):
    out = {}
    if not os.path.isfile(path):
        return out
    src = open(path, encoding="utf-8-sig", errors="replace").read()
    for k, rx in GUI.items():
        m = rx.search(src)
        if m:
            out[k] = int(m.group(1))
    return out


def lines_for(en, zh, width, size):
    lat = width / (0.52 * size)
    cjk = width / (1.02 * size)
    en, zh = TAGS.sub("", en), TAGS.sub("", zh)
    # an explicit \n always costs a line break, so count each segment separately
    e = sum(max(1, math.ceil(len(p) / lat)) for p in en.split("\n"))
    z = sum(max(1, math.ceil(len(p) / cjk)) for p in zh.split("\n"))
    return e + z


def split_lines(en, zh, width, size, en_size):
    """(chinese_px, english_px) - the two languages can be sized differently."""
    def seg(text, per):
        return sum(max(1, math.ceil(len(p) / per)) for p in text.split("\n"))
    z = seg(TAGS.sub("", zh), width / (1.02 * size)) * size * 1.32
    e = seg(TAGS.sub("", en), width / (0.52 * en_size)) * en_size * 1.32
    return z, e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--gui", default="game/gui.rpy")
    ap.add_argument("--width", type=int, default=0)
    ap.add_argument("--size", type=int, default=0, help="the game's base text size")
    ap.add_argument("--ypos", type=int, default=0)
    ap.add_argument("--height", type=int, default=0, help="the game's current ysize")
    ap.add_argument("--sizes", default="", help="candidate point sizes, e.g. 38,34,30")
    ap.add_argument("--en-sizes", default="",
                    help="candidate sizes for the reference line when the box stays put")
    args = ap.parse_args()

    g = read_gui(args.gui)
    width = args.width or g.get("dialogue_width") or 1116
    base = args.size or g.get("text_size") or 38
    ypos = args.ypos or g.get("dialogue_ypos") or 75
    cur = args.height or g.get("textbox_height") or 0

    recs = [r for r in json.load(open(args.json, encoding="utf-8"))
            if r["kind"] == "say" and r.get("zh")]
    if not recs:
        raise SystemExit("no translated say records in %s - run apply_trans first" % args.json)

    cands = [base] + [int(s) for s in args.sizes.split(",") if s.strip()]
    print("corpus: %d translated say lines | width %d | ypos %d | current ysize %d"
          % (len(recs), width, ypos, cur))
    print("size  max  p99.5  p99 | ysize@100%% ysize@p99.5  shift-up  clipped")
    for size in dict.fromkeys(cands):
        ln = sorted(lines_for(r["en"], r["zh"], width, size) for r in recs)
        n = len(ln)
        p995, p99 = ln[int(n * 0.995) - 1], ln[int(n * 0.99) - 1]
        top = ln[-1]
        need = lambda k: int(math.ceil(k * size * 1.32)) + ypos
        clip = sum(1 for v in ln if v > (cur - ypos) / (size * 1.32)) if cur else 0
        print("%4d %4d %6d %5d | %9d %11d %8d %7d"
              % (size, top, p995, p99, need(top), need(p995), need(top) - cur, clip))
    n = len(recs)
    ens = [int(x) for x in args.en_sizes.split(",") if x.strip()]
    if ens and cur:
        avail = cur - ypos
        print("\nkeeping the box exactly as shipped (ysize %d, %d px for text), Chinese"
              " at the game's own %d, English reference shrunk:" % (cur, avail, base))
        print("en_size  zh-clipped  any-clipped  worst-line")
        for es in ens:
            pairs = [split_lines(r["en"], r["zh"], width, base, es) for r in recs]
            zo = sum(1 for z, _e in pairs if z > avail)
            to = sum(1 for z, e in pairs if z + e > avail)
            worst = max(z + e for z, e in pairs)
            print("%7d %8d (%4.1f%%) %9d (%4.1f%%) %8.0fpx"
                  % (es, zo, 100.0 * zo / n, to, 100.0 * to / n, worst))
        print("zh-clipped is the number that matters: the Chinese line is drawn first,")
        print("so whatever falls outside the box is the English reference tail.")

    print("\nysize must be a FIXED number. `ysize None` makes the stock say window")
    print("wrap its two children (namebox + text) in a Fixed, which reports the whole")
    print("available area as its size - the box becomes fullscreen. See playbook §5.1.")
    print("If the game's `style window` has `background None`, growing ysize adds no")
    print("visible panel; it only lifts where the text starts. Pass --window-bg none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

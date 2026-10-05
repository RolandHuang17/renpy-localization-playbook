"""Read a TTF/OTF `cmap` with the standard library only.

Used to answer one question before we put a character on screen: does this font
actually have the glyph? Ren'Py has no per-glyph fallback, so a missing glyph is
a tofu box, and the game's own UI font (LEMONMILK here) carries Latin only - any
symbol or CJK marker must either be wrapped in {font=} or not used at all.

Usage:
    python tools/font_cmap.py --font game/fonts/NotoSansSC-VariableFont_wght.ttf --text "⚑她主导"
"""
import argparse
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _tables(data):
    num = struct.unpack(">H", data[4:6])[0]
    stride = 16 if struct.unpack(">I", data[0:4])[0] == 0x10000 else 12
    out = {}
    for i in range(num):
        base = 12 + stride * i
        tag = data[base:base + 4]
        offset = struct.unpack(">I", data[base + 8:base + 12])[0]
        out[tag] = offset
    return out


def cmap_of(path):
    """Return the set of codepoints this font claims to cover."""
    data = open(path, "rb").read()
    off = _tables(data).get(b"cmap")
    if off is None:
        return set()
    count = struct.unpack(">H", data[off + 2:off + 4])[0]
    subs = []
    for i in range(count):
        pid, eid, so = struct.unpack(">HHI", data[off + 4 + 8 * i:off + 12 + 8 * i])
        subs.append((pid, eid, so))
    # prefer a full Unicode subtable: (3,10) fmt12 > (3,1) fmt4 > (0,x)
    subs.sort(key=lambda t: (0 if t[:2] == (3, 10) else 1 if t[:2] == (3, 1) else 2 if t[0] == 0 else 3))
    codes = set()
    for pid, eid, so in subs[:1]:
        base = off + so
        fmt = struct.unpack(">H", data[base:base + 2])[0]
        if fmt == 4:
            segx = struct.unpack(">H", data[base + 6:base + 8])[0] // 2
            ends = struct.unpack(">%dH" % segx, data[base + 14:base + 14 + 2 * segx])
            starts = struct.unpack(">%dH" % segx, data[base + 16 + 2 * segx:base + 16 + 4 * segx])
            deltas = struct.unpack(">%dh" % segx, data[base + 18 + 4 * segx:base + 18 + 6 * segx])
            rpos = base + 18 + 6 * segx
            ranges = struct.unpack(">%dH" % segx, data[rpos:rpos + 2 * segx])
            for i in range(segx):
                if starts[i] == 0xFFFF:
                    break
                for c in range(starts[i], min(ends[i], 0xFFFE) + 1):
                    if ranges[i] == 0:
                        # idRangeOffset 0: the delta result IS the glyph id, and
                        # glyph 0 is .notdef - a tofu box, not coverage.
                        if (c + deltas[i]) & 0xFFFF:
                            codes.add(c)
                    else:
                        p = rpos + 2 * i + ranges[i] + 2 * (c - starts[i])
                        gi = struct.unpack(">H", data[p:p + 2])[0]
                        if gi:
                            gi = (gi + deltas[i]) & 0xFFFF
                        if gi:
                            codes.add(c)
        elif fmt in (12, 13):
            ngroups = struct.unpack(">I", data[base + 12:base + 16])[0]
            for i in range(ngroups):
                sc, ec, gs = struct.unpack(">III", data[base + 16 + 12 * i:base + 28 + 12 * i])
                # sc/ec are CODEPOINTS; gs is the start glyph id and must not be
                # mistaken for one (that mistake reports tofu as coverage).
                codes.update(range(sc, ec + 1))
        elif fmt == 6:
            first, entry = struct.unpack(">HH", data[base + 6:base + 10])
            for i in range(entry):
                if data[base + 10 + i]:
                    codes.add(first + i)
    return codes


def missing(font_path, text):
    codes = cmap_of(font_path)
    return sorted({ch for ch in text if ord(ch) > 0x20 and ord(ch) not in codes})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--text", default="")
    ap.add_argument("--list-codepoints", default="", help="space separated U+XXXX")
    args = ap.parse_args()
    codes = cmap_of(args.font)
    print("%s: %d codepoints" % (args.font, len(codes)))
    bad = missing(args.font, args.text)
    print("MISSING for %r: %s" % (args.text, " ".join("U+%04X %s" % (ord(c), c) for c in bad) or "none"))
    for tok in args.list_codepoints.split():
        cp = int(tok.replace("U+", ""), 16)
        print("  U+%04X %s -> %s" % (cp, chr(cp), "ok" if cp in codes else "MISSING"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

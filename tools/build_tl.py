"""Generate a bilingual (target + English) Ren'Py `tl` overlay layer.

Inputs : localization/en-zh.json (from tools/extract.py)
Outputs: <out>/<lang>/**.rpy   translate <lang> strings: blocks (one per source file)
         <out>/<lang>/00zz_bilingual.rpy  language + font + line-break plumbing

Everything written here is NEW. Source archives, engine files and saves are never
touched, so uninstalling is deleting the generated paths (see tools/uninstall.py).

Usage:
    python tools/build_tl.py --lang zh --kinds say --layout zh-first
"""

import argparse
import collections
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpautil as R  # noqa: E402

# renpy/translation/__init__.py:497 quote_unicode - keep byte-identical.
def quote_unicode(s):
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\a", "\\a")
    s = s.replace("\b", "\\b")
    s = s.replace("\f", "\\f")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    s = s.replace("\v", "\\v")
    return s


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CJK_FONT_HINTS = (
    "notosanssc", "notoserifsc", "sourcehan", "simhei", "simsun", "msyh",
    "yahei", "hanSans", "NotoSansCJK", "dengxian", "pingfang", "harmonyos",
)
WEIGHTS = ["Black", "SemiBold", "Medium", "Bold", "Regular", "Light", "Thin"]


def weight_of(name):
    low = name.lower()
    for w in WEIGHTS:
        if w.lower() in low:
            return w
    return "Regular"


def find_cjk_fonts(game_dir, extra_dirs=()):
    """Locate CJK-capable fonts already inside archives (preferred) or on disk."""
    found = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in ("saves",)]
        for fn in files:
            if fn.endswith(".rpa"):
                try:
                    arc = R.RPA3(os.path.join(root, fn))
                except Exception:
                    continue
                for n in arc.names():
                    if n.lower().endswith((".ttf", ".otf")) and any(
                        h.lower() in n.lower() for h in CJK_FONT_HINTS
                    ):
                        found.append(n)
                arc.close()
    for d in extra_dirs:
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower().endswith((".ttf", ".otf")) and any(
                    h.lower() in fn.lower() for h in CJK_FONT_HINTS
                ):
                    found.append(os.path.join(d, fn))
    return sorted(set(found))


def game_fonts(game_dir):
    """All latin-ish .ttf/.otf paths the game can render text with."""
    out = set()
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in ("saves",)]
        for fn in files:
            if fn.endswith(".rpa"):
                try:
                    arc = R.RPA3(os.path.join(root, fn))
                except Exception:
                    continue
                for n in arc.names():
                    if n.lower().endswith((".ttf", ".otf")):
                        out.add(n)
                arc.close()
            elif fn.lower().endswith((".ttf", ".otf")):
                rel = os.path.relpath(os.path.join(root, fn), game_dir).replace("\\", "/")
                out.add("game/" + rel if not rel.startswith("game/") else rel)
    return sorted(out)


def build_font_map(fonts, cjk_fonts):
    """(latin font path -> cjk path) with matching weight where possible."""
    by_weight = {}
    for c in cjk_fonts:
        by_weight.setdefault(weight_of(os.path.basename(c)), c)
    primary = by_weight.get("Regular") or (cjk_fonts[0] if cjk_fonts else None)
    fm, frm = {}, {}
    for f in fonts:
        base = os.path.basename(f)
        if base.lower().endswith((".ttf", ".otf")) and any(
            h.lower() in base.lower() for h in CJK_FONT_HINTS
        ):
            continue  # already a CJK font
        if primary is None:
            continue
        repl = by_weight.get(weight_of(base), primary)
        fm[f] = repl
        for bold in (True, False):
            for ital in (True, False):
                frm[(f, bold, ital)] = (repl, bold, ital)
    return fm, frm, primary


def norm_target(src_file):
    """game/scripts/sub/x.rpy(.rpyc) -> scripts/sub/x.rpy  (normalise BEFORE grouping)"""
    p = (src_file or "").replace("\\", "/")
    if p.startswith("game/"):
        p = p[len("game/") :]
    if p.endswith(".rpyc"):
        p = p[:-1]
    if not p.endswith(".rpy"):
        p = (p or "misc") + ".rpy"
    if p.startswith("tl/"):
        p = p.split("/", 2)[-1]
    return p


def layout_pair(zh, en, layout, sep, font_tag=None):
    if layout == "zh-only":
        return wrap_font(zh, font_tag)
    # moans, onomatopoeia and name-only lines have nothing to translate; stacking
    # them would print the same English twice in the say box
    if not CJK_RE.search(zh):
        return en
    if layout == "en-first":
        return sep.join([en, wrap_font(zh, font_tag)])
    return sep.join([wrap_font(zh, font_tag), en])


def wrap_font(zh, font_tag):
    """`--font-mode tag` renders only the Chinese line in the CJK font, so the
    game's own latin typeface is untouched. The zh string already carries the
    original's {tags}; wrapping the whole thing keeps them balanced."""
    if not font_tag:
        return zh
    return "{font=%s}%s{/font}" % (font_tag, zh)


SETUP_TEMPLATE = '''# Generated by tools/build_tl.py - bilingual overlay for "{lang}".
# Pure addition: delete this file (and game/tl/{lang}/) to uninstall.

init -2000 python:
    config.default_language = "{lang}"

init -1510 python:
{font_block}
    # Chinese has no spaces: without UAX#14 line breaking a long line never wraps.
    style.text.language = "eastasian"

    # Optional: appear in the game's own language picker, if it has one
    # (many games ship `define languages = {{}}` filled by each tl/<lang>/<lang>.rpy).
    try:
        languages["{lang}"] = ({picker_name!r}, {primary!r})
    except Exception:
        pass

init -1000 python:
    # 00defaults only applies config.default_language on the very first run, and a
    # returning player's persistent may already hold another language, so set it here.
    if not persistent.{flag}:
        renpy.game.preferences.language = "{lang}"

# Applied AFTER gui._apply_rebuild(), which change_language() calls and which
# otherwise wipes the init-time style changes.
{style_blocks}'''

FONT_MAP_BLOCK = """\
    # Font plumbing. style.text.font takes no fallback chain and there is no
    # automatic per-glyph substitution, so every latin-only font the game uses
    # is remapped to a font that also carries CJK glyphs.
    _zh_font_map = {fmap!r}
    for _k, _v in _zh_font_map.items():
        config.font_name_map[_k] = _v
    _zh_repl = {frepl!r}
    for _k, _v in _zh_repl:
        config.font_replacement_map[tuple(_k)] = tuple(_v)
"""

FONT_TAG_BLOCK = """\
    # --font-mode tag: the Chinese line is wrapped in {font=...} inside the
    # translated strings themselves, so the game keeps its own latin typeface
    # everywhere else. No font maps here on purpose - they would also catch the
    # fonts the game sets explicitly for its title cards.
"""


def style_blocks(lang, font_mode, primary, textbox_height,
                 window_bg="gui/textbox.png", window_borders="430, 20",
                 window_styles=("say_window",), window_ypos=None):
    out = []
    if font_mode == "map" and primary:
        for st in ("default", "say_dialogue", "nvl_dialogue"):
            out.append("translate %s style %s:\n    font %r\n" % (lang, st, primary))
    body = 'translate %s style say_dialogue:\n    language "eastasian"\n' % lang
    if textbox_height:
        # Grow the fixed-height say window to fit both languages. Do NOT use
        # `ysize None`: the stock say screen's window holds a namebox AND the
        # text, so SL wraps them in a Fixed, and a Fixed reports the whole
        # available area as its size - the window silently becomes fullscreen
        # and the stretched background dims the entire game.
        body += (
            "\ntranslate %s style say_window:\n"
            "    ysize %d\n"
            "    background Frame(\"%s\", %s, xalign=0.5, yalign=1.0)\n"
            % (lang, textbox_height, window_bg, window_borders)
        )
    # Alternative to the above when the artwork must not stretch: move the box up.
    # NOTE the style names - a game whose `screen say` says `style "window"` never
    # touches say_window, so `--window-style window,window1` is what works there.
    for st in window_styles:
        if window_ypos is not None:
            body += "\ntranslate %s style %s:\n    ypos %d\n" % (lang, st, window_ypos)
    out.append(body)
    return "\n".join(out)


def write_setup(path, lang, fonts, cjk_fonts, picker_name, flag,
                font_mode="map", textbox_height=0, font_tag=None,
                window_bg="gui/textbox.png", window_borders="430, 20",
                window_styles=("say_window",), window_ypos=None):
    if font_mode == "map":
        fm, frm, primary = build_font_map(fonts, cjk_fonts)
        font_block = FONT_MAP_BLOCK.format(
            fmap=fm,
            frepl=[[list(k), list(v)]
                   for k, v in sorted(frm.items(), key=lambda t: str(t[0]))],
        )
        nmap = len(fm)
    else:
        fm, primary, font_block, nmap = {}, (cjk_fonts or [None])[0], FONT_TAG_BLOCK, 0
    if primary is None and font_mode == "map":
        raise SystemExit(
            "no CJK-capable font found - install/copy one (e.g. NotoSansSC) and re-run"
        )
    body = SETUP_TEMPLATE.format(
        lang=lang,
        font_block=font_block,
        primary=font_tag or primary,
        picker_name=picker_name,
        flag=flag,
        style_blocks=style_blocks(lang, font_mode, primary, textbox_height,
                                  window_bg, window_borders,
                                  window_styles, window_ypos),
    )
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\ufeff" + body)
    return primary, nmap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--gamedir", default="game")
    ap.add_argument("--out", default=None, help="default: <gamedir>/tl/<lang>")
    ap.add_argument("--kinds", default="say", help="comma list: say,menu,uwrap")
    ap.add_argument(
        "--layout",
        default="zh-first",
        choices=["zh-first", "en-first", "zh-only"],
    )
    ap.add_argument("--sep", default="\\n", help="separator between the two lines")
    ap.add_argument("--limit", type=int, default=0, help="smoke test: first N entries")
    ap.add_argument("--picker-name", default="中文 / English")
    ap.add_argument("--flag", default="mp_bi_off", help="persistent toggle name")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument(
        "--font-mode",
        default="map",
        choices=["map", "tag"],
        help="map = remap every latin font to a CJK one (safe for tofu, changes the "
             "game's latin look). tag = wrap only the Chinese line in {font=...} and "
             "leave the game's own typeface alone.",
    )
    ap.add_argument(
        "--cjk-font",
        default=None,
        help="copy this font file into tl/<lang>/font/ and use it (needed with "
             "--font-mode tag, or when the game ships no CJK font at all)",
    )
    ap.add_argument(
        "--font-ref",
        default=None,
        help="path renpy.loader can already resolve (a font the GAME ships). "
             "--font-mode tag wraps the Chinese line in {font=THIS} and copies "
             "nothing - use it whenever the archive/dir already has a CJK font",
    )
    ap.add_argument(
        "--textbox-height",
        type=int,
        default=0,
        help="if the game's say window has a FIXED ysize (gui.textbox_height), pass "
             "that number: the window then grows upward instead of clipping the "
             "second language off screen",
    )
    ap.add_argument(
        "--window-bg",
        default="gui/textbox.png",
        help="say window background artwork, used with --textbox-height so the "
             "stretched Frame matches the game instead of a hardcoded path",
    )
    ap.add_argument(
        "--window-borders",
        default="430, 20",
        help="Frame left/right, top/bottom borders in px. left+right must stay "
             "under the image width or the horizontal fades get squeezed",
    )
    ap.add_argument(
        "--window-style", default="say_window",
        help="comma list of the styles the game's say window really uses. Read "
             "`screen say` first: a game that writes `style \"window\"` never sees "
             "say_window, so the default does nothing there.")
    ap.add_argument("--window-ypos", type=int, default=None,
        help="absolute ypos for --window-style. Raising a FIXED-height box is the "
             "no-stretch way to gain lines (ysize None turns a two-child window "
             "into a full-screen Fixed, see playbook 5.1).")
    ap.add_argument(
        "--manifest", default="localization/generated_files.txt"
    )
    args = ap.parse_args()

    sep = args.sep.encode().decode("unicode_escape")
    out_dir = args.out or os.path.join(args.gamedir, "tl", args.lang)
    kinds = tuple(k.strip() for k in args.kinds.split(","))

    recs = json.load(open(args.json, encoding="utf-8"))
    picked = collections.OrderedDict()
    prio = {"say": 0, "menu": 1, "uwrap": 2}
    for r in recs:
        if r["kind"] not in kinds or not r.get("zh"):
            continue
        old = r["en"]
        if old in picked and prio.get(picked[old]["kind"], 9) <= prio.get(r["kind"], 9):
            continue  # keep the higher-priority kind's translation
        picked[old] = r
    items = list(picked.values())
    if args.limit:
        items = items[: args.limit]

    if args.clean and os.path.isdir(out_dir):
        removed = 0
        for root, dirs, files in os.walk(out_dir):
            for fn in files:
                if fn.endswith((".rpy", ".rpyc")):
                    os.remove(os.path.join(root, fn))
                    removed += 1
        print("cleaned %d generated files" % removed)

    # group by NORMALISED target path first (playbook bug #10)
    groups = collections.defaultdict(list)
    for r in items:
        groups[norm_target(r["file"])].append(r)

    os.makedirs(out_dir, exist_ok=True)

    # Copy the CJK font INTO the overlay dir: pure addition, and the path the game
    # loads stays under game/tl/<lang>/ so uninstalling is still just deleting files.
    font_tag = None
    if args.font_ref:
        font_tag = args.font_ref
    elif args.cjk_font:
        fdir = os.path.join(out_dir, "font")
        os.makedirs(fdir, exist_ok=True)
        base = os.path.basename(args.cjk_font)
        dest = os.path.join(fdir, base)
        if not os.path.isfile(dest):
            shutil.copyfile(args.cjk_font, dest)
        font_tag = "/".join(["tl", args.lang, "font", base])

    written = []
    for tpath, rs in sorted(groups.items()):
        rs.sort(key=lambda r: (r["file"], r["line"]))
        dest = os.path.join(out_dir, tpath)
        dn = os.path.dirname(dest)
        if dn:
            os.makedirs(dn, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write("\ufeff")
            f.write("# Bilingual overlay generated by tools/build_tl.py\n")
            f.write("# Chinese + original English, both shown.\n")
            f.write("translate %s strings:\n\n" % args.lang)
            for r in rs:
                new = layout_pair(r["zh"], r["en"], args.layout, sep,
                                  font_tag if args.font_mode == "tag" else None)
                f.write("    # %s:%s\n" % (r["file"], r["line"]))
                f.write('    old "%s"\n' % quote_unicode(r["en"]))
                f.write('    new "%s"\n' % quote_unicode(new))
                f.write("\n")
        written.append(dest)

    setup = os.path.join(out_dir, "00zz_bilingual.rpy")
    fonts = game_fonts(args.gamedir)
    cjk = find_cjk_fonts(args.gamedir, extra_dirs=(os.path.join(out_dir, "font"),))
    primary, nmap = write_setup(
        setup, args.lang, fonts, cjk, args.picker_name, args.flag,
        font_mode=args.font_mode, textbox_height=args.textbox_height,
        font_tag=font_tag, window_bg=args.window_bg,
        window_borders=args.window_borders,
        window_styles=tuple(x.strip() for x in args.window_style.split(",")),
        window_ypos=args.window_ypos,
    )
    written.append(setup)
    if args.font_mode == "tag" and not font_tag:
        print("WARNING: --font-mode tag without --cjk-font writes no {font=} wrapper; "
              "Chinese will render as tofu unless the game already ships a CJK font")

    os.makedirs(os.path.dirname(args.manifest) or ".", exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as f:
        f.write("\n".join(written) + "\n")

    print(
        "wrote %d .rpy files (%d strings) to %s" % (len(written) - 1, len(items), out_dir)
    )
    print("setup: %s  font=%s  mapped=%d latin fonts" % (setup, primary, nmap))
    print("game fonts: %s" % ", ".join(fonts))
    print("cjk fonts:  %s" % ", ".join(cjk))


if __name__ == "__main__":
    main()

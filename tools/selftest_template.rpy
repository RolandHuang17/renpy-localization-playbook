# TEMPORARY in-game self-test harness. Delete this file AND game/tl/zh/99zz_selftest.rpyc.
# It asserts the bilingual overlay through the real say screen and screenshots it.

init 9999 python:
    import json, os, time

    _zz = {"t0": None, "jumped": False, "next_shot": 0, "stage": 0}
    _zz_base = os.path.normpath(renpy.config.renpy_base)
    _zz_dir = os.path.join(_zz_base, "localization", "shots")
    _zz_rep = os.path.join(_zz_base, "localization", "selftest_report.txt")
    if not os.path.isdir(_zz_dir):
        os.makedirs(_zz_dir)

    def _zz_lines():
        # Probe strings come from the generated list, never typed by hand: one
        # differing character (a curly apostrophe) makes the strings table miss.
        p = os.path.join(_zz_base, "##JSON##")
        return json.load(open(p, encoding="utf-8"))

    def _zz_style_info():
        out = []
        try:
            import renpy.display.style as DS
            for name in ("say_window", "say_dialogue"):
                st = DS.style.get(name, "_zz")
                out.append("%s: ysize=%s size=%s font=%s language=%s" % (
                    name, getattr(st, "ysize", "?"), getattr(st, "size", "?"),
                    getattr(st, "font", "?"), getattr(st, "language", "?")))
        except Exception as exc:
            out.append("style introspection unavailable: %r" % (exc,))
        return out

    def _zz_write(tag):
        rows = ["=== %s ===" % tag,
                "elapsed              : %s" % round(time.time() - (_zz["t0"] or 0), 1),
                "preferences.language : %r" % (renpy.game.preferences.language,),
                "known_languages      : %r" % (sorted(renpy.known_languages()),),
                "default_language     : %r" % (renpy.config.default_language,),
                "font_name_map        : %r" % (dict(renpy.config.font_name_map),),
                "afm_enable/afm_time  : %r / %r" % (renpy.game.preferences.afm_enable,
                                                     renpy.game.preferences.afm_time),
                "text_cps             : %r" % (renpy.game.preferences.text_cps,),
                "context.current      : %r" % (renpy.game.context().current,)]
        rows += _zz_style_info()
        rows.append("")
        rows.append("--- translate_string on real source strings ---")
        hits = 0
        for r in _zz_lines():
            t = renpy.translate_string(r["en"])
            if t != r["en"]:
                hits += 1
            rows.append("HIT=%s [%s:%s] who=%s" % (
                "YES" if t != r["en"] else "NO", r["file"], r["line"], r["who"]))
            rows.append("  OLD: " + r["en"].replace(chr(10), "\\n")[:160])
            rows.append("  NEW: " + t.replace(chr(10), "\\n")[:240])
        rows.append("")
        rows.append("hits %d / %d" % (hits, len(_zz_lines())))
        try:
            open(_zz_rep, "w", encoding="utf-8").write(chr(10).join(rows) + chr(10))
        except Exception:
            pass

    def _zz_run():
        now = time.time()
        if _zz["t0"] is None:
            _zz["t0"] = now
        el = now - _zz["t0"]
        if el > 12 and _zz["stage"] == 0:
            _zz["stage"] = 1
            _zz_write("before jump")
        if el > 16 and not _zz["jumped"]:
            _zz["jumped"] = True
            renpy.jump_out_of_context("zz_probe")
        if _zz["jumped"] and el > _zz["next_shot"] and _zz["stage"] < 3:
            if _zz["next_shot"] == 0:
                _zz["next_shot"] = el + 1.2
            elif _zz["stage"] < 3:
                _zz["shots"] = _zz.get("shots", 0) + 1
                try:
                    renpy.screenshot(os.path.join(
                        _zz_dir, "shot_%02d.png" % _zz["shots"]))
                except Exception:
                    pass
                _zz["next_shot"] = el + 1.25
                if _zz["shots"] >= 12:
                    _zz["stage"] = 3
                    _zz_write("after probe")
        if el > 75 and _zz["stage"] < 3:
            _zz["stage"] = 3
            _zz_write("timeout")

    def _zz_tick():
        # A swallowed JumpOutException means the jump silently never happened,
        # so it must go back up untouched.
        try:
            _zz_run()
        except renpy.game.JumpOutException:
            raise
        except Exception as exc:
            _zz["stage"] = 3
            try:
                open(_zz_rep, "w", encoding="utf-8").write(
                    "HARNESS ERROR: %r\n" % (exc,))
            except Exception:
                pass

    renpy.config.periodic_callbacks.append(_zz_tick)

init 9998 python:
    import json
    _zz_names = json.loads(r'''##NAMES##''')
    _zz_chars = {}

    import re as _zz_re

    def zz_say(who, text):
        # Go through the stock say screen with a real Character, so the namebox and
        # say_dialogue styles are both exercised - a synthetic screen of isolated
        # text widgets cannot reproduce the two-child window layout.
        # `[x]`, `[m]`, `[b]` ... are story variables created while playing, so the
        # main-menu context has no binding for them and substitution raises KeyError.
        for _m in _zz_re.finditer(r"\[([A-Za-z_]\w*)[!\]]", text):
            if _m.group(1) not in store.__dict__:
                setattr(store, _m.group(1), _m.group(1))
        if who and who not in _zz_chars:
            _zz_chars[who] = Character(_zz_names.get(who) or who)
        if who:
            _zz_chars[who](text)
        else:
            renpy.say(None, text)

label zz_probe:
    $ renpy.game.preferences.afm_enable = True
    $ renpy.game.preferences.afm_time = 6.0
    $ renpy.game.preferences.text_cps = 0
##SAYS##
    return

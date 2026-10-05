"""Reuse the game's shipped translation when it is *plaintext* .rpy (mode B).

extract.py does this for archived .rpyc; this is the loose-file counterpart.
Ren'Py's `translate` command writes shipped translations as id blocks:

    # game/script.rpy:6
    translate chinese start_9f50295d:

        # "Would you like to see the tutorial?"
        "你想看新手教程吗？"

and strings blocks as `old "..." / new "..."`. Both forms are joined to the
source by *string content*, so no `get_code()` / md5 reconstruction is needed.
"""
import argparse, collections, json, os, re, shutil

CWD = os.getcwd()


def unescape(s):
    """Decode a Ren'Py / Python double-quoted string body."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c != "\\" or i + 1 >= n:
            out.append(c); i += 1; continue
        nx = s[i + 1]
        mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "a": "\a", "b": "\b", "f": "\f", "v": "\v"}
        if nx in mapping:
            out.append(mapping[nx])
        elif nx == "u" and i + 5 < n:
            out.append(chr(int(s[i + 2:i + 6], 16))); i += 4
        elif nx == "U" and i + 9 < n:
            out.append(chr(int(s[i + 2:i + 10], 16))); i += 8
        elif nx == "x" and i + 3 < n:
            out.append(chr(int(s[i + 2:i + 4], 16))); i += 2
        else:
            out.append(c); out.append(nx)  # Python keeps unknown escapes verbatim: "\%" -> "\%"
        i += 2
    return "".join(out)


STR_RE = re.compile(r'^\s*(?:(?:old|new)\s+|[A-Za-z_][\w.]*\s+)?"((?:[^"\\]|\\.)*)"\s*(?:\S.*)?$')
COMMENT_STR_RE = re.compile(r'^\s*#\s*(?:[A-Za-z_][\w.]*\s+)?"((?:[^"\\]|\\.)*)"\s*(?:\S.*)?$')
BLOCK_RE = re.compile(r'^translate\s+(\S+)\s+(\S+)\s*:\s*$')
PYBLOCK_RE = re.compile(r'^translate\s+(\S+)\s+python\s*:\s*$')


def harvest(path, lang):
    """Yield (old, new) pairs for `lang` from one plaintext translate file.

    Handles both shapes Ren'Py emits: `# "old"` / `"new"` and the speaker-
    prefixed `# mc "old"` / `mc "new"`, plus `old`/`new` pairs in strings and
    python blocks. A non-matching line never drops a pending `old`.
    """
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines()
    in_want, pending = False, None
    for raw in lines:
        m = BLOCK_RE.match(raw)
        if m:
            in_want = m.group(1) == lang
            pending = None
            continue
        if PYBLOCK_RE.match(raw):
            in_want = True if lang == "python" else False
            continue
        if not in_want:
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        if pending is None:
            cm = COMMENT_STR_RE.match(raw)
            if cm:
                pending = unescape(cm.group(1))
                continue
            if stripped.startswith("old "):
                m2 = STR_RE.match(raw)
                if m2:
                    pending = unescape(m2.group(1))
            continue
        if STR_RE.match(raw):
            yield pending, unescape(STR_RE.match(raw).group(1))
            pending = None
            continue
        cm = COMMENT_STR_RE.match(raw)
        if cm:
            pending = unescape(cm.group(1))



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="localization/en-zh.json")
    ap.add_argument("--tl", default="game/tl/chinese", help="shipped translation dir (a folder of .rpy)")
    ap.add_argument("--lang", default=None, help="language keyword inside the blocks (default: folder name)")
    ap.add_argument("--apply", action="store_true", help="write zh back into the json (default: dry run)")
    ap.add_argument("--backup", default="localization/en-zh.before_reuse.json")
    ap.add_argument("--report", default="localization/reuse_report.txt")
    args = ap.parse_args()

    lang = args.lang or os.path.basename(os.path.normpath(args.tl))
    files = sorted(f for f in os.listdir(args.tl) if f.endswith(".rpy"))
    votes = collections.defaultdict(collections.Counter)
    n_pairs = 0
    for f in files:
        for old, new in harvest(os.path.join(args.tl, f), lang):
            n_pairs += 1
            if new and new != old:
                votes[old][new] += 1

    entries = json.load(open(args.json, encoding="utf-8"))
    # whitespace-only drift between the shipped translation and a newer source
    # ("what about you?" vs "what  about you?") is the most common near-miss.
    norm_votes = collections.defaultdict(collections.Counter)
    for old, cand in votes.items():
        norm_votes[" ".join(old.split())].update(cand)
    filled = exact = fuzzy = ambiguous = still = 0
    chars_reused = 0
    for e in entries:
        if e.get("zh"):
            continue
        cand = votes.get(e["en"])
        src = "exact"
        if not cand:
            cand = norm_votes.get(" ".join(e["en"].split()))
            src = "fuzzy"
        if not cand:
            still += 1
            continue
        if len(cand) > 1:
            ambiguous += 1
        best = min(cand, key=lambda z: (-cand[z], z))
        e["zh"] = best
        filled += 1
        if src == "exact":
            exact += 1
        else:
            fuzzy += 1
        chars_reused += len(best)
    say = [e for e in entries if e["kind"] == "say"]
    rep = []
    rep.append("shipped translation dir : %s (lang keyword %s)" % (args.tl, lang))
    rep.append("files scanned           : %d" % len(files))
    rep.append("old/new pairs harvested : %d" % n_pairs)
    rep.append("distinct source strings : %d" % len(votes))
    rep.append("entries total / say     : %d / %d" % (len(entries), len(say)))
    rep.append("reused (zh filled)      : %d  (%d chars, exact %d, whitespace-fuzzy %d, ambiguous %d)"
               % (filled, chars_reused, exact, fuzzy, ambiguous))
    rep.append("still untranslated      : %d  (%d chars)" % (still, sum(len(e["en"]) for e in entries if not e["zh"])))
    rep.append("say still untranslated  : %d  (%d chars)" % (
        sum(1 for e in say if not e["zh"]), sum(len(e["en"]) for e in say if not e["zh"])))
    txt = "\n".join(rep) + "\n"
    open(args.report, "w", encoding="utf-8").write(txt)
    print(txt)
    if args.apply:
        if not os.path.exists(args.backup):
            shutil.copy2(args.json, args.backup)
        json.dump(entries, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote %s (backup %s)" % (args.json, args.backup))
    else:
        print("dry run; pass --apply to write")


if __name__ == "__main__":
    main()

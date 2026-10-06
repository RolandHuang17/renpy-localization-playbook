"""Repair the mechanical JSON defects a translation shard picks up at scale.

Agents writing 500-line JSON by hand make two recurring typos: a key that lost its
opening quote, and an unescaped `"` inside a value (usually quoting a Chinese
coinage). Re-dispatching a whole group costs more than the tokens the group is
worth, so fix the syntax and let tools/apply_trans.py re-check the content.

The repair is deliberately narrow: one record per line, keys matched against the
group file, and anything it cannot prove correct is reported instead of guessed.

Usage:
    python tools/repair_json.py --in localization/out_13.json --group localization/groups/group_13.json
"""

import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
LINE = re.compile(r'^\s*"(?P<key>[^"\s]+)"\s*:\s*(?P<val>.+?)\s*,?\s*$')
BARE_KEY = re.compile(r'^\s*(?P<key>[A-Za-z]\w*)"\s*:\s*(?P<val>.+?)\s*,?\s*$')


def unquote(raw):
    """Turn a value token into a string, escaping quotes the writer left bare."""
    if raw.startswith('"'):
        raw = raw[1:]
    if raw.endswith('"'):
        raw = raw[:-1]
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == "\\" and i + 1 < len(raw):
            out.append(raw[i:i + 2])
            i += 2
            continue
        if c == '"':
            out.append('\\"')
        else:
            out.append(c)
        i += 1
    return json.loads('"' + "".join(out) + '"')


def repair(text):
    data, bad = {}, []
    for num, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        # braces and a comma that wrapped onto its own line carry no record
        if not stripped or re.fullmatch(r"[][{}.,:\s]*", stripped):
            continue
        m = LINE.match(line) or BARE_KEY.match(line)
        if not m:
            bad.append((num, line[:80]))
            continue
        try:
            data[m.group("key")] = unquote(m.group("val"))
        except Exception as exc:
            bad.append((num, "%s / %r" % (exc, line[:60])))
    return data, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--group", default="", help="the groups/group_NN.json this shard answers")
    ap.add_argument("--backup", default=".bad")
    args = ap.parse_args()

    text = open(args.src, encoding="utf-8-sig").read()
    clean = None
    try:
        clean = json.loads(text)
        print("%s: already valid JSON" % args.src)
    except Exception as exc:
        print("%s: %s -> repairing line by line" % (args.src, exc))

    if isinstance(clean, dict):
        # A syntactically valid shard can still be missing keys or carry extras, so the
        # alignment check below has to run on this path too (it used to be skipped).
        data, bad = clean, []
    else:
        data, bad = repair(text)
    want = []
    if args.group and os.path.isfile(args.group):
        want = [r["id"] for r in json.load(open(args.group, encoding="utf-8"))]
    missing = [k for k in want if k not in data]
    extra = [k for k in data if want and k not in set(want)]
    empty = [k for k, v in data.items() if not str(v).strip()]

    print("recovered %d records | unparsable lines %d | missing %d | extra %d | empty %d"
          % (len(data), len(bad), len(missing), len(extra), len(empty)))
    for num, why in bad[:10]:
        print("   line %d: %s" % (num, why))
    for k in missing[:10]:
        print("   MISSING key %s" % k)
    if missing or bad or extra or empty:
        print("NOT WRITTEN - needs a re-dispatch or a manual look")
        return 1
    if isinstance(clean, dict):
        print("aligned with %s, nothing to repair" % (args.group or "the group"))
        return 0

    os.rename(args.src, args.src + args.backup)
    with open(args.src, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("wrote %s (original kept as %s%s)" % (args.src, args.src, args.backup))
    return 0


if __name__ == "__main__":
    sys.exit(main())

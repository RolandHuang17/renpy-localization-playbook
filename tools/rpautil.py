"""Archive/AST access for stock Ren'Py distributions (RPA-3.0 + RENPY RPC2).

Verified against Ren'Py 8.4.2 and 8.5.2 distributions.
No renpy import: everything is parsed from bytes with a stub unpickler.
"""

import os
import pickle
import struct
import zlib

MAGIC = b"RENPY RPC2"


class Stub:
    """Stand-in for any pickled engine class we do not need to execute."""

    __stubname__ = "Stub"

    def __new__(cls, *a, **k):
        return object.__new__(cls)

    def __init__(self, *a, **k):
        # REDUCE-built objects (e.g. renpy.astsupport.PyExpr) carry their
        # constructor args here; for PyExpr the source code is args[0].
        if a:
            self._reduce_args = a
        if k:
            self._reduce_kwargs = k

    def __setstate__(self, state):
        parts = []
        if isinstance(state, tuple) and len(state) == 2:
            parts = [p for p in state if isinstance(p, dict)]
        elif isinstance(state, dict):
            parts = [state]
        if parts:
            for p in parts:
                self.__dict__.update(p)
        else:
            self.__dict__["_state"] = state

    def __repr__(self):
        return "<%s %r>" % (self.__stubname__, sorted(self.__dict__.keys()))


_BUILTIN_ALIASES = {
    ("renpy", "revertable.RevertableDict"): dict,
    ("renpy", "revertable.RevertableList"): list,
    ("renpy", "revertable.RevertableSet"): set,
    ("renpy.revertable", "RevertableDict"): dict,
    ("renpy.revertable", "RevertableList"): list,
    ("renpy.revertable", "RevertableSet"): set,
    ("collections", "defaultdict"): __import__("collections").defaultdict,
    ("builtins", "object"): object,
    ("builtins", "str"): str,
    ("builtins", "int"): int,
    ("builtins", "bool"): bool,
    ("builtins", "float"): float,
    ("builtins", "bytes"): bytes,
    ("builtins", "list"): list,
    ("builtins", "dict"): dict,
    ("builtins", "tuple"): tuple,
    ("builtins", "set"): set,
    ("builtins", "frozenset"): frozenset,
    ("builtins", "slice"): slice,
    ("builtins", "complex"): complex,
    ("renpy.python", "revertable_class"): type,
    ("renpy.python", "dict_class"): dict,
    ("renpy.python", "list_class"): list,
    ("renpy.python", "set_class"): set,
}

_stub_cache = {}


def find_class(module, name):
    full = module + "." + name
    key = (module, name)
    if key in _BUILTIN_ALIASES:
        return _BUILTIN_ALIASES[key]
    if full in ("renpy.ast.PyCode", "renpy.astsupport.PyExpr"):
        # handled by callers through .__dict__ / REDUCE args
        pass
    if full not in _stub_cache:
        _stub_cache[full] = type(
            "Stub_" + name.replace(".", "_"), (Stub,), {"__stubname__": full}
        )
    return _stub_cache[full]


class StubUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        return find_class(module, name)

    def persistent_load(self, pid):
        return None


def load_stub(obj_bytes):
    return StubUnpickler(__import__("io").BytesIO(obj_bytes)).load()


class RPA3(object):
    """Read-only RPA-3.0 archive."""

    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        header = self.f.readline()
        if not header.startswith(b"RPA-3.0"):
            raise ValueError("not RPA-3.0: %s" % header[:32])
        fields = header.decode("latin1").split()[1:]
        self.index_offset = int(fields[0], 16)
        self.key = int(fields[1], 16) if len(fields) > 1 else 0
        self.f.seek(self.index_offset)
        blob = self.f.read()
        self.index = pickle.loads(zlib.decompress(blob))

    def names(self):
        return list(self.index.keys())

    def ranges(self, name):
        """Return list of (start, length) real byte ranges for a file name."""
        out = []
        for entry in self.index.get(name, []):
            offset, size = entry[0] ^ self.key, entry[1] ^ self.key
            skip = len(entry[2]) if len(entry) > 2 else 0
            out.append((offset + skip, size))
        return out

    def read(self, name):
        ranges = self.ranges(name)
        if not ranges:
            raise KeyError(name)
        chunks = []
        for start, size in ranges:
            self.f.seek(start)
            chunks.append(self.f.read(size))
        return b"".join(chunks)

    def close(self):
        try:
            self.f.close()
        except Exception:
            pass


def rpc2_slots(raw):
    """Yield (slot, payload_bytes) for a .rpyc blob, slot 2 first (post-restructure)."""
    if not raw.startswith(MAGIC):
        return []
    out = []
    pos = len(MAGIC)
    while pos + 12 <= len(raw):
        slot, start, length = struct.unpack_from("<iii", raw, pos)
        pos += 12
        if slot == 0:
            break
        if start <= 0 or length <= 0:
            continue
        try:
            payload = zlib.decompress(raw[start : start + length])
        except zlib.error:
            continue
        out.append((slot, payload))
    out.sort(key=lambda t: -t[0])  # slot 2 before slot 1
    return out


def load_script(raw):
    """Unpickle a .rpyc into (data, stmts); prefers slot 2."""
    for slot, payload in rpc2_slots(raw):
        try:
            return load_stub(payload)
        except Exception:
            continue
    return None


# Fields that may hold child nodes / code objects in engine AST + SL2 nodes.
CHILD_FIELDS = (
    "block",
    "children",
    "statements",
    "true",
    "false",
    "second",
    "body",
    "items",
    "child",
    "code",
    "screen",
    "hidden",
    "showif",
    "on",
    "key",
    "input",
    "keyboard",
    "predicate",
    "conditional",
)


def iter_nodes(node, seen=None, depth=0):
    """Depth-first walk over Stub / list / dict / tuple graphs."""
    if seen is None:
        seen = set()
    if node is None or depth > 60:
        return
    oid = id(node)
    if oid in seen:
        return
    seen.add(oid)
    yield node
    if isinstance(node, (list, set, frozenset, tuple)):
        for v in node:
            for g in iter_nodes(v, seen, depth + 1):
                yield g
        return
    d = getattr(node, "__dict__", None)
    if isinstance(d, dict):
        for k, v in list(d.items()):
            for g in iter_nodes(v, seen, depth + 1):
                yield g
            if k in CHILD_FIELDS and isinstance(v, (list, tuple)):
                pass


def node_type(node):
    return getattr(node, "__stubname__", type(node).__name__)


def pycode_source(obj):
    """Extract python source text from PyCode / PyExpr / raw strings."""
    if obj is None or isinstance(obj, str):
        return obj
    name = node_type(obj)
    d = getattr(obj, "__dict__", {}) or {}
    ra = d.get("_reduce_args")
    if name == "renpy.astsupport.PyExpr":
        if ra and isinstance(ra[0], str):
            return ra[0]
        st = d.get("_state")
        if isinstance(st, tuple) and st and isinstance(st[0], str):
            return st[0]
        return None
    if name == "renpy.ast.PyCode":
        st = d.get("_state")
        if isinstance(st, tuple):
            for cand in st:
                if isinstance(cand, str) and ("_" in cand or "(" in cand):
                    # PyCode.__getstate__ = (1, <PyExpr|str>, loc, mode, py, hash, col)
                    return cand
                if isinstance(cand, tuple):
                    for c2 in cand:
                        if isinstance(c2, str) and "(" in c2:
                            return c2
            if len(st) > 1 and isinstance(st[1], str):
                return st[1]
            if len(st) > 1:
                inner = pycode_source(st[1])
                if inner:
                    return inner
        for key in ("code", "py", "source"):
            if isinstance(d.get(key), str):
                return d[key]
    if ra:
        for cand in ra:
            if isinstance(cand, str) and "(" in cand:
                return cand
    return None


def archives_with_scripts(game_dir, skip_sizes_gb=3.0):
    """Return RPA paths that plausibly hold .rpyc, cheapest first.

    Huge media archives are skipped by size unless they contain .rpyc names.
    """
    out = []
    for root, dirs, files in os.walk(game_dir):
        dirs[:] = [d for d in dirs if d not in ("cache", "saves", "tl")]
        for fn in files:
            if fn.endswith(".rpa"):
                out.append(os.path.join(root, fn))
    out.sort(key=lambda p: os.path.getsize(p))
    return out

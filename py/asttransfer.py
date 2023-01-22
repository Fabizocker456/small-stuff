# converts a python ast to/from s-expression

import ast, asdl, marshal, pickle
import typing
import s
import hashlib
import sys

__version__ = "0.1.0"
sl, sd = (s.s_to_py, s.py_to_s)
astast = asdl.parse("./Python.asdl")
with open("./Python.asdl", "rb") as fi:
    astver = hashlib.sha256(fi.read()).hexdigest()
no, opt, seq = range(3)


def type_by_name(inp: str) -> asdl.Sum | asdl.Product:
    if inp not in astast.types:
        raise NameError(f"Cannot find type {inp!r}")
    return astast.types[inp]


def dump_item(item: typing.Any, kind: str) -> s.se_type:
    if kind == "int":
        return str(item)
    if kind in ("string", "identifier"):
        return item
    if kind == "constant":
        p = ""
        try:
            p = "m_" + marshal.dumps(item).hex()
        except:
            p = "p_" + pickle.dumps(item).hex()
        return p
    else:
        return dump_node(item, kind)


def dump_single(item: typing.Any, kind: asdl.Field) -> s.se_type:
    if kind.opt and item is None:
        return ()
    if kind.seq:
        return tuple((dump_item(i, kind.type) for i in item))
    return dump_item(item, kind.type)


def dump_node(item: ast.AST, kind: str) -> s.se_type:
    tp = type_by_name(kind)
    if isinstance(tp, asdl.Product):
        q = []
        for f in tp.fields:
            assert f.name
            c = getattr(item, f.name)
            q.append(dump_single(c, f))
        if not len(tp.attributes):
            return tuple(q)
        at = []
        for f in tp.attributes:
            assert f.name
            c = getattr(item, f.name)
            at.append(dump_single(c, f))
        q.append(tuple(at))
        return tuple(q)
    q = []
    nm = type(item).__name__
    q.append(nm)
    c = None
    for i in tp.types:
        if i.name == nm:
            c = i
            break
    if c is None:
        raise TypeError(f"{nm!r} is not a constructor of {kind!r}")
    for f in c.fields:
        assert f.name
        elem = getattr(item, f.name)
        q.append(dump_single(elem, f))
    if not len(tp.attributes):
        return tuple(q)
    at = []
    for i in tp.attributes:
        assert i.name
        el = getattr(item, i.name)
        at.append(dump_single(el, i))
    q.append(tuple(at))
    return tuple(q)


def load_item(inp: s.se_type, kind: str):
    if kind == "int":
        assert isinstance(inp, str)
        return int(inp)
    if kind in ("string", "identifier"):
        assert isinstance(inp, str)
        return inp
    if kind == "constant":
        assert isinstance(inp, str)
        if inp.startswith("m_"):
            return marshal.loads(bytes.fromhex(inp[2:]))
        elif inp.startswith("p_"):
            return pickle.loads(bytes.fromhex(inp[2:]))
        else:
            raise ValueError(f"Invalid constant prefix: {inp}")
    return load_node(inp, kind)


def load_node(inp: s.se_type, kind: str) -> ast.AST:
    il = list(inp)
    tp = type_by_name(kind)
    attr, fields = (None, None)
    mnm = kind
    if isinstance(tp, asdl.Product):
        attr = tp.attributes
        fields = tp.fields
    else:
        mnm = il.pop(0)
        assert isinstance(mnm, str)
        attr = tp.attributes
        for i in tp.types:
            if i.name == mnm:
                fields = i.fields
                break
        if fields is None:
            raise TypeError(f"{mnm!r} is not a constructor of {kind!r}")
    node = getattr(ast, mnm)()
    for i in fields:
        c = load_single(il.pop(0), i)
        assert i.name
        setattr(node, i.name, c)
    if len(attr):
        at = list(il.pop(0))
        for i in attr:
            c = load_single(at.pop(0), i)
            assert i.name
            setattr(node, i.name, c)
    return node


def load_single(inp: s.se_type, kind: asdl.Field):
    if kind.opt and inp == ():
        return None
    if kind.seq:
        return [load_item(i, kind.type) for i in inp]
    return load_item(inp, kind.type)


def dumps(inp: ast.AST, /, *, indent: str | int | None = None) -> str:
    return sd(("AST", (__version__, astver), dump_node(inp, "mod")), indent=indent)


def loads(inp: str) -> ast.AST:
    c = sl(inp)
    if c[0] != "AST" or c[1] != (__version__, astver):
        raise ValueError("Invalid or outdated AST")
    return load_node(c[2], "mod")


if __name__ == "__main__":
    with open(sys.argv[1], "r") as fi:
        tx = fi.read()
    if sys.argv[1].endswith(".py"):
        at = ast.parse(tx, "exec")
        print(dumps(at, indent=2))
    else:
        at = loads(tx)
        print(ast.dump(at))

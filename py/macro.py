import ast
from os import path
import typing
import tokenize, io

macros = {"expr": {}, "stmt": {}, "tok": {}}

def macro(arg: str, type: typing.Literal["stmt"]
                        | typing.Literal["expr"]
                        | typing.Literal["tok"] = "expr"):
    return lambda fn: macros[type].update({"mac_" + arg: fn})

def import_with_macros(file: str):
    with open(file, "r") as strm:
        code = strm.read()
    tok = tokenize.tokenize(io.BytesIO(code.encode("utf8")).readline)
    tok = list(tok)[::-1]
    nl = []
    while tok:
        cur = tok.pop()
        if cur.type == tokenize.NAME and cur.string in macros["tok"]:
            ch = tok.pop()
            if ch.type == tokenize.OP and ch.string == "(":
                qs = 1
                ls = []
                while qs:
                    c = tok.pop()
                    if c.type == tokenize.OP and c.string == ")":
                        qs -= 1
                    if c.type == tokenize.OP and c.string == "(":
                        qs += 1
                    if qs:
                        ls.append(c)
                ret: list[tokenize.TokenInfo] = list(macros["tok"][cur.string](*ls))
                if ret:
                    nl += [*ret]
            else:
                nl.append(cur)
                nl.append(ch)
        else:
            nl.append(cur)
    ncode = tokenize.untokenize(nl)
    nodes = ast.parse(ncode, "exec")
    nodes = MacroExecutor().visit(nodes)
    ast.fix_missing_locations(nodes)
    exec(compile(nodes, path.realpath(file), "exec"))

class MacroExecutor(ast.NodeTransformer):
    def visit_Call(self, arg: ast.Call) -> ast.expr:
        self.generic_visit(arg)
        match arg:
            case ast.Call(func = ast.Name(id = name)):
                if name not in macros["expr"] or name in macros["stmt"]:
                    return arg
                func = macros["expr"][name]
                kws = {}
                for i in arg.keywords:
                    if i.arg:
                        kws[i.arg] = i.value
                    else:
                        kws["star"] = i.value
                return func(*arg.args, **kws)
            case o:
                return o
    def visit_Expr(self, node: ast.Expr) -> ast.stmt:
        self.generic_visit(node)
        match node:
            case ast.Expr(value = ast.Call(func = ast.Name(id = name))):
                val = node.value
                assert isinstance(val, ast.Call) # calms pyright
                if name not in macros["stmt"]:
                    return node
                fn = macros["stmt"][name]
                kws = {}
                for i in val.keywords:
                    if i.arg:
                        kws[i.arg] = i.value
                    else:
                        kws["star"] = i.value
                return fn(*val.args, **kws)
            case o:
                return o

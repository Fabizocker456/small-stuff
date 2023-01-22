# A small S-expression parser.
#
# usage:
# 
# import s
# print(s.py_to_s(("a", "b", "c")))
#
# TODO: locate and squish bugs

se_type = str | tuple["se_type", ...]

cm = {"x": 2, "u": 4, "U": 8}


def s_to_py(inp: str) -> tuple[se_type, ...]:
    stack = []
    q = list(inp)[::-1]
    quot = ""
    while q:
        cur = q.pop()
        if cur.isspace():
            continue
        if cur == ";":
            while q and q[-1] != "\n":
                q.pop()
            continue
        if cur == "(":
            stack.append([])
            continue
        if cur == ")":
            if len(stack) == 1:
                return tuple(stack.pop())
            stack[-2].append(tuple(stack.pop()))
            continue
        if cur in "'\"":
            cs = ""
            quot = cur
            while q:
                cur = q.pop()
                if cur == quot:
                    break
                if cur == "\\":
                    es = q.pop()
                    if es == "n":
                        cs += "\n"
                    elif es in cm:
                        c = ""
                        for _ in range(cm[es]):
                            c += q.pop()
                        c = int(c, base=16)
                        cs += chr(c)
                    else:
                        cs += es
                else:
                    cs += cur
            stack[-1].append(cs)
            continue
        cs = cur
        while not q[-1].isspace() and q[-1] not in ["(", ")", ";"]:
            cs += q.pop()
        stack[-1].append(cs)
    raise Exception("Brackets don't close correctly")


def _escape_str(inp: str):
    c = '"'
    for i in inp:
        if i == "\n":
            c += "\\n"
        elif ord(i) < ord(" ") or ord(i) > ord("~"):
            if ord(i) < 0x100:
                c += f"\\x{ord(i):02x}"
            elif ord(i) < 0x10000:
                c += f"\\u{ord(i):04x}"
            else:
                c += f"\\U{ord(i):08x}"
        elif i == '"':
            c += '\\"'
        else:
            c += i
    return c + '"'


def py_to_s(inp: se_type, /, *, indent: int | str | None = None) -> str:
    ss = []
    if isinstance(indent, int):
        indent = " " * indent
    for i in inp:
        if isinstance(i, tuple):
            ss.append(py_to_s(i, indent=indent))
            continue
        assert isinstance(i, str)
        c = False
        for j in i:
            if j.isspace() or j in "()\"'":
                c = True
            if ord(j) < ord(" ") or ord(j) > ord("~"):
                c = True
        if not c:
            ss.append(i)
            continue
        ss.append(_escape_str(i))
    if indent is None:
        return "(" + " ".join(ss) + ")"
    else:
        if len(ss) == 0:
            return "()"
        if len(ss) == 1:
            return f"({ss[0]})"
        ret = "("
        for i in ss:
            for j in i.split("\n"):
                ret += f"\n{indent}{j}"
        return ret + "\n)"

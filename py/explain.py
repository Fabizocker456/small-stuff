import ast, dis
import typing, types

ops: dict[str, str] = {
    "RESUME": "starts execution",
    "RETURN_VALUE": "returns the top of stack and terminates execution",
    "LOAD_CONST": "loads a constant onto stack",
    "LOAD_NAME": "loads a variable onto stack",
    "NOP": "does absolutely nothing",
    "PUSH_NULL": "pushes the special NULL value onto the stack",
    "CALL": "calls the top of stack with the specified number of arguments",
    "POP_TOP": "pops the top of stack",
    "JUMP_BACKWARD": "jumps backwards",
    "END_FOR": "pops the top of stack twice",
    "COPY": "duplicates the item at the stack depth pointed at onto the stack",
    "SWAP": "swaps the top of stack with the item pointed at",
    "UNARY_POSITIVE": "applies the unary + operator onto top of stack",
    "UNARY_NEGATIVE": "applies the unary - operator onto top of stack",
    "POP_JUMP_IF_TRUE": "pops the top of stack, jumps if it's True",
    "POP_JUMP_IF_NONE": "pops the top of stack, jumps if it's None",
}


def explain_bytecode(code: str):
    co = compile(code, "<dis>", "exec")
    dis.dis(co)
    inst = list(dis.get_instructions(co))
    for i in inst:
        print(i.opname, i.arg if i.arg is not None else "")
        print("-", ops[i.opname] if i.opname in ops else "<unknown purpose>")
        if i.is_jump_target:
            print(f"- *{i.offset:x}")
        if i.opcode < dis.HAVE_ARGUMENT:
            continue
        else:
            assert i.arg is not None
        if i.opname == "LOAD_ATTR":
            pass
        elif i.opcode in dis.hasjrel:
            assert i.arg
            if i.opname in ("JUMP_BACKWARD", "JUMP_BACKWARDS_NO_INTERRUPT"):
                tar = i.offset - 2 * (i.arg - 1)
            else:
                tar = i.offset + 2 * (i.arg + 1)
            print(f"- jump target: *{tar:x}")
        elif i.opcode in dis.hasname:
            print(i.arg, co.co_names, i.opname)
            print(f"- name: {co.co_names[i.arg]!r}")
        elif i.opcode in dis.hascompare:
            print(f"- comparison: {dis.cmp_op[i.arg]!r}")


def explain_ast(code: str):
    co = ast.parse(code, "exec")


with open(__file__, "r") as fi:
    explain_bytecode(fi.read())

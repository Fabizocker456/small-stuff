import wave
import math
import sys
import re

WAVE="squ"

nftob = lambda i: int(((1 << 16) - 1) * i)
tobt = lambda i: int.to_bytes(i - (1 << 15), 2, "little", signed=True)

nfuns = {
    "sin": lambda i: 0.5 * (math.sin(math.pi * 2 * i) + 1),
    "squ": lambda i: 1 if i % 1 <= 0.5 else 0,
    "saw": lambda i: i % 1,
    "tri": lambda i: 2 * min(i%1, 1-i%1)
}

nfun = nfuns[WAVE]

SQ12 = 2 ** (1/12)
OFFSET = -9

HERTZ=44100
LOUDNESS = 0.2

gauss = lambda i: math.e ** -(i ** 2)

def note(x: int):
    global OFFSET
    return round(440 * SQ12 ** (x + OFFSET))

def tokenize(inp: str) -> list[str]:
    def notize(i):
        return str(note(int(i.group(1))))
    inp = re.sub(r"n\((-?[0-9]+)\)", notize, inp)
    toks = []
    inint = False
    cur = ""
    for i in inp:
        if i in "\n\t ":
            if inint:
                toks.append(cur)
                cur = ""
            inint = False
        elif i in "0123456789":
            cur += i
            inint = True
        elif i == "=":
            if inint:
                toks.append(cur)
                cur = ""
            inint = False
            toks.append("=")
        elif i == "@":
            if inint:
                toks.append(cur)
                cur = ""
            inint = False
            toks.append("@")
        elif i == "$":
            if inint:
                toks.append(cur)
                cur = ""
            inint = False
            toks.append("$")
    return toks

ix2t = lambda i: i / HERTZ
t2ix = lambda i: int(i * HERTZ)

def to_notes(inp: list[str]) -> list[tuple[float, float, int, float]]:
    notes = []
    bpm = int(inp.pop(0))
    slen = 60 / bpm
    ct = 0.0
    ld = None

    while inp:
        if inp[0] == "$":
            inp.pop(0)
            x = inp.pop(0)
            a, b, c, _ = notes[-1]
            notes.append((a, b, c * 2, int(x) / 100))
            continue
        if inp[0] == "@":
            inp.pop(0)
            x = inp.pop(0)
            ld = int(x) / 100
            continue
        fq = int(inp.pop(0))
        tm = int(inp.pop(0))
        if ld is not None:
            notes.append((ct, ct + tm * slen, fq, ld))
            ld = None
        else:
            notes.append((ct, ct + tm * slen, fq, LOUDNESS))
        ct += slen * tm
        if inp and inp[0] == "=":
            inp.pop(0)
            ct = notes[-1][0]
    return notes

def to_file(inp: list[tuple[float, float, int, float]], name: str, pop = False):
    f = wave.open(name, "wb")
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(HERTZ)
    dur = max(inp, key=lambda i: i[1])[1]
    print("duration", dur)
    d = [0.0] * int(dur * HERTZ)
    for st, et, fq, l in inp:
        if not fq: continue
        for i in range(t2ix(st), t2ix(et)):
            d[i] += l * nfun(ix2t(i-st) * fq)
    for ix, i in enumerate(d):
        d[ix] = max(0, min(1, i))
    for i in d:
        f.writeframesraw(tobt(nftob(i)))
    f.close()
    
    if not pop:
        return
    for i in range(len(d) - 1):
        if abs(d[i] - d[i+1]) > 0.025:
            print("potential pop:", ix2t(i))

if __name__ == "__main__":
    with open(sys.argv[1], "r") as fi:
        print(t := tokenize(fi.read()))
    print(n := to_notes(t))
    to_file(n, sys.argv[2], "--pop" in sys.argv)

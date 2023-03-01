# PC Screen Font renderer
# Usage: psf.py <filename>.psf <outfile>.png [0x<foreground color as hex> [0x<background color as hex>]]
# reads input from stdin, renders it, writes it to outfile
# TODO: use PIL

import png
import sys
import readline

assert readline # calms pyright

GLYPH_YES = "\u2588\u2588"
GLYPH_NO = "  "

u32_le = lambda x: (int.from_bytes(x[:4], "little", signed=False), x[4:])
u16_le_t = lambda x: int.to_bytes(x, 2, "little", signed=False)
u32_le_t = lambda x: int.to_bytes(x, 4, "little", signed=False)

class Glyph:
    def __init__(self, bits: list[list[bool]]):
        self.h = len(bits)
        self.w = len(bits[0])
        for i in bits:
            if len(i) != self.w:
                raise ValueError("All lines must be the same length")
        self.bits = bits
        self.seq: list[str] = []

    @classmethod
    def from_bytes(cls, w: int, h: int, buf: bytes):
        aw = (w + 7) // 8
        cbuf = [buf[i * aw : (i + 1) * aw] for i in range(h)]
        ls: list[list[bool]] = []
        for ln in cbuf:
            cc = []
            for b in ln:
                for i in range(8):
                    cc.append(bool(b & (128 >> i)))
            cc = cc[:w]
            ls.append(cc)
        return cls(ls)

    def __str__(self):
        b = ""
        for l in self.bits:
            for c in l:
                b += GLYPH_YES if c else GLYPH_NO
            b += "\n"
        return b[:-1]

    def __repr__(self):
        return f"""Glyph({self.seq}, \"\"\"
{str(self)}
\"\"\")"""

    def to_bytes(self, size: int | None = None):
        ret: bytes = b""
        for i in self.bits:
            ls = i[:]
            if len(ls) % 8:
                ls += [False] * (8 - len(ls) % 8)
            for i in range(len(ls) // 8):
                a, b, c, d, e, f, g, h = ls[i * 8: i * 8 + 8]
                n = a << 7 | b << 6 | c << 5 | d << 4 | e << 3 | f << 2 | g << 1 | h
                ret += bytes([n])

        if size is None:
            return ret
        if len(ret) < size:
            ret += b"\x00" * (size - len(ret))
        elif len(ret) > size:
            raise OverflowError(f"Glyph too big to be represented in {size} bytes: {len(ret)}")
        return ret


class PsfFile:
    @classmethod
    def from_bytes(cls, fi: bytes):
        ret = cls()
        if fi[:2] == b"\x36\x04":
            mv = 1
        elif fi[:4] == b"\x72\xb5\x4a\x86":
            mv = 2
        else:
            raise ValueError("Invalid PSF file: bad magic number")
        if mv == 1:
            ret.parse_v1(fi[2:])
        else:
            ret.parse_v2(fi[4:])
        return ret

    def __init__(self) -> None:
        self.glyphs: list[Glyph] = []

    def parse_v2(self, code: bytes):
        self.version, code = u32_le(code)
        hsiz, code = u32_le(code)
        dt = code[hsiz - 12 :]
        mode, code = u32_le(code)
        self.do_tab = bool(mode & 1)
        self.chars, code = u32_le(code)
        self.charsz, code = u32_le(code)
        self.charh, code = u32_le(code)
        self.charw, code = u32_le(code)
        self.parse_glyphs(dt[: self.charsz * self.chars])
        if self.do_tab:
            self.parse_tab_v2(dt[self.charsz * self.chars :])

    def parse_v1(self, code: bytes):
        self.version = -1
        mode = code[0]
        self.do_tab = True
        if bool(mode & 0x2) == bool(mode & 0x4):
            self.do_tab = False
        if mode & ~7:
            raise ValueError("Only the last 3 bits should be set")
        self.chars: int = 256
        if mode & 0x1:
            self.chars = 512
        self.charh: int = code[1]
        self.charw: int = 8
        self.charsz = self.charh
        self.parse_glyphs(code[2 : 2 + self.charh * self.chars])
        if self.do_tab:
            self.parse_tab_v1(code[2 + self.charh * self.chars :], mode)

    def parse_glyphs(self, data: bytes):
        self.glyphs: list[Glyph] = []

        for i in range(self.chars):
            self.glyphs.append(
                Glyph.from_bytes(
                    self.charw,
                    self.charh,
                    data[self.charsz * i : self.charsz * (i + 1)],
                )
            )

    def parse_tab_v1(self, data: bytes, mode: int):
        cq = [
            int.from_bytes(data[i : i + 2], "little", signed=False)
            for i in range(0, len(data), 2)
        ]
        chrs = [[]]
        for i in cq:
            chrs[-1].append(i)
            if i == 0xFFFF:
                chrs.append([])
        chrs = chrs[:-1]
        for c, g in zip(chrs, self.glyphs):
            sk = []
            # haha consuming iterators
            i = iter(c)
            q = 0
            for n in i:
                if n in (0xFFFF, 0xFFFE):
                    q = n
                    break
                sk.append(chr(n))
            if q & 1:
                g.seq = sk
                continue
            if not mode & 0x4:
                raise ValueError(
                    "The mode specifies exclusively single-character glyphs, yet sequences are present"
                )
            cs = ""
            q = 0
            for n in i:
                if i == 0xFFFF:
                    break
                if i == 0xFFFE:
                    sk.append(cs)
                    cs = ""
                    continue
                cs += chr(n)
            sk.append(cs)
            g.seq = sk

    def parse_tab_v2(self, code: bytes):
        ls = [i.split(b"\xfe") for i in code.split(b"\xff")]
        for bt, gl in zip(ls, self.glyphs):
            if not bt:
                continue
            for i in bt[0].decode("utf8"):
                gl.seq.append(i)
            for i in bt[1:]:
                gl.seq.append(i.decode("utf8"))

    def seek_char(self, chr: str):
        if not self.do_tab:
            raise ValueError("Font does not contain a table")
        for i in self.glyphs:  # find char
            if chr in i.seq:
                return i
        for i in self.glyphs:  # find "�"
            if "\ufffd" in i.seq:
                return i
        raise ValueError(f"Cannot seek character {chr}: no fallback present")

    def render(self, text: str) -> list[Glyph | int]:
        ls = []
        while text:
            nl = False
            if ord(text[0]) < ord(" "):
                ls.append(ord(text[0]))
                text = text[1:]
                continue
            for i in self.glyphs:
                for j in i.seq:
                    if text.startswith(j):
                        ls.append(i)
                        text = text[len(j) :]
                        nl = True
                        break
                if nl:
                    break
            if nl:
                continue
            for i in self.glyphs:
                if "\ufffd" in i.seq:
                    ls.append(i)
                    break
            else:
                raise ValueError(
                    f"Cannot seek character {text[0]}: no fallback present"
                )
        return ls

    def to_bitmap(self, inp: list[Glyph | int]) -> list[list[bool]]:
        lq: list[list[Glyph]] = [[]]
        for i in inp:
            if isinstance(i, Glyph):
                lq[-1].append(i)
            elif i == 10:
                lq.append([])
        col = len(max(lq, key=len)) * self.charw
        for i in lq:
            while len(i) * file.charw < col:
                i.append(file.seek_char(" "))
        bits = []
        for i in lq:
            for j in range(file.charh):
                bits.append([])
                for k in i:
                    bits[-1] += k.bits[j]
        return bits

    def to_file(self, force_v2 = False):
        if force_v2 or self.charw != 8 or len(self.glyphs) not in (256, 512):
            # return self.to_file_v2
            pass
        return self.to_file_v1()

    def to_file_v1(self) -> bytes:
        ret = b"\x36\x04"
        if len(self.glyphs) == 256:
            mode = 0x04
        elif len(self.glyphs) == 512:
            mode = 0x04 | 0x01
        else:
            raise ValueError(f"PSF v1 font must contain 256 or 512 glyphs, this font contains {len(self.glyphs)}")
        ret += bytes([mode])
        if self.charw != 8:
            raise ValueError(f"PSF v1 font must have 8 pixel wide glyphs, not {self.charw}")
        ret += bytes([self.charh])
        return ret

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as fi:
        data = fi.read()
    file = PsfFile.from_bytes(data)
    txt = ""
    while True:
        try:
            txt += input() + "\n"
        except EOFError:
            break
    txt = txt[:-1]
    data = file.render(txt)
    if len(data) >= 2 and data[-1] == 10:
        data.pop()
    sv = []
    bg = [0, 0, 0]
    fg = [255, 255, 255]
    if len(sys.argv) > 3:
        num = int(sys.argv[3], base=16)
        fg = [(num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff]
        print("fg", fg)
    if len(sys.argv) > 4:
        num = int(sys.argv[4], base=16)
        bg = [(num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff]
        print("bg", bg)
    r, g, b, = fg
    r2, g2, b2 = bg
    for i in file.to_bitmap(data):
        x = []
        for j in i:
            if j:
                x += fg
            else:
                x += bg
        sv.append(x)

    png.from_array(sv, mode="RGB").save(sys.argv[2])

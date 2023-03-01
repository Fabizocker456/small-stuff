# Makes random images black-and-white
# usage: decolor.py <input.png> <output.png>...
# (can make multiple outputs from same image)
# TODO: improve performance

import png
import sys
import random

rd = png.Reader(filename=sys.argv[1])

gamma = lambda r, g, b, a: (r + g + b) / 3 * (a / 255) / 255

w, h, d, i = rd.asRGBA8()
d = list(map(list, d))
print(i)
print(w, "×", h)

rnd = lambda: random.randint(0, 0xffffffff) / 0xffffffff

for i in sys.argv[2:]:

    img = []

    for row in d:
        img.append([])
        pixel = []
        for value in row:
            pixel.append(value)
            if len(pixel) < 4: continue
            img[-1].append(255 if gamma(*pixel) > rnd() else 0)
            pixel = []
    
    # calms pyright
    wr = png.Writer.__call__(width = w, height = h, greyscale=True)
    with open(i, "wb") as f:
        wr.write(f, img)
    print(i, "done")


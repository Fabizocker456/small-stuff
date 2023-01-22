# Small tool for ANSI terminal escape codes
# example usage:
#
# print(f"""7
# {esc(red + fg)}red text{no}
# {esc(green + bg}text on green background{no)""")
#
# TODO: more code formats

csi = "\x1b["
fg = 30
bg = 40
black, red, green, yellow, blue, magenta, cyan, white = range(8)

def esc(col):
    return f"{csi}{col}m"

no = esc(0)

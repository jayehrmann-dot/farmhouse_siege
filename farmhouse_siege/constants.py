"""Constants, layout, tuning, palette, scenery and the static map for Farmhouse Siege."""
from collections import deque

W, H = 40, 20                  # playfield in logical cells (1 cell = 2 columns)
FPS = 12
FIELD_TOP = 3                  # terminal row where the playfield starts
NEED_COLS, NEED_ROWS = 82, 26
HX0, HY0, HX1, HY1 = 8, 3, 31, 16      # outer rectangle of the farmhouse
HATCH = (20, 12)
START = (20, 11)
WIN_POS = [(13, 3), (26, 3), (13, 16), (26, 16), (8, 7), (8, 12), (31, 7), (31, 12)]
WIN_NAME = ["NW", "NE", "SW", "SE", "W-UPPER", "W-LOWER", "E-UPPER", "E-LOWER"]
WIN_INDEX = {p: i for i, p in enumerate(WIN_POS)}
D4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
BITE_CD = 18

DIFFS = [
    dict(name="ROOKIE", night=150, spawn=7.5, cap=8, ammo=7, sammo=(1, 1, 0), zmove=8,
         wb=40, hatch=14, block=4, crate=18, crates=3, crate_ammo=3, shp=2, php=4,
         blurb="SLOW GHOULS, STURDY BOARDS, EXTRA ROUNDS."),
    dict(name="FARMHAND", night=210, spawn=7.0, cap=10, ammo=6, sammo=(1, 0, 0), zmove=7,
         wb=36, hatch=10, block=3, crate=26, crates=2, crate_ammo=2, shp=1, php=3,
         blurb="A LONG NIGHT. AMMO IS TIGHT."),
    dict(name="NIGHTMARE", night=240, spawn=5.0, cap=14, ammo=4, sammo=(0, 0, 0), zmove=5,
         wb=28, hatch=7, block=2, crate=38, crates=1, crate_ammo=2, shp=1, php=3,
         blurb="FAST DEAD. WEAK BOARDS. ONE BULLET EACH."),
]

# colours (xterm-256 indices) ------------------------------------------------
BLACK, RED, DKRED, BLOOD, YEL, ORG = 16, 196, 88, 124, 226, 208
GRN, CYA, GREY, DIM, WHITE = 40, 51, 245, 240, 252
AMBIENT = [
    "SOMETHING SCRATCHES AT THE WALL...",
    "A FLOORBOARD CREAKS ABOVE YOU.",
    "THE WIND HOWLS THROUGH THE CRACKS.",
    "SOMEONE IS HUMMING. NOBODY HERE IS HUMMING.",
    "THE CLOCK IS WRONG. IT IS ALWAYS WRONG.",
    "A SHAPE WAITS AT THE TREELINE.",
    "THE DOGS STOPPED BARKING HOURS AGO.",
]


# ---------------------------------------------------------------- the map
def build_map():
    kind = [["yard"] * W for _ in range(H)]
    for y in range(HY0, HY1 + 1):
        for x in range(HX0, HX1 + 1):
            edge = x in (HX0, HX1) or y in (HY0, HY1)
            kind[y][x] = "wall" if edge else "floor"
    for (x, y) in WIN_POS:
        kind[y][x] = "win"
    kind[HY1][20] = "door"
    for x in range(19, 22):
        kind[4][x] = "fire"
    for y in (8, 9):
        for x in range(18, 22):
            kind[y][x] = "table"
    for x in range(10, 13):
        kind[15][x] = "couch"
    for x in range(27, 31):
        kind[14][x] = "bed"
        kind[15][x] = "bed"
    for x in range(28, 31):
        kind[4][x] = "shelf"
    kind[HATCH[1]][HATCH[0]] = "hatch"
    return kind


KIND = build_map()


def inside_house(x, y):
    return HX0 <= x <= HX1 and HY0 <= y <= HY1


def hpass(n):          # humans: floor and hatch only
    x, y = n
    return 0 <= x < W and 0 <= y < H and KIND[y][x] in ("floor", "hatch")


def ypass(n):          # the yard
    x, y = n
    return 0 <= x < W and 0 <= y < H and KIND[y][x] == "yard"


def bfs(sources, ok):
    dist = {s: 0 for s in sources}
    q = deque(sources)
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in D4:
            n = (x + dx, y + dy)
            if n not in dist and ok(n):
                dist[n] = d
                q.append(n)
    return dist


def _out_in(p):
    x, y = p
    if y == HY0:
        return (x, y - 1), (x, y + 1)
    if y == HY1:
        return (x, y + 1), (x, y - 1)
    if x == HX0:
        return (x - 1, y), (x + 1, y)
    return (x + 1, y), (x - 1, y)


WIN_OUT = [_out_in(p)[0] for p in WIN_POS]
WIN_IN = [_out_in(p)[1] for p in WIN_POS]
FWIN = [bfs([o], ypass) for o in WIN_OUT]       # yard flow fields to each window
FIN = [bfs([i], hpass) for i in WIN_IN]         # house flow fields to each window
FHATCH = bfs([HATCH], hpass)

# scenery -------------------------------------------------------------------
DECOR = {}
for (tx, ty) in [(3, 5), (2, 13), (36, 6), (35, 15), (4, 17), (22, 18), (14, 0), (29, 1)]:
    DECOR[(tx, ty)] = ("\\/", 94)
    if ty + 1 < H:
        DECOR[(tx, ty + 1)] = ("||", 94)
for (gx, gy) in [(34, 18), (2, 2), (6, 9), (37, 11), (11, 18), (30, 18)]:
    DECOR[(gx, gy)] = ("n ", 247)
STARS = [(2, 0), (6, 1), (10, 0), (17, 1), (21, 0), (25, 2), (28, 0), (31, 1), (38, 2), (1, 7)]
MOON = {(34, 0): 230, (35, 0): 187, (34, 1): 230, (35, 1): 230}

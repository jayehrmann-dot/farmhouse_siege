"""Curses drawing for Farmhouse Siege: solid colour blocks, two columns per cell, 2600 style."""
import curses
import random

from .constants import *  # noqa: F401,F403
from .engine import dist


def _rgb(c):
    if c < 16:
        return ((c & 1) * 200 + (c > 7) * 55, ((c >> 1) & 1) * 200 + (c > 7) * 55,
                ((c >> 2) & 1) * 200 + (c > 7) * 55)
    if c < 232:
        c -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return lv[c // 36], lv[(c // 6) % 6], lv[c % 6]
    v = 8 + (c - 232) * 10
    return v, v, v


def to8(c):
    if c < 16:
        return c & 7
    r, g, b = _rgb(c)
    return (1 if r >= 110 else 0) | (2 if g >= 110 else 0) | (4 if b >= 110 else 0)


class Renderer:
    def __init__(self, scr):
        self.scr = scr
        self.cache = {}
        self.big = curses.COLORS >= 256
        self.ox = 0
        self.oy = 0
        self.cells = []

    def layout(self, rows, cols):
        self.ox = max(0, (cols - 80) // 2)
        self.oy = max(0, (rows - 25) // 2)

    def pair(self, fg, bg):
        key = (fg, bg)
        p = self.cache.get(key)
        if p is None:
            idx = len(self.cache) + 1
            if idx >= curses.COLOR_PAIRS:
                return 0
            f, b = (fg, bg) if self.big else (to8(fg), to8(bg))
            curses.init_pair(idx, f, b)
            p = curses.color_pair(idx)
            self.cache[key] = p
        return p

    def begin(self):
        self.cells = [[("  ", 250, BLACK)] * W for _ in range(H)]

    def text(self, row, col, s, fg=250, bg=BLACK, bold=False):
        attr = self.pair(fg, bg) | (curses.A_BOLD if bold else 0)
        try:
            self.scr.addstr(self.oy + row, self.ox + col, s, attr)
        except curses.error:
            pass

    def flush(self):
        for y in range(H):
            row = self.cells[y]
            x = 0
            while x < W:
                _, fg, bg = row[x]
                j = x
                buf = ""
                while j < W and row[j][1] == fg and row[j][2] == bg:
                    buf += row[j][0]
                    j += 1
                self.text(FIELD_TOP + y, x * 2, buf, fg, bg)
                x = j

    def box(self, top, gx0, gx1, lines, fg, centre=True):
        """Draw a solid black text panel over playfield cells gx0..gx1 (inclusive)."""
        width = (gx1 - gx0 + 1) * 2
        for i, ln in enumerate(lines):
            self.text(FIELD_TOP + top + i, gx0 * 2, (ln.center(width) if centre else ln.ljust(width))[:width],
                      fg, BLACK, True)

    # ---- scenes -----------------------------------------------------------
    def draw_field(self, g, lc):
        cells = self.cells
        f = g.frame
        fl = g.flash > 0
        prog = g.prog()
        sky = 243 if fl else 233 + int(prog * 9)
        for y in range(H):
            row = cells[y]
            for x in range(W):
                k = KIND[y][x]
                d2 = (x - lc[0]) ** 2 + (y - lc[1]) ** 2
                if k == "yard":
                    row[x] = ("  ", 250, sky + (y & 1) + (2 if (d2 <= 30 or fl) else 0))
                elif k == "floor":
                    if d2 <= 16 or fl:
                        bg = 59 if y & 1 else 58
                    elif d2 <= 49:
                        bg = 238 if y & 1 else 237
                    else:
                        bg = 235 if y & 1 else 234
                    row[x] = ("  ", 250, bg)
                elif k == "wall":
                    row[x] = ("  ", 250, 88 if (x + y) & 1 else 52)
                elif k == "door":
                    row[x] = ("||", 58, 94)
                elif k == "win":
                    b = g.boards[WIN_INDEX[(x, y)]]
                    if b == 3:
                        row[x] = ("##", 94, 130)
                    elif b == 2:
                        row[x] = ("==", 94, 130)
                    elif b == 1:
                        row[x] = ("--", 130, 94)
                    else:
                        row[x] = (("><" if (f // 3) & 1 else "<>"), RED, 17)
                elif k == "fire":
                    row[x] = (random.choice(("^^", "^~", "~^", "^ ")), random.choice((202, 208, YEL)), 52)
                elif k == "table":
                    row[x] = ("  ", 250, 94)
                elif k == "couch":
                    row[x] = ("  ", 250, 90)
                elif k == "bed":
                    row[x] = ("  ", 250, 24 if y == 14 else 60)
                elif k == "shelf":
                    row[x] = ("||", 130, 58)
                elif k == "hatch":
                    glow = 208 if (g.cellar and (f // 2) & 1) else 214
                    row[x] = ("[]", glow, 94)
        # scenery
        for (x, y), (txt, fg) in DECOR.items():
            if KIND[y][x] == "yard":
                cells[y][x] = (txt, fg, cells[y][x][2])
        for (sx, sy) in STARS:
            if random.random() > 0.12:
                cells[sy][sx] = (". ", 250 if fl else 246, cells[sy][sx][2])
        mcol = 215 if prog > 0.92 else None
        for (mx, my), c in MOON.items():
            cells[my][mx] = ("  ", 250, mcol or c)
        # fog
        for fx, fy, _ in g.fog:
            x, y = int(fx) % W, int(fy) % H
            if KIND[y][x] == "yard":
                cells[y][x] = ("░░", 244 if fl else 239, cells[y][x][2])
        # crates
        for (cx, cy) in g.crates:
            cells[cy][cx] = ("AM", BLACK, 178)
        # survivors
        for s in g.surv:
            if not s.cellar:
                cells[s.y][s.x] = (("(>" if s.ammo > 0 else "()"), BLACK, 123 if s.ammo > 0 else 117)
        # zombies (with Atari-style sprite flicker when a row gets crowded)
        rowcount = {}
        for z in g.zombies:
            n = rowcount.get(z.y, 0)
            rowcount[z.y] = n + 1
            if n >= 3 and (n + f) % 2:
                continue
            under = cells[z.y][z.x]
            d2 = (z.x - lc[0]) ** 2 + (z.y - lc[1]) ** 2
            if d2 <= 49 or fl:
                cells[z.y][z.x] = ("oo", RED, 28)
            elif random.random() > 0.07:
                cells[z.y][z.x] = ("oo", RED, under[2])
        # player
        if not g.demo and not g.cellar and not (g.inv > 0 and (f & 1)):
            cells[g.py][g.px] = ("{}", BLACK, 203 if g.inv > 14 else 229)
        # gunfire
        for path, _ in g.tracers:
            for (tx, ty) in path:
                cells[ty][tx] = ("**", YEL, cells[ty][tx][2])

    def draw_cellar(self, g):
        cells = self.cells
        f = g.frame
        candle = (12, 13)
        flick = random.random() < 0.15
        for y in range(H):
            for x in range(W):
                if y < 2:
                    cells[y][x] = ("  ", 250, 52 if (x + y) & 1 else 88)
                elif x == 0 or x == W - 1 or y == H - 1:
                    cells[y][x] = ("  ", 250, 59 if (x + y) & 1 else 60)
                else:
                    d = min(dist((x, y), candle), dist((x, y), (20, 8)) + 3)
                    lvl = 235 if d > 12 else 236 if d > 8 else 58 if d > 5 else 94
                    if flick and d < 12:
                        lvl -= 1
                    cells[y][x] = ("  ", 250, lvl)
        for x in (19, 20, 21):
            cells[1][x] = ("[]", 214, 94)
        for y in range(2, 7):
            cells[y][20] = ("H=" if y % 2 else "=H", 130, cells[y][20][2])
        for (bx, by) in [(3, 5), (4, 5), (3, 6), (5, 6)]:
            cells[by][bx] = ("()", 94, 58)
        for x in range(33, 38):
            cells[4][x] = ("||", 130, 58)
            cells[5][x] = ("oo" if x % 2 else "o ", random.choice((40, 99, 160)), 58)
        for (cx, cy) in [(1, 2), (W - 2, 2)]:
            cells[cy][cx] = ("\\/", 245, cells[cy][cx][2])
        cells[candle[1]][candle[0]] = (("i " if not flick else "' "), YEL, cells[candle[1]][candle[0]][2])
        cells[candle[1] + 1][candle[0]] = ("[]", 94, 237)
        if random.random() < 0.25:
            ex = random.choice((3, 36, 30, 6))
            cells[17][ex] = ("oo", RED, cells[17][ex][2])
        shift = 1 if g.thump > 0 and (f & 1) else 0
        for y in range(2, 7):
            if shift:
                cells[y][20] = ("  ", 250, cells[y][20][2])
                cells[y][21] = ("H=", 130, cells[y][21][2])
        slots = [(17, 10), (23, 10), (20, 11), (16, 12), (24, 12)]
        k = 0
        for s in g.surv:
            if s.cellar and k < len(slots):
                sx, sy = slots[k]
                k += 1
                cells[sy][sx] = (("(>" if s.ammo > 0 else "()"), BLACK, 123 if s.ammo > 0 else 117)
        cells[9][20] = ("{}", BLACK, 229)
        if g.upshot > 0:
            for y in range(2, 9):
                cells[y][20] = ("**", YEL, 94)

    # ---- drawing: HUD -----------------------------------------------------
    def draw_hud(self, g):
        self.text(0, 1, "FARMHOUSE SIEGE", RED, BLACK, True)
        self.text(0, 34, g.clock().rjust(8), WHITE, BLACK, True)
        self.text(0, 64, "SCORE %06d" % g.score, YEL, BLACK, True)
        c = 1
        segs = [("LIFE ", GREY), ("♥" * g.php, RED),
                ("♡" * (g.d["php"] - g.php), DKRED),
                ("   AMMO ", GREY),
                ("|" * min(g.ammo, 12) + ("+%d" % (g.ammo - 12) if g.ammo > 12 else ""), YEL),
                ("   FOLK ", GREY)]
        for t, col in segs:
            self.text(1, c, t, col)
            c += len(t)
        for s in g.surv:
            self.text(1, c, "()", CYA)
            c += 3
        for _ in range(g.lost):
            self.text(1, c, "xx", DKRED)
            c += 3
        self.text(1, 51, "WINDOWS", GREY)
        c = 59
        for b in g.boards:
            self.text(1, c, str(b) if b else "X", {3: GRN, 2: YEL, 1: ORG, 0: RED}[b], BLACK, b == 0)
            c += 2
        self.text(1, 76 if not g.cellar else 66, "" if not g.cellar else "[CELLAR]", CYA, BLACK, True)
        fill = int(g.prog() * 62)
        col = 25 if g.prog() < 0.4 else 91 if g.prog() < 0.75 else 166 if g.prog() < 0.92 else 214
        self.text(2, 1, "█" * fill, col)
        self.text(2, 1 + fill, "░" * (62 - fill), 238)
        self.text(2, 65, "DAWN", ORG if g.prog() > 0.85 else DIM)
        base = FIELD_TOP + H
        if g.msg_ttl > 0 and g.msg:
            self.text(base, 1, g.msg.center(78)[:78], g.msg_col, BLACK, True)
        self.text(base + 1, 1, "ARROWS/WASD MOVE   SPACE: FIRE/BOARD/SHARE/HATCH   P PAUSE   Q QUIT".center(78),
                DIM)

    def draw(self, g):
        self.begin()
        if g.cellar and not g.demo:
            self.draw_cellar(g)
            self.flush()
            near, blocked = g.hatch_block()
            self.box(8, 14, 25, [
                "THE CELLAR",
                "",
                "ABOVE: %d AT THE HATCH" % near,
                ("PATH BLOCKED!" if blocked else "PATH CLEAR"),
                "",
                ("SPACE: FIRE UP (%d ROUNDS)" % (g.ammo + sum(s.ammo for s in g.surv if s.cellar))
                 if blocked else "SPACE: CLIMB OUT"),
            ], (RED if blocked else CYA))
            hp = max(0, g.hatch_hp)
            bar = "█" * hp + "░" * (g.d["hatch"] - hp)
            self.text(FIELD_TOP + 15, 29, "HATCH " + bar, RED if hp <= 3 else ORG)
        else:
            lc = (g.px, g.py) if not g.demo else (20, 10)
            self.draw_field(g, lc)
            self.flush()
        self.draw_hud(g)



def title_overlay(ui, game, sel, scores):
    f = game.frame
    title = "F A R M H O U S E   S I E G E"
    if random.random() < 0.08:
        i = random.randrange(len(title))
        title = title[:i] + " " + title[i + 1:]
    col = random.choice((RED, RED, 160, 124)) if f % 4 == 0 else RED
    ui.text(FIELD_TOP + 0, (80 - len(title)) // 2, title, col, BLACK, True)
    sub = "SURVIVE UNTIL DAWN"
    ui.text(FIELD_TOP + 1, (80 - len(sub)) // 2, sub, 244)
    lines = ["-- CHOOSE YOUR NIGHT --", ""]
    for i, d in enumerate(DIFFS):
        best = scores.get(d["name"], 0)
        mark = ">" if i == sel else " "
        lines.append("%s %-10s  BEST %06d" % (mark, d["name"], best))
    lines += ["", DIFFS[sel]["blurb"], "",
              "UP/DOWN: SELECT      SPACE: START",
              "BOARD WINDOWS - SHARE AMMO - HIDE IN CELLAR",
              "BUT IF THE HATCH IS BLOCKED... YOU'RE TRAPPED.",
              "Q: QUIT"]
    ui.box(5, 9, 30, lines, WHITE)
    # highlight the selected row
    i = 2 + sel
    ui.text(FIELD_TOP + 5 + i, 18, "%s %-10s  BEST %06d" % (">", DIFFS[sel]["name"], scores.get(DIFFS[sel]["name"], 0)),
            YEL if (f // 4) & 1 else ORG, BLACK, True)


def end_overlay(ui, game, scores):
    d = game.d
    if game.result == "win":
        lines = ["", "* * *  D A W N   B R E A K S  * * *", "",
                 "THE SUN BURNS THE DEAD AWAY.",
                 "SURVIVORS SAVED: %d OF 3" % len(game.surv),
                 "ZOMBIES DOWNED: %d" % game.kills,
                 "BONUS: %d" % game.bonus,
                 "FINAL SCORE: %06d" % game.score]
        col = YEL
    else:
        lines = ["", "T H E   N I G H T   W I N S", "",
                 game.reason[:40], game.reason[40:80] if len(game.reason) > 40 else "",
                 "ZOMBIES DOWNED: %d" % game.kills,
                 "FINAL SCORE: %06d" % game.score, ""]
        col = RED
    best = scores.get(d["name"], 0)
    lines += ["", "BEST (%s): %06d" % (d["name"], best), "", "SPACE: TITLE     Q: QUIT"]
    ui.box(4, 9, 30, lines, col)


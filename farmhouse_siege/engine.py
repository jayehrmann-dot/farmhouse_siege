"""Game rules for Farmhouse Siege. No curses in here so the logic can be tested headless."""
import json
import math
import os
import random

from .constants import *  # noqa: F401,F403
from .constants import HATCH

HIGH_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "highscore.json")


# ---------------------------------------------------------------- helpers
def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def line_cells(a, b):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if (x0, y0) == (x1, y1):
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out[1:-1]



def load_scores():
    """Best score per difficulty name, stored as {"high": {"ROOKIE": 0, ...}}."""
    try:
        with open(HIGH_PATH) as f:
            data = json.load(f).get("high", {})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_scores(scores):
    try:
        with open(HIGH_PATH, "w") as f:
            json.dump({"high": scores}, f)
    except Exception:
        pass


class Zombie:
    __slots__ = ("x", "y", "tw", "cd", "mv")

    def __init__(self, x, y, tw):
        self.x, self.y, self.tw = x, y, tw
        self.cd = random.randint(5, 20)
        self.mv = random.randint(1, 6)


class Survivor:
    __slots__ = ("x", "y", "ammo", "hp", "cd", "mv", "bcd", "cellar")

    def __init__(self, x, y, ammo, hp):
        self.x, self.y, self.ammo, self.hp = x, y, ammo, hp
        self.cd = 0
        self.mv = 0
        self.bcd = 0
        self.cellar = False



# ---------------------------------------------------------------- the game
class Game:
    def __init__(self, di, demo=False):
        self.di = di
        self.d = DIFFS[di]
        self.demo = demo
        self.frame = 0
        self.t = 0
        self.night = self.d["night"] * FPS
        self.boards = [random.choice((2, 3, 3)) for _ in WIN_POS]
        self.px, self.py = START
        self.php = self.d["php"]
        self.ammo = self.d["ammo"]
        self.inv = 0
        self.bcd = 0
        self.mvcd = 0
        self.hold = None
        self.hold_ttl = 0
        self.cellar = False
        self.hatch_hp = self.d["hatch"]
        spots = [(18, 12), (22, 12), (20, 14)]
        self.surv = [Survivor(sx, sy, a, self.d["shp"]) for (sx, sy), a in zip(spots, self.d["sammo"])]
        self.zombies = []
        self.crates = []
        self.tracers = []
        self.kills = 0
        self.score = 0
        self.lost = 0
        self.spawn_cd = 5 * FPS
        self.crate_cd = int(self.d["crate"] * FPS * 0.6)
        self.msg = ""
        self.msg_ttl = 0
        self.msg_col = YEL
        self.thump = 0
        self.upshot = 0
        self.flash = 0
        self.next_flash = random.randint(150, 300)
        self.fog = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.03, 0.12)] for _ in range(16)]
        self.amb_cd = 30 * FPS
        self.result = None
        self.reason = ""
        self.bonus = 0
        self.fh = {}
        self.say("THE SUN SETS. BOARD THE WINDOWS.", 40)
        if demo:
            self.boards = [3, 2, 0, 3, 1, 3, 2, 3]
            for (zx, zy) in [(5, 4), (6, 10), (34, 9), (14, 18), (26, 1), (3, 15), (36, 2)]:
                self.zombies.append(Zombie(zx, zy, 0))

    # ---- small helpers ----------------------------------------------------
    def prog(self):
        return min(1.0, self.t / float(self.night))

    def clock(self):
        m = int(self.prog() * 360)
        h = m // 60
        return "%d:%02d AM" % (12 if h == 0 else h, m % 60)

    def say(self, text, ttl=30, col=YEL):
        self.msg, self.msg_ttl, self.msg_col = text, ttl, col

    def zpass(self, n):
        x, y = n
        if not (0 <= x < W and 0 <= y < H):
            return False
        k = KIND[y][x]
        if k in ("yard", "floor", "hatch"):
            return True
        if k == "win":
            return self.boards[WIN_INDEX[n]] == 0
        return False

    def human_cells(self):
        cells = [(s.x, s.y) for s in self.surv if not s.cellar]
        if not self.cellar:
            cells.append((self.px, self.py))
        return cells

    def free_h(self, n, zset):
        if not hpass(n) or n in zset:
            return False
        if not self.cellar and n == (self.px, self.py):
            return False
        for s in self.surv:
            if not s.cellar and (s.x, s.y) == n:
                return False
        return True

    def add_tracer(self, a, b):
        self.tracers.append([line_cells(a, b), 3])

    def kill_zombie(self, z):
        if z in self.zombies:
            self.zombies.remove(z)
            self.kills += 1
            self.score += 10

    def lose(self, reason):
        if self.result is None:
            self.result = "lose"
            self.reason = reason

    def win(self):
        alive = len(self.surv)
        self.bonus = alive * 250 + self.php * 50 + sum(self.boards) * 5
        self.score += self.bonus
        self.result = "win"

    # ---- player -----------------------------------------------------------
    def handle_keys(self, keys):
        d, pressed = None, False
        for k in keys:
            if k in DIRS:
                d = k
            elif k == "btn":
                pressed = True
        if self.bcd > 0:
            self.bcd -= 1
        if self.mvcd > 0:
            self.mvcd -= 1
        if d and not self.cellar:
            self.hold, self.hold_ttl = d, 2
        if self.hold_ttl > 0 and not self.cellar:
            self.hold_ttl -= 1
            if self.mvcd == 0:
                self.move_player(DIRS[self.hold])
                self.mvcd = 2
        if pressed:
            self.press()

    def move_player(self, dxy):
        n = (self.px + dxy[0], self.py + dxy[1])
        if not hpass(n):
            return
        if any((z.x, z.y) == n for z in self.zombies):
            return
        for s in self.surv:
            if not s.cellar and (s.x, s.y) == n:
                s.x, s.y = self.px, self.py          # swap places
        self.px, self.py = n
        if n in self.crates:
            self.crates.remove(n)
            self.ammo += self.d["crate_ammo"]
            self.say("FOUND AMMO! +%d ROUNDS" % self.d["crate_ammo"], 30, GRN)

    def nearest_zombie(self, pos, rng):
        best, bd = None, rng + 0.01
        for z in self.zombies:
            dd = dist(pos, (z.x, z.y))
            if dd < bd:
                best, bd = z, dd
        return best

    def press(self):
        if self.cellar:
            return self.cellar_press()
        if self.bcd > 0:
            return
        pos = (self.px, self.py)
        if pos == HATCH:
            return self.descend()
        z = self.nearest_zombie(pos, 3.5)
        if z and self.ammo > 0:
            self.ammo -= 1
            self.bcd = 5
            self.add_tracer(pos, (z.x, z.y))
            if random.random() < 0.8:
                self.kill_zombie(z)
                self.say("BANG! ONE LESS.", 18, ORG)
            else:
                self.say("BANG! MISSED!", 18, RED)
            return
        weak = [i for i, b in enumerate(self.boards) if b < 3 and cheb(pos, WIN_POS[i]) <= 1]
        if weak:
            i = min(weak, key=lambda k: self.boards[k])
            if any((z.x, z.y) == WIN_POS[i] for z in self.zombies):
                self.say("A ZOMBIE IS IN THE WINDOW!", 20, RED)
                self.bcd = 5
                return
            self.boards[i] += 1
            self.bcd = 4
            self.say("BOARD NAILED. %s WINDOW %d/3" % (WIN_NAME[i], self.boards[i]), 20, GRN)
            return
        near = [s for s in self.surv if not s.cellar and cheb(pos, (s.x, s.y)) <= 1]
        if near:
            s = near[0]
            self.bcd = 6
            if self.ammo - s.ammo >= 2 or (s.ammo == 0 and self.ammo >= 1):
                self.ammo -= 1
                s.ammo += 1
                self.say("YOU PASS A ROUND TO THE SURVIVOR.", 24, CYA)
            elif s.ammo - self.ammo >= 2 or (self.ammo == 0 and s.ammo >= 1):
                self.ammo += 1
                s.ammo -= 1
                self.say("YOU TAKE A ROUND BACK.", 24, CYA)
            else:
                self.say("YOU AGREE TO SHARE EQUALLY.", 18, CYA)
            return
        self.bcd = 6
        self.say("NOTHING TO DO HERE.", 12, GREY)

    def descend(self):
        self.cellar = True
        self.hatch_hp = min(self.d["hatch"], self.hatch_hp + 2)
        n = 0
        for s in self.surv:
            if not s.cellar and cheb((s.x, s.y), HATCH) <= 3:
                s.cellar = True
                n += 1
        left = len([s for s in self.surv if not s.cellar])
        txt = "DOWN THE HATCH. %d FOLLOW." % n
        if left:
            txt += " %d LEFT UPSTAIRS!" % left
        self.say(txt, 40, CYA)
        self.bcd = 8

    def hatch_block(self):
        near = sum(1 for z in self.zombies if cheb((z.x, z.y), HATCH) <= 2)
        on = any((z.x, z.y) == HATCH for z in self.zombies)
        return near, on or near >= self.d["block"]

    def cellar_press(self):
        if self.bcd > 0:
            return
        near, blocked = self.hatch_block()
        self.bcd = 6
        if blocked:
            giver = None
            if self.ammo > 0:
                giver = "me"
            else:
                for s in self.surv:
                    if s.cellar and s.ammo > 0:
                        giver = s
                        break
            if giver is None:
                self.say("TRAPPED! THE HATCH IS BLOCKED AND YOU HAVE NO AMMO!", 40, RED)
                return
            if giver == "me":
                self.ammo -= 1
            else:
                giver.ammo -= 1
            self.upshot = 4
            tgt = min(self.zombies, key=lambda z: cheb((z.x, z.y), HATCH), default=None)
            if tgt and random.random() < 0.8:
                self.kill_zombie(tgt)
                self.say("YOU FIRE UP THROUGH THE HATCH. ONE FALLS.", 24, ORG)
            else:
                self.say("YOU FIRE BLIND THROUGH THE BOARDS. MISS.", 24, RED)
            return
        self.cellar = False
        self.px, self.py = HATCH
        self.inv = 10
        free = [c for c in bfs([HATCH], hpass) if c != HATCH]
        free.sort(key=lambda c: (cheb(c, HATCH), random.random()))
        zset = {(z.x, z.y) for z in self.zombies}
        k = 0
        for s in self.surv:
            if s.cellar:
                while k < len(free) and free[k] in zset:
                    k += 1
                if k < len(free):
                    s.x, s.y = free[k]
                    k += 1
                else:
                    s.x, s.y = HATCH
                s.cellar = False
        self.say("YOU CLIMB OUT INTO THE DARK.", 30, CYA)

    def bite_player(self):
        if self.inv > 0:
            return
        self.php -= 1
        self.inv = 24
        if self.php <= 0:
            self.lose("YOU WERE BITTEN ONE TIME TOO MANY.")
        else:
            self.say("OUCH! YOU'RE BITTEN!", 30, RED)

    def hurt_survivor(self, s):
        s.hp -= 1
        if s.hp <= 0:
            self.surv.remove(s)
            self.lost += 1
            self.say("A SURVIVOR WAS TAKEN!", 50, RED)
        else:
            self.say("A SURVIVOR IS BITTEN!", 30, RED)

    # ---- zombies ----------------------------------------------------------
    def spawn(self):
        self.spawn_cd -= 1
        if self.spawn_cd > 0:
            return
        breaches = self.boards.count(0)
        iv = self.d["spawn"] * (1 - 0.45 * self.prog()) / (1 + 0.3 * breaches)
        self.spawn_cd = max(6, int(iv * FPS * random.uniform(0.7, 1.3)))
        if len(self.zombies) >= self.d["cap"]:
            return
        tw = random.choices(range(8), [(4 - b) ** 2 for b in self.boards])[0]
        wx, wy = WIN_POS[tw]
        j = random.randint(-8, 8)
        if wy == HY0:
            sx, sy = wx + j, 0
        elif wy == HY1:
            sx, sy = wx + j, H - 1
        elif wx == HX0:
            sx, sy = 0, wy + j
        else:
            sx, sy = W - 1, wy + j
        sx, sy = max(0, min(W - 1, sx)), max(0, min(H - 1, sy))
        if ypass((sx, sy)) and not any((z.x, z.y) == (sx, sy) for z in self.zombies):
            self.zombies.append(Zombie(sx, sy, tw))

    def zombie_attack(self, z, fh):
        pos = (z.x, z.y)
        prey = [s for s in self.surv if not s.cellar and cheb(pos, (s.x, s.y)) <= 1]
        me = (not self.cellar) and cheb(pos, (self.px, self.py)) <= 1
        if prey or me:
            if z.cd <= 0:
                z.cd = BITE_CD
                if me and (not prey or random.random() < 0.5):
                    self.bite_player()
                else:
                    self.hurt_survivor(random.choice(prey))
            return True
        if self.cellar and cheb(pos, HATCH) <= 1:
            if z.cd <= 0:
                z.cd = 20
                self.hatch_hp -= 1
                self.thump = 6
                self.say("THUMP! THE HATCH SPLINTERS!", 14, RED)
            return True
        if KIND[z.y][z.x] == "yard" and pos not in fh:
            i = z.tw
            if self.boards[i] > 0 and cheb(pos, WIN_POS[i]) <= 1:
                if z.cd <= 0:
                    z.cd = self.d["wb"] + random.randint(0, 8)
                    self.boards[i] -= 1
                    if self.boards[i] == 0:
                        self.say("%s WINDOW BREACHED!" % WIN_NAME[i], 50, RED)
                    else:
                        self.say("CRACK! A BOARD GIVES WAY AT %s." % WIN_NAME[i], 16, ORG)
                return True
        return False

    def move_zombie(self, z, fh, occ):
        pos = (z.x, z.y)
        field = fh
        d = fh.get(pos)
        if d is None:
            field = FWIN[z.tw]
            d = field.get(pos)
            if d is None:
                return
        nb = [(pos[0] + dx, pos[1] + dy) for dx, dy in D4]
        random.shuffle(nb)
        opts = [n for n in nb if field.get(n, 9999) < d and n not in occ and self.zpass(n)]
        if not opts and random.random() < 0.5:
            opts = [n for n in nb if field.get(n, 9999) == d and n not in occ and self.zpass(n)]
        if opts:
            occ.discard(pos)
            z.x, z.y = opts[0]
            occ.add(opts[0])

    def update_zombies(self, fh):
        occ = {(z.x, z.y) for z in self.zombies}
        for z in list(self.zombies):
            z.cd -= 1
            z.mv -= 1
            if self.zombie_attack(z, fh):
                continue
            if z.mv <= 0:
                z.mv = self.d["zmove"] + random.randint(0, 2)
                self.move_zombie(z, fh, occ)

    # ---- survivors --------------------------------------------------------
    def step_field(self, s, field, zset):
        d = field.get((s.x, s.y))
        if d is None:
            return
        nb = [(s.x + dx, s.y + dy) for dx, dy in D4]
        opts = [n for n in nb if field.get(n, 9999) < d and self.free_h(n, zset)]
        if opts:
            s.x, s.y = random.choice(opts)
            self.survivor_pickup(s)

    def survivor_pickup(self, s):
        if (s.x, s.y) in self.crates:
            self.crates.remove((s.x, s.y))
            s.ammo += 1

    def wiggle(self, s, zset):
        nb = [(s.x + dx, s.y + dy) for dx, dy in D4]
        nb = [n for n in nb if self.free_h(n, zset)]
        if nb:
            s.x, s.y = random.choice(nb)

    def survivor_think(self, s, zset, fp):
        pos = (s.x, s.y)
        threats = [z for z in self.zombies if inside_house(z.x, z.y)]
        if threats:
            near = min(cheb(pos, (z.x, z.y)) for z in threats)
            if near <= 2:
                cands = [pos] + [(s.x + dx, s.y + dy) for dx, dy in D4]
                cands = [c for c in cands if c == pos or self.free_h(c, zset)]
                best = max(cands, key=lambda c: (min(cheb(c, (z.x, z.y)) for z in threats),
                                                 -FHATCH.get(c, 99), random.random()))
                s.x, s.y = best
                return
        if s.ammo > 0 and s.cd <= 0:
            tg = [z for z in self.zombies
                  if dist(pos, (z.x, z.y)) <= (6 if inside_house(z.x, z.y) else 3.5)]
            if tg:
                z = min(tg, key=lambda q: dist(pos, (q.x, q.y)))
                s.ammo -= 1
                s.cd = 26
                self.add_tracer(pos, (z.x, z.y))
                if random.random() < 0.55:
                    self.kill_zombie(z)
                    self.say("A SURVIVOR DROPS ONE!", 18, ORG)
                return
        if not self.cellar and fp and cheb(pos, (self.px, self.py)) <= 7:
            if cheb(pos, (self.px, self.py)) > 2:
                self.step_field(s, fp, zset)
            elif random.random() < 0.1:
                self.wiggle(s, zset)
            return
        weak = [i for i, b in enumerate(self.boards) if b < 3]
        if weak:
            i = min(weak, key=lambda k: (self.boards[k], FIN[k].get(pos, 99)))
            if cheb(pos, WIN_POS[i]) <= 1:
                if s.bcd <= 0 and WIN_POS[i] not in zset:
                    self.boards[i] += 1
                    s.bcd = 40
            else:
                self.step_field(s, FIN[i], zset)
        elif not self.cellar and fp:
            self.step_field(s, fp, zset)
        elif random.random() < 0.2:
            self.wiggle(s, zset)

    def update_survivors(self):
        zset = {(z.x, z.y) for z in self.zombies}
        fp = bfs([(self.px, self.py)], hpass) if not self.cellar else None
        for s in list(self.surv):
            if s.cellar:
                continue
            s.cd -= 1
            s.bcd -= 1
            s.mv -= 1
            if s.mv > 0:
                continue
            s.mv = 3
            self.survivor_think(s, zset, fp)

    # ---- world ------------------------------------------------------------
    def ambient(self):
        """Things that happen even on the title screen: fog, lightning, flicker."""
        self.frame += 1
        for f in self.fog:
            f[0] = (f[0] + f[2]) % W
            f[1] = (f[1] + random.uniform(-0.02, 0.02)) % H
        if self.flash > 0:
            self.flash -= 1
        self.next_flash -= 1
        if self.next_flash <= 0:
            self.flash = random.choice((2, 2, 3, 5))
            self.next_flash = random.randint(180, 360)

    def update_misc(self):
        self.ambient()
        self.crate_cd -= 1
        if self.crate_cd <= 0:
            self.crate_cd = int(self.d["crate"] * FPS * random.uniform(0.7, 1.3))
            if len(self.crates) < self.d["crates"]:
                for _ in range(40):
                    c = (random.randint(HX0 + 1, HX1 - 1), random.randint(HY0 + 1, HY1 - 1))
                    if KIND[c[1]][c[0]] == "floor" and c not in self.crates and cheb(c, (self.px, self.py)) > 2:
                        self.crates.append(c)
                        self.say("YOU HEAR A CRATE SLIDE ACROSS THE FLOOR...", 30, GREY)
                        break
        for t in self.tracers:
            t[1] -= 1
        self.tracers = [t for t in self.tracers if t[1] > 0]
        if self.msg_ttl > 0:
            self.msg_ttl -= 1
        if self.inv > 0:
            self.inv -= 1
        if self.thump > 0:
            self.thump -= 1
        if self.upshot > 0:
            self.upshot -= 1
        self.amb_cd -= 1
        if self.amb_cd <= 0:
            self.amb_cd = random.randint(25, 50) * FPS
            if self.msg_ttl <= 0:
                self.say(random.choice(AMBIENT), 50, GREY)
        if self.hatch_hp <= 0 and self.cellar:
            self.lose("THE HATCH GAVE WAY. THE CELLAR BECAME A GRAVE.")

    def step(self, keys):
        if self.result:
            return
        self.t += 1
        self.handle_keys(keys)
        self.spawn()
        humans = self.human_cells()
        fh = bfs(humans or [HATCH], self.zpass)
        self.fh = fh
        self.update_zombies(fh)
        self.update_survivors()
        self.update_misc()
        if self.result is None and self.t >= self.night:
            self.win()


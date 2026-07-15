# cells_v4.py — Constraint Cells v0.4: trust, choice, and learning
#
# v0.3 ended on a wall: rival camps that logic cannot decide between.
# v0.4 adds TRUST:
#   - every premise has a trust score (default 1.0)
#   - camps are grouped by the CONCLUSION they imply
#   - each conclusion is scored by its best-trusted camp
#   - the network BELIEVES the top conclusion (or admits a tie)
#   - when an episode ends, experience updates trust:
#       premises in the winning worldview gain, the rest lose.
#
# Logic proves the options. Trust chooses. Experience reshapes trust.

from itertools import combinations

INF = float("inf")

def intersect(i, j): return (max(i[0], j[0]), min(i[1], j[1]))
def empty(i):        return i[0] > i[1] + 1e-9

def fmt(i):
    if i[0] > i[1] + 1e-9: return "IMPOSSIBLE"
    if i[0] == -INF and i[1] == INF: return "?"
    if i[1] - i[0] < 1e-9: return str(round(i[0], 6))
    return f"[{round(i[0],6)} .. {round(i[1],6)}]"

# ---------- global state ----------

QUEUE    = []
NOGOODS  = []     # premise sets proven jointly impossible
PREMISES = set()  # every premise used in this network
TRUST    = {}     # premise -> trust. PERSISTS across episodes = memory.

def trust(p): return TRUST.get(p, 1.0)
def is_bad(S): return any(ng <= S for ng in NOGOODS)

def record_nogood(S):
    if is_bad(S): return
    NOGOODS[:] = [ng for ng in NOGOODS if not (S <= ng)]
    NOGOODS.append(S)

def reset():
    """New episode: forget the network, KEEP the trust (the memory)."""
    QUEUE.clear(); NOGOODS.clear(); PREMISES.clear()

# ---------- the cell (same soul as v0.3) ----------

class Cell:
    def __init__(self, name):
        self.name = name
        self.beliefs = {}
        self.watchers = []

    def _add(self, S, interval):
        if is_bad(S): return
        cur = self.beliefs.get(S, (-INF, INF))
        new = intersect(cur, interval)
        if empty(new):
            record_nogood(S)
            self.beliefs.pop(S, None)
            for p in self.watchers: QUEUE.append(p)
            return
        if new == cur:
            return
        # SUBSUMPTION PRUNING (v0.4.1): a row is dead weight if a row with
        # FEWER assumptions already says something at least as tight.
        for S2, I2 in self.beliefs.items():
            if S2 < S and I2[0] >= new[0] - 1e-12 and I2[1] <= new[1] + 1e-12:
                return                      # new row adds nothing: skip it
        # and storing this row may make existing bigger rows dead weight:
        for S2 in [S2 for S2, I2 in self.beliefs.items()
                   if S < S2 and new[0] >= I2[0] - 1e-12 and new[1] <= I2[1] + 1e-12]:
            del self.beliefs[S2]
        self.beliefs[S] = new
        for p in self.watchers: QUEUE.append(p)

    def tell(self, lo, hi, supports=frozenset()):
        S = frozenset(supports)
        PREMISES.update(S)
        for S2, I2 in list(self.beliefs.items()):
            self._add(S | S2, intersect(I2, (lo, hi)))
        self._add(S, (lo, hi))

    def under(self, premises):
        premises = frozenset(premises)
        result = (-INF, INF)
        for S, I in self.beliefs.items():
            if S <= premises and not is_bad(S):
                result = intersect(result, I)
        return result

# ---------- propagators ----------

class Adder:
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        for cell in (a, b, c): cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, b, c = self.a, self.b, self.c
        for x, y, z, f in ((a, b, c, lambda i, j: (i[0]+j[0], i[1]+j[1])),
                           (c, b, a, lambda i, j: (i[0]-j[1], i[1]-j[0])),
                           (c, a, b, lambda i, j: (i[0]-j[1], i[1]-j[0]))):
            for Sx, Ix in list(x.beliefs.items()):
                for Sy, Iy in list(y.beliefs.items()):
                    U = Sx | Sy
                    if is_bad(U): continue
                    lo, hi = f(Ix, Iy)
                    z.tell(lo, hi, U)

def settle():
    steps = 0
    try:
        while QUEUE:
            QUEUE.pop(0).run()
            steps += 1
            if steps > 200000: raise RuntimeError("did not settle")
    finally:
        QUEUE.clear()

# ---------- NEW in v0.4: choosing and learning ----------

def rival_camps():
    """All maximal premise sets that survive every known conflict."""
    ps = sorted(PREMISES)
    camps = []
    for r in range(len(ps), 0, -1):
        for combo in combinations(ps, r):
            w = frozenset(combo)
            if not is_bad(w) and not any(w < big for big in camps):
                camps.append(w)
    return camps

def believe(cells):
    """Group camps by conclusion; rank conclusions by best camp's trust."""
    table = {}   # conclusion -> (best score, [camps reaching it at best score])
    for w in rival_camps():
        key = tuple(fmt(c.under(w)) for c in cells)
        s = round(sum(trust(p) for p in w), 6)
        if key not in table or s > table[key][0]:
            table[key] = (s, [w])
        elif s == table[key][0]:
            table[key][1].append(w)
    ranked = sorted(table.items(), key=lambda kv: -kv[1][0])
    return ranked

def show_belief(label, cells):
    ranked = believe(cells)
    top_score = ranked[0][1][0]
    tied = sum(1 for _, (s, _) in ranked if abs(s - top_score) < 1e-9)
    print(f"   {label}")
    for key, (s, camps) in ranked[:3]:
        vals = ", ".join(f"{c.name}={v}" for c, v in zip(cells, key))
        mark = " <== BELIEVED" if s == top_score and tied == 1 else \
               " <- tied" if abs(s - top_score) < 1e-9 else ""
        print(f"     score {round(s,2):>5}  {vals}{mark}")
        for w in camps:
            print(f"                  camp: {sorted(w)}")
    if tied > 1:
        print("     ^ genuine tie between DIFFERENT conclusions:")
        print("       the network refuses to pretend it knows.")
        return None
    # winners = everyone in any top camp of the winning conclusion
    winners = set()
    for w in ranked[0][1][1]: winners |= w
    return winners

def experience_update(winners):
    """Experience reshapes trust. Winners +5%, losers -20%."""
    for p in sorted(PREMISES):
        old = trust(p)
        TRUST[p] = round(old * (1.05 if p in winners else 0.80), 6)
        tag = "kept " if p in winners else "DROP "
        print(f"     {tag}trust[{p}]: {round(old,3)} -> {round(TRUST[p],3)}")

def build_story():
    A, B, Cs, D, E = Cell("A"), Cell("B"), Cell("C"), Cell("D"), Cell("E")
    Adder(A, B, Cs)
    Adder(Cs, D, E)
    A.tell(10, 10, {"alice"})
    B.tell(40, 40, {"bob"})
    Cs.tell(60, 60, {"carol"})
    D.tell(1, 1, {"dave"})
    E.tell(51, 51, {"eve"})
    E.tell(61, 61, {"frank"})
    settle()
    return Cs, D, E

# =====================================================================
print("EPISODE 1 — everyone equally trusted: an honest deadlock")
reset()
Cs, D, E = build_story()
show_belief("conclusions on the table:", [Cs, D, E])

print("\nEPISODE 2 — carol is a calibrated instrument (trust 3.0)")
TRUST["carol"] = 3.0
winners = show_belief("same conflicts, new scores:", [Cs, D, E])

print("\nEPISODE 3 — gina (trust 2.5, independent auditor) reports E = 51")
TRUST["gina"] = 2.5
E.tell(51, 51, {"gina"})
settle()
winners = show_belief("after gina's report:", [Cs, D, E])

print("\nEPISODE 4 — episode ends; experience reshapes trust")
experience_update(winners)
print("   ^ Nobody edited a config file. Events changed the machine.")
print("     Next episode, the dropped premises' word buys less.")

# cells_v3.py — Constraint Cells v0.3: the Truth Maintenance upgrade
#
# THE ONE CHANGE: a cell no longer holds ONE interval.
# It holds a TABLE:  premise-set -> interval.
#
#   v0.2:  Celsius = [37.78, 37.78]        (premises fused, unrecoverable)
#   v0.3:  Celsius:
#            {}                    -> anything
#            {weather_report}      -> [0, 40]
#            {my_thermometer}      -> [37.78, 37.78]
#            {weather, thermo}     -> [37.78, 37.78]
#
# Because nothing is ever fused, three abilities appear:
#   1. RETRACTION      — drop a premise; knowledge from others survives
#   2. MINIMAL BLAME   — contradictions name the smallest guilty premise set
#   3. PARALLEL WORLDS — incompatible hypotheses coexist in one network

INF = float("inf")

def intersect(i, j):
    return (max(i[0], j[0]), min(i[1], j[1]))

def empty(i):
    return i[0] > i[1] + 1e-9

def fmt(i):
    if i[0] > i[1] + 1e-9: return "IMPOSSIBLE"
    if i[0] == -INF and i[1] == INF: return "?"
    if i[1] - i[0] < 1e-9: return str(round(i[0], 6))
    return f"[{round(i[0],6)} .. {round(i[1],6)}]"

# ---------- Nogoods: premise combinations proven impossible ----------

QUEUE = []
NOGOODS = []          # list of frozensets, kept minimal

def is_bad(S):
    return any(ng <= S for ng in NOGOODS)

def record_nogood(S):
    if is_bad(S):
        return                                    # already covered
    NOGOODS[:] = [ng for ng in NOGOODS if not (S <= ng)]  # drop weaker ones
    NOGOODS.append(S)

def reset():
    QUEUE.clear()
    NOGOODS.clear()

# ---------- The Cell ----------

class Cell:
    def __init__(self, name):
        self.name = name
        self.beliefs = {}          # frozenset(premises) -> (lo, hi)
        self.watchers = []

    def _add(self, S, interval):
        if is_bad(S):
            return
        cur = self.beliefs.get(S, (-INF, INF))
        new = intersect(cur, interval)
        if empty(new):
            record_nogood(S)       # this premise combo is impossible
            self.beliefs.pop(S, None)
            for p in self.watchers: QUEUE.append(p)
            return
        if new != cur:
            self.beliefs[S] = new
            for p in self.watchers: QUEUE.append(p)

    def tell(self, lo, hi, supports=frozenset()):
        S = frozenset(supports)
        # cross the new info against every existing belief:
        # if row S2 and claim S clash, then S|S2 is jointly impossible.
        for S2, I2 in list(self.beliefs.items()):
            self._add(S | S2, intersect(I2, (lo, hi)))
        self._add(S, (lo, hi))

    def under(self, premises):
        """What do I know, IF I believe exactly these premises?"""
        premises = frozenset(premises)
        result = (-INF, INF)
        for S, I in self.beliefs.items():
            if S <= premises and not is_bad(S):
                result = intersect(result, I)
        return result

    def show(self):
        print(f"   {self.name}:")
        for S in sorted(self.beliefs, key=lambda s: (len(s), sorted(s))):
            mark = "  DEAD (nogood)" if is_bad(S) else ""
            label = "{" + ", ".join(sorted(S)) + "}" if S else "{}"
            print(f"     {label:38s} -> {fmt(self.beliefs[S])}{mark}")

# ---------- Propagators: every belief combination flows ----------

class Adder:
    """a + b = c in all directions, per premise-combination."""
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

class Multiplier:
    """a * k = c for a positive constant k."""
    def __init__(self, a, k, c):
        self.a, self.k, self.c = a, k, c
        for cell in (a, c): cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, k, c = self.a, self.k, self.c
        for S, I in list(a.beliefs.items()):
            if not is_bad(S): c.tell(I[0]*k, I[1]*k, S)
        for S, I in list(c.beliefs.items()):
            if not is_bad(S): a.tell(I[0]/k, I[1]/k, S)

def settle():
    steps = 0
    try:
        while QUEUE:
            QUEUE.pop(0).run()
            steps += 1
            if steps > 200000:
                raise RuntimeError("network did not settle")
    finally:
        QUEUE.clear()

def constant(value):
    cell = Cell(str(value))
    cell.beliefs[frozenset()] = (value, value)   # true under NO assumptions
    return cell

def build_thermometer():
    C, F, t = Cell("Celsius"), Cell("Fahrenheit"), Cell("t")
    Multiplier(C, 1.8, t)
    Adder(t, constant(32), F)
    return C, F

# =====================================================================
# DEMOS
# =====================================================================

print("DEMO 1 — the belief table: premises never fuse")
reset()
C, F = build_thermometer()
C.tell(0, 40, {"weather_report"})
F.tell(100, 100, {"my_thermometer"})
settle()
C.show()

print("\nDEMO 2 — RETRACTION: change your mind without recomputing")
print("   believing both:            ", fmt(C.under({"weather_report", "my_thermometer"})))
print("   thermometer found broken:  ", fmt(C.under({"weather_report"})))
print("   weather report fakeinstead:", fmt(C.under({"my_thermometer"})))
print("   ^ Same network, three worldviews, zero recomputation.")

print("\nDEMO 3 — MINIMAL BLAME + finding the liar")
reset()
A, B, Cs, D, E = Cell("A"), Cell("B"), Cell("C"), Cell("D"), Cell("E")
Adder(A, B, Cs)      # A + B = C
Adder(Cs, D, E)      # C + D = E
A.tell(10, 10, {"alice"})
B.tell(40, 40, {"bob"})
Cs.tell(60, 60, {"carol"})   # clashes with alice+bob (10+40=50)
D.tell(1, 1, {"dave"})
E.tell(51, 51, {"eve"})      # fits alice+bob+dave, clashes carol+dave
E.tell(61, 61, {"frank"})    # frank BACKS CAROL's story (60 + 1 = 61)
settle()
print("   Impossible premise combinations found:")
for ng in NOGOODS:
    print("     can't ALL be true:", sorted(ng))
suspicion = {}
for ng in NOGOODS:
    for p in ng: suspicion[p] = suspicion.get(p, 0) + 1
print("   Suspicion count:", dict(sorted(suspicion.items())))
print("   ^ A perfect tie. Blame-counting cannot find a single liar.")

# So find every MAXIMAL consistent world instead.
from itertools import combinations
everyone = sorted({p for ng in NOGOODS for p in ng} |
                  {"alice", "bob", "carol", "dave", "eve", "frank"})
def consistent(w): return not any(ng <= w for ng in NOGOODS)
camps = []
for r in range(len(everyone), 0, -1):
    for combo in combinations(everyone, r):
        w = frozenset(combo)
        if consistent(w) and not any(w < big for big in camps):
            camps.append(w)
print("   Largest consistent worlds (rival camps):")
for w in camps:
    print(f"     {sorted(w)}: C = {fmt(Cs.under(w))}, E = {fmt(E.under(w))}")
print("   ^ The network cannot decide WHICH camp is right —")
print("     it can only prove these are the options. Choosing is v0.4.")

print("\nDEMO 4 — PARALLEL WORLDS: incompatible hypotheses coexist")
reset()
C, F = build_thermometer()
C.tell(0, 0, {"hypothesis_freezing"})
C.tell(100, 100, {"hypothesis_boiling"})
settle()
print("   F if freezing:", fmt(F.under({"hypothesis_freezing"})))
print("   F if boiling: ", fmt(F.under({"hypothesis_boiling"})))
print("   Known impossible combos:", [sorted(ng) for ng in NOGOODS])
print("   ^ One network holds BOTH worlds, and knows they exclude each other.")

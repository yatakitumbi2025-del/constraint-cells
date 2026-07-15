# cells_v5.py — Constraint Cells v0.5: the machine invents its own structure
#
# Until now, WE wired every propagator. In v0.5 the machine:
#   1. OBSERVES raw data pairs
#   2. INDUCES a law ("Total is always Price + 5")
#   3. INSTALLS its own propagator for that law
#   4. TAGS it with its own premise, trusted in proportion to evidence
#   5. PREDICTS with it in new situations
#   6. DEMOTES it when reality contradicts it
#
# Created structure + earned trust + revision by experience =
# the last line of the original vision: "the machine invents ways to think."

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

QUEUE, NOGOODS, PREMISES = [], [], set()
TRUST = {}     # persists across episodes
LAWS  = []     # persists: structure the machine has built for itself

def trust(p): return TRUST.get(p, 1.0)
def is_bad(S): return any(ng <= S for ng in NOGOODS)

def record_nogood(S):
    if is_bad(S): return
    NOGOODS[:] = [ng for ng in NOGOODS if not (S <= ng)]
    NOGOODS.append(S)

def reset():
    QUEUE.clear(); NOGOODS.clear(); PREMISES.clear()

# ---------- the cell (v0.4.1 core, with subsumption pruning) ----------

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
        if new == cur: return
        for S2, I2 in self.beliefs.items():
            if S2 < S and I2[0] >= new[0] - 1e-12 and I2[1] <= new[1] + 1e-12:
                return
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

def settle():
    steps = 0
    try:
        while QUEUE:
            QUEUE.pop(0).run()
            steps += 1
            if steps > 200000: raise RuntimeError("did not settle")
    finally:
        QUEUE.clear()

# ---------- choosing and learning (from v0.4) ----------

def rival_camps():
    ps = sorted(PREMISES)
    camps = []
    for r in range(len(ps), 0, -1):
        for combo in combinations(ps, r):
            w = frozenset(combo)
            if not is_bad(w) and not any(w < big for big in camps):
                camps.append(w)
    return camps

def believe(cells):
    table = {}
    for w in rival_camps():
        key = tuple(fmt(c.under(w)) for c in cells)
        s = round(sum(trust(p) for p in w), 6)
        if key not in table or s > table[key][0]:
            table[key] = (s, [w])
        elif s == table[key][0]:
            table[key][1].append(w)
    return sorted(table.items(), key=lambda kv: -kv[1][0])

def show_belief(label, cells):
    ranked = believe(cells)
    top = ranked[0][1][0]
    tied = sum(1 for _, (s, _) in ranked if abs(s - top) < 1e-9)
    print(f"   {label}")
    for key, (s, camps) in ranked[:3]:
        vals = ", ".join(f"{c.name}={v}" for c, v in zip(cells, key))
        mark = " <== BELIEVED" if s == top and tied == 1 else \
               " <- tied" if abs(s - top) < 1e-9 else ""
        print(f"     score {round(s,2):>5}  {vals}{mark}")
        for w in camps: print(f"                  camp: {sorted(w)}")
    if tied > 1:
        print("     ^ genuine tie: the network refuses to pretend it knows.")
        return None
    winners = set()
    for w in ranked[0][1][1]: winners |= w
    return winners

def experience_update(winners):
    if winners is None:
        print("     (tie: no update — no evidence about who was right)")
        return
    for p in sorted(PREMISES):
        old = trust(p)
        TRUST[p] = round(old * (1.05 if p in winners else 0.80), 6)
        tag = "kept " if p in winners else "DROP "
        print(f"     {tag}trust[{p}]: {round(old,3)} -> {round(TRUST[p],3)}")

# ---------- NEW in v0.5: the machine builds its own propagators ----------

class LawAdder:
    """dst = src + k — a propagator the MACHINE installed, believed
    only under the law's own premise."""
    def __init__(self, src, dst, k, name):
        self.src, self.dst, self.k, self.name = src, dst, k, name
        for cell in (src, dst): cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        nm = frozenset([self.name])
        for S, I in list(self.src.beliefs.items()):
            if not is_bad(S | nm):
                self.dst.tell(I[0] + self.k, I[1] + self.k, S | nm)
        for S, I in list(self.dst.beliefs.items()):
            if not is_bad(S | nm):
                self.src.tell(I[0] - self.k, I[1] - self.k, S | nm)

def induce(observations, src_name, dst_name):
    """Look at raw (src, dst) pairs. If dst - src is constant across 3+
    observations, the machine WRITES ITSELF A LAW."""
    diffs = [d - s for s, d in observations]
    if len(diffs) >= 3 and max(diffs) - min(diffs) < 1e-9:
        k = diffs[0]
        name = f"law:{dst_name}={src_name}+{k:g}"
        if not any(l["name"] == name for l in LAWS):
            LAWS.append({"name": name, "src": src_name, "dst": dst_name, "k": k})
            TRUST[name] = round(0.5 + 0.5 * len(diffs), 3)  # trust = evidence
        return name
    return None

def new_network():
    """Build a fresh episode — and the machine wires in ITS OWN laws."""
    P, T = Cell("Price"), Cell("Total")
    cells = {"Price": P, "Total": T}
    for law in LAWS:
        LawAdder(cells[law["src"]], cells[law["dst"]], law["k"], law["name"])
    return P, T

# =====================================================================
print("PHASE 1 — the machine observes raw data and INDUCES a law")
observations = [(10, 15), (20, 25), (7, 12)]
print("   observations (Price, Total):", observations)
law = induce(observations, "Price", "Total")
print(f"   machine wrote itself a law: '{law}'  trust {trust(law)}")
print("   ^ Nobody coded 'add 5'. The structure was INVENTED from data.")

print("\nPHASE 2 — a new situation: prediction using its OWN law")
reset()
P, T = new_network()
P.tell(40, 40, {"order_form"})
settle()
winners = show_belief("customer orders at Price=40:", [P, T])

print("\nPHASE 3 — reality disagrees: two signed receipts (trust 2.5)")
TRUST["receipt_P"] = 2.5
TRUST["receipt_T"] = 2.5
reset()
P, T = new_network()
P.tell(100, 100, {"receipt_P"})
T.tell(120, 120, {"receipt_T"})       # fee is different for big orders!
settle()
print("   conflicts found:", [sorted(ng) for ng in NOGOODS])
winners = show_belief("what should the machine believe?", [P, T])

print("\nPHASE 4 — the machine DEMOTES its own invention")
experience_update(winners)
print("   ^ The machine built a law, used it, met a counterexample,")
print("     and now trusts its own creation less. Invent -> test -> revise:")
print("     structure and belief are BOTH now shaped by experience.")

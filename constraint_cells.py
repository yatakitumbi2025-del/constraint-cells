"""constraint_cells — a tiny, self-revising computational fabric.

The one rule: a cell holds an interval [lo, hi] of possible values and can
only ever NARROW. Never widen. Information only accumulates. Propagators are
dumb local rules ("a + b = c") that push knowledge between cells in every
direction until the network settles.

On top of that rule, this library provides:
  - justified knowledge      (every belief remembers its premises)
  - truth maintenance        (rival worldviews coexist; retraction is free)
  - trust-weighted choice    (the network believes the best-scoring world)
  - experience               (outcomes reshape trust)
  - structure invention      (laws induced from data become new propagators)

Everything lives inside a Network object. No global state: any number of
independent networks can coexist in one program.

Typical use:
    net = Network()
    C, F = net.cell("Celsius"), net.cell("Fahrenheit")
    t = net.cell("t")
    Multiplier(C, 1.8, t)
    Adder(t, net.constant(32), F)
    F.tell(212, 212, {"reading"})
    net.settle()
    C.under({"reading"})   # -> (100.0, 100.0)
"""

from itertools import combinations

__version__ = "1.1.0"

# Trust categories — the budget example's lesson: a payslip is not a wish.
FACT, ESTIMATE, WISH = 3.0, 2.0, 1.0

INF = float("inf")
_EPS = 1e-9


def intersect(i, j):
    return (max(i[0], j[0]), min(i[1], j[1]))


def is_empty(i):
    return i[0] > i[1] + _EPS


def fmt(i):
    """Human-readable interval. Empty intervals are IMPOSSIBLE, never a number."""
    if is_empty(i):
        return "IMPOSSIBLE"
    if i[0] == -INF and i[1] == INF:
        return "?"
    if i[1] - i[0] < _EPS:
        return str(round(i[0], 6))
    return f"[{round(i[0], 6)} .. {round(i[1], 6)}]"


# ---------------------------------------------------------------------------
# Network: owns all state that used to be global
# ---------------------------------------------------------------------------

class Network:
    def __init__(self):
        self.queue = []        # propagators with possibly-new work
        self.nogoods = []      # premise sets proven jointly impossible
        self.premises = set()  # every premise used in this network
        self.trust = {}        # premise -> trust score (default 1.0)
        self.laws = []         # structure the machine has induced

    # ----- construction -----

    def cell(self, name):
        return Cell(self, name)

    def constant(self, value):
        c = Cell(self, str(value))
        c.beliefs[frozenset()] = (value, value)   # true under NO assumptions
        return c

    def successor(self):
        """A fresh episode: new cells and conflicts, SAME memory.
        Trust and laws are shared by reference — that's what persists."""
        n = Network()
        n.trust = self.trust
        n.laws = self.laws
        return n

    # ----- nogoods -----

    def is_bad(self, S):
        return any(ng <= S for ng in self.nogoods)

    def record_nogood(self, S):
        if self.is_bad(S):
            return
        self.nogoods = [ng for ng in self.nogoods if not (S <= ng)]
        self.nogoods.append(S)

    # ----- running -----

    def settle(self, max_steps=200000):
        steps = 0
        try:
            while self.queue:
                self.queue.pop(0).run()
                steps += 1
                if steps > max_steps:
                    raise RuntimeError("network did not settle")
        finally:
            self.queue.clear()
        return steps

    # ----- trust -----

    def trust_of(self, p):
        return self.trust.get(p, 1.0)

    def set_trust(self, p, v):
        self.trust[p] = v

    # ----- worldviews and choice -----

    def rival_camps(self):
        """All maximal premise sets that survive every known conflict."""
        ps = sorted(self.premises)
        camps = []
        for r in range(len(ps), 0, -1):
            for combo in combinations(ps, r):
                w = frozenset(combo)
                if not self.is_bad(w) and not any(w < big for big in camps):
                    camps.append(w)
        return camps

    def believe(self, cells):
        """Group camps by the conclusion they imply for `cells`; rank
        conclusions by their best camp's total trust.
        Returns [(score, values_tuple, [camps])], best first."""
        table = {}
        for w in self.rival_camps():
            key = tuple(fmt(c.under(w)) for c in cells)
            s = round(sum(self.trust_of(p) for p in w), 6)
            cur = table.get(key)
            if cur is None or s > cur[0]:
                table[key] = (s, [w])
            elif s == cur[0]:
                cur[1].append(w)
        ranked = [(s, key, camps) for key, (s, camps) in table.items()]
        ranked.sort(key=lambda t: (-t[0], t[1]))
        return ranked

    def winners(self, ranked):
        """Premises in any top camp of the winning conclusion,
        or None on a genuine tie between different conclusions."""
        if not ranked:
            return None
        top = ranked[0][0]
        tops = [r for r in ranked if abs(r[0] - top) < _EPS]
        if len(tops) > 1:
            return None
        out = set()
        for w in tops[0][2]:
            out |= w
        return out

    def believed(self, cell):
        """The cell's value under the winning worldview,
        or None on a genuine tie."""
        ranked = self.believe([cell])
        w = self.winners(ranked)
        return None if w is None else cell.under(w)

    def experience_update(self, winners, gain=1.05, loss=0.80):
        """Outcomes reshape trust. Returns [(premise, old, new)].
        A tie (winners=None) teaches nothing and changes nothing."""
        changes = []
        if winners is None:
            return changes
        for p in sorted(self.premises):
            old = self.trust_of(p)
            self.trust[p] = round(old * (gain if p in winners else loss), 6)
            changes.append((p, old, self.trust[p]))
        return changes

    # ----- structure invention -----

    def induce(self, observations, src_name, dst_name, min_obs=3):
        """Observe raw (src, dst) pairs. If dst - src is constant across
        min_obs+ observations, the machine writes itself a law and trusts
        it in proportion to the evidence. Returns the law premise name."""
        diffs = [d - s for s, d in observations]
        if len(diffs) >= min_obs and max(diffs) - min(diffs) < _EPS:
            k = diffs[0]
            name = f"law:{dst_name}={src_name}+{k:g}"
            if not any(l["name"] == name for l in self.laws):
                self.laws.append(
                    {"name": name, "src": src_name, "dst": dst_name, "k": k})
                self.trust.setdefault(name, round(0.5 + 0.5 * len(diffs), 6))
            return name
        return None

    def wire_laws(self, cells_by_name):
        """Install every induced law whose cells exist in this episode."""
        for law in self.laws:
            if law["src"] in cells_by_name and law["dst"] in cells_by_name:
                LawAdder(cells_by_name[law["src"]],
                         cells_by_name[law["dst"]],
                         law["k"], law["name"])


# ---------------------------------------------------------------------------
# Cell: justified, multi-worldview knowledge with subsumption pruning
# ---------------------------------------------------------------------------

class Cell:
    def __init__(self, net, name):
        self.net = net
        self.name = name
        self.beliefs = {}      # frozenset(premises) -> (lo, hi)
        self.watchers = []

    def _add(self, S, interval):
        net = self.net
        if net.is_bad(S):
            return
        cur = self.beliefs.get(S, (-INF, INF))
        new = intersect(cur, interval)
        if is_empty(new):
            net.record_nogood(S)
            self.beliefs.pop(S, None)
            net.queue.extend(self.watchers)
            return
        if new == cur:
            return
        # Subsumption pruning: a row is dead weight if a row with FEWER
        # assumptions already says something at least as tight.
        for S2, I2 in self.beliefs.items():
            if S2 < S and I2[0] >= new[0] - 1e-12 and I2[1] <= new[1] + 1e-12:
                return
        for S2 in [S2 for S2, I2 in self.beliefs.items()
                   if S < S2 and new[0] >= I2[0] - 1e-12
                   and new[1] <= I2[1] + 1e-12]:
            del self.beliefs[S2]
        self.beliefs[S] = new
        net.queue.extend(self.watchers)

    def tell(self, lo, hi, supports=frozenset(), trust=None):
        """Learn something under a set of premises. No premises = axiom.
        trust= sets the trust of every premise in supports (last write wins);
        use the FACT / ESTIMATE / WISH constants or any number."""
        S = frozenset(supports)
        self.net.premises.update(S)
        if trust is not None:
            for p in S:
                self.net.trust[p] = trust
        for S2, I2 in list(self.beliefs.items()):
            self._add(S | S2, intersect(I2, (lo, hi)))
        self._add(S, (lo, hi))

    def under(self, premises):
        """What do I know, IF I believe exactly these premises?"""
        premises = frozenset(premises)
        result = (-INF, INF)
        for S, I in self.beliefs.items():
            if S <= premises and not self.net.is_bad(S):
                result = intersect(result, I)
        return result

    def rows(self):
        return len(self.beliefs)

    def __repr__(self):
        return f"<Cell {self.name}: {self.rows()} beliefs>"


# ---------------------------------------------------------------------------
# Propagators: dumb local rules, knowledge flows in every direction
# ---------------------------------------------------------------------------

class _Propagator:
    def __init__(self, *cells):
        nets = {c.net for c in cells}
        assert len(nets) == 1, "all cells must belong to the same Network"
        self.net = nets.pop()
        for c in cells:
            c.watchers.append(self)
        self.net.queue.append(self)


class Adder(_Propagator):
    """a + b = c, in all directions, per premise-combination."""

    def __init__(self, a, b, c):
        super().__init__(a, b, c)
        self.a, self.b, self.c = a, b, c

    def run(self):
        a, b, c = self.a, self.b, self.c
        for x, y, z, f in (
                (a, b, c, lambda i, j: (i[0] + j[0], i[1] + j[1])),
                (c, b, a, lambda i, j: (i[0] - j[1], i[1] - j[0])),
                (c, a, b, lambda i, j: (i[0] - j[1], i[1] - j[0]))):
            for Sx, Ix in list(x.beliefs.items()):
                for Sy, Iy in list(y.beliefs.items()):
                    U = Sx | Sy
                    if self.net.is_bad(U):
                        continue
                    lo, hi = f(Ix, Iy)
                    z.tell(lo, hi, U)


class Multiplier(_Propagator):
    """a * k = c for a positive constant k."""

    def __init__(self, a, k, c):
        assert k > 0, "Multiplier requires a positive constant"
        super().__init__(a, c)
        self.a, self.k, self.c = a, k, c

    def run(self):
        a, k, c = self.a, self.k, self.c
        for S, I in list(a.beliefs.items()):
            if not self.net.is_bad(S):
                c.tell(I[0] * k, I[1] * k, S)
        for S, I in list(c.beliefs.items()):
            if not self.net.is_bad(S):
                a.tell(I[0] / k, I[1] / k, S)


class Squarer(_Propagator):
    """a * a = c, assuming a >= 0. 'Unknown' is [0, inf), not wildly negative."""

    def __init__(self, a, c):
        super().__init__(a, c)
        self.a, self.c = a, c

    def run(self):
        a, c = self.a, self.c
        for S, I in list(a.beliefs.items()):
            if self.net.is_bad(S):
                continue
            lo = max(0.0, I[0])
            hi = I[1] if I[1] != INF else INF
            c.tell(lo * lo, hi * hi if hi != INF else INF, S)
        for S, I in list(c.beliefs.items()):
            if self.net.is_bad(S):
                continue
            lo = max(0.0, I[0]) ** 0.5
            hi = I[1] ** 0.5 if I[1] != INF else INF
            a.tell(lo, hi, S)


class Sum:
    """total = term1 + term2 + ... — sugar that builds a hidden chain of
    pairwise Adders. No new propagation math: reuses the tested primitive,
    so every Adder guarantee (bidirectionality, justification flow,
    minimal nogoods) holds automatically."""

    def __init__(self, total, terms):
        assert len(terms) >= 2, "Sum needs at least two terms"
        net = total.net
        acc = terms[0]
        for i, term in enumerate(terms[1:-1], 1):
            hidden = net.cell(f"_{total.name}:partial{i}")
            Adder(acc, term, hidden)
            acc = hidden
        Adder(acc, terms[-1], total)


class LawAdder(_Propagator):
    """dst = src + k — a propagator the MACHINE installed, believed only
    under the law's own premise."""

    def __init__(self, src, dst, k, name):
        super().__init__(src, dst)
        self.src, self.dst, self.k, self.name = src, dst, k, name
        self.net.premises.add(name)

    def run(self):
        nm = frozenset([self.name])
        for S, I in list(self.src.beliefs.items()):
            if not self.net.is_bad(S | nm):
                self.dst.tell(I[0] + self.k, I[1] + self.k, S | nm)
        for S, I in list(self.dst.beliefs.items()):
            if not self.net.is_bad(S | nm):
                self.src.tell(I[0] - self.k, I[1] - self.k, S | nm)


# ---------------------------------------------------------------------------
# Convenience printing (for examples and interactive use)
# ---------------------------------------------------------------------------

def print_belief(net, label, cells, top=3):
    ranked = net.believe(cells)
    if not ranked:
        print(f"   {label}\n     (no premises yet)")
        return None
    best = ranked[0][0]
    tied = sum(1 for s, _, _ in ranked if abs(s - best) < _EPS)
    print(f"   {label}")
    for s, key, camps in ranked[:top]:
        vals = ", ".join(f"{c.name}={v}" for c, v in zip(cells, key))
        mark = " <== BELIEVED" if s == best and tied == 1 else \
               " <- tied" if abs(s - best) < _EPS else ""
        print(f"     score {round(s, 2):>6}  {vals}{mark}")
        for w in camps:
            print(f"                   camp: {sorted(w)}")
    if tied > 1:
        print("     ^ genuine tie: the network refuses to pretend it knows.")
    return net.winners(ranked)
      

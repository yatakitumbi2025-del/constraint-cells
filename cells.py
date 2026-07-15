# cells.py — Constraint Cell prototype (v0.1)
# Pure Python, no libraries. Runs anywhere, including phones.
#
# THE ONE RULE: a cell holds an interval [lo, hi] of possible values.
# It can only ever NARROW. Never widen. Information only accumulates.

class Contradiction(Exception):
    pass

# ---------- The Cell ----------

class Cell:
    def __init__(self, name, lo=float("-inf"), hi=float("inf")):
        self.name = name
        self.lo, self.hi = lo, hi
        self.watchers = []          # propagators that care about me

    def tell(self, lo, hi):
        """Someone learned something. Narrow my interval (intersect)."""
        new_lo = max(self.lo, lo)
        new_hi = min(self.hi, hi)
        if new_lo > new_hi + 1e-9:
            raise Contradiction(f"{self.name}: [{self.lo},{self.hi}] vs [{lo},{hi}]")
        if new_lo > self.lo or new_hi < self.hi:      # did I actually learn?
            self.lo, self.hi = new_lo, new_hi
            for p in self.watchers:                    # wake my neighbors
                QUEUE.append(p)

    def known(self):
        return self.hi - self.lo < 1e-9

    def __repr__(self):
        if self.known():
            return f"{self.name} = {round(self.lo, 6)}"
        if self.lo == float("-inf") and self.hi == float("inf"):
            return f"{self.name} = ? (anything)"
        return f"{self.name} = [{round(self.lo,6)} .. {round(self.hi,6)}]"

# ---------- The Propagators (dumb local rules) ----------

QUEUE = []

class Adder:
    """Knows one fact: a + b = c. Pushes knowledge in ALL directions."""
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        for cell in (a, b, c):
            cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, b, c = self.a, self.b, self.c
        c.tell(a.lo + b.lo, a.hi + b.hi)   # c = a + b
        a.tell(c.lo - b.hi, c.hi - b.lo)   # a = c - b
        b.tell(c.lo - a.hi, c.hi - a.lo)   # b = c - a

class Multiplier:
    """Knows one fact: a * k = c, for a POSITIVE constant k."""
    def __init__(self, a, k, c):
        self.a, self.k, self.c = a, k, c
        for cell in (a, c):
            cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, k, c = self.a, self.k, self.c
        c.tell(a.lo * k, a.hi * k)         # c = a * k
        a.tell(c.lo / k, c.hi / k)         # a = c / k

def settle():
    """Run until no propagator has anything new to say."""
    steps = 0
    try:
        while QUEUE:
            QUEUE.pop(0).run()
            steps += 1
            if steps > 100000:
                raise RuntimeError("network did not settle")
    finally:
        QUEUE.clear()   # a failed settle must not leak work into the next one

def constant(value):
    cell = Cell(str(value))
    cell.lo = cell.hi = value
    return cell

# =====================================================================
# DEMOS
# =====================================================================

def build_thermometer():
    """Wire the RELATIONSHIP  F = C * 1.8 + 32  as a network. Once."""
    C = Cell("Celsius")
    F = Cell("Fahrenheit")
    t = Cell("t")
    Multiplier(C, 1.8, t)          # t = C * 1.8
    Adder(t, constant(32), F)      # F = t + 32
    return C, F

print("DEMO 1 — set Fahrenheit, Celsius appears")
C, F = build_thermometer()
F.tell(212, 212)
settle()
print("  ", C, "|", F)

print("\nDEMO 2 — SAME network design, set Celsius instead")
C, F = build_thermometer()
C.tell(37, 37)
settle()
print("  ", C, "|", F)

print("\nDEMO 3 — partial knowledge in, partial knowledge out")
C, F = build_thermometer()
C.tell(20, 25)                     # 'somewhere between 20 and 25 degrees'
settle()
print("  ", C, "|", F)

print("\nDEMO 4 — three cells solve for the middle (A + B = C)")
A, B, Csum = Cell("A"), Cell("B"), Cell("C")
Adder(A, B, Csum)
A.tell(10, 10)
Csum.tell(50, 50)
settle()
print("  ", A, "|", B, "|", Csum)

print("\nDEMO 5 — contradiction is a SIGNAL, not a crash")
C, F = build_thermometer()
try:
    C.tell(0, 0)
    F.tell(100, 100)               # but 0 C must be 32 F!
    settle()
except Contradiction as e:
    print("   Contradiction detected ->", e)

import math

class Squarer:
    """Knows one fact: a * a = c  (assume a >= 0)"""
    def __init__(self, a, c):
        self.a, self.c = a, c
        for cell in (a, c):
            cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, c = self.a, self.c
        lo = max(0, a.lo)          # enforce the a >= 0 assumption before squaring
        c.tell(lo * lo, a.hi * a.hi)
        a.tell(math.sqrt(max(0, c.lo)), math.sqrt(c.hi) if c.hi != float('inf') else float('inf'))

print("\nDEMO 6 — Pythagoras, forward direction")
a, b, c = Cell("a"), Cell("b"), Cell("c")
a2, b2, c2 = Cell("a2"), Cell("b2"), Cell("c2")
Squarer(a, a2)
Squarer(b, b2)
Squarer(c, c2)
Adder(a2, b2, c2)
a.tell(3, 3)
b.tell(4, 4)
settle()
print("  ", a, "|", b, "|", c)

print("\nDEMO 6b — SAME network, feed it hypotenuse + one side instead")
a, b, c = Cell("a"), Cell("b"), Cell("c")
a2, b2, c2 = Cell("a2"), Cell("b2"), Cell("c2")
Squarer(a, a2)
Squarer(b, b2)
Squarer(c, c2)
Adder(a2, b2, c2)
a.tell(3, 3)
c.tell(5, 5)
settle()
print("  ", a, "|", b, "|", c)

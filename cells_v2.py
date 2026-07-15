# cells_v2.py — Constraint Cells v0.2: knowledge with justifications
#
# NEW IDEA: a cell no longer stores just "what I know".
# It stores "what I know AND which assumptions it depends on".
#
#   v0.1 cell:  Celsius = [0, 0]
#   v0.2 cell:  Celsius = [0, 0]  because {"weather_report"}
#
# When knowledge flows through a propagator, the justifications
# flow WITH it (they merge). So when a contradiction happens, the
# network can name exactly which assumptions are collectively guilty.

class Contradiction(Exception):
    def __init__(self, cell_name, guilty):
        self.guilty = guilty     # set of premise names that clash
        super().__init__(f"{cell_name} impossible. Guilty premises: {sorted(guilty)}")

QUEUE = []

# ---------- The Cell ----------

class Cell:
    def __init__(self, name, lo=float("-inf"), hi=float("inf")):
        self.name = name
        self.lo, self.hi = lo, hi
        self.supports = set()    # premises my current interval depends on
        self.watchers = []

    def tell(self, lo, hi, supports=frozenset()):
        """Learn something, and remember WHY it is believed."""
        supports = set(supports)
        new_lo = max(self.lo, lo)
        new_hi = min(self.hi, hi)
        if new_lo > new_hi + 1e-9:
            # The clash is caused by everything the old value depended on
            # PLUS everything the new value depended on.
            raise Contradiction(self.name, self.supports | supports)
        if new_lo > self.lo or new_hi < self.hi:
            self.lo, self.hi = new_lo, new_hi
            self.supports |= supports        # justifications accumulate too
            for p in self.watchers:
                QUEUE.append(p)

    def known(self):
        return self.hi - self.lo < 1e-9

    def __repr__(self):
        why = f"  because {sorted(self.supports)}" if self.supports else ""
        if self.known():
            return f"{self.name} = {round(self.lo, 6)}{why}"
        if self.lo == float("-inf") and self.hi == float("inf"):
            return f"{self.name} = ?"
        return f"{self.name} = [{round(self.lo,6)} .. {round(self.hi,6)}]{why}"

# ---------- Propagators (justifications flow through them) ----------

class Adder:
    """a + b = c, in all directions. Outputs inherit inputs' premises."""
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c
        for cell in (a, b, c):
            cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, b, c = self.a, self.b, self.c
        c.tell(a.lo + b.lo, a.hi + b.hi, a.supports | b.supports)
        a.tell(c.lo - b.hi, c.hi - b.lo, c.supports | b.supports)
        b.tell(c.lo - a.hi, c.hi - a.lo, c.supports | a.supports)

class Multiplier:
    """a * k = c for positive constant k. Constants need no premises."""
    def __init__(self, a, k, c):
        self.a, self.k, self.c = a, k, c
        for cell in (a, c):
            cell.watchers.append(self)
        QUEUE.append(self)

    def run(self):
        a, k, c = self.a, self.k, self.c
        c.tell(a.lo * k, a.hi * k, a.supports)
        a.tell(c.lo / k, c.hi / k, c.supports)

def settle():
    steps = 0
    try:
        while QUEUE:
            QUEUE.pop(0).run()
            steps += 1
            if steps > 100000:
                raise RuntimeError("network did not settle")
    finally:
        QUEUE.clear()

def constant(value):
    cell = Cell(str(value))
    cell.lo = cell.hi = value    # no supports: constants are always true
    return cell

def build_thermometer():
    C, F, t = Cell("Celsius"), Cell("Fahrenheit"), Cell("t")
    Multiplier(C, 1.8, t)
    Adder(t, constant(32), F)
    return C, F

# =====================================================================
# DEMOS
# =====================================================================

print("DEMO 1 — knowledge now carries its justification")
C, F = build_thermometer()
C.tell(37, 37, {"thermometer_reading"})
settle()
print("  ", C)
print("  ", F)
print("   ^ F was DERIVED, yet it knows which assumption it rests on.")

print("\nDEMO 2 — vague premise + precise premise: they COOPERATE")
C, F = build_thermometer()
try:
    C.tell(0, 40, {"weather_report"})      # vague: 'between 0 and 40'
    F.tell(100, 100, {"my_thermometer"})   # precise: 'exactly 100 F'
    settle()
    print("  ", C)
    print("  ", F)
    print("   ^ No contradiction: 100 F fits inside the vague range.")
    print("     But look at Celsius: TWO premises fused into ONE belief.")
    print("     If my_thermometer is later found broken, this cell cannot")
    print("     recover what weather_report alone said. That is v0.3's job.")
except Contradiction as e:
    print("  ", e)

print("\nDEMO 2b — make the premises CLASH instead")
C, F = build_thermometer()
try:
    C.tell(0, 0, {"weather_report"})       # precise: 'exactly 0 C'
    F.tell(100, 100, {"my_thermometer"})   # precise: 'exactly 100 F' -> clash!
    settle()
except Contradiction as e:
    print("  ", e)
    print("   ^ The network identified WHICH beliefs clash. Not just 'error'.")

print("\nDEMO 3 — innocent premises are NOT blamed")
A, B, Csum = Cell("A"), Cell("B"), Cell("C")
D, E = Cell("D"), Cell("E")
Adder(A, B, Csum)     # A + B = C
Adder(Csum, D, E)     # C + D = E
try:
    A.tell(10, 10, {"alice_said"})
    B.tell(40, 40, {"bob_said"})
    D.tell(1, 1, {"dave_said"})
    E.tell(99, 99, {"eve_said"})   # but 50 + 1 = 51, not 99!
    settle()
except Contradiction as e:
    print("  ", e)
    print("   ^ All four premises touched this cell's value,")
    print("     so all four are suspects. Narrowing suspects further")
    print("     (finding the MINIMAL guilty set) is v0.3's job —")
    print("     that requires tracking multiple justifications per cell.")

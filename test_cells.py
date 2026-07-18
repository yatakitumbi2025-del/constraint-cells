"""test_cells.py — every claim this project makes, as an assertion.

Run with:  python3 test_cells.py   (no dependencies)
or:        pytest test_cells.py    (if you have pytest)

Each test names the version whose claim it locks in. Several tests are
regression tests for real bugs found during development — those say so.
"""

import time
from constraint_cells import (
    Network, Adder, Multiplier, Squarer, fmt, INF)


def thermometer(net):
    C, F, t = net.cell("Celsius"), net.cell("Fahrenheit"), net.cell("t")
    Multiplier(C, 1.8, t)
    Adder(t, net.constant(32), F)
    return C, F


def approx(interval, value, tol=1e-6):
    return abs(interval[0] - value) < tol and abs(interval[1] - value) < tol


# ----- v0.1: computation self-assembles from relationships -----

def test_bidirectional_thermometer():
    net = Network()
    C, F = thermometer(net)
    F.tell(212, 212, {"r"})
    net.settle()
    assert approx(C.under({"r"}), 100)

    net = Network()
    C, F = thermometer(net)
    C.tell(37, 37, {"r"})
    net.settle()
    assert approx(F.under({"r"}), 98.6)


def test_partial_knowledge_propagates():
    net = Network()
    C, F = thermometer(net)
    C.tell(20, 25, {"r"})
    net.settle()
    lo, hi = F.under({"r"})
    assert abs(lo - 68) < 1e-6 and abs(hi - 77) < 1e-6


def test_solve_for_the_middle():
    net = Network()
    A, B, C = net.cell("A"), net.cell("B"), net.cell("C")
    Adder(A, B, C)
    A.tell(10, 10, {"r"})
    C.tell(50, 50, {"r"})
    net.settle()
    assert approx(B.under({"r"}), 40)


def test_pythagoras_both_directions():
    def triangle(net):
        a, b, c = net.cell("a"), net.cell("b"), net.cell("c")
        a2, b2, c2 = net.cell("a2"), net.cell("b2"), net.cell("c2")
        Squarer(a, a2); Squarer(b, b2); Squarer(c, c2)
        Adder(a2, b2, c2)
        return a, b, c

    net = Network()
    a, b, c = triangle(net)
    a.tell(3, 3, {"r"}); b.tell(4, 4, {"r"})
    net.settle()
    assert approx(c.under({"r"}), 5)

    net = Network()
    a, b, c = triangle(net)
    a.tell(3, 3, {"r"}); c.tell(5, 5, {"r"})
    net.settle()
    assert approx(b.under({"r"}), 4)   # same wiring, solved backwards


def test_squarer_unknown_is_not_negative():
    """Regression: v0.1 squared an unknown cell's -inf lower bound into a
    false hard [inf, inf] claim. 'Unknown' must mean [0, inf) under a>=0."""
    net = Network()
    a, c = net.cell("a"), net.cell("c")
    Squarer(a, c)
    net.settle()
    lo, hi = c.under(set())
    assert lo <= 0 + 1e-9 and hi == INF


# ----- v0.2: knowledge carries its justification -----

def test_justification_flows_through_derivation():
    net = Network()
    C, F = thermometer(net)
    C.tell(37, 37, {"thermo"})
    net.settle()
    assert approx(F.under({"thermo"}), 98.6)
    assert F.under(set()) == (-INF, INF)   # without the premise, F knows nothing


def test_contradiction_names_the_guilty():
    net = Network()
    C, F = thermometer(net)
    C.tell(0, 0, {"weather"})
    F.tell(100, 100, {"thermo"})
    net.settle()
    assert any(ng == {"weather", "thermo"} for ng in map(set, net.nogoods))


def test_vague_and_precise_premises_cooperate():
    net = Network()
    C, F = thermometer(net)
    C.tell(0, 40, {"weather"})
    F.tell(100, 100, {"thermo"})
    net.settle()
    assert net.nogoods == []
    assert approx(C.under({"weather", "thermo"}), 37.7777778, tol=1e-4)


# ----- v0.3: rival worldviews, retraction, minimal blame -----

def story(net):
    A, B, C, D, E = (net.cell(n) for n in "ABCDE")
    Adder(A, B, C)
    Adder(C, D, E)
    A.tell(10, 10, {"alice"})
    B.tell(40, 40, {"bob"})
    C.tell(60, 60, {"carol"})
    D.tell(1, 1, {"dave"})
    E.tell(51, 51, {"eve"})
    return A, B, C, D, E


def test_minimal_nogoods():
    net = Network()
    story(net)
    net.settle()
    found = set(map(frozenset, net.nogoods))
    assert frozenset({"alice", "bob", "carol"}) in found
    assert frozenset({"carol", "dave", "eve"}) in found
    # innocents are never blamed alone
    for ng in found:
        assert ng not in ({"dave"}, {"eve"}, {"alice"}, {"bob"})


def test_retraction_is_free():
    net = Network()
    C, F = thermometer(net)
    C.tell(0, 40, {"weather"})
    F.tell(100, 100, {"thermo"})
    net.settle()
    # retracting = just not believing the premise; old knowledge intact
    lo, hi = C.under({"weather"})
    assert abs(lo - 0) < 1e-9 and abs(hi - 40) < 1e-9


def test_parallel_worlds_coexist():
    net = Network()
    C, F = thermometer(net)
    C.tell(0, 0, {"h_freeze"})
    C.tell(100, 100, {"h_boil"})
    net.settle()
    assert approx(F.under({"h_freeze"}), 32)
    assert approx(F.under({"h_boil"}), 212)
    assert any(ng == {"h_freeze", "h_boil"} for ng in map(set, net.nogoods))


# ----- v0.4: trust chooses; ties are admitted; experience updates -----

def frank_story(net):
    A, B, C, D, E = story(net)
    E.tell(61, 61, {"frank"})
    return A, B, C, D, E


def test_equal_trust_is_an_honest_tie():
    net = Network()
    _, _, C, D, E = frank_story(net)
    net.settle()
    ranked = net.believe([C, D, E])
    assert net.winners(ranked) is None            # refuses to pretend
    assert net.experience_update(None) == []      # a tie teaches nothing


def test_trust_breaks_the_tie():
    net = Network()
    _, _, C, D, E = frank_story(net)
    net.settle()
    net.set_trust("carol", 3.0)
    ranked = net.believe([C, D, E])
    assert ranked[0][1][0] == "60"                # believed C = 60
    assert net.winners(ranked) is not None


def test_emergent_sacrifice_world():
    """Documented emergent behavior: with carol trusted 3.0 and gina 2.5,
    the network keeps both good witnesses by doubting low-trust dave,
    concluding D = -9. Nobody programmed this tradeoff."""
    net = Network()
    _, _, C, D, E = frank_story(net)
    net.settle()
    net.set_trust("carol", 3.0)
    net.set_trust("gina", 2.5)
    E.tell(51, 51, {"gina"})
    net.settle()
    ranked = net.believe([C, D, E])
    assert ranked[0][1] == ("60", "-9", "51")


def test_physics_constraint_kills_the_sacrifice():
    net = Network()
    _, _, C, D, E = frank_story(net)
    net.settle()
    net.set_trust("carol", 3.0)
    net.set_trust("gina", 2.5)
    net.set_trust("physics", 100.0)
    E.tell(51, 51, {"gina"})
    D.tell(0, 1000, {"physics"})
    net.settle()
    ranked = net.believe([C, D, E])
    assert ranked[0][1] == ("50", "1", "51")      # photo finish, reality wins


def test_experience_update_direction():
    net = Network()
    net.premises.update({"good", "bad"})
    changes = net.experience_update({"good"})
    d = {p: (old, new) for p, old, new in changes}
    assert d["good"][1] > d["good"][0]
    assert d["bad"][1] < d["bad"][0]


# ----- v0.4.1: the pruning that moved the wall -----

def test_subsumption_keeps_tables_small_and_fast():
    """Regression: this exact 8-premise scenario took 245s / ~390 rows
    before pruning. Locked in: must stay fast and small."""
    t0 = time.time()
    net = Network()
    A, B, C, D, E = frank_story(net)
    net.settle()
    E.tell(51, 51, {"gina"})
    D.tell(0, 1000, {"physics"})
    net.settle()
    elapsed = time.time() - t0
    total_rows = sum(c.rows() for c in (A, B, C, D, E))
    assert elapsed < 5.0, f"too slow: {elapsed:.2f}s"
    assert total_rows < 120, f"table blow-up: {total_rows} rows"


# ----- v0.5: the machine invents its own structure -----

def test_induction_prediction_and_falsification():
    memory = Network()                       # holds trust + laws across episodes
    law = memory.induce([(10, 15), (20, 25), (7, 12)], "Price", "Total")
    assert law == "law:Total=Price+5"
    assert memory.trust_of(law) == 2.0       # trust earned from evidence

    # prediction, forward
    ep = memory.successor()
    P, T = ep.cell("Price"), ep.cell("Total")
    ep.wire_laws({"Price": P, "Total": T})
    P.tell(40, 40, {"order"})
    ep.settle()
    assert approx(T.under({"order", law}), 45)

    # prediction, BACKWARD through the machine's own law
    ep = memory.successor()
    P, T = ep.cell("Price"), ep.cell("Total")
    ep.wire_laws({"Price": P, "Total": T})
    T.tell(52, 52, {"invoice"})
    ep.settle()
    assert approx(P.under({"invoice", law}), 47)

    # falsification and demotion
    ep = memory.successor()
    ep.set_trust("receipt_P", 2.5)
    ep.set_trust("receipt_T", 2.5)
    P, T = ep.cell("Price"), ep.cell("Total")
    ep.wire_laws({"Price": P, "Total": T})
    P.tell(100, 100, {"receipt_P"})
    T.tell(120, 120, {"receipt_T"})
    ep.settle()
    assert any(law in ng for ng in ep.nogoods)
    ranked = ep.believe([P, T])
    assert ranked[0][1] == ("100", "120")    # reality outweighs the law
    before = ep.trust_of(law)
    ep.experience_update(ep.winners(ranked))
    assert ep.trust_of(law) < before         # the machine demotes its invention
    assert memory.trust_of(law) < 2.0        # ...and the MEMORY remembers


# ----- v1.0: architecture guarantees -----

def test_networks_are_independent():
    """The reason the Network object exists: no shared global state."""
    n1, n2 = Network(), Network()
    C1, F1 = thermometer(n1)
    C2, F2 = thermometer(n2)
    C1.tell(0, 0, {"r"})
    C2.tell(100, 100, {"r"})
    F1.tell(100, 100, {"clash"})             # contradiction in n1 only
    n1.settle()
    n2.settle()
    assert n1.nogoods and not n2.nogoods     # n1's conflict never leaks to n2
    assert approx(F2.under({"r"}), 212)


def test_fmt_never_lies():
    """Regression: an empty interval once displayed as a real value,
    hiding an inconsistency. IMPOSSIBLE must be IMPOSSIBLE."""
    assert fmt((60, 50)) == "IMPOSSIBLE"
    assert fmt((-INF, INF)) == "?"
    assert fmt((5, 5)) == "5"





# ----- v1.1: features demanded by real usage (the budget example) -----

def test_sum_forward_and_backward():
    from constraint_cells import Sum
    net = Network()
    total = net.cell("total")
    a, b, c, d = (net.cell(n) for n in "abcd")
    Sum(total, [a, b, c, d])
    a.tell(1, 1, {"r"}); b.tell(2, 2, {"r"}); c.tell(3, 3, {"r"})
    d.tell(4, 4, {"r"})
    net.settle()
    assert approx(total.under({"r"}), 10)

    net = Network()
    total = net.cell("total")
    a, b, c, d = (net.cell(n) for n in "abcd")
    Sum(total, [a, b, c, d])
    total.tell(10, 10, {"r"})
    a.tell(1, 1, {"r"}); b.tell(2, 2, {"r"}); d.tell(4, 4, {"r"})
    net.settle()
    assert approx(c.under({"r"}), 3)     # solves for the missing term


def test_tell_trust_parameter():
    from constraint_cells import FACT, WISH
    net = Network()
    x = net.cell("x")
    x.tell(1, 1, {"doc"}, trust=FACT)
    x.tell(0, 5, {"hope"}, trust=WISH)
    assert net.trust_of("doc") == 3.0
    assert net.trust_of("hope") == 1.0
    x.tell(1, 1, {"doc"}, trust=1.5)     # last write wins
    assert net.trust_of("doc") == 1.5


def test_believed_convenience():
    net = Network()
    C, F, t = net.cell("C"), net.cell("F"), net.cell("t")
    Multiplier(C, 1.8, t); Adder(t, net.constant(32), F)
    C.tell(0, 0, {"h1"})
    C.tell(100, 100, {"h2"})
    net.settle()
    assert net.believed(F) is None       # honest tie
    net.set_trust("h1", 2.0)
    assert approx(net.believed(F), 32)   # trust breaks it


def test_budget_scenario_with_v11_api():
    """The full real-world scenario that spec'd v1.1, as a regression test."""
    from constraint_cells import Sum, FACT, ESTIMATE, WISH
    net = Network()
    Income, Rent, Food, Transport, Savings = (
        net.cell(n) for n in
        ("Income", "Rent", "Food", "Transport", "Savings"))
    Sum(Income, [Rent, Food, Transport, Savings])
    Income.tell(2000, 2000, {"payslip"}, trust=FACT)
    Rent.tell(800, 800, {"landlord"}, trust=FACT)
    Transport.tell(150, 150, {"transport_pass"}, trust=FACT)
    Food.tell(350, 450, {"grocery_history"}, trust=ESTIMATE)
    Savings.tell(700, 700, {"savings_goal"}, trust=WISH)
    Food.tell(400, INF, {"honesty"}, trust=ESTIMATE)
    net.settle()
    assert net.nogoods, "goal vs honesty conflict must be detected"
    lo, hi = net.believed(Savings)
    assert abs(lo - 600) < 1e-6 and abs(hi - 650) < 1e-6
    # the facts must never be the ones sacrificed
    ranked = net.believe([Savings])
    top_camps = ranked[0][2]
    for w in top_camps:
        assert {"payslip", "landlord", "transport_pass"} <= w





# ----- v1.2: explain(), retraction, and the console -----

def test_explain_names_binding_premises():
    net = Network()
    C, F, t = net.cell("C"), net.cell("F"), net.cell("t")
    Multiplier(C, 1.8, t); Adder(t, net.constant(32), F)
    C.tell(0, 40, {"weather"})
    F.tell(100, 100, {"thermo"})
    net.settle()
    text = C.explain({"weather", "thermo"})
    assert "37.77" in text
    assert "thermo" in text          # the binding premise is named


def test_explain_admits_ties():
    net = Network()
    C, F, t = net.cell("C"), net.cell("F"), net.cell("t")
    Multiplier(C, 1.8, t); Adder(t, net.constant(32), F)
    C.tell(0, 0, {"h1"})
    C.tell(100, 100, {"h2"})
    net.settle()
    assert "TIE" in F.explain()


def test_retract_and_restore():
    net = Network()
    C, F, t = net.cell("C"), net.cell("F"), net.cell("t")
    Multiplier(C, 1.8, t); Adder(t, net.constant(32), F)
    C.tell(0, 0, {"h1"})
    C.tell(100, 100, {"h2"})
    net.settle()
    assert net.believed(F) is None            # tie
    net.retract("h2")
    assert approx(net.believed(F), 32)        # h1's world, instantly
    net.restore("h2"); net.retract("h1")
    assert approx(net.believed(F), 212)       # h2's world, no recompute


def test_console_full_session():
    from console import Console
    c = Console()
    script = [
        "cell Income Rent Food Transport Savings",
        "sum Income = Rent + Food + Transport + Savings",
        "fact payslip: Income = 2000",
        "fact landlord: Rent = 800",
        "fact transport_pass: Transport = 150",
        "estimate groceries: Food = 350..450",
        "wish goal: Savings = 700",
        "estimate honesty: Food = 400..",
    ]
    for line in script:
        assert c.handle(line) is True
    assert c.net.nogoods                      # conflict detected
    lo, hi = c.net.believed(c.cells["Savings"])
    assert hi <= 650 + 1e-6                   # goal loses to facts
    assert "Savings" in c.cells["Savings"].explain()
    assert c.handle("quit") is False



# ----- v1.3: incremental propagation -----

def test_incremental_propagation_scales():
    """Regression for the v1.3 engine upgrade. This exact scenario took
    7.31s / 857 wake-ups on v1.2 (propagators re-crossed every belief row
    on every wake-up). Incremental propagation — process only rows added
    or narrowed since last run, plus queue dedup — must keep it fast, on
    the SAME answer."""
    import time as _t
    net = Network()
    n_inputs, n_witnesses = 6, 10
    xs = [net.cell(f"x{i}") for i in range(n_inputs)]
    prev = xs[0]; sums = []
    for i in range(1, n_inputs):
        s = net.cell(f"s{i}"); Adder(prev, xs[i], s)
        sums.append(s); prev = s
    for i, x in enumerate(xs):
        x.tell(10 * i, 10 * i + 4, {f"base{i}"})
    total = sums[-1]
    for w in range(n_witnesses):
        total.tell(w * 0.5,
                   10 * sum(range(n_inputs)) + 4 * n_inputs - w * 0.5,
                   {f"w{w}"})
    t0 = _t.time()
    steps = net.settle()
    elapsed = _t.time() - t0
    world = ({f"base{i}" for i in range(n_inputs)}
             | {f"w{i}" for i in range(n_witnesses)})
    lo, hi = total.under(world)
    assert abs(lo - 150) < 1e-6 and abs(hi - 169.5) < 1e-6  # same answer
    assert elapsed < 3.0, f"too slow: {elapsed:.2f}s (v1.2 took 7.31s)"
    assert steps < 100, f"wake-up storm: {steps} (v1.2 took 857)"


# ===========================================================================
# RUNNER — MUST BE THE LAST THING IN THIS FILE.
# Python executes top-to-bottom: any test defined below this block
# will silently never run (this bit us twice). Add new tests ABOVE.
if __name__ == "__main__":
    import sys
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

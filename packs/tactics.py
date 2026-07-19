"""packs/tactics.py — Domain Pack #1: adversarial decision-making.

The domain: I have options, an adversary responds, outcomes are uncertain,
resources are limited — pick the move whose WORST case I can live with.
The test rig: a 2-turn duel. The machinery is domain-blind: swap
attack/defend/heal for cut_price/hold/bundle and HP for cash, and this
same file plans a pricing standoff.

What this pack adds ON TOP of the kernel (which is untouched):
  - time, encoded as cells per turn (myHP_t0, myHP_t1, ...)
  - actions, encoded as premises ("me_t1:attack")
  - an Effect propagator: state flows turn-to-turn under action premises
  - mutual exclusivity of actions, declared as nogoods
  - a maximin brain: choose the plan with the best worst-case future
  - explainable tactics: every recommendation traces to premises

KERNEL DEMANDS THIS PACK DISCOVERED — and their status:
  1. Public Propagator base ............ SHIPPED in v1.4 (used below)
  2. Max/Min for HP caps ............... SHIPPED in v1.4 (pack adopts them
     in its next revision, together with the score-function fix — one
     behavior change per release)
  3. Conditional termination ........... DEFERRED (research-sized; futures
     where the foe died at turn 1 still get a turn 2 planned)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from itertools import product
from constraint_cells import Network, fmt, INF, Propagator


class Effect(Propagator):
    """dst = src + [dlo, dhi], but ONLY in worlds where all the given
    action premises hold. The pack's one new propagator — same pattern
    as the kernel's LawAdder: stamp the premises onto everything."""

    def __init__(self, src, dst, dlo, dhi, premises):
        super().__init__(src, dst)
        self.src, self.dst = src, dst
        self.dlo, self.dhi = dlo, dhi
        self.premises = frozenset(premises)
        self.net.premises.update(self.premises)

    def run(self):
        P = self.premises
        fs, fd = self.fresh(self.src), self.fresh(self.dst)
        self.mark(self.src, self.dst)
        for S, I in fs:
            if not self.net.is_bad(S | P):
                self.dst.tell(I[0] + self.dlo, I[1] + self.dhi, S | P)
        for S, I in fd:
            if not self.net.is_bad(S | P):
                self.src.tell(I[0] - self.dhi, I[1] - self.dlo, S | P)


def exclusive(net, *premises):
    """Declare that these premises are mutually exclusive choices:
    no world may contain two of them."""
    ps = list(premises)
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            net.record_nogood(frozenset({ps[i], ps[j]}))


# ---------------------------------------------------------------------------
# The duel
# ---------------------------------------------------------------------------

MY_ACTIONS = ("attack", "defend", "heal")
FOE_ACTIONS = ("attack", "defend")

# net effect on (myHP, foeHP) for each (my_action, foe_action) combo per turn
EFFECTS = {
    # mine       foe        my_delta      foe_delta
    ("attack", "attack"): ((-9, -6),    (-10, -5)),
    ("attack", "defend"): ((0, 0),      (-3, -1)),   # foe blocks most of it
    ("defend", "attack"): ((-3, -1),    (0, 0)),     # I block most of it
    ("defend", "defend"): ((0, 0),      (0, 0)),
    ("heal",   "attack"): ((-5, 0),     (0, 0)),     # heal 4..6 minus 6..9
    ("heal",   "defend"): ((4, 6),      (0, 0)),
}


def build_duel(my_hp=12, foe_hp=11, turns=2):
    net = Network()
    me = [net.cell(f"myHP_t{t}") for t in range(turns + 1)]
    foe = [net.cell(f"foeHP_t{t}") for t in range(turns + 1)]
    me[0].tell(my_hp, my_hp, {"start"})
    foe[0].tell(foe_hp, foe_hp, {"start"})
    for t in range(1, turns + 1):
        exclusive(net, *[f"me_t{t}:{a}" for a in MY_ACTIONS])
        exclusive(net, *[f"foe_t{t}:{a}" for a in FOE_ACTIONS])
        for (mine, theirs), (my_d, foe_d) in EFFECTS.items():
            prem = {f"me_t{t}:{mine}", f"foe_t{t}:{theirs}"}
            Effect(me[t - 1], me[t], my_d[0], my_d[1], prem)
            Effect(foe[t - 1], foe[t], foe_d[0], foe_d[1], prem)
    net.settle()
    return net, me, foe


def world_for(my_plan, foe_plan):
    w = {"start"}
    for t, a in enumerate(my_plan, 1):
        w.add(f"me_t{t}:{a}")
    for t, a in enumerate(foe_plan, 1):
        w.add(f"foe_t{t}:{a}")
    return w


def plan(net, me, foe, turns=2):
    """Maximin: for each of my plans, find the foe reply that hurts most;
    choose the plan whose WORST future is best. Returns
    (best_plan, worst_reply, report)."""
    report = []
    for my_plan in product(MY_ACTIONS, repeat=turns):
        worst_score, worst_reply, worst_state = INF, None, None
        for foe_plan in product(FOE_ACTIONS, repeat=turns):
            w = world_for(my_plan, foe_plan)
            my_final = me[turns].under(w)
            foe_final = foe[turns].under(w)
            # conservative score: my guaranteed HP minus foe's best-case HP
            score = my_final[0] - foe_final[1]
            report.append([my_plan, foe_plan, my_final, foe_final, score])
            if score < worst_score:
                worst_score = score
                worst_reply = foe_plan
                worst_state = (my_final, foe_final)
        report.append([my_plan, "WORST", worst_state[0], worst_state[1],
                       worst_score, worst_reply])
    best = max((r for r in report if r[1] == "WORST"), key=lambda r: r[4])
    return best[0], best[5], report


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    net, me, foe = build_duel()
    turns = 2
    best_plan, worst_reply, report = plan(net, me, foe, turns)

    print("THE DUEL — me: 12 HP, foe: 11 HP, thinking 2 turns ahead\n")
    print("every plan, judged by its WORST surviving future:")
    for r in report:
        if r[1] != "WORST":
            continue
        mark = "  <== CHOSEN" if r[0] == best_plan else ""
        print(f"  {'+'.join(r[0]):15s} worst case: "
              f"me={fmt(r[2]):12s} foe={fmt(r[3]):12s} "
              f"score={r[4]:6.1f}{mark}")

    print(f"\nDECISION: {' then '.join(best_plan)}")
    print(f"hardest reply: foe plays {' then '.join(worst_reply)}")
    w = world_for(best_plan, worst_reply)
    print("\nWHY (the machine's own account of that future):")
    print(me[turns].explain(w))
    print()
    print(foe[turns].explain(w))

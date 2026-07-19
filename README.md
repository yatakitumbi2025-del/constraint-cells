# Constraint Cells

A tiny, self-revising computational fabric. Pure Python, zero dependencies,
runs on a phone. Built as a sequence of falsifiable experiments toward one
question:

> Instead of executing instructions, can computation self-assemble from
> relationships — and can such a machine justify, revise, and extend
> its own beliefs?

Every claim in this repository is locked in by `test_cells.py`
(20 assertions, no test framework needed) and demonstrated by a runnable
example. Nothing here requires more hardware than a mobile phone.

## The one rule

A **cell** holds an interval of possible values `[lo, hi]`. It can only ever
**narrow**. Never widen. Information only accumulates. **Propagators** are
dumb local rules ("a + b = c") that push knowledge between cells in every
direction until the network settles. There is no program counter, no
execution order, no algorithm — only relationships and flow.

Everything else falls out of that rule.

## Layout

```
constraint_cells.py   the library (one file, no dependencies)
test_cells.py         every claim as an assertion; run: python3 test_cells.py
examples/
  01_bidirectional.py       wire F = C*1.8+32 once; get converter, reverse
                            converter, and range propagation for free
  02_justified_knowledge.py beliefs remember their premises; retraction free
  03_rival_worlds.py        contradictions blame minimally; camps coexist
  04_trust_and_choice.py    trust breaks ties; ties are admitted honestly;
                            outcomes reshape trust
  05_invention.py           the machine induces a law from raw data, installs
                            its own propagator, predicts in BOTH directions,
                            and demotes the law when reality contradicts it
```

## Quick start

Any Python 3. No installs. On Android: Pydroid 3 or Termux. iPhone: a-Shell.

```
python3 test_cells.py          # 20/20 expected
cd examples && python3 05_invention.py
```

As a library:

```python
from constraint_cells import Network, Adder, Multiplier

net = Network()
C, F, t = net.cell("Celsius"), net.cell("Fahrenheit"), net.cell("t")
Multiplier(C, 1.8, t)
Adder(t, net.constant(32), F)
F.tell(212, 212, {"reading"})
net.settle()
C.under({"reading"})           # -> (100.0, 100.0)
```

All state lives in the `Network` object — any number of independent networks
can coexist (this is tested).

## What's new in v1.4 — the pack-author contract

Every item was demanded by Domain Pack #1 (`packs/tactics.py`), which was
deliberately built BEFORE this release so the kernel's next features would
be discovered, not guessed:

- **Public `Propagator` base** — subclass it, use `fresh(cell)` / `mark()`,
  implement `run()`. This interface is covered by tests and will not move;
  it is the contract that makes packs safe to build. (`_Propagator` remains
  as a compatibility alias.)
- **`Max` / `Min` propagators** — full multi-directional interval semantics,
  including the inference "if the other input provably can't reach the
  maximum, this one must supply it".
- **`Clamp(x, lo, hi, out)`** — sugar over Max+Min, for quantities with hard
  floors and ceilings (the pack's HP that shouldn't go below 0).
- Deliberately deferred: conditional termination (planning stops in futures
  where the game already ended) — research-sized, kept on the roadmap.

The tactics pack now runs on the public API with byte-identical output.
One behavior change per release: the pack's score-function fix (it
currently turtles — see its test's docstring) ships separately, next.

## What's new in v1.3 — the engine got 100x stronger, the API didn't move

Incremental propagation: propagators now remember what they have already
processed and act only on belief rows added or *narrowed* since their last
wake-up, and the scheduler refuses duplicate wake-ups. Measured on the
frozen benchmark (6-input adder pipeline, 10 interval witnesses):

- v1.2: **7.31 s**, 857 propagator wake-ups
- v1.3: **0.07 s**, 17 wake-ups — identical answer, bit for bit

Configs the old engine could not touch now run comfortably
(12 inputs / 20 witnesses: 1.1 s). Every prior test passes unchanged —
no public signature moved, which is the contract that makes future
domain packs safe to build on this core.

## What's new in v1.2

The machine can now answer WHY — reasons are retrieved, not generated:

- `cell.explain()` — names which premises set which bound of a believed
  value, and honestly reports ties between worldviews.
- `net.retract(p)` / `net.restore(p)` — stop or resume believing a
  premise; knowledge is filtered, never destroyed.
- `console.py` — an interactive reasoning console: state facts,
  estimates, and wishes, then interrogate the network
  (`why`, `believe`, `conflicts`, `retract`).

## What's new in v1.1

Every v1.1 feature was demanded by real usage (`examples/06_budget.py`),
not guessed:

- `Sum(total, [terms])` — n-ary sums without hand-made intermediate cells.
  Implemented as sugar over a hidden chain of the tested pairwise `Adder`,
  so every existing guarantee holds automatically.
- `net.believed(cell)` — the value under the winning worldview in one call
  (returns `None` on a genuine tie).
- `tell(..., trust=...)` with `FACT` / `ESTIMATE` / `WISH` constants —
  encoding the budget example's lesson: a payslip is not a wish, and a
  network told all sources are equal will happily doubt your income to
  protect your goals.

## Measured results

The architecture's historical enemy is combinatorial explosion of belief
combinations — the reason truth-maintenance systems stayed academic. We hit
it, measured it, and moved it:

- 8 premises, naive: **245 s**, ~390 belief rows
- with subsumption pruning (a belief is dead weight if a belief with fewer
  assumptions is at least as tight): **0.04 s**, 39 rows — identical
  conclusions, identical impossibility proofs.

This bound is a regression test, not a claim. Honest note: pruning defers
the exponential; it does not repeal it. Dense conflict networks with many
premises will still hurt. That is the known frontier, not a hidden flaw.

## Documented emergent behavior

With one witness highly trusted, the network reconciles conflicting
testimony by *doubting the least-trusted witness* — inventing a world
nobody programmed (see `test_emergent_sacrifice_world`). A single physical
constraint (`D >= 0`) kills that world and flips belief by half a trust
point. Both behaviors are locked in as tests.

## What this is not

- Not a CPU replacement, and not trying to be one from a phone.
- Not novel science: the lineage is real and credited below. The
  contribution is a minimal, reproducible, phone-runnable synthesis of that
  lineage plus a trust/experience layer, with every claim under test.
- The law induction is deliberately primitive (constant offsets from 3+
  observations). Real induction — choosing which hypotheses to even try —
  is the open problem, not an implementation detail.

## Prior art and reading

- Sussman & Radul, *The Art of the Propagator* (MIT CSAIL, 2009) —
  the propagator model this project rebuilds and extends.
- de Kleer, *An Assumption-based Truth Maintenance System* (1986) —
  the belief-table idea.
- Constraint satisfaction, dataflow architectures, cellular automata —
  the wider family. This lineage lost to von Neumann machines in the 1970s
  largely for economic reasons, not conceptual ones.

## Roadmap

- Incremental propagation: propagators currently re-cross all belief rows
  when woken; propagating only *new* rows is the next performance frontier.
- Structure death: laws falsified often enough get uninstalled, not just
  demoted.
- Attention: the machine decides which cell pairs are worth watching for
  laws, instead of being told.
- Richer induction: multiplicative, threshold, multi-variable laws.

## Origin

Started as a thought experiment: "what would you build after the transistor —
not a smarter switch, but a better organization of computation?" This
repository is that idea reduced to its smallest living form, one falsifiable
version at a time, built and tested entirely on a mobile phone.

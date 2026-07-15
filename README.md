# Constraint Cells

A tiny, self-revising computational fabric. Pure Python, zero dependencies,
runs on a phone. Built as a sequence of five falsifiable experiments toward
one question:

> Instead of executing instructions, can computation self-assemble from
> relationships — and can such a machine justify, revise, and extend
> its own beliefs?

Every claim below is demonstrated by a runnable file in this repository.
Nothing here requires more hardware than a mobile phone.

## The one rule

A **cell** holds an interval of possible values `[lo, hi]`. It can only ever
**narrow**. Never widen. Information only accumulates. **Propagators** are
dumb local rules ("a + b = c") that push knowledge between cells in every
direction until the network settles. There is no program counter, no
execution order, no algorithm — only relationships and flow.

Everything else in this project falls out of that rule.

## The five experiments

| File | Claim tested | Result |
|---|---|---|
| `cells.py` (v0.1) | Computation can self-assemble from stated relationships | Wire `F = C*1.8 + 32` once: get the forward converter, the reverse converter, a range propagator, and a consistency checker for free. Pythagoras solves for any side of the triangle from the other two, same network, zero new code. |
| `cells_v2.py` (v0.2) | Knowledge can carry its own justification | Every belief remembers which assumptions it rests on. Contradictions name the clashing premises instead of just failing. |
| `cells_v3.py` (v0.3) | A machine can hold rival worldviews | Truth maintenance: each cell keeps one belief per premise-combination. Retraction is free (knowledge is filtered, never destroyed). Incompatible hypotheses coexist in one network, which also proves which combinations are impossible and enumerates the maximal consistent "camps". |
| `cells_v4.py` (v0.4) | A machine can choose, and be changed by events | Premises carry trust scores; the network believes the best-scoring conclusion, admits genuine ties, and updates trust from outcomes. Includes the subsumption-pruning fix (see Results). |
| `cells_v5.py` (v0.5) | A machine can invent its own structure | From raw data pairs it induces a law, installs its own propagator for it, trusts it in proportion to evidence, predicts with it (in both directions), and demotes it when reality contradicts it. Invent → test → revise, as executable code. |

## Quick start

Any Python 3. No installs. On Android: Pydroid 3 or Termux. On iPhone: a-Shell.

```
python3 cells_v5.py
```

Each file is self-contained and prints an annotated demo of its claims.

## Measured results

The architecture's historical enemy is combinatorial explosion of belief
combinations — the reason truth-maintenance systems stayed academic. We hit
it, measured it, and moved it:

- 8 premises, naive: **245 s**, ~390 belief rows
- 8 premises, with subsumption pruning (a row is dead weight if a row with
  fewer assumptions is at least as tight): **0.04 s**, 39 rows —
  identical conclusions and identical impossibility proofs.

Honest note: pruning defers the exponential; it does not repeal it. Dense
conflict networks with many premises will still hurt. That is the known
frontier, not a hidden flaw.

## What this is not

- Not a CPU replacement, and not trying to be one from a phone.
- Not novel science: the lineage is real and credited below. The
  contribution here is a minimal, reproducible, phone-runnable synthesis
  of that lineage plus a trust/learning layer, built and verified in the open.
- The law-induction in v0.5 is deliberately primitive (constant offsets
  from 3+ observations). Real induction — choosing which hypotheses to
  even try — is the open problem, not an implementation detail.

## Prior art and reading

- Sussman & Radul, *The Art of the Propagator* (MIT CSAIL, 2009) —
  the propagator model this project independently rebuilds and extends.
- de Kleer, *An Assumption-based Truth Maintenance System* (1986) —
  the belief-table idea in v0.3.
- Constraint satisfaction, dataflow architectures, cellular automata —
  the wider family. This design lineage lost to von Neumann machines in
  the 1970s largely for economic reasons, not conceptual ones.

## Roadmap

- v0.6 — structure death: laws falsified often enough get uninstalled,
  not just demoted.
- Attention: the machine decides which cell pairs are worth watching for
  laws, instead of being told.
- Richer induction: multiplicative, threshold, multi-variable laws.
- Scaling experiments: where exactly is the next wall, in premises and cells?

## Origin

Started as a thought experiment: "what would you build after the
transistor — not a smarter switch, but a better organization of
computation?" This repository is that idea reduced to its smallest living
form, one falsifiable version at a time, built and tested entirely on a
mobile phone.

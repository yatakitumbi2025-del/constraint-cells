"""console.py — talk to your machine.

A tiny declarative language over constraint_cells. You state facts,
estimates, and wishes; the network believes, conflicts, chooses — and
answers WHY. Run:

    python3 console.py            # interactive
    python3 console.py < script   # scripted session

Commands:
    cell NAME [NAME ...]              create cells
    sum TOTAL = A + B + C             constrain: TOTAL is the sum of terms
    fact NAME: CELL = VALUE           claim with trust 3.0 (a document)
    estimate NAME: CELL = VALUE       claim with trust 2.0 (a guess)
    wish NAME: CELL = VALUE           claim with trust 1.0 (a hope)
    why CELL                          explain the believed value
    believe CELL [CELL ...]           show ranked rival worldviews
    conflicts                         show impossible premise combinations
    retract NAME / restore NAME       stop / resume believing a premise
    trust [NAME VALUE]                show trust table, or set one
    cells                             list cells with believed values
    help / quit

VALUE forms:  2000    350..450    400..    ..400
"""
import sys
from constraint_cells import (
    Network, Sum, fmt, print_belief, INF, FACT, ESTIMATE, WISH)


def parse_value(text):
    text = text.strip()
    if ".." in text:
        lo_s, hi_s = text.split("..", 1)
        lo = float(lo_s) if lo_s.strip() else -INF
        hi = float(hi_s) if hi_s.strip() else INF
        return lo, hi
    v = float(text)
    return v, v


class Console:
    def __init__(self):
        self.net = Network()
        self.cells = {}

    def get_cell(self, name):
        if name not in self.cells:
            raise ValueError(f"no cell named '{name}' — create it: cell {name}")
        return self.cells[name]

    def claim(self, trust, rest):
        premise, expr = rest.split(":", 1)
        cell_name, value = expr.split("=", 1)
        lo, hi = parse_value(value)
        cell = self.get_cell(cell_name.strip())
        cell.tell(lo, hi, {premise.strip()}, trust=trust)
        self.net.settle()
        if self.net.nogoods:
            print(f"  noted. CONFLICT now exists — type 'conflicts' to see it.")
        else:
            print(f"  noted: {cell.name} = {fmt((lo, hi))} "
                  f"per '{premise.strip()}'")

    def handle(self, line):
        line = line.strip()
        if not line or line.startswith("#"):
            return True
        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()

        if cmd in ("quit", "exit"):
            return False
        elif cmd == "help":
            print(__doc__)
        elif cmd == "cell":
            for name in rest.split():
                self.cells[name] = self.net.cell(name)
            print("  created:", ", ".join(rest.split()))
        elif cmd == "sum":
            total_name, terms_expr = rest.split("=", 1)
            terms = [self.get_cell(t.strip())
                     for t in terms_expr.split("+")]
            Sum(self.get_cell(total_name.strip()), terms)
            self.net.settle()
            print(f"  constrained: {total_name.strip()} = "
                  f"{' + '.join(t.name for t in terms)}")
        elif cmd == "fact":
            self.claim(FACT, rest)
        elif cmd == "estimate":
            self.claim(ESTIMATE, rest)
        elif cmd == "wish":
            self.claim(WISH, rest)
        elif cmd == "why":
            print(self.get_cell(rest.strip()).explain())
        elif cmd == "believe":
            cells = [self.get_cell(n) for n in rest.split()]
            print_belief(self.net, "ranked worldviews:", cells)
        elif cmd == "conflicts":
            if not self.net.nogoods:
                print("  none — all beliefs coexist.")
            for ng in self.net.nogoods:
                print("  can't ALL be true:", sorted(ng))
        elif cmd == "retract":
            self.net.retract(rest.strip())
            print(f"  no longer believing '{rest.strip()}' "
                  f"(knowledge kept, filtered)")
        elif cmd == "restore":
            self.net.restore(rest.strip())
            print(f"  believing '{rest.strip()}' again")
        elif cmd == "trust":
            if rest.strip():
                name, value = rest.split()
                self.net.set_trust(name, float(value))
                print(f"  trust[{name}] = {value}")
            else:
                for p in sorted(self.net.premises):
                    flag = "  (retracted)" if p in self.net.retracted else ""
                    print(f"  {p}: {self.net.trust_of(p)}{flag}")
        elif cmd == "cells":
            for name, cell in self.cells.items():
                v = self.net.believed(cell)
                print(f"  {name} = {fmt(v) if v else '(tie)'}")
        else:
            print(f"  unknown command '{cmd}' — type 'help'")
        return True


def main():
    console = Console()
    interactive = sys.stdin.isatty()
    if interactive:
        print("constraint-cells console — type 'help' for commands")
    for line in sys.stdin:
        if not interactive:
            print(f"> {line.rstrip()}")
        try:
            if not console.handle(line):
                break
        except Exception as e:
            print(f"  error: {e}")
        if interactive:
            print("> ", end="", flush=True)


if __name__ == "__main__":
    main()

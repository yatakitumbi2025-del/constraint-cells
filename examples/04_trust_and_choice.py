"""v0.4's claim: trust chooses; ties are admitted; experience updates."""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, Adder, print_belief

net = Network()
A, B, C, D, E = (net.cell(n) for n in "ABCDE")
Adder(A, B, C); Adder(C, D, E)
A.tell(10, 10, {"alice"}); B.tell(40, 40, {"bob"})
C.tell(60, 60, {"carol"}); D.tell(1, 1, {"dave"})
E.tell(51, 51, {"eve"}); E.tell(61, 61, {"frank"})
net.settle()

print_belief(net, "equal trust — honest deadlock:", [C, D, E])

net.set_trust("carol", 3.0)
print_belief(net, "carol is a calibrated instrument (3.0):", [C, D, E])

net.set_trust("gina", 2.5)
E.tell(51, 51, {"gina"}); net.settle()
winners = print_belief(net, "gina (2.5) reports E=51:", [C, D, E])

print("experience reshapes trust:")
for p, old, new in net.experience_update(winners):
    print(f"  trust[{p}]: {old} -> {new}")

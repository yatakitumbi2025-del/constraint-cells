"""v0.3's claim: rival worldviews coexist; blame is minimal."""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, Adder

net = Network()
A, B, C, D, E = (net.cell(n) for n in "ABCDE")
Adder(A, B, C); Adder(C, D, E)
A.tell(10, 10, {"alice"}); B.tell(40, 40, {"bob"})
C.tell(60, 60, {"carol"}); D.tell(1, 1, {"dave"})
E.tell(51, 51, {"eve"})
net.settle()

print("impossible combinations (nobody else blamed):")
for ng in net.nogoods:
    print("  can't all be true:", sorted(ng))
print("surviving camps:")
for w in net.rival_camps():
    print(" ", sorted(w))

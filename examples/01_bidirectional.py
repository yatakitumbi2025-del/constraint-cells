"""v0.1's claim: wire a relationship ONCE, get every algorithm free."""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, Adder, Multiplier, fmt

def thermometer(net):
    C, F, t = net.cell("Celsius"), net.cell("Fahrenheit"), net.cell("t")
    Multiplier(C, 1.8, t)
    Adder(t, net.constant(32), F)
    return C, F

net = Network(); C, F = thermometer(net)
F.tell(212, 212, {"reading"}); net.settle()
print("set F=212        ->  C =", fmt(C.under({"reading"})))

net = Network(); C, F = thermometer(net)
C.tell(37, 37, {"reading"}); net.settle()
print("set C=37         ->  F =", fmt(F.under({"reading"})))

net = Network(); C, F = thermometer(net)
C.tell(20, 25, {"reading"}); net.settle()
print("set C=[20..25]   ->  F =", fmt(F.under({"reading"})))

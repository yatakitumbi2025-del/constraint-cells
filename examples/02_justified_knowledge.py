"""v0.2's claim: knowledge remembers WHY it is believed."""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, Adder, Multiplier, fmt

net = Network()
C, F, t = net.cell("Celsius"), net.cell("Fahrenheit"), net.cell("t")
Multiplier(C, 1.8, t); Adder(t, net.constant(32), F)

C.tell(0, 40, {"weather_report"})     # vague
F.tell(100, 100, {"my_thermometer"})  # precise
net.settle()

print("C believing both:        ", fmt(C.under({"weather_report", "my_thermometer"})))
print("C if thermometer broken: ", fmt(C.under({"weather_report"})))
print("C if weather report fake:", fmt(C.under({"my_thermometer"})))
print("conflicts:", [sorted(ng) for ng in net.nogoods] or "none — they cooperate")

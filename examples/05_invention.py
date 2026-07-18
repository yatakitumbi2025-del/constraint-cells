"""v0.5's claim: the machine invents, uses, and demotes its own structure."""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, fmt, print_belief

memory = Network()   # trust + laws live here, across episodes
law = memory.induce([(10, 15), (20, 25), (7, 12)], "Price", "Total")
print(f"induced from raw data: '{law}'  trust {memory.trust_of(law)}")

ep = memory.successor()
P, T = ep.cell("Price"), ep.cell("Total")
ep.wire_laws({"Price": P, "Total": T})
P.tell(40, 40, {"order"}); ep.settle()
print("Price=40  -> predicted Total =", fmt(T.under({"order", law})))

ep = memory.successor()
P, T = ep.cell("Price"), ep.cell("Total")
ep.wire_laws({"Price": P, "Total": T})
T.tell(52, 52, {"invoice"}); ep.settle()
print("Total=52  -> inferred  Price =", fmt(P.under({"invoice", law})), "(backwards!)")

ep = memory.successor()
ep.set_trust("receipt_P", 2.5); ep.set_trust("receipt_T", 2.5)
P, T = ep.cell("Price"), ep.cell("Total")
ep.wire_laws({"Price": P, "Total": T})
P.tell(100, 100, {"receipt_P"}); T.tell(120, 120, {"receipt_T"})
ep.settle()
winners = print_belief(ep, "reality disagrees with the law:", [P, T])
ep.experience_update(winners)
print(f"law demoted by experience: trust now {memory.trust_of(law)}")

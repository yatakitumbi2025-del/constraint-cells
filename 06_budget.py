"""06_budget.py — the first REAL problem: a budget reality-checker.

Your money as a constraint network:

    Income = Rent + Food + Transport + Savings

Every number carries its source as a premise. The network's job:
catch the moment your plans contradict your money — and tell you
which belief has to give.

Edit the numbers to your real ones. That's the point.
"""
import sys; sys.path.insert(0, "..")
from constraint_cells import Network, Adder, fmt, print_belief, INF

net = Network()

Income    = net.cell("Income")
Rent      = net.cell("Rent")
Food      = net.cell("Food")
Transport = net.cell("Transport")
Savings   = net.cell("Savings")

# Income = Rent + Food + Transport + Savings, built from pair-wise adders.
# (FRICTION NOTE: needing intermediate cells for a 4-term sum is clumsy.)
rf  = net.cell("rent+food")
rft = net.cell("rent+food+transport")
Adder(Rent, Food, rf)
Adder(rf, Transport, rft)
Adder(rft, Savings, Income)

# --- the facts, each with its source ---
Income.tell(2000, 2000, {"payslip"})
Rent.tell(800, 800, {"landlord"})
Transport.tell(150, 150, {"transport_pass"})
Food.tell(350, 450, {"grocery_history"})     # honest range from past months

print("STEP 1 — no goal yet: what does reality allow?")
net.settle()
print("   Savings can be:", fmt(Savings.under(
    {"payslip", "landlord", "transport_pass", "grocery_history"})))

print("\nSTEP 2 — add the goal: save 700/month")
Savings.tell(700, 700, {"savings_goal"})
net.settle()
world = {"payslip", "landlord", "transport_pass", "grocery_history",
         "savings_goal"}
print("   conflicts:", [sorted(ng) for ng in net.nogoods] or "none")
print("   Food is now forced to:", fmt(Food.under(world)))
print("   ^ The network didn't just check the goal — it DERIVED what the")
print("     goal costs: food must sit at the very bottom of its range.")

print("\nSTEP 3 — honesty arrives: food is realistically at least 400")
Food.tell(400, INF, {"honesty"})
net.settle()
print("   conflicts:", [sorted(ng) for ng in net.nogoods])
print("   ^ Now the goal and honesty cannot coexist. Something must give.")

print("\nSTEP 4 — which belief should give? At equal trust: a tie.")
net.set_trust("honesty", 2.0)        # past data doesn't lie
print_belief(net, "the machine's honest confusion:", [Food, Savings])
print("   ^ Note the absurd camps: it will happily doubt your PAYSLIP to")
print("     protect your goal — because we told it all sources are equal.")

print("\nSTEP 5 — the modeling lesson: a payslip is not a wish.")
print("   Documents get trust 3, estimates 2, aspirations 1:")
for doc in ("payslip", "landlord", "transport_pass"):
    net.set_trust(doc, 3.0)          # pieces of paper: hard to doubt
net.set_trust("grocery_history", 2.0)  # estimate from data
net.set_trust("savings_goal", 1.0)     # a wish: first thing to revise
winners = print_belief(net, "the machine's advice:", [Food, Savings])
print("   believable savings this month:", fmt(Savings.under(winners)))
print("   ^ Decisive now: revise the GOAL. The facts stay standing.")

"""06_budget.py — a budget reality-checker (v1.1 API).

Your money as a constraint network:

    Income = Rent + Food + Transport + Savings

Every number carries its source as a premise, and every source carries a
trust category — the lesson this example taught us:

    FACT     (3.0)  pieces of paper: payslip, lease, ticket
    ESTIMATE (2.0)  honest guesses from data
    WISH     (1.0)  goals and hopes: first thing to revise

Edit the numbers to your real ones. That's the point.
"""
import sys; sys.path.insert(0, "..")
from constraint_cells import (
    Network, Sum, fmt, print_belief, INF, FACT, ESTIMATE, WISH)

net = Network()
Income, Rent, Food, Transport, Savings = (
    net.cell(n) for n in ("Income", "Rent", "Food", "Transport", "Savings"))

Sum(Income, [Rent, Food, Transport, Savings])   # one line, no junk cells

Income.tell(2000, 2000, {"payslip"}, trust=FACT)
Rent.tell(800, 800, {"landlord"}, trust=FACT)
Transport.tell(150, 150, {"transport_pass"}, trust=FACT)
Food.tell(350, 450, {"grocery_history"}, trust=ESTIMATE)

net.settle()
world = {"payslip", "landlord", "transport_pass", "grocery_history"}
print("STEP 1 — what does reality allow?")
print("   Savings can be:", fmt(Savings.under(world)))

print("\nSTEP 2 — add the goal: save 700/month")
Savings.tell(700, 700, {"savings_goal"}, trust=WISH)
net.settle()
print("   conflicts:", [sorted(ng) for ng in net.nogoods] or "none")
print("   Food is now forced to:", fmt(Food.under(world | {"savings_goal"})))
print("   ^ The network DERIVED what the goal costs.")

print("\nSTEP 3 — honesty: food is realistically at least 400")
Food.tell(400, INF, {"honesty"}, trust=ESTIMATE)
net.settle()
print("   conflicts:", [sorted(ng) for ng in net.nogoods])

print("\nSTEP 4 — the machine's advice (facts outrank wishes):")
print_belief(net, "ranked worldviews:", [Food, Savings])
print("   believable savings this month:", fmt(net.believed(Savings)))
print("   ^ Revise the GOAL. The facts stay standing.")

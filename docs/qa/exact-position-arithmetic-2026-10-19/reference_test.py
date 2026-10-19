"""Executable arithmetic contract for synthetic paper fixtures, not a product engine.

No API, database, persistence, adapter or real money. Fraction is an exact oracle;
choosing a production representation requires separate performance/DB checks.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import unittest


class Conflict(ValueError):
    pass


def down(value, step):
    if value < 0 or step <= 0:
        raise Conflict("invalid quantity/step")
    return (value // step) * step


def up(value, unit):
    if value < 0 or unit <= 0:
        raise Conflict("invalid reserve/unit")
    return -((-value) // unit)*unit


@dataclass
class Part:
    q: F
    basis: F
    buy_fee_basis: F = F(0)
    debt: F = F(0)
    allocated: F = F(0)
    released: F = F(0)
    proceeds: F = F(0)
    sell_fee: F = F(0)
    mode: str = "copied"

    @property
    def cost(self):
        return self.q*self.basis

    @property
    def remaining_buy_fee(self):
        return self.q*self.buy_fee_basis

    def reduce(self, fraction):
        if not 0 <= fraction <= 1:
            raise Conflict("unproven/out-of-range fraction")
        self.debt += fraction*(self.q-self.debt)

    def detach(self, quantity):
        if not 0 < quantity <= self.q-self.allocated:
            raise Conflict("cannot invalidate an active allocation")
        self.debt *= (self.q-quantity)/self.q
        self.q -= quantity
        return Part(quantity, self.basis, self.buy_fee_basis, mode="manual")

    def change_whole_mode_to_manual(self):
        self.mode = "manual"
        self.debt = F(0)  # still does not cancel an already allocated SELL


class Order:
    def __init__(self, parts, amount, automatic=False):
        if any(p.allocated for p in parts):
            raise Conflict("outcome gate is held")
        weights = [p.debt if automatic else p.q for p in parts]
        total = sum(weights)
        if not 0 < amount <= total:
            raise Conflict("oversell or empty order")
        self.parts, self.amount, self.remaining = parts, amount, amount
        self.weights = [w/total for w in weights]
        self.filled = self.cancelled = self.cash_in = self.cash_fee = F(0)
        self.seen = {}
        for part, weight in zip(parts, self.weights):
            part.allocated = amount*weight

    def fill(self, identity, quantity, proceeds, fee):
        fact = (quantity, proceeds, fee)
        if identity in self.seen:
            if fact != self.seen[identity]:
                raise Conflict("same identity with contradictory facts")
            return
        if not 0 < quantity <= self.remaining or proceeds < 0 or fee < 0:
            raise Conflict("inconsistent fill: preserve evidence for reconciliation")
        allocations = [quantity*w for w in self.weights]
        if any(x > p.q or x > p.allocated for p, x in zip(self.parts, allocations)):
            raise Conflict("allocation no longer matches confirmed ownership")
        for part, x, weight in zip(self.parts, allocations, self.weights):
            part.q -= x
            part.allocated -= x
            part.debt = max(F(0), part.debt-x)
            part.released += x*part.basis
            part.proceeds += proceeds*weight
            part.sell_fee += fee*weight
        self.remaining -= quantity
        self.filled += quantity
        self.cash_in += proceeds
        self.cash_fee += fee
        self.seen[identity] = fact

    def cancel_requested(self):
        pass  # no mathematical fact of final non-execution

    def cancel_confirmed(self):
        for part, weight in zip(self.parts, self.weights):
            part.allocated -= self.remaining*weight
        self.cancelled += self.remaining
        self.remaining = F(0)


class ExactArithmetic(unittest.TestCase):
    def test_internal_parts_may_be_fractions_of_an_atom(self):
        parts = [Part(F(1), F(10)), Part(F(2), F(20))]
        order = Order(parts, F(1))
        order.fill("f", F(1), F(5), F(1, 100))
        self.assertEqual([p.q for p in parts], [F(2, 3), F(4, 3)])
        self.assertEqual(sum(p.q for p in parts), 2)
        self.assertEqual(sum(p.released for p in parts), F(50, 3))
        self.assertEqual(sum(p.proceeds for p in parts), order.cash_in)
        self.assertEqual(sum(p.sell_fee for p in parts), order.cash_fee)

    def test_sale_partition_and_delivery_order_do_not_change_totals(self):
        facts = [("a", F(2, 5), F(3), F(1, 100)), ("b", F(3, 5), F(7), F(2, 100))]
        expected = None
        for messages in [facts, list(reversed(facts)), [("c", F(1), F(10), F(3, 100))]]:
            parts = [Part(F(1), F(10)), Part(F(2), F(20))]
            order = Order(parts, F(1))
            for message in messages:
                order.fill(*message)
            state = [(p.q, p.cost, p.released, p.proceeds, p.sell_fee) for p in parts]
            expected = state if expected is None else expected
            self.assertEqual(state, expected)

    def test_full_close_releases_exact_cost_and_fee_attribution(self):
        p = Part(F(3), F(10, 3), F(1, 9))
        order = Order([p], F(3))
        for i in range(3):
            order.fill(str(i), F(1), F(4), F(1, 100))
            self.assertEqual(p.released+p.cost, 10)
        self.assertEqual((p.q, p.cost, p.remaining_buy_fee), (0, 0, 0))
        self.assertEqual(order.cash_fee, F(3, 100))
        # BUY fee was paid separately; attribution is not a second cash fee.

    def test_detach_does_not_release_cost_or_create_cash(self):
        p = Part(F(3), F(10, 3), F(1, 9), debt=F(1))
        manual = p.detach(F(1))
        self.assertEqual(p.cost+manual.cost, 10)
        self.assertEqual(p.remaining_buy_fee+manual.remaining_buy_fee, F(1, 3))
        self.assertEqual((p.debt, manual.debt), (F(2, 3), 0))
        self.assertEqual(p.proceeds+manual.proceeds, 0)

    def test_split_then_sale_matches_sale_then_split_for_cost(self):
        original_cost, original_qty = F(17), F(7)
        for split in [F(1, 3), F(2), F(7, 2)]:
            copied = Part(original_qty, original_cost/original_qty)
            manual = copied.detach(split)
            for p in [copied, manual]:
                q = p.q/F(2)
                Order([p], q).fill("sale", q, F(1), F(0))
            self.assertEqual(copied.cost+manual.cost, original_cost/2)
            self.assertEqual(copied.released+manual.released, original_cost/2)

    def test_pending_cancel_keeps_allocation_until_final_confirmation(self):
        p = Part(F(20), F(1))
        order = Order([p], F(5))
        order.fill("a", F(2), F(2), F(0))
        order.cancel_requested()
        self.assertEqual((p.q, p.allocated), (18, 3))
        with self.assertRaises(Conflict):
            Order([p], F(1))
        order.cancel_confirmed()
        self.assertEqual((p.q, p.allocated), (18, 0))
        self.assertEqual(order.filled+order.cancelled+order.remaining, order.amount)

    def test_duplicate_and_contradiction_are_distinct(self):
        p = Part(F(2), F(1))
        order = Order([p], F(1))
        order.fill("f", F(1), F(3), F(0))
        order.fill("f", F(1), F(3), F(0))
        self.assertEqual((p.q, order.cash_in), (1, 3))
        with self.assertRaises(Conflict):
            order.fill("f", F(1), F(4), F(0))
        self.assertEqual((p.q, order.cash_in), (1, 3))

    def test_contradictory_fill_after_final_cancel_needs_reconciliation(self):
        p = Part(F(2), F(1))
        order = Order([p], F(1))
        order.cancel_confirmed()
        with self.assertRaises(Conflict):
            order.fill("new", F(1), F(2), F(0))
        self.assertEqual(p.q, 2)  # caller must preserve evidence + reconcile

    def test_mode_change_does_not_undo_inflight_sale(self):
        p = Part(F(4), F(1), debt=F(1))
        order = Order([p], F(1), automatic=True)
        p.change_whole_mode_to_manual()
        order.fill("late", F(1), F(1), F(0))
        self.assertEqual((p.q, p.debt, p.allocated), (3, 0, 0))

    def test_rounding_tail_composes_without_becoming_an_extra_asset(self):
        p = Part(F(703, 100), F(1))
        for identity, fraction, expected_sale in [("a", F(1, 4), F(175, 100)), ("b", F(1, 2), F(264, 100))]:
            p.reduce(fraction)
            amount = down(p.debt, F(1, 100))
            self.assertEqual(amount, expected_sale)
            Order([p], amount, automatic=True).fill(identity, amount, amount, F(0))
        self.assertEqual((p.q, p.debt), (F(264, 100), F(375, 100000)))
        p.reduce(F(1))
        self.assertEqual(p.debt, p.q)

    def test_manual_sale_satisfies_automatic_debt(self):
        p = Part(F(528, 100), F(1), debt=F(75, 10000))
        Order([p], F(1, 100)).fill("manual", F(1, 100), F(1, 100), F(0))
        self.assertEqual((p.q, p.debt), (F(527, 100), 0))

    def test_late_cohort_gets_old_fractions_new_buy_does_not(self):
        late = Part(F(8), F(1))
        late.reduce(F(1, 4))
        late.reduce(F(1, 2))
        independent = Part(F(8), F(1))
        self.assertEqual((late.debt, independent.debt), (5, 0))

    def test_weight_debt_never_sells_more_than_its_own_obligation(self):
        parts = [Part(F(1), F(1), debt=F(1, 10)), Part(F(2), F(1), debt=F(3, 2))]
        debts = [p.debt for p in parts]
        order = Order(parts, F(1), automatic=True)
        order.fill("f", F(1), F(1), F(0))
        self.assertTrue(all(0 <= p.debt <= old for p, old in zip(parts, debts)))
        self.assertEqual(sum(p.debt for p in parts), F(3, 5))

    def test_exact_limit_comparison_does_not_round_remaining_cost_down(self):
        remaining_cost = F(20, 3)
        limit = F(10)
        desired = F(334, 100)
        self.assertGreater(remaining_cost+desired, limit)

    def test_cash_reserve_ceil_does_not_understate_known_bound(self):
        self.assertEqual(up(F(1, 3), F(1, 100)), F(34, 100))
        self.assertEqual(up(F(1), F(1, 100)), 1)
        for value in [F(0), F(1, 7), F(11, 13), F(1000, 3)]:
            rounded = up(value, F(1, 100))
            self.assertTrue(value <= rounded < value+F(1, 100))
        with self.assertRaises(Conflict):
            up(F(-1), F(1, 100))

    def test_small_exact_sweep_of_debt_and_cost_invariants(self):
        for q in range(1, 12):
            for cost in range(1, 12):
                for fraction in [F(0), F(1, 7), F(1, 2), F(1)]:
                    p = Part(F(q), F(cost, q))
                    p.reduce(fraction)
                    amount = down(p.debt, F(1))
                    if amount:
                        Order([p], amount, automatic=True).fill("x", amount, amount, F(0))
                    self.assertTrue(0 <= p.debt <= p.q)
                    self.assertEqual(p.cost+p.released, cost)
                    self.assertLess(p.debt, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

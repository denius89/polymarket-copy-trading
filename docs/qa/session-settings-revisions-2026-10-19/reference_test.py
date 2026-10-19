"""Synthetic sequential oracle for contract 134; no DB, API, queue or live funds."""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from itertools import permutations
import unittest


class Conflict(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    revision: int = 1
    budget: F = F(200)
    mode: str = "fixed"
    value: F = F(20)
    position_ratio: F = F(1, 10)
    day_ratio: F = F(3, 20)


class Session:
    def __init__(self):
        self.current = Settings()
        self.history = [self.current]
        self.cash = F(200)
        self.cash_known = True
        self.positions = {}
        self.pending = {}
        self.fills = []  # (notional, proven synthetic day or None)
        self.day = 0
        self.flows = []
        self.commands = {}
        self.signals = {}
        self.decisions = {}
        self.buy_allowed = True

    def free_cash(self):
        return self.cash-sum(o["remaining"]+o["fee"] for o in self.pending.values())

    def used_position(self, outcome):
        return self.positions.get(outcome, F(0))+sum(
            o["remaining"] for o in self.pending.values() if o["outcome"] == outcome)

    def used_day(self):
        return sum(amount for amount, day in self.fills if day is None or day == self.day)+sum(
            o["remaining"] for o in self.pending.values())

    def edit(self, command, expected, **patch):
        payload = (expected, tuple(sorted(patch.items())))
        if command in self.commands:
            previous_payload, result = self.commands[command]
            if payload != previous_payload:
                raise Conflict("idempotency key reused with different input")
            return result
        if expected != self.current.revision:
            raise Conflict("settings version changed; review again")
        candidate = replace(self.current, **patch)
        if (candidate.budget <= 0 or candidate.value <= 0
                or candidate.mode not in ("fixed", "percent")
                or min(candidate.position_ratio, candidate.day_ratio) < 0):
            raise Conflict("invalid input; production bounds are separately versioned")
        if candidate == self.current:
            self.commands[command] = (payload, self.current)
            return self.current
        delta = candidate.budget-self.current.budget
        if delta < 0 and (not self.cash_known or -delta > self.free_cash()):
            raise Conflict("cannot remove committed or unproven money")
        # One reference transition. Real all-or-nothing DB semantics are NOT tested.
        candidate = replace(candidate, revision=self.current.revision+1)
        self.cash += delta
        if delta:
            self.flows.append(delta)
        self.current = candidate
        self.history.append(candidate)
        self.commands[command] = (payload, candidate)
        return candidate

    def observe(self, identity, outcome, trader_amount=F(100)):
        fact = (outcome, trader_amount)
        if identity in self.signals:
            if self.signals[identity][0] != fact:
                raise Conflict("same event identity with contradictory source")
            return self.signals[identity]
        amount = self.current.value if self.current.mode == "fixed" else trader_amount*self.current.value
        signal = (fact, amount, self.current.revision)
        self.signals[identity] = signal
        return signal

    def admit(self, identity, fee=F(0)):
        if identity in self.decisions:
            return self.decisions[identity]
        (outcome, _), amount, sizing_revision = self.signals[identity]
        c = self.current
        accepted = (self.buy_allowed and self.cash_known
                    and amount+fee <= self.free_cash()
                    and self.used_position(outcome)+amount <= c.budget*c.position_ratio
                    and self.used_day()+amount <= c.budget*c.day_ratio)
        result = (accepted, sizing_revision, c.revision, amount)
        if accepted:
            self.pending[identity] = dict(outcome=outcome, remaining=amount, fee=fee,
                                          sizing_revision=sizing_revision, admission_revision=c.revision)
        self.decisions[identity] = result
        return result

    def fill(self, identity, amount, proven_day):
        order = self.pending[identity]
        if not 0 < amount <= order["remaining"]:
            raise Conflict("unproven/contradictory fill")
        order["remaining"] -= amount
        outcome = order["outcome"]
        self.positions[outcome] = self.positions.get(outcome, F(0))+amount
        self.cash -= amount
        self.fills.append((amount, proven_day))

    def final_cancel(self, identity):
        self.pending[identity]["remaining"] = F(0)
        self.pending[identity]["fee"] = F(0)

    def sell(self, outcome, released_cost, proceeds):
        if released_cost > self.positions[outcome]:
            raise Conflict("invalid cost release")
        self.positions[outcome] -= released_cost
        self.cash += proceeds


def example():
    s = Session()
    s.positions["A"] = F(18)  # bought yesterday
    s.cash = F(182)
    s.observe("old", "B")
    assert s.admit("old", F(1, 5))[0]
    return s


class Revisions(unittest.TestCase):
    def test_budget_reduction_preserves_old_commitments_above_new_caps(self):
        s = example()
        old_order = s.pending["old"].copy()
        s.edit("edit", 1, budget=F(100))
        self.assertEqual((s.cash, s.free_cash()), (82, F(618, 10)))
        self.assertEqual((s.used_position("A"), s.used_position("B"), s.used_day()), (18, 20, 20))
        self.assertEqual(s.pending["old"], old_order)
        self.assertEqual(s.current.value, 20)
        s.observe("next", "C")
        self.assertFalse(s.admit("next")[0])

    def test_raise_budget_opens_only_difference_in_day_headroom(self):
        s = example()
        s.edit("down", 1, budget=F(100))
        s.edit("up", 2, budget=F(300))
        self.assertEqual((s.cash, s.free_cash()), (282, F(2618, 10)))
        self.assertEqual(s.current.budget*s.current.day_ratio-s.used_day(), 25)

    def test_unfunded_reduction_changes_nothing(self):
        s = Session()
        s.positions = {str(i): F(20) for i in range(8)}
        s.cash = F(40)
        s.observe("old", "new")
        s.admit("old", F(1, 5))
        with self.assertRaises(Conflict):
            s.edit("withdraw", 1, budget=F(150), value=F(5))
        self.assertEqual((s.cash, s.current.revision, len(s.history), s.flows), (40, 1, 1, []))

    def test_old_signal_keeps_size_but_uses_current_limits(self):
        s = Session()
        s.observe("before", "A")
        s.edit("edit", 1, budget=F(100), value=F(5))
        self.assertEqual(s.admit("before"), (False, 1, 2, 20))
        s.observe("after", "A")
        self.assertEqual(s.admit("after"), (True, 2, 2, 5))

    def test_old_size_is_not_replaced_even_when_it_still_fits(self):
        s = Session()
        s.observe("before", "A")
        s.edit("edit", 1, value=F(5))
        self.assertEqual(s.admit("before"), (True, 1, 2, 20))

    def test_old_percent_size_does_not_become_percent_of_budget(self):
        s = Session()
        s.edit("percent", 1, mode="percent", value=F(3, 100))
        s.observe("trade", "A", F(500))
        s.edit("budget", 2, budget=F(300), value=F(1, 100))
        self.assertEqual(s.admit("trade"), (True, 2, 3, 15))

    def test_settings_idempotency_prevents_duplicate_money_flow(self):
        s = Session()
        original = s.edit("fund", 1, budget=F(300))
        s.edit("later", 2, value=F(5))
        self.assertEqual(s.edit("fund", 1, budget=F(300)), original)
        self.assertEqual((s.cash, s.flows, s.current.revision), (300, [100], 3))
        with self.assertRaises(Conflict):
            s.edit("fund", 1, budget=F(400))

    def test_two_stale_writers_do_not_silently_merge(self):
        for changes in permutations([dict(budget=F(300)), dict(value=F(5))]):
            s = Session()
            s.edit("first", 1, **changes[0])
            with self.assertRaises(Conflict):
                s.edit("second", 1, **changes[1])
            self.assertEqual(len(s.history), 2)

    def test_receipt_duplicate_does_not_take_new_sizing_revision(self):
        s = Session()
        original = s.observe("event", "A")
        s.edit("edit", 1, value=F(5))
        self.assertEqual(s.observe("event", "A"), original)
        with self.assertRaises(Conflict):
            s.observe("event", "B")

    def test_skip_is_not_caught_up_after_settings_raise(self):
        s = Session()
        s.edit("small", 1, budget=F(100))
        s.observe("skip", "A")
        decision = s.admit("skip")
        self.assertFalse(decision[0])
        s.edit("large", 2, budget=F(300))
        self.assertEqual(s.admit("skip"), decision)

    def test_partial_old_fill_changes_live_usage_not_settings_history(self):
        s = example()
        s.edit("small", 1, budget=F(100))
        s.fill("old", F(8), 0)
        self.assertEqual((s.used_position("B"), s.used_day()), (20, 20))
        self.assertEqual((s.positions["B"], s.pending["old"]["remaining"]), (8, 12))
        self.assertEqual((s.current.revision, s.pending["old"]["admission_revision"]), (2, 1))
        s.final_cancel("old")
        self.assertEqual((s.used_position("B"), s.used_day()), (8, 8))

    def test_day_change_keeps_unresolved_old_revision_reserve(self):
        s = example()
        s.fill("old", F(8), 0)
        s.day = 1  # synthetic proven boundary; not a clock implementation
        s.edit("edit", 1, value=F(5))
        self.assertEqual(s.used_day(), 12)
        self.assertEqual(s.pending["old"]["remaining"], 12)

    def test_unknown_fill_time_is_not_freed_by_a_settings_change(self):
        s = example()
        s.fill("old", F(8), None)
        s.day = 1
        s.edit("edit", 1, value=F(5))
        self.assertEqual(s.used_day(), 20)

    def test_sales_do_not_refill_day_budget(self):
        s = example()
        s.fill("old", F(20), 0)
        s.final_cancel("old")
        s.sell("B", F(10), F(12))
        s.edit("edit", 1, value=F(5))
        self.assertEqual((s.positions["B"], s.used_day()), (10, 20))

    def test_position_overage_is_local_when_day_and_cash_allow_other_outcome(self):
        s = Session()
        s.positions["A"], s.cash = F(18), F(182)
        s.edit("edit", 1, budget=F(100), value=F(5))
        s.observe("same", "A")
        s.observe("other", "B")
        self.assertFalse(s.admit("same")[0])
        self.assertTrue(s.admit("other")[0])

    def test_no_op_and_non_budget_settings_do_not_create_funding_flow(self):
        s = Session()
        s.edit("noop", 1, budget=F(200))
        self.assertEqual((s.current.revision, s.flows), (1, []))
        s.edit("size", 1, value=F(5))
        self.assertEqual((s.cash, s.flows), (200, []))

    def test_returning_to_start_budget_keeps_change_history(self):
        s = Session()
        s.edit("up", 1, budget=F(300))
        s.edit("back", 2, budget=F(200))
        self.assertEqual((sum(s.flows), s.cash), (0, 200))
        self.assertEqual(s.flows, [100, -100])

    def test_config_update_cannot_resume_paused_or_exit_only_session(self):
        s = Session()
        s.buy_allowed = False
        s.edit("fund", 1, budget=F(300))
        s.observe("event", "A")
        self.assertFalse(s.admit("event")[0])

    def test_unproven_cash_cannot_be_removed(self):
        s = Session()
        s.cash_known = False
        with self.assertRaises(Conflict):
            s.edit("remove", 1, budget=F(100))
        self.assertEqual(s.current.revision, 1)

    def test_both_linear_orders_of_limit_edit_and_admission(self):
        for edit_first in [False, True]:
            s = Session()
            s.observe("event", "A")
            if edit_first:
                s.edit("edit", 1, budget=F(100))
                self.assertFalse(s.admit("event")[0])
            else:
                self.assertTrue(s.admit("event")[0])
                s.edit("edit", 1, budget=F(100))
                self.assertEqual(s.pending["event"]["remaining"], 20)

    def test_money_available_in_preview_may_be_reserved_before_commit(self):
        s = Session()
        s.positions = {str(i): F(20) for i in range(8)}
        s.cash = F(40)
        self.assertGreaterEqual(s.free_cash(), 30)  # earlier preview
        s.observe("new", "ninth")
        s.admit("new", F(1, 5))
        with self.assertRaises(Conflict):
            s.edit("withdraw", 1, budget=F(170))
        self.assertEqual((s.cash, s.current.revision, s.flows), (40, 1, []))

    def test_current_position_limit_keeps_exact_rational_cost(self):
        s = Session()
        s.positions["A"], s.cash = F(20, 3), F(194)
        s.edit("edit", 1, budget=F(100), value=F(334, 100))
        s.observe("new", "A")
        self.assertFalse(s.admit("new")[0])  # 20/3 + 3.34 > 10


if __name__ == "__main__":
    unittest.main(verbosity=2)

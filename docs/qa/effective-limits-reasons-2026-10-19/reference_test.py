"""Synthetic exact oracle for BL-08, not an admission engine or policy service."""
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import permutations
import unittest


CODES = [
    "service_unavailable", "action_blocked", "reconciliation_required", "accounting_unavailable",
    "context_invalid", "source_unavailable", "policy_unavailable", "constraints_incompatible",
    "units_incompatible", "evaluation_incomplete", "signal_stale", "market_rules_unavailable",
    "quote_unavailable", "quote_stale", "fee_bound_unavailable", "precision_unavailable",
    "below_market_minimum", "insufficient_liquidity", "insufficient_cash", "exposure_limit",
    "daily_buy_limit", "other_limit",
]
LAYER = {"system": 0, "session": 1, "individual": 2}


@dataclass(frozen=True)
class Rule:
    identity: str
    layer: str
    kind: str
    scope: str
    cap: F | None
    required: bool = True  # None + False means proven absence, NOT a fetch error
    currency: str = "USD"
    period: str = "session"
    applicable: bool = True
    actions: tuple = ("BUY",)


@dataclass(frozen=True)
class Check:
    code: str
    state: str
    scope: str = ""
    headroom: F | None = None
    sources: tuple = ()  # all sources and equal binding sources are separate
    binding: tuple = ()
    required: bool = True
    dependencies: tuple = ()


@dataclass(frozen=True)
class Evaluation:
    allowed_by_checks: bool
    primary: Check | None
    checks: tuple


def sort_key(check):
    remaining = check.headroom if check.headroom is not None else F(0)
    source_rank = min((LAYER[layer] for layer, _ in check.binding), default=3)
    return (CODES.index(check.code), remaining, source_rank, check.scope, check.sources)


def result(checks):
    valid_states = {"passed", "failed", "unavailable", "not_evaluated", "not_applicable"}
    checks = [c if c.code in CODES and c.state in valid_states
              else Check("policy_unavailable", "unavailable", scope="invalid-check") for c in checks]
    blockers = [c for c in checks if c.required and c.state in ("failed", "unavailable")]
    codes = {c.code for c in blockers}
    for c in checks:
        if c.required and c.state == "not_evaluated" and not codes.intersection(c.dependencies):
            checks.append(Check("evaluation_incomplete", "unavailable"))
            break
    blockers = [c for c in checks if c.required and c.state in ("failed", "unavailable")]
    incomplete = any(c.required and c.state == "not_evaluated" for c in checks)
    primary = min(blockers, key=sort_key) if blockers else None
    return Evaluation(not blockers and not incomplete, primary, tuple(sorted(checks, key=sort_key)))


def evaluate(rules, usage, amount=F(4), cash=F(1000), fee=F(0), gates=(), action="BUY",
             policy_present=True, previous=None):
    if previous is not None:
        return previous  # real identity/provenance validation belongs to the caller
    checks = list(gates)
    if amount is not None and amount <= 0:
        checks.append(Check("context_invalid", "failed"))
    if not policy_present:
        checks.append(Check("policy_unavailable", "unavailable"))
    if action == "BUY":
        deps = []
        for value, code in [(amount, "source_unavailable"), (cash, "accounting_unavailable"),
                            (fee, "fee_bound_unavailable")]:
            if value is None:
                checks.append(Check(code, "unavailable"))
                deps.append(code)
        if deps:
            checks.append(Check("insufficient_cash", "not_evaluated", dependencies=tuple(deps)))
        else:
            checks.append(Check("insufficient_cash", "passed" if amount+fee <= cash else "failed"))
    unique, conflicts, groups = {}, set(), {}
    for rule in rules:
        if rule.identity in unique:
            if rule != unique[rule.identity]:
                conflicts.add(rule.identity)
            continue
        unique[rule.identity] = rule
    for identity in sorted(conflicts):
        checks.append(Check("policy_unavailable", "unavailable", scope=identity))
    for rule in (unique[k] for k in sorted(unique) if k not in conflicts):
        if not rule.applicable or action not in rule.actions:
            checks.append(Check(rule.kind, "not_applicable", rule.scope, required=False))
            continue
        if rule.layer not in LAYER:
            checks.append(Check("policy_unavailable", "unavailable", rule.scope))
            continue
        if rule.currency != "USD":
            checks.append(Check("units_incompatible", "unavailable", rule.scope))
            continue
        if rule.cap is None:
            checks.append(Check("policy_unavailable", "unavailable" if rule.required else "not_applicable",
                                rule.scope, required=rule.required))
            continue
        if rule.cap < 0:
            checks.append(Check("policy_unavailable", "unavailable", rule.scope))
            continue
        groups.setdefault((rule.kind, rule.scope, rule.period), []).append(rule)
    for key, group in sorted(groups.items()):
        kind, scope, _ = key
        cap = min(r.cap for r in group)
        source_order = lambda x: (LAYER[x[0]], x[1])
        sources = tuple(sorted(((r.layer, r.identity) for r in group), key=source_order))
        binding = tuple(sorted(((r.layer, r.identity) for r in group if r.cap == cap), key=source_order))
        used = usage.get(key)
        if used is None:
            checks.append(Check("accounting_unavailable", "unavailable", scope))
            checks.append(Check(kind, "not_evaluated", scope, sources=sources, binding=binding,
                                dependencies=("accounting_unavailable",)))
        elif used < 0:
            checks.append(Check("context_invalid", "failed", scope))
        elif amount is None:
            checks.append(Check("source_unavailable", "unavailable", scope))
            checks.append(Check(kind, "not_evaluated", scope, sources=sources, binding=binding,
                                dependencies=("source_unavailable",)))
        else:
            headroom = cap-used
            checks.append(Check(kind, "passed" if amount <= headroom else "failed", scope,
                                headroom, sources, binding))
    return result(checks)


def exposure(identity, layer, scope, cap, **kwargs):
    return Rule(identity, layer, "exposure_limit", scope, cap, **kwargs)


class EffectiveLimits(unittest.TestCase):
    def test_same_bucket_uses_min_cap_and_one_counter(self):
        rules = [exposure("sys", "system", "position", F(15)),
                 exposure("session", "session", "position", F(20)),
                 exposure("trader", "individual", "position", F(12))]
        r = evaluate(rules, {("exposure_limit", "position", "session"): F(9)})
        self.assertEqual((r.primary.headroom, r.primary.binding), (3, (("individual", "trader"),)))
        self.assertEqual(len(r.primary.sources), 3)

    def test_different_scopes_compare_remaining_not_raw_caps(self):
        rules = [exposure("sys", "system", "account", F(100)),
                 exposure("pos", "session", "position", F(20)),
                 exposure("trader", "individual", "trader", F(10))]
        usage = {("exposure_limit", scope, "session"): F(value)
                 for scope, value in [("account", 95), ("position", 2), ("trader", 3)]}
        r = evaluate(rules, usage, amount=F(6))
        self.assertFalse(r.allowed_by_checks)
        self.assertEqual((r.primary.scope, r.primary.headroom), ("account", 5))

    def test_rule_order_does_not_change_result(self):
        rules = [exposure("sys", "system", "p", F(15)), exposure("s", "session", "p", F(20)),
                 exposure("i", "individual", "p", F(12))]
        expected = evaluate(rules, {("exposure_limit", "p", "session"): F(9)})
        for ordering in permutations(rules):
            self.assertEqual(evaluate(ordering, {("exposure_limit", "p", "session"): F(9)}), expected)

    def test_equal_binding_sources_are_all_preserved(self):
        r = evaluate([exposure("sys", "system", "p", F(3)), exposure("i", "individual", "p", F(3))],
                     {("exposure_limit", "p", "session"): F(0)})
        self.assertEqual(r.primary.binding, (("system", "sys"), ("individual", "i")))

    def test_verified_optional_absence_inherits(self):
        rules = [exposure("s", "session", "p", F(20)),
                 exposure("i", "individual", "p", None, required=False)]
        r = evaluate(rules, {("exposure_limit", "p", "session"): F(0)})
        self.assertTrue(r.allowed_by_checks)

    def test_optional_but_configured_limit_is_binding(self):
        r = evaluate([exposure("i", "individual", "p", F(0), required=False)],
                     {("exposure_limit", "p", "session"): F(0)})
        self.assertFalse(r.allowed_by_checks)

    def test_required_unknown_policy_is_not_infinite(self):
        r = evaluate([exposure("sys", "system", "p", None)], {})
        self.assertEqual((r.allowed_by_checks, r.primary.code), (False, "policy_unavailable"))

    def test_missing_policy_manifest_is_not_permission(self):
        self.assertFalse(evaluate([], {}, policy_present=False).allowed_by_checks)

    def test_missing_usage_is_not_zero(self):
        r = evaluate([exposure("sys", "system", "p", F(20))], {})
        self.assertEqual(r.primary.code, "accounting_unavailable")
        self.assertTrue(any(c.state == "not_evaluated" for c in r.checks))

    def test_cash_primary_retains_exposure_and_day_failures(self):
        rules = [exposure("p", "session", "p", F(8)),
                 Rule("d", "session", "daily_buy_limit", "d", F(15), period="day-1")]
        usage = {("exposure_limit", "p", "session"): F(0), ("daily_buy_limit", "d", "day-1"): F(0)}
        r = evaluate(rules, usage, amount=F(20), cash=F(10), fee=F(1, 5))
        self.assertEqual(r.primary.code, "insufficient_cash")
        self.assertEqual(len([c for c in r.checks if c.state == "failed"]), 3)

    def test_stale_signal_precedes_financial_failure(self):
        r = evaluate([], {}, amount=F(20), cash=F(10), gates=[Check("signal_stale", "failed")])
        self.assertEqual(r.primary.code, "signal_stale")

    def test_missing_quote_precedes_proven_cash_failure(self):
        r = evaluate([], {}, amount=F(20), cash=F(10), gates=[Check("quote_unavailable", "unavailable")])
        self.assertEqual(r.primary.code, "quote_unavailable")

    def test_unknown_fee_is_not_a_proven_cash_failure(self):
        r = evaluate([], {}, amount=F(20), cash=F(100), fee=None)
        self.assertEqual(r.primary.code, "fee_bound_unavailable")
        self.assertFalse(any(c.code == "insufficient_cash" and c.state == "failed" for c in r.checks))

    def test_service_block_precedes_other_causes(self):
        r = evaluate([], {}, cash=F(0), gates=[Check("signal_stale", "failed"),
                                              Check("service_unavailable", "failed")])
        self.assertEqual(r.primary.code, "service_unavailable")

    def test_buy_quota_alone_does_not_block_sell(self):
        rules = [exposure("p", "session", "p", F(0))]
        self.assertTrue(evaluate(rules, {}, action="SELL").allowed_by_checks)
        self.assertFalse(evaluate(rules, {}, action="SELL", gates=[Check("service_unavailable", "failed")]).allowed_by_checks)

    def test_existing_unknown_operation_stays_a_reconciliation_condition(self):
        r = evaluate([], {}, gates=[Check("reconciliation_required", "unavailable")])
        self.assertEqual((r.allowed_by_checks, r.primary.code), (False, "reconciliation_required"))

    def test_previous_verdict_is_not_replaced_after_policy_relaxation(self):
        old = evaluate([], {}, cash=F(0))
        self.assertEqual(evaluate([], {}, cash=F(1000), previous=old), old)

    def test_units_cannot_be_silently_converted(self):
        r = evaluate([exposure("sys", "system", "p", F(20), currency="EUR")], {})
        self.assertEqual(r.primary.code, "units_incompatible")

    def test_source_unknown_does_not_create_numeric_failures(self):
        r = evaluate([exposure("sys", "system", "p", F(20))],
                     {("exposure_limit", "p", "session"): F(0)}, amount=None)
        self.assertEqual(r.primary.code, "source_unavailable")
        self.assertFalse(any(c.state == "failed" for c in r.checks))

    def test_conflicting_duplicate_rule_identity_is_not_last_writer_wins(self):
        rules = [exposure("same", "system", "p", F(20)), exposure("same", "system", "p", F(40))]
        usage = {("exposure_limit", "p", "session"): F(0)}
        expected = evaluate(rules, usage)
        self.assertEqual(expected.primary.code, "policy_unavailable")
        self.assertFalse(any(c.code == "exposure_limit" for c in expected.checks))
        self.assertEqual(evaluate(list(reversed(rules)), usage), expected)

    def test_exact_boundary_including_costs_passes(self):
        r = evaluate([exposure("p", "session", "p", F(20))],
                     {("exposure_limit", "p", "session"): F(16)}, cash=F(21, 5), fee=F(1, 5))
        self.assertTrue(r.allowed_by_checks)

    def test_tightest_headroom_with_same_code_is_deterministic(self):
        rules = [exposure("a", "system", "a", F(100)), exposure("b", "individual", "b", F(10))]
        usage = {("exposure_limit", "a", "session"): F(99), ("exposure_limit", "b", "session"): F(8)}
        self.assertEqual(evaluate(rules, usage).primary.scope, "a")

    def test_market_minimum_cannot_be_overridden_by_maximum(self):
        r = evaluate([], {}, gates=[Check("below_market_minimum", "failed")])
        self.assertFalse(r.allowed_by_checks)

    def test_unexplained_required_check_is_not_implicitly_passed(self):
        r = evaluate([], {}, gates=[Check("exposure_limit", "not_evaluated")])
        self.assertEqual(r.primary.code, "evaluation_incomplete")

    def test_inapplicable_scope_does_not_consume_quota(self):
        r = evaluate([exposure("other", "system", "other-venue", F(0), applicable=False)], {})
        self.assertTrue(r.allowed_by_checks)

    def test_normalized_same_scope_percent_cap_and_fixed_cap(self):
        rules = [exposure("percent", "session", "p", F(200)*F(1, 5)),
                 exposure("fixed", "system", "p", F(30))]
        r = evaluate(rules, {("exposure_limit", "p", "session"): F(28)})
        self.assertEqual((r.primary.headroom, r.primary.binding), (2, (("system", "fixed"),)))

    def test_invalid_check_or_nonpositive_candidate_cannot_pass(self):
        r = evaluate([], {}, gates=[Check("unknown-code", "unexpected-state")])
        self.assertEqual(r.primary.code, "policy_unavailable")
        self.assertFalse(evaluate([], {}, amount=F(-1)).allowed_by_checks)

    def test_time_windows_are_independent_counter_buckets(self):
        rules = [exposure("session", "session", "account", F(100)),
                 exposure("day", "system", "account", F(20), period="day-2")]
        usage = {("exposure_limit", "account", "session"): F(99),
                 ("exposure_limit", "account", "day-2"): F(0)}
        r = evaluate(rules, usage)
        self.assertEqual(len([c for c in r.checks if c.code == "exposure_limit"]), 2)
        self.assertEqual(r.primary.binding, (("session", "session"),))


if __name__ == "__main__":
    unittest.main(verbosity=2)

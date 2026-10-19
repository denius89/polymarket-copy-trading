"""Isolated settings-contract model; no application or admission implementation."""
import json
from fractions import Fraction as Q
from pathlib import Path
import unittest

POLICY = json.loads((Path(__file__).resolve().parents[2] / "policies/paper-mvp-settings-v1.json").read_text())
FIELDS = POLICY["fields"]


def valid(field, value):
    value = Q(str(value))
    rule = FIELDS[field]
    return (Q(rule["min"]) <= value <= Q(rule["max"])
            and ((value - Q(rule["origin"])) / Q(rule["step"])).denominator == 1)


def caps(b, p, d):
    return Q(str(b)) * Q(str(p)) / 100, Q(str(b)) * Q(str(d)) / 100


def fixed_max(b, p, d):
    return min(caps(b, p, d)).__floor__()


def selection_ok(b, p, d, mode, value, previous=None):
    if not all(valid(k, v) for k, v in zip(
            ("budgetUsd", "positionPercent", "dailyPercent"), (b, p, d))):
        return False
    if mode == "percent":
        return valid("copyPercent", value)
    if mode != "fixed" or not valid("fixedCopyUsd", value):
        return False
    # previous is an authoritative persisted active setting, never a client claim.
    retained = (previous is not None and previous["mode"] == "fixed"
                and Q(str(previous["value"])) == Q(str(value)))
    return Q(str(value)) <= fixed_max(b, p, d) or retained


def desired(source_buy, percentage):
    return Q(str(source_buy)) * Q(str(percentage)) / 100


class NumericPolicyContract(unittest.TestCase):
    def test_version_and_scope(self):
        self.assertEqual(POLICY["policyId"], "paper-mvp-settings-v1")
        self.assertEqual(POLICY["status"], "accepted")
        self.assertEqual(POLICY["environment"], "paper")
        self.assertIsNone(POLICY["percentNotionalProductMinimumUsd"])
        self.assertEqual(FIELDS["copyPercent"]["basis"], "confirmed_individual_trader_buy_notional")
        for key in ("positionPercent", "dailyPercent"):
            self.assertEqual(FIELDS[key]["basis"], "session_budget_usd")
        self.assertTrue(FIELDS["fixedCopyUsd"]["retainUnchangedActiveValueOnCapReduction"])
        self.assertEqual(FIELDS["fixedCopyUsd"]["newSelectionLimitRule"],
                         "floor_min_session_position_and_day_usd")

    def test_owner_approved_boundaries(self):
        expected = {"budgetUsd": ("100", "1000", "10", "200"),
                    "fixedCopyUsd": ("5", "200", "1", "20"),
                    "copyPercent": ("1", "20", "0.5", "3"),
                    "positionPercent": ("5", "20", "1", "10"),
                    "dailyPercent": ("10", "30", "1", "15")}
        for key, values in expected.items():
            with self.subTest(field=key):
                self.assertEqual(tuple(FIELDS[key][k] for k in ("min", "max", "step", "default")), values)
                lo, hi, step, default = map(Q, values)
                for value in (lo, hi, default):
                    self.assertTrue(valid(key, value))
                for value in (lo-step, hi+step, lo+step/2):
                    self.assertFalse(valid(key, value))

    def test_defaults(self):
        self.assertEqual(caps(200, 10, 15), (20, 30))
        self.assertTrue(selection_ok(200, 10, 15, "fixed", 20))
        self.assertTrue(selection_ok(200, 10, 15, "percent", 3))

    def test_small_new_budget_does_not_silently_repair_default(self):
        self.assertFalse(selection_ok(100, 10, 15, "fixed", 20))
        self.assertTrue(selection_ok(100, 10, 15, "fixed", 10))

    def test_retained_active_value_and_new_choice_differ(self):
        old = {"mode": "fixed", "value": 20}
        self.assertTrue(selection_ok(100, 10, 15, "fixed", 20, old))
        self.assertFalse(selection_ok(100, 10, 15, "fixed", 19, old))
        self.assertFalse(selection_ok(100, 10, 15, "fixed", 20,
                                      {"mode": "percent", "value": 20}))
        self.assertFalse(selection_ok(100, 10, 15, "fixed", 20))

    def test_grid_is_not_venue_rounding(self):
        self.assertFalse(selection_ok(105, 10, 15, "fixed", 5))
        self.assertFalse(selection_ok(200, 10, 15, "percent", "3.2"))
        self.assertTrue(selection_ok(200, 10, 15, "percent", "3.0"))

    def test_fractional_cap_is_not_floored(self):
        self.assertEqual(caps(110, 7, 10), (Q("7.7"), 11))
        self.assertEqual(fixed_max(110, 7, 10), 7)
        self.assertTrue(selection_ok(110, 7, 10, "fixed", 7))
        self.assertFalse(selection_ok(110, 7, 10, "fixed", "7.7"))
        self.assertEqual(caps(110, 7, 10)[0], Q("7.7"))

    def test_position_can_exceed_day(self):
        self.assertEqual(caps(200, 20, 10), (40, 20))
        self.assertTrue(selection_ok(200, 20, 10, "fixed", 20))
        self.assertFalse(selection_ok(200, 20, 10, "fixed", 21))

    def test_percent_copy_below_fixed_field_minimum(self):
        self.assertEqual(desired(100, 3), 3)
        self.assertEqual(desired(75, 1), Q("0.75"))
        self.assertEqual(desired(500, 3), 15)
        self.assertEqual(desired(1000, 3), 30)
        # Desired amount survives a failed full-size comparison; no resize.
        self.assertGreater(desired(1000, 3), caps(200, 10, 15)[0])
        self.assertEqual(desired(1000, 3), 30)

    def test_percent_grid_has_39_values(self):
        values = [Q(1) + i * Q("0.5") for i in range(39)]
        self.assertTrue(all(valid("copyPercent", v) for v in values))
        self.assertEqual(values[-1], 20)

    def test_signal_age_not_editable_book_age(self):
        self.assertEqual(FIELDS["signalMaxAgeSeconds"], {
            "value": "30", "editable": False, "unit": "seconds",
            "appliesTo": "signal_not_orderbook"})

    def test_all_30576_budget_limit_combinations(self):
        count = 0
        maximum = 0
        for b in range(100, 1001, 10):
            for p in range(5, 21):
                for d in range(10, 31):
                    maximum_f = fixed_max(b, p, d)
                    self.assertGreaterEqual(maximum_f, 5)
                    self.assertTrue(selection_ok(b, p, d, "fixed", maximum_f))
                    self.assertFalse(selection_ok(b, p, d, "fixed", maximum_f+1))
                    self.assertLessEqual(maximum_f, min(caps(b, p, d)))
                    self.assertGreater(maximum_f+1, min(caps(b, p, d)))
                    count += 1
                    maximum = max(maximum, maximum_f)
        self.assertEqual(count, 30576)
        self.assertEqual(maximum, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)

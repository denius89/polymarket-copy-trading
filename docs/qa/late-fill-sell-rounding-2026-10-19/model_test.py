"""Isolated exact-arithmetic checks; not a product engine or database test."""
from fractions import Fraction as F
from itertools import permutations
import unittest


def floor_step(value, step):
    if step <= 0 or value < 0:
        raise ValueError("invalid quantity/step")
    return (value // step) * step


def allocate(total, weights):
    """Integer-atom largest remainders for one frozen order allocation."""
    if total < 0 or not weights or any(w <= 0 for w in weights):
        raise ValueError("invalid allocation")
    exact = [F(total * w, sum(weights)) for w in weights]
    out = [x.numerator // x.denominator for x in exact]
    ranking = sorted(range(len(weights)), key=lambda i: (-(exact[i]-out[i]), i))
    for i in ranking[:total-sum(out)]:
        out[i] += 1
    return out


def atom_schedule(reserved):
    """Example monotone fill allocation over a frozen vector, for small fixtures.

    Not a production algorithm: explicitly enumerates atoms. Each prefix is
    immutable, so splitting a fill into messages cannot reassign earlier atoms.
    """
    return [i for _, i in sorted((F(k, n), i)
            for i, n in enumerate(reserved) for k in range(1, n + 1))]


def apply_fill_messages(reserved, messages):
    sequence = atom_schedule(reserved)
    consumed, cursor = [0]*len(reserved), 0
    snapshots = []
    for amount in messages:
        if amount < 0 or cursor+amount > len(sequence):
            raise ValueError("fill exceeds frozen reservation")
        for index in sequence[cursor:cursor+amount]:
            consumed[index] += 1
        cursor += amount
        snapshots.append(consumed.copy())
    return snapshots


class ModelChecks(unittest.TestCase):
    def test_late_part_multiple_reductions(self):
        self.assertEqual(8 * (1-F(1, 4)) * (1-F(1, 2)), 3)

    def test_partial_retry_is_gap_to_target(self):
        target = 20 * (1-F(1, 4))
        actual = 20 - 2
        self.assertEqual(actual-target, 3)
        target *= 1-F(1, 2)
        self.assertEqual(actual-target, F(21, 2))

    def test_cumulative_cost_independent_of_fill_partition(self):
        for quantity in range(1, 25):
            for cost in range(1, 25):
                prev = 0
                for sold in range(1, quantity+1):
                    cumulative = cost*sold//quantity
                    self.assertGreaterEqual(cumulative-prev, 0)
                    prev = cumulative
                self.assertEqual(prev, cost)
        self.assertEqual([10*s//3 - 10*(s-1)//3 for s in (1, 2, 3)], [3, 3, 4])

    def test_no_allocation_lost_or_exceeds_lot(self):
        self.assertEqual(allocate(100, [100, 200]), [33, 67])
        for a in range(1, 15):
            for b in range(1, 15):
                for amount in range(a+b+1):
                    result = allocate(amount, [a, b])
                    self.assertEqual(sum(result), amount)
                    self.assertTrue(all(0 <= x <= w for x, w in zip(result, [a, b])))

    def test_partial_allocation_is_monotone_and_partition_invariant(self):
        for reserved in ([2, 5], [1, 1, 1], [3, 7, 4]):
            sequence = atom_schedule(reserved)
            self.assertEqual([sequence.count(i) for i in range(len(reserved))], list(reserved))
            for cut in range(len(sequence)+1):
                snapshots = apply_fill_messages(reserved, [cut, len(sequence)-cut])
                self.assertEqual(snapshots[-1], list(reserved))
                self.assertEqual(sum(snapshots[0]), cut)
                self.assertTrue(all(a <= b <= n for a, b, n in zip(*snapshots, reserved)))
                for end in range(cut, len(sequence)+1):
                    split = apply_fill_messages(reserved, [cut, end-cut])[-1]
                    unsplit = apply_fill_messages(reserved, [end])[-1]
                    self.assertEqual(split, unsplit)
        with self.assertRaises(ValueError):
            apply_fill_messages([2, 5], [8])

    def test_duplicate_late_fill_does_not_change_final_result(self):
        for messages in permutations([("A", 8), ("B", 4), ("B", 4)]):
            seen, filled, reserve = set(), 0, 20
            for identity, quantity in messages:
                if identity not in seen:
                    seen.add(identity)
                    filled += quantity
                    reserve -= quantity
                self.assertEqual(filled+reserve, 20)
            self.assertEqual((filled, reserve), (12, 8))

    def test_one_winner_for_competing_manual_requests_in_each_linear_order(self):
        for requests in permutations(["manual-a", "manual-b"]):
            current = None
            accepted = []
            for request in requests:
                if current is None:
                    current = request
                    accepted.append(request)
            self.assertEqual(accepted, [requests[0]])
        # This checks the sequential contract, not a real atomic DB transaction.

    def test_round_down_never_increases_risk(self):
        self.assertEqual(floor_step(F(703, 100)*F(1, 4), F(1, 100)), F(175, 100))
        for numerator in range(100):
            desired, step = F(numerator, 37), F(1, 10)
            normalized = floor_step(desired, step)
            self.assertLessEqual(normalized, desired)
            self.assertLess(desired-normalized, step)

    def test_rounding_cannot_rescue_failed_full_buy(self):
        desired, capacity, step = F(1001, 100), F(10), F(1, 10)
        self.assertEqual(floor_step(desired, step), capacity)
        self.assertFalse(desired <= capacity)  # still reject before normalization

    def test_dust_and_unknown_are_not_final(self):
        for quantity, reserve, unknown in [(F(1, 10000), 0, False), (0, 1, False), (0, 0, True)]:
            final = quantity == 0 and reserve == 0 and not unknown
            self.assertFalse(final)


if __name__ == "__main__":
    unittest.main(verbosity=2)

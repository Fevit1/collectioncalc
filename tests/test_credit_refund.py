"""Offline suite for the credit-refund unit (2026-08-27).

This touches the usage counter that gates billing caps, so it gets the
billing-teardown treatment: a stateful fake DB that enforces real SQL
semantics (flag transition gates the decrement; rollback undoes an
uncommitted flag flip), and positive controls in BOTH directions per
L-SW-2026-015/024:

  · a multi_edition refusal refunds EXACTLY ONCE across repeated calls
  · everything else — replays, wrong user, anonymous, missing grading id,
    lost persist race — refunds NOTHING

The route-level negative direction (normal valuation carries
credit_refunded: false) is asserted live in the ship block; the helper-level
guards here are the offline half.

Run: python tests/test_credit_refund.py
"""

import os
import sys
import types
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


class FakeDB:
    """Stateful stand-in for the two tables the refund touches.

    Enforces the transactional contract: writes land in a pending buffer and
    reach 'disk' only on commit(); rollback() discards them. That is what lets
    the crash-between-flag-and-decrement test prove the flag is NOT burned.
    """

    def __init__(self):
        self.submissions = {}   # grading_uuid -> {'user_id':…, 'credit_refunded':…}
        self.counters = {}      # user_id -> gradings_this_month
        self.fail_on_decrement = False
        self.commits = 0

    def conn(self):
        return _FakeConn(self)


class _FakeConn:
    def __init__(self, db):
        self.db = db
        self.pending = []       # list of callables applied at commit
        self.rowcount = 0

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        for apply in self.pending:
            apply()
        self.pending = []
        self.db.commits += 1

    def rollback(self):
        self.pending = []

    def close(self):
        pass


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    @property
    def rowcount(self):
        return self.conn.rowcount

    def execute(self, sql, params=None):
        db = self.conn.db
        s = ' '.join(sql.split())
        if 'UPDATE grade_submissions' in s:
            uuid, user_id = params
            row = db.submissions.get(uuid)
            if row and row['user_id'] == user_id and not row['credit_refunded']:
                self.conn.rowcount = 1
                self.conn.pending.append(
                    lambda r=row: r.__setitem__('credit_refunded', True))
            else:
                self.conn.rowcount = 0
        elif 'UPDATE users' in s:
            if db.fail_on_decrement:
                raise RuntimeError('induced decrement failure')
            (user_id,) = params
            self.conn.rowcount = 1
            # Honor the ACTUAL SQL semantics rather than hardcoding the floor
            # (review 2026-08-27: a fake that applies its own GREATEST would
            # let the floor test pass vacuously if production SQL lost it).
            floored = 'GREATEST(' in s
            def _apply(u=user_id, fl=floored):
                v = db.counters.get(u, 0) - 1
                db.counters[u] = max(v, 0) if fl else v
            self.conn.pending.append(_apply)
        else:
            raise AssertionError('unexpected SQL: %s' % s[:80])

    def close(self):
        pass


def _load_refund(db):
    """Import the real helper with the db pool stubbed to the fake."""
    fake_pool = types.ModuleType('db')
    fake_pool.get_db = lambda **kw: db.conn()
    sys.modules['db'] = fake_pool
    sys.modules.pop('routes.sales_valuation', None)
    from routes.sales_valuation import _maybe_refund_grading_credit
    return _maybe_refund_grading_credit


class TestCreditRefund(unittest.TestCase):
    def setUp(self):
        self._saved_db = sys.modules.get('db')
        self.db = FakeDB()
        self.db.submissions['uuid-1'] = {'user_id': 7, 'credit_refunded': False}
        self.db.counters[7] = 5
        self.refund = _load_refund(self.db)

    def tearDown(self):
        if self._saved_db is None:
            sys.modules.pop('db', None)
        else:
            sys.modules['db'] = self._saved_db
        sys.modules.pop('routes.sales_valuation', None)

    # ── positive control: fires, and exactly once ──

    def test_refunds_exactly_once_across_repeated_calls(self):
        self.assertTrue(self.refund('uuid-1', 7))
        self.assertEqual(self.db.counters[7], 4)
        self.assertTrue(self.db.submissions['uuid-1']['credit_refunded'])
        # replays: same grading, same user, three more times
        for _ in range(3):
            self.assertFalse(self.refund('uuid-1', 7))
        self.assertEqual(self.db.counters[7], 4)   # decremented ONCE, ever

    # ── negative controls: every guard, individually ──

    def test_anonymous_caller_no_refund_no_sql(self):
        self.assertFalse(self.refund('uuid-1', None))
        self.assertEqual(self.db.counters[7], 5)
        self.assertEqual(self.db.commits, 0)       # never even touched the DB

    def test_missing_grading_id_no_refund_no_sql(self):
        self.assertFalse(self.refund(None, 7))
        self.assertFalse(self.refund('', 7))
        self.assertEqual(self.db.commits, 0)

    def test_wrong_user_cannot_refund_someone_elses_grading(self):
        self.assertFalse(self.refund('uuid-1', 99))
        self.assertEqual(self.db.counters[7], 5)
        self.assertFalse(self.db.submissions['uuid-1']['credit_refunded'])

    def test_unknown_grading_lost_persist_race_is_a_safe_miss(self):
        self.assertFalse(self.refund('uuid-never-persisted', 7))
        self.assertEqual(self.db.counters[7], 5)

    # ── transactional shape ──

    def test_decrement_failure_rolls_back_flag_so_refund_can_retry(self):
        self.db.fail_on_decrement = True
        self.assertFalse(self.refund('uuid-1', 7))
        self.assertFalse(self.db.submissions['uuid-1']['credit_refunded'])  # not burned
        self.assertEqual(self.db.counters[7], 5)
        self.db.fail_on_decrement = False
        self.assertTrue(self.refund('uuid-1', 7))  # retry succeeds
        self.assertEqual(self.db.counters[7], 4)

    def test_counter_floors_at_zero(self):
        self.db.counters[7] = 0
        self.assertTrue(self.refund('uuid-1', 7))  # flag still flips
        self.assertEqual(self.db.counters[7], 0)   # never negative

    def test_helper_never_raises(self):
        fake_pool = types.ModuleType('db')
        def _boom(**kw):
            raise RuntimeError('pool down')
        fake_pool.get_db = _boom
        sys.modules['db'] = fake_pool
        sys.modules.pop('routes.sales_valuation', None)
        from routes.sales_valuation import _maybe_refund_grading_credit
        self.assertFalse(_maybe_refund_grading_credit('uuid-1', 7))  # no exception


if __name__ == '__main__':
    unittest.main(verbosity=2)

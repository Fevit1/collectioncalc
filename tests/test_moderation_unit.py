"""Offline tests for the 2026-08-25 moderation unit.

Covers, with POSITIVE CONTROLS per L-SW-2026-015 (every alarm is proven able
to fire, not inferred):

1. The wiring alarm (_moderation_wiring_status + check_aws_rekognition (0)):
   fires when moderate_image is None in a loaded route module; silent when
   wired; not-applicable outside the app.
2. The model-version-change alarm: fires on >1 distinct persisted version,
   silent on 0 or 1.
3. _record_model_version: writes once per version per process, retries after
   a failed write, never raises, rolls back on failure.
4. The v7 category sets: blocked/warned/clean classification against real v7
   label shapes, including the ancestor-matching semantics the sets rely on,
   and negative controls proving the deleted categories no longer block.

No network, no DB, no AWS: boto3 and db are stubbed in sys.modules.
Run:  python -m pytest tests/test_moderation_unit.py -q
  or: python tests/test_moderation_unit.py
"""

import os
import sys
import types
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        self.conn.executed.append((" ".join(sql.split()), params))
        if self.conn.fail_on and self.conn.fail_on in sql:
            raise RuntimeError(f"induced failure on: {self.conn.fail_on}")

    def fetchall(self):
        return self.conn.rows

    def close(self):
        pass


class _FakeConn:
    """Stub for db.get_db() pooled connections."""

    def __init__(self, rows=None, fail_on=None):
        self.rows = rows or []
        self.fail_on = fail_on
        self.executed = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _install_fake_db(conn):
    mod = types.ModuleType('db')
    mod.get_db = lambda **kw: conn
    sys.modules['db'] = mod
    return mod


def _label(name, parent='', level=None, conf=95.0):
    d = {'Name': name, 'ParentName': parent, 'Confidence': conf}
    if level is not None:
        d['TaxonomyLevel'] = level
    return d


def _fresh_content_moderation(labels=None, model_version='7.0'):
    """Import content_moderation with a stubbed boto3 returning `labels`."""
    fake_boto3 = types.ModuleType('boto3')

    class _FakeRekognition:
        def detect_moderation_labels(self, Image=None, MinConfidence=None):
            return {'ModerationLabels': labels or [],
                    'ModerationModelVersion': model_version}

    fake_boto3.client = lambda *a, **kw: _FakeRekognition()
    sys.modules['boto3'] = fake_boto3
    sys.modules.pop('content_moderation', None)
    with mock.patch.dict(os.environ, {'AWS_ACCESS_KEY_ID': 'x',
                                      'AWS_SECRET_ACCESS_KEY': 'y'}):
        import content_moderation
    return content_moderation


# A benign 1x1 base64 payload; content is irrelevant to the stub.
_B64 = 'aGVsbG8='


# ---------------------------------------------------------------------------
# 1. Wiring alarm
# ---------------------------------------------------------------------------

class TestWiringAlarm(unittest.TestCase):
    def setUp(self):
        import dependency_monitor
        self.dm = dependency_monitor
        self._saved = {k: sys.modules.get(k)
                       for k in ('wsgi', 'routes.grading', 'routes.images',
                                 'routes.vision')}
        # The end-to-end tests run the real check, which writes synthetic
        # results into the module-global cache with a fresh timestamp; without
        # restoration, any later in-process caller of check_aws_rekognition()
        # would get this test's fabricated data for the next CACHE_TTL (24h).
        self._saved_cache = dict(self.dm._caches['aws_rekognition'])

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        self.dm._caches['aws_rekognition'] = self._saved_cache

    def _fake_app(self, moderate_image):
        sys.modules['wsgi'] = types.ModuleType('wsgi')
        for name in ('routes.grading', 'routes.images', 'routes.vision'):
            m = types.ModuleType(name)
            m.moderate_image = moderate_image
            sys.modules[name] = m

    def test_positive_control_alarm_fires_when_unwired(self):
        """The exact prod failure shape: wsgi loaded, moderate_image None."""
        self._fake_app(moderate_image=None)
        unwired = self.dm._moderation_wiring_status()
        self.assertEqual(unwired, ['routes.grading', 'routes.images',
                                   'routes.vision'])

    def test_silent_when_wired(self):
        self._fake_app(moderate_image=lambda b64: {'allowed': True})
        self.assertEqual(self.dm._moderation_wiring_status(), [])

    def test_not_applicable_outside_app(self):
        for k in self._saved:
            sys.modules.pop(k, None)
        self.assertIsNone(self.dm._moderation_wiring_status())

    def test_check_emits_error_entry_end_to_end(self):
        """check_aws_rekognition() itself must carry the alarm."""
        self._fake_app(moderate_image=None)
        self.dm._caches['aws_rekognition'] = {'data': [], 'fetched_at': 0}
        with mock.patch.object(self.dm, '_rekognition_model_versions_seen',
                               return_value=[]), \
             mock.patch.object(self.dm, '_get_installed_boto3_version',
                               return_value=None):
            out = self.dm.check_aws_rekognition(force=True)
        wiring = [w for w in out if w.get('item') == 'moderation wiring']
        self.assertEqual(len(wiring), 1)
        self.assertEqual(wiring[0]['status'], 'error')
        self.assertIn('routes.grading', wiring[0]['detail'])

    def test_check_silent_when_wired_end_to_end(self):
        self._fake_app(moderate_image=lambda b64: {'allowed': True})
        self.dm._caches['aws_rekognition'] = {'data': [], 'fetched_at': 0}
        with mock.patch.object(self.dm, '_rekognition_model_versions_seen',
                               return_value=[]), \
             mock.patch.object(self.dm, '_get_installed_boto3_version',
                               return_value=None):
            out = self.dm.check_aws_rekognition(force=True)
        self.assertEqual([w for w in out
                          if w.get('item') == 'moderation wiring'], [])


# ---------------------------------------------------------------------------
# 2. Model-version-change alarm
# ---------------------------------------------------------------------------

class TestVersionChangeAlarm(unittest.TestCase):
    def setUp(self):
        import dependency_monitor
        self.dm = dependency_monitor

    def test_positive_control_two_versions_fire(self):
        out = self.dm._model_version_warnings([('7.0', 'T1'), ('8.0', 'T2')])
        self.assertEqual(len(out), 1)
        self.assertIn('7.0 -> 8.0', out[0]['detail'])
        self.assertIn("version <> '8.0'", out[0]['action'])

    def test_single_version_silent(self):
        self.assertEqual(self.dm._model_version_warnings([('7.0', 'T1')]), [])

    def test_no_versions_silent(self):
        self.assertEqual(self.dm._model_version_warnings([]), [])

    def test_gap_entry_reports_last_seen(self):
        gap = self.dm._rekognition_taxonomy_gap('7.0')
        self.assertIn('last seen: 7.0', gap['action'])
        gap_none = self.dm._rekognition_taxonomy_gap(None)
        self.assertIn('no version recorded yet', gap_none['action'])


# ---------------------------------------------------------------------------
# 3. _record_model_version
# ---------------------------------------------------------------------------

class TestRecordModelVersion(unittest.TestCase):
    def setUp(self):
        self._saved_db = sys.modules.get('db')
        self._saved_boto3 = sys.modules.get('boto3')

    def tearDown(self):
        for name, saved in (('db', self._saved_db),
                            ('boto3', self._saved_boto3)):
            if saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved
        sys.modules.pop('content_moderation', None)

    def test_writes_once_per_version(self):
        cm = _fresh_content_moderation()
        conn = _FakeConn()
        _install_fake_db(conn)
        cm._record_model_version('7.0')
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)
        self.assertIn('7.0', cm._seen_model_versions)
        conn2 = _FakeConn()
        _install_fake_db(conn2)
        cm._record_model_version('7.0')  # cached — no second write
        self.assertEqual(conn2.executed, [])

    def test_failed_write_rolls_back_and_retries(self):
        cm = _fresh_content_moderation()
        bad = _FakeConn(fail_on='INSERT')
        _install_fake_db(bad)
        cm._record_model_version('7.0')  # must not raise
        self.assertTrue(bad.rolled_back)
        self.assertTrue(bad.closed)
        self.assertNotIn('7.0', cm._seen_model_versions)  # retry-able
        good = _FakeConn()
        _install_fake_db(good)
        cm._record_model_version('7.0')
        self.assertTrue(good.committed)
        self.assertIn('7.0', cm._seen_model_versions)

    def test_called_from_moderate_image(self):
        cm = _fresh_content_moderation(labels=[], model_version='7.0')
        conn = _FakeConn()
        _install_fake_db(conn)
        result = cm.moderate_image(_B64)
        self.assertTrue(result['allowed'])
        self.assertIn('7.0', cm._seen_model_versions)

    def test_none_version_ignored(self):
        cm = _fresh_content_moderation()
        conn = _FakeConn()
        _install_fake_db(conn)
        cm._record_model_version(None)
        self.assertEqual(conn.executed, [])


# ---------------------------------------------------------------------------
# 4. v7 category sets
# ---------------------------------------------------------------------------

class TestV7Categories(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop('content_moderation', None)
        sys.modules.pop('boto3', None)

    def _moderate(self, labels):
        cm = _fresh_content_moderation(labels=labels)
        cm._record_model_version = lambda v: None  # not under test here
        return cm.moderate_image(_B64)

    # -- blocked: the three live entries, at every level AWS returns --

    def test_explicit_l1_blocks(self):
        r = self._moderate([_label('Explicit', '', 1)])
        self.assertTrue(r['blocked'])

    def test_explicit_l2s_block_via_parent(self):
        for l2 in ('Explicit Nudity', 'Explicit Sexual Activity', 'Sex Toys'):
            r = self._moderate([_label(l2, 'Explicit', 2)])
            self.assertTrue(r['blocked'], l2)

    def test_explicit_l3_blocks_because_ancestors_accompany_it(self):
        # AWS returns ancestor labels alongside a detected child; the L1/L2
        # entries fire even though the L3's own parent is not in the set.
        r = self._moderate([
            _label('Explicit', '', 1),
            _label('Explicit Nudity', 'Explicit', 2),
            _label('Exposed Male Genitalia', 'Explicit Nudity', 3),
        ])
        self.assertTrue(r['blocked'])

    def test_explicit_l3_alone_does_not_block(self):
        # Documents the known boundary of the matching semantics: an L3 whose
        # parent is an L2 matches nothing by itself — blocking relies on AWS
        # returning the ancestors with it (asserted above). If this test ever
        # FAILS, matching got deeper and the comment on BLOCKED_CATEGORIES
        # should be updated with it.
        r = self._moderate([_label('Exposed Male Genitalia',
                                   'Explicit Nudity', 3)])
        self.assertFalse(r['blocked'])

    def test_graphic_violence_blocks_with_l3s(self):
        r = self._moderate([_label('Graphic Violence', 'Violence', 2),
                            _label('Blood & Gore', 'Graphic Violence', 3)])
        self.assertTrue(r['blocked'])

    def test_hate_symbols_block_l1_and_children(self):
        self.assertTrue(self._moderate([_label('Hate Symbols', '', 1)])['blocked'])
        self.assertTrue(self._moderate(
            [_label('Nazi Party', 'Hate Symbols', 2)])['blocked'])

    # -- warnings: allowed through, logged --

    def test_violence_warns_not_blocks(self):
        r = self._moderate([_label('Violence', '', 1),
                            _label('Weapons', 'Violence', 2)])
        self.assertTrue(r['allowed'])
        self.assertEqual(len(r['warnings']), 2)

    def test_visually_disturbing_warns(self):
        r = self._moderate([_label('Visually Disturbing', '', 1)])
        self.assertTrue(r['allowed'])
        self.assertTrue(r['warnings'])

    # -- negative controls: deliberate deletions must NOT block or warn --

    def test_drugs_tobacco_alcohol_pass_clean(self):
        r = self._moderate([
            _label('Drugs & Tobacco', '', 1),
            _label('Products', 'Drugs & Tobacco', 2),
            _label('Drugs & Tobacco Paraphernalia & Use', 'Drugs & Tobacco', 2),
            _label('Alcohol', '', 1),
            _label('Alcoholic Beverages', 'Alcohol', 2),
        ])
        self.assertTrue(r['allowed'])
        self.assertFalse(r['blocked'])
        self.assertEqual(r['warnings'], [])

    def test_suggestive_successors_pass_clean(self):
        r = self._moderate([
            _label('Non-Explicit Nudity of Intimate parts and Kissing', '', 1),
            _label('Non-Explicit Nudity',
                   'Non-Explicit Nudity of Intimate parts and Kissing', 2),
            _label('Swimwear or Underwear', '', 1),
        ])
        self.assertTrue(r['allowed'])
        self.assertFalse(r['blocked'])
        self.assertEqual(r['warnings'], [])

    def test_clean_image_clean_result(self):
        r = self._moderate([])
        self.assertTrue(r['allowed'])
        self.assertEqual(r['warnings'], [])

    def test_fail_open_carries_marker(self):
        cm = _fresh_content_moderation()

        def _boom(**kw):
            raise RuntimeError('induced Rekognition outage')

        cm.rekognition_client.detect_moderation_labels = _boom
        r = cm.moderate_image(_B64)
        self.assertTrue(r['allowed'])
        self.assertTrue(any('Moderation check failed' in w
                            for w in r['warnings']))


if __name__ == '__main__':
    unittest.main(verbosity=2)

"""Offline tests for the 2026-08-25 upload-endpoints unit.

Positive-controls every gate per L-SW-2026-015 — each alarm/refusal is proven
able to fire, not inferred:

1. /api/images/upload-for-sale is GONE (404).
2. /api/images/upload: sale_id explicitly rejected (400), rate limit fires on
   the 11th request (429) and is per-IP, moderation blocks (400) and logs,
   warnings and fail-open markers log, clean uploads pass.

No network, no DB, no R2: everything is stubbed. Run:
  python -m pytest tests/test_upload_endpoints.py -q
  or: python tests/test_upload_endpoints.py
"""

import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from flask import Flask
from routes import images as images_mod


def _make_app(moderate=None):
    """Minimal app with the real blueprint and stubbed module wiring."""
    app = Flask(__name__)
    app.register_blueprint(images_mod.images_bp)
    incidents = []

    def _log(user_id, endpoint, result, image_hash=None):
        incidents.append({'user_id': user_id, 'endpoint': endpoint,
                          'result': result})

    images_mod.init_modules(
        True,                                              # r2_available
        lambda sid, img, t='front': {'success': True,      # upload_sale_image
                                     'url': f'sales/{sid}'},
        lambda img, prefix='temp': {'success': True,       # upload_temp_image
                                    'url': f'{prefix}/stub.jpg'},
        lambda *a, **k: {'success': True},                 # upload_submission
        lambda: True,                                      # check_r2
        lambda b64: None,                                  # scan_barcode
        moderate,                                          # moderate_image
        _log,                                              # log_moderation_incident
        lambda b64: 'hash123',                             # get_image_hash
    )
    return app, incidents


class TestUploadForSaleDeleted(unittest.TestCase):
    def test_endpoint_is_gone(self):
        app, _ = _make_app()
        resp = app.test_client().post('/api/images/upload-for-sale',
                                      json={'sale_id': 1, 'image': 'x'})
        self.assertEqual(resp.status_code, 404)


class TestUploadEndpoint(unittest.TestCase):
    def setUp(self):
        images_mod._upload_rate_store.clear()

    def tearDown(self):
        images_mod._upload_rate_store.clear()

    def test_malformed_body_gets_our_400_not_flasks(self):
        # Bot scanners POST garbage at public endpoints; the handler's own
        # JSON error must answer, not Flask's default HTML error page.
        app, _ = _make_app()
        resp = app.test_client().post('/api/images/upload',
                                      data='not json at all',
                                      content_type='text/plain')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['error'], 'Image data required')

    def test_sale_id_explicitly_rejected(self):
        app, _ = _make_app()
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x', 'sale_id': 42})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('sale_id is no longer accepted',
                      resp.get_json()['error'])

    def test_clean_upload_goes_to_temp(self):
        app, incidents = _make_app(
            moderate=lambda b64: {'allowed': True, 'blocked': False,
                                  'warnings': [], 'labels': []})
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['url'], 'whatnot/stub.jpg')
        self.assertEqual(incidents, [])

    # -- rate limit --

    def test_positive_control_rate_limit_fires_on_11th(self):
        app, _ = _make_app()
        c = app.test_client()
        for i in range(10):
            resp = c.post('/api/images/upload', json={'image': 'x'})
            self.assertEqual(resp.status_code, 200, f'request {i + 1}')
        resp = c.post('/api/images/upload', json={'image': 'x'})
        self.assertEqual(resp.status_code, 429)
        self.assertIn('Rate limit', resp.get_json()['error'])

    def test_rate_limit_is_per_ip(self):
        app, _ = _make_app()
        c = app.test_client()
        for _ in range(11):
            c.post('/api/images/upload', json={'image': 'x'})
        resp = c.post('/api/images/upload', json={'image': 'x'},
                      environ_overrides={'REMOTE_ADDR': '203.0.113.9'})
        self.assertEqual(resp.status_code, 200)

    def test_rate_limit_window_resets(self):
        app, _ = _make_app()
        c = app.test_client()
        for _ in range(11):
            c.post('/api/images/upload', json={'image': 'x'})
        # Jump past the window; the same IP must be admitted again.
        real_time = images_mod.time.time
        with mock.patch.object(
                images_mod.time, 'time',
                side_effect=lambda: real_time()
                + images_mod.UPLOAD_RATE_LIMIT_WINDOW + 1):
            resp = c.post('/api/images/upload', json={'image': 'x'})
        self.assertEqual(resp.status_code, 200)

    def test_rate_limit_checked_before_moderation(self):
        # An over-budget IP must not consume a Rekognition call.
        calls = []
        app, _ = _make_app(
            moderate=lambda b64: calls.append(1) or
            {'allowed': True, 'blocked': False, 'warnings': [], 'labels': []})
        c = app.test_client()
        for _ in range(10):
            c.post('/api/images/upload', json={'image': 'x'})
        self.assertEqual(len(calls), 10)
        c.post('/api/images/upload', json={'image': 'x'})
        self.assertEqual(len(calls), 10)  # 11th blocked pre-moderation

    # -- moderation --

    def test_positive_control_moderation_blocks_and_logs(self):
        app, incidents = _make_app(
            moderate=lambda b64: {'allowed': False, 'blocked': True,
                                  'reason': 'Explicit', 'warnings': [],
                                  'labels': [{'name': 'Explicit'}]})
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x'})
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(resp.get_json()['moderation'])
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]['endpoint'], '/api/images/upload')
        self.assertIsNone(incidents[0]['user_id'])  # anonymous caller logs

    def test_warnings_log_but_pass(self):
        app, incidents = _make_app(
            moderate=lambda b64: {'allowed': True, 'blocked': False,
                                  'warnings': [{'name': 'Violence'}],
                                  'labels': []})
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(incidents), 1)

    def test_fail_open_marker_logs_but_passes(self):
        app, incidents = _make_app(
            moderate=lambda b64: {'allowed': True, 'blocked': False,
                                  'warnings': ['Moderation check failed: boom'],
                                  'labels': []})
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(incidents), 1)

    def test_moderation_unwired_still_uploads(self):
        # moderate_image=None (the wiring fail-open) must not 500 the public
        # page; the monitor unit owns alerting on that state.
        app, incidents = _make_app(moderate=None)
        resp = app.test_client().post('/api/images/upload',
                                      json={'image': 'x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(incidents, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)

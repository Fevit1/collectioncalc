"""Offline tests for the 2026-08-25 check.html result-card unit (backend half).

Positive-controls the privacy strip per L-SW-2026-015. The frontend half
(badge/title/removed cells) is verified by direct render in the browser and
by grep asserts in the ship block.

Run: python tests/test_check_card_unit.py
"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from routes.monitor import _strip_private_match_fields


def _match(**over):
    m = {
        'serial_number': 'SW-2026-DTA2EV',
        'owner_display': 'm*******3@y***o.com',
        'confidence': 84.9,
        'copy_match': 'different_copy',
        '_reg_photo_url': 'https://r2/x.jpg',
        '_reg_extra_photos': [{'url': 'https://r2/y.jpg'}],
        'comic': {'title': 'The Terminator', 'issue_number': '1'},
    }
    m.update(over)
    return m


class TestStripPrivateFields(unittest.TestCase):
    def test_positive_control_unauthenticated_strips_owner(self):
        matches = [_match(), _match(serial_number='SW-2026-V48W8Y')]
        _strip_private_match_fields(matches, authenticated=False)
        for m in matches:
            self.assertNotIn('owner_display', m)
            self.assertNotIn('_reg_photo_url', m)
            self.assertNotIn('_reg_extra_photos', m)
            # Serial deliberately stays public — the verification path.
            self.assertIn('serial_number', m)
            self.assertIn('comic', m)

    def test_authenticated_keeps_owner_but_never_internal(self):
        matches = [_match()]
        _strip_private_match_fields(matches, authenticated=True)
        self.assertEqual(matches[0]['owner_display'], 'm*******3@y***o.com')
        self.assertNotIn('_reg_photo_url', matches[0])
        self.assertNotIn('_reg_extra_photos', matches[0])

    def test_legacy_shape_without_optional_fields(self):
        # check-hash's legacy dicts have no _reg_* keys; pop must not raise.
        m = {'serial_number': 'X', 'owner_display': 'a@b.c'}
        _strip_private_match_fields([m], authenticated=False)
        self.assertEqual(m, {'serial_number': 'X'})

    def test_empty_list_noop(self):
        _strip_private_match_fields([], authenticated=False)


if __name__ == '__main__':
    unittest.main(verbosity=2)

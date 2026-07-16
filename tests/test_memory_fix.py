"""Offline verification for the /api/grade memory fix (2026-07-16 OOM incident).

Covers:
  A. Correctness of max_long_edge capping in normalize_orientation_b64 /
     normalize_for_photo_type (12MP real-world-sized fixtures, JPEG + HEIC,
     EXIF-rotated, no-EXIF landscape, centerfold, garbage, data-URL prefix).
  B. Uncapped path unchanged (extract/barcode compat).
  C. Peak-RSS measurement of a realistic 4-photo grade normalization at 12MP,
     capped vs uncapped — the test class that was missing when the regression
     shipped (small fixtures never exercised peak memory).

Run from repo root:  python tests/test_memory_fix.py
"""
import base64
import io
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

from comic_extraction import normalize_orientation_b64, normalize_for_photo_type

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def noise_rgb(w, h):
    """Photo-realistic fixture: smooth gradient + mild noise. Pure noise is
    incompressible (a 12MP noise JPEG is ~15MB vs ~2-4MB for a real photo),
    which makes base64 strings dominate peak memory and hides the decode-buffer
    reduction this fix targets. Gradient+mild-noise compresses like a real
    comic photo."""
    gradient = Image.linear_gradient("L").resize((w, h)).convert("RGB")
    noise = Image.effect_noise((w, h), 24).convert("RGB")
    return Image.blend(gradient, noise, 0.25)


def to_b64(img, fmt="JPEG", exif_orientation=None):
    buf = io.BytesIO()
    kwargs = {"quality": 90} if fmt in ("JPEG", "HEIF") else {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        kwargs["exif"] = exif.tobytes()
    img.save(buf, format=fmt, **kwargs)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def dims_of(b64):
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    return img.size, img.format


print("Building 12MP fixtures (this allocates deliberately large images)...")
# 12MP iPhone-shaped: 4032x3024 stored landscape with EXIF orientation 6
# (rotate 90 CW to display) -> upright result should be portrait 3024x4032-ish.
JPEG_12MP_EXIF6 = to_b64(noise_rgb(4032, 3024), "JPEG", exif_orientation=6)
# 12MP stored-portrait, no EXIF (already upright front cover)
JPEG_12MP_PORTRAIT = to_b64(noise_rgb(3024, 4032), "JPEG")
# 12MP landscape, NO EXIF (sideways front-cover photo -> mode-2 force rotate)
JPEG_12MP_LANDSCAPE_NOEXIF = to_b64(noise_rgb(4032, 3024), "JPEG")
# 12MP HEIC portrait
HEIC_12MP = to_b64(noise_rgb(3024, 4032), "HEIF")
# small control fixture
JPEG_SMALL = to_b64(noise_rgb(400, 600), "JPEG")

print("\n[A] Capped correctness (max_long_edge=2000)")

out = normalize_for_photo_type(JPEG_12MP_EXIF6, "front", max_long_edge=2000)
(w, h), fmt = dims_of(out)
check("EXIF-6 12MP front: upright portrait", h > w, f"got {w}x{h}")
check("EXIF-6 12MP front: long edge capped to 2000", max(w, h) == 2000, f"got {w}x{h}")
check("EXIF-6 12MP front: emits JPEG", fmt == "JPEG", fmt)

out = normalize_for_photo_type(JPEG_12MP_PORTRAIT, "spine", max_long_edge=2000)
(w, h), _ = dims_of(out)
check("portrait 12MP spine: stays portrait, capped", h > w and max(w, h) == 2000, f"{w}x{h}")

out = normalize_for_photo_type(JPEG_12MP_LANDSCAPE_NOEXIF, "front", max_long_edge=2000)
(w, h), _ = dims_of(out)
check("no-EXIF landscape 12MP front: force-rotated portrait, capped",
      h > w and max(w, h) == 2000, f"{w}x{h}")

out = normalize_for_photo_type(JPEG_12MP_EXIF6, "centerfold", max_long_edge=2000)
(w, h), _ = dims_of(out)
check("centerfold: EXIF honored only, never force-rotated, capped",
      max(w, h) == 2000, f"{w}x{h}")

out = normalize_for_photo_type(HEIC_12MP, "front", max_long_edge=2000)
(w, h), fmt = dims_of(out)
check("HEIC 12MP front: decoded, portrait, capped, JPEG",
      fmt == "JPEG" and h > w and max(w, h) == 2000, f"{w}x{h} {fmt}")

out = normalize_for_photo_type(JPEG_SMALL, "front", max_long_edge=2000)
(w, h), _ = dims_of(out)
check("small image under cap: NOT upscaled", (w, h) == (400, 600), f"{w}x{h}")

out = normalize_orientation_b64("data:image/jpeg;base64," + JPEG_SMALL,
                                assume_portrait=True, max_long_edge=2000)
check("data-URL prefix tolerated with cap", dims_of(out)[0] == (400, 600))

try:
    normalize_for_photo_type(base64.b64encode(b"not an image").decode(), "front",
                             max_long_edge=2000)
    check("garbage raises ValueError", False)
except ValueError:
    check("garbage raises ValueError", True)

print("\n[B] Uncapped path unchanged (extract/barcode compat)")

out = normalize_for_photo_type(JPEG_12MP_EXIF6, "front")  # no cap
(w, h), _ = dims_of(out)
check("uncapped 12MP: full resolution preserved (3024x4032)",
      (w, h) == (3024, 4032), f"{w}x{h}")

out = normalize_for_photo_type(JPEG_SMALL, "front")
check("uncapped small: unchanged", dims_of(out)[0] == (400, 600))

print("\n[C] Peak-RSS: realistic 4-photo 12MP grade normalization")

proc = psutil.Process()


class RssSampler:
    def __init__(self):
        self.peak = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, proc.memory_info().rss)
            time.sleep(0.002)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join()


GRADE_PHOTOS = [  # what a real /api/grade sees: 4 photos, mixed types
    (JPEG_12MP_EXIF6, "front"),
    (JPEG_12MP_PORTRAIT, "spine"),
    (HEIC_12MP, "back"),
    (JPEG_12MP_EXIF6, "centerfold"),
]
JPEG_ONLY_PHOTOS = [(JPEG_12MP_EXIF6, "front"), (JPEG_12MP_PORTRAIT, "spine"),
                    (JPEG_12MP_EXIF6, "back"), (JPEG_12MP_PORTRAIT, "centerfold")]


def measure(fn):
    import gc
    gc.collect()
    base = proc.memory_info().rss
    with RssSampler() as s:
        fn()
    gc.collect()
    time.sleep(0.05)
    final = proc.memory_info().rss
    return (s.peak - base) / 1e6, (final - base) / 1e6


def seq_loop(photos, cap):
    def run():
        for b64, ptype in photos:
            normalize_for_photo_type(b64, ptype, max_long_edge=cap)
    return run


# C1 — JPEG-only, capped vs uncapped: isolates the draft/thumbnail win (HEIC
# has no reduced-scale decode, so it would mask this). Uncapped runs FIRST, so
# allocator reuse favors the second (capped) run being *penalized*, not helped.
u_peak, _ = measure(seq_loop(JPEG_ONLY_PHOTOS, None))
c_peak, _ = measure(seq_loop(JPEG_ONLY_PHOTOS, 2000))
print(f"  C1 JPEG-only 4x12MP:  uncapped peak +{u_peak:.0f}MB, capped peak +{c_peak:.0f}MB")
check("C1: cap cuts JPEG decode peak by >40%", c_peak < u_peak * 0.6,
      f"{c_peak:.0f} vs {u_peak:.0f}")

# C2 — realistic mixed grade (3 JPEG + 1 HEIC), capped: the absolute budget
# that matters on the 512MB instance (~330MB baseline + this transient).
m_peak, m_retained = measure(seq_loop(GRADE_PHOTOS, 2000))
print(f"  C2 mixed 4x12MP capped: peak +{m_peak:.0f}MB, retained +{m_retained:.0f}MB")
check("C2: mixed-grade peak fits budget (<150MB)", m_peak < 150, f"{m_peak:.0f}MB")
check("C2: no significant retained growth (<25MB)", m_retained < 25, f"{m_retained:.0f}MB")

# C3 — 8 concurrent 12MP normalizations (one worker's full thread pool, i.e.
# the F-L4 burst shape) with the decode gate at its default of 2: peak must
# stay near 2-deep, NOT 8-deep.
import comic_extraction


def concurrent_8():
    threads = [threading.Thread(target=seq_loop([p], 2000))
               for p in (GRADE_PHOTOS * 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


g_peak, _ = measure(concurrent_8)
print(f"  C3 8-way concurrent, gate=2: peak +{g_peak:.0f}MB")
check("C3: gated concurrent peak bounded (<250MB, ~2-deep not 8-deep)",
      g_peak < 250, f"{g_peak:.0f}MB")
check("C3: decode gate exists with default 2",
      comic_extraction._DECODE_GATE._value in (0, 1, 2))

print("\n[D] Extract-path cap (EXTRACT_MAX_LONG_EDGE=4096) — the 1437fdb OOM class")
# The 18:00:52Z OOM on the ROLLBACK build: one raw 24MP photo through
# /api/extract (normalize uncapped + scan_barcode re-decode) peaked +310MB
# from a ~330MB baseline. 4096 must bound that while passing 12MP untouched.
from comic_extraction import EXTRACT_MAX_LONG_EDGE, scan_barcode

check("D: default extract cap is 4096", EXTRACT_MAX_LONG_EDGE == 4096,
      str(EXTRACT_MAX_LONG_EDGE))

out = normalize_for_photo_type(JPEG_12MP_PORTRAIT, "front",
                               max_long_edge=EXTRACT_MAX_LONG_EDGE)
(w, h), _ = dims_of(out)
check("D: 12MP (4032px) passes UNTOUCHED at extract cap — barcode parity",
      (w, h) == (3024, 4032), f"{w}x{h}")

JPEG_24MP = to_b64(noise_rgb(4284, 5712), "JPEG")  # raw iPhone 24MP default


def extract_pipeline(b64, cap):
    """What /api/extract does: normalize, then scan_barcode on the output."""
    norm = normalize_for_photo_type(b64, "front", max_long_edge=cap)
    try:
        scan_barcode(base64.b64decode(norm))
    except Exception:
        pass
    return norm


u_peak, _ = measure(lambda: extract_pipeline(JPEG_24MP, None))
c_peak, _ = measure(lambda: extract_pipeline(JPEG_24MP, EXTRACT_MAX_LONG_EDGE))
print(f"  D 24MP extract pipeline: uncapped peak +{u_peak:.0f}MB, capped +{c_peak:.0f}MB")
check("D: capped 24MP extract fits the instance budget (<180MB)",
      c_peak < 180, f"{c_peak:.0f}MB")
check("D: cap materially reduces the 24MP extract peak", c_peak < u_peak * 0.75,
      f"{c_peak:.0f} vs {u_peak:.0f}")
out = normalize_for_photo_type(JPEG_24MP, "front", max_long_edge=EXTRACT_MAX_LONG_EDGE)
(w, h), _ = dims_of(out)
# Half-decode rule: an over-cap source lands in (cap/2, cap] — 5712 -> 2856.
check("D: 24MP output bounded by the cap (half-decoded)",
      EXTRACT_MAX_LONG_EDGE // 2 <= max(w, h) <= EXTRACT_MAX_LONG_EDGE, f"{w}x{h}")
del JPEG_24MP

# Raw 24MP HEIC — the literal Gate-0 killer input (iPhone default format at
# current default resolution, reaching the server unresized because Chrome
# cannot canvas-decode HEIC). HEIC has NO reduced-scale decode path, so the
# full bitmap exists transiently regardless of cap — this is the honest
# worst-case single-request number for the 512MB budget. Runs in a SUBPROCESS:
# the local Windows libheif build hard-crashes (no Python traceback) when
# encoding 24MP inside this heap-churned process, and a fresh process is a
# cleaner RSS baseline anyway. quality=80 — the encoder fails to round-trip
# our synthetic at q90.
import json
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEIC_SNIPPET = r'''
import base64, io, json, sys, threading, time, gc
sys.path.insert(0, r"%s")
import psutil
from PIL import Image
import pillow_heif
pillow_heif.register_heif_opener()
from comic_extraction import normalize_for_photo_type, scan_barcode, EXTRACT_MAX_LONG_EDGE
g = Image.linear_gradient("L").resize((4284, 5712)).convert("RGB")
n = Image.effect_noise((4284, 5712), 24).convert("RGB")
img = Image.blend(g, n, 0.25)
buf = io.BytesIO(); img.save(buf, format="HEIF", quality=80); img.close()
b64 = base64.b64encode(buf.getvalue()).decode()
proc = psutil.Process(); gc.collect()
base = proc.memory_info().rss; peak = base
stop = threading.Event()
def samp():
    global peak
    while not stop.is_set():
        peak = max(peak, proc.memory_info().rss); time.sleep(0.002)
t = threading.Thread(target=samp, daemon=True); t.start()
norm = normalize_for_photo_type(b64, "front", max_long_edge=EXTRACT_MAX_LONG_EDGE)
try: scan_barcode(base64.b64decode(norm))
except Exception: pass
stop.set(); t.join()
out = Image.open(io.BytesIO(base64.b64decode(norm)))
print(json.dumps({"peak_mb": (peak - base) / 1e6, "w": out.size[0], "h": out.size[1],
                  "fmt": out.format, "cap": EXTRACT_MAX_LONG_EDGE}))
''' % REPO_ROOT

r = subprocess.run([sys.executable, "-c", HEIC_SNIPPET], capture_output=True, text=True,
                   timeout=600)
try:
    hres = json.loads(r.stdout.strip().splitlines()[-1])
except Exception:
    hres = None
check("D: raw 24MP HEIC measurement subprocess completed", hres is not None,
      f"exit={r.returncode} stderr={r.stderr[-200:]}")
if hres:
    print(f"  D 24MP raw-HEIC extract pipeline, capped: peak +{hres['peak_mb']:.0f}MB, "
          f"output {hres['w']}x{hres['h']} {hres['fmt']}")
    check("D: raw 24MP HEIC decodes, emits capped JPEG",
          hres["fmt"] == "JPEG" and max(hres["w"], hres["h"]) <= hres["cap"])
    # ⚠️ MEASURED FLOOR, not a comfort number: libheif double-buffers the
    # decode (C frame + PIL copy), so a raw 24MP HEIC costs ~200MB transient
    # NO MATTER WHAT our code does — from the ~330MB 2-worker baseline that is
    # ~528MB, i.e. AT/OVER the 512MB Starter ceiling. This check is a
    # regression guard (it must not get WORSE); making this input class safe
    # is an INSTANCE-SIZE or reject-policy decision, not a code fix. See
    # LAUNCH_READINESS (2026-07-16) for the tradeoff record.
    check("D: raw 24MP HEIC peak at the known libheif floor (<230MB regression guard)",
          hres["peak_mb"] < 230, f"{hres['peak_mb']:.0f}MB")
    if hres["peak_mb"] >= 180:
        print("  NOTE: raw 24MP HEIC exceeds Starter-512MB headroom — needs 2GB tier "
              "or an over-size reject policy; code caps cannot fix this class.")

print(f"\n{'='*50}\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

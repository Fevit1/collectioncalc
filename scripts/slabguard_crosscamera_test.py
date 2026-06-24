"""
Slab Guard — Cross-Camera Recovery Test Harness  (READ-ONLY / not wired into prod)
==================================================================================

Purpose
-------
Measure the DECISIVE recovery metrics on a real, multi-copy, multi-DEVICE test set:

    TRUE-POSITIVE  rate  — same physical copy shot on two different phones  → want SAME_COPY
    FALSE-POSITIVE rate  — a DIFFERENT copy of the SAME issue, other phone  → MUST be DIFFERENT_COPY

The false-positive rate is the one that gates the "recovery" marketing claim: even one
different-copy pair wrongly called SAME_COPY means we could flag an innocent seller's
legitimate copy as stolen. We want 0 false positives AND a high true-positive rate.

This harness changes NO production code. It imports the live CV path
(routes.slab_guard_cv.compare_covers_with_vision) exactly as /api/monitor/check-image
calls it, with marketplace_mode=True (the recovery path: Vision is the primary verdict).

How it feeds local photos to the CV path
-----------------------------------------
compare_covers_with_vision() downloads its inputs from URLs. Rather than touch that code
or upload anything to R2, this harness spins up a localhost static file server over the
capture directory and passes http://127.0.0.1:PORT/<file> URLs. Nothing leaves the machine.

We deliberately bypass the perceptual-hash "issue gate" (the 77/105 candidate filter).
That gate only confirms "same issue", which is TRUE for both our TP and FP pairs by design,
so it is not the discriminator. The discriminator is the copy-level verdict, which is exactly
what compare_covers_with_vision() returns.

Capture protocol + file naming
-------------------------------
Shoot the FRONT COVER of each (copy, phone). The real shoot is 6 issues x (2 OR 3 copies)
x 2 phones — copies vary per issue, so the harness enumerates whatever it finds (no fixed count).

    Lighting   : even, diffuse, no glare/hotspots (especially on slabs). Window light or two lamps.
    Background : plain, flat, MATTE, contrasting color (NO blankets/wood grain/cloth — textured
                 surfaces create false border matches; this is the #1 documented failure mode).
    Framing    : whole cover visible, square-on (minimize tilt), cover fills ~80-90% of frame.
    Resolution : full-res phone camera. Min 500px short side; 1000px+ strongly preferred.
    Devices    : Phone 1 and Phone 2 must be GENUINELY DIFFERENT devices (this is the whole point).

Name every file (extension .jpg/.jpeg/.png/.webp):

    <issue-slug>_copy<A|B|C...>_phone<1|2>.<ext>
    The slug is any issue identifier you choose (mu1, ironman200, invaders41,
    heroesforhope, hulkwolverine1, ...). Copies are single letters A, B, C, ...
    e.g.  mu1_copyA_phone1.jpg   mu1_copyA_phone2.jpg
          mu1_copyB_phone1.jpg   mu1_copyB_phone2.jpg
          mu1_copyC_phone1.jpg   mu1_copyC_phone2.jpg   (3rd copy, if present)

Optional cross-IMAGE baseline (same phone, second shot — should be an easy SAME_COPY):
    <issue-slug>_copy<A|B|C>_phone1b.<ext>   (or _phone2b)

Pairs the harness builds per issue (copies enumerated dynamically when files exist)
-----------------------------------------------------------------------------------
    TP                : copyX/phone1 vs copyX/phone2   expect same_copy   (one per copy)
    FP / cross_camera : copyX/phone1 vs copyY/phone2   expect different_copy (every ordered X!=Y)
    FP / same_phone   : copyX/phoneN vs copyY/phoneN   expect different_copy (every X<Y, per phone)
    BASELINE (opt.)   : copyX/phone1 vs copyX/phone1b  expect same_copy   (cross-image control)

The two FP modes report separately: a cross_camera false positive is camera-driven, a
same_phone false positive is copy-similarity-driven. Both must be 0; the split says which.

Run
---
    # from the repo root, in the project venv (needs opencv + anthropic + ANTHROPIC_API_KEY)
    python scripts/slabguard_crosscamera_test.py --captures "C:/path/to/your/photos"

    # optional: A/B a different vision model for the arbiter (e.g. Opus for the forensic call)
    python scripts/slabguard_crosscamera_test.py --captures ... --model claude-opus-4-6

    # optional: write the per-pair table to CSV for the record
    python scripts/slabguard_crosscamera_test.py --captures ... --csv results.csv

Outputs: a per-pair metric table (final_verdict, final_confidence, avg_dilated_iou,
border_inliers, lpq_chi2, vision_verdict, cost_usd), then the TRUE-POSITIVE and
FALSE-POSITIVE rates and total Vision cost. Nothing is written to the DB or to prod.
"""

import argparse
import csv as csv_mod
import os
import re
import sys
import threading
from collections import defaultdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Windows stdout must be explicit UTF-8 (cross-project lesson L-2026-015) — we print ✓/✗/—.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Make the repo root importable so `routes.slab_guard_cv` resolves regardless of CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

VALID_EXT = (".jpg", ".jpeg", ".png", ".webp")
# <slug>_copy<A|B|C...>_phone<1|2>  (+ optional phone1b/2b baseline). The slug IS the
# issue id — any prefix (mu1, ironman200, heroesforhope). The trailing $ binds the
# _copy<L>_phone<P> suffix to the END, so a slug that itself contains "_copy" still parses.
NAME_RE = re.compile(
    r"^(?P<issue>.+?)_copy(?P<copy>[A-Za-z])_phone(?P<phone>1b|2b|1|2)$",
    re.IGNORECASE,
)


def discover(captures_dir):
    """Return {(issue, copy, phone): filename} for every well-named capture."""
    found = {}
    skipped = []
    for fn in sorted(os.listdir(captures_dir)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in VALID_EXT:
            continue
        m = NAME_RE.match(stem)
        if not m:
            skipped.append(fn)
            continue
        key = (m["issue"], m["copy"].upper(), m["phone"].lower())
        found[key] = fn
    return found, skipped


def build_pairs(found):
    """
    From discovered captures, build TP/FP pairs (+ optional baselines). Copies are
    enumerated dynamically per issue, so 2-copy and 3+-copy issues are both handled.
    Each pair: dict(issue, kind, fp_mode, expect, ref_file, test_file, label).
      kind    : 'TP' | 'FP' | 'BASE'  (drives the rate math)
      fp_mode : 'cross_camera' | 'same_phone' | ''  (only set on FP rows; splits the metric)
    """
    issues = defaultdict(dict)
    for (issue, copy, phone), fn in found.items():
        issues[issue][(copy, phone)] = fn

    pairs = []
    for issue in sorted(issues):
        c = issues[issue]

        def add(kind, fp_mode, expect, ref_kc, test_kc):
            if ref_kc in c and test_kc in c:
                pairs.append({
                    "issue": issue,
                    "kind": kind,
                    "fp_mode": fp_mode,
                    "expect": expect,
                    "ref_file": c[ref_kc],
                    "test_file": c[test_kc],
                    "label": f"{issue} {kind}{('/' + fp_mode) if fp_mode else ''} "
                             f"{ref_kc[0]}{ref_kc[1]}->{test_kc[0]}{test_kc[1]}",
                })

        copies = sorted({copy for (copy, _phone) in c})

        # TP: each copy matched to itself across the two phones (cross-camera same_copy)
        for cp in copies:
            add("TP", "", "same_copy", (cp, "1"), (cp, "2"))

        # FP cross-camera: every ordered distinct copy pair, ref phone1 vs test phone2.
        # Both orderings (X1->Y2 and Y1->X2) preserve the original A/B coverage.
        for i in range(len(copies)):
            for j in range(len(copies)):
                if i == j:
                    continue
                add("FP", "cross_camera", "different_copy", (copies[i], "1"), (copies[j], "2"))

        # FP same-phone: every distinct unordered copy pair, both shot on the SAME device.
        # Run per phone so a copy-similarity false match is caught independent of camera.
        for phone in ("1", "2"):
            for i in range(len(copies)):
                for j in range(i + 1, len(copies)):
                    add("FP", "same_phone", "different_copy", (copies[i], phone), (copies[j], phone))

        # Optional cross-image (same-camera) baselines
        for cp in copies:
            add("BASE", "", "same_copy", (cp, "1"), (cp, "1b"))
            add("BASE", "", "same_copy", (cp, "2"), (cp, "2b"))

    return pairs


def start_file_server(directory):
    """Serve `directory` on a localhost ephemeral port. Returns (server, base_url)."""
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}"


def main():
    ap = argparse.ArgumentParser(description="Slab Guard cross-camera recovery test (read-only).")
    ap.add_argument("--captures", required=True, help="Directory containing the named capture photos.")
    ap.add_argument("--model", default=None, help="Optional vision model override for the arbiter call.")
    ap.add_argument("--csv", default=None, help="Optional path to write the per-pair table as CSV.")
    args = ap.parse_args()

    captures_dir = os.path.abspath(args.captures)
    if not os.path.isdir(captures_dir):
        print(f"✗ captures dir not found: {captures_dir}")
        sys.exit(1)

    # Import the live CV path AFTER sys.path is set. This is the exact function the
    # marketplace recovery flow calls per registry candidate.
    try:
        from routes.slab_guard_cv import compare_covers_with_vision, CV2_AVAILABLE, ANTHROPIC_AVAILABLE
    except Exception as e:
        print(f"✗ could not import routes.slab_guard_cv: {e}")
        print("  Run from the project venv with opencv + anthropic installed.")
        sys.exit(1)

    if not CV2_AVAILABLE:
        print("✗ OpenCV not available — SIFT copy matching disabled. Install opencv-python-headless.")
        sys.exit(1)
    arbiter_ok = bool(ANTHROPIC_AVAILABLE and os.environ.get("ANTHROPIC_API_KEY"))
    if not arbiter_ok:
        print("⚠  ANTHROPIC_API_KEY not set / anthropic missing. marketplace_mode needs Vision as the")
        print("   PRIMARY verdict; without it the harness falls back to quant-only (confidence capped at")
        print("   0.5) and the result is NOT a valid recovery test. Set the key and re-run.")
        print("   → every CSV row is flagged invalid_no_arbiter=True so a banked run can't")
        print("     later be mistaken for a valid one.")
        # continue anyway so Mike at least sees the quant layer, but flag it loudly.

    found, skipped = discover(captures_dir)
    if skipped:
        print(f"ℹ  ignored {len(skipped)} unrecognized file(s): {', '.join(skipped[:6])}"
              + (" ..." if len(skipped) > 6 else ""))
    if not found:
        print("✗ no well-named captures found. Expected e.g. issue1_copyA_phone1.jpg")
        print("  pattern: issue<N>_copy<A|B>_phone<1|2>.<jpg|jpeg|png|webp>")
        sys.exit(1)

    pairs = build_pairs(found)
    if not pairs:
        print("✗ found captures but could not form any TP/FP pairs. Need, per issue, at least")
        print("  copyA/phone1 + copyA/phone2 (TP) and copyA/phone1 + copyB/phone2 (FP).")
        sys.exit(1)

    n_tp = sum(1 for p in pairs if p["kind"] == "TP")
    n_fp_cross = sum(1 for p in pairs if p["fp_mode"] == "cross_camera")
    n_fp_same = sum(1 for p in pairs if p["fp_mode"] == "same_phone")
    n_base = sum(1 for p in pairs if p["kind"] == "BASE")
    print(f"\nDiscovered {len(found)} captures → {len(pairs)} pairs "
          f"({n_tp} TP, {n_fp_cross} FP cross-camera, {n_fp_same} FP same-phone, {n_base} baseline).")
    print(f"Vision model: {args.model or 'default (Opus 4.8 via opus fallback chain)'}   "
          f"marketplace_mode=True\n")

    httpd, base_url = start_file_server(captures_dir)
    rows = []
    try:
        for p in pairs:
            ref_url = f"{base_url}/{p['ref_file']}"
            test_url = f"{base_url}/{p['test_file']}"
            kw = dict(ref_url=ref_url, test_url=test_url, marketplace_mode=True)
            if args.model:
                kw["model"] = args.model
            try:
                r = compare_covers_with_vision(**kw)
            except Exception as e:
                r = {"success": False, "error": f"{type(e).__name__}: {e}"}

            verdict = (r.get("final_verdict") or r.get("verdict") or "error")
            correct = (verdict == p["expect"])
            mark = "✓" if correct else ("—" if verdict in ("uncertain", "error") else "✗")
            row = {
                "issue": p["issue"],
                "kind": p["kind"],
                "fp_mode": p["fp_mode"],
                "expect": p["expect"],
                "ref": p["ref_file"],
                "test": p["test_file"],
                "final_verdict": verdict,
                "ok": mark,
                "final_confidence": r.get("final_confidence", r.get("confidence")),
                "avg_dilated_iou": r.get("avg_dilated_iou"),
                "border_inliers": (r.get("alignment") or {}).get("border_inliers"),
                "lpq_chi2": r.get("lpq_chi2"),
                "vision_verdict": r.get("vision_verdict"),
                "cost_usd": r.get("cost_usd"),
                "invalid_no_arbiter": (not arbiter_ok),
                "error": r.get("error"),
            }
            rows.append(row)
            print(f"[{mark}] {p['label']:<34} verdict={verdict:<15} "
                  f"conf={row['final_confidence']}  dIoU={row['avg_dilated_iou']}  "
                  f"border={row['border_inliers']}  lpq={row['lpq_chi2']}  "
                  f"vision={row['vision_verdict']}  ${row['cost_usd']}"
                  + (f"  ERR={row['error']}" if row['error'] else ""))
    finally:
        httpd.shutdown()

    # ── Rates ──
    tp_rows = [r for r in rows if r["kind"] == "TP"]
    fp_cross = [r for r in rows if r["fp_mode"] == "cross_camera"]
    fp_same = [r for r in rows if r["fp_mode"] == "same_phone"]
    tp_hits = sum(1 for r in tp_rows if r["final_verdict"] == "same_copy")
    fp_cross_false = sum(1 for r in fp_cross if r["final_verdict"] == "same_copy")
    fp_same_false = sum(1 for r in fp_same if r["final_verdict"] == "same_copy")
    total_cost = sum((r["cost_usd"] or 0) for r in rows)

    print("\n" + "=" * 64)
    print("RESULTS")
    print("=" * 64)
    if not arbiter_ok:
        print("⚠  INVALID RUN — no Vision arbiter (ANTHROPIC_API_KEY/anthropic missing).")
        print("   Rates below are quant-only and must NOT be used as a recovery result.")
    if tp_rows:
        print(f"TRUE-POSITIVE  rate (recovery sensitivity): {tp_hits}/{len(tp_rows)} "
              f"same-copy cross-camera pairs correctly matched")
    if fp_cross:
        print(f"FALSE-POSITIVE — CROSS-CAMERA (LIABILITY — must be 0): {fp_cross_false}/{len(fp_cross)} "
              f"different-copy pairs WRONGLY matched")
    if fp_same:
        print(f"FALSE-POSITIVE — SAME-PHONE  (LIABILITY — must be 0): {fp_same_false}/{len(fp_same)} "
              f"different-copy pairs WRONGLY matched")
    if (fp_cross_false + fp_same_false):
        cam = ("camera-driven" if fp_cross_false and not fp_same_false else
               "copy-similarity-driven" if fp_same_false and not fp_cross_false else
               "both camera- and copy-driven")
        print(f"   ⚠  NON-ZERO FALSE POSITIVES ({cam}) — recovery claim is NOT safe to market as-is.")
    uncertain = sum(1 for r in rows if r["final_verdict"] in ("uncertain", "error"))
    if uncertain:
        print(f"({uncertain} pair(s) returned uncertain/error — neither match nor clear non-match.)")
    print(f"Total Vision cost for this run: ${total_cost:.4f}")
    print("=" * 64)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv_mod.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nPer-pair table written to {args.csv}")


if __name__ == "__main__":
    main()

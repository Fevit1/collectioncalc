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
or upload anything to R2, this harness spins up ONE localhost static file server per phone
directory and passes http://127.0.0.1:PORT/<file> URLs. Nothing leaves the machine.

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

PHONE = FOLDER. Put each device's photos in its own directory (--phone1, --phone2). The
SAME physical copy must carry the SAME copy number on both phones (copy 1 on phone1 and
copy 1 on phone2 are the same book) — the whole TP/FP mapping depends on that alignment.

Name every file (extension .jpg/.jpeg/.png/.webp), identically in both phone folders:

    <Issue_Name>_<Front|Back>_<copyNumber>.<ext>
    e.g.  Iron_Man_200_Front_1.jpg            Iron_Man_200_Front_2.jpg
          Marvel_Universe_1_Front_1.jpg       Marvel_Universe_1_Back_1.jpg
          Wolverine_..._Hulk_1_Front_3.jpg    (3rd copy, if present)
    Copy numbers are 1, 2, 3, ...  Front/Back let you test either side (default: front).

Pairs the harness builds per issue (copies enumerated dynamically from what it finds)
-------------------------------------------------------------------------------------
    TP                : copyX/phone1 vs copyX/phone2   expect same_copy   (one per copy)
    FP / cross_camera : copyX/phone1 vs copyY/phone2   expect different_copy (every ordered X!=Y)
    FP / same_phone   : copyX/phoneN vs copyY/phoneN   expect different_copy (every X<Y, per phone)

The two FP modes report separately: a cross_camera false positive is camera-driven, a
same_phone false positive is copy-similarity-driven. Both must be 0; the split says which.

Run
---
    # from the repo root, in the project venv (needs opencv + anthropic + ANTHROPIC_API_KEY)
    python scripts/slabguard_crosscamera_test.py \
        --phone1 "C:/.../tests/SlabGuardTests/PixelPhotos" \
        --phone2 "C:/.../tests/SlabGuardTests/iPhonePhotos"

    # discovery dry-run (no phone2 yet): only same-phone FP pairs form, not a recovery test
    python scripts/slabguard_crosscamera_test.py --phone1 "C:/.../PixelPhotos"

    # optional: A/B a different vision model for the arbiter (default is Opus 4.8)
    python scripts/slabguard_crosscamera_test.py --phone1 ... --phone2 ... --model claude-sonnet-4-6

    # optional: test back covers too, and write the per-pair table to CSV for the record
    python scripts/slabguard_crosscamera_test.py --phone1 ... --phone2 ... --side both --csv results.csv

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
# Real-shoot capture naming (one file per copy, per side):
#     <Issue_Name>_<Front|Back>_<copyNumber>.<ext>
#     e.g.  Iron_Man_200_Front_1.jpg   Marvel_Universe_1_Back_2.jpg
# The PHONE is the FOLDER (--phone1 / --phone2), NOT the filename. The greedy issue
# group + the $-anchored _(Front|Back)_<n> suffix mean an issue name that itself ends
# in a number (Marvel_Universe_1) still parses correctly.
NAME_RE = re.compile(
    r"^(?P<issue>.+)_(?P<side>Front|Back)_(?P<copy>\d+)$",
    re.IGNORECASE,
)
# Alt layout 'crosscam-fp' (the FalsePostiveTest set): one DIFFERENT physical copy per
# phone, phone label baked into the filename and also the folder:
#     <Issue_Name>_<Front|Back>_<Pixel|iPhone>.<ext>
# We take issue+side from the name but derive copy identity from the FOLDER (phone), so a
# same-issue Pixel↔iPhone pair is correctly treated as two different copies (cross-camera FP).
FP_NAME_RE = re.compile(
    r"^(?P<issue>.+)_(?P<side>Front|Back)_(?P<label>Pixel|iPhone)$",
    re.IGNORECASE,
)


def discover(phone_dir, phone, side, layout="copynum"):
    """
    Scan ONE phone's directory for ONE cover side. Return
    ({(issue, copy, phone): filename}, [skipped filenames]). `phone` is '1' or '2',
    `side` is 'front' or 'back'. Files of the other side (or unrecognized names) go to
    `skipped`.

    layout='copynum'     : <Issue>_<Front|Back>_<copyNumber>; copy = the number ('1','2','3').
    layout='crosscam-fp' : <Issue>_<Front|Back>_<Pixel|iPhone>; copy is derived from the
                           PHONE/folder ('pix' on phone1, 'iph' on phone2) so a same-issue
                           Pixel↔iPhone pair reads as two different copies.
    """
    regex = FP_NAME_RE if layout == "crosscam-fp" else NAME_RE
    found = {}
    skipped = []
    for fn in sorted(os.listdir(phone_dir)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in VALID_EXT:
            continue
        m = regex.match(stem)
        if not m:
            skipped.append(fn)
            continue
        if m["side"].lower() != side:
            skipped.append(fn)
            continue
        copy = m["copy"] if layout == "copynum" else ("pix" if phone == "1" else "iph")
        key = (m["issue"], copy, phone)
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
                    "ref_phone": ref_kc[1],
                    "test_phone": test_kc[1],
                    "label": f"{issue} {kind}{('/' + fp_mode) if fp_mode else ''} "
                             f"c{ref_kc[0]}p{ref_kc[1]}->c{test_kc[0]}p{test_kc[1]}",
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
    ap.add_argument("--phone1", required=True,
                    help="Directory of phone-1 photos (e.g. .../PixelPhotos).")
    ap.add_argument("--phone2", default=None,
                    help="Directory of phone-2 photos (e.g. .../iPhonePhotos). Omit for a discovery "
                         "dry-run — only same-phone FP pairs form; NOT a valid recovery test.")
    ap.add_argument("--side", choices=["front", "back", "both"], default="front",
                    help="Cover side(s) to test. Default 'front' (the documented recovery surface). "
                         "'both' runs front-vs-front and back-vs-back as separate passes, never mixed.")
    ap.add_argument("--layout", choices=["copynum", "crosscam-fp"], default="copynum",
                    help="Filename layout. 'copynum' (default): <Issue>_<Front|Back>_<copyNumber>. "
                         "'crosscam-fp': the FalsePostiveTest set — <Issue>_<Front|Back>_<Pixel|iPhone>, "
                         "one different copy per phone; yields same-issue cross-camera FP pairs only.")
    ap.add_argument("--model", default=None, help="Optional vision model override for the arbiter call.")
    ap.add_argument("--csv", default=None, help="Optional path to write the per-pair table as CSV.")
    args = ap.parse_args()

    dir1 = os.path.abspath(args.phone1)
    if not os.path.isdir(dir1):
        print(f"✗ phone1 dir not found: {dir1}")
        sys.exit(1)
    dir2 = os.path.abspath(args.phone2) if args.phone2 else None
    if args.phone2 and not os.path.isdir(dir2):
        print(f"✗ phone2 dir not found: {dir2}")
        sys.exit(1)
    if args.layout == "crosscam-fp" and not dir2:
        print("✗ --layout crosscam-fp needs both --phone1 (Pixel) and --phone2 (iPhone) folders.")
        sys.exit(1)
    if not dir2:
        print("⚠  --phone2 not given: cross-camera TP/FP pairs cannot form. Only same-phone FP")
        print("   pairs within phone1 will run — a useful dry-run, but NOT a recovery result.")

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

    sides = ["front", "back"] if args.side == "both" else [args.side]

    # One static file server per phone directory: filenames are IDENTICAL across phones
    # (same issue, same copy number), so each phone is served from its own root and the
    # correct base is chosen per pair via the ref/test phone token.
    httpd1, base1 = start_file_server(dir1)
    base_by_phone = {"1": base1}
    servers = [httpd1]
    if dir2:
        httpd2, base2 = start_file_server(dir2)
        base_by_phone["2"] = base2
        servers.append(httpd2)

    rows = []
    try:
        for side in sides:
            found, skipped = discover(dir1, "1", side, args.layout)
            if dir2:
                f2, s2 = discover(dir2, "2", side, args.layout)
                found.update(f2)
                skipped += s2
            if skipped:
                print(f"ℹ  [{side}] ignored {len(skipped)} unrecognized/other-side file(s).")
            if not found:
                print(f"✗ [{side}] no well-named captures. Expected e.g. Iron_Man_200_Front_1.jpg")
                continue

            pairs = build_pairs(found)
            if not pairs:
                print(f"✗ [{side}] found captures but formed no pairs "
                      "(need ≥2 copies per issue; for TP/cross-camera, supply --phone2).")
                continue

            n_tp = sum(1 for p in pairs if p["kind"] == "TP")
            n_fp_cross = sum(1 for p in pairs if p["fp_mode"] == "cross_camera")
            n_fp_same = sum(1 for p in pairs if p["fp_mode"] == "same_phone")
            print(f"\n[{side.upper()}] {len(found)} captures → {len(pairs)} pairs "
                  f"({n_tp} TP, {n_fp_cross} FP cross-camera, {n_fp_same} FP same-phone).")
            print(f"Vision model: {args.model or 'default (Opus 4.8 via opus fallback chain)'}   "
                  f"marketplace_mode=True")

            for p in pairs:
                ref_url = f"{base_by_phone[p['ref_phone']]}/{p['ref_file']}"
                test_url = f"{base_by_phone[p['test_phone']]}/{p['test_file']}"
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
                    "side": side,
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
                print(f"[{mark}] {p['label']:<46} verdict={verdict:<15} "
                      f"conf={row['final_confidence']}  dIoU={row['avg_dilated_iou']}  "
                      f"border={row['border_inliers']}  lpq={row['lpq_chi2']}  "
                      f"vision={row['vision_verdict']}  ${row['cost_usd']}"
                      + (f"  ERR={row['error']}" if row['error'] else ""))
    finally:
        for s in servers:
            s.shutdown()

    if not rows:
        print("\n✗ no pairs ran — nothing to report. (Need ≥2 copies per issue; for TP and "
              "cross-camera FP, supply --phone2.)")
        sys.exit(1)

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

"""
Grade-submission retention.

Persists every /api/grade submission — the photos plus the assigned grade, the 8
subgrades, confidence, and the identified comic — so grading-accuracy complaints are
diagnosable (the thing that was MISSING when we tried to investigate matbanshee).
See docs/technical/GRADE_RETENTION_SPEC.md.

- Images are stored in Cloudflare R2 at grade_submissions/{id}/{label}.jpg; metadata
  lives in the grade_submissions table (`photos` jsonb maps label -> R2 key).
- Persistence runs on a background thread so it adds NO latency to the grade response.
- Retention window is 90 days (disclosed in privacy.html). The 90-day auto-purge is a
  SEPARATE scheduled job (deferred; see TODO). This module only persists and provides
  the admin find/delete (erasure) surface that honors the deletion-on-request right.
"""
import threading
import psycopg2
from psycopg2.extras import RealDictCursor, Json

RETENTION_DAYS = 90


def _to_int_or_none(v):
    try:
        if v is None or v == '':
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────
# PERSIST (Part 1)
# ──────────────────────────────────────────────

def persist_grade_submission_async(user_id, images, photo_labels, result, model, database_url):
    """Fire-and-forget persist on a daemon thread so the grade response isn't delayed.

    All Flask request state (g/request) must be resolved by the caller and passed in —
    the thread runs outside the request context.
    """
    t = threading.Thread(
        target=_persist_grade_submission,
        args=(user_id, images, photo_labels, result, model, database_url),
        daemon=True,
    )
    t.start()


def _persist_grade_submission(user_id, images, photo_labels, result, model, database_url):
    """Insert the row, upload images to R2 under the row id, backfill the keys. Never raises."""
    conn = None
    try:
        grade = result.get('final_grade')
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO grade_submissions
                 (user_id, title, issue, year, publisher, grade, grade_label,
                  raw_grade, category_scores, limiting_factor, confidence, photos_used,
                  defects, photo_labels, model, run_count, grade_reasoning,
                  reread_fired, saved_collection_id, images_purge_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,
                       NULL, NULL, (now() AT TIME ZONE 'utc') + make_interval(days => %s))
               RETURNING id""",
            (
                user_id,
                result.get('title'),
                str(result.get('issue')) if result.get('issue') is not None else None,
                _to_int_or_none(result.get('year')),
                result.get('publisher'),
                grade if isinstance(grade, (int, float)) else None,
                result.get('grade_label'),
                result.get('raw_grade'),
                Json(result.get('category_scores') or {}),
                result.get('limiting_factor'),
                _to_int_or_none(result.get('confidence')),
                _to_int_or_none(result.get('photos_used')),
                Json(result.get('defects') or {}),
                Json(photo_labels or []),
                model,
                _to_int_or_none(result.get('run_count')),
                result.get('grade_reasoning') or result.get('observations'),
                RETENTION_DAYS,
            ),
        )
        submission_id = cur.fetchone()[0]
        conn.commit()

        # Upload images now that we have the id for the R2 path.
        from r2_storage import upload_image
        photos = {}
        for img in images or []:
            b64 = img.get('base64', '')
            if not b64:
                continue
            label = (img.get('label') or 'photo').strip().lower().replace(' ', '_') or 'photo'
            key = f"grade_submissions/{submission_id}/{label}.jpg"
            up = upload_image(b64, key, content_type=img.get('media_type', 'image/jpeg'))
            if up.get('success'):
                photos[label] = key

        cur.execute("UPDATE grade_submissions SET photos = %s WHERE id = %s",
                    (Json(photos), submission_id))
        conn.commit()
        cur.close()
        print(f"[GradeRetention] persisted submission #{submission_id} "
              f"({len(photos)} image(s), grade={grade})")
    except Exception as e:
        print(f"[GradeRetention] persist failed (non-fatal): {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ──────────────────────────────────────────────
# DELETE / ERASURE (Part 2) — cascades to BOTH the DB row AND the R2 objects
# ──────────────────────────────────────────────

def _delete_r2_keys(keys):
    """Delete a list of R2 keys; returns (deleted_count, failed_count)."""
    from r2_storage import delete_image
    deleted, failed = 0, 0
    for k in keys:
        if not k:
            continue
        try:
            if delete_image(k).get('success'):
                deleted += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return deleted, failed


def _keys_from_photos(photos):
    return list(photos.values()) if isinstance(photos, dict) else []


def delete_grade_submission(submission_id, database_url):
    """Delete one submission: R2 objects FIRST, then the DB row. Never orphans images.

    Returns {'success', 'submission_id', 'images_deleted', 'images_failed'} or an error.
    """
    conn = None
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT id, photos FROM grade_submissions WHERE id = %s", (submission_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return {'success': False, 'error': 'not_found'}

        deleted, failed = _delete_r2_keys(_keys_from_photos(row.get('photos')))
        cur.execute("DELETE FROM grade_submissions WHERE id = %s RETURNING id", (submission_id,))
        cur.fetchone()
        conn.commit()
        cur.close()
        return {'success': True, 'submission_id': submission_id,
                'images_deleted': deleted, 'images_failed': failed}
    except Exception as e:
        if conn:
            conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def delete_user_grade_submissions(user_id, database_url):
    """Erasure helper: delete ALL of a user's grade submissions (R2 objects + DB rows).

    Used to honor a deletion-on-request / account-deletion erasure for grade data.
    Returns {'success', 'rows_deleted', 'images_deleted', 'images_failed'} or an error.
    """
    conn = None
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT id, photos FROM grade_submissions WHERE user_id = %s", (user_id,))
        rows = cur.fetchall()

        all_keys = []
        for r in rows:
            all_keys.extend(_keys_from_photos(r.get('photos')))
        deleted, failed = _delete_r2_keys(all_keys)

        cur.execute("DELETE FROM grade_submissions WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        return {'success': True, 'rows_deleted': len(rows),
                'images_deleted': deleted, 'images_failed': failed}
    except Exception as e:
        if conn:
            conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

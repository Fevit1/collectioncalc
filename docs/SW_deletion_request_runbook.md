# Slab Worthy — Data Deletion Request Runbook (internal)

Internal process for honoring "delete my data" requests. Matches the privacy policy
(deletion within 30 days; honored from anyone). **Human-run; never auto-delete.**

---

## Step 1 — Verify ownership
Controlling the registered email proves ownership (like a password reset).

- If the request comes from the account's **registered email** → verified, proceed.
- If it comes from a **different address** (or anything's off) → do **NOT** delete; reply to the
  account's **registered email** to confirm before acting.
- Never delete on an unverified claim. Never ask for ID or sensitive proof — email ownership is enough.

## Step 2 — Identify scope
Look up the user in admin. Their data spans:

- **Account record** (if they want the account deleted)
- **Saved collection comics + R2 images**
- **Grade submissions** — saved **AND** unsaved (the ~90-day retained photos/grades). **Don't forget these.**
- **Slab Guard registrations** (`comic_registry`) — the policy says deleting the account deletes these too, and
  that any or all of them can be deleted on request without deleting the account. **Nothing else ever deletes
  a registration** (no purge job, nothing on downgrade — verified 2026-09-17), so this step is the only way
  "deleted" happens.

Confirm scope if ambiguous.

## Step 3 — Delete
Use the admin find-and-delete tool. Deletion must cascade to **BOTH** the DB rows **AND** the R2
objects (**R2 first, then rows — never orphan images**). Confirm the `images_deleted` count.

### Step 3b — Slab Guard registrations (by hand; the admin tool does not touch `comic_registry`)

1. **List them first** and put the list in the log (2026-09-17: 23 rows exist in total, 21 `active`, 2 `recovered`):
   ```sql
   SELECT id, serial_number, status, reported_stolen_date, recovery_date, certificate_url
   FROM comic_registry WHERE user_id = <user_id>;
   ```
2. **A registration marked `reported_stolen` stops being matchable the moment it is deleted** — the fingerprint
   is what the marketplace monitor compares against. If the request is "delete everything", confirm in the
   reply to the registered email that the stolen-comic record goes too and that we will no longer be able to
   match it; if the request is "delete some", the owner may keep the stolen one. `recovered` and `active` rows
   delete like any other. There is no "freeze" state — a registration either exists (and is matched) or is gone.
3. **Delete in this order** (`sighting_reports` references the serial number WITHOUT cascade, so a registration
   with sightings cannot be deleted until they are; `match_reports` cascades from the registry row on its own):
   ```sql
   DELETE FROM sighting_reports
   WHERE serial_number IN (SELECT serial_number FROM comic_registry WHERE user_id = <user_id>);
   DELETE FROM comic_registry WHERE user_id = <user_id>;   -- or WHERE id IN (...) for "some"
   ```
   If a `certificate_url` pointed at an object in R2, delete that object as well (same rule as images: object
   first, then the row).
4. **Whole-account deletion:** `comic_registry.user_id` is `ON DELETE CASCADE` in the live schema, so deleting
   the `users` row removes the registrations and their match reports by itself — but step 3's `sighting_reports`
   delete must still run FIRST or the user delete fails on the foreign key. Confirm the registry count for the
   user is 0 afterwards.

## Step 4 — Confirm back
Reply confirming what was deleted and when.

---

## Timing
Within 30 days (policy); in practice same-day. Don't let a request sit past ~2 weeks.

## Logging
Keep a light record (date, account, scope, completed date).

## Never
- Auto-delete from a parsed email.
- Delete on sender/account mismatch without confirming via the registered email.
- Ignore unsaved grade submissions.
- Forget the registrations: the policy promises they go with the account, and no job does it for you.
- Delete a `reported_stolen` registration without saying, in the confirmation, that the comic can no longer be matched.
- Claim deletion done before the R2 objects are actually gone.

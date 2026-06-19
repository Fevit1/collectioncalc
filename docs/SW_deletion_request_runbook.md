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

Confirm scope if ambiguous.

## Step 3 — Delete
Use the admin find-and-delete tool. Deletion must cascade to **BOTH** the DB rows **AND** the R2
objects (**R2 first, then rows — never orphan images**). Confirm the `images_deleted` count.

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
- Claim deletion done before the R2 objects are actually gone.

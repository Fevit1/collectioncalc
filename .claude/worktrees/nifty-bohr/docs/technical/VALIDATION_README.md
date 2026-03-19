# Slab Worthy Code Validation System

## Purpose
Catch bugs **before** presenting code to the user. These scripts validate HTML/JS and Python code for common errors that waste debugging time.

## Scripts

### `validate-frontend.sh`
Validates HTML/JS files for:
- ✅ Missing `getElementById()` targets
- ✅ Duplicate variable declarations
- ✅ Undefined function calls
- ✅ Basic HTML structure
- ✅ Unclosed tags

**Usage:**
```bash
bash validate-frontend.sh app.html
bash validate-frontend.sh collection.html
```

### `validate-backend.py`
Validates Python Flask files for:
- ✅ Python syntax errors
- ✅ Flask route definitions
- ✅ Required imports
- ✅ SQL injection vulnerabilities
- ✅ Database connection handling
- ✅ Error handling (try/except)

**Usage:**
```bash
python3 validate-backend.py sales.py
python3 validate-backend.py collection.py
```

### `validate-all.sh`
Master script that runs all validations.

**Usage:**
```bash
bash validate-all.sh
```

---

## Claude's Workflow (MANDATORY)

### Before Presenting ANY Code Changes:

1. **Copy files to outputs directory:**
   ```bash
   cp app.html /mnt/user-data/outputs/
   cp collection.html /mnt/user-data/outputs/
   cp sales.py /mnt/user-data/outputs/
   ```

2. **Run validation:**
   ```bash
   cd /mnt/user-data/outputs
   bash validate-all.sh
   ```

3. **If validation PASSES ✅:**
   - Present files to user with confidence
   
4. **If validation FAILS ❌:**
   - Fix the issues
   - Re-run validation
   - DO NOT present code until it passes

---

## Why This Matters

### Real Example (Session 36):
**Bug:** JavaScript called `getElementById('gradingVerdict')` but HTML had `id="recommendationVerdict"`

**Result:** "Should You Slab It?" section never appeared

**Time Wasted:** 30+ minutes debugging

**Could Have Been Caught:** In 2 seconds with `validate-frontend.sh`

---

## For User

You can also run these scripts before deploying to catch issues:

```bash
# In your frontend repo
bash validate-frontend.sh app.html

# In your backend repo  
python3 validate-backend.py routes/sales.py
```

**But Claude should catch these first!**

---

## Future Improvements

Possible additions:
- [ ] CSS class reference validation
- [ ] API endpoint matching (frontend calls vs backend routes)
- [ ] Automated Playwright integration tests
- [ ] Pre-commit git hooks
- [ ] CI/CD integration

---

## Credits

Suggested by user's Caltech PhD friend - this is **standard engineering practice**, not overkill.

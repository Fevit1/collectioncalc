# CollectionCalc Troubleshooting Playbook
**Your step-by-step guide to fixing deployment and runtime issues**

---

## 🚨 QUICK TRIAGE - Start Here

### Is the server responding?
```powershell
# Test health endpoint
curl https://collectioncalc-docker.onrender.com/health
```

**Expected:** `{"status": "ok", "version": "4.3.0", ...}`

**If you get:**
- ✅ **200 OK** → Server is up, skip to "Route-Specific Issues"
- ❌ **503/502** → Server is down, go to "Server Won't Start"
- ❌ **Timeout** → Render might be sleeping, check Render dashboard

---

## 🔴 SERVER WON'T START

### Step 1: Check Render Logs

Go to Render Dashboard → Logs, look for error patterns:

#### Pattern A: ImportError
```
ImportError: cannot import name 'X' from 'Y'
```

**Cause:** Module `Y` doesn't have function/class `X`

**Fix:**
1. Check if `X` exists in `Y.py`:
   ```powershell
   Select-String -Path Y.py -Pattern "def X"
   ```
2. If missing → Add it or remove the import
3. If present → Force reload:
   ```powershell
   Add-Content -Path Y.py -Value "`n# Force reload"
   git add Y.py
   git commit -m "Force reload Y.py"
   git push
   deploy
   ```

#### Pattern B: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'routes'
```

**Cause:** Directory not deployed or missing `__init__.py`

**Fix:**
```powershell
# Check __init__.py exists
Test-Path routes\__init__.py

# If missing, create it
New-Item -Path routes\__init__.py -ItemType File -Force

# Commit
git add routes\__init__.py
git commit -m "Add missing __init__.py"
git push
deploy
```

#### Pattern C: Worker Failed to Boot
```
[ERROR] Worker (pid:7) exited with code 3
[ERROR] Reason: Worker failed to boot
```

**Cause:** Syntax error, import error, or runtime error in startup code

**Fix:**
1. Look for the **actual error** above these lines in logs
2. It will show which file/line caused the problem
3. Fix that specific error
4. Common causes:
   - Missing comma in list
   - Indentation error
   - Circular import
   - Missing dependency

---

## 🟡 SERVER STARTS BUT ROUTES FAIL

### Check if specific route exists

```powershell
# Test a specific route
curl -X POST https://collectioncalc-docker.onrender.com/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"test@test.com","password":"test"}'
```

**If you get 404:**

1. **Check blueprint registration:**
   ```powershell
   Select-String -Path wsgi.py -Pattern "register_blueprint"
   ```
   Should see: `app.register_blueprint(auth_bp)`

2. **Check URL prefix matches:**
   - Blueprint: `auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')`
   - Route: `@auth_bp.route('/login', methods=['POST'])`
   - Full URL: `/api/auth/login` ✅

3. **Check route is in the right blueprint:**
   - Login route should be in `routes/auth_routes.py`
   - Sales route should be in `routes/sales.py`
   - See ROUTE_MAPPING.md for full list

---

## 🟢 CHROME EXTENSION ISSUES

### Extension showing errors in console

**Symptoms:**
- "Failed to fetch"
- "Network error"
- "500 Internal Server Error"

### Debug Steps:

**1. Check server is actually up:**
```powershell
curl https://collectioncalc-docker.onrender.com/health
```

**2. Check the specific endpoint the extension uses:**

For eBay Collector extension:
```powershell
# Test batch endpoint
curl -X POST https://collectioncalc-docker.onrender.com/api/ebay-sales/batch `
  -H "Content-Type: application/json" `
  -d '{"sales":[]}'
```

Expected: `{"error": "No sales provided"}` (400 status is OK - means route works!)

**3. Check extension permissions:**
- Open Chrome → Extensions → eBay Collector → Details
- Verify "Site access" includes `collectioncalc-docker.onrender.com`

**4. Check CORS:**
```powershell
# Look for CORS config in wsgi.py
Select-String -Path wsgi.py -Pattern "CORS"
```
Should see: `CORS(app, resources={r"/api/*": {"origins": "*"}})`

**5. Common Extension Fixes:**
- **Clear extension cache:** Chrome Extensions → Remove → Reinstall
- **Check API key/auth:** Extensions may cache old tokens
- **Reload extension:** Click reload button in Extensions page

---

## 🔧 COMMON FIXES CHEAT SHEET

### Force Python to Reload a File
```powershell
Add-Content -Path filename.py -Value "`n# Force reload $(Get-Date)"
git add filename.py
git commit -m "Force reload"
git push
deploy
```

### Clear All Python Cache
```powershell
Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Force -Recurse
git add .
git commit -m "Clear Python cache"
git push
deploy
```

### Emergency Rollback (Last Working Version)
```powershell
git revert HEAD
git push
deploy
```

### Rollback Multiple Commits
```powershell
# See recent commits
git log --oneline -5

# Rollback to specific commit
git reset --hard abc123  # Replace abc123 with commit hash
git push --force
deploy
```

### Check What Changed in Last Deploy
```powershell
git log -1 --stat
```

### See Diff of a Specific File
```powershell
git diff HEAD~1 wsgi.py
```

---

## 📊 DIAGNOSTIC COMMANDS

### File Checks
```powershell
# Check if function exists in file
Select-String -Path auth.py -Pattern "def require_auth"

# List all routes in a blueprint
Select-String -Path routes\sales.py -Pattern "@sales_bp.route"

# Check imports in a file
Select-String -Path wsgi.py -Pattern "^from|^import"

# Verify routes directory structure
Get-ChildItem -Path routes -Recurse
```

### Git Checks
```powershell
# Current branch
git branch

# What's changed but not committed
git status

# What's committed but not pushed
git log origin/main..HEAD

# See file at specific commit
git show abc123:wsgi.py
```

### Render Checks
```powershell
# Check if deploy is running (in Render dashboard)
# Look for: "Building..." or "Deploying..."

# Check environment variables set (in Render dashboard)
# Settings → Environment → Should see DATABASE_URL, JWT_SECRET, etc.
```

---

## 🔍 ERROR PATTERN LOOKUP

### "cannot import name 'X' from 'Y'"

**Checklist:**
- [ ] Does `X` exist in `Y.py`?
- [ ] Is `X` spelled correctly (case-sensitive)?
- [ ] Is `X` defined before it's imported?
- [ ] Is there a circular import? (A imports B, B imports A)

**Solution Matrix:**

| Situation | Action |
|-----------|--------|
| X doesn't exist in Y | Add X to Y.py or remove import |
| X exists but misspelled | Fix spelling in import |
| Circular import | Move shared code to new module |
| Python cache issue | Force reload (add comment) |

### "Worker failed to boot"

**Always means:** Something crashed during startup

**Find the real error:**
1. Scroll up in Render logs
2. Look for `File "/app/...`, line XX` 
3. That line has the actual problem

**Common causes:**
- Missing imports
- Syntax errors
- Division by zero in global code
- File not found during import

### "404 Not Found" on valid route

**Checklist:**
- [ ] Blueprint registered in wsgi.py?
- [ ] URL prefix correct?
- [ ] Route decorator uses correct method?
- [ ] Blueprint URL matches frontend call?

**Example debug:**
```powershell
# Route defined as:
@sales_bp.route('/fmv', methods=['GET'])  # in sales.py with prefix='/api/sales'

# Should be accessible at:
# GET /api/sales/fmv

# Check registration:
Select-String -Path wsgi.py -Pattern "register_blueprint.*sales"
```

### "Module 'X' has no attribute 'Y'"

**Cause:** Trying to access something that doesn't exist

**Common in CollectionCalc:**
- `anthropic.Anthropic()` → Check if anthropic installed
- `R2_AVAILABLE` → Check if r2_storage imported
- `BARCODE_AVAILABLE` → Check if pyzbar imported (Docker only)

**Fix:** Add try/except or check availability first

---

## 🎯 BLUEPRINT-SPECIFIC ISSUES

### Auth Routes Not Working (`/api/auth/*`)

**File:** `routes/auth_routes.py`

**Common issues:**
- Missing decorators in `auth.py` (`require_auth`, `require_approved`)
- JWT_SECRET not set in environment
- Database connection failing

**Test:**
```powershell
# Test login (should return error about credentials, not 500)
curl -X POST https://collectioncalc-docker.onrender.com/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"test","password":"test"}'
```

### Admin Routes Not Working (`/api/admin/*`)

**File:** `routes/admin_routes.py`

**Common issues:**
- Missing `require_admin_auth` decorator
- Moderation functions not passed to init_modules
- Database queries failing

**Test:**
```powershell
# Test dashboard (should return 401 unauthorized, not 500)
curl https://collectioncalc-docker.onrender.com/api/admin/dashboard
```

### Grading Routes Not Working (`/api/valuate`, `/api/extract`)

**File:** `routes/grading.py`

**Common issues:**
- ANTHROPIC_API_KEY not set
- Moderation functions missing
- ebay_valuation module not imported

**Test:**
```powershell
# Test valuate (should return error about auth, not 500)
curl -X POST https://collectioncalc-docker.onrender.com/api/valuate `
  -H "Content-Type: application/json" `
  -d '{}'
```

---

## 🚑 EMERGENCY PROCEDURES

### Site is Down, Need it Back ASAP

**Option 1: Instant Rollback (safest)**
```powershell
# Rollback to last working version
git revert HEAD
git push
deploy
# Wait 2-3 minutes for deploy
```

**Option 2: Rollback to Specific Known-Good Version**
```powershell
# Find the last good commit (check journal.txt or git log)
git log --oneline -10

# Rollback to it (example: abc123)
git reset --hard abc123
git push --force
deploy
```

**Option 3: Use Render's Manual Deploy**
- Go to Render Dashboard
- Click "Manual Deploy"
- Select a previous commit from dropdown
- Click "Deploy"

### Database is Corrupted/Migration Failed

**Don't panic - data is probably fine**

1. Check if it's just connection issue:
   ```powershell
   # Check if DATABASE_URL is set in Render
   # Dashboard → Environment → DATABASE_URL
   ```

2. Test database directly (if you have psql):
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
   ```

3. If migration failed, check for:
   - Typos in SQL
   - Missing tables
   - Constraint violations

### Extensions Stopped Working After Deploy

**Symptoms:**
- Extensions were working
- Deployed changes
- Now extensions show errors

**Likely causes:**

1. **API route moved/renamed:**
   - Check ROUTE_MAPPING.md
   - Verify blueprint has correct URL prefix
   - Example: `/api/ebay-sales/batch` must still work

2. **Server is down:**
   - Check /health endpoint
   - Check Render logs for errors

3. **CORS issue:**
   - Check `CORS(app, resources=...)` in wsgi.py
   - Should allow `*` origins

**Quick test:**
```powershell
# Test the exact endpoint extension uses
# For eBay Collector:
curl -X POST https://collectioncalc-docker.onrender.com/api/ebay-sales/batch `
  -H "Content-Type: application/json" `
  -d '{"sales":[]}'

# Should get 400 error "No sales provided" (this is good! Route works!)
```

---

## 🌐 CLOUDFLARE PAGES (FRONTEND) DEPLOYMENT ISSUES

### Symptoms: Live site not updating after git push

**You pushed changes, maybe even purged the CDN cache, but the live site still shows old content.**

#### Step 1: Confirm git push actually went through
```powershell
git log origin/main --oneline -3
```
If your latest commit is there, the push succeeded.

#### Step 2: Check for failed Cloudflare Pages deployment
- Go to **Cloudflare Dashboard → Pages → slabworthy → Deployments**
- Look for red/failed deployments
- Click on the failed deployment to see the error

#### Step 3: Check repo size and file count

**⚠️ THIS IS THE #1 GOTCHA (Session 61, Feb 23 2026)**

Cloudflare Pages has a **20,000 file limit** and size constraints. If large binary files (images, .docx, .zip, test data) get committed to git, Cloudflare Pages deployments can **silently fail** and keep serving the last successful deployment.

**Diagnosis:**
```powershell
# Check if there are untracked large files or folders in git
git ls-files | Measure-Object -Line

# Check repo size
git count-objects -vH

# Look for large files that shouldn't be tracked
git ls-files | Select-String -Pattern "\.(jpg|jpeg|png|docx|pptx|xlsx|zip|pdf)$"
```

**What happened in Session 61:**
A previous commit accidentally added hundreds of binary files (ComicBookImages/, _cleanup_candidates/, test photos, .docx files) to git. The files were later deleted locally but the **deletions were never committed** — so origin/main still had them all. Cloudflare Pages couldn't deploy the bloated repo, so it kept serving the old version. Purging the CDN cache had no effect because the deployment itself was stuck.

**Fix:**
```powershell
# Stage all deletions of tracked files (without adding untracked files)
git add -u

# Commit and push
git commit -m "Remove binary files bloating repo"
git push
```

**Prevention:**
- Always use `git add <specific files>` instead of `git add .`
- Keep `.gitignore` updated with patterns for images, binaries, and test data
- The current `.gitignore` has patterns for: `ComicBookImages/`, `_cleanup_candidates/`, `WV/`, credential files, and common binary extensions
- Before committing, run `git status` and review what's being staged

#### Step 4: Check if footer.js is being served correctly
```powershell
# In browser DevTools (F12), check Console for JS errors
# Or test directly:
curl -s -o NUL -w "%{content_type}" https://slabworthy.com/js/footer.js
```
**Expected:** `application/javascript` or `text/javascript`
**Bad sign:** `text/html` — means Cloudflare is serving an HTML fallback instead of the JS file

#### Step 5: Check `_routes.json` configuration
```json
{
  "version": 1,
  "include": ["/*"],
  "exclude": ["/js/*", "/images/*", "/icons/*", "/*.css", "/*.js", "/manifest.json", "/robots.txt", "/sw.js"]
}
```
- `exclude` paths are served as **static files** (bypass Functions middleware)
- `include` paths go through `_middleware.js`
- If a static file isn't found, Cloudflare may serve HTML fallback → JS files break

#### Step 6: Service worker caching (browser-side)

The service worker (`sw.js`) uses network-first strategy, so it should always get fresh content. But if a user installed the PWA, they might have stale cache.

**Force service worker update (for users):**
- Hard refresh: `Ctrl+Shift+R`
- Clear site data: DevTools → Application → Storage → Clear site data
- Unregister service worker: DevTools → Application → Service Workers → Unregister

**Force service worker update (for devs):**
Bump the cache version in `sw.js`:
```javascript
const CACHE_NAME = 'slabworthy-v2';  // was v1
```
Commit and push — the new service worker will activate and clear old caches.

#### Step 7: Trigger a fresh deploy

If all else fails, push a trivial commit to force a new Cloudflare Pages build:
```powershell
git commit --allow-empty -m "Trigger Cloudflare Pages redeploy"
git push
```

### Cloudflare Pages Deployment Checklist

When the live site isn't updating:

- [ ] Did `git push` succeed? (`git log origin/main --oneline -1`)
- [ ] Is the Cloudflare Pages deployment green? (check dashboard)
- [ ] Are there large binary files bloating the repo? (`git ls-files | Select-String "\.(jpg|jpeg|png)"`)
- [ ] Are there deleted files that need to be committed? (`git status` — look for "deleted:" lines)
- [ ] Is `footer.js` serving JavaScript, not HTML?
- [ ] Has the browser service worker updated?

### Deploy Commands Reference
```
git add <specific files> ; git commit -m "message" ; git push
```
- **Frontend (Cloudflare Pages):** Auto-deploys on git push to main
- **Backend (Render):** Manual deploy command or auto-deploy
- **CDN Cache Purge:** Cloudflare Dashboard → Caching → Purge Everything (only helps if deployment succeeded)

---

## 📚 REFERENCE DOCUMENTS

When troubleshooting, refer to:

1. **ROUTE_MAPPING.md** - Which route is in which blueprint?
2. **MIGRATION_GUIDE.md** - How blueprints work, what changed
3. **journal.txt** - Previous session notes, what worked before
4. **Git history** - What changed recently?

---

## 🎓 LEARNING FROM ERRORS

### After Fixing an Issue, Document It:

**Add to journal.txt:**
```
Session XX: [Problem] - [Solution]
Problem: ImportError on require_auth
Solution: Added decorators to auth.py (lines 946-1000)
Time to fix: 15 minutes
```

**Create issue notes:**
- What broke
- What the error was
- How you fixed it
- How to prevent it next time

---

## 💡 PREVENTION TIPS

### Before Deploying:

1. **Test locally if possible**
   ```powershell
   python wsgi.py
   # Should see: "✅ All blueprints registered successfully!"
   ```

2. **Check syntax:**
   ```powershell
   python -m py_compile wsgi.py
   python -m py_compile routes/auth_routes.py
   # No output = no syntax errors
   ```

3. **Verify imports:**
   ```powershell
   # Make sure imported functions exist
   Select-String -Path auth.py -Pattern "def require_auth"
   ```

4. **Small commits:**
   - Don't change 10 files at once
   - Easier to rollback if needed
   - Easier to find which change broke it

5. **Keep journal.txt updated:**
   - Note what you're deploying
   - Note what works
   - Future you will thank present you

---

## ✅ HEALTH CHECK SCRIPT

Save this as `health-check.ps1`:

```powershell
# CollectionCalc Health Check
# Run this anytime to verify API status

$base_url = "https://collectioncalc-docker.onrender.com"

Write-Host "🏥 CollectionCalc Health Check" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Test 1: Health endpoint
Write-Host "`n1. Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = curl -s "$base_url/health" | ConvertFrom-Json
    Write-Host "   ✅ Status: $($health.status)" -ForegroundColor Green
    Write-Host "   ✅ Version: $($health.version)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Health check failed!" -ForegroundColor Red
    exit 1
}

# Test 2: Auth endpoint
Write-Host "`n2. Testing auth endpoint..." -ForegroundColor Yellow
try {
    $response = curl -s -X POST "$base_url/api/auth/login" `
        -H "Content-Type: application/json" `
        -d '{"email":"test","password":"test"}'
    Write-Host "   ✅ Auth endpoint responding" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Auth endpoint failed!" -ForegroundColor Red
}

# Test 3: Sales endpoint
Write-Host "`n3. Testing sales endpoint..." -ForegroundColor Yellow
try {
    $response = curl -s -X POST "$base_url/api/ebay-sales/batch" `
        -H "Content-Type: application/json" `
        -d '{"sales":[]}'
    Write-Host "   ✅ Sales endpoint responding" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Sales endpoint failed!" -ForegroundColor Red
}

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Health check complete!" -ForegroundColor Cyan
```

**Run it:**
```powershell
.\health-check.ps1
```

---

## 📞 GETTING HELP

If you're stuck:

1. **Check this playbook** - Most issues are here
2. **Check journal.txt** - Have you seen this before?
3. **Check Render logs** - Error is usually very specific
4. **Google the exact error** - Someone's probably seen it
5. **Ask Claude** - Paste the error, ask for help

**When asking for help, include:**
- The full error message from Render logs
- What you were trying to deploy
- What you've already tried
- Recent git commits (`git log -3 --oneline`)

---

**Last updated:** February 23, 2026
**Version:** 1.1 (Added Cloudflare Pages / Frontend Deployment section — Session 61)

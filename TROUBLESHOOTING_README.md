# How to Use the Troubleshooting Playbook

## When Something Goes Wrong:

**1. Start with Quick Triage** (top of TROUBLESHOOTING.md)
   - Is server responding? Test /health endpoint
   - This tells you if it's a server crash vs. route-specific issue

**2. Match Your Symptoms to a Section:**
   - 🔴 Server won't start → "SERVER WON'T START" section
   - 🟡 Server up but routes fail → "SERVER STARTS BUT ROUTES FAIL"
   - 🟢 Extensions not working → "CHROME EXTENSION ISSUES"

**3. Follow the Flowchart in That Section**
   - Each section has step-by-step instructions
   - Copy/paste the PowerShell commands
   - Most fixes take < 5 minutes

**4. If Stuck, Check "Common Fixes Cheat Sheet"**
   - Force reload
   - Clear cache
   - Emergency rollback

## Most Common Issues:

**After deploying blueprints:**
1. ImportError → Check "cannot import name 'X' from 'Y'" section
2. Worker failed to boot → Check "Worker Failed to Boot" section
3. Extensions failing → Check "CHROME EXTENSION ISSUES" section

## Emergency "Just Make It Work" Command:

```powershell
# Instant rollback to last working version
git revert HEAD
git push
deploy
```

## Keep This Updated:

After fixing a new issue:
1. Add it to TROUBLESHOOTING.md
2. Note it in journal.txt
3. Future you will thank present you!

---

**The playbook is your friend - use it every time something breaks!**

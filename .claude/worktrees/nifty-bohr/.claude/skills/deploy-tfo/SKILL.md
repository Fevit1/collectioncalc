---
name: deploy-tfo
description: Deploy TheFormOf backend to Render
disable-model-invocation: true
---

Deploy the TFO backend to Render:

1. Run `git status` to check for uncommitted changes
2. If there are changes, ask the user if they want to commit first
3. Push the current branch to the remote: `git push`
4. Render auto-deploys from the pushed branch — confirm which branch is configured
5. After push, hit the health endpoint to verify deployment:
   - `curl https://collectioncalc-docker.onrender.com/health`
   - Verify response contains `"status": "ok"`
   - Report the version number returned
6. If health check fails, check Render logs for errors

# NPM Registry Fix

This build removes OpenAI internal npm registry URLs from `frontend/package-lock.json` and adds `frontend/.npmrc` so Render/Railway installs packages from the public npm registry.

If deployment fails at `npm ci`, confirm that no lockfile entry contains `packages.applied-caas` or `artifactory`:

```bat
findstr /S /I "applied-caas artifactory" frontend\package-lock.json frontend\.npmrc Dockerfile
```

There should be no matches except this README.

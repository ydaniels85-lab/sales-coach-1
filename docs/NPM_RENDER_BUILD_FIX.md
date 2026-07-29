# Render npm build fix

## Cause

The previous `frontend/package-lock.json` was generated in a private build environment and contained 120 `resolved` package URLs pointing to an internal OpenAI Artifactory host. Render cannot reach that host. npm retried until its own process ended with:

`npm error Exit handler never called!`

## Changes

- All `resolved` URLs now use `https://registry.npmjs.org/`.
- Frontend image changed from floating `node:22-alpine` to stable `node:20-bookworm-slim`.
- Top-level package versions are pinned.
- The Dockerfile `ENV` values force the public npm registry and disable audit/fund/update checks during the build. No `.npmrc` file is required.
- Docker dependency installation retries up to three times for transient network failures.
- Dependency files are copied before source files so Render can cache the npm layer.

## Render redeploy

Push this full package to the repository and choose **Manual Deploy > Clear build cache & deploy** for the first corrected deployment. Clearing the cache is important because the failed dependency layer may still be cached.

# Docker build fix: missing `frontend/.npmrc`

## Error

`failed to calculate checksum ... "/frontend/.npmrc": not found`

## Cause

The previous Dockerfile copied `frontend/.npmrc` as a required source file. Hidden files can be omitted when copying or committing a project, so Docker could not calculate the build-layer checksum.

## Correction

The Dockerfile now copies only:

```dockerfile
COPY frontend/package.json frontend/package-lock.json ./
```

The public npm registry, retries, audit, fund, and update-notifier settings remain configured through Docker `ENV` values. The `.npmrc` file has been removed from this package entirely because the Docker build does not need it.

## Render action

Replace the repository contents with this package, commit and push, then choose **Manual Deploy > Clear build cache & deploy**.

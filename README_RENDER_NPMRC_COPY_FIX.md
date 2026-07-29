# Render fix: frontend/.npmrc missing during Docker build

This build removes the Dockerfile dependency on `frontend/.npmrc` so Render cannot fail with:

```text
failed to calculate checksum ... "/frontend/.npmrc": not found
```

The Dockerfile now sets the npm registry directly inside the Docker build step and installs from the public npm registry without using `package-lock.json`.

Deploy steps:

```bat
git add .
git commit -m "Fix Render npmrc copy error"
git push
```

Then in Render:

```text
Manual Deploy → Clear build cache & deploy
```

Confirm the build log shows:

```text
RUN npm config set registry https://registry.npmjs.org/
```

It must not show:

```text
COPY frontend/.npmrc /app/frontend/.npmrc
```

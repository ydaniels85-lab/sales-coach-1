# Fin-Tastic Sales Coach - CORS/Admin Workflow Status Fix

This build fixes the browser error:

`Access to fetch at http://localhost:5000/api/clients/<client_id>/admin-workflow/status from origin http://localhost:5173 has been blocked by CORS policy`

## What changed

- Added a hard backend CORS fallback for every response, including errors and preflight requests.
- Added global OPTIONS handling so PATCH/PUT/DELETE requests from the React frontend do not fail preflight.
- Added a read-only `GET /api/clients/<client_id>/admin-workflow/status` endpoint.
- Kept `PATCH /api/clients/<client_id>/admin-workflow/status` restricted to Admin/Manager users.
- Added JSON error handling so real backend errors show in the UI/dev console instead of being hidden as vague CORS errors.

## Run

```bat
START_ALL.bat
```

## Important

After replacing the files, fully stop both backend and frontend before restarting.

```bat
taskkill /F /IM python.exe
taskkill /F /IM node.exe
START_ALL.bat
```


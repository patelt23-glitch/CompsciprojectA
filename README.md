# Visuospatial Assessment frontend

A separate Django frontend based on the supplied six-page visuospatial wireframe PDF. The original djangostarter project is not modified.

## Run in VS Code

Open this folder, then run in the terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py runserver 8001
```

Open http://127.0.0.1:8001/.

## Included

- Responsive home, about, information and test giver login preview.
- Demo dashboard with preview-link creation and clipboard copying.
- Instructions, practice, five-second study, matching and completion screens.
- Six shuffled cards with three matching pairs per round. Assessment includes directional arrows.
- Actual session metrics, results view and CSV export.
- Keyboard controls, visible focus indicators, live feedback and mobile layouts.

## Backend boundary

Django only serves one HTML template and local static assets. There is no database, migration, authentication or existing-backend change. Demo access is an interface preview, not an authorization boundary. Results are held in JavaScript memory and lost on refresh; no patient details or passwords are collected. Links open the local instructions route and are not secure invitations. Completing a test does not submit data to a server.

To preview results: enter the demo dashboard, open a patient test, finish practice and the assessment, then return through Login to the demo dashboard in the same tab. Select View to see real session metrics or export CSV.

For integration, replace the demo login with server authentication, generate validated expiring invitations on the server, persist attempts through an authenticated API, and authorize all result access server-side. Keep template and static files when integrating into an existing Django app.

## Files

- `templates/index.html`: page shell.
- `static/app.css`: wireframe-inspired styling and responsive layout.
- `static/app.js`: navigation, matching logic and demo interactions.
- `config/`: minimal Django preview configuration.

Metrics: correct matches counts completed pairs; mistakes counts mismatched attempts; accuracy is correct matches / all pair attempts; average time is the mean pair-selection time, excluding the study phase, mismatch reset delay and completion delay.

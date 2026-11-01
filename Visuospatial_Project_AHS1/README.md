# Visuospatial Card Matching — Anjal Project with Patient Backend

**Educational prototype only:** This is a visuospatial card-matching task inspired by spatial-orientation concepts; it is not a JOLO reproduction or a validated diagnostic assessment. Reaction times are measured in the browser and may vary with hardware and human interaction. Standard difficulty presets are project-defined, not clinically normed equivalents. Custom difficulty settings are marked nonstandard.

## Run locally (Windows / VS Code)

1. Extract this ZIP, open its extracted folder in VS Code.
2. Install **Python 3.12 or later** from python.org if needed; select **Add Python to PATH**.
3. Open VS Code Terminal in the folder containing `manage.py`, and run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test assessment
.\.venv\Scripts\python.exe manage.py runserver 8000
```

Alternatively, double-click **RUN_WINDOWS.bat** (Windows; requires Python on PATH). For Mac/Linux use `bash run_mac_linux.sh`.

Then open **http://127.0.0.1:8000/** in a browser. Do not open HTML files directly: Django must be running. A new local `db.sqlite3` file is generated; no old patient database is bundled.

## Test the complete workflow

1. At `/signup/` create a test-giver account; log in and open `/dashboard/`.
2. Choose **Standard** or **Advanced** and, if desired, card counts per scored round (4–12, even, nondecreasing), a shape group, and study duration. The standardized defaults are **Standard: practice 4 / scored 6,8,10** and **Advanced: practice 4 / scored 6,8,12**.
3. Click **Generate Patient Link**. Copy the **secure invitation code** or patient URL. Do not confuse the secure invitation code with a participant ID such as P001.
4. For **anonymous testing**, open the test URL directly in a private browser window. Patients are not required to register.
5. For **registered patients**, visit `/patient-register/`, create an account, then enter the secure invitation code at `/patient-dashboard/`. It links that invitation to the signed-in patient. After a claim, the test URL is accessible only from that patient account.
6. Complete the practice and three scored rounds. The patient sees a simple confirmation; detailed scores remain with the clinician.
7. Return to the clinician dashboard. Open the completed assessment to see database-backed scores, per-level metrics, response trend, and CSV export.

The clinician's local URL works only on their computer unless the Django server is deployed. Sharing `127.0.0.1` with a remote patient **will not work**.

## Endpoints added

| Route | Methods | Purpose |
|---|---|---|
| `/patient-register/` | GET/POST | Optional patient account creation |
| `/patient-login/` | GET/POST | Patient login |
| `/patient-logout/` | POST | Patient logout, CSRF-protected |
| `/patient-dashboard/` | GET/POST | Claim secure invitation code and view patient history |

Existing clinician endpoints are unchanged, including `/api/sessions/` (accepts `card_counts`, `shape_types`, `study_time_ms`), `/patient/<token>/`, `/api/sessions/<uuid>/attempts/`, `/api/sessions/<uuid>/complete/`, and clinician-owned results and exports.

Sample customized session JSON (authenticated clinician, CSRF token required):

```json
{
  "difficulty": "Advanced",
  "card_counts": [6, 8, 12],
  "shape_types": ["arrow", "triangle", "l_shape"],
  "study_time_ms": [5000, 4000, 3000],
  "participant_id": "P001"
}
```

**Important:** Settings are frozen per invitation when created; they cannot be modified during a test. Standard presets choose the same card types but shuffle their positions. Matches require the same shape, orientation and mirrored state. Practice attempts are excluded from aggregate scored accuracy. Response times are stored in milliseconds. Export includes summarized rows and individual recorded selections.

## Changes and scope

- `assessment/difficulty.py`: settings validation, shape/orientation/reflection stimuli, default round specs.
- `assessment/models.py`, `assessment/migrations/0003_patient_difficulty_settings.py`: patient accounts, invitation claim ownership, saved difficulty configuration, secure invitation code.
- `assessment/views.py`, `assessment/urls.py`: patient authentication, invitation claiming, assessment/result access controls, variable-deck generation and scoring, deduplicating retries, actual results chart inputs and raw per-response CSV export.
- `templates/patient_*.html`: minimal patient account pages and dashboard.
- `templates/dashboard.html`, `static/js/dashboard.js`: doctor controls and invitation code display.
- `static/js/assessment_engine.js`: arrow and L-shape rendering, mirrored variants, patient-only completion confirmation.
- `templates/results.html`, `static/js/results_charts.js`: remove hard-coded example test scores and use real recorded data instead.
- `assessment/test_patient_difficulty.py`: integration tests for patient accounts, session generation, access restrictions and anonymous links. Existing test suite preserved and updated for the four-stage round structure.

## Privacy, limitations and deployment

This is a student prototype. Avoid entering real patient identities, real diagnoses or medical records in a demo. Invitations are bearer secrets, expire in seven days, and allow one completion. Registered patients see only assessments claimed by their own account; detailed results and CSV are available only to the clinician who generated each invitation. Passwords are hashed by Django. The clinician UI no longer requests a date of birth by default.

For internet deployment: configure a unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, correct `DJANGO_ALLOWED_HOSTS`, HTTPS, CSRF origins, persistent database, static files, backups, clinician registration approval, throttling/rate limiting, and password recovery email. The original included Vercel config uses temporary SQLite when no external `DATABASE_URL` is set, which is **not** a persistent clinical database. Do not deploy personal health data to it.

**Verification in the artifact-building environment:** Python module compilation, JavaScript syntax checks and standalone deterministic/deck invariants completed successfully. Full Django integration tests could not be run here because Django dependencies are not installed and this environment could not access package downloads. Run `manage.py migrate` and `manage.py test assessment` locally and report any failures. The package is integration-ready source, **not a claim of successful live deployment**.

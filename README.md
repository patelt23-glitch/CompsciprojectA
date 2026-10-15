# Visuospatial Assessment

Django application with a card-matching assessment, test-giver accounts, participant invitations, saved results and CSV export.

## Run locally in VS Code

Open this folder and run these commands in the terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 8011
```

Open http://127.0.0.1:8011/. The SQLite database is created at `db.sqlite3` and excluded from Git. Back it up to preserve local records.

## Use the application

1. Select **Clinician login**, then **Create account**. Registration creates a Django user with a hashed password and signs you in. Existing accounts sign in with their email and password.
2. In the dashboard, enter a participant ID such as `P001` and select **Generate Link**. IDs accept letters, numbers, hyphens and underscores. No participant names or dates of birth are required. Reusing an ID under your account attaches another invitation to the same participant.
3. Copy the generated invitation or open it in another tab. Invitations expire seven days after creation and accept one completed assessment. Opening a link alone does not consume it. Only English without audio is implemented; unsupported language and voice choices are no longer offered.
4. Participants complete practice and the assessment without needing an account. The server creates an attempt and shuffled assessment deck, validates submitted card selections, computes scores, and saves results. A failed save displays a retry button; keep the completion page open until saving succeeds. Retrying a successful submission does not create duplicate results.
5. Return to the dashboard to load saved results. Select **View**, then **Export CSV**, or use **Export all results CSV**. Test givers can access and export only records belonging to their own invitations, including when URLs are requested directly.
6. **Profile** saves your name, organization and email. Changing email also changes the email used to sign in. **Sign out** ends the server session. Without **Remember me**, the session expires when the browser closes; with it, the session lasts two weeks.

The home-page test and **Preview Patient Test** run without an invitation and do not save results. Browser-measured response times are validated for type and range; they are not independently verified timing measurements. Accuracy is completed pairs divided by pair selections, and average time excludes study and mismatch reset delays.

Local links using `127.0.0.1` work on the computer running Django. Remote participants require a hosted application and an appropriate public hostname.

## Database

- Django `User`: login, email, name and password hash.
- `TestGiverProfile`: organization linked to a user.
- `Participant`: participant identifier scoped to its test giver.
- `Invitation`: unique random token, participant, settings, expiry and completion time.
- `AssessmentAttempt`: server-generated deck and start/completion times; one per invitation.
- `AssessmentResult`: raw pair selections and server-calculated matches, mistakes, accuracy and average time; one per attempt.

Migrations are included in `assessments/migrations/`. Run `manage.py migrate` after pulling changes.

## Backend routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/dashboard/` | GET | Authenticated dashboard shell |
| `/api/session/` | GET | Current user and CSRF cookie |
| `/api/signup/` | POST | Create a test-giver account |
| `/api/login/` | POST | Django session login |
| `/api/logout/` | POST | Authenticated logout |
| `/api/profile/` | POST | Update your profile |
| `/api/dashboard/` | GET | Your invitations and results |
| `/api/invitations/` | POST | Create your participant's invitation |
| `/api/invitations/<token>/start/` | POST | Start/resume an unexpired invitation |
| `/api/invitations/<token>/complete/` | POST | Validate and save selections |
| `/api/results/export/` | GET | Export your saved results |
| `/api/results/<id>/export/` | GET | Export one of your saved results |

POST routes accept JSON and require the CSRF cookie value in `X-CSRFToken`. Invitation tokens grant access only to their assessment submission, not the dashboard or results. Sensitive responses use `Cache-Control: no-store`. A no-referrer policy avoids leaking invitation URLs through referrers.

## Deployment configuration

Defaults are for local development. Before hosting, set `DJANGO_SECRET_KEY` to a private random value, `DJANGO_DEBUG=0`, and `DJANGO_ALLOWED_HOSTS` to your hostname. Non-debug mode enables secure session and CSRF cookies, so serve over HTTPS. Configure production static-file serving and database backups. Public registration currently permits anyone to create a test-giver account; add account approval and login rate limiting before a public rollout. Password recovery email delivery is not implemented; a local administrator can reset a password with `manage.py changepassword <email>`.

## Main files

- `assessments/models.py`, `views.py`: database, API and access checks.
- `config/`: Django settings and routes.
- `templates/index.html`: page shell.
- `static/state.js`: shared state and CSRF-aware API requests.
- `static/views.js`: accounts, dashboard, invitations, completion and results.
- `static/game.js`: practice and assessment interactions.
- `static/app.css`: responsive page styling.

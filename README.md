# Visuospatial Assessment System
### Computer Science Senior Project - Final Clinical Backend & Assessment Platform

[![Django](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
[![Design](https://img.shields.io/badge/Design-Apple%20Fluid%20UI-indigo.svg)](https://developer.apple.com/design/)

A clinical-grade visuospatial memory assessment platform built with **Django**, providing persistent patient sessions, sub-millisecond response latency tracking, voice interaction, multilingual translation, account security, and spreadsheet export. Designed according to the specifications in `Visuospatial_Final_Backend_Design.pptx` and styled using fluid Apple Design principles with zero em-dashes and tactile spring feedback.

---

## Key Modules & Features

### 1. Account Security & Clinician Management
- **Self-Service Registration (`/signup/`)**: Clinicians can register accounts with name, healthcare organization, and email.
- **Strict Password Validation**: Enforces minimum 8 characters, common password rejection, and user attribute similarity checks.
- **Session Policies & Remember Me**:
  - Without Remember Me: Session cookie expires when browser closes (`expiry=0`).
  - With Remember Me: Session cookie is maintained for 14 days (`SESSION_COOKIE_AGE=1209600`).
- **Profile Management (`/profile/`)**: Clinicians can view and update their name, organization, email address, and preferred interface language.
- **Cross-Clinician Access Isolation**: Strict ownership checks prevent any clinician from viewing, exporting, or modifying sessions or results belonging to other clinicians.
- **Security Headers**: Configured with `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, `SECURE_REFERRER_POLICY='no-referrer'`, and `DEBUG` toggles via environment variables.

### 2. Password Recovery (Forgot Password & OTP)
- **Recovery Request (`/forgot-password/`)**: Clinicians enter their email address to generate a cryptographically random reset token and a 6-digit verification OTP valid for 15 minutes.
- **Confirmation Page (`/reset-password/`)**:
  - Direct token link access (`/reset-password/<token>/`).
  - Form access entering registered email plus the 6-digit OTP code.
- **Instant Testing Support**: In local development and testing environments, the generated OTP code and direct reset link are displayed right on screen and sent to the console.

### 3. Multilingual Support (Text-Language Persistence)
- **Supported Languages**: English, Spanish (Español), French (Français), and German (Deutsch).
- **Comprehensive Translation Dictionary (`translations.js`)**: All instructions, study countdowns, matching cues, status announcements, card labels, and completion screens are fully translated.
- **Persistence**: Selected language is persisted on the `AssessmentSession` database record and stored in client settings.

### 4. Voice Functionality (Voice Input & Output)
- **Speech Synthesis (Voice Output)**:
  - Supports **Female**, **Male**, and **No Voice** settings.
  - Automatically identifies and matches browser speech synthesis voices matching the chosen gender and language locale (`es-ES`, `fr-FR`, `de-DE`, `en-US`).
  - Controls: Dedicated **Mute Voice** toggle and **Replay Audio** instruction button.
- **Speech Recognition (Voice Input / Web Speech API)**:
  - Interactive hands-free test participation (`[Voice Control: Listening]`).
  - Allows patients to speak card numbers (e.g. "Card 1", "Card 2", "Uno", "Dos", "Un", "Deux", "Eins", "Zwei") or commands ("Start", "Next", "Repeat", "Mute").
  - Animated glowing pulse indicator when the microphone is actively listening, with graceful fallback on unsupported browsers.

### 5. Clinical Assessment Engine & Authoritative Deck Verification
- **Server-Generated Authoritative Decks**: Shuffled card layouts are generated and stored on `AssessmentRound.deck_layout`. The server independently validates whether card selections match, completely preventing client-side spoofing.
- **Practice Round Separation**: Round 1 is designated as Practice (`is_practice=True`, "Practice: Not scored"). Any mistakes during practice are recorded for audit in `practice_summary` but **strictly excluded** from clinical accuracy and mistake counts.
- **Difficulty Configurations**:
  - **Standard**: 3 rounds (Practice 2 pairs / 4 cards, Standard Level 1 with 3 pairs / 6 cards, Standard Level 2 with 4 pairs / 8 cards).
  - **Advanced**: 4 rounds with rotational geometry and faster timers (Practice, Level 1 shapes, Level 2 directions, Level 3 complex matching up to 10 cards).
- **Synchronized Attempt Tracking & Network Retry UI**:
  - Selections are submitted synchronously and queued locally.
  - If a network error occurs during completion, a dedicated Apple-style recovery card appears with a **Retry Submission** button, preserving all answers with zero data loss.
- **Custom Participant ID & 7-Day Expiry**:
  - Clinicians can enter existing participant IDs (e.g. `P001`, `PT-102`) or leave blank to auto-generate `PPST-XXXX`.
  - Invitation links remain valid for 7 days (`INVITATION_DAYS=7`).

### 6. Results Analysis & CSV Export
- **Results Dashboard (`/results/<id>/`)**: Comparative metrics, accuracy bar chart, response time trend line across attempts, attention consistency gauge, and error pattern breakdown.
- **Single & Bulk CSV Streaming**:
  - `/api/results/<id>/export.csv`
  - `/dashboard/export.csv`
  - Columns: `session_id, participant_id, patient_code, completed_at, difficulty, language, voice, correct_matches, mistakes, total_attempts, accuracy_percent, avg_latency_seconds, completion_seconds`.

---

## API Endpoints Reference

| Method | Endpoint | Description | Access Control |
|---|---|---|---|
| `GET` | `/` | Public landing page | Public |
| `GET` / `POST` | `/signup/` | Clinician account registration | Public |
| `GET` / `POST` | `/login/` | Clinician authentication with Remember Me | Public |
| `GET` / `POST` | `/logout/` | Sign out clinician and terminate session | Authenticated |
| `GET` / `POST` | `/profile/` | Clinician profile viewing and editing | Authenticated |
| `GET` / `POST` | `/forgot-password/` | Request password reset token and OTP | Public |
| `GET` / `POST` | `/reset-password/` | Reset password using OTP or direct token link | Token / OTP validation |
| `GET` | `/dashboard/` | Clinician dashboard with metrics and session list | Authenticated |
| `GET` | `/dashboard/export.csv` | Export all clinician results to CSV | Authenticated |
| `POST` | `/api/sessions/` | Generate 7-day patient link with custom ID and difficulty | Authenticated |
| `GET` | `/patient/<token>/` | Patient assessment interface | Valid token required |
| `POST` | `/api/sessions/<id>/attempts/` | Submit attempt with authoritative server match check | Token verified |
| `POST` | `/api/sessions/<id>/complete/` | Idempotent atomic completion excluding practice round | Token verified |
| `GET` | `/results/<id>/` | Comprehensive clinical analysis view | Clinician ownership |
| `GET` | `/api/results/<id>/export.csv` | Download single session CSV | Clinician ownership |

---

## Running Automated Tests

Run the complete 15-test automated test suite:

```bash
python manage.py test assessment
```

Expected output:
```
Creating test database for alias 'default'...
...............
----------------------------------------------------------------------
Ran 15 tests in 15.742s

OK
Destroying test database for alias 'default'...
Found 15 test(s).
System check identified no issues (0 silenced).
```

---

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/patelt23-glitch/CompsciprojectA.git
cd CompsciprojectA

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Seed database with demo accounts and sample records
python manage.py seed_data

# 5. Start development server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

Pre-configured Demo Accounts:
- **Clinician Login**: `clinician` / `assessment2025` (or `sarah.chen@clinic.org` / `StrongPassword2026!`)
- **Patient Test Link**: `/patient/sample-patient-token-2025/`

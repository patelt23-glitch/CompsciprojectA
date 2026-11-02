# Visuospatial Assessment System
### Computer Science Senior Project - Final Clinical Backend & Assessment Platform

[![Django](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
[![Tests](https://img.shields.io/badge/Tests-22%20Passed-success.svg)](https://github.com/Singhtanuj387/assessment)
[![Design](https://img.shields.io/badge/Design-Apple%20Fluid%20UI-indigo.svg)](https://developer.apple.com/design/)

A clinical-grade visuospatial memory assessment platform built with **Django**, providing persistent patient sessions, sub-millisecond response latency tracking, voice interaction, multilingual translation, account security, link lifecycle management, PDF clinical reports, patient assessment history, and spreadsheet export. Designed according to the specifications in `Visuospatial_Final_Backend_Design.pptx` and styled using fluid Apple Design principles with zero em-dashes and tactile spring feedback.

---

## Key Modules & Features

### 1. Assessment Link Management
- **Link Status Tracking**: Real-time lifecycle states (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `EXPIRED`, `CANCELED`).
- **Automatic Expiration Handling**: Links enforce an expiration date (7-day window by default) and automatically mark overdue sessions as `EXPIRED`.
- **Link Cancellation**: Clinicians can cancel pending or unstarted assessment links directly from the dashboard to revoke patient access immediately.
- **Link Regeneration**: Clinicians can regenerate expired or canceled links with a fresh cryptographic token and a new 7-day expiration date without re-entering patient configuration or creating duplicate sessions.

### 2. Doctor Dashboard Search and Filters
- **Real-Time Patient Search**: Instant lookup by Patient Code or Participant ID using database queries.
- **Multi-Parameter Filtering**:
  - Filter by **Completion Status** (`ALL`, `PENDING`, `IN_PROGRESS`, `COMPLETED`, `EXPIRED`, `CANCELED`).
  - Filter by **Difficulty Level** (`ALL`, `Standard`, `Advanced`).
  - Filter by **Time Period** (`Today`, `Past 7 Days`, `Past Month / 30 Days`, `Past 90 Days`, `All Time`).
- **Asynchronous Data API**: Dedicated `/api/dashboard/sessions/` endpoint for fast JSON queries and dynamic table updates.

### 3. PDF Assessment Report Generator
- **Clinical-Grade PDF Engine**: Downloadable medical report (`/results/<id>/report.pdf`) generated dynamically using ReportLab.
- **Authoritative Metrics Included**:
  - Patient ID, date of birth, age bracket, and assessment timestamp.
  - Difficulty level, language, and audio guidance settings.
  - Total correct matches, total attempts, mistake count, error rate, and overall accuracy percentage.
  - Average, fastest, and slowest response latencies (in seconds).
  - Round-by-round performance breakdown table (pairs, cards, correct, mistakes, accuracy, and average latency).
  - Visual stimulus error distribution breakdown for pattern analysis.
  - Clinician diagnostic observations and medical data confidentiality disclaimer.

### 4. Patient Assessment History & Dedicated Portal
- **Patient Authentication (`/patient/login/`, `/patient/signup/`)**: Separate, isolated authentication system for patients with secure credentials and profile management.
- **Automatic Assessment Association**: Automatically links existing tests to patient accounts matching their assigned patient code.
- **Assessment History Dashboard (`/patient/history/`)**: Dedicated patient page showing longitudinal progress: total tests taken, average accuracy, personal best accuracy, and average response latency.
- **Individual Test Performance Detail (`/patient/history/<id>/`)**: Deep dive view into completed tests showing round breakdowns, correct matches, mistakes, and latencies.
- **Strict Privacy Isolation**: Patients can strictly access only their own assessments; unauthorized cross-patient requests are blocked with HTTP 403.

### 5. Improved Results Dashboard & Interactive Visualizations
- **Authoritative Database Data**: Replaces all hardcoded or mock numbers with real data calculated from `ResponseEvent` and `AssessmentRound` database records.
- **Level Comparison Bar Chart**: Interactive toggling between **Accuracy (%)** and **Average Response Time (s)** per round.
- **Response Time Trend Line**: Attempt-by-attempt latency sequence chart distinguishing correct responses from mistakes.
- **Attention Consistency Gauge**: Measures response time variance ($\pm\text{seconds}$) to evaluate sustained patient attention.
- **Working Memory Stamina**: Tracks performance changes from initial to advanced levels.
- **Stimulus Mistake Patterns**: Visual breakdown of the most frequently missed shapes and directional attributes.
- **In-Place Notes Editor**: Clinicians can edit and save diagnostic notes asynchronously via AJAX.

### 6. Account Security & Clinician Management
- **Self-Service Registration (`/signup/`)**: Clinicians can register accounts with name, healthcare organization, and email.
- **Strict Password Validation**: Enforces minimum 8 characters, common password rejection, and user attribute similarity checks.
- **Session Policies & Remember Me**:
  - Without Remember Me: Session cookie expires when browser closes (`expiry=0`).
  - With Remember Me: Session cookie is maintained for 14 days (`SESSION_COOKIE_AGE=1209600`).
- **Profile Management (`/profile/`)**: Clinicians can view and update their name, organization, email address, and preferred interface language.
- **Cross-Clinician Access Isolation**: Strict ownership checks prevent any clinician from viewing, exporting, or modifying sessions or results belonging to other clinicians.
- **Security Headers**: Configured with `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SECURE_CONTENT_TYPE_NOSNIFF=True`, and origin verification middleware.

### 7. Password Recovery (Forgot Password & OTP)
- **Recovery Request (`/forgot-password/`)**: Clinicians enter their email address to generate a cryptographically random reset token and a 6-digit verification OTP valid for 15 minutes.
- **Confirmation Page (`/reset-password/`)**:
  - Direct token link access (`/reset-password/<token>/`).
  - Form access entering registered email plus the 6-digit OTP code.
- **Instant Testing Support**: In local development and testing environments, the generated OTP code and direct reset link are displayed right on screen and sent to the console.

### 8. Multilingual Support (Text-Language Persistence)
- **Supported Languages**: English, Spanish (Español), French (Français), and German (Deutsch).
- **Comprehensive Translation Dictionary (`translations.js`)**: All instructions, study countdowns, matching cues, status announcements, card labels, and completion screens are fully translated.
- **Persistence**: Selected language is persisted on the `AssessmentSession` database record and stored in client settings.

### 9. Voice Functionality (Voice Input & Output)
- **Speech Synthesis (Voice Output)**:
  - Supports **Female**, **Male**, and **No Voice** settings.
  - Automatically identifies and matches browser speech synthesis voices matching the chosen gender and language locale (`es-ES`, `fr-FR`, `de-DE`, `en-US`).
  - Controls: Dedicated **Mute Voice** toggle and **Replay Audio** instruction button.
- **Speech Recognition (Voice Input / Web Speech API)**:
  - Interactive hands-free test participation (`[Voice Control: Listening]`).
  - Allows patients to speak card numbers (e.g. "Card 1", "Card 2", "Uno", "Dos", "Un", "Deux", "Eins", "Zwei") or commands ("Start", "Next", "Repeat", "Mute").
  - Animated glowing pulse indicator when the microphone is actively listening, with graceful fallback on unsupported browsers.

### 10. Clinical Assessment Engine & Authoritative Deck Verification
- **Server-Generated Authoritative Decks**: Shuffled card layouts are generated and stored on `AssessmentRound.deck_layout`. The server independently validates whether card selections match, completely preventing client-side spoofing.
- **Practice Round Separation**: Round 1 is designated as Practice (`is_practice=True`, "Practice: Not scored"). Any mistakes during practice are recorded for audit in `practice_summary` but **strictly excluded** from clinical accuracy and mistake counts.
- **Difficulty Configurations**:
  - **Standard**: 3 rounds (Practice 2 pairs / 4 cards, Standard Level 1 with 3 pairs / 6 cards, Standard Level 2 with 4 pairs / 8 cards).
  - **Advanced**: 4 rounds with rotational geometry and faster timers (Practice, Level 1 shapes, Level 2 directions, Level 3 complex matching up to 10 cards).
- **Synchronized Attempt Tracking & Network Retry UI**:
  - Selections are submitted synchronously and queued locally.
  - If a network error occurs during completion, a dedicated Apple-style recovery card appears with a **Retry Submission** button, preserving all answers with zero data loss.

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
| `GET` | `/dashboard/` | Clinician dashboard with search, filters, and link management | Authenticated |
| `GET` | `/dashboard/export.csv` | Export all clinician results to CSV | Authenticated |
| `GET` | `/api/dashboard/sessions/` | Filtered assessment sessions JSON API | Authenticated |
| `POST` | `/api/sessions/` | Generate 7-day patient link with custom ID and difficulty | Authenticated |
| `POST` | `/api/sessions/<id>/cancel/` | Cancel pending or unstarted assessment link | Clinician ownership |
| `POST` | `/api/sessions/<id>/regenerate/` | Regenerate link with fresh 7-day token | Clinician ownership |
| `GET` | `/patient/<token>/` | Patient assessment interface | Valid token required |
| `POST` | `/api/sessions/<id>/attempts/` | Submit attempt with authoritative server match check | Token verified |
| `POST` | `/api/sessions/<id>/complete/` | Idempotent atomic completion excluding practice round | Token verified |
| `GET` | `/results/<id>/` | Comprehensive clinical analysis view with interactive charts | Clinician ownership |
| `GET` | `/results/<id>/report.pdf` | Download clinical assessment PDF report | Clinician ownership |
| `GET` | `/api/results/<id>/export.csv` | Download single session CSV | Clinician ownership |
| `POST` | `/api/results/<id>/notes/` | Save clinician diagnostic notes via AJAX | Clinician ownership |
| `GET` / `POST` | `/patient/signup/` | Patient account registration | Public |
| `GET` / `POST` | `/patient/login/` | Patient authentication | Public |
| `GET` / `POST` | `/patient/logout/` | Patient sign out | Authenticated |
| `GET` | `/patient/history/` | Patient assessment history list & progress metrics | Patient only |
| `GET` | `/patient/history/<id>/` | Patient detailed view of completed test | Patient ownership |

---

## Running Automated Tests

Run the complete 22-test automated test suite:

```bash
python manage.py test assessment
```

Expected output:
```
Creating test database for alias 'default'...
......................
----------------------------------------------------------------------
Ran 22 tests in 16.424s

OK
Destroying test database for alias 'default'...
Found 22 test(s).
System check identified no issues (0 silenced).
```

---

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Singhtanuj387/assessment.git
cd assessment

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
- **Patient Portal**: `/patient/login/` with any registered patient account

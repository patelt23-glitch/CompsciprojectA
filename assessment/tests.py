import json
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from assessment.models import (
    ClinicianProfile,
    PasswordResetToken,
    AssessmentSession,
    AssessmentRound,
    ResponseEvent,
    AssessmentResult,
    calculate_age_bracket,
)


class VisuospatialComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create primary clinician user
        self.user = User.objects.create_user(
            username="dr_sarah",
            email="sarah.chen@clinic.org",
            password="StrongPassword2026!",
            first_name="Dr. Sarah Chen",
        )
        self.profile = ClinicianProfile.objects.create(
            user=self.user,
            display_name="Dr. Sarah Chen",
            organization="Memory & Cognitive Health Institute",
            preferred_language="English",
        )

        # Create secondary clinician user for cross-account isolation testing
        self.other_user = User.objects.create_user(
            username="dr_bob",
            email="bob.smith@hospital.org",
            password="StrongPassword2026!",
            first_name="Dr. Bob Smith",
        )
        self.other_profile = ClinicianProfile.objects.create(
            user=self.other_user,
            display_name="Dr. Bob Smith",
            organization="Private Neurological Center",
            preferred_language="English",
        )

    # ==========================================================================
    # 1. Clinician Registration & Password Rules
    # ==========================================================================

    def test_signup_validation_weak_password_rejected(self):
        """Verify that weak passwords are rejected per Django password rules."""
        res = self.client.post('/signup/', {
            'name': 'Dr. New User',
            'organization': 'City Clinic',
            'email': 'new.doctor@clinic.org',
            'password': 'short', # Less than 8 chars
            'confirm_password': 'short',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'at least 8 characters')
        self.assertFalse(User.objects.filter(email='new.doctor@clinic.org').exists())

    def test_signup_password_mismatch_rejected(self):
        """Verify mismatched password confirmation is rejected."""
        res = self.client.post('/signup/', {
            'name': 'Dr. New User',
            'organization': 'City Clinic',
            'email': 'new.doctor@clinic.org',
            'password': 'StrongPassword123!',
            'confirm_password': 'DifferentPassword123!',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Passwords do not match')

    def test_signup_successful_creation_and_auto_login(self):
        """Verify successful registration creates User, ClinicianProfile, and starts session."""
        res = self.client.post('/signup/', {
            'name': 'Dr. Alex Rivera',
            'organization': 'Neuro Health Center',
            'email': 'alex.rivera@neuro.org',
            'password': 'ValidPassword2026!',
            'confirm_password': 'ValidPassword2026!',
        })
        self.assertRedirects(res, '/dashboard/')

        new_user = User.objects.filter(email='alex.rivera@neuro.org').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.first_name, 'Dr. Alex Rivera')
        self.assertTrue(hasattr(new_user, 'profile'))
        self.assertEqual(new_user.profile.organization, 'Neuro Health Center')

    # ==========================================================================
    # 2. Clinician Session Handling & Remember Me
    # ==========================================================================

    def test_login_session_expiry_with_and_without_remember(self):
        """Verify session handling: 14 days when remembered, 0 (browser close) when not."""
        # Login without remember
        self.client.post('/login/', {
            'username': 'sarah.chen@clinic.org',
            'password': 'StrongPassword2026!',
        })
        self.assertTrue(self.client.session.get_expire_at_browser_close())

        self.client.logout()

        # Login with remember
        self.client.post('/login/', {
            'username': 'sarah.chen@clinic.org',
            'password': 'StrongPassword2026!',
            'remember': 'on',
        })
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertGreater(self.client.session.get_expiry_age(), 86400)

    def test_profile_update_and_email_sync(self):
        """Verify clinician can update profile and changing email updates sign-in email."""
        self.client.login(username='dr_sarah', password='StrongPassword2026!')

        res = self.client.post('/profile/', {
            'name': 'Dr. Sarah Chen, PhD',
            'organization': 'Advanced Brain Institute',
            'email': 'sarah.updated@clinic.org',
            'preferred_language': 'Spanish',
        })
        self.assertEqual(res.status_code, 200)

        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.display_name, 'Dr. Sarah Chen, PhD')
        self.assertEqual(self.profile.organization, 'Advanced Brain Institute')
        self.assertEqual(self.user.email, 'sarah.updated@clinic.org')
        self.assertEqual(self.profile.preferred_language, 'Spanish')

    # ==========================================================================
    # 3. Password Recovery: Forgot Password & Reset
    # ==========================================================================

    def test_forgot_password_generates_token_and_otp(self):
        """Verify forgot password request creates PasswordResetToken with 6-digit OTP."""
        res = self.client.post('/forgot-password/', {
            'email': 'sarah.chen@clinic.org',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Verification code generated')

        reset_token = PasswordResetToken.objects.filter(user=self.user, is_used=False).first()
        self.assertIsNotNone(reset_token)
        self.assertEqual(len(reset_token.otp), 6)
        self.assertTrue(reset_token.is_valid())

    def test_reset_password_with_token(self):
        """Verify setting a new password via the reset token link."""
        reset_token = PasswordResetToken.generate_for_user(self.user, expiry_minutes=15)

        # POST new password to reset endpoint
        res = self.client.post(f'/reset-password/{reset_token.token}/', {
            'password': 'BrandNewPassword2026!',
            'confirm_password': 'BrandNewPassword2026!',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Password Updated')

        # Verify old password fails and new password works
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('StrongPassword2026!'))
        self.assertTrue(self.user.check_password('BrandNewPassword2026!'))

        # Token must be consumed
        reset_token.refresh_from_db()
        self.assertTrue(reset_token.is_used)
        self.assertFalse(reset_token.is_valid())

    def test_reset_password_with_otp_and_email(self):
        """Verify resetting password via email and 6-digit OTP."""
        reset_token = PasswordResetToken.generate_for_user(self.user, expiry_minutes=15)

        res = self.client.post('/reset-password/', {
            'email': 'sarah.chen@clinic.org',
            'otp': reset_token.otp,
            'password': 'OtpResetPassword2026!',
            'confirm_password': 'OtpResetPassword2026!',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Password Updated')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OtpResetPassword2026!'))

    # ==========================================================================
    # 4. Cross-Clinician Isolation & Access Control
    # ==========================================================================

    def test_cross_clinician_access_forbidden(self):
        """Verify that Clinician B cannot view or export Clinician A's assessment results."""
        # Create completed session for Clinician A
        session_a = AssessmentSession.objects.create(
            clinician=self.profile,
            patient_code="PT-ALPHA",
            status="COMPLETED",
            token_hash=AssessmentSession.hash_token("token-alpha"),
            token_raw="token-alpha",
            expires_at=timezone.now() + timedelta(days=7),
        )
        AssessmentResult.objects.create(
            session=session_a,
            completed_pairs=3,
            total_attempts=3,
            mistakes=0,
            accuracy_percent=100.0,
            avg_latency_ms=1800.0,
        )

        # Login as Clinician B
        self.client.login(username='dr_bob', password='StrongPassword2026!')

        # Attempt to view Clinician A's results view
        res = self.client.get(f'/results/{session_a.id}/')
        self.assertEqual(res.status_code, 403)

        # Attempt to export Clinician A's CSV
        csv_res = self.client.get(f'/api/results/{session_a.id}/export.csv')
        self.assertEqual(csv_res.status_code, 403)

        # Clinician B dashboard should not contain Clinician A's patient code
        dash_res = self.client.get('/dashboard/')
        self.assertEqual(dash_res.status_code, 200)
        self.assertNotContains(dash_res, 'PT-ALPHA')

    # ==========================================================================
    # 5. Session Creation: Custom Participant ID, 7-Day Expiry, Difficulty Decks
    # ==========================================================================

    def test_create_session_with_custom_participant_id(self):
        """Verify custom participant ID (e.g. P001) and 7-day expiration."""
        self.client.login(username='dr_sarah', password='StrongPassword2026!')

        payload = {
            'participant_id': 'P001',
            'language': 'Spanish',
            'audio_voice': 'Female',
            'difficulty': 'Standard',
            'dob': '1995-04-12',
        }
        res = self.client.post('/api/sessions/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)

        data = res.json()
        self.assertEqual(data['patient_code'], 'P001')
        self.assertEqual(data['participant_id'], 'P001')

        session = AssessmentSession.objects.get(id=data['session_id'])
        self.assertEqual(session.patient_code, 'P001')
        self.assertEqual(session.language, 'Spanish')

        # Verify 7-day expiration
        expected_expiry_min = timezone.now() + timedelta(days=6, hours=23)
        self.assertGreater(session.expires_at, expected_expiry_min)

    def test_difficulty_settings_round_generation(self):
        """Verify Standard creates 3 rounds and Advanced creates 4 rounds with decks."""
        self.client.login(username='dr_sarah', password='StrongPassword2026!')

        # Standard session
        res_std = self.client.post('/api/sessions/', data=json.dumps({
            'difficulty': 'Standard',
        }), content_type='application/json')
        session_std = AssessmentSession.objects.get(id=res_std.json()['session_id'])
        self.assertEqual(session_std.rounds.count(), 3)
        self.assertTrue(session_std.rounds.get(round_number=1).is_practice)
        self.assertFalse(session_std.rounds.get(round_number=2).is_practice)

        # Advanced session
        res_adv = self.client.post('/api/sessions/', data=json.dumps({
            'difficulty': 'Advanced',
        }), content_type='application/json')
        session_adv = AssessmentSession.objects.get(id=res_adv.json()['session_id'])
        self.assertEqual(session_adv.rounds.count(), 4)
        r4 = session_adv.rounds.get(round_number=4)
        self.assertEqual(r4.pair_count, 5)
        self.assertEqual(r4.card_count, 10)
        self.assertEqual(r4.study_time_ms, 3000)
        self.assertEqual(len(r4.deck_layout), 10)

    # ==========================================================================
    # 6. Patient Link & Security: Mandatory Token Enforcement
    # ==========================================================================

    def test_patient_api_requires_valid_token(self):
        """Verify that attempt and completion APIs reject requests without a valid token."""
        raw_token = "secure-patient-token-xyz"
        session = AssessmentSession.objects.create(
            clinician=self.profile,
            patient_code="PT-SECURE",
            status="IN_PROGRESS",
            token_hash=AssessmentSession.hash_token(raw_token),
            token_raw=raw_token,
            expires_at=timezone.now() + timedelta(days=7),
        )
        AssessmentRound.objects.create(
            session=session, round_number=1, is_practice=False,
            pair_count=3, card_count=6, deck_layout=[]
        )

        # 1. Attempt API without token should return 403
        attempt_no_token = self.client.post(
            f'/api/sessions/{session.id}/attempts/',
            data=json.dumps({'round': 1, 'selected': [0, 1]}),
            content_type='application/json'
        )
        self.assertEqual(attempt_no_token.status_code, 403)

        # 2. Attempt API with invalid token should return 403
        attempt_bad_token = self.client.post(
            f'/api/sessions/{session.id}/attempts/',
            data=json.dumps({'round': 1, 'selected': [0, 1], 'token': 'wrong-token'}),
            content_type='application/json'
        )
        self.assertEqual(attempt_bad_token.status_code, 403)

        # 3. Completion API without token should return 403
        complete_no_token = self.client.post(
            f'/api/sessions/{session.id}/complete/',
            data=json.dumps({'notes': 'Test'}),
            content_type='application/json'
        )
        self.assertEqual(complete_no_token.status_code, 403)

    # ==========================================================================
    # 7. Authoritative Server-Side Card Verification (No Client Spoofing)
    # ==========================================================================

    def test_authoritative_server_score_verification(self):
        """Verify that server independently computes correctness from deck_layout."""
        raw_token = "auth-deck-token"
        session = AssessmentSession.objects.create(
            clinician=self.profile,
            patient_code="PT-DECK",
            status="IN_PROGRESS",
            token_hash=AssessmentSession.hash_token(raw_token),
            token_raw=raw_token,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Authoritative deck: Card 0 and Card 3 match; Card 1 is different
        deck = [
            {'id': 0, 'shape': 'circle', 'match_key': 'circle_pair'},
            {'id': 1, 'shape': 'square', 'match_key': 'square_pair'},
            {'id': 2, 'shape': 'triangle', 'match_key': 'triangle_pair'},
            {'id': 3, 'shape': 'circle', 'match_key': 'circle_pair'},
        ]
        r1 = AssessmentRound.objects.create(
            session=session, round_number=1, is_practice=False,
            pair_count=2, card_count=4, deck_layout=deck
        )

        # Patient picks card 0 and card 3 (Matching pair)
        res_match = self.client.post(
            f'/api/sessions/{session.id}/attempts/',
            data=json.dumps({
                'token': raw_token,
                'round': 1,
                'attempt': 1,
                'selected': [0, 3],
                'response_latency_ms': 1420.0,
            }),
            content_type='application/json'
        )
        self.assertEqual(res_match.status_code, 200)
        self.assertTrue(res_match.json()['is_correct'])

        # Patient picks card 0 and card 1 (Mismatch) but client claims is_correct: True
        res_mismatch = self.client.post(
            f'/api/sessions/{session.id}/attempts/',
            data=json.dumps({
                'token': raw_token,
                'round': 1,
                'attempt': 2,
                'selected': [0, 1],
                'is_correct': True, # Client tries to spoof!
                'response_latency_ms': 1950.0,
            }),
            content_type='application/json'
        )
        self.assertEqual(res_mismatch.status_code, 200)
        # Server MUST correctly mark it as False regardless of client claim
        self.assertFalse(res_mismatch.json()['is_correct'])

    # ==========================================================================
    # 8. Practice Round Exclusion from Clinical Accuracy Score
    # ==========================================================================

    def test_practice_round_excluded_from_clinical_accuracy(self):
        """Verify that Practice Round errors do NOT lower final clinical assessment accuracy."""
        raw_token = "practice-exclusion-token"
        session = AssessmentSession.objects.create(
            clinician=self.profile,
            patient_code="PT-PRACTICE-TEST",
            status="IN_PROGRESS",
            token_hash=AssessmentSession.hash_token(raw_token),
            token_raw=raw_token,
            expires_at=timezone.now() + timedelta(days=7),
        )

        # Round 1: Practice Round (is_practice = True)
        r1_practice = AssessmentRound.objects.create(
            session=session, round_number=1, is_practice=True,
            pair_count=2, card_count=4, deck_layout=[]
        )
        # Patient makes 5 mistakes in the practice round!
        for i in range(5):
            ResponseEvent.objects.create(
                round=r1_practice, attempt_number=i+1, selected_cards=[0, 1],
                target_shape="Practice Error", is_correct=False, response_latency_ms=2500.0
            )

        # Round 2: Clinical Scored Round (is_practice = False)
        r2_scored = AssessmentRound.objects.create(
            session=session, round_number=2, is_practice=False,
            pair_count=3, card_count=6, deck_layout=[]
        )
        # Patient performs with 100% accuracy in the clinical round! (3 correct out of 3)
        for i in range(3):
            ResponseEvent.objects.create(
                round=r2_scored, attempt_number=i+1, selected_cards=[0, 2],
                target_shape="Circle", is_correct=True, response_latency_ms=1800.0
            )

        # Complete assessment
        comp_res = self.client.post(
            f'/api/sessions/{session.id}/complete/',
            data=json.dumps({'token': raw_token}),
            content_type='application/json'
        )
        self.assertEqual(comp_res.status_code, 201)

        result = AssessmentResult.objects.get(session=session)
        # Accuracy MUST be 100% because practice mistakes are excluded!
        self.assertEqual(result.accuracy_percent, 100.0)
        self.assertEqual(result.mistakes, 0)
        self.assertEqual(result.total_attempts, 3)

        # Practice stats preserved in practice_summary
        self.assertIn('practice', result.practice_summary.get('title', '').lower())
        self.assertEqual(result.practice_summary.get('total'), 5)

    # ==========================================================================
    # 9. Idempotency & Retry Protection
    # ==========================================================================

    def test_completion_idempotency_on_network_retry(self):
        """Verify that retrying completion does not create duplicate results or fail."""
        raw_token = "retry-token"
        session = AssessmentSession.objects.create(
            clinician=self.profile,
            patient_code="PT-RETRY",
            status="IN_PROGRESS",
            token_hash=AssessmentSession.hash_token(raw_token),
            token_raw=raw_token,
            expires_at=timezone.now() + timedelta(days=7),
        )
        AssessmentRound.objects.create(
            session=session, round_number=1, is_practice=False,
            pair_count=2, card_count=4, deck_layout=[]
        )

        # First completion
        res1 = self.client.post(
            f'/api/sessions/{session.id}/complete/',
            data=json.dumps({'token': raw_token}),
            content_type='application/json'
        )
        self.assertEqual(res1.status_code, 201)
        self.assertTrue(res1.json()['saved'])

        # Second completion (Network retry)
        res2 = self.client.post(
            f'/api/sessions/{session.id}/complete/',
            data=json.dumps({'token': raw_token}),
            content_type='application/json'
        )
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()['saved'])
        self.assertEqual(res2.json()['status'], 'already_completed')
        self.assertEqual(AssessmentResult.objects.filter(session=session).count(), 1)

    # ==========================================================================
    # 7. CSRF Origin Sanitization
    # ==========================================================================

    def test_null_origin_middleware_sanitization(self):
        """Verify that FixNullOriginMiddleware sanitizes Origin null header."""
        from django.test import RequestFactory
        from assessment.middleware import FixNullOriginMiddleware

        factory = RequestFactory()
        req = factory.post('/login/', HTTP_ORIGIN='null', HTTP_HOST='localhost:8000')
        middleware = FixNullOriginMiddleware(lambda r: r)
        middleware(req)
        self.assertEqual(req.META.get('HTTP_ORIGIN'), 'http://localhost:8000')


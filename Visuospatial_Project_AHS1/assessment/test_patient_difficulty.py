"""Backend integration checks for the assigned patient and difficulty features."""
import json
from collections import Counter
from django.contrib.auth.models import User
from django.test import TestCase
from assessment.difficulty import create_deck, parse_configuration
from assessment.models import ClinicianProfile, PatientProfile, AssessmentSession


class PatientDifficultyTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user('doctor@test.invalid', 'doctor@test.invalid', 'DoctorPass!2026')
        ClinicianProfile.objects.create(user=self.doctor, display_name='Dr Test')
        self.patient = User.objects.create_user('patient@test.invalid', 'patient@test.invalid', 'PatientPass!2026')
        PatientProfile.objects.create(user=self.patient)
        self.other = User.objects.create_user('other@test.invalid', 'other@test.invalid', 'OtherPass!2026')
        PatientProfile.objects.create(user=self.other)

    def test_custom_settings_create_three_scored_rounds(self):
        self.client.force_login(self.doctor)
        res = self.client.post('/api/sessions/', json.dumps({
            'difficulty': 'Advanced', 'card_counts': [4, 8, 12],
            'study_time_ms': [3000, 5000, 7000],
            'shape_types': ['arrow', 'triangle', 'l_shape'],
        }), content_type='application/json')
        self.assertEqual(res.status_code, 201, res.content)
        session = AssessmentSession.objects.get(pk=res.json()['session_id'])
        self.assertEqual([r.card_count for r in session.rounds.all()], [4, 4, 8, 12])
        self.assertEqual([r.study_time_ms for r in session.rounds.all()], [5000, 3000, 5000, 7000])
        for r in session.rounds.all():
            keys = Counter(item['match_key'] for item in r.deck_layout)
            self.assertEqual(len(keys), r.pair_count)
            self.assertEqual(set(keys.values()), {2})
        self.assertFalse(session.difficulty_settings['standardized'])

    def test_registration_login_claim_patient_dashboard_and_ownership(self):
        self.client.force_login(self.doctor)
        created = self.client.post('/api/sessions/', '{}', content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        invite = created.json()
        self.client.logout()
        res = self.client.post('/patient-register/', {
            'email': 'newpatient@test.invalid', 'password': 'FreshPass!2026',
            'confirm_password': 'FreshPass!2026'})
        self.assertRedirects(res, '/patient-dashboard/')
        res = self.client.post('/patient-dashboard/', {'code': invite['invitation_code']})
        self.assertEqual(res.status_code, 302)
        session = AssessmentSession.objects.get(pk=invite['session_id'])
        self.assertEqual(session.patient_user.username, 'newpatient@test.invalid')
        self.assertEqual(self.client.get('/patient-dashboard/').status_code, 200)
        self.client.logout()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/patient/{invite['token']}/").status_code, 403)
        self.assertEqual(self.client.get('/dashboard/').status_code, 403)
        self.assertEqual(self.client.get('/patient-dashboard/').status_code, 200)

    def test_anonymous_invitation_and_no_cross_clinician_results(self):
        self.client.force_login(self.doctor)
        created = self.client.post('/api/sessions/', '{}', content_type='application/json').json()
        self.client.logout()
        self.assertEqual(self.client.get(f"/patient/{created['token']}/").status_code, 200)
        self.assertEqual(self.client.get(f"/results/{created['session_id']}/").status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/api/results/{created['session_id']}/").status_code, 403)

    def test_invalid_controls_rejected(self):
        self.client.force_login(self.doctor)
        res = self.client.post('/api/sessions/', json.dumps({'card_counts': [5, 7, 9]}), content_type='application/json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(AssessmentSession.objects.count(), 0)
        self.assertEqual(len(create_deck(6, 'complex', ['arrow', 'triangle', 'l_shape'])), 12)

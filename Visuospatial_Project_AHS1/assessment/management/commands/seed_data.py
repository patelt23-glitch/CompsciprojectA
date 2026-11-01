import random
import uuid
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from assessment.models import (
    ClinicianProfile,
    AssessmentSession,
    AssessmentRound,
    ResponseEvent,
    AssessmentResult,
)


class Command(BaseCommand):
    help = "Seeds database with clinician user, test sessions, and PPST-4938 results matching senior project design."

    def handle(self, *args, **options):
        # 1. Create or get clinician user
        user, created = User.objects.get_or_create(username="clinician")
        if created:
            user.set_password("assessment2025")
            user.first_name = "Sarah"
            user.last_name = "Chen, MD"
            user.email = "dr.chen@cognitivehealth.org"
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS("Created clinician user: clinician / assessment2025"))
        else:
            user.set_password("assessment2025")
            user.save()

        profile, _ = ClinicianProfile.objects.get_or_create(
            user=user,
            defaults={
                'display_name': "Dr. Sarah Chen",
                'organization': "Cognitive Health & Memory Institute"
            }
        )

        # 2. Seed PPST-4938 (Slide 2-4 / Slide 9 specifications)
        # Check if PPST-4938 already exists
        session_4938 = AssessmentSession.objects.filter(patient_code="PPST-4938", status="COMPLETED").first()
        if not session_4938:
            session_id = uuid.uuid4()
            completed_time = timezone.now() - timedelta(hours=2)
            started_time = completed_time - timedelta(minutes=4, seconds=12)

            session_4938 = AssessmentSession.objects.create(
                id=session_id,
                clinician=profile,
                patient_code="PPST-4938",
                dob=date(1998, 5, 14),
                age_bracket="18-30 years",
                language="English",
                audio_voice="Female",
                difficulty="Standard",
                status="COMPLETED",
                token_hash=AssessmentSession.hash_token("demo-token-4938"),
                token_raw="demo-token-4938",
                expires_at=timezone.now() + timedelta(days=5),
                started_at=started_time,
                completed_at=completed_time,
            )

            # Round 1: Shape Matching (15 attempts, 14 correct, 1 mistake)
            r1 = AssessmentRound.objects.create(
                session=session_4938,
                round_number=1,
                mode="shape_matching",
                pair_count=3,
                card_count=6,
                study_time_ms=5000,
            )
            # Round 2: Shape + Direction (15 attempts, 12 correct, 3 mistakes)
            r2 = AssessmentRound.objects.create(
                session=session_4938,
                round_number=2,
                mode="shape_direction",
                pair_count=3,
                card_count=6,
                study_time_ms=5000,
            )
            # Round 3: Increased Complexity (18 attempts, 13 correct, 5 mistakes => total 48 attempts, 39 correct, 9 mistakes = 82%)
            r3 = AssessmentRound.objects.create(
                session=session_4938,
                round_number=3,
                mode="complex_matching",
                pair_count=4,
                card_count=8,
                study_time_ms=5000,
            )

            # Generate realistic attempts for R1
            # Avg latency around 2.1s (2100ms)
            attempt_num = 1
            for i in range(15):
                is_corr = (i != 4) # 1 error on attempt 5
                lat = round(random.uniform(1400, 2800), 1)
                target = "Circle (direction)" if not is_corr else "Circle"
                ResponseEvent.objects.create(
                    round=r1,
                    attempt_number=attempt_num,
                    selected_cards=[0, 3] if is_corr else [0, 2],
                    target_shape=target,
                    is_correct=is_corr,
                    response_latency_ms=lat,
                )
                attempt_num += 1

            # Generate realistic attempts for R2
            # Avg latency around 2.9s (2900ms)
            for i in range(15):
                is_corr = (i not in (3, 8, 12)) # 3 errors
                lat = round(random.uniform(2000, 3800), 1)
                target = "Triangle (direction)" if not is_corr else "Triangle"
                ResponseEvent.objects.create(
                    round=r2,
                    attempt_number=attempt_num,
                    selected_cards=[1, 4] if is_corr else [1, 5],
                    target_shape=target,
                    is_correct=is_corr,
                    response_latency_ms=lat,
                )
                attempt_num += 1

            # Generate realistic attempts for R3
            # Avg latency around 3.4s (3400ms)
            # Fastest latency: 800ms, Slowest: 7400ms
            for i in range(18):
                is_corr = (i not in (2, 7, 10, 14, 16)) # 5 errors
                if i == 0:
                    lat = 800.0 # Fastest response as per slide: 0.8s
                elif i == 11:
                    lat = 7400.0 # Slowest response as per slide: 7.4s
                else:
                    lat = round(random.uniform(2200, 4600), 1)

                if i == 2:
                    target = "Plus (rotation)"
                elif i == 7:
                    target = "Plus (rotation)"
                elif i == 10:
                    target = "Plus (rotation)"
                elif i == 14:
                    target = "Square (rotation)"
                elif i == 16:
                    target = "Triangle (direction)"
                else:
                    target = "Shape Match"

                ResponseEvent.objects.create(
                    round=r3,
                    attempt_number=attempt_num,
                    selected_cards=[2, 6] if is_corr else [2, 5],
                    target_shape=target,
                    is_correct=is_corr,
                    response_latency_ms=lat,
                )
                attempt_num += 1

            # Create AssessmentResult matching Slide 2-4 / Slide 9
            level_summary = {
                'level_1': {
                    'level_number': 1,
                    'title': 'Shape Matching',
                    'accuracy': 93.3,
                    'correct': 14,
                    'total': 15,
                    'avg_latency_ms': 2100.0,
                    'avg_response_sec': '2.1s',
                    'completion_time_sec': 62,
                    'completion_time_display': '1m 02s'
                },
                'level_2': {
                    'level_number': 2,
                    'title': 'Shape + Direction',
                    'accuracy': 80.0,
                    'correct': 12,
                    'total': 15,
                    'avg_latency_ms': 2900.0,
                    'avg_response_sec': '2.9s',
                    'completion_time_sec': 94,
                    'completion_time_display': '1m 34s'
                },
                'level_3': {
                    'level_number': 3,
                    'title': 'Increased Complexity',
                    'accuracy': 72.2,
                    'correct': 13,
                    'total': 18,
                    'avg_latency_ms': 3400.0,
                    'avg_response_sec': '3.4s',
                    'completion_time_sec': 96,
                    'completion_time_display': '1m 36s'
                }
            }

            shape_errors = {
                'Triangle (direction)': 4,
                'Plus (rotation)': 3,
                'Circle (direction)': 1,
                'Square (rotation)': 1,
            }

            # 48 points for response time trend line chart
            attempts_all = list(ResponseEvent.objects.filter(round__session=session_4938).order_by('attempt_number'))
            questions_trend = [
                {'question': i + 1, 'latency_sec': round(a.response_latency_ms / 1000.0, 2), 'is_correct': a.is_correct}
                for i, a in enumerate(attempts_all)
            ]

            full_summary_json = {
                'levels': level_summary,
                'shape_errors': shape_errors,
                'attention_consistency': {
                    'score': 85,
                    'variation_sec': 1.1,
                    'label': 'Consistent',
                    'description': 'Low variation suggests sustained attention',
                },
                'memory_trend': {
                    'change_percent': -20.0,
                    'l1_acc': 93,
                    'l3_acc': 73,
                    'description': 'Accuracy decreased from 93% to 73%',
                },
                'questions_trend': questions_trend,
            }

            AssessmentResult.objects.create(
                session=session_4938,
                completed_pairs=10,
                total_attempts=48,
                mistakes=9,
                accuracy_percent=82.0,
                avg_latency_ms=2800.0,
                fastest_latency_ms=800.0,
                slowest_latency_ms=7400.0,
                completion_time_ms=252000, # 4m 12s
                level_summary_json=full_summary_json,
                clinician_notes="Patient completed all levels with good overall accuracy (82%). Noted decrease in accuracy and slower response times at higher complexity level (Level 3), which may suggest increased cognitive load with added directional components.",
            )
            self.stdout.write(self.style.SUCCESS("Created completed assessment PPST-4938"))

        # 3. Create a pending session as shown in image-2-1.png ("PPST-4938" or "PPST-5120")
        pending_token = "sample-patient-token-2025"
        pending_session = AssessmentSession.objects.filter(token_raw=pending_token).first()
        if not pending_session:
            pending_session = AssessmentSession.objects.create(
                clinician=profile,
                patient_code="PPST-5120",
                dob=date(1995, 8, 22),
                age_bracket="18-30 years",
                language="English",
                audio_voice="Female",
                difficulty="Standard",
                status="PENDING",
                token_hash=AssessmentSession.hash_token(pending_token),
                token_raw=pending_token,
                expires_at=timezone.now() + timedelta(days=2),
            )
            AssessmentRound.objects.create(session=pending_session, round_number=1, mode='shape_matching', pair_count=3, card_count=6, study_time_ms=5000)
            AssessmentRound.objects.create(session=pending_session, round_number=2, mode='shape_direction', pair_count=3, card_count=6, study_time_ms=5000)
            AssessmentRound.objects.create(session=pending_session, round_number=3, mode='complex_matching', pair_count=4, card_count=8, study_time_ms=5000)
            self.stdout.write(self.style.SUCCESS(f"Created pending session PPST-5120 with link token: {pending_token}"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))

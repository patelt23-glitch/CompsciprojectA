import uuid
import hashlib
import secrets
from datetime import datetime, date, timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ClinicianProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=150)
    organization = models.CharField(max_length=200, blank=True)
    preferred_language = models.CharField(max_length=16, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_name} ({self.organization or 'Independent'})"


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    otp = models.CharField(max_length=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    @classmethod
    def generate_for_user(cls, user, expiry_minutes=15):
        raw_token = secrets.token_urlsafe(32)
        raw_otp = f"{secrets.randbelow(900000) + 100000}"
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        return cls.objects.create(
            user=user,
            token=raw_token,
            otp=raw_otp,
            expires_at=expires_at,
        )

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    def __str__(self):
        return f"Reset token for {self.user.username} (Valid: {self.is_valid()})"


def calculate_age_bracket(dob_or_date):
    if not dob_or_date:
        return "18-30 years"
    if isinstance(dob_or_date, str):
        try:
            dob_or_date = datetime.strptime(dob_or_date, "%Y-%m-%d").date()
        except ValueError:
            return "18-30 years"
    today = date.today()
    age = today.year - dob_or_date.year - ((today.month, today.day) < (dob_or_date.month, dob_or_date.day))
    if age < 18:
        return "Under 18"
    elif age <= 30:
        return "18-30 years"
    elif age <= 44:
        return "30-44 years"
    elif age <= 59:
        return "45-59 years"
    else:
        return "60+ years"


class PatientProfile(models.Model):
    """Optional patient accounts; anonymous invitations remain supported."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patient account {self.user_id}"


class AssessmentSession(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinician = models.ForeignKey(ClinicianProfile, on_delete=models.CASCADE, related_name='sessions')
    patient_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='patient_assessments')
    invitation_code = models.CharField(max_length=40, unique=True, null=True, blank=True, db_index=True)
    difficulty_settings = models.JSONField(default=dict, blank=True)
    participant_id = models.CharField(max_length=64, blank=True, db_index=True)
    patient_code = models.CharField(max_length=64, db_index=True)
    dob = models.DateField(null=True, blank=True)
    age_bracket = models.CharField(max_length=32, default="18-30 years")
    language = models.CharField(max_length=32, default="English")
    audio_voice = models.CharField(max_length=32, default="Female")
    difficulty = models.CharField(max_length=32, default="Standard")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    token_hash = models.CharField(max_length=64, db_index=True)
    token_raw = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    def __str__(self):
        return f"{self.patient_code} - {self.status} ({self.id})"


class AssessmentRound(models.Model):
    session = models.ForeignKey(AssessmentSession, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()
    is_practice = models.BooleanField(default=False)
    mode = models.CharField(max_length=64, default="card_matching")
    pair_count = models.IntegerField(default=3)
    card_count = models.IntegerField(default=6)
    study_time_ms = models.IntegerField(default=5000)
    deck_layout = models.JSONField(default=list)

    class Meta:
        ordering = ['round_number']
        unique_together = ('session', 'round_number')

    def __str__(self):
        practice_tag = " [Practice]" if self.is_practice else ""
        return f"Round {self.round_number}{practice_tag} (Session {self.session.patient_code})"


class ResponseEvent(models.Model):
    round = models.ForeignKey(AssessmentRound, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.IntegerField()
    selected_cards = models.JSONField(default=list)
    target_shape = models.CharField(max_length=64, blank=True)
    is_correct = models.BooleanField(default=False)
    response_latency_ms = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['attempt_number']

    def __str__(self):
        return f"Attempt {self.attempt_number} (Round {self.round.round_number}) - {'Correct' if self.is_correct else 'Mistake'}"


class AssessmentResult(models.Model):
    session = models.OneToOneField(AssessmentSession, on_delete=models.CASCADE, related_name='result')
    completed_pairs = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    mistakes = models.IntegerField(default=0)
    accuracy_percent = models.FloatField(default=0.0)
    avg_latency_ms = models.FloatField(default=0.0)
    fastest_latency_ms = models.FloatField(default=0.0)
    slowest_latency_ms = models.FloatField(default=0.0)
    completion_time_ms = models.IntegerField(default=0)
    practice_summary = models.JSONField(default=dict)
    level_summary_json = models.JSONField(default=dict)
    clinician_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result {self.session.patient_code} - Accuracy: {self.accuracy_percent:.1f}%"

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def invitation_token():
    return secrets.token_urlsafe(32)


def invitation_expiry():
    return timezone.now() + timedelta(days=settings.INVITATION_DAYS)


class TestGiverProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    organization = models.CharField(max_length=200, blank=True)


class Participant(models.Model):
    test_giver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participants')
    identifier = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['test_giver', 'identifier'], name='unique_participant_per_giver')]


class Invitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='invitations')
    token = models.CharField(max_length=64, default=invitation_token, unique=True, editable=False)
    language = models.CharField(max_length=16, default='English')
    voice = models.CharField(max_length=16, default='No Voice')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=invitation_expiry)
    consumed_at = models.DateTimeField(null=True, blank=True)


class AssessmentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invitation = models.OneToOneField(Invitation, on_delete=models.CASCADE, related_name='attempt')
    deck = models.JSONField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class AssessmentResult(models.Model):
    attempt = models.OneToOneField(AssessmentAttempt, on_delete=models.CASCADE, related_name='result')
    selections = models.JSONField()
    matches = models.PositiveIntegerField()
    mistakes = models.PositiveIntegerField()
    average_seconds = models.FloatField()
    accuracy = models.FloatField()

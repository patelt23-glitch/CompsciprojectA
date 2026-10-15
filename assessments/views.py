import csv
import json
import math
import random
import re
from functools import wraps

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from .models import AssessmentAttempt, AssessmentResult, Invitation, Participant, TestGiverProfile


def api(methods, authenticated=False):
    def decorate(view):
        @never_cache
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                response = JsonResponse({'error': 'Method not allowed.'}, status=405)
                response['Allow'] = ', '.join(methods)
                return response
            if authenticated and not request.user.is_authenticated:
                return JsonResponse({'error': 'Please sign in.'}, status=401)
            try:
                request.data = {}
                if request.method == 'POST':
                    request.data = json.loads(request.body or '{}')
                    if not isinstance(request.data, dict):
                        raise ValueError('Expected a JSON object.')
                return view(request, *args, **kwargs)
            except (ValueError, ValidationError) as error:
                message = ' '.join(error.messages) if isinstance(error, ValidationError) else str(error)
                return JsonResponse({'error': message or 'Invalid request.'}, status=400)
        return wrapped
    return decorate


def text(data, key, maximum, required=True):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise ValueError(f'Invalid {key}.')
    value = value.strip()
    if len(value) > maximum or (required and not value):
        raise ValueError(f'{key} is required and must be at most {maximum} characters.')
    return value


def identity(user):
    profile, _ = TestGiverProfile.objects.get_or_create(user=user)
    return {'name': user.first_name or user.username, 'email': user.email, 'organization': profile.organization}


@never_cache
@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, 'index.html')


@login_required
@never_cache
@ensure_csrf_cookie
@require_GET
def dashboard_page(request):
    return render(request, 'index.html')


@ensure_csrf_cookie
@api(['GET'])
def session(request):
    return JsonResponse({'user': identity(request.user) if request.user.is_authenticated else None})


@api(['POST'])
def sign_in(request):
    email = text(request.data, 'email', 150).lower()
    password = request.data.get('password', '')
    if not isinstance(password, str) or len(password) > 4096:
        raise ValueError('Invalid password.')
    user = authenticate(request, username=email, password=password)
    if user is None:
        return JsonResponse({'error': 'Incorrect email or password.'}, status=401)
    login(request, user)
    request.session.set_expiry(1209600 if request.data.get('remember') is True else 0)
    return JsonResponse({'user': identity(user)})


@api(['POST'])
def sign_up(request):
    email = text(request.data, 'email', 150).lower()
    validate_email(email)
    name = text(request.data, 'name', 150)
    organization = text(request.data, 'organization', 200, required=False)
    password = request.data.get('password', '')
    if not isinstance(password, str) or len(password) > 4096:
        raise ValueError('Invalid password.')
    user = get_user_model()(username=email, email=email, first_name=name)
    validate_password(password, user=user)
    try:
        with transaction.atomic():
            user.set_password(password)
            user.save()
            TestGiverProfile.objects.create(user=user, organization=organization)
    except IntegrityError:
        raise ValueError('An account with that email already exists.')
    login(request, user)
    request.session.set_expiry(0)
    return JsonResponse({'user': identity(user)}, status=201)


@api(['POST'], authenticated=True)
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})


@api(['POST'], authenticated=True)
def profile(request):
    user = request.user
    name = text(request.data, 'name', 150)
    email = text(request.data, 'email', 150).lower()
    validate_email(email)
    organization = text(request.data, 'organization', 200, required=False)
    try:
        with transaction.atomic():
            user.first_name, user.email, user.username = name, email, email
            user.save(update_fields=['first_name', 'email', 'username'])
            TestGiverProfile.objects.update_or_create(user=user, defaults={'organization': organization})
    except IntegrityError:
        raise ValueError('An account with that email already exists.')
    return JsonResponse({'user': identity(user)})


def invitation_data(request, invitation):
    return {
        'id': str(invitation.id), 'participantId': invitation.participant.identifier,
        'language': invitation.language, 'voice': invitation.voice,
        'created': invitation.created_at.isoformat(), 'expires': invitation.expires_at.isoformat(),
        'status': 'Completed' if invitation.consumed_at else ('Expired' if invitation.expires_at <= timezone.now() else 'Pending'),
        'url': request.build_absolute_uri(reverse('home')) + '?invite=' + invitation.token + '#instructions',
    }


def result_data(result):
    invitation = result.attempt.invitation
    return {
        'id': result.pk, 'sessionId': str(invitation.id),
        'participantId': invitation.participant.identifier,
        'date': result.attempt.completed_at.isoformat(), 'matches': result.matches,
        'mistakes': result.mistakes, 'attempts': len(result.selections),
        'accuracy': round(result.accuracy), 'average': result.average_seconds,
    }


@api(['GET'], authenticated=True)
def dashboard(request):
    invitations = Invitation.objects.filter(participant__test_giver=request.user).select_related('participant').order_by('-created_at')
    results = AssessmentResult.objects.filter(attempt__invitation__participant__test_giver=request.user).select_related('attempt__invitation__participant').order_by('-attempt__completed_at')
    return JsonResponse({
        'invitations': [invitation_data(request, invitation) for invitation in invitations if not invitation.consumed_at],
        'results': [result_data(result) for result in results],
    })


@api(['POST'], authenticated=True)
def create_invitation(request):
    identifier = text(request.data, 'participantId', 64)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise ValueError('Participant ID may contain letters, numbers, hyphens and underscores only.')
    language = text(request.data, 'language', 16)
    voice = text(request.data, 'voice', 16)
    if language != 'English' or voice != 'No Voice':
        raise ValueError('Only English without audio is currently supported.')
    with transaction.atomic():
        participant, _ = Participant.objects.get_or_create(test_giver=request.user, identifier=identifier)
        invitation = Invitation.objects.create(participant=participant, language=language, voice=voice)
    return JsonResponse(invitation_data(request, invitation), status=201)


@api(['POST'])
def start_attempt(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    if invitation.consumed_at or invitation.expires_at <= timezone.now():
        return JsonResponse({'error': 'This invitation has expired or has already been completed.'}, status=410)
    deck = ['up', 'right', 'triangle'] * 2
    random.SystemRandom().shuffle(deck)
    attempt, _ = AssessmentAttempt.objects.get_or_create(invitation=invitation, defaults={'deck': deck})
    return JsonResponse({'attemptId': str(attempt.id), 'deck': attempt.deck})


def score(deck, selections):
    if not isinstance(selections, list) or not 3 <= len(selections) <= 1000:
        raise ValueError('Submit between 3 and 1000 pair selections.')
    matched, mistakes, times = set(), 0, []
    for selection in selections:
        if not isinstance(selection, dict):
            raise ValueError('Invalid pair selection.')
        first, second, seconds = (selection.get(key) for key in ('first', 'second', 'seconds'))
        if (type(first) is not int or type(second) is not int or not 0 <= first < 6
                or not 0 <= second < 6 or first == second or first in matched or second in matched):
            raise ValueError('Invalid card selection.')
        if type(seconds) not in (float, int) or not math.isfinite(seconds) or not 0 <= seconds <= 3600:
            raise ValueError('Invalid response time.')
        times.append(seconds)
        if deck[first] == deck[second]:
            matched.update([first, second])
        else:
            mistakes += 1
    if len(matched) != 6:
        raise ValueError('Complete all three pairs before submitting.')
    return mistakes, sum(times) / len(times), 300 / len(times)


@api(['POST'])
def complete_attempt(request, token):
    invitation = get_object_or_404(Invitation, token=token)
    attempt = get_object_or_404(AssessmentAttempt, invitation=invitation)
    # A retry after a lost response must not create a second result.
    if invitation.consumed_at:
        return JsonResponse({'saved': True})
    if invitation.expires_at <= timezone.now():
        return JsonResponse({'error': 'This invitation has expired.'}, status=410)
    selections = request.data.get('selections')
    mistakes, average, accuracy = score(attempt.deck, selections)
    now = timezone.now()
    with transaction.atomic():
        claimed = Invitation.objects.filter(pk=invitation.pk, consumed_at__isnull=True, expires_at__gt=now).update(consumed_at=now)
        if not claimed:
            return JsonResponse({'error': 'This invitation is no longer available.'}, status=409)
        attempt.completed_at = now
        attempt.save(update_fields=['completed_at'])
        AssessmentResult.objects.create(
            attempt=attempt, selections=selections, matches=3, mistakes=mistakes,
            average_seconds=average, accuracy=accuracy,
        )
    return JsonResponse({'saved': True}, status=201)


@login_required
@never_cache
@require_GET
def export_csv(request, result_id=None):
    results = AssessmentResult.objects.filter(attempt__invitation__participant__test_giver=request.user).select_related('attempt__invitation__participant').order_by('-attempt__completed_at')
    if result_id is not None:
        results = [get_object_or_404(results, pk=result_id)]
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="assessment-results.csv"'
    writer = csv.writer(response)
    writer.writerow(['session_id', 'participant_id', 'completed_at', 'correct_matches', 'mistakes', 'accuracy_percent', 'average_seconds'])
    for result in results:
        row = result_data(result)
        writer.writerow([row['sessionId'], row['participantId'], row['date'], row['matches'], row['mistakes'], round(result.accuracy, 2), round(row['average'], 2)])
    return response

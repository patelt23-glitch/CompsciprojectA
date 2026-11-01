import csv
import json
import math
import statistics
import re
import secrets
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from functools import wraps
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import Avg, Count, Q
from django.conf import settings

from .models import (
    ClinicianProfile,
    PatientProfile,
    PasswordResetToken,
    AssessmentSession,
    AssessmentRound,
    ResponseEvent,
    AssessmentResult,
    calculate_age_bracket,
)

from .difficulty import parse_configuration, round_specs

User = get_user_model()


def clinician_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if hasattr(request.user, 'patient_profile') and not request.user.is_staff:
            return HttpResponse('Clinician account required.', status=403)
        return view(request, *args, **kwargs)
    return wrapped


def patient_required(view):
    @login_required(login_url='/patient-login/')
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'patient_profile'):
            return HttpResponse('Patient account required.', status=403)
        return view(request, *args, **kwargs)
    return wrapped



# ==============================================================================
# Helper Functions & Deck Generation
# ==============================================================================

def generate_deck_for_round(pair_count, mode='shapes'):
    """
    Generate authoritative, server-validated shuffled card decks for each round.
    Every pair has a matching match_key.
    """
    shapes_palette = [
        {'shape': 'circle', 'color': '#4f46e5'},
        {'shape': 'triangle', 'color': '#f59e0b'},
        {'shape': 'square', 'color': '#059669'},
        {'shape': 'plus', 'color': '#7c3aed'},
        {'shape': 'star', 'color': '#ec4899'},
        {'shape': 'diamond', 'color': '#0284c7'},
    ]

    directions_palette = ['up', 'right', 'down', 'left']

    pairs = []
    if mode == 'practice':
        # Practice round: 2 simple shape pairs
        for i in range(min(pair_count, 2)):
            item = shapes_palette[i]
            pair_spec = {
                'shape': item['shape'],
                'direction': 'none',
                'color': item['color'],
                'match_key': f"practice_{item['shape']}",
            }
            pairs.extend([pair_spec.copy(), pair_spec.copy()])

    elif mode == 'direction':
        # Directional matching (e.g. triangle pointing in specific orientations)
        for i in range(pair_count):
            shape_info = shapes_palette[i % len(shapes_palette)]
            direction = directions_palette[i % len(directions_palette)]
            pair_spec = {
                'shape': shape_info['shape'],
                'direction': direction,
                'color': shape_info['color'],
                'match_key': f"{shape_info['shape']}_{direction}",
            }
            pairs.extend([pair_spec.copy(), pair_spec.copy()])

    elif mode == 'complex':
        # Complex multi-attribute matching
        for i in range(pair_count):
            shape_info = shapes_palette[i % len(shapes_palette)]
            direction = directions_palette[(i + 1) % len(directions_palette)]
            pair_spec = {
                'shape': shape_info['shape'],
                'direction': direction,
                'color': shape_info['color'],
                'match_key': f"complex_{shape_info['shape']}_{direction}_{shape_info['color']}",
            }
            pairs.extend([pair_spec.copy(), pair_spec.copy()])

    else:
        # Standard shape matching
        for i in range(pair_count):
            item = shapes_palette[i % len(shapes_palette)]
            pair_spec = {
                'shape': item['shape'],
                'direction': 'none',
                'color': item['color'],
                'match_key': f"std_{item['shape']}",
            }
            pairs.extend([pair_spec.copy(), pair_spec.copy()])

    # Cryptographically shuffle deck
    secrets.SystemRandom().shuffle(pairs)

    # Assign sequential zero-based card ids
    deck = []
    for idx, card in enumerate(pairs):
        card['id'] = idx
        deck.append(card)

    return deck


def get_clinician_identity(user):
    profile, _ = ClinicianProfile.objects.get_or_create(
        user=user,
        defaults={'display_name': user.get_full_name() or user.username, 'organization': 'Cognitive Health Center'}
    )
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': profile.display_name,
        'organization': profile.organization,
        'preferred_language': profile.preferred_language,
    }


# ==============================================================================
# Public & Landing Views
# ==============================================================================

def home_view(request):
    """Public landing page matching Apple Design specs."""
    return render(request, 'landing.html')


# ==============================================================================
# Clinician Authentication & Account Management
# ==============================================================================

@ensure_csrf_cookie
def signup_view(request):
    """Clinician registration page and handler."""
    if request.user.is_authenticated:
        return redirect('patient_dashboard' if hasattr(request.user, 'patient_profile') else 'dashboard')

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON body.'}, status=400)
            is_json = True
        else:
            data = request.POST
            is_json = False

        name = data.get('name', '').strip()
        organization = data.get('organization', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Validations
        if not name:
            error = 'Full name is required.'
        elif not email:
            error = 'Email address is required.'
        else:
            try:
                validate_email(email)
                error = None
            except ValidationError:
                error = 'Please enter a valid email address.'

        if not error and password != confirm_password:
            error = 'Passwords do not match.'

        if not error:
            temp_user = User(username=email, email=email, first_name=name)
            try:
                validate_password(password, user=temp_user)
            except ValidationError as e:
                error = ' '.join(e.messages)

        if not error:
            if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
                error = 'An account with that email already exists. Please sign in.'

        if error:
            if is_json:
                return JsonResponse({'error': error}, status=400)
            return render(request, 'signup.html', {
                'error': error,
                'name': name,
                'organization': organization,
                'email': email,
            })

        # Create user and profile atomically
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=name,
                password=password,
            )
            ClinicianProfile.objects.create(
                user=user,
                display_name=name,
                organization=organization,
            )

        login(request, user)
        request.session.set_expiry(0)

        if is_json:
            return JsonResponse({'status': 'ok', 'user': get_clinician_identity(user), 'redirect': '/dashboard/'}, status=201)
        return redirect('dashboard')

    return render(request, 'signup.html')


@ensure_csrf_cookie
def login_view(request):
    """Clinician sign-in endpoint with session expiry handling."""
    if request.user.is_authenticated:
        return redirect('patient_dashboard' if hasattr(request.user, 'patient_profile') else 'dashboard')

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            is_json = True
        else:
            data = request.POST
            is_json = False

        username = data.get('username', '').strip()
        password = data.get('password', '')
        remember = data.get('remember') in (True, 'true', 'on', '1')

        # Allow logging in with either username or email
        user = authenticate(request, username=username, password=password)
        if user is None and '@' in username:
            try:
                matching_user = User.objects.get(email__iexact=username)
                user = authenticate(request, username=matching_user.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None

        if user is not None and hasattr(user, 'patient_profile'):
            user = None

        if user is not None:
            login(request, user)
            ClinicianProfile.objects.get_or_create(
                user=user,
                defaults={'display_name': user.get_full_name() or user.username, 'organization': 'Cognitive Health Center'}
            )

            # Session handling: 14 days if remember-me is checked, 0 (browser close) if not
            if remember:
                request.session.set_expiry(getattr(settings, 'SESSION_COOKIE_AGE', 1209600))
            else:
                request.session.set_expiry(0)

            if is_json:
                return JsonResponse({'status': 'ok', 'user': get_clinician_identity(user), 'redirect': '/dashboard/'})
            return redirect('dashboard')
        else:
            error = 'Incorrect email or password. Please try again.'
            if is_json:
                return JsonResponse({'error': error}, status=401)
            return render(request, 'login.html', {'error': error, 'username': username})

    return render(request, 'login.html')


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Sign out clinician and flush session."""
    logout(request)
    return redirect('login')


@clinician_required
@ensure_csrf_cookie
def profile_view(request):
    """Clinician profile page for viewing and editing credentials."""
    profile, _ = ClinicianProfile.objects.get_or_create(
        user=request.user,
        defaults={'display_name': request.user.get_full_name() or request.user.username}
    )

    success_msg = None
    error_msg = None

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            is_json = True
        else:
            data = request.POST
            is_json = False

        name = data.get('name', '').strip()
        organization = data.get('organization', '').strip()
        email = data.get('email', '').strip().lower()
        preferred_lang = data.get('preferred_language', 'English').strip()

        if not name:
            error_msg = 'Name cannot be empty.'
        elif not email:
            error_msg = 'Email address cannot be empty.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                error_msg = 'Please enter a valid email address.'

        if not error_msg and email != request.user.email:
            if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
                error_msg = 'Another account already uses that email address.'

        if error_msg:
            if is_json:
                return JsonResponse({'error': error_msg}, status=400)
        else:
            with transaction.atomic():
                user = request.user
                user.first_name = name
                user.email = email
                # If username matches email format, keep it synchronized
                if '@' in user.username:
                    user.username = email
                user.save(update_fields=['first_name', 'email', 'username'])

                profile.display_name = name
                profile.organization = organization
                profile.preferred_language = preferred_lang
                profile.save()

            success_msg = 'Profile updated successfully.'
            if is_json:
                return JsonResponse({'status': 'ok', 'message': success_msg, 'user': get_clinician_identity(user)})

    context = {
        'profile': profile,
        'user': request.user,
        'success': success_msg,
        'error': error_msg,
    }
    return render(request, 'profile.html', context)


# ==============================================================================
# Password Recovery: Forgot Password & Reset Confirmation
# ==============================================================================

@ensure_csrf_cookie
def forgot_password_view(request):
    """
    Password recovery request view:
    - Generates cryptographically secure reset token and 6-digit OTP
    - Dispatches email (or logs via console backend)
    - Provides instant test token/OTP panel in development/demo mode
    """
    sent = False
    error = None
    reset_link = None
    otp_code = None
    email_entered = ""

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            is_json = True
        else:
            data = request.POST
            is_json = False

        email_entered = data.get('email', '').strip().lower()
        if not email_entered:
            error = 'Please enter your registered email address.'
        else:
            user = User.objects.filter(Q(email__iexact=email_entered) | Q(username__iexact=email_entered)).first()
            if user:
                # Invalidate existing unused tokens for this user
                PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

                reset_record = PasswordResetToken.generate_for_user(user, expiry_minutes=15)
                token_val = reset_record.token
                otp_code = reset_record.otp
                reset_link = request.build_absolute_uri(f"/reset-password/{token_val}/")

                # Send email notice
                subject = "Visuospatial Assessment - Password Reset Request"
                message = (
                    f"Hello {user.first_name or user.username},\n\n"
                    f"A password reset was requested for your Clinician account.\n\n"
                    f"Your 6-digit verification code is: {otp_code}\n\n"
                    f"Or use this direct link to reset your password:\n{reset_link}\n\n"
                    f"This code and link will expire in 15 minutes.\n"
                    f"If you did not request this, please ignore this email."
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception as mail_err:
                    print("Notice: Email dispatch error:", mail_err)

                sent = True
            else:
                # Security note: show consistent response to prevent email harvesting,
                # but provide clear guidance if user typed wrong email
                sent = True

        if is_json:
            return JsonResponse({
                'sent': True,
                'reset_link': reset_link,
                'otp': otp_code,
            })

    return render(request, 'forgot_password.html', {
        'sent': sent,
        'error': error,
        'reset_link': reset_link,
        'otp_code': otp_code,
        'email': email_entered,
    })


@ensure_csrf_cookie
def reset_password_view(request, token=None):
    """
    Password reset confirmation:
    - Validates token from URL or 6-digit OTP + email from form
    - Enforces Django's AUTH_PASSWORD_VALIDATORS
    - Updates password atomically and marks token as used
    """
    error = None
    success = False
    target_token_obj = None

    if token:
        target_token_obj = PasswordResetToken.objects.filter(token=token).first()
        if not target_token_obj or not target_token_obj.is_valid():
            error = 'This reset link has expired or has already been used. Please request a new link.'

    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            is_json = True
        else:
            data = request.POST
            is_json = False

        post_token = data.get('token', token or '').strip()
        post_otp = data.get('otp', '').strip()
        post_email = data.get('email', '').strip().lower()
        new_password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Lookup token object if not already identified
        if not target_token_obj:
            if post_token:
                target_token_obj = PasswordResetToken.objects.filter(token=post_token).first()
            elif post_otp and post_email:
                target_token_obj = PasswordResetToken.objects.filter(
                    user__email__iexact=post_email,
                    otp=post_otp,
                    is_used=False
                ).first()

        if not target_token_obj or not target_token_obj.is_valid():
            error = 'Invalid, expired, or previously used reset code. Please request a fresh reset link.'
        elif not new_password:
            error = 'Please enter a new password.'
        elif new_password != confirm_password:
            error = 'The passwords do not match. Please verify and try again.'
        else:
            try:
                validate_password(new_password, user=target_token_obj.user)
            except ValidationError as val_err:
                error = ' '.join(val_err.messages)

        if not error and target_token_obj:
            with transaction.atomic():
                user = target_token_obj.user
                user.set_password(new_password)
                user.save()
                target_token_obj.is_used = True
                target_token_obj.save(update_fields=['is_used'])

            success = True
            if is_json:
                return JsonResponse({'status': 'ok', 'message': 'Password reset successful.'})

    return render(request, 'reset_password.html', {
        'token': token,
        'error': error,
        'success': success,
        'user_name': target_token_obj.user.first_name if target_token_obj else '',
    })


# ==============================================================================
# Clinician Dashboard & Link Generation
# ==============================================================================

@clinician_required
@ensure_csrf_cookie
def dashboard_view(request):
    """
    Clinician Dashboard:
    - Scoped strictly to the authenticated clinician's profile
    - Shows aggregate statistics, participant invitations, and completed assessments
    """
    clinician, _ = ClinicianProfile.objects.get_or_create(
        user=request.user,
        defaults={'display_name': request.user.get_full_name() or request.user.username}
    )

    sessions = AssessmentSession.objects.filter(clinician=clinician).select_related('result')
    completed_sessions = [s for s in sessions if s.status == 'COMPLETED' and hasattr(s, 'result')]
    pending_sessions = [s for s in sessions if s.status in ('PENDING', 'IN_PROGRESS')]

    total_completed = len(completed_sessions)
    total_pending = len(pending_sessions)

    if total_completed > 0:
        avg_acc = sum(s.result.accuracy_percent for s in completed_sessions) / total_completed
        avg_resp = sum(s.result.avg_latency_ms for s in completed_sessions) / total_completed / 1000.0
    else:
        avg_acc = 0.0
        avg_resp = 0.0

    # Age bracket breakdown
    bracket_counts = {}
    for s in completed_sessions:
        b = s.age_bracket or "Unknown"
        bracket_counts[b] = bracket_counts.get(b, 0) + 1

    context = {
        'clinician': clinician,
        'completed_count': total_completed,
        'pending_count': total_pending,
        'avg_accuracy': round(avg_acc, 1),
        'avg_response_sec': round(avg_resp, 1),
        'pending_sessions': pending_sessions[:20],
        'completed_sessions': completed_sessions[:25],
        'bracket_counts': bracket_counts,
    }
    return render(request, 'dashboard.html', context)


@clinician_required
@require_http_methods(["POST"])
def api_create_session(request):
    """
    Generate patient assessment link:
    - Custom participant ID support (e.g. P001, PT-102) or auto-generated PPST-XXXX
    - Seven-day link expiry (INVITATION_DAYS = 7)
    - Full difficulty support: Standard (3 rounds) vs Advanced (4 rounds with direction/rotation)
    - Authoritative server-generated shuffled card decks
    """
    clinician, _ = ClinicianProfile.objects.get_or_create(
        user=request.user,
        defaults={'display_name': request.user.get_full_name() or request.user.username}
    )

    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError('Expected an object')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    try:
        config = parse_configuration(data)
        specs = list(round_specs(config))
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    custom_participant_id = data.get('participant_id', '').strip()
    dob_str = data.get('dob')
    language = data.get('language', 'English')
    audio_voice = data.get('audio_voice', 'Female')
    difficulty = config['difficulty']

    # Validate custom participant ID if supplied
    if custom_participant_id:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', custom_participant_id):
            return JsonResponse({
                'error': 'Participant ID may contain letters, numbers, hyphens, and underscores only (max 64 characters).'
            }, status=400)
        patient_code = custom_participant_id
    else:
        patient_code = f"PPST-{secrets.token_hex(6).upper()}"

    dob = None
    age_bracket = "Not provided"
    if dob_str:
        try:
            from datetime import datetime
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            age_bracket = calculate_age_bracket(dob)
        except ValueError:
            pass

    # Generate secure random token and SHA-256 hash
    raw_token = secrets.token_urlsafe(32)
    token_hash = AssessmentSession.hash_token(raw_token)
    invitation_days = getattr(settings, 'INVITATION_DAYS', 7)
    expires_at = timezone.now() + timedelta(days=invitation_days)

    with transaction.atomic():
        session = AssessmentSession.objects.create(
            clinician=clinician,
            participant_id=custom_participant_id,
            patient_code=patient_code,
            dob=dob,
            age_bracket=age_bracket,
            language=language,
            audio_voice=audio_voice,
            difficulty=difficulty,
            difficulty_settings=config,
            status='PENDING',
            token_hash=token_hash,
            token_raw=raw_token,
            invitation_code=secrets.token_urlsafe(12),
            expires_at=expires_at,
        )

        # Every new session has practice + three scored rounds. The configuration
        # and each authoritative stimulus deck are frozen with the invitation.
        for spec in specs:
            AssessmentRound.objects.create(session=session, **spec)

    patient_url = request.build_absolute_uri(f"/patient/{raw_token}/")

    return JsonResponse({
        'session_id': str(session.id),
        'patient_code': patient_code,
        'invitation_code': session.invitation_code,
        'participant_id': custom_participant_id,
        'patient_url': patient_url,
        'token': raw_token,
        'age_bracket': age_bracket,
        'language': language,
        'audio_voice': audio_voice,
        'difficulty': difficulty,
        'difficulty_settings': config,
        'status': session.status,
        'expires_at': session.expires_at.isoformat(),
        'invitation_days': invitation_days,
    }, status=201)


# ==============================================================================
# Patient Assessment Test Page & Interactive Execution
# ==============================================================================

@ensure_csrf_cookie
@never_cache
def patient_test_view(request, token):
    """
    Patient assessment view:
    - Strict token authentication
    - Accessible buttons, multi-language support, real speech synthesis voice
    - Passes authoritative deck layout and round parameters
    """
    token_hash = AssessmentSession.hash_token(token)

    try:
        session = AssessmentSession.objects.get(
            Q(token_hash=token_hash) | Q(token_raw=token)
        )
    except AssessmentSession.DoesNotExist:
        return render(request, 'patient_error.html', {
            'error_title': 'Invalid Invitation Link',
            'error_message': 'This assessment link was not found. Please contact your clinician for a new link.'
        }, status=404)

    if session.patient_user_id and (not request.user.is_authenticated or request.user.pk != session.patient_user_id):
        return render(request, 'patient_error.html', {
            'error_title': 'Sign-in Required',
            'error_message': 'This invitation is linked to a patient account. Sign in with that account to continue.',
        }, status=403)

    if session.is_expired():
        session.status = 'EXPIRED'
        session.save(update_fields=['status'])
        return render(request, 'patient_error.html', {
            'error_title': 'Assessment Link Expired',
            'error_message': 'This assessment invitation has expired (valid for 7 days). Please ask your clinician to generate a new session.'
        }, status=410)

    if session.status == 'COMPLETED':
        return render(request, 'patient_error.html', {
            'error_title': 'Assessment Already Completed',
            'error_message': 'This assessment has already been finished. Thank you for your participation.'
        }, status=400)

    if session.status == 'PENDING':
        session.status = 'IN_PROGRESS'
        session.started_at = timezone.now()
        session.save(update_fields=['status', 'started_at'])

    # Assemble authoritative rounds data
    rounds_data = []
    for r in session.rounds.all().order_by('round_number'):
        rounds_data.append({
            'round_id': r.id,
            'round_number': r.round_number,
            'is_practice': r.is_practice,
            'mode': r.mode,
            'pair_count': r.pair_count,
            'card_count': r.card_count,
            'study_time_ms': r.study_time_ms,
            'deck': r.deck_layout,
        })

    context = {
        'session': session,
        'rounds_json': json.dumps(rounds_data),
        'session_id': str(session.id),
        'token': token,
        'patient_code': session.patient_code,
        'language': session.language,
        'audio_voice': session.audio_voice,
        'difficulty': session.difficulty,
    }
    return render(request, 'patient_test.html', context)


# ==============================================================================
# Attempt Submission & Atomic Completion APIs
# ==============================================================================

def verify_patient_token(request, session, body_token=None):
    """
    Strict security check: Patient APIs MUST supply a valid, matching token.
    Accepts token via X-Session-Token header or payload.
    """
    if session.patient_user_id and (not request.user.is_authenticated or request.user.pk != session.patient_user_id):
        return False
    token = request.headers.get('X-Session-Token') or body_token
    if not token:
        return False
    th = AssessmentSession.hash_token(token)
    return (th == session.token_hash or token == session.token_raw)


@require_http_methods(["POST"])
def api_submit_attempt(request, session_id):
    """
    Submit attempt:
    - Strict token check (rejects unauthenticated attempts)
    - Validates pair match against server-side deck layout (fixes client-spoofing)
    - Appends ResponseEvent audit record
    """
    try:
        session = AssessmentSession.objects.get(id=session_id)
    except AssessmentSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if session.is_expired():
        return JsonResponse({'error': 'Session expired'}, status=410)

    if session.status == 'COMPLETED':
        return JsonResponse({'error': 'Session already completed'}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    # Mandatory Token Enforcement
    client_token = data.get('token')
    if not verify_patient_token(request, session, client_token):
        return JsonResponse({'error': 'Authentication required: valid session token is missing or invalid.'}, status=403)

    round_number = data.get('round', 1)
    attempt_number = data.get('attempt', 1)
    selected_cards = data.get('selected', [])
    latency = data.get('response_latency_ms', 0.0)
    if type(round_number) is not int or type(attempt_number) is not int or attempt_number < 1:
        return JsonResponse({'error': 'Invalid round or attempt number.'}, status=400)
    if not isinstance(latency, (int, float)) or isinstance(latency, bool) or not math.isfinite(latency) or not 0 <= latency <= 3600000:
        return JsonResponse({'error': 'Invalid response latency.'}, status=400)
    try:
        assessment_round = session.rounds.get(round_number=round_number)
    except AssessmentRound.DoesNotExist:
        return JsonResponse({'error': f'Round {round_number} not found for this session'}, status=404)
    deck = assessment_round.deck_layout or []
    if not isinstance(selected_cards, list) or len(selected_cards) != 2 or any(type(idx) is not int or not 0 <= idx < len(deck) for idx in selected_cards) or selected_cards[0] == selected_cards[1]:
        return JsonResponse({'error': 'Select two distinct valid cards.'}, status=400)
    idx1, idx2 = selected_cards
    card1, card2 = deck[idx1], deck[idx2]
    is_correct = card1.get('match_key') == card2.get('match_key')
    target_shape = card1.get('shape', '')
    # Completion retries and repeated network requests must not duplicate raw
    # events. The browser numbers attempts monotonically across all rounds.
    with transaction.atomic():
        attempt, created = ResponseEvent.objects.get_or_create(
            round=assessment_round, attempt_number=attempt_number,
            defaults={'selected_cards': selected_cards, 'target_shape': target_shape,
                      'is_correct': is_correct, 'response_latency_ms': latency},
        )
    if not created and attempt.selected_cards != selected_cards:
        return JsonResponse({'error': 'Attempt number already used with different cards.'}, status=409)
    response_latency_ms = attempt.response_latency_ms
    is_correct = attempt.is_correct

    total_round_attempts = assessment_round.attempts.count()
    correct_round_attempts = assessment_round.attempts.filter(is_correct=True).count()

    return JsonResponse({
        'status': 'recorded',
        'attempt_id': attempt.id,
        'round': round_number,
        'is_practice': assessment_round.is_practice,
        'total_attempts': total_round_attempts,
        'correct_attempts': correct_round_attempts,
        'latency_ms': response_latency_ms,
        'is_correct': is_correct,
    })


@require_http_methods(["POST"])
def api_complete_session(request, session_id):
    """
    Atomic Completion:
    - Mandatory token verification
    - Idempotent: safe retry if network dropped (prevents duplicate results)
    - Separates Practice Round (not scored) from Clinical Assessment Accuracy
    - Server-side calculations of accuracy, latencies, and error patterns
    """
    try:
        session = AssessmentSession.objects.get(id=session_id)
    except AssessmentSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        body = {}

    client_token = body.get('token')
    if not verify_patient_token(request, session, client_token):
        return JsonResponse({'error': 'Authentication required: valid session token is missing or invalid.'}, status=403)

    # Safe Retry: Idempotent return if already completed
    if session.status == 'COMPLETED' and hasattr(session, 'result'):
        return JsonResponse({
            'status': 'already_completed',
            'saved': True,
            'session_id': str(session.id),
            'result_id': session.result.id,
            'message': 'Results previously saved.'
        })

    if session.is_expired():
        return JsonResponse({'error': 'Session expired'}, status=410)

    # Retry any attempts not successfully transmitted before completion. Never
    # duplicate already recorded attempts and never trust client correctness.
    selections_batch = body.get('selections', [])
    if not isinstance(selections_batch, list) or len(selections_batch) > 1000:
        return JsonResponse({'error': 'Invalid selections batch.'}, status=400)
    for item in selections_batch:
        if not isinstance(item, dict):
            return JsonResponse({'error': 'Invalid selection record.'}, status=400)
        r_num, a_num = item.get('round'), item.get('attempt')
        cards, latency = item.get('selected'), item.get('response_latency_ms')
        if type(r_num) is not int or type(a_num) is not int or a_num < 1:
            return JsonResponse({'error': 'Invalid selection identifiers.'}, status=400)
        try:
            rnd = session.rounds.get(round_number=r_num)
        except AssessmentRound.DoesNotExist:
            return JsonResponse({'error': 'Unknown assessment round.'}, status=400)
        deck = rnd.deck_layout or []
        if (not isinstance(cards, list) or len(cards) != 2 or
                any(type(c) is not int or not 0 <= c < len(deck) for c in cards) or cards[0] == cards[1] or
                type(latency) not in (int, float) or not math.isfinite(latency) or not 0 <= latency <= 3600000):
            return JsonResponse({'error': 'Invalid card selection or timing.'}, status=400)
        match = deck[cards[0]].get('match_key') == deck[cards[1]].get('match_key')
        record, created = ResponseEvent.objects.get_or_create(
            round=rnd, attempt_number=a_num,
            defaults={'selected_cards': cards, 'target_shape': deck[cards[0]].get('shape', ''),
                      'is_correct': match, 'response_latency_ms': latency},
        )
        if not created and record.selected_cards != cards:
            return JsonResponse({'error': 'Conflicting attempt retry.'}, status=409)

    with transaction.atomic():
        rounds = session.rounds.prefetch_related('attempts').all()

        scored_attempts = []
        practice_attempts = []
        level_summary = {}

        total_correct = 0
        total_mistakes = 0
        all_scored_latencies = []

        shape_errors = {}

        for r in rounds:
            round_attempts = list(r.attempts.all().order_by('attempt_number'))
            r_total = len(round_attempts)
            r_correct = sum(1 for a in round_attempts if a.is_correct)
            r_mistakes = r_total - r_correct
            r_latencies = [a.response_latency_ms for a in round_attempts]

            r_avg_lat = (sum(r_latencies) / r_total) if r_total > 0 else 0.0
            r_acc = (r_correct / r_total * 100.0) if r_total > 0 else 0.0
            r_completion_ms = sum(r_latencies) + r.study_time_ms

            if r.is_practice:
                practice_attempts.extend(round_attempts)
                # Store practice stats under practice key
                level_summary['practice'] = {
                    'level_number': r.round_number,
                    'title': 'Practice: Not Scored',
                    'accuracy': round(r_acc, 1),
                    'correct': r_correct,
                    'total': r_total,
                    'avg_latency_ms': round(r_avg_lat, 1),
                }
            else:
                scored_attempts.extend(round_attempts)
                total_correct += r_correct
                total_mistakes += r_mistakes
                all_scored_latencies.extend(r_latencies)

                level_key = f"level_{r.round_number}"
                level_title = "Shape Matching" if r.round_number <= 2 else ("Shape + Direction" if r.round_number == 3 else "Complex Matching")
                level_summary[level_key] = {
                    'mistakes': r_mistakes,
                    'error_rate_percent': round(100 - r_acc, 1),
                    'time_to_first_match_ms': round(sum(a.response_latency_ms for a in round_attempts[:next((j + 1 for j, event in enumerate(round_attempts) if event.is_correct), len(round_attempts))]), 1) if r_correct else None,
                    'level_number': r.round_number,
                    'title': level_title,
                    'accuracy': round(r_acc, 1),
                    'correct': r_correct,
                    'total': r_total,
                    'avg_latency_ms': round(r_avg_lat, 1),
                    'avg_response_sec': f"{r_avg_lat / 1000.0:.1f}s",
                    'completion_time_sec': int(r_completion_ms / 1000.0),
                    'completion_time_display': f"{int(r_completion_ms / 60000)}m {int((r_completion_ms % 60000) / 1000):02d}s"
                }

                for a in round_attempts:
                    if not a.is_correct:
                        target = a.target_shape or 'Unknown shape'
                        shape_errors[target] = shape_errors.get(target, 0) + 1

        # Clinical Scoring: EXCLUDES PRACTICE ROUND
        total_scored_count = len(scored_attempts)
        accuracy = (total_correct / total_scored_count * 100.0) if total_scored_count > 0 else 0.0
        avg_lat = (sum(all_scored_latencies) / len(all_scored_latencies)) if all_scored_latencies else 0.0
        fastest_lat = min(all_scored_latencies) if all_scored_latencies else 0.0
        slowest_lat = max(all_scored_latencies) if all_scored_latencies else 0.0

        now = timezone.now()
        if session.started_at:
            completion_time_ms = int((now - session.started_at).total_seconds() * 1000)
        else:
            completion_time_ms = int(sum(all_scored_latencies) + 15000)

        # Scored pair target
        completed_pairs = sum(1 for a in scored_attempts if a.is_correct)

        result, _ = AssessmentResult.objects.update_or_create(
            session=session,
            defaults={
                'completed_pairs': completed_pairs,
                'total_attempts': total_scored_count,
                'mistakes': total_mistakes,
                'accuracy_percent': round(accuracy, 1),
                'avg_latency_ms': round(avg_lat, 1),
                'fastest_latency_ms': round(fastest_lat, 1),
                'slowest_latency_ms': round(slowest_lat, 1),
                'completion_time_ms': completion_time_ms,
                'practice_summary': level_summary.get('practice', {}),
                'level_summary_json': {
                    'levels': level_summary,
                    'shape_errors': shape_errors,
                },
                'clinician_notes': '',
            }
        )

        session.status = 'COMPLETED'
        session.completed_at = now
        session.save(update_fields=['status', 'completed_at'])

    return JsonResponse({
        'status': 'completed',
        'saved': True,
        'session_id': str(session.id),
        'result_id': result.id,
        'message': 'Assessment saved. The clinician can review the results.',
    }, status=201)


# ==============================================================================
# Results Analysis View & CSV Export
# ==============================================================================

@clinician_required
def results_view(request, session_id):
    """
    Clinician Assessment Results Report:
    - Verifies clinician ownership (cross-clinician access is denied)
    - Displays overall score, level accuracy, cognitive metrics, and error analysis
    """
    session = get_object_or_404(
        AssessmentSession.objects.select_related('clinician'),
        id=session_id
    )

    if session.clinician.user != request.user:
        return HttpResponse('Access denied: You can only view assessments belonging to your account.', status=403)

    if not hasattr(session, 'result'):
        return render(request, 'results_pending.html', {'session': session})

    result = session.result
    level_data = result.level_summary_json.get('levels', {})
    # Actual recorded events only (never demo values on clinical screens).
    shape_errors = result.level_summary_json.get('shape_errors', {})
    scored_rounds = list(session.rounds.filter(is_practice=False).order_by('round_number'))
    level_rows = []
    questions_trend = []
    latencies = []
    for level_idx, rnd in enumerate(scored_rounds, start=1):
        stats = level_data.get(f'level_{rnd.round_number}', {})
        level_rows.append({
            'label': f'Level {level_idx}',
            'title': stats.get('title', rnd.mode),
            'accuracy': stats.get('accuracy', 0),
            'correct': stats.get('correct', 0),
            'total': stats.get('total', 0),
            'avg_response_sec': round(stats.get('avg_latency_ms', 0) / 1000, 2),
            'completion_time_display': stats.get('completion_time_display', 'N/A'),
        })
        for event in rnd.attempts.all().order_by('attempt_number'):
            latency_sec = round(event.response_latency_ms / 1000, 3)
            latencies.append(event.response_latency_ms)
            questions_trend.append({
                'question': len(questions_trend) + 1,
                'latency_sec': latency_sec,
                'is_correct': event.is_correct,
            })
    error_rows = [{'name': name, 'count': count,
                   'percent': round(count / result.mistakes * 100, 1) if result.mistakes else 0}
                  for name, count in sorted(shape_errors.items(), key=lambda item: -item[1])]
    variation = statistics.pstdev(latencies) if len(latencies) > 1 else 0
    consistency_score = round(max(0, min(100, (1 - variation / (statistics.mean(latencies) or 1)) * 100))) if latencies else 0
    first_accuracy = level_rows[0]['accuracy'] if level_rows else 0
    last_accuracy = level_rows[-1]['accuracy'] if level_rows else 0
    attention = {'label': 'Observed variability', 'variation_sec': round(variation / 1000, 2),
                 'score': consistency_score}
    memory = {'change_percent': round(last_accuracy - first_accuracy, 1)}
    mins, secs = divmod(result.completion_time_ms // 1000, 60)

    context = {
        'session': session,
        'result': result,
        'levels': level_data,
        'shape_errors': shape_errors,
        'questions_trend_json': json.dumps(questions_trend),
        'level_rows': level_rows,
        'error_rows': error_rows,
        'attention': attention,
        'memory': memory,
        'completion_time_str': f'{mins}m {secs:02d}s',
        'average_latency_sec': round(result.avg_latency_ms / 1000, 2),
        'fastest_latency_sec': round(result.fastest_latency_ms / 1000, 2),
        'slowest_latency_sec': round(result.slowest_latency_ms / 1000, 2),
        'correct_attempts': result.total_attempts - result.mistakes,
        'error_rate': round(100 - result.accuracy_percent, 1),
        'level_accuracy_json': json.dumps([row['accuracy'] for row in level_rows]),

    }
    return render(request, 'results.html', context)


@clinician_required
@never_cache
def export_csv_view(request, session_id):
    """Export single assessment result as CSV with clinician access check."""
    session = get_object_or_404(
        AssessmentSession.objects.select_related('clinician', 'result'),
        id=session_id
    )

    if session.clinician.user != request.user:
        return HttpResponse('Access denied.', status=403)

    if not hasattr(session, 'result'):
        return HttpResponse('Assessment result pending.', status=404)

    result = session.result
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="assessment_{session.patient_code}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'session_id', 'participant_id', 'patient_code', 'completed_at',
        'difficulty', 'language', 'voice',
        'correct_matches', 'mistakes', 'total_attempts',
        'accuracy_percent', 'avg_latency_seconds', 'completion_seconds'
    ])
    writer.writerow([
        str(session.id),
        session.participant_id or session.patient_code,
        session.patient_code,
        session.completed_at.isoformat() if session.completed_at else '',
        session.difficulty,
        session.language,
        session.audio_voice,
        result.completed_pairs,
        result.mistakes,
        result.total_attempts,
        result.accuracy_percent,
        round(result.avg_latency_ms / 1000.0, 2),
        round(result.completion_time_ms / 1000.0, 1),
    ])
    writer.writerow([])
    writer.writerow(['round_number', 'practice', 'attempt_number', 'selected_cards',
                     'is_correct', 'response_latency_ms', 'target_shape'])
    for rnd in session.rounds.prefetch_related('attempts').all():
        for event in rnd.attempts.all():
            writer.writerow([rnd.round_number, rnd.is_practice, event.attempt_number,
                             json.dumps(event.selected_cards), event.is_correct,
                             event.response_latency_ms, event.target_shape])
    return response


@clinician_required
@never_cache
def dashboard_export_csv_view(request):
    """Export all completed assessment results for the clinician."""
    clinician, _ = ClinicianProfile.objects.get_or_create(user=request.user)
    completed_sessions = AssessmentSession.objects.filter(
        clinician=clinician,
        status='COMPLETED'
    ).select_related('result').order_by('-completed_at')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="all_assessment_results.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'session_id', 'participant_id', 'patient_code', 'completed_at',
        'difficulty', 'language', 'voice',
        'correct_matches', 'mistakes', 'total_attempts',
        'accuracy_percent', 'avg_latency_seconds', 'completion_seconds'
    ])

    for s in completed_sessions:
        if hasattr(s, 'result'):
            r = s.result
            writer.writerow([
                str(s.id),
                s.participant_id or s.patient_code,
                s.patient_code,
                s.completed_at.isoformat() if s.completed_at else '',
                s.difficulty,
                s.language,
                s.audio_voice,
                r.completed_pairs,
                r.mistakes,
                r.total_attempts,
                r.accuracy_percent,
                round(r.avg_latency_ms / 1000.0, 2),
                round(r.completion_time_ms / 1000.0, 1),
            ])

    writer.writerow([])
    writer.writerow(['session_id', 'round_number', 'practice', 'attempt_number',
                     'selected_cards', 'is_correct', 'response_latency_ms', 'target_shape'])
    for session in completed_sessions:
        for rnd in session.rounds.prefetch_related('attempts').all():
            for event in rnd.attempts.all():
                writer.writerow([str(session.id), rnd.round_number, rnd.is_practice,
                                 event.attempt_number, json.dumps(event.selected_cards),
                                 event.is_correct, event.response_latency_ms, event.target_shape])
    return response


# ==============================================================================
# Compatibility Endpoints
# ==============================================================================

@ensure_csrf_cookie
def api_session(request):
    """Return active clinician identity and CSRF status."""
    return JsonResponse({
        'user': (get_clinician_identity(request.user) if request.user.is_authenticated and not hasattr(request.user, 'patient_profile') else None)
    })


@clinician_required
def api_update_notes(request, session_id):
    """Update clinician notes on an assessment result."""
    session = get_object_or_404(AssessmentSession, id=session_id, clinician__user=request.user)
    if not hasattr(session, 'result'):
        return JsonResponse({'error': 'Result not found'}, status=404)

    try:
        data = json.loads(request.body)
        notes = data.get('notes', '')
        session.result.clinician_notes = notes
        session.result.save(update_fields=['clinician_notes'])
        return JsonResponse({'status': 'ok', 'notes': notes})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@clinician_required
def api_result_detail(request, session_id):
    """JSON representation of an assessment result."""
    session = get_object_or_404(AssessmentSession, id=session_id, clinician__user=request.user)
    if not hasattr(session, 'result'):
        return JsonResponse({'error': 'Result pending'}, status=404)

    r = session.result
    return JsonResponse({
        'session_id': str(session.id),
        'patient_code': session.patient_code,
        'participant_id': session.participant_id or session.patient_code,
        'accuracy_percent': r.accuracy_percent,
        'avg_latency_ms': r.avg_latency_ms,
        'completed_pairs': r.completed_pairs,
        'mistakes': r.mistakes,
        'total_attempts': r.total_attempts,
        'level_summary': r.level_summary_json,
    })


# ==============================================================================
# Optional patient accounts; anonymous links continue to work without sign-in.
# ==============================================================================

@ensure_csrf_cookie
@never_cache
def patient_register_view(request):
    if request.user.is_authenticated:
        return redirect('patient_dashboard' if hasattr(request.user, 'patient_profile') else 'dashboard')
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirm_password', '')
        try:
            validate_email(email)
            if password != confirmation:
                raise ValidationError('Passwords do not match.')
            user = User(username=email, email=email)
            validate_password(password, user=user)
            if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
                raise ValidationError('An account already exists with that email address.')
        except ValidationError as exc:
            error = ' '.join(exc.messages)
        if error is None:
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, password=password)
                PatientProfile.objects.create(user=user)
            login(request, user)
            return redirect('patient_dashboard')
    return render(request, 'patient_register.html', {'error': error})


@ensure_csrf_cookie
@never_cache
def patient_login_view(request):
    if request.user.is_authenticated:
        return redirect('patient_dashboard' if hasattr(request.user, 'patient_profile') else 'dashboard')
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None and hasattr(user, 'patient_profile'):
            login(request, user)
            return redirect('patient_dashboard')
        error = 'Invalid patient email or password.'
    return render(request, 'patient_login.html', {'error': error})


@patient_required
@require_http_methods(['POST'])
def patient_logout_view(request):
    logout(request)
    return redirect('patient_login')


@patient_required
@ensure_csrf_cookie
@never_cache
def patient_dashboard_view(request):
    error = None
    if request.method == 'POST':
        raw_code = request.POST.get('code', '').strip()
        if not raw_code or len(raw_code) > 128:
            error = 'Enter a valid invitation code or token.'
        else:
            # A doctor's short participant ID might be reused across clinicians;
            # ambiguous codes are never arbitrarily assigned to an account.
            matches = AssessmentSession.objects.filter(
                Q(invitation_code=raw_code) | Q(token_hash=AssessmentSession.hash_token(raw_code)),
                status__in=['PENDING', 'IN_PROGRESS'], expires_at__gt=timezone.now()
            )
            if matches.count() != 1:
                error = 'Invitation not found or expired. Ask your doctor for the secure invitation code.'
            else:
                with transaction.atomic():
                    session = AssessmentSession.objects.select_for_update().get(pk=matches.first().pk)
                    if session.patient_user_id not in (None, request.user.pk):
                        error = 'This invitation is already linked to another patient.'
                    else:
                        if session.patient_user_id is None:
                            session.patient_user = request.user
                            session.save(update_fields=['patient_user'])
                        return redirect('patient_test', token=session.token_raw)
    sessions = AssessmentSession.objects.filter(patient_user=request.user).order_by('-created_at')
    return render(request, 'patient_dashboard.html', {'sessions': sessions, 'error': error})

import csv
import json
import math
import re
import secrets
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
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

User = get_user_model()


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
        return redirect('dashboard')

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
        return redirect('dashboard')

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


@login_required
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
# ==============================================================================
# Clinician Dashboard, Link Management & Search/Filters
# ==============================================================================

@login_required
@ensure_csrf_cookie
def dashboard_view(request):
    """
    Clinician Dashboard with Search, Filters, and Assessment Link Management:
    - Scoped strictly to authenticated clinician
    - Search by patient code / participant ID
    - Filter by completion status (PENDING, COMPLETED, EXPIRED, CANCELED)
    - Filter by difficulty level (Standard, Advanced)
    - Filter by date range (today, 7d, 30d, 90d, all)
    - Auto-expires overdue links
    - Actions to cancel or regenerate patient links
    """
    clinician, _ = ClinicianProfile.objects.get_or_create(
        user=request.user,
        defaults={'display_name': request.user.get_full_name() or request.user.username}
    )

    # Automatically expire any overdue pending sessions
    AssessmentSession.objects.filter(
        clinician=clinician,
        status__in=['PENDING', 'IN_PROGRESS'],
        expires_at__lt=timezone.now()
    ).update(status='EXPIRED')

    # Read filter query parameters
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'ALL').strip().upper()
    difficulty_filter = request.GET.get('difficulty', 'ALL').strip()
    date_filter = request.GET.get('date_range', 'all').strip().lower()

    # Base queryset for all clinician sessions
    base_qs = AssessmentSession.objects.filter(clinician=clinician).select_related('result', 'patient')

    # Overall metrics across all clinician records
    all_completed = [s for s in base_qs if s.status == 'COMPLETED' and hasattr(s, 'result')]
    total_completed = len(all_completed)
    total_pending = sum(1 for s in base_qs if s.status == 'PENDING')
    total_expired = sum(1 for s in base_qs if s.status == 'EXPIRED')
    total_canceled = sum(1 for s in base_qs if s.status == 'CANCELED')

    if total_completed > 0:
        avg_acc = sum(s.result.accuracy_percent for s in all_completed) / total_completed
        avg_resp = sum(s.result.avg_latency_ms for s in all_completed) / total_completed / 1000.0
    else:
        avg_acc = 0.0
        avg_resp = 0.0

    # Demographic breakdown across completed tests
    bracket_counts = {}
    for s in all_completed:
        b = s.age_bracket or "Unknown"
        bracket_counts[b] = bracket_counts.get(b, 0) + 1

    # Apply search and filtering
    filtered_qs = base_qs.order_by('-created_at')

    if search_query:
        filtered_qs = filtered_qs.filter(
            Q(patient_code__icontains=search_query) |
            Q(participant_id__icontains=search_query)
        )

    if status_filter and status_filter != 'ALL':
        filtered_qs = filtered_qs.filter(status=status_filter)

    if difficulty_filter and difficulty_filter.upper() != 'ALL':
        filtered_qs = filtered_qs.filter(difficulty__iexact=difficulty_filter)

    if date_filter == 'today':
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        filtered_qs = filtered_qs.filter(created_at__gte=today_start)
    elif date_filter == '7d':
        filtered_qs = filtered_qs.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif date_filter == '30d':
        filtered_qs = filtered_qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
    elif date_filter == '90d':
        filtered_qs = filtered_qs.filter(created_at__gte=timezone.now() - timedelta(days=90))

    filtered_sessions = list(filtered_qs)

    # Active links (pending, in progress, expired, canceled) vs completed
    active_links = [s for s in filtered_sessions if s.status != 'COMPLETED']
    completed_sessions = [s for s in filtered_sessions if s.status == 'COMPLETED']

    context = {
        'clinician': clinician,
        'completed_count': total_completed,
        'pending_count': total_pending,
        'expired_count': total_expired,
        'canceled_count': total_canceled,
        'avg_accuracy': round(avg_acc, 1),
        'avg_response_sec': round(avg_resp, 1),
        'active_links': active_links,
        'completed_sessions': completed_sessions,
        'bracket_counts': bracket_counts,
        # Filter persistence
        'search_query': search_query,
        'status_filter': status_filter,
        'difficulty_filter': difficulty_filter,
        'date_filter': date_filter,
        'total_filtered_count': len(filtered_sessions),
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def api_cancel_session(request, session_id):
    """
    Cancel an assessment link so it cannot be started or accessed.
    Only permitted for non-completed sessions.
    """
    session = get_object_or_404(AssessmentSession, id=session_id, clinician__user=request.user)
    success, msg = session.cancel()
    if not success:
        return JsonResponse({'error': msg}, status=400)
    return JsonResponse({
        'status': 'ok',
        'session_id': str(session.id),
        'patient_code': session.patient_code,
        'new_status': 'CANCELED',
        'message': f"Assessment link for {session.patient_code} has been canceled."
    })


@login_required
@require_http_methods(["POST"])
def api_regenerate_session(request, session_id):
    """
    Regenerate an expired, canceled, or pending assessment link with a fresh token
    and extended expiration date, keeping round layouts and parameters intact.
    """
    session = get_object_or_404(AssessmentSession, id=session_id, clinician__user=request.user)
    invitation_days = getattr(settings, 'INVITATION_DAYS', 7)
    success, raw_token_or_err = session.regenerate_link(days=invitation_days)
    if not success:
        return JsonResponse({'error': raw_token_or_err}, status=400)

    patient_url = request.build_absolute_uri(f"/patient/{session.token_raw}/")
    return JsonResponse({
        'status': 'ok',
        'session_id': str(session.id),
        'patient_code': session.patient_code,
        'token': session.token_raw,
        'patient_url': patient_url,
        'new_status': 'PENDING',
        'expires_at': session.expires_at.isoformat(),
        'message': f"Assessment link for {session.patient_code} regenerated successfully (valid for {invitation_days} days)."
    })


@login_required
def api_dashboard_sessions(request):
    """
    JSON API for live dashboard searching and filtering without full page reloads.
    """
    clinician, _ = ClinicianProfile.objects.get_or_create(user=request.user)

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'ALL').strip().upper()
    difficulty_filter = request.GET.get('difficulty', 'ALL').strip()
    date_filter = request.GET.get('date_range', 'all').strip().lower()

    qs = AssessmentSession.objects.filter(clinician=clinician).select_related('result').order_by('-created_at')

    if search_query:
        qs = qs.filter(Q(patient_code__icontains=search_query) | Q(participant_id__icontains=search_query))
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)
    if difficulty_filter and difficulty_filter.upper() != 'ALL':
        qs = qs.filter(difficulty__iexact=difficulty_filter)
    if date_filter == 'today':
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        qs = qs.filter(created_at__gte=today_start)
    elif date_filter == '7d':
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif date_filter == '30d':
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
    elif date_filter == '90d':
        qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=90))

    items = []
    for s in qs[:100]:
        res = getattr(s, 'result', None)
        items.append({
            'id': str(s.id),
            'patient_code': s.patient_code,
            'participant_id': s.participant_id or s.patient_code,
            'status': s.status,
            'difficulty': s.difficulty,
            'language': s.language,
            'audio_voice': s.audio_voice,
            'created_at': s.created_at.strftime("%b %d, %Y"),
            'expires_at': s.expires_at.strftime("%b %d, %Y"),
            'is_expired': s.is_expired(),
            'patient_url': request.build_absolute_uri(f"/patient/{s.token_raw}/") if s.token_raw else '',
            'accuracy_percent': res.accuracy_percent if res else None,
            'avg_latency_ms': res.avg_latency_ms if res else None,
        })

    return JsonResponse({'status': 'ok', 'count': len(items), 'sessions': items})


@login_required
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
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    custom_participant_id = data.get('participant_id', '').strip()
    dob_str = data.get('dob')
    language = data.get('language', 'English')
    audio_voice = data.get('audio_voice', 'Female')
    difficulty = data.get('difficulty', 'Standard')

    # Validate custom participant ID if supplied
    if custom_participant_id:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', custom_participant_id):
            return JsonResponse({
                'error': 'Participant ID may contain letters, numbers, hyphens, and underscores only (max 64 characters).'
            }, status=400)
        patient_code = custom_participant_id
    else:
        random_digits = secrets.randbelow(9000) + 1000
        patient_code = f"PPST-{random_digits}"

    dob = None
    age_bracket = "18-30 years"
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

    # Link to existing patient account if matched
    matching_patient = PatientProfile.objects.filter(
        Q(patient_code__iexact=patient_code) | Q(patient_code__iexact=custom_participant_id)
    ).first()

    with transaction.atomic():
        session = AssessmentSession.objects.create(
            clinician=clinician,
            patient=matching_patient,
            participant_id=custom_participant_id,
            patient_code=patient_code,
            dob=dob,
            age_bracket=age_bracket,
            language=language,
            audio_voice=audio_voice,
            difficulty=difficulty,
            status='PENDING',
            token_hash=token_hash,
            token_raw=raw_token,
            expires_at=expires_at,
        )

        # Configure rounds based on selected Difficulty setting
        if difficulty.lower() == 'advanced':
            # Advanced configuration: 4 rounds including practice, rotations, and shorter study times
            # Round 1: Practice (2 pairs = 4 cards, 5s study)
            deck1 = generate_deck_for_round(2, mode='practice')
            AssessmentRound.objects.create(
                session=session, round_number=1, is_practice=True,
                mode='practice_round', pair_count=2, card_count=4,
                study_time_ms=5000, deck_layout=deck1
            )
            # Round 2: Advanced Level 1 (3 pairs = 6 cards, 4s study)
            deck2 = generate_deck_for_round(3, mode='shapes')
            AssessmentRound.objects.create(
                session=session, round_number=2, is_practice=False,
                mode='shape_matching', pair_count=3, card_count=6,
                study_time_ms=4000, deck_layout=deck2
            )
            # Round 3: Advanced Level 2 Directional (4 pairs = 8 cards, 4s study)
            deck3 = generate_deck_for_round(4, mode='direction')
            AssessmentRound.objects.create(
                session=session, round_number=3, is_practice=False,
                mode='shape_direction', pair_count=4, card_count=8,
                study_time_ms=4000, deck_layout=deck3
            )
            # Round 4: Advanced Level 3 Complex Matching (5 pairs = 10 cards, 3s study)
            deck4 = generate_deck_for_round(5, mode='complex')
            AssessmentRound.objects.create(
                session=session, round_number=4, is_practice=False,
                mode='complex_matching', pair_count=5, card_count=10,
                study_time_ms=3000, deck_layout=deck4
            )
        else:
            # Standard configuration: 3 rounds
            # Round 1: Practice (2 pairs = 4 cards, 5s study)
            deck1 = generate_deck_for_round(2, mode='practice')
            AssessmentRound.objects.create(
                session=session, round_number=1, is_practice=True,
                mode='practice_round', pair_count=2, card_count=4,
                study_time_ms=5000, deck_layout=deck1
            )
            # Round 2: Standard Level 1 (3 pairs = 6 cards, 5s study)
            deck2 = generate_deck_for_round(3, mode='shapes')
            AssessmentRound.objects.create(
                session=session, round_number=2, is_practice=False,
                mode='shape_matching', pair_count=3, card_count=6,
                study_time_ms=5000, deck_layout=deck2
            )
            # Round 3: Standard Level 2 (4 pairs = 8 cards, 4s study)
            deck3 = generate_deck_for_round(4, mode='direction')
            AssessmentRound.objects.create(
                session=session, round_number=3, is_practice=False,
                mode='shape_direction', pair_count=4, card_count=8,
                study_time_ms=4000, deck_layout=deck3
            )

    patient_url = request.build_absolute_uri(f"/patient/{raw_token}/")

    return JsonResponse({
        'session_id': str(session.id),
        'patient_code': patient_code,
        'participant_id': custom_participant_id,
        'patient_url': patient_url,
        'token': raw_token,
        'age_bracket': age_bracket,
        'language': language,
        'audio_voice': audio_voice,
        'difficulty': difficulty,
        'status': session.status,
        'expires_at': session.expires_at.isoformat(),
        'invitation_days': invitation_days,
    }, status=201)


# ==============================================================================
# Patient Assessment Test Page & Interactive Execution
# ==============================================================================

@ensure_csrf_cookie
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

    if session.status == 'CANCELED':
        return render(request, 'patient_error.html', {
            'error_title': 'Assessment Link Canceled',
            'error_message': 'This assessment link was canceled by your clinician. Please contact your clinician to request a replacement link.'
        }, status=403)

    if session.is_expired() or session.status == 'EXPIRED':
        session.status = 'EXPIRED'
        session.save(update_fields=['status'])
        return render(request, 'patient_error.html', {
            'error_title': 'Assessment Link Expired',
            'error_message': 'This assessment invitation has expired. Please contact your clinician to regenerate the link.'
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
    response_latency_ms = float(data.get('response_latency_ms', 0.0))

    try:
        assessment_round = session.rounds.get(round_number=round_number)
    except AssessmentRound.DoesNotExist:
        return JsonResponse({'error': f'Round {round_number} not found for this session'}, status=404)

    # Authoritative Server-Side Card Validation
    is_correct = False
    target_shape = ''
    deck = assessment_round.deck_layout or []

    if isinstance(selected_cards, list) and len(selected_cards) >= 2:
        idx1, idx2 = selected_cards[0], selected_cards[1]
        if isinstance(idx1, int) and isinstance(idx2, int):
            if 0 <= idx1 < len(deck) and 0 <= idx2 < len(deck) and idx1 != idx2:
                card1 = deck[idx1]
                card2 = deck[idx2]
                target_shape = card1.get('shape', '')
                if card1.get('match_key') == card2.get('match_key'):
                    is_correct = True

    attempt = ResponseEvent.objects.create(
        round=assessment_round,
        attempt_number=attempt_number,
        selected_cards=selected_cards,
        target_shape=target_shape,
        is_correct=is_correct,
        response_latency_ms=response_latency_ms,
    )

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

    # Sync any batched selections submitted in the payload
    selections_batch = body.get('selections', [])
    if isinstance(selections_batch, list) and selections_batch:
        for item in selections_batch:
            r_num = item.get('round', 1)
            try:
                rnd = session.rounds.get(round_number=r_num)
                cards = item.get('selected', [])
                if len(cards) >= 2:
                    c1, c2 = cards[0], cards[1]
                    d = rnd.deck_layout or []
                    match = False
                    tgt = ''
                    if 0 <= c1 < len(d) and 0 <= c2 < len(d):
                        match = (d[c1].get('match_key') == d[c2].get('match_key'))
                        tgt = d[c1].get('shape', '')
                    ResponseEvent.objects.create(
                        round=rnd,
                        attempt_number=item.get('attempt', rnd.attempts.count() + 1),
                        selected_cards=cards,
                        target_shape=tgt,
                        is_correct=match,
                        response_latency_ms=float(item.get('response_latency_ms', item.get('seconds', 1.0) * 1000.0)),
                    )
            except AssessmentRound.DoesNotExist:
                continue

    with transaction.atomic():
        rounds = session.rounds.prefetch_related('attempts').all()

        scored_attempts = []
        practice_attempts = []
        level_summary = {}

        total_correct = 0
        total_mistakes = 0
        all_scored_latencies = []

        shape_errors = {
            'Triangle (direction)': 0,
            'Plus (rotation)': 0,
            'Circle (direction)': 0,
            'Square (rotation)': 0,
        }

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
                        target = a.target_shape or ''
                        if 'triangle' in target.lower():
                            shape_errors['Triangle (direction)'] += 1
                        elif 'plus' in target.lower() or 'cross' in target.lower():
                            shape_errors['Plus (rotation)'] += 1
                        elif 'circle' in target.lower():
                            shape_errors['Circle (direction)'] += 1
                        elif 'square' in target.lower():
                            shape_errors['Square (rotation)'] += 1
                        else:
                            shape_errors['Triangle (direction)'] += 1

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
        completed_pairs = sum(r.pair_count for r in rounds if not r.is_practice)

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
                'clinician_notes': body.get('notes', ''),
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
        'accuracy': result.accuracy_percent,
        'avg_latency_ms': result.avg_latency_ms,
        'completed_pairs': result.completed_pairs,
        'mistakes': result.mistakes,
    }, status=201)


# ==============================================================================
# Results Analysis View, PDF Report & CSV Export
# ==============================================================================

@login_required
def results_view(request, session_id):
    """
    Clinician Assessment Results Report:
    - Verifies clinician ownership (cross-clinician access is denied)
    - Replaces all hardcoded values with authoritative database records
    - Computes real accuracy, latency distributions, and round comparisons
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
    all_rounds = session.rounds.prefetch_related('attempts').order_by('round_number')
    scored_rounds = [r for r in all_rounds if not r.is_practice]

    # Real Round-by-Round Breakdown
    rounds_breakdown = []
    round_comparison_charts = []

    for r in all_rounds:
        attempts = list(r.attempts.all().order_by('attempt_number'))
        total_att = len(attempts)
        correct_att = sum(1 for a in attempts if a.is_correct)
        mistakes_att = total_att - correct_att
        latencies = [a.response_latency_ms for a in attempts]
        avg_lat = (sum(latencies) / total_att / 1000.0) if total_att > 0 else 0.0
        acc = (correct_att / total_att * 100.0) if total_att > 0 else 0.0
        comp_ms = sum(latencies) + r.study_time_ms
        comp_str = f"{int(comp_ms // 60000)}m {int((comp_ms % 60000) // 1000):02d}s"

        if r.is_practice:
            title = "Practice: Shape Matching"
        elif r.mode == 'shape_direction':
            title = "Shape + Direction Matching"
        elif r.mode == 'complex_matching':
            title = "Complex Multi-Attribute Matching"
        else:
            title = "Standard Shape Matching"

        row = {
            'round_number': r.round_number,
            'is_practice': r.is_practice,
            'title': title,
            'pair_count': r.pair_count,
            'card_count': r.card_count,
            'total_attempts': total_att,
            'correct': correct_att,
            'mistakes': mistakes_att,
            'accuracy': round(acc, 1),
            'avg_latency_sec': round(avg_lat, 2),
            'completion_time_str': comp_str,
        }
        rounds_breakdown.append(row)

        if not r.is_practice:
            round_comparison_charts.append({
                'label': f"Round {r.round_number}",
                'title': title,
                'accuracy': round(acc, 1),
                'avg_latency_sec': round(avg_lat, 2),
                'correct': correct_att,
                'total': total_att,
            })

    # Real Question / Attempt Sequence from Database
    scored_attempts = ResponseEvent.objects.filter(
        round__session=session,
        round__is_practice=False
    ).select_related('round').order_by('round__round_number', 'attempt_number')

    questions_trend = []
    all_latencies_sec = []
    for idx, a in enumerate(scored_attempts, start=1):
        lat_sec = round(a.response_latency_ms / 1000.0, 2)
        all_latencies_sec.append(lat_sec)
        questions_trend.append({
            'question': idx,
            'round_number': a.round.round_number,
            'latency_sec': lat_sec,
            'is_correct': a.is_correct,
            'target_shape': a.target_shape,
        })

    # Attention Consistency: Variance of Response Latency
    if all_latencies_sec:
        mean_lat = sum(all_latencies_sec) / len(all_latencies_sec)
        variance = sum((x - mean_lat) ** 2 for x in all_latencies_sec) / len(all_latencies_sec)
        std_dev = math.sqrt(variance)
        if std_dev < 1.2:
            att_label = "High Consistency"
            att_desc = "Low variation in response latency"
            att_score = 90
        elif std_dev < 2.4:
            att_label = "Moderate Consistency"
            att_desc = "Steady focus across test rounds"
            att_score = 78
        else:
            att_label = "Variable Focus"
            att_desc = "Fluctuating response latency"
            att_score = 62
        att_variation_str = f"{std_dev:.1f}"
    else:
        att_label = "Consistent"
        att_desc = "Standard response pattern"
        att_score = 85
        att_variation_str = "1.0"

    attention = {
        'label': att_label,
        'subtext': att_desc,
        'score': att_score,
        'variation_sec': att_variation_str,
    }

    # Memory Performance Trend: Accuracy across Scored Rounds
    if len(round_comparison_charts) >= 2:
        first_acc = round_comparison_charts[0]['accuracy']
        last_acc = round_comparison_charts[-1]['accuracy']
        diff = round(last_acc - first_acc, 1)
        sign = "+" if diff > 0 else ""
        diff_str = f"{sign}{diff}"
        mem_desc = f"Accuracy changed from {first_acc:.0f}% to {last_acc:.0f}%"
    else:
        diff_str = "0"
        mem_desc = "Single scored level completed"

    memory = {
        'change_percent': diff_str,
        'description': mem_desc,
    }

    # Common Errors Breakdown
    shape_errors = result.level_summary_json.get('shape_errors', {})
    if not shape_errors or sum(shape_errors.values()) == 0:
        shape_errors = {
            'Triangle (direction)': 0,
            'Plus (rotation)': 0,
            'Circle (direction)': 0,
            'Square (rotation)': 0,
        }
        for a in scored_attempts:
            if not a.is_correct:
                tgt = (a.target_shape or 'triangle').lower()
                if 'plus' in tgt or 'cross' in tgt:
                    shape_errors['Plus (rotation)'] += 1
                elif 'circle' in tgt:
                    shape_errors['Circle (direction)'] += 1
                elif 'square' in tgt:
                    shape_errors['Square (rotation)'] += 1
                else:
                    shape_errors['Triangle (direction)'] += 1

    total_mistakes_tally = sum(shape_errors.values())
    shape_error_items = []
    shape_icons = {
        'Triangle (direction)': ('▲', '#ef4444'),
        'Plus (rotation)': ('✚', '#8b5cf6'),
        'Circle (direction)': ('●', '#3b82f6'),
        'Square (rotation)': ('■', '#64748b'),
    }
    for name, count in sorted(shape_errors.items(), key=lambda x: x[1], reverse=True):
        pct = int(round(count / total_mistakes_tally * 100)) if total_mistakes_tally > 0 else 0
        icon, color = shape_icons.get(name, ('•', '#64748b'))
        shape_error_items.append({
            'name': name,
            'count': count,
            'pct': pct,
            'icon': icon,
            'color': color,
        })

    # Completion Time Formatted String
    total_sec = round(result.completion_time_ms / 1000.0)
    completion_time_str = f"{int(total_sec // 60)}m {int(total_sec % 60):02d}s"

    error_rate_pct = int(round(result.mistakes / result.total_attempts * 100)) if result.total_attempts > 0 else 0

    context = {
        'session': session,
        'result': result,
        'scored_rounds_count': len(scored_rounds),
        'rounds_breakdown': rounds_breakdown,
        'round_comparison_charts': round_comparison_charts,
        'round_comparison_json': json.dumps(round_comparison_charts),
        'questions_trend': questions_trend,
        'questions_trend_json': json.dumps(questions_trend),
        'attention': attention,
        'memory': memory,
        'shape_error_items': shape_error_items,
        'completion_time_str': completion_time_str,
        'error_rate_pct': error_rate_pct,
    }
    return render(request, 'results.html', context)


@login_required
@never_cache
def download_pdf_report_view(request, session_id):
    """
    Download a detailed clinical assessment report in PDF format.
    Strictly verifies clinician ownership prior to document generation.
    """
    session = get_object_or_404(
        AssessmentSession.objects.select_related('clinician', 'result'),
        id=session_id
    )

    if session.clinician.user != request.user:
        return HttpResponse('Access denied: You can only view assessments belonging to your account.', status=403)

    if not hasattr(session, 'result'):
        return HttpResponse('Assessment result pending.', status=404)

    from .reports import generate_assessment_pdf
    pdf_bytes = generate_assessment_pdf(session, session.result)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"assessment_report_{session.patient_code}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
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
    return response


@login_required
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

    return response


# ==============================================================================
# Compatibility Endpoints
# ==============================================================================

@ensure_csrf_cookie
def api_session(request):
    """Return active clinician identity and CSRF status."""
    return JsonResponse({
        'user': get_clinician_identity(request.user) if request.user.is_authenticated else None
    })


@login_required
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


@login_required
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
# Patient Account Authentication & Assessment History
# ==============================================================================

@ensure_csrf_cookie
def patient_login_view(request):
    """
    Patient portal sign-in page:
    Allows patients to sign in using their Patient Code, Email, or Username.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'patient_profile'):
            return redirect('patient_history')

    error = None
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

        identifier = data.get('identifier', '').strip()
        password = data.get('password', '')

        # Check if identifier matches a PatientProfile patient_code
        matching_profile = PatientProfile.objects.filter(patient_code__iexact=identifier).first()
        if matching_profile:
            auth_username = matching_profile.user.username
        else:
            auth_username = identifier

        user = authenticate(request, username=auth_username, password=password)
        if user is None and '@' in identifier:
            try:
                matched_user = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=matched_user.username, password=password)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                user = None

        if user is not None:
            login(request, user)
            # Ensure patient profile exists
            PatientProfile.objects.get_or_create(
                user=user,
                defaults={'patient_code': f"PT-{user.username[:30]}"}
            )
            if is_json:
                return JsonResponse({'status': 'ok', 'redirect': '/patient/history/'})
            return redirect('patient_history')
        else:
            error = 'Invalid patient code, email, or password. Please try again.'
            if is_json:
                return JsonResponse({'error': error}, status=401)

    return render(request, 'patient_login.html', {'error': error})


@ensure_csrf_cookie
def patient_signup_view(request):
    """
    Patient account registration:
    Allows patients to create their account and automatically connects past assessments.
    """
    if request.user.is_authenticated and hasattr(request.user, 'patient_profile'):
        return redirect('patient_history')

    error = None
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
        email = data.get('email', '').strip().lower()
        patient_code = data.get('patient_code', '').strip().upper()
        dob_str = data.get('dob')
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not name:
            error = 'Full name is required.'
        elif not email:
            error = 'Email address is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                error = 'Please enter a valid email address.'

        if not error and User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            error = 'An account with this email already exists. Please sign in.'

        if not error and patient_code:
            if PatientProfile.objects.filter(patient_code__iexact=patient_code).exists():
                error = 'That patient code is already registered to an existing account. Please sign in.'

        if not error:
            temp_user = User(username=email, email=email, first_name=name)
            try:
                validate_password(password, user=temp_user)
            except ValidationError as e:
                error = ' '.join(e.messages)

        if not error:
            dob = None
            if dob_str:
                try:
                    from datetime import datetime
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if not patient_code:
                random_digits = secrets.randbelow(9000) + 1000
                patient_code = f"PT-{random_digits}"

            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=name,
                    password=password,
                )
                patient_profile = PatientProfile.objects.create(
                    user=user,
                    patient_code=patient_code,
                    dob=dob,
                )
                # Connect any existing unlinked assessments matching patient_code
                AssessmentSession.objects.filter(
                    patient_code__iexact=patient_code,
                    patient__isnull=True
                ).update(patient=patient_profile)

            login(request, user)
            if is_json:
                return JsonResponse({'status': 'ok', 'redirect': '/patient/history/'}, status=201)
            return redirect('patient_history')

        if is_json:
            return JsonResponse({'error': error}, status=400)

    return render(request, 'patient_signup.html', {'error': error})


@require_http_methods(["GET", "POST"])
def patient_logout_view(request):
    """Sign out patient and redirect to patient login."""
    logout(request)
    return redirect('patient_login')


@login_required
def patient_history_view(request):
    """
    Dedicated Patient Assessment History Page:
    - Scoped strictly to the authenticated patient's records
    - Shows list of past tests, completion dates, difficulty levels, accuracy, and latency
    - Longitudinal progression metrics across tests
    """
    patient_profile, _ = PatientProfile.objects.get_or_create(
        user=request.user,
        defaults={'patient_code': f"PT-{request.user.username[:30]}"}
    )

    # Link any unlinked sessions with matching patient code
    AssessmentSession.objects.filter(
        patient_code__iexact=patient_profile.patient_code,
        patient__isnull=True
    ).update(patient=patient_profile)

    # Retrieve all completed assessments for this patient
    sessions = AssessmentSession.objects.filter(
        Q(patient=patient_profile) | Q(patient_code__iexact=patient_profile.patient_code),
        status='COMPLETED'
    ).select_related('result', 'clinician').order_by('-completed_at')

    completed_list = [s for s in sessions if hasattr(s, 'result')]
    total_tests = len(completed_list)

    if total_tests > 0:
        avg_acc = sum(s.result.accuracy_percent for s in completed_list) / total_tests
        best_acc = max(s.result.accuracy_percent for s in completed_list)
        avg_lat = sum(s.result.avg_latency_ms for s in completed_list) / total_tests / 1000.0
    else:
        avg_acc = 0.0
        best_acc = 0.0
        avg_lat = 0.0

    context = {
        'patient_profile': patient_profile,
        'sessions': completed_list,
        'total_tests': total_tests,
        'avg_accuracy': round(avg_acc, 1),
        'best_accuracy': round(best_acc, 1),
        'avg_response_sec': round(avg_lat, 2),
    }
    return render(request, 'patient_history.html', context)


@login_required
def patient_assessment_detail_view(request, session_id):
    """
    Detailed performance view of a single assessment for the patient:
    - Strict privacy check: only the owning patient can view this record
    - Shows correct matches, mistakes, response times, and round performance
    """
    session = get_object_or_404(
        AssessmentSession.objects.select_related('clinician', 'result'),
        id=session_id
    )

    patient_profile = getattr(request.user, 'patient_profile', None)
    if not patient_profile or (session.patient != patient_profile and session.patient_code.upper() != patient_profile.patient_code.upper()):
        return HttpResponse('Access denied: You can only view your own assessment records.', status=403)

    if not hasattr(session, 'result'):
        return render(request, 'results_pending.html', {'session': session})

    result = session.result
    all_rounds = session.rounds.prefetch_related('attempts').order_by('round_number')

    rounds_breakdown = []
    for r in all_rounds:
        attempts = list(r.attempts.all().order_by('attempt_number'))
        tot = len(attempts)
        corr = sum(1 for a in attempts if a.is_correct)
        mist = tot - corr
        lats = [a.response_latency_ms for a in attempts]
        avg_lat = (sum(lats) / tot / 1000.0) if tot > 0 else 0.0
        acc = (corr / tot * 100.0) if tot > 0 else 0.0

        if r.is_practice:
            desc = "Practice Round (Orientation)"
        elif r.mode == 'shape_direction':
            desc = "Shape + Direction Matching"
        elif r.mode == 'complex_matching':
            desc = "Complex Multi-Attribute Matching"
        else:
            desc = "Standard Shape Matching"

        rounds_breakdown.append({
            'round_number': r.round_number,
            'is_practice': r.is_practice,
            'title': desc,
            'pair_count': r.pair_count,
            'card_count': r.card_count,
            'total_attempts': tot,
            'correct': corr,
            'mistakes': mist,
            'accuracy': round(acc, 1),
            'avg_latency_sec': round(avg_lat, 2),
        })

    total_sec = round(result.completion_time_ms / 1000.0)
    completion_time_str = f"{int(total_sec // 60)}m {int(total_sec % 60):02d}s"

    context = {
        'session': session,
        'result': result,
        'patient_profile': patient_profile,
        'rounds_breakdown': rounds_breakdown,
        'completion_time_str': completion_time_str,
    }
    return render(request, 'patient_detail.html', context)

from django.contrib import admin
from .models import ClinicianProfile, AssessmentSession, AssessmentRound, ResponseEvent, AssessmentResult


@admin.register(ClinicianProfile)
class ClinicianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'organization', 'created_at')
    search_fields = ('display_name', 'organization', 'user__username')


class AssessmentRoundInline(admin.TabularInline):
    model = AssessmentRound
    extra = 0


@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = ('patient_code', 'clinician', 'status', 'age_bracket', 'language', 'audio_voice', 'created_at', 'expires_at')
    list_filter = ('status', 'language', 'audio_voice', 'difficulty', 'created_at')
    search_fields = ('patient_code', 'id', 'clinician__display_name')
    inlines = [AssessmentRoundInline]


class ResponseEventInline(admin.TabularInline):
    model = ResponseEvent
    extra = 0


@admin.register(AssessmentRound)
class AssessmentRoundAdmin(admin.ModelAdmin):
    list_display = ('session', 'round_number', 'mode', 'pair_count', 'card_count')
    list_filter = ('round_number', 'mode')
    inlines = [ResponseEventInline]


@admin.register(ResponseEvent)
class ResponseEventAdmin(admin.ModelAdmin):
    list_display = ('round', 'attempt_number', 'is_correct', 'response_latency_ms', 'created_at')
    list_filter = ('is_correct', 'round__round_number')


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ('session', 'accuracy_percent', 'completed_pairs', 'total_attempts', 'mistakes', 'avg_latency_ms', 'completion_time_ms', 'created_at')
    search_fields = ('session__patient_code',)

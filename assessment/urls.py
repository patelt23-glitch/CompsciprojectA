from django.urls import path
from . import views

urlpatterns = [
    # Public & Landing
    path('', views.home_view, name='home'),

    # Clinician Authentication & Registration
    path('signup/', views.signup_view, name='signup'),
    path('api/signup/', views.signup_view, name='api_signup'),
    path('login/', views.login_view, name='login'),
    path('api/login/', views.login_view, name='api_login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/logout/', views.logout_view, name='api_logout'),

    # Clinician Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('api/profile/', views.profile_view, name='api_profile'),

    # Password Recovery
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('api/forgot-password/', views.forgot_password_view, name='api_forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password_token'),
    path('api/reset-password/', views.reset_password_view, name='api_reset_password'),

    # Clinician Dashboard & Exports
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/export.csv', views.dashboard_export_csv_view, name='dashboard_export_csv'),
    path('api/results/export/', views.dashboard_export_csv_view, name='api_results_export_all'),

    # Patient Link & Session Generation API
    path('api/sessions/', views.api_create_session, name='api_create_session'),
    path('api/invitations/', views.api_create_session, name='api_invitations'),

    # Patient Assessment Test Page (Token based)
    path('patient/<str:token>/', views.patient_test_view, name='patient_test'),

    # Attempt Submission & Assessment Completion APIs
    path('api/sessions/<uuid:session_id>/attempts/', views.api_submit_attempt, name='api_submit_attempt'),
    path('api/sessions/<uuid:session_id>/complete/', views.api_complete_session, name='api_complete_session'),

    # Detailed Results View & Export
    path('results/<uuid:session_id>/', views.results_view, name='results'),
    path('api/results/<uuid:session_id>/', views.api_result_detail, name='api_result_detail'),
    path('api/results/<uuid:session_id>/export.csv', views.export_csv_view, name='export_csv'),
    path('api/results/<uuid:session_id>/export/', views.export_csv_view, name='api_export_csv_alias'),
    path('api/results/<uuid:session_id>/notes/', views.api_update_notes, name='api_update_notes'),

    # Session & Identity Check
    path('api/session/', views.api_session, name='api_session'),
]

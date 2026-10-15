from django.urls import path
from assessments import views

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard_page, name='dashboard'),
    path('api/session/', views.session),
    path('api/login/', views.sign_in),
    path('api/signup/', views.sign_up),
    path('api/logout/', views.sign_out),
    path('api/profile/', views.profile),
    path('api/dashboard/', views.dashboard),
    path('api/invitations/', views.create_invitation),
    path('api/invitations/<str:token>/start/', views.start_attempt),
    path('api/invitations/<str:token>/complete/', views.complete_attempt),
    path('api/results/export/', views.export_csv),
    path('api/results/<int:result_id>/export/', views.export_csv),
]

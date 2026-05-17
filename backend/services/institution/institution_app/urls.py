from django.urls import path
from . import views

urlpatterns = [
    # Issuer endpoints
    path('apply/', views.apply, name='institution-apply'),
    path('status/', views.application_status, name='institution-status'),

    # Admin endpoints
    path('pending/', views.pending_applications, name='institution-pending'),
    path('all/', views.all_institutions, name='institution-all'),
    path('<uuid:institution_id>/', views.institution_detail, name='institution-detail'),
    path('<uuid:institution_id>/approve/', views.approve_institution, name='institution-approve'),
    path('<uuid:institution_id>/reject/', views.reject_institution, name='institution-reject'),
    path('<uuid:institution_id>/revoke/', views.revoke_institution, name='institution-revoke'),
]
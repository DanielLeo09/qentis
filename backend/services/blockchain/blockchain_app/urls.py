from django.urls import path
from . import views

urlpatterns = [
    # Core blockchain operations
    path('store/',   views.store_hash,   name='blockchain-store'),
    path('verify/',  views.verify_hash,  name='blockchain-verify'),
    path('revoke/',  views.revoke_hash,  name='blockchain-revoke'),

    # Health check
    path('health/',  views.health_check, name='blockchain-health'),
]
from django.urls import path
from . import views

urlpatterns = [
    # Public verification endpoints — no authentication required
    path('qr/', views.verify_qr, name='verify-qr'),
    path('serial/', views.verify_serial, name='verify-serial'),
    path('signature/', views.verify_signature, name='verify-signature'),
    path('ocr/', views.verify_ocr, name='verify-ocr'),
    path('watermark/', views.verify_watermark, name='verify-watermark'),
    path('report/', views.report_item, name='verify-report'),

    # Admin endpoints
    path('history/<uuid:item_id>/', views.verification_history, name='verify-history'),
    path('flags/', views.fraud_flags, name='verify-flags'),
]
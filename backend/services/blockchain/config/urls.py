from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Qentis Blockchain Service API",
        default_version='v1',
        description="API for writing and reading item hashes on the Ethereum blockchain (Ganache)",
        contact=openapi.Contact(email="admin@qentis.cm"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/blockchain/', include('blockchain_app.urls')),

    # Swagger documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
]
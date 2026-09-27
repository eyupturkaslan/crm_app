"""Minimal URLconf for API tests, independent from crm.web (owned by other agents)."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

urlpatterns = [
    path("api/v1/", include("crm.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .views import ActivityViewSet, CompanyViewSet, ContactViewSet, DealViewSet, StatsView, TagViewSet

router = DefaultRouter()
router.register("tags", TagViewSet, basename="tag")
router.register("companies", CompanyViewSet, basename="company")
router.register("contacts", ContactViewSet, basename="contact")
router.register("deals", DealViewSet, basename="deal")
router.register("activities", ActivityViewSet, basename="activity")

urlpatterns = [
    path("stats/", StatsView.as_view(), name="stats"),
    path("auth/token/", obtain_auth_token, name="api-token-auth"),
    path("", include(router.urls)),
]

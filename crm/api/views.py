from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from crm.models import Activity, Company, Contact, Deal, Tag
from crm.services import pipeline_stats

from .serializers import (
    ActivitySerializer,
    CompanySerializer,
    ContactSerializer,
    DealMoveSerializer,
    DealSerializer,
    PipelineStatsSerializer,
    TagSerializer,
)


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Common behaviour: assign request.user as owner on create when not given."""

    def perform_create(self, serializer):
        extra = {}
        if "owner" not in serializer.validated_data and self.request.user.is_authenticated:
            extra["owner"] = self.request.user
        serializer.save(**extra)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]


class CompanyViewSet(OwnedModelViewSet):
    queryset = Company.objects.select_related("owner").prefetch_related("tags")
    serializer_class = CompanySerializer
    filterset_fields = ["industry", "size", "city", "country", "owner"]
    search_fields = ["name", "domain", "industry", "city"]
    ordering_fields = ["name", "created_at", "updated_at"]


class ContactViewSet(OwnedModelViewSet):
    queryset = Contact.objects.select_related("company", "owner").prefetch_related("tags")
    serializer_class = ContactSerializer
    filterset_fields = ["lifecycle_stage", "source", "company", "owner", "marketing_consent"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    ordering_fields = ["first_name", "last_name", "score", "created_at", "updated_at"]


class DealViewSet(OwnedModelViewSet):
    queryset = Deal.objects.select_related("company", "contact", "owner")
    serializer_class = DealSerializer
    filterset_fields = ["stage", "company", "contact", "owner", "currency"]
    search_fields = ["title"]
    ordering_fields = ["value", "position", "expected_close", "created_at", "updated_at"]

    @extend_schema(
        request=DealMoveSerializer,
        responses={200: DealSerializer, 400: OpenApiResponse(description="Invalid stage")},
    )
    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        deal = self.get_object()
        serializer = DealMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deal.move_to(serializer.validated_data["stage"], serializer.validated_data.get("position"))
        return Response(DealSerializer(deal, context={"request": request}).data)


class ActivityViewSet(OwnedModelViewSet):
    queryset = Activity.objects.select_related("contact", "company", "deal", "owner")
    serializer_class = ActivitySerializer
    filterset_fields = ["kind", "done", "contact", "company", "deal", "owner"]
    search_fields = ["subject", "body"]
    ordering_fields = ["due_at", "created_at", "updated_at"]

    @extend_schema(request=None, responses={200: ActivitySerializer})
    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        activity = self.get_object()
        activity.done = not activity.done
        activity.save(update_fields=["done", "updated_at"])
        return Response(ActivitySerializer(activity, context={"request": request}).data)


class StatsView(APIView):
    """Pipeline-wide aggregate statistics."""

    @extend_schema(responses={200: PipelineStatsSerializer})
    def get(self, request):
        data = pipeline_stats()
        serializer = PipelineStatsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

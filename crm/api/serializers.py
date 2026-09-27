from rest_framework import serializers

from crm.models import Activity, Company, Contact, Deal, Tag

READ_ONLY_TIMESTAMPS = ("id", "created_at", "updated_at")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color"]


class CompanySerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True, default="")
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "domain",
            "industry",
            "size",
            "phone",
            "address",
            "city",
            "country",
            "owner",
            "owner_name",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = READ_ONLY_TIMESTAMPS

    def create(self, validated_data):
        request = self.context.get("request")
        if not validated_data.get("owner") and request is not None and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Contact
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "job_title",
            "company",
            "company_name",
            "lifecycle_stage",
            "source",
            "preferred_channel",
            "marketing_consent",
            "consent_at",
            "score",
            "notes",
            "owner",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (*READ_ONLY_TIMESTAMPS, "score", "consent_at")

    def create(self, validated_data):
        request = self.context.get("request")
        if not validated_data.get("owner") and request is not None and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class DealSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    contact_name = serializers.CharField(source="contact.full_name", read_only=True, default="")
    weighted_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Deal
        fields = [
            "id",
            "title",
            "company",
            "company_name",
            "contact",
            "contact_name",
            "value",
            "currency",
            "stage",
            "probability",
            "expected_close",
            "closed_at",
            "position",
            "owner",
            "weighted_value",
            "is_open",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (*READ_ONLY_TIMESTAMPS, "closed_at")

    def create(self, validated_data):
        request = self.context.get("request")
        if not validated_data.get("owner") and request is not None and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class DealMoveSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Deal.Stage.choices)
    position = serializers.IntegerField(required=False, min_value=0)


class ActivitySerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "kind",
            "subject",
            "body",
            "due_at",
            "done",
            "contact",
            "company",
            "deal",
            "owner",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = READ_ONLY_TIMESTAMPS

    def create(self, validated_data):
        request = self.context.get("request")
        if not validated_data.get("owner") and request is not None and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class StageBreakdownSerializer(serializers.Serializer):
    stage = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    value = serializers.DecimalField(max_digits=14, decimal_places=2)


class PipelineStatsSerializer(serializers.Serializer):
    companies = serializers.IntegerField()
    contacts = serializers.IntegerField()
    open_deals = serializers.IntegerField()
    pipeline_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    weighted_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    won_this_month = serializers.DecimalField(max_digits=14, decimal_places=2)
    win_rate = serializers.FloatField(allow_null=True)
    by_stage = StageBreakdownSerializer(many=True)
    overdue_activities = serializers.IntegerField()

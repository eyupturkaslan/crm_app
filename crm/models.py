from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("oluşturulma"), auto_now_add=True)
    updated_at = models.DateTimeField(_("güncellenme"), auto_now=True)

    class Meta:
        abstract = True


class Tag(models.Model):
    name = models.CharField(_("ad"), max_length=50, unique=True)
    color = models.CharField(_("renk"), max_length=7, default="#6366f1")

    class Meta:
        ordering = ["name"]
        verbose_name = _("etiket")
        verbose_name_plural = _("etiketler")

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    class Size(models.TextChoices):
        MICRO = "1-10", "1-10"
        SMALL = "11-50", "11-50"
        MEDIUM = "51-250", "51-250"
        LARGE = "251-1000", "251-1000"
        ENTERPRISE = "1000+", "1000+"

    name = models.CharField(_("ad"), max_length=200)
    domain = models.CharField(_("alan adı"), max_length=200, blank=True)
    industry = models.CharField(_("sektör"), max_length=100, blank=True)
    size = models.CharField(_("çalışan sayısı"), max_length=10, choices=Size.choices, blank=True)
    phone = models.CharField(_("telefon"), max_length=30, blank=True)
    address = models.TextField(_("adres"), blank=True)
    city = models.CharField(_("şehir"), max_length=100, blank=True)
    country = models.CharField(_("ülke"), max_length=100, blank=True, default="Türkiye")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
        verbose_name=_("sorumlu"),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="companies", verbose_name=_("etiketler"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("firma")
        verbose_name_plural = _("firmalar")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("crm:company_detail", args=[self.pk])


class Contact(TimeStampedModel):
    class Lifecycle(models.TextChoices):
        LEAD = "lead", _("Aday")
        PROSPECT = "prospect", _("Potansiyel")
        CUSTOMER = "customer", _("Müşteri")
        CHURNED = "churned", _("Kaybedilen")

    class Channel(models.TextChoices):
        EMAIL = "email", _("E-posta")
        PHONE = "phone", _("Telefon")
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    class Source(models.TextChoices):
        WEBSITE = "website", _("Web sitesi")
        REFERRAL = "referral", _("Referans")
        SOCIAL = "social", _("Sosyal medya")
        EVENT = "event", _("Etkinlik")
        ADS = "ads", _("Reklam")
        OTHER = "other", _("Diğer")

    first_name = models.CharField(_("ad"), max_length=100)
    last_name = models.CharField(_("soyad"), max_length=100, blank=True)
    email = models.EmailField(_("e-posta"), blank=True)
    phone = models.CharField(_("telefon"), max_length=30, blank=True)
    job_title = models.CharField(_("unvan"), max_length=100, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("firma"),
    )
    lifecycle_stage = models.CharField(
        _("yaşam döngüsü"), max_length=20, choices=Lifecycle.choices, default=Lifecycle.LEAD
    )
    source = models.CharField(_("kaynak"), max_length=20, choices=Source.choices, default=Source.OTHER)
    preferred_channel = models.CharField(
        _("tercih edilen kanal"), max_length=20, choices=Channel.choices, default=Channel.EMAIL
    )
    # KVKK / GDPR: explicit marketing consent with timestamp.
    marketing_consent = models.BooleanField(_("pazarlama izni"), default=False)
    consent_at = models.DateTimeField(_("izin tarihi"), null=True, blank=True)
    score = models.PositiveSmallIntegerField(_("skor"), default=0, editable=False)
    notes = models.TextField(_("notlar"), blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("sorumlu"),
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="contacts", verbose_name=_("etiketler"))

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = _("kişi")
        verbose_name_plural = _("kişiler")
        indexes = [models.Index(fields=["email"]), models.Index(fields=["lifecycle_stage"])]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self):
        return reverse("crm:contact_detail", args=[self.pk])

    def compute_score(self):
        """Simple, explainable lead score (0-100)."""
        score = 0
        score += 15 if self.email else 0
        score += 10 if self.phone else 0
        score += 10 if self.company_id else 0
        score += 10 if self.job_title else 0
        score += 15 if self.marketing_consent else 0
        score += {"referral": 20, "event": 15, "website": 10, "ads": 5, "social": 5}.get(self.source, 0)
        score += {"prospect": 10, "customer": 20}.get(self.lifecycle_stage, 0)
        return min(score, 100)

    def save(self, *args, **kwargs):
        if self.marketing_consent and not self.consent_at:
            self.consent_at = timezone.now()
        elif not self.marketing_consent:
            self.consent_at = None
        self.score = self.compute_score()
        super().save(*args, **kwargs)


class Deal(TimeStampedModel):
    class Stage(models.TextChoices):
        NEW = "new", _("Yeni")
        QUALIFIED = "qualified", _("Nitelikli")
        PROPOSAL = "proposal", _("Teklif")
        NEGOTIATION = "negotiation", _("Pazarlık")
        WON = "won", _("Kazanıldı")
        LOST = "lost", _("Kaybedildi")

    # Default win probability per stage (%), used for weighted pipeline forecasts.
    STAGE_PROBABILITY = {
        "new": 10,
        "qualified": 25,
        "proposal": 50,
        "negotiation": 75,
        "won": 100,
        "lost": 0,
    }
    OPEN_STAGES = ("new", "qualified", "proposal", "negotiation")

    title = models.CharField(_("başlık"), max_length=200)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name=_("firma"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name=_("kişi"),
    )
    value = models.DecimalField(_("tutar"), max_digits=14, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(_("para birimi"), max_length=3, default="TRY")
    stage = models.CharField(_("aşama"), max_length=20, choices=Stage.choices, default=Stage.NEW)
    probability = models.PositiveSmallIntegerField(_("olasılık (%)"), default=10)
    expected_close = models.DateField(_("beklenen kapanış"), null=True, blank=True)
    closed_at = models.DateTimeField(_("kapanış"), null=True, blank=True)
    position = models.PositiveIntegerField(_("sıra"), default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name=_("sorumlu"),
    )

    class Meta:
        ordering = ["stage", "position", "-created_at"]
        verbose_name = _("fırsat")
        verbose_name_plural = _("fırsatlar")
        indexes = [models.Index(fields=["stage", "position"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("crm:deal_detail", args=[self.pk])

    @property
    def is_open(self):
        return self.stage in self.OPEN_STAGES

    @property
    def weighted_value(self):
        return self.value * Decimal(self.probability) / Decimal(100)

    def move_to(self, stage, position=None):
        """Change stage, keeping probability and closed_at consistent."""
        self.stage = stage
        self.probability = self.STAGE_PROBABILITY.get(stage, self.probability)
        if position is not None:
            self.position = position
        self.save()

    def save(self, *args, **kwargs):
        if self.stage in (self.Stage.WON, self.Stage.LOST):
            self.closed_at = self.closed_at or timezone.now()
        else:
            self.closed_at = None
        super().save(*args, **kwargs)


class Activity(TimeStampedModel):
    class Kind(models.TextChoices):
        NOTE = "note", _("Not")
        CALL = "call", _("Arama")
        EMAIL = "email", _("E-posta")
        MEETING = "meeting", _("Toplantı")
        TASK = "task", _("Görev")

    kind = models.CharField(_("tür"), max_length=20, choices=Kind.choices, default=Kind.NOTE)
    subject = models.CharField(_("konu"), max_length=200)
    body = models.TextField(_("açıklama"), blank=True)
    due_at = models.DateTimeField(_("son tarih"), null=True, blank=True)
    done = models.BooleanField(_("tamamlandı"), default=False)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("kişi"),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("firma"),
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("fırsat"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("sorumlu"),
    )

    class Meta:
        ordering = ["done", "due_at", "-created_at"]
        verbose_name = _("aktivite")
        verbose_name_plural = _("aktiviteler")

    def __str__(self):
        return self.subject

    @property
    def is_overdue(self):
        return bool(self.due_at and not self.done and self.due_at < timezone.now())

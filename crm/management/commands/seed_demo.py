"""Seed the database with deterministic Turkish demo data.

Usage:
    python manage.py seed_demo [--reset]

``--reset`` wipes existing CRM rows (Tag/Company/Contact/Deal/Activity) before
reseeding. The superuser ``demo``/``demo12345`` is created if missing (kept on
reset). Uses ``random.Random(42)`` so the generated data is reproducible.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import Activity, Company, Contact, Deal, Tag

TAG_DEFS = [
    ("VIP", "#f59e0b"),
    ("Yeni", "#22c55e"),
    ("Soğuk", "#38bdf8"),
    ("Riskli", "#ef4444"),
    ("Kurumsal", "#6366f1"),
    ("KOBİ", "#a855f7"),
]

COMPANY_NAMES = [
    ("Anadolu Teknoloji A.Ş.", "Yazılım", "İstanbul"),
    ("Boğaziçi Lojistik Ltd.", "Lojistik", "İstanbul"),
    ("Ege Tarım Ürünleri A.Ş.", "Tarım", "İzmir"),
    ("Karadeniz Enerji A.Ş.", "Enerji", "Trabzon"),
    ("Akdeniz Turizm Ltd.", "Turizm", "Antalya"),
    ("Marmara Tekstil A.Ş.", "Tekstil", "Bursa"),
    ("Toros Gıda Sanayi A.Ş.", "Gıda", "Mersin"),
    ("Başkent Danışmanlık Ltd.", "Danışmanlık", "Ankara"),
    ("Nilüfer Elektronik A.Ş.", "Elektronik", "Bursa"),
    ("Sakarya Otomotiv A.Ş.", "Otomotiv", "Sakarya"),
    ("Konya Makine İmalat A.Ş.", "Üretim", "Konya"),
    ("Kapadokya Yazılım Ltd.", "Yazılım", "Nevşehir"),
    ("Fırat İnşaat A.Ş.", "İnşaat", "Elazığ"),
    ("Van Gölü Sağlık Ltd.", "Sağlık", "Van"),
    ("Trakya Kimya A.Ş.", "Kimya", "Edirne"),
]

FIRST_NAMES = [
    "Ahmet",
    "Mehmet",
    "Ayşe",
    "Fatma",
    "Mustafa",
    "Emine",
    "Ali",
    "Zeynep",
    "Hüseyin",
    "Hatice",
    "İbrahim",
    "Elif",
    "Hasan",
    "Merve",
    "Murat",
    "Selin",
    "Kemal",
    "Deniz",
    "Burak",
    "Ece",
    "Serkan",
    "Gizem",
    "Emre",
    "Buse",
    "Onur",
    "Ceren",
    "Uğur",
    "Nihan",
    "Yusuf",
    "Aslı",
    "Barış",
    "Pınar",
    "Cem",
    "Sibel",
    "Tolga",
    "Derya",
    "Kaan",
    "Şeyma",
    "Volkan",
    "Melis",
]
LAST_NAMES = [
    "Yılmaz",
    "Kaya",
    "Demir",
    "Çelik",
    "Şahin",
    "Yıldız",
    "Yıldırım",
    "Öztürk",
    "Aydın",
    "Özdemir",
    "Arslan",
    "Doğan",
    "Kılıç",
    "Aslan",
    "Çetin",
    "Kara",
    "Koç",
    "Kurt",
    "Özkan",
    "Şimşek",
]

DEAL_TITLES = [
    "Yıllık lisans yenileme",
    "Kurumsal paket satışı",
    "Pilot proje",
    "Bulut geçiş projesi",
    "Danışmanlık anlaşması",
    "Donanım tedariki",
    "Bakım sözleşmesi",
    "Entegrasyon projesi",
    "Eğitim paketi",
    "Genişletilmiş destek anlaşması",
]

ACTIVITY_SUBJECTS = {
    Activity.Kind.CALL: ["Tanışma araması", "Takip araması", "Fiyat görüşmesi", "Referans araması"],
    Activity.Kind.EMAIL: ["Teklif e-postası", "Hatırlatma e-postası", "Bilgilendirme e-postası"],
    Activity.Kind.MEETING: ["Demo toplantısı", "İhtiyaç analizi toplantısı", "Sözleşme toplantısı"],
    Activity.Kind.TASK: ["Sözleşme hazırla", "Teklif güncelle", "Raporu gönder"],
    Activity.Kind.NOTE: ["Görüşme notu", "İç not"],
}


class Command(BaseCommand):
    help = "Seed deterministic Turkish demo data for the CRM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing Tag/Company/Contact/Deal/Activity rows before seeding.",
        )

    def handle(self, *args, **options):
        rng = random.Random(42)
        now = timezone.now()

        if options["reset"]:
            Activity.objects.all().delete()
            Deal.objects.all().delete()
            Contact.objects.all().delete()
            Company.objects.all().delete()
            Tag.objects.all().delete()
            self.stdout.write("Mevcut CRM verileri silindi.")

        User = get_user_model()
        demo_user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com", "is_staff": True, "is_superuser": True},
        )
        if created:
            demo_user.set_password("demo12345")
            demo_user.save()
            self.stdout.write("Superuser 'demo' / 'demo12345' oluşturuldu.")
        else:
            self.stdout.write("Superuser 'demo' zaten mevcut.")

        with transaction.atomic():
            tags = self._seed_tags(rng)
            companies = self._seed_companies(rng, demo_user, tags)
            contacts = self._seed_contacts(rng, demo_user, companies, tags)
            deals = self._seed_deals(rng, demo_user, companies, contacts, now)
            self._seed_activities(rng, demo_user, contacts, companies, deals, now)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed tamamlandı: {len(tags)} etiket, {len(companies)} firma, "
                f"{len(contacts)} kişi, {len(deals)} fırsat."
            )
        )

    def _seed_tags(self, rng):
        tags = []
        for name, color in TAG_DEFS:
            tag, _created = Tag.objects.get_or_create(name=name, defaults={"color": color})
            tags.append(tag)
        return tags

    def _seed_companies(self, rng, owner, tags):
        companies = []
        for name, industry, city in COMPANY_NAMES:
            company, created = Company.objects.get_or_create(
                name=name,
                defaults={
                    "domain": self._slugify(name) + ".com.tr",
                    "industry": industry,
                    "size": rng.choice(Company.Size.values),
                    "phone": self._phone(rng),
                    "city": city,
                    "country": "Türkiye",
                    "owner": owner,
                },
            )
            # Always draw from rng (even if not creating) so the random sequence
            # consumed here stays identical across runs, keeping later entities
            # (contacts/deals/activities) deterministic regardless of --reset.
            picked_tags = rng.sample(tags, k=rng.randint(0, 2))
            if created:
                company.tags.set(picked_tags)
            companies.append(company)
        return companies

    def _seed_contacts(self, rng, owner, companies, tags):
        contacts = []
        lifecycle_values = Contact.Lifecycle.values
        source_values = Contact.Source.values
        channel_values = Contact.Channel.values
        for i in range(40):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            company = rng.choice(companies) if rng.random() < 0.9 else None
            marketing_consent = rng.random() < 0.55
            email = f"{self._slugify(first)}.{self._slugify(last)}{i}@example.com"
            contact, created = Contact.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": self._phone(rng),
                    "job_title": rng.choice(
                        ["Satın Alma Müdürü", "Genel Müdür", "IT Yöneticisi", "Satış Direktörü", ""]
                    ),
                    "company": company,
                    "lifecycle_stage": rng.choice(lifecycle_values),
                    "source": rng.choice(source_values),
                    "preferred_channel": rng.choice(channel_values),
                    "marketing_consent": marketing_consent,
                    "owner": owner,
                },
            )
            picked_tags = rng.sample(tags, k=rng.randint(0, 2))
            if created:
                contact.tags.set(picked_tags)
            contacts.append(contact)
        return contacts

    def _seed_deals(self, rng, owner, companies, contacts, now):
        deals = []
        stage_values = list(Deal.Stage.values)
        # Weighted distribution so most deals sit in earlier/open stages.
        stage_weights = {
            "new": 6,
            "qualified": 6,
            "proposal": 5,
            "negotiation": 4,
            "won": 5,
            "lost": 4,
        }
        weighted_stages = [s for s in stage_values for _ in range(stage_weights.get(s, 1))]
        stage_positions = dict.fromkeys(stage_values, 0)

        for i in range(30):
            stage = weighted_stages[i % len(weighted_stages)]
            if i % 7 == 0:
                rng.shuffle(weighted_stages)
            company = rng.choice(companies)
            company_contacts = [c for c in contacts if c.company_id == company.id] or contacts
            contact = rng.choice(company_contacts)
            title = f"{rng.choice(DEAL_TITLES)} - {company.name.split()[0]}"
            value = Decimal(rng.randint(15, 500) * 1000)
            position = stage_positions[stage]
            stage_positions[stage] += 1

            deal = Deal.objects.create(
                title=title,
                company=company,
                contact=contact,
                value=value,
                currency="TRY",
                stage=stage,
                probability=Deal.STAGE_PROBABILITY.get(stage, 10),
                expected_close=(now + timedelta(days=rng.randint(-10, 60))).date(),
                position=position,
                owner=owner,
            )
            if stage in (Deal.Stage.WON, Deal.Stage.LOST):
                # Backdate closed_at a bit so "won this month" style stats vary.
                deal.closed_at = now - timedelta(days=rng.randint(0, 45))
                deal.save(update_fields=["closed_at"])
            deals.append(deal)
        return deals

    def _seed_activities(self, rng, owner, contacts, companies, deals, now):
        activities = []
        kinds = list(Activity.Kind.values)
        for _i in range(50):
            kind = rng.choice(kinds)
            subject = rng.choice(ACTIVITY_SUBJECTS.get(kind, ["Görev"]))
            done = rng.random() < 0.4
            # Roughly a third overdue (past + not done), rest upcoming/past-done.
            if not done and rng.random() < 0.5:
                due_at = now - timedelta(days=rng.randint(1, 20))
            else:
                due_at = now + timedelta(days=rng.randint(1, 30))
            contact = rng.choice(contacts) if rng.random() < 0.6 else None
            deal = rng.choice(deals) if rng.random() < 0.4 else None
            company = contact.company if contact and contact.company_id else rng.choice(companies)

            activity = Activity.objects.create(
                kind=kind,
                subject=subject,
                body="",
                due_at=due_at,
                done=done,
                contact=contact,
                company=company,
                deal=deal,
                owner=owner,
            )
            activities.append(activity)
        return activities

    @staticmethod
    def _slugify(value):
        return "".join(ch.lower() for ch in value if ch.isalnum())

    @staticmethod
    def _phone(rng):
        prefix = rng.choice([5, 2])
        return f"0{prefix}{rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(10, 99)} {rng.randint(10, 99)}"

# CRM

Küçük ve orta ölçekli ekipler için modern, hızlı ve API öncelikli bir müşteri ilişkileri yönetimi (CRM) uygulaması.

**Teknoloji:** Django 5.2 · Django REST Framework · HTMX 2 · Tailwind CSS v4 · PostgreSQL / SQLite · Docker

## Özellikler

- **Panel:** açık pipeline, ağırlıklı tahmin, bu ay kazanılan, kazanma oranı, geciken görevler ve aşamalara göre pipeline grafiği
- **Fırsat panosu (Kanban):** sürükle-bırak ile aşama değiştirme; olasılık ve kapanış tarihi otomatik güncellenir
- **Kişiler ve firmalar:** canlı arama, filtreleme, sayfalama, aktivite zaman akışı
- **Aday skorlama:** her kişi için açıklanabilir 0–100 skoru (iletişim bilgisi, kaynak, yaşam döngüsü, izin)
- **KVKK/GDPR:** pazarlama izni zaman damgasıyla saklanır
- **Çok kanallı iletişim tercihi:** e-posta, telefon, WhatsApp, SMS
- **Aktiviteler ve görevler:** not, arama, e-posta, toplantı, görev; geciken ve bugünkü görev görünümleri
- **CSV içe/dışa aktarma:** Excel uyumlu (UTF-8 BOM); içe aktarırken e-posta ile tekilleştirme
- **Global arama:** `Ctrl/⌘ + K`
- **Karanlık mod**, mobil uyumlu arayüz, PWA manifest, TR/EN i18n altyapısı
- **REST API:** `/api/v1/`; token ve oturum kimlik doğrulaması, filtreleme, arama, sıralama, OpenAPI/Swagger (`/api/docs/`)
- **Üretime hazır:** 12-factor yapılandırma, WhiteNoise, Gunicorn, sağlık kontrolü (`/healthz/`), güvenlik başlıkları, CI

## Hızlı başlangıç

```bash
make install        # .venv oluşturur, bağımlılıkları kurar
make seed           # veritabanını kurar, demo verisi yükler (kullanıcı: demo / demo12345)
make run            # http://127.0.0.1:8000
```

### Docker ile

```bash
cp .env.example .env    # DJANGO_SECRET_KEY'i değiştirin
docker compose up --build
docker compose exec web python manage.py seed_demo
```

## API

```bash
# Token al
curl -X POST localhost:8000/api/v1/auth/token/ -d "username=demo&password=demo12345"

# Kişileri listele (filtre + arama)
curl -H "Authorization: Token <token>" "localhost:8000/api/v1/contacts/?lifecycle_stage=lead&search=ahmet"

# Fırsatı başka aşamaya taşı
curl -X POST -H "Authorization: Token <token>" -d "stage=won" localhost:8000/api/v1/deals/1/move/
```

Uç noktalar: `tags`, `companies`, `contacts`, `deals` (`/move/`), `activities` (`/toggle/`), `stats`. Tam şema için `/api/docs/` adresine bakın.

## Geliştirme

```bash
make test     # pytest
make lint     # ruff check + format kontrolü
make fmt      # otomatik düzelt
```

Yapılandırma ortam değişkenleriyle yapılır; tüm değişkenler için `.env.example` dosyasına bakın.

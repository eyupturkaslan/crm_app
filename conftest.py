import pytest
from rest_framework.test import APIClient

from crm.models import Company, Contact, Deal


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="ayse", password="pass12345", first_name="Ayşe")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def api_client(user):
    api = APIClient()
    api.force_authenticate(user)
    return api


@pytest.fixture
def company(user):
    return Company.objects.create(name="Acme A.Ş.", industry="Yazılım", owner=user)


@pytest.fixture
def contact(company, user):
    return Contact.objects.create(
        first_name="Mehmet", last_name="Yılmaz", email="mehmet@acme.test", company=company, owner=user
    )


@pytest.fixture
def deal(company, contact, user):
    return Deal.objects.create(title="Lisans yenileme", company=company, contact=contact, value=50000, owner=user)

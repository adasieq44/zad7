import pytest

from pydantic import ValidationError
from src.models import Apartment, Tenant


def test_apartment_fields():
    data = Apartment(
        key="apart-test",
        name="Test Apartment",
        location="Test Location",
        area_m2=50.0,
        rooms={
            "room-1": {"name": "Living Room", "area_m2": 30.0},
            "room-2": {"name": "Bedroom", "area_m2": 20.0}
        }
    )
    assert data.key == "apart-test"
    assert data.name == "Test Apartment"
    assert data.location == "Test Location"
    assert data.area_m2 == 50.0
    assert len(data.rooms) == 2


def test_apartment_from_dict():
    data = {
        "key": "apart-test",
        "name": "Test Apartment",
        "location": "Test Location",
        "area_m2": 50.0,
        "rooms": {
            "room-1": {"name": "Living Room", "area_m2": 30.0},
            "room-2": {"name": "Bedroom", "area_m2": 20.0}
        }
    }
    apartment = Apartment(**data)
    assert apartment.key == data["key"]
    assert apartment.name == data["name"]
    assert apartment.location == data["location"]
    assert apartment.area_m2 == data["area_m2"]
    assert len(apartment.rooms) == len(data["rooms"])

    data['area_m2'] = "25m2" # Invalid field
    with pytest.raises(ValidationError):
        wrong_apartment = Apartment(**data)

def test_tenant_fields():
    tenant = Tenant(
        name='Test Tenant',
        apartment='apart-test',
        room='test-room',
        apartment_key='apart-test',
        rent_pln=1500.0,
        deposit_pln=3000.0,
        date_agreement_from='2024-01-01',
        date_agreement_to='2024-12-31'
    )

    assert tenant.name == 'Test Tenant'
    assert tenant.apartment == 'apart-test'
    assert tenant.room == 'test-room'
    assert tenant.apartment == 'apart-test'
    assert tenant.rent_pln == 1500.0
    assert tenant.deposit_pln == 3000.0
    assert tenant.date_agreement_from == '2024-01-01'
    assert tenant.date_agreement_to == '2024-12-31'

def test_tenant_from_dict():
    data = {
        "name": "Test Testowy",
        "apartment": "test-apart",
        "room": "test-room",
        "rent_pln": 4324.0,
        "deposit_pln": 12356.0,
        "date_agreement_from": "2032-01-01",
        "date_agreement_to": "2033-01-01"
    }
    tenant = Tenant(**data)
    assert tenant.name == data["name"]
    assert tenant.apartment == data["apartment"]
    assert tenant.room == data["room"]
    assert tenant.rent_pln == data["rent_pln"]

    with pytest.raises(ValidationError):
        data['rent_pln'] = "1500PLN" # Invalid field
        wrong_tenant = Tenant(**data)
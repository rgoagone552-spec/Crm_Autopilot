import pytest
from app.db import models

def test_create_and_get_deal(client):
    payload = {
        "id": "d1",
        "name": "Deal One",
        "amount": 1000.0,
        "stage": "prospect",
    }
    response = client.post("/deals/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "d1"
    assert data["name"] == "Deal One"

    # Retrieve
    resp_get = client.get(f"/deals/{payload['id']}")
    assert resp_get.status_code == 200
    got = resp_get.json()
    assert got["id"] == payload["id"]
    assert got["name"] == payload["name"]

def test_list_deals_pagination(client):
    for i in range(5):
        client.post("/deals/", json={"id": f"d{i}", "name": f"Deal{i}"})
    resp = client.get("/deals/?limit=2&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["id"] == "d1"

def test_update_and_delete_deal(client):
    client.post("/deals/", json={"id": "d10", "name": "Initial"})
    # Update
    upd = client.put("/deals/d10", json={"id": "d10", "name": "Updated"})
    assert upd.status_code == 200
    assert upd.json()["name"] == "Updated"
    # Delete
    del_resp = client.delete("/deals/d10")
    assert del_resp.status_code == 200
    # Verify deletion
    get_resp = client.get("/deals/d10")
    assert get_resp.status_code == 404

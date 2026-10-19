import pytest
from app.db import models

def test_create_and_get_contact(client):
    payload = {
        "id": "c1",
        "name": "Alice",
        "email": "alice@example.com",
        "phone": "1234567890",
    }
    response = client.post("/contacts/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "c1"
    assert data["name"] == "Alice"

    # Retrieve
    resp_get = client.get(f"/contacts/{payload['id']}")
    assert resp_get.status_code == 200
    got = resp_get.json()
    assert got["id"] == payload["id"]
    assert got["name"] == payload["name"]

def test_list_contacts_pagination(client):
    # Insert multiple contacts
    for i in range(5):
        client.post("/contacts/", json={"id": f"c{i}", "name": f"Name{i}"})
    resp = client.get("/contacts/?limit=2&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["id"] == "c1"

def test_update_and_delete_contact(client):
    client.post("/contacts/", json={"id": "c10", "name": "Bob"})
    # Update
    upd = client.put("/contacts/c10", json={"id": "c10", "name": "Bob Updated"})
    assert upd.status_code == 200
    assert upd.json()["name"] == "Bob Updated"
    # Delete
    del_resp = client.delete("/contacts/c10")
    assert del_resp.status_code == 200
    # Verify deletion
    get_resp = client.get("/contacts/c10")
    assert get_resp.status_code == 404

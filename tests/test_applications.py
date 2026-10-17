from .conftest import register

URL = "/api/applications"


def create(client, headers, **overrides):
    payload = {"company": "Acme", "role": "Backend Intern", **overrides}
    return client.post(URL, json=payload, headers=headers)


def test_create_and_fetch(client, auth_headers):
    res = create(client, auth_headers, location="Bengaluru", applied_on="2026-10-01")
    assert res.status_code == 201
    app = res.get_json()
    assert app["status"] == "applied"
    assert app["applied_on"] == "2026-10-01"
    assert app["history"][0] == {**app["history"][0], "from": None, "to": "applied"}

    fetched = client.get(f"{URL}/{app['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.get_json()["company"] == "Acme"


def test_create_validation(client, auth_headers):
    res = client.post(URL, json={"company": "", "status": "ghosted"}, headers=auth_headers)
    assert res.status_code == 422
    assert set(res.get_json()["details"]) == {"company", "role", "status"}

    res = create(client, auth_headers, applied_on="01-10-2026")
    assert res.status_code == 422


def test_status_update_records_history(client, auth_headers):
    app_id = create(client, auth_headers).get_json()["id"]
    client.patch(f"{URL}/{app_id}", json={"status": "interview"}, headers=auth_headers)
    res = client.patch(
        f"{URL}/{app_id}", json={"status": "offer", "notes": "Yay"}, headers=auth_headers
    )
    body = res.get_json()
    assert body["status"] == "offer"
    assert body["notes"] == "Yay"
    assert [h["to"] for h in body["history"]] == ["applied", "interview", "offer"]

    # Updating other fields does not add a history entry
    res = client.patch(f"{URL}/{app_id}", json={"location": "Remote"}, headers=auth_headers)
    assert len(res.get_json()["history"]) == 3


def test_list_filters_search_sort_and_paginate(client, auth_headers):
    create(client, auth_headers, company="Zeta", role="SDE", applied_on="2026-09-01")
    create(client, auth_headers, company="Alpha", role="BD Associate", applied_on="2026-10-05",
           status="interview")
    create(client, auth_headers, company="Beta", role="Data Analyst", applied_on="2026-08-15",
           status="rejected")

    all_items = client.get(URL, headers=auth_headers).get_json()
    assert all_items["total"] == 3
    assert [a["company"] for a in all_items["items"]] == ["Alpha", "Zeta", "Beta"]

    filtered = client.get(f"{URL}?status=interview,rejected", headers=auth_headers).get_json()
    assert {a["company"] for a in filtered["items"]} == {"Alpha", "Beta"}

    searched = client.get(f"{URL}?q=analyst", headers=auth_headers).get_json()
    assert [a["company"] for a in searched["items"]] == ["Beta"]

    by_name = client.get(f"{URL}?sort=company", headers=auth_headers).get_json()
    assert [a["company"] for a in by_name["items"]] == ["Alpha", "Beta", "Zeta"]

    page2 = client.get(f"{URL}?sort=company&per_page=2&page=2", headers=auth_headers).get_json()
    assert page2["pages"] == 2
    assert [a["company"] for a in page2["items"]] == ["Zeta"]

    assert client.get(f"{URL}?status=ghosted", headers=auth_headers).status_code == 400
    assert client.get(f"{URL}?sort=password", headers=auth_headers).status_code == 400


def test_users_cannot_see_each_others_applications(client, auth_headers):
    app_id = create(client, auth_headers).get_json()["id"]
    other_token = register(client, email="other@example.com").get_json()["token"]
    other = {"Authorization": f"Bearer {other_token}"}

    assert client.get(f"{URL}/{app_id}", headers=other).status_code == 404
    assert client.patch(f"{URL}/{app_id}", json={"status": "offer"}, headers=other).status_code == 404
    assert client.delete(f"{URL}/{app_id}", headers=other).status_code == 404
    assert client.get(URL, headers=other).get_json()["total"] == 0


def test_delete(client, auth_headers):
    app_id = create(client, auth_headers).get_json()["id"]
    assert client.delete(f"{URL}/{app_id}", headers=auth_headers).status_code == 204
    assert client.get(f"{URL}/{app_id}", headers=auth_headers).status_code == 404


def test_stats(client, auth_headers):
    create(client, auth_headers, status="wishlist")
    create(client, auth_headers)
    create(client, auth_headers, status="interview")
    rejected_after_oa = create(client, auth_headers, status="oa").get_json()["id"]
    client.patch(f"{URL}/{rejected_after_oa}", json={"status": "rejected"}, headers=auth_headers)
    create(client, auth_headers, status="offer")

    stats = client.get(f"{URL}/stats", headers=auth_headers).get_json()
    assert stats["total"] == 5
    assert stats["by_status"]["rejected"] == 1
    assert stats["active"] == 3
    # 4 submitted (wishlist excluded); 3 ever reached oa/interview/offer
    assert stats["response_rate"] == 0.75
    assert stats["offer_rate"] == 0.25

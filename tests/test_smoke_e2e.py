"""Spec §16 — composite end-to-end happy path."""
import pytest
from django.contrib.auth import SESSION_KEY, get_user_model
from django.core import mail
from django.core.management import call_command

from apps.security.honeypot import HONEYPOT_FIELD
from apps.users.client_hash import derive_client_hash

User = get_user_model()


@pytest.mark.django_db
def test_full_smoke_flow(client, signup_post_payload):
    mail.outbox.clear()

    # 1. Signup with mixed-case email
    payload = signup_post_payload(username="newbie", email="Foo@Example.com",
                                  plaintext="my-real-password")
    resp = client.post("/accounts/signup/", payload)
    assert resp.status_code == 302
    assert SESSION_KEY in client.session

    # 2. Logout
    resp = client.post("/accounts/logout/")
    assert resp.status_code == 302
    assert SESSION_KEY not in client.session

    # 3. Login with mixed-case email
    resp = client.post("/accounts/login/", {
        "email": "FOO@EXAMPLE.COM",
        "password": derive_client_hash("my-real-password", "foo@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    assert SESSION_KEY in client.session

    # 4. Save profile with calendly URL — no warning.
    payload = {
        "first_name": "Foo", "last_name": "",
        "bio": "A community member offering thoughtful conversation and mentoring opportunities.",
        "scheduling_url": "https://calendly.com/me/30",
        "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "0",
        "providerservice_set-INITIAL_FORMS": "0",
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    resp = client.post("/settings/", payload)
    assert resp.status_code == 302

    # 5. Switch to non-allowlisted host — warning fires
    payload["scheduling_url"] = "https://my-tool.example.com/me"
    resp = client.post("/settings/", payload, follow=True)
    body = resp.content.decode()
    # Apostrophe is HTML-entity-encoded by Django's auto-escape; assert by substring.
    assert "recognize this scheduling tool" in body

    # Visit own profile — caution panel renders.
    resp = client.get("/p/newbie/")
    assert b"scheduling-caution" in resp.content

    # Switch back to calendly — caution removed.
    payload["scheduling_url"] = "https://calendly.com/me/30"
    client.post("/settings/", payload)
    resp = client.get("/p/newbie/")
    assert b"scheduling-caution" not in resp.content

    # 6. Add a Mentoring service with custom_description
    from apps.directory.models import ServiceCategory
    cat = ServiceCategory.objects.get(slug="mock-interview")
    other = ServiceCategory.objects.get(slug="other")
    user = User.objects.get(email="foo@example.com")
    # Reset payload — earlier steps may have added formset prefixes that conflict.
    payload2 = {
        "first_name": "Foo", "last_name": "",
        "bio": "A community member offering thoughtful conversation and mentoring opportunities.",
        "scheduling_url": "https://calendly.com/me/30",
        "feedback_url": "",
        "providerservice_set-TOTAL_FORMS": "2",
        "providerservice_set-INITIAL_FORMS": str(user.profile.providerservice_set.count()),
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
        "providerservice_set-0-id": "",
        "providerservice_set-0-profile": "",
        "providerservice_set-0-category": str(cat.id),
        "providerservice_set-0-custom_description": "early-career engineers",
        "providerservice_set-1-id": "",
        "providerservice_set-1-profile": "",
        "providerservice_set-1-category": str(other.id),
        "providerservice_set-1-custom_description": "System design office hours",
    }
    # Wipe profile services first (fresh start).
    user.profile.providerservice_set.all().delete()
    payload2["providerservice_set-INITIAL_FORMS"] = "0"
    resp = client.post("/settings/", payload2)
    assert resp.status_code == 302, resp.content.decode()[:2000]
    user.refresh_from_db()
    assert user.profile.providerservice_set.count() == 2

    # 7. Set feedback_url — keep the existing services, just update the URL field.
    saved_services = list(user.profile.providerservice_set.values("id", "category_id", "custom_description").order_by("id"))
    payload3 = {
        "first_name": "Foo", "last_name": "",
        "bio": "A community member offering thoughtful conversation and mentoring opportunities.",
        "scheduling_url": "https://calendly.com/me/30",
        "feedback_url": "https://forms.google.com/abc",
        "providerservice_set-TOTAL_FORMS": str(len(saved_services)),
        "providerservice_set-INITIAL_FORMS": str(len(saved_services)),
        "providerservice_set-MIN_NUM_FORMS": "0",
        "providerservice_set-MAX_NUM_FORMS": "12",
    }
    for i, svc in enumerate(saved_services):
        payload3[f"providerservice_set-{i}-id"] = str(svc["id"])
        payload3[f"providerservice_set-{i}-profile"] = str(user.profile.id)
        payload3[f"providerservice_set-{i}-category"] = str(svc["category_id"])
        payload3[f"providerservice_set-{i}-custom_description"] = svc["custom_description"]
    resp = client.post("/settings/", payload3)
    assert resp.status_code == 302, resp.content.decode()[:2000]

    # 8. Visit own profile, no badge.
    resp = client.get("/p/newbie/")
    assert resp.status_code == 200
    assert b"verified-badge" not in resp.content

    # 9. Anon visit — still 200.
    client.logout()
    resp = client.get("/p/newbie/")
    assert resp.status_code == 200
    assert b"verified-badge" not in resp.content

    # 10. Directory shows profile.
    resp = client.get("/directory/")
    assert b"Foo" in resp.content

    # 11. Operator verifies. Reload — badge appears.
    call_command("verify_user", "foo@example.com")
    resp = client.get("/directory/")
    assert b"verified-badge" in resp.content
    resp = client.get("/p/newbie/")
    assert b"verified-badge" in resp.content

    # 12. Operator unverifies. Badge gone.
    call_command("verify_user", "foo@example.com", "--unverify")
    resp = client.get("/p/newbie/")
    assert b"verified-badge" not in resp.content

    # 13. Search by `engineers` finds profile.
    resp = client.get("/directory/?q=engineers")
    assert b"Foo" in resp.content

    # 14. Filter by Mentoring chip
    resp = client.get("/directory/?category=mock-interview")
    assert b"Foo" in resp.content

    # 15-16. Outbound link attrs already covered in test_outbound_links.

    # 18. reset_password flow
    call_command("reset_password", "foo@example.com", "--password=temp-1234")
    resp = client.post("/accounts/login/", {
        "email": "foo@example.com",
        "password": derive_client_hash("temp-1234", "foo@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    # /settings/ redirects to /settings/password/
    resp = client.get("/settings/")
    assert resp.status_code == 302
    assert "/settings/password/" in resp.headers["Location"]
    # Submit a new password
    resp = client.post("/settings/password/", {
        "current_password": derive_client_hash("temp-1234", "foo@example.com"),
        "new_password": derive_client_hash("permanent-pw", "foo@example.com"),
        HONEYPOT_FIELD: "",
    })
    assert resp.status_code == 302
    resp = client.get("/settings/")
    assert resp.status_code == 200

    # 19. /admin/ returns 404
    resp = client.get("/admin/")
    assert resp.status_code == 404

    # 20. Operator deactivates
    User.objects.filter(email__iexact="foo@example.com").update(is_active=False)
    resp = client.get("/p/newbie/")
    assert resp.status_code == 404
    resp = client.get("/directory/")
    assert b"Foo" not in resp.content

    # 21. Reactivate
    User.objects.filter(email__iexact="foo@example.com").update(is_active=True)
    resp = client.get("/directory/")
    assert b"Foo" in resp.content

    # 22. Hard delete
    User.objects.filter(email__iexact="foo@example.com").delete()
    assert User.objects.filter(username="newbie").count() == 0

    # 23. Mailbox is empty.
    assert mail.outbox == []

from audiol.studio.media import issue_ticket


def _ticket(client, path: str, kind: str = "epub", book_id: str | None = None) -> dict:
    response = client.post(
        "/api/media/ticket",
        json={
            "book_id": book_id if book_id is not None else path.split("/")[3],
            "kind": kind,
            "path": path,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_media_ticket_opens_media_without_a_header(client, unauth_client, imported):
    path = f"/api/books/{imported['id']}/epub"
    ticket = _ticket(client, path)

    response = unauth_client.get(ticket["url"])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/epub+zip")


def test_media_ticket_is_bound_to_its_path(client, unauth_client, imported):
    path = f"/api/books/{imported['id']}/epub"
    ticket = _ticket(client, path)
    other = f"/api/books/{imported['id']}/cover"

    response = unauth_client.get(ticket["url"].replace(path, other))

    assert response.status_code == 401


def test_media_ticket_rejects_tampering(client, unauth_client, imported):
    path = f"/api/books/{imported['id']}/epub"
    ticket = _ticket(client, path)
    url, query = ticket["url"].split("?")
    signature = query.split("=", 1)[1]
    tampered = f"{url}?ticket={signature[:-1]}0"

    assert unauth_client.get(tampered).status_code == 401


def test_expired_media_ticket_is_rejected(unauth_client, imported):
    path = f"/api/books/{imported['id']}/epub"
    ticket, _ = issue_ticket(imported["id"], "epub", path, ttl=-1)

    response = unauth_client.get(f"{path}?ticket={ticket}")

    assert response.status_code == 401


def test_media_ticket_requires_the_local_header(client):
    response = client.post(
        "/api/media/ticket",
        json={"book_id": "", "kind": "preview", "path": "/api/previews/abc"},
        headers={"X-Vibebook-Token": "wrong"},
    )

    assert response.status_code == 401


def test_media_ticket_validates_kind_and_book(client, imported):
    wrong_kind = client.post(
        "/api/media/ticket",
        json={
            "book_id": imported["id"],
            "kind": "cover",
            "path": f"/api/books/{imported['id']}/epub",
        },
    )
    wrong_book = client.post(
        "/api/media/ticket",
        json={
            "book_id": "otro-libro",
            "kind": "epub",
            "path": f"/api/books/{imported['id']}/epub",
        },
    )

    assert wrong_kind.status_code == 422
    assert wrong_book.status_code == 404


def test_media_query_token_is_no_longer_accepted(unauth_client, imported):
    path = f"/api/books/{imported['id']}/epub"

    response = unauth_client.get(f"{path}?token=test-token")

    assert response.status_code == 401

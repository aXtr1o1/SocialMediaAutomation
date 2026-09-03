from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.publication_service import PublicationServices


@pytest.fixture
def service():
    with (
        patch("app.services.publication_service.get_supabase_client"),
        patch("app.services.publication_service.AccountService"),
        patch("app.services.publication_service.LinkedInService"),
        patch("app.services.publication_service.GenerationService"),
        patch("app.services.publication_service.BlueskyService"),
    ):
        return PublicationServices()


@pytest.fixture
def ids():
    return {
        "user": uuid4(),
        "draft": uuid4(),
        "account": uuid4(),
        "publication": uuid4(),
        "version": uuid4(),
        "status": uuid4(),
        "platform": uuid4(),
    }


def make_draft(ids):
    return {
        "id": str(ids["draft"]),
        "platform": "linkedin",
        "current_version_id": str(ids["version"]),
        "versions": [
            {
                "id": str(ids["version"]),
                "full_post": "Test post content",
            }
        ],
    }


def make_publication(ids, status="completed"):
    return {
        "id": str(ids["publication"]),
        "draft_id": str(ids["draft"]),
        "version_id": str(ids["version"]),
        "status_id": str(ids["status"]),
        "status_name": status,
        "user_id": str(ids["user"]),
        "platform_id": str(ids["platform"]),
        "connected_account_id": str(ids["account"]),
        "platform_post_id": (
            "linkedin-post-123" if status == "completed" else None
        ),
        "platform_response": "success" if status == "completed" else None,
        "error_message": (
            None if status == "completed" else "Platform publishing failed"
        ),
        "retry_count": 0,
    }


def configure_publish_mocks(service, ids):
    service.generation_service.get_draft = MagicMock(
        return_value=make_draft(ids)
    )

    service._get_owned_account = MagicMock(
        return_value={
            "id": str(ids["account"]),
            "platform_id": str(ids["platform"]),
            "is_enabled": True,
        }
    )

    service._validate_connected_account = MagicMock()
    service._get_platform_name = MagicMock(return_value="linkedin")
    service._find_existing_publication = MagicMock(return_value=None)
    service._create_publication = MagicMock(
        return_value={
            "id": str(ids["publication"]),
            "draft_id": str(ids["draft"]),
            "version_id": str(ids["version"]),
            "status_id": str(ids["status"]),
            "user_id": str(ids["user"]),
            "platform_id": str(ids["platform"]),
            "connected_account_id": str(ids["account"]),
        }
    )

    service._get_status_id = MagicMock(
        side_effect=lambda name: {
            "queued": uuid4(),
            "running": uuid4(),
            "completed": ids["status"],
            "failed": uuid4(),
        }[name]
    )

    service._set_publication_status = MagicMock()
    service._create_publication_event = MagicMock()


@pytest.mark.asyncio
async def test_publish_success(service, ids):
    configure_publish_mocks(service, ids)

    service._publish_to_platform = AsyncMock(
        return_value={
            "platform_post_id": "linkedin-post-123",
            "platform_response": "success",
        }
    )

    service._get_publication = MagicMock(
        return_value=make_publication(ids)
    )

    result = await service.publish(
        user_id=ids["user"],
        draft_id=ids["draft"],
        connected_account_id=ids["account"],
    )

    assert result["status_name"] == "completed"
    assert result["platform_post_id"] == "linkedin-post-123"
    service._publish_to_platform.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_failure(service, ids):
    configure_publish_mocks(service, ids)

    service._publish_to_platform = AsyncMock(
        side_effect=RuntimeError("Platform publishing failed")
    )

    service._mark_publication_failed = MagicMock()
    service._get_publication = MagicMock(
        return_value=make_publication(ids, "failed")
    )

    result = await service.publish(
        user_id=ids["user"],
        draft_id=ids["draft"],
        connected_account_id=ids["account"],
    )

    assert result["status_name"] == "failed"
    assert result["error_message"] == "Platform publishing failed"

    service._publish_to_platform.assert_awaited_once()
    service._mark_publication_failed.assert_called_once()


@pytest.mark.asyncio
async def test_publish_draft_not_found(service, ids):
    service.generation_service.get_draft = MagicMock(return_value=None)

    with pytest.raises(Exception):
        await service.publish(
            user_id=ids["user"],
            draft_id=ids["draft"],
            connected_account_id=ids["account"],
        )


@pytest.mark.asyncio
async def test_publish_multiple(service):
    user_id = uuid4()

    results = [
        {"id": str(uuid4()), "status_name": "completed"},
        {"id": str(uuid4()), "status_name": "completed"},
    ]

    service.publish = AsyncMock(side_effect=results)

    publications = [
        {
            "draft_id": str(uuid4()),
            "connected_account_id": str(uuid4()),
        },
        {
            "draft_id": str(uuid4()),
            "connected_account_id": str(uuid4()),
        },
    ]

    result = await service.publish_multiple(
        user_id=user_id,
        publications=publications,
    )

    assert result == results
    assert service.publish.await_count == 2


def test_get_publications(service):
    user_id = uuid4()

    completed_status = uuid4()
    failed_status = uuid4()
    publication_id = uuid4()
    version_id = uuid4()
    platform_id = uuid4()

    service._get_status_id = MagicMock(
        side_effect=[completed_status, failed_status]
    )

    def query(data):
        q = MagicMock()
        q.in_.return_value = q
        q.eq.return_value = q
        q.order.return_value = q
        q.execute.return_value = MagicMock(data=data)
        return q

    published_posts = query([
        {
            "id": str(publication_id),
            "draft_id": str(uuid4()),
            "version_id": str(version_id),
            "status_id": str(completed_status),
            "user_id": str(user_id),
            "platform_id": str(platform_id),
            "connected_account_id": str(uuid4()),
            "platform_post_id": "post-123",
            "platform_response": "success",
            "error_message": None,
            "retry_count": 0,
        }
    ])

    versions = query([
        {
            "id": str(version_id),
            "draft_id": str(uuid4()),
            "full_post": "Published test message",
        }
    ])

    platforms = query([
        {
            "id": str(platform_id),
            "platform_name": "linkedin",
        }
    ])

    def table(name):
        table = MagicMock()

        if name == "published_posts":
            table.select.return_value = published_posts
        elif name == "generation_versions":
            table.select.return_value = versions
        elif name == "platforms":
            table.select.return_value = platforms

        return table

    service.db.table.side_effect = table

    result = service.get_publications(user_id=user_id)

    assert len(result) == 1
    assert result[0]["status_name"] == "completed"
    assert result[0]["full_message"] == "Published test message"
    assert result[0]["platform_name"] == "linkedin"


def test_get_publications_empty(service):
    service._get_status_id = MagicMock(
        side_effect=[uuid4(), uuid4()]
    )

    query = MagicMock()
    query.eq.return_value = query
    query.in_.return_value = query
    query.order.return_value = query
    query.execute.return_value = MagicMock(data=[])

    service.db.table.return_value.select.return_value = query

    result = service.get_publications(user_id=uuid4())

    assert result == []
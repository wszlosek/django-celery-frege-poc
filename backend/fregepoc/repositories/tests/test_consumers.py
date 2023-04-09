import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_api_key.models import APIKey

from fregepoc.repositories.consumers import LiveStatusConsumer
from fregepoc.repositories.factories import (
    RepositoryFactory,
    RepositoryFileFactory,
)
from fregepoc.repositories.serializers import (
    RepositoryFileSerializer,
    RepositorySerializer,
)


@pytest.fixture()
def api_key():
    _, key = APIKey.objects.create_key(name="test-key")
    return key


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestLiveStatusConsumer:
    @staticmethod
    @database_sync_to_async
    def _create_test_repository():
        return RepositoryFactory()

    @staticmethod
    @database_sync_to_async
    def _create_test_repository_file():
        return RepositoryFileFactory()

    @staticmethod
    async def _test_event_api(
        api_key, request_action, create_fn, response_action, serializer
    ):
        communicator = WebsocketCommunicator(
            LiveStatusConsumer.as_asgi(), "/ws/"
        )
        connected, _ = await communicator.connect()
        assert connected
        assert await communicator.receive_json_from() == {
            "type": "websocket.accept"
        }
        await communicator.send_json_to(
            {"type": "websocket.send", "text": api_key}
        )
        assert await communicator.receive_json_from() == {
            "type": "websocket.send",
            "text": "OK",
        }
        obj = await create_fn()
        await communicator.send_json_to(
            {
                "type": "websocket.send",
                "text": serializer(obj).data,
                "action": request_action,
            }
        )
        assert await communicator.receive_json_from() == {
            "type": "websocket.send",
            "text": "OK",
            "action": response_action,
        }
        await communicator.disconnect()

    async def test_subscribe_to_repository_file_activity(self, api_key):
        # tu blad
        pass
        await self._test_event_api(
            api_key=api_key,
            request_action="subscribe_to_repository_file_activity",
            create_fn=self._create_test_repository_file,
            response_action="repository_file/create",
            serializer=RepositoryFileSerializer,
        )

    async def test_subscribe_to_repository_activity(self, api_key):
        await self._test_event_api(
            api_key=api_key,
            request_action="subscribe_to_repository_activity",
            create_fn=self._create_test_repository,
            response_action="repository/create",
            serializer=RepositorySerializer,
        )

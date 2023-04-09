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


def _get_event_api_request(action, data):
    return {
        "type": "websocket.receive",
        "text": '{"action": "%s", "data": %s}' % (action, data),
    }

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
    def test_event_api(
        api_key,
        request_action,
        create_fn,
        response_action,
        serializer,
    ):
        async def _test_event_api():
            communicator = WebsocketCommunicator(
                LiveStatusConsumer, "/ws/"
            )
            connected, _ = await communicator.connect()
            assert connected

            await communicator.send_json_to(
                {
                    "action": "authenticate",
                    "data": {"api_key": api_key},
                }
            )
            response = await communicator.receive_json_from()
            assert response["action"] == "authenticated"
            assert response["data"] is True

            await communicator.send_json_to(
                _get_event_api_request(
                    request_action, serializer(create_fn()).data
                )
            )
            response = await communicator.receive_json_from()
            assert response["action"] == response_action
            assert response["data"] == serializer(create_fn()).data

            await communicator.disconnect()

        return _test_event_api

    async def test_subscribe_to_repository_file_activity(self, api_key):
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

#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from datetime import datetime
from uuid import UUID, uuid4

from argilla._constants import API_KEY_HEADER_NAME
from argilla.server.models import Response, User
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import (
    AnnotatorFactory,
    RecordFactory,
    ResponseFactory,
    WorkspaceFactory,
)


def test_create_record_response(client: TestClient, db: Session, admin: User, admin_auth_header: dict):
    record = RecordFactory.create()
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(f"/api/v1/records/{record.id}/responses", headers=admin_auth_header, json=response_json)

    assert response.status_code == 201
    assert db.query(Response).count() == 1

    response_body = response.json()
    assert db.get(Response, UUID(response_body["id"]))
    assert response_body == {
        "id": str(UUID(response_body["id"])),
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
        "user_id": str(admin.id),
        "inserted_at": datetime.fromisoformat(response_body["inserted_at"]).isoformat(),
        "updated_at": datetime.fromisoformat(response_body["updated_at"]).isoformat(),
    }


def test_create_record_response_without_authentication(client: TestClient, db: Session):
    record = RecordFactory.create()
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(f"/api/v1/records/{record.id}/responses", json=response_json)

    assert response.status_code == 401
    assert db.query(Response).count() == 0


def test_create_record_response_as_annotator(client: TestClient, db: Session):
    record = RecordFactory.create()
    annotator = AnnotatorFactory.create(workspaces=[record.dataset.workspace])
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(
        f"/api/v1/records/{record.id}/responses", headers={API_KEY_HEADER_NAME: annotator.api_key}, json=response_json
    )

    assert response.status_code == 201
    assert db.query(Response).count() == 1

    response_body = response.json()
    assert response_body == {
        "id": str(UUID(response_body["id"])),
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
        "user_id": str(annotator.id),
        "inserted_at": datetime.fromisoformat(response_body["inserted_at"]).isoformat(),
        "updated_at": datetime.fromisoformat(response_body["updated_at"]).isoformat(),
    }


def test_create_record_response_as_annotator_from_different_workspace(client: TestClient, db: Session):
    record = RecordFactory.create()
    annotator = AnnotatorFactory.create(workspaces=[WorkspaceFactory.build()])
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(
        f"/api/v1/records/{record.id}/responses", headers={API_KEY_HEADER_NAME: annotator.api_key}, json=response_json
    )

    assert response.status_code == 403
    assert db.query(Response).count() == 0


def test_create_record_response_already_created(client: TestClient, db: Session, admin: User, admin_auth_header: dict):
    record = RecordFactory.create()
    ResponseFactory.create(record=record, user=admin)
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(f"/api/v1/records/{record.id}/responses", headers=admin_auth_header, json=response_json)

    assert response.status_code == 409
    assert db.query(Response).count() == 1


def test_create_record_response_with_invalid_values(client: TestClient, db: Session, admin_auth_header: dict):
    record = RecordFactory.create()
    response_json = {"values": "invalid"}

    response = client.post(f"/api/v1/records/{record.id}/responses", headers=admin_auth_header, json=response_json)

    assert response.status_code == 422
    assert db.query(Response).count() == 0


def test_create_record_response_with_nonexistent_record_id(client: TestClient, db: Session, admin_auth_header: dict):
    RecordFactory.create()
    response_json = {
        "values": {
            "input_ok": {"value": "yes"},
            "output_ok": {"value": "yes"},
        },
    }

    response = client.post(f"/api/v1/records/{uuid4()}/responses", headers=admin_auth_header, json=response_json)

    assert response.status_code == 404
    assert db.query(Response).count() == 0


def test_list_record_responses(client: TestClient, db: Session, admin_auth_header: dict):
    record = RecordFactory.create()
    response_a = ResponseFactory.create(record=record)
    response_b = ResponseFactory.create(record=record)

    response = client.get(f"/api/v1/records/{record.id}/responses", headers=admin_auth_header)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(response_a.id),
                "values": response_a.values,
                "user_id": str(response_a.user_id),
                "inserted_at": response_a.inserted_at.isoformat(),
                "updated_at": response_a.updated_at.isoformat(),
            },
            {
                "id": str(response_b.id),
                "values": response_b.values,
                "user_id": str(response_b.user.id),
                "inserted_at": response_b.inserted_at.isoformat(),
                "updated_at": response_b.updated_at.isoformat(),
            },
        ]
    }


def test_list_record_responses_as_annotator(client: TestClient, db: Session, admin: User, admin_auth_header: dict):
    record = RecordFactory.create()
    annotator = AnnotatorFactory.create(workspaces=[record.dataset.workspace])
    response_a = ResponseFactory.create(record=record, user=annotator)
    ResponseFactory.create(record=record, user=admin)
    ResponseFactory.create(record=record)

    response = client.get(f"/api/v1/records/{record.id}/responses", headers={API_KEY_HEADER_NAME: annotator.api_key})

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(response_a.id),
                "values": response_a.values,
                "user_id": str(response_a.user_id),
                "inserted_at": response_a.inserted_at.isoformat(),
                "updated_at": response_a.updated_at.isoformat(),
            }
        ]
    }


def test_list_record_responses_as_annotator_from_different_workspace(client: TestClient, db: Session):
    record = RecordFactory.create()
    annotator = AnnotatorFactory.create(workspaces=[WorkspaceFactory.build()])

    response = client.get(f"/api/v1/records/{record.id}/responses", headers={API_KEY_HEADER_NAME: annotator.api_key})

    assert response.status_code == 403


def test_list_record_responses_with_nonexistent_record_id(client: TestClient, db: Session, admin_auth_header: dict):
    record = RecordFactory.create()
    ResponseFactory.create(record=record)

    response = client.get(f"/api/v1/records/{uuid4()}/responses", headers=admin_auth_header)

    assert response.status_code == 404
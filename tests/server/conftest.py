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

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from argilla.server.daos.backend import GenericElasticEngineBackend
from argilla.server.daos.datasets import DatasetsDAO
from argilla.server.daos.records import DatasetRecordsDAO
from argilla.server.search_engine import SearchEngine
from argilla.server.services.datasets import DatasetsService


@pytest_asyncio.fixture()
async def elastic_search_engine(elasticsearch_config: dict) -> AsyncGenerator[SearchEngine, None]:
    engine = SearchEngine(config=elasticsearch_config, es_number_of_replicas=0, es_number_of_shards=1)
    yield engine

    await engine.client.close()


@pytest.fixture(scope="session")
def es():
    return GenericElasticEngineBackend.get_instance()


@pytest.fixture(scope="session")
def records_dao(es: GenericElasticEngineBackend):
    return DatasetRecordsDAO.get_instance(es)


@pytest.fixture(scope="session")
def datasets_dao(records_dao: DatasetRecordsDAO, es: GenericElasticEngineBackend):
    return DatasetsDAO.get_instance(es=es, records_dao=records_dao)


@pytest.fixture(scope="session")
def datasets_service(datasets_dao: DatasetsDAO):
    return DatasetsService.get_instance(datasets_dao)

from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)

from pydantic import BaseModel
from pydantic.generics import GenericModel

from rubrix.server.commons.es_helpers import aggregations
from rubrix.server.tasks.commons import BaseRecord


GenericRecord = TypeVar("GenericRecord", bound=BaseRecord)


class BaseMetric(BaseModel):
    """
    Base model for rubrix dataset metrics summaries
    """

    id: str
    name: str
    description: str = None


class PythonMetric(BaseMetric, Generic[GenericRecord]):
    """
    A metric definition which will be calculated using raw queried data
    """

    def apply(self, records: Iterable[GenericRecord]) -> Dict[str, Any]:
        """
        Metric calculation method.

        Parameters
        ----------
        records:
            The matched records

        Returns
        -------
            The metric result
        """
        raise NotImplementedError()


class ElasticsearchMetric(BaseMetric):
    """
    A metric summarized by using one or several elasticsearch aggregations
    """

    def aggregation_request(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Configures the summary es aggregation definition
        """
        raise NotImplementedError()

    def aggregation_result(self, aggregation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the es aggregation result. Override this method
        for result customization

        Parameters
        ----------
        aggregation_result:
            Retrieved es aggregation result

        """
        return aggregation_result


class NestedPathElasticsearchMetric(ElasticsearchMetric):
    """
    A ``ElasticsearchMetric`` which need nested fields for summary calculation.

    Aggregations for nested fields need some extra configuration and this class
    encapsulate these common logic.

    Attributes:
    -----------
    nested_path:
        The nested
    """

    nested_path: str

    def inner_aggregation(self, *args, **kwargs) -> Dict[str, Any]:
        """The specific aggregation definition"""
        raise NotImplementedError()

    def aggregation_request(self, *args, **kwargs) -> Dict[str, Any]:
        """Implements the common mechanism to define aggregations with nested fields"""
        return {
            self.id: aggregations.nested_aggregation(
                nested_path=self.nested_path,
                inner_aggregation=self.inner_aggregation(*args, **kwargs),
            )
        }

    def compound_nested_field(self, inner_field: str) -> str:
        return f"{self.nested_path}.{inner_field}"


class BaseTaskMetrics(GenericModel, Generic[GenericRecord]):
    """
    Base class encapsulating related task metrics

    Attributes:
    -----------

    metrics:
        A list of configured metrics for task
    """

    metrics: ClassVar[List[BaseMetric]]

    @classmethod
    def configure_es_index(cls):
        """
        If some metrics require specific es field mapping definitions,
        include them here.

        """
        pass

    @classmethod
    def find_metric(cls, id: str) -> Optional[BaseMetric]:
        """
        Finds a metric by id

        Parameters
        ----------
        id:
            The metric id

        Returns
        -------
            Found metric if any, ``None`` otherwise

        """
        for metric in cls.metrics:
            if metric.id == id:
                return metric

    @classmethod
    def record_metrics(cls, record: GenericRecord) -> Dict[str, Any]:
        """
        Use this method is some configured metric requires additional
        records fields.

        Generated records will be persisted under ``metrics`` record path.
        For example, if you define a field called ``sentence_length`` like

        >>> def record_metrics(cls, record)-> Dict[str, Any]:
        ...     return { "sentence_length" : len(record.text) }

        The new field will be stored in elasticsearch in ``metrics.sentence_length``

        Parameters
        ----------
        record:
            The record used for calculate metrics fields

        Returns
        -------
            A dict with calculated metrics fields
        """
        return {}


class HistogramAggregation(ElasticsearchMetric):
    """
    Base elasticsearch histogram aggregation metric

    Attributes
    ----------
    field:
        The histogram field
    script:
        If provided, it will be used as scripted field
        for aggregation
    fixed_interval:
        If provided, it will used ALWAYS as the histogram
        aggregation interval
    """

    field: str
    script: Optional[Union[str, Dict[str, Any]]] = None
    fixed_interval: Optional[float] = None

    def aggregation_request(self, interval: float) -> Dict[str, Any]:
        if self.fixed_interval:
            interval = self.fixed_interval
        return {
            self.id: aggregations.histogram_aggregation(
                field_name=self.field, script=self.script, interval=interval
            )
        }


class TermsAggregation(ElasticsearchMetric):
    """
    The base elasticsearch terms aggregation metric

    Attributes
    ----------

    field:
        The term field
    script:
        If provided, it will be used as scripted field
        for aggregation
    fixed_size:
        If provided, the size will use for terms aggregation
    missing:
        If provided, will use the value for docs results with missing value for field

    """

    field: str = None
    script: Union[str, Dict[str, Any]] = None
    fixed_size: Optional[int] = None
    missing: Optional[str] = None

    def aggregation_request(self, size: int = None) -> Dict[str, Any]:
        if self.fixed_size:
            size = self.fixed_size
        return {
            self.id: aggregations.terms_aggregation(
                self.field, script=self.script, size=size, missing=self.missing
            )
        }

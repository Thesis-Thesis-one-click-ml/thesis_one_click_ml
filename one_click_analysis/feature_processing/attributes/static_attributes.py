import abc
from typing import Optional

from pycelonis.celonis_api.pql import pql

from one_click_analysis import utils
from one_click_analysis.feature_processing.attributes.attribute import Attribute
from one_click_analysis.feature_processing.attributes.attribute import (
    AttributeDataType,
)
from one_click_analysis.feature_processing.attributes.attribute import AttributeType
from one_click_analysis.process_config.process_config import ProcessConfig


class StaticAttribute(Attribute, abc.ABC):
    display_name = "Static attribute"

    def __init__(
        self,
        process_config: ProcessConfig,
        attribute_name: str,
        pql_query: pql.PQLColumn,
        data_type: AttributeDataType,
        attribute_type: AttributeType,
        is_feature: bool = False,
        is_class_feature: bool = False,
        unit: str = "",
        column_name: Optional[str] = None,
    ):
        super().__init__(
            process_config=process_config,
            attribute_name=attribute_name,
            pql_query=pql_query,
            data_type=data_type,
            attribute_type=attribute_type,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
            unit=unit,
            column_name=column_name,
        )

    def get_query_with_value(self, value: Optional[str] = None):
        """Get PQL query for the attribute for a specific value. If the
        attribute was one-hot-encoded, the query for just the value is used. The
        result will be 0s and 1s. If the attribute was not one-hot-encoded, the
        pql query is the same as for the attribute.

        :param value: specific value of the attribute (from one-hot-encoding)
        :return: the PQL query
        """
        return self.pql_query


class CaseDurationAttribute(StaticAttribute):
    """Duration of the whle case"""

    display_name = "Case duration"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        time_aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.time_aggregation = time_aggregation
        self.attribute_name = "Case duration"
        self.activity_table = self.process_config.table_dict[activity_table_str]
        pql_query = self._gen_query()
        super().__init__(
            process_config=process_config,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            data_type=AttributeDataType.NUMERICAL,
            attribute_type=AttributeType.OTHER,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
            unit=self.time_aggregation.lower(),
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "(CALC_THROUGHPUT(ALL_OCCURRENCE['Process Start'] TO ALL_OCCURRENCE["
            "'Process End'], REMAP_TIMESTAMPS(\""
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.eventtime_col_str
            + '", '
            "" + self.time_aggregation + ")))"
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class WorkInProgressAttribute(StaticAttribute):
    """Work in Progress for whole case"""

    display_name = "Work in Progress during case"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.aggregation = aggregation
        aggregation_df_name = utils.get_aggregation_df_name(aggregation)
        self.attribute_name = "Case Work in progress" + " (" + aggregation_df_name + ")"
        pql_query = self._gen_query()
        super().__init__(
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            data_type=AttributeDataType.NUMERICAL,
            attribute_type=AttributeType.OTHER,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "PU_"
            + self.aggregation
            + ' ( "'
            + self.activity_table.case_table_str
            + '", '
            "RUNNING_SUM( "
            "CASE WHEN "
            'INDEX_ACTIVITY_ORDER ( "'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.activity_col_str
            + '" ) = 1 THEN 1'
            " WHEN "
            'INDEX_ACTIVITY_ORDER_REVERSE ( "'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.activity_col_str
            + '" ) = 1 THEN -1 ELSE 0 END, ORDER BY ( "'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.eventtime_col_str
            + '" ) ) )'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class EventCountAttribute(StaticAttribute):
    """Event Count for a whole case"""

    display_name = "Case Event count"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = "Case Event count"
        pql_query = self._gen_query()
        super().__init__(
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            data_type=AttributeDataType.NUMERICAL,
            attribute_type=AttributeType.OTHER,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_COUNT("' + self.activity_table.case_table_str + '", '
            '"'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.activity_col_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ActivityOccurenceAttribute(StaticAttribute):
    """Rework occurence for a whole case"""

    display_name = "Activity occurence in case"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        activity: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.activity = activity
        self.attribute_name = f"Activity = {self.activity} (occurence)"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.CATEGORICAL,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            attribute_type=AttributeType.OTHER,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            f'CASE WHEN PU_SUM("{self.activity_table.case_table_str}", CASE WHEN "'
            f'{self.activity_table.table_str}"."'
            f"{self.activity_table.activity_col_str}\" = '{self.activity}' THEN 1 "
            f"ELSE 0"
            f" END) >= 1 THEN 1 ELSE 0 END"
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ReworkCountAttribute(StaticAttribute):
    """Count of reworked activities"""

    display_name = "Rework count in case"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.attribute_name = f"Case Rework count (all activities)"
        self.activity_table = self.process_config.table_dict[activity_table_str]
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.NUMERICAL,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f"""
            PU_SUM("{self.activity_table.case_table_str}",
                CASE
                    WHEN INDEX_ACTIVITY_TYPE (
                        "{self.activity_table.table_str}".
                        "{self.activity_table.activity_col_str}") > 1
                    THEN 1
                    ELSE 0
                END)
            """
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ReworkOccurrenceAttribute(StaticAttribute):
    """Whether any activity was done more than once"""

    display_name = "Rework occurence in case"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = f"Case Rework occurence (any activity)"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.CATEGORICAL,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f"""
            CASE
            WHEN PU_SUM("{self.activity_table.case_table_str}",
                CASE
                    WHEN INDEX_ACTIVITY_TYPE (
                        "{self.activity_table.table_str}".
                        "{self.activity_table.activity_col_str}") > 1
                    THEN 1
                    ELSE 0
                END) >=1 THEN 1 ELSE 0 END
            """
        return pql.PQLColumn(query=q, name=self.attribute_name)


class StartActivityAttribute(StaticAttribute):
    """Start activity"""

    display_name = "Start activity"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = f"Start activity"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.CATEGORICAL,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_FIRST("' + self.activity_table.case_table_str + '", '
            '"'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.activity_col_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)

    def get_query_with_value(self, value: Optional[str] = None):
        """Get PQL query for the attribute for a specific value. If the
        attribute was one-hot-encoded, the query for just the value is used. The
        result will be 0s and 1s. If the attribute was not one-hot-encoded, the
        pql query is the same as for the attribute.

        :param value: specific value of the attribute (from one-hot-encoding)
        :return: the PQL query
        """
        q = (
            f'CASE WHEN  PU_FIRST("{self.activity_table.case_table_str}", '
            + f'"{self.activity_table.table_str}"."'
            f"{self.activity_table.activity_col_str}\" = '{value}') THEN 1 ELSE "
            f"0 END"
        )

        return pql.PQLColumn(name=f"{self.attribute_name} = {value}", query=q)


class EndActivityAttribute(StaticAttribute):
    """End activity"""

    display_name = "End activity"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = f"End activity"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.CATEGORICAL,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_LAST("' + self.activity_table.case_table_str + '", '
            '"'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.activity_col_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)

    def get_query_with_value(self, value: Optional[str] = None):
        """Get PQL query for the attribute for a specific value. If the
        attribute was one-hot-encoded, the query for just the value is used. The
        result will be 0s and 1s. If the attribute was not one-hot-encoded, the
        pql query is the same as for the attribute.

        :param value: specific value of the attribute (from one-hot-encoding)
        :return: the PQL query
        """
        q = (
            f'CASE WHEN  PU_LAST("{self.activity_table.case_table_str}", '
            + f'"{self.activity_table.table_str}"."'
            f"{self.activity_table.activity_col_str}\" = '{value}') THEN 1 ELSE "
            f"0 END"
        )

        return pql.PQLColumn(name=f"{self.attribute_name} = {value}", query=q)


class NumericActivityTableColumnAttribute(StaticAttribute):
    """Any numeric activity table column."""

    display_name = "Numeric activity table column aggregation"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        column_name: str,
        aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.column_name = column_name
        self.aggregation = aggregation  # aggregation for PU function
        aggregation_pretty_name = utils.get_aggregation_df_name(aggregation)
        self.attribute_name = (
            f"{self.activity_table.table_str}."
            f"{self.column_name} ("
            f"{aggregation_pretty_name})"
        )
        self.display_name = (
            f"Numeric activity table column (aggregation={aggregation_pretty_name})"
        )
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.NUMERICAL,
            attribute_type=AttributeType.ACTIVITY_COL,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
            column_name=column_name,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "PU_" + self.aggregation + '("' + self.activity_table.case_table_str + '", '
            '"' + self.activity_table.table_str + '"."' + self.column_name + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class CaseTableColumnAttribute(StaticAttribute):
    """Any case table column."""

    def __init__(
        self,
        process_config: ProcessConfig,
        table_name: str,
        column_name: str,
        attribute_datatype: AttributeDataType,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.table_name = table_name
        self.column_name = column_name
        self.attribute_name = f"{table_name}." f"{self.column_name}"
        self.display_name = f"{table_name} column"
        pql_query = self._gen_query()
        attribute_type = AttributeType.CASE_COL
        super().__init__(
            pql_query=pql_query,
            data_type=attribute_datatype,
            attribute_type=attribute_type,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
            column_name=column_name,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f'"{self.table_name}"."{self.column_name}"'
        return pql.PQLColumn(query=q, name=self.attribute_name)

    def get_query_with_value(self, value: Optional[str] = None):
        """Get PQL query for the attribute for a specific value. If the
        attribute was one-hot-encoded, the query for just the value is used. The
        result will be 0s and 1s. If the attribute was not one-hot-encoded, the
        pql query is the same as for the attribute.

        :param value: specific value of the attribute (from one-hot-encoding)
        :return: the PQL query
        """
        q = (
            f'CASE WHEN "{self.table_name}"."{self.column_name}" = '
            f"'{value}' THEN 1 ELSE 0 END"
        )

        return pql.PQLColumn(name=f"{self.attribute_name} = {value}", query=q)


class TransitionOccurenceAttribute(StaticAttribute):
    """Whether a transition happens in a case"""

    display_name = "Transition occurence in case"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
        transition_start: str,
        transition_end: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.transition_start = transition_start
        self.transition_end = transition_end
        self.attribute_name = (
            f"Transition occurence ({transition_start} -> {transition_end})"
        )
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.CATEGORICAL,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            f'CASE WHEN PROCESS ON "{self.activity_table.table_str}"."'
            f'{self.activity_table.activity_col_str}" EQUALS '
            f"'{self.transition_start}' TO "
            f"'{self.transition_end}' THEN 1 ELSE 0 END"
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class StartActivityTimeAttribute(StaticAttribute):
    """Start activity time"""

    display_name = "Start activity time"

    def __init__(
        self,
        process_config: ProcessConfig,
        activity_table_str: str,
    ):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = f"Start activity Time"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.DATETIME,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=False,
            is_class_feature=False,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_FIRST("' + self.activity_table.case_table_str + '", '
            '"'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.eventtime_col_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class EndActivityTimeAttribute(StaticAttribute):
    """End activity time"""

    display_name = "End activity time"

    def __init__(self, process_config: ProcessConfig, activity_table_str: str):
        self.process_config = process_config
        self.activity_table = self.process_config.table_dict[activity_table_str]
        self.attribute_name = f"End activity Time"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            data_type=AttributeDataType.DATETIME,
            attribute_type=AttributeType.OTHER,
            process_config=self.process_config,
            attribute_name=self.attribute_name,
            is_feature=False,
            is_class_feature=False,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_Last("' + self.activity_table.case_table_str + '", '
            '"'
            + self.activity_table.table_str
            + '"."'
            + self.activity_table.eventtime_col_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)

    def gen_query_with_value(self, value: Optional[str] = None):
        return self.pql_query

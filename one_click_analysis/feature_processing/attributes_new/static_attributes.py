import abc

from prediction_builder.data_extraction import ProcessModel
from pycelonis.celonis_api.pql import pql

from one_click_analysis.feature_processing.attributes_new import attribute_utils
from one_click_analysis.feature_processing.attributes_new.attribute import Attribute


class StaticAttribute(Attribute, abc.ABC):
    def __init__(
        self,
        process_model: ProcessModel,
        attribute_name: str,
        pql_query: pql.PQLColumn,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        super().__init__(
            process_model=process_model,
            attribute_name=attribute_name,
            pql_query=pql_query,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )


class CaseDurationAttribute(StaticAttribute):
    """Duration of the whle case"""

    def __init__(
        self,
        process_model: ProcessModel,
        time_aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.time_aggregation = time_aggregation
        self.attribute_name = "Case duration"
        pql_query = self._gen_query()
        super().__init__(
            process_model=process_model,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "(CALC_THROUGHPUT(ALL_OCCURRENCE['Process Start'] TO ALL_OCCURRENCE["
            "'Process End'], REMAP_TIMESTAMPS(\""
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.eventtime_col
            + '", '
            "" + self.process_model.timestamp_column_str + ")))"
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class WorkInProgressAttribute(StaticAttribute):
    """Work in Progress for whole case"""

    def __init__(
        self,
        process_model: ProcessModel,
        aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.aggregation = aggregation
        aggregation_df_name = attribute_utils.get_aggregation_df_name(aggregation)
        self.attribute_name = "Case Work in progress" + " (" + aggregation_df_name + ")"
        pql_query = self._gen_query()
        super().__init__(
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "PU_"
            + self.aggregation
            + ' ( "'
            + self.process_model.case_table_str
            + '", '
            "RUNNING_SUM( "
            "CASE WHEN "
            'INDEX_ACTIVITY_ORDER ( "'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.activity_column_str
            + '" ) = 1 THEN 1'
            " WHEN "
            'INDEX_ACTIVITY_ORDER_REVERSE ( "'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.activity_col
            + '" ) = 1 THEN -1 ELSE 0 END, ORDER BY ( "'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.timestamp_column_str
            + '" ) ) )'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class EventCountAttribute(StaticAttribute):
    """Event Count for a whole case"""

    def __init__(
        self,
        process_model: ProcessModel,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.attribute_name = "Case Event count"
        pql_query = self._gen_query()
        super().__init__(
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            pql_query=pql_query,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_COUNT("' + self.process_model.case_table_str + '", '
            '"'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.activity_column_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ActivityOccurenceAttribute(StaticAttribute):
    """Rework occurence for a whole case"""

    def __init__(
        self,
        process_model: ProcessModel,
        activity: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.activity = activity
        self.attribute_name = f"Activity = {self.activity} (occurence)"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            f'CASE WHEN PU_SUM("{self.process_model.case_table_str}", CASE WHEN "'
            f'{self.process_model.activity_table_str}"."'
            f"{self.process_model.activity_column_str}\" = '{self.activity}' THEN 1 "
            f"ELSE 0"
            f" END) >= 1 THEN 1 ELSE 0 END"
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ReworkCountAttribute(StaticAttribute):
    """Count of reworked activities"""

    def __init__(
        self,
        process_model: ProcessModel,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.attribute_name = f"Case Rework count (all activities)"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f"""
            PU_SUM("{self.process_model.case_table_str}",
                CASE
                    WHEN INDEX_ACTIVITY_TYPE (
                        {self.process_model.activity_column.query}) > 1
                    THEN 1
                    ELSE 0
                END)
            """
        return pql.PQLColumn(query=q, name=self.attribute_name)


class ReworkOccurrenceAttribute(StaticAttribute):
    """Whether any activity was done more than once"""

    def __init__(
        self,
        process_model: ProcessModel,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.attribute_name = f"Case Rework occurence (any activity)"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f"""
            CASE
            WHEN PU_SUM("{self.process_model.case_table_str}",
                CASE
                    WHEN INDEX_ACTIVITY_TYPE (
                        {self.process_model.activity_column.query}) > 1
                    THEN 1
                    ELSE 0
                END) >=1 THEN 1 ELSE 0 END
            """
        return pql.PQLColumn(query=q, name=self.attribute_name)


class StartActivityAttribute(StaticAttribute):
    """Start activity"""

    def __init__(
        self,
        process_model: ProcessModel,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.attribute_name = f"Start activity"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_FIRST("' + self.process_model.case_table_str + '", '
            '"'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.activity_column_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class EndActivityAttribute(StaticAttribute):
    """End activity"""

    def __init__(
        self,
        process_model: ProcessModel,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.attribute_name = f"End activity"
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            'PU_LAST("' + self.process_model.case_table_str + '", '
            '"'
            + self.process_model.activity_table_str
            + '"."'
            + self.process_model.activity_column_str
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class NumericActivityTableColumnAttribute(StaticAttribute):
    """Any numeric activity table column."""

    def __init__(
        self,
        process_model: ProcessModel,
        column_name: str,
        aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.column_name = column_name
        self.aggregation = aggregation  # aggregation for PU function
        self.attribute_name = (
            f"{self.process_model.activity_table_str}."
            f"{self.column_name} ("
            f"{attribute_utils.get_aggregation_df_name(aggregation)})"
        )
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = (
            "PU_" + self.aggregation + '("' + self.process_model.case_table_str + '", '
            '"'
            + self.process_model.activity_table_str
            + '"."'
            + self.column_name
            + '")'
        )
        return pql.PQLColumn(query=q, name=self.attribute_name)


class CaseTableColumnAttribute(StaticAttribute):
    """Any case table column."""

    def __init__(
        self,
        process_model: ProcessModel,
        column_name: str,
        aggregation: str,
        is_feature: bool = False,
        is_class_feature: bool = False,
    ):
        self.process_model = process_model
        self.column_name = column_name
        self.aggregation = aggregation  # aggregation for PU function
        self.attribute_name = (
            f"{self.process_model.case_table_str}." f"{self.column_name}"
        )
        pql_query = self._gen_query()
        super().__init__(
            pql_query=pql_query,
            process_model=self.process_model,
            attribute_name=self.attribute_name,
            is_feature=is_feature,
            is_class_feature=is_class_feature,
        )

    def _gen_query(self) -> pql.PQLColumn:
        q = f'"{self.process_model.case_table_str}"."{self.column_name}"'
        return pql.PQLColumn(query=q, name=self.attribute_name)
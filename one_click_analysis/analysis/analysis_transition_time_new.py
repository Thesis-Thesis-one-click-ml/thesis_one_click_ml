from typing import List
from typing import Optional

from IPython.display import display
from ipywidgets import Tab
from ipywidgets import widgets

from one_click_analysis.configuration.configurations import ActivityTableConfig
from one_click_analysis.configuration.configurations import AttributeSelectionConfig
from one_click_analysis.configuration.configurations import DatamodelConfig
from one_click_analysis.configuration.configurations import DatePickerConfig
from one_click_analysis.configuration.configurations import IsClosedConfig
from one_click_analysis.configuration.configurations import TransitionConfig
from one_click_analysis.configuration.configurator import Configurator
from one_click_analysis.configuration.configurator_view import ConfiguratorView
from one_click_analysis.feature_processing.processors.analysis_processors import (
    TransitionTimeProcessor,
)
from one_click_analysis.gui.decision_rule_screen import DecisionRulesScreen
from one_click_analysis.gui.description_screen import DescriptionScreen
from one_click_analysis.gui.overview_screen import OverviewScreenTransitionTime
from one_click_analysis.gui.statistical_analysis_screen import (
    StatisticalAnalysisScreen,
)


class AnalysisTransitionTime:
    """Analysis of potential effects on case duration."""

    def __init__(self, login: Optional[dict] = None):
        """

        :param datamodel: datamodel name or id
        :param celonis_login: dict with login information
        """

        self.activity_table_str = None
        self.datamodel = None
        self.login = login
        self.dm = None
        self.process_config = None
        self.transition_time_processor = None
        self.df_total_time = None
        self.configurator = None
        self.description_view = None
        self.config_view = None
        self.overview_screen = None
        self.stat_analysis_screen = None
        self.dec_rule_screen = None
        self.expert_screen = None
        self.attr_selection = None
        self.tabs = None
        self.tab_names = [
            "Description",
            "Configurations",
            "Overview",
            "Statistical Analysis",
            "Decision Rules",
        ]

        self.selected_attributes = []
        self.selected_activity_table_cols = []
        self.selected_case_table_cols = []

    def _create_description(self):
        static_attributes = (
            TransitionTimeProcessor.potential_static_attributes_descriptors
        )
        dynamic_attributes = (
            TransitionTimeProcessor.potential_dynamic_attributes_descriptors
        )
        name_str = "Bottleneck / Transition-Time Analysis"
        goal_str = (
            "The goal of the bottleneck analysis is to get insights into the "
            "possible root causes of long transition times between two "
            "directly-following activities."
        )
        definition_str = (
            "The transition time is the time between two "
            "directly-following activities."
        )

        self.description_view = DescriptionScreen(
            analysis_name=name_str,
            analysis_goal=goal_str,
            analysis_definition=definition_str,
            static_attribute_descriptors=static_attributes,
            dynamic_attribute_descriptors=dynamic_attributes,
        )
        self.description_view.create_description_screen()

    def _create_config(self):
        """Create config view.
        The analysis needs the following configs:
        DatamodelConfig
        ActivityTableConfig
        DatePickerConfig
        AttributeSelectionConfig

        :return:
        """
        self.configurator = Configurator()
        config_dm = DatamodelConfig(
            configurator=self.configurator, celonis_login=self.login, required=True
        )
        config_activity_table = ActivityTableConfig(
            configurator=self.configurator,
            datamodel_identifier="datamodel",
            required=True,
        )

        config_closed_cases = IsClosedConfig(
            configurator=self.configurator,
            datamodel_identifier="datamodel",
            activity_table_identifier="activity_table",
            required=True,
            additional_prerequsit_config_ids=[],
        )

        config_datepicker = DatePickerConfig(
            configurator=self.configurator,
            datamodel_identifier="datamodel",
            activity_table_identifier="activity_table",
            required=False,
            additional_prerequsit_config_ids=["is_closed"],
        )

        config_transition = TransitionConfig(
            configurator=self.configurator,
            datamodel_identifier="datamodel",
            activitytable_identifier="activity_table",
            required=True,
            additional_prerequsit_config_ids=["datepicker"],
        )

        static_attributes = (
            TransitionTimeProcessor.potential_static_attributes_descriptors
        )
        dynamic_attributes = (
            TransitionTimeProcessor.potential_dynamic_attributes_descriptors
        )
        config_attributeselector = AttributeSelectionConfig(
            configurator=self.configurator,
            static_attribute_descriptors=static_attributes,
            dynamic_attribute_descriptors=dynamic_attributes,
            datamodel_identifier="datamodel",
            activity_table_identifier="activity_table",
            required=False,
            additional_prerequsit_config_ids=["transition"],
        )

        # Set the subsequrnt configurations that are updated when the respective
        # configuration is applied or updated itself
        config_dm.subsequent_configurations = [config_activity_table]
        config_activity_table.subsequent_configurations = [config_closed_cases]
        config_closed_cases.subsequent_configurations = [config_datepicker]
        config_datepicker.subsequent_configurations = [config_transition]
        config_transition.subsequent_configurations = [
            config_attributeselector,
        ]

        config_attributeselector.subsequent_configurations = []
        self.config_view = ConfiguratorView(
            configurations=[
                config_dm,
                config_activity_table,
                config_closed_cases,
                config_datepicker,
                config_transition,
                config_attributeselector,
            ],
            run_analysis=self.run_analysis,
        )

    def run(self):
        # 1. Connect to Celonis and get dm
        self._create_description()
        self._create_config()

        # 2. Create FeatureProcessor and Configurator
        # self.process_config =

        self.tabs = self.create_tabs(
            [
                self.description_view.description_box,
                self.config_view.configurator_box,
                widgets.VBox(),
                widgets.VBox(),
                widgets.VBox(),
            ]
        )
        display(self.tabs)

    def run_analysis(self):
        # Reset fp from a previous run

        # Get configurations
        datepicker_configs = self.configurator.config_dict.get("datepicker")
        if datepicker_configs is not None:
            start_date = datepicker_configs.get("date_start")
            end_date = datepicker_configs.get("date_end")
        else:
            start_date = None
            end_date = None

        self.process_config = self.configurator.config_dict["datamodel"][
            "process_config"
        ]
        activity_table_str = self.configurator.config_dict["activity_table"][
            "activity_table_str"
        ]
        is_closed_query = self.configurator.config_dict["is_closed"]["pql_query"]

        source_activity = self.configurator.config_dict["transition"]["source_activity"]
        target_activity = self.configurator.config_dict["transition"]["target_activity"]

        used_static_attribute_descriptors = self.configurator.config_dict[
            "attribute_selection"
        ]["static_attributes"]
        used_dynamic_attribute_descriptors = self.configurator.config_dict[
            "attribute_selection"
        ]["dynamic_attributes"]
        considered_activity_table_cols = self.configurator.config_dict[
            "attribute_selection"
        ]["activity_table_cols"]
        considered_case_level_table_cols = self.configurator.config_dict[
            "attribute_selection"
        ]["case_level_table_cols"]
        time_unit = "DAYS"

        self.transition_time_processor = TransitionTimeProcessor(
            process_config=self.process_config,
            activity_table_str=activity_table_str,
            used_static_attribute_descriptors=used_static_attribute_descriptors,
            used_dynamic_attribute_descriptors=used_dynamic_attribute_descriptors,
            considered_activity_table_cols=considered_activity_table_cols,
            considered_case_level_table_cols=considered_case_level_table_cols,
            is_closed_query=is_closed_query,
            source_activity=source_activity,
            target_activity=target_activity,
            time_unit=time_unit,
            start_date=start_date,
            end_date=end_date,
        )
        self.transition_time_processor.process()

        # 3. Create the GUI

        # Create overview box
        self.overview_screen = OverviewScreenTransitionTime(
            self.transition_time_processor.df_x,
            self.transition_time_processor.df_target,
            self.transition_time_processor.features,
            self.transition_time_processor.target_features,
            self.transition_time_processor.df_timestamp_column,
            source_activity,
            target_activity,
            self.transition_time_processor.num_cases,
        )

        attributes = (
            self.transition_time_processor.used_static_attributes
            + self.transition_time_processor.used_dynamic_attributes
        )

        # Ceate statistical analysis tab
        self.stat_analysis_screen = StatisticalAnalysisScreen(
            self.transition_time_processor.df_x,
            self.transition_time_processor.df_target,
            attributes,
            self.transition_time_processor.features,
            self.transition_time_processor.target_features,
            self.transition_time_processor.df_timestamp_column,
            datapoint_str="Cases",
        )
        self.stat_analysis_screen.create_statistical_screen()

        # Create decision rule miner box
        df_combined = self.transition_time_processor.df_x
        df_combined[
            self.transition_time_processor.df_target.columns.tolist()
        ] = self.transition_time_processor.df_target
        self.dec_rule_screen = DecisionRulesScreen(
            df_combined,
            features=self.transition_time_processor.features,
            target_features=self.transition_time_processor.target_features,
            attributes=attributes,
        )
        self.dec_rule_screen.create_decision_rule_screen()

        # Create expert box
        # attributes = self.case_duration_processor.static_attributes +
        # self.case_duration_processor.dynamic_attributes

        # self.expert_screen = ExpertScreen(
        #    attributes=attributes,
        #    activity_table_cols=self.fp.dynamic_categorical_cols
        #    + self.fp.dynamic_numerical_cols,
        #    case_table_cols={
        #        "table name": self.fp.static_categorical_cols
        #        + self.fp.static_numerical_cols
        #    },
        #    features=self.fp.features,
        #    attr_selection=self.attr_selection,
        # )
        # self.expert_screen.create_expert_box()

        # Create tabs
        self.update_tabs(
            [
                self.description_view.description_box,
                self.config_view.configurator_box,
                self.overview_screen.overview_box,
                self.stat_analysis_screen.statistical_analysis_box,
                self.dec_rule_screen.decision_rule_box,
            ]
        )
        # out.close()
        # del out
        # display(self.tabs)

    def create_tabs(self, tab_contents: List[widgets.widget.Widget]):
        """Create the tabs for the GUI.

        :return:
        """
        tab = Tab(tab_contents)
        for i, el in enumerate(self.tab_names):
            tab.set_title(i, el)

        return tab

    def update_tabs(self, tab_contents: List[widgets.widget.Widget]):
        self.tabs.children = tab_contents

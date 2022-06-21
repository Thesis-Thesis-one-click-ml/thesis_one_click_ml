from typing import List

from IPython.display import display
from ipywidgets import Tab
from ipywidgets import widgets

from one_click_analysis.configuration.configurations_new import AttributeSelectionConfig
from one_click_analysis.configuration.configurator_class import Configurator
from one_click_analysis.configuration.configurator_new import ConfiguratorView
from one_click_analysis.feature_processing.processors.analysis_processors import (
    IncompleteCaseProcessor,
)
from one_click_analysis.gui.decision_rule_screen import DecisionRulesScreen
from one_click_analysis.gui.description_screen import DescriptionScreen
from one_click_analysis.gui.statistical_analysis_screen_new import (
    StatisticalAnalysisScreen,
)


class AnalysisIncompleteViolation:
    """Analysis of potential effects on case duration."""

    def __init__(
        self,
        configurator: Configurator,
        time_unit: str = "DAYS",
        th: float = 0.3,
    ):
        """

        :param datamodel: datamodel name or id
        :param celonis_login: dict with login information
        """

        self.activity_table_str = None
        self.configurator = self._create_initial_configurator(configurator)
        self.time_unit = time_unit
        self.datamodel = None
        self.th = th
        self.dm = None
        self.process_config = None
        self.incomplete_processor = None
        self.df_total_time = None
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
            "Statistical Analysis",
            "Decision Rules",
        ]

        self.selected_attributes = []
        self.selected_activity_table_cols = []
        self.selected_case_table_cols = []

    def _create_initial_configurator(self, configurator: Configurator):
        """Create an initial configurator with the attribute of another
        configurator. Basically it is creating the configurator with the same
        attributes. This is fine because the object in the attributes (e.g. the
        datamodel) will not be changed.

        :param configurator: configurator with populated attributes
        :return: initialized
        """
        configurator_init = Configurator()
        configurator_init.config_dict = configurator.config_dict
        configurator_init.filter_dict = configurator.filter_dict
        return configurator_init

    def _create_description(self):
        static_attributes = (
            IncompleteCaseProcessor.potential_static_attributes_descriptors
        )
        dynamic_attributes = (
            IncompleteCaseProcessor.potential_dynamic_attributes_descriptors
        )
        name_str = "Incomplete case violation Analysis"
        goal_str = (
            "The goal of the Incomplete case violation analysis is to get insights "
            "into the possible root causes of incomplete cases. Both closed and "
            "unclosed cases are used for this analysis."
        )
        definition_str = (
            "A case is incomplete if ... Not 100% sure, need to ask how it is defined"
        )

        self.description_view = DescriptionScreen(
            analysis_name=name_str,
            analysis_goal=goal_str,
            analysis_definition=definition_str,
            static_attribute_descriptors=static_attributes,
            dynamic_attribute_descriptors=dynamic_attributes,
        )
        self.description_view.create_description_screen()

    def _create_config(self, out):
        """Create config view.
        The analysis needs the following configs:
        DatamodelConfig
        ActivityTableConfig
        DatePickerConfig
        AttributeSelectionConfig

        :return:
        """
        static_attributes = (
            IncompleteCaseProcessor.potential_static_attributes_descriptors
        )
        dynamic_attributes = (
            IncompleteCaseProcessor.potential_dynamic_attributes_descriptors
        )
        config_attributeselector = AttributeSelectionConfig(
            configurator=self.configurator,
            static_attribute_descriptors=static_attributes,
            dynamic_attribute_descriptors=dynamic_attributes,
            datamodel_identifier="datamodel",
            activity_table_identifier="activity_table",
            required=False,
            additional_prerequsit_config_ids=[],
        )

        # Set the subsequrnt configurations that are updated when the respective
        # configuration is applied or updated itself
        config_attributeselector.subsequent_configurations = []
        self.config_view = ConfiguratorView(
            configurations=[
                config_attributeselector,
            ],
            run_analysis=self.run_analysis,
            out=out,
        )

    def run(self):
        out = widgets.Output(layout={"border": "1px solid black"})
        display(out)
        out.append_stdout("\nConfiguration...")
        # 1. Connect to Celonis and get dm
        self._create_description()
        self._create_config(out=out)

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
        # display(self.tabs)

    def run_analysis(self, out: widgets.Output):
        # Reset fp from a previous run
        out.append_stdout("\nFetching data and preprocessing...")

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
        is_closed_query = self.configurator.config_dict["is_closed"]["pql_query"]

        activity_table_str = self.configurator.config_dict["activity_table"][
            "activity_table_str"
        ]
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
        conformance_query = self.configurator.config_dict["conformance_query"][
            "conformance_query"
        ]

        time_unit = "DAYS"

        self.incomplete_processor = IncompleteCaseProcessor(
            process_config=self.process_config,
            activity_table_str=activity_table_str,
            used_static_attribute_descriptors=used_static_attribute_descriptors,
            used_dynamic_attribute_descriptors=used_dynamic_attribute_descriptors,
            considered_activity_table_cols=considered_activity_table_cols,
            considered_case_level_table_cols=considered_case_level_table_cols,
            conformance_query=conformance_query,
            is_closed_query=is_closed_query,
            time_unit=time_unit,
            start_date=start_date,
            end_date=end_date,
        )
        self.incomplete_processor.process()
        out.append_stdout("\nDone")

        # 3. Create the GUI
        out.append_stdout("\nCreatng GUI...")

        attributes = (
            self.incomplete_processor.used_static_attributes
            + self.incomplete_processor.used_dynamic_attributes
        )

        # Ceate statistical analysis tab
        self.stat_analysis_screen = StatisticalAnalysisScreen(
            self.incomplete_processor.df_x,
            self.incomplete_processor.df_target,
            attributes,
            self.incomplete_processor.features,
            self.incomplete_processor.target_features,
            self.incomplete_processor.df_timestamp_column,
            datapoint_str="Cases",
            th=self.th,
        )
        self.stat_analysis_screen.create_statistical_screen()

        # Create decision rule miner box
        df_combined = self.incomplete_processor.df_x
        df_combined[
            self.incomplete_processor.df_target.columns.tolist()
        ] = self.incomplete_processor.df_target
        self.dec_rule_screen = DecisionRulesScreen(
            df_combined,
            features=self.incomplete_processor.features,
            target_features=self.incomplete_processor.target_features,
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

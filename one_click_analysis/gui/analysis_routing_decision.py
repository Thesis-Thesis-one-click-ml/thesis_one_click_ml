from typing import List
from typing import Optional

from IPython.display import display
from ipywidgets import Tab
from ipywidgets import widgets

from one_click_analysis import utils
from one_click_analysis.attribute_selection import AttributeSelection
from one_click_analysis.configuration.configurations import DatePickerConfig
from one_click_analysis.configuration.configurations import TransitionConfig
from one_click_analysis.configuration.configurator import Configurator
from one_click_analysis.feature_processing import attributes
from one_click_analysis.feature_processing.attributes_new.attribute import AttributeType
from one_click_analysis.feature_processing.attributes_new.feature import Feature
from one_click_analysis.feature_processing.feature_processor import FeatureProcessor
from one_click_analysis.gui.decision_rule_screen import DecisionRulesScreen
from one_click_analysis.gui.expert_screen import ExpertScreen
from one_click_analysis.gui.overview_screen import OverviewScreenDecisionRules
from one_click_analysis.gui.statistical_analysis_screen import StatisticalAnalysisScreen


class AttributeSelectionRoutingDecision(AttributeSelection):
    def __init__(
        self,
        selected_attributes: List[attributes.MinorAttribute],
        selected_activity_table_cols: List[str],
        selected_case_table_cols: List[str],
        statistical_analysis_screen: StatisticalAnalysisScreen,
        decision_rules_screen: DecisionRulesScreen,
        features: List[Feature],
    ):
        super().__init__(
            selected_attributes,
            selected_activity_table_cols,
            selected_case_table_cols,
            features,
        )
        self.statistical_analysis_screen = statistical_analysis_screen
        self.decision_rules_screen = decision_rules_screen
        self.updated_features = features.copy()

    def update(self):
        self.updated_features = []
        for f in self.features:
            if f.attribute in self.selected_attributes:
                if f.attribute.attribute_type == AttributeType.OTHER:
                    self.updated_features.append(f)
                elif f.attribute.attribute_type in [
                    AttributeType.ACTIVITY_COL_NUMERICAL,
                    AttributeType.ACTIVITY_COL_CATEGORICAL,
                ]:
                    if f.column_name in self.selected_activity_table_cols:
                        self.updated_features.append(f)
                elif f.attribute.attribute_type in [
                    AttributeType.CASE_COL_CATEGORICAL,
                    AttributeType.CASE_COL_NUMERICAL,
                ]:
                    if f.column_name in self.selected_activity_table_cols:
                        self.updated_features.append(f)

        self.statistical_analysis_screen.update_attr_selection(self.updated_features)
        self.decision_rules_screen.update_features(self.updated_features)


class AnalysisRoutingDecision:
    """Analysis of potential effects on case duration."""

    def __init__(
        self, datamodel: str, celonis_login: Optional[dict] = None, th: float = 0.3
    ):
        """

        :param datamodel: datamodel name or id
        :param celonis_login: dict with login information
        """

        self.datamodel = datamodel
        self.celonis_login = celonis_login
        self.th = th
        self.dm = None
        self.fp = None
        self.df_total_time = None
        self.configurator = None
        self.overview_screen = None
        self.stat_analysis_screen = None
        self.dec_rule_screen = None
        self.expert_screen = None
        self.tabs = None
        self.tab_names = [
            "Configurations",
            "Overview",
            "Statistical Analysis",
            "Decision Rules",
            "Expert Tab",
        ]

        self.selected_attributes = []
        self.selected_activity_table_cols = []
        self.selected_case_table_cols = []

    def run(self):
        out = widgets.Output(layout={"border": "1px solid black"})
        display(out)
        # 1. Connect to Celonis and get dm
        with out:
            print("Connecting to Celonis...")
        self.dm = utils.get_dm(self.datamodel, celonis_login=self.celonis_login)
        with out:
            print("Done")
        # 2. Create FeatureProcessor and Configurator

        self.fp = FeatureProcessor(self.dm)
        dp_config = DatePickerConfig(self.fp)
        tr_config = TransitionConfig(fp=self.fp, required=True)
        self.configurator = Configurator(
            self.fp, [dp_config, tr_config], self.run_analysis, out
        )
        self.tabs = self.create_tabs(
            [
                self.configurator.configurator_box,
                widgets.VBox(),
                widgets.VBox(),
                widgets.VBox(),
                widgets.VBox(),
            ]
        )
        display(self.tabs)

    def run_analysis(self, out: widgets.Output):
        # Reset fp from a previous run
        self.fp.reset_fp()

        with out:
            print("Fetching data and preprocessing...")

        # Get configurations
        start_date = self.configurator.applied_configs.get("start_date")
        end_date = self.configurator.applied_configs.get("end_date")
        start_activity = self.configurator.applied_configs.get("source_activity")
        end_activities = self.configurator.applied_configs.get("target_activities")
        print(f"source_activities: {start_activity}")
        print(f"end_activities: {end_activities}")

        self.fp.run_decision_point_PQL(
            start_activity=start_activity,
            end_activities=end_activities,
            time_unit="DAYS",
            start_date=start_date,
            end_date=end_date,
        )
        with out:
            print("Done")

        # assign the attributes and columns
        self.selected_attributes = self.fp.minor_attrs
        self.selected_activity_table_cols = (
            self.fp.dynamic_categorical_cols + self.fp.dynamic_numerical_cols
        )
        self.selected_case_table_cols = (
            self.fp.static_categorical_cols + self.fp.static_numerical_cols
        )

        # 3. Create the GUI
        with out:
            print("Creatng GUI...")
        # Create overview box
        # self.overview_screen = OverviewScreen(self.fp)
        # self.overview_screen.create_overview_screen()

        # Ceate statistical analysis tab
        self.overview_screen = OverviewScreenDecisionRules(
            fp=self.fp,
            source_activity="Status Change",
            target_activities=[
                "Assignment",
                "Caused By CI",
                "Operator Update",
                "Update",
            ],
        )

        self.stat_analysis_screen = StatisticalAnalysisScreen(
            self.fp,
            self.th,
            self.selected_attributes,
            self.selected_activity_table_cols,
            self.selected_case_table_cols,
        )
        self.stat_analysis_screen.create_statistical_screen()

        # Create decision rule miner box
        self.dec_rule_screen = DecisionRulesScreen(
            self.fp,
            self.selected_attributes,
            self.selected_activity_table_cols,
            self.selected_case_table_cols,
        )
        self.dec_rule_screen.create_decision_rule_screen()

        # Create AttributeSelection object
        attr_selection_case_duration = AttributeSelectionRoutingDecision(
            self.selected_attributes,
            self.selected_activity_table_cols,
            self.selected_case_table_cols,
            self.stat_analysis_screen,
            self.dec_rule_screen,
        )

        # Create expert box
        self.expert_screen = ExpertScreen(self.fp, attr_selection_case_duration)
        self.expert_screen.create_expert_box()

        # Create tabs
        self.update_tabs(
            [
                self.configurator.configurator_box,
                self.overview_screen.overview_box,
                self.stat_analysis_screen.statistical_analysis_box,
                self.dec_rule_screen.decision_rule_box,
                self.expert_screen.expert_box,
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

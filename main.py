from module_hierarchy_parser.hierarchyParser import HierarchyParser
from module_hierarchy_builder.hierarchyBuilder import HierarchyBuilder
from module_attributes.attributeHandler import AttributeHandler
from module_config.config import Config
from module_dictionary_handler.dictionaryHandler import DictionaryHandler
from module_converter.converter import Converter
from module_converter.converter_data_adapter import ConverterDataAdapter

from module_diagram_creation.modelCreator import ModelCreator

# Submodules
from spmclient.spm.spmclient import SPMClient
from amlparser.amlparser import AMLParser
from amlparser.amlquery import AMLQuery

# Imports alloy
from alloy.databases.database_utility_factory import DatabaseUtilityFactory
from alloy.task_watch.task_watch import TaskWatch
from alloy.logging.logger_utility import logger
from alloy.general.helpers import root
from alloy.general.helpers import measure_execution_time
from alloy.file_handler import json_files
import table_definitions as table_definitions

# External
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Migration:
    def __init__(self) -> None:

        # ------------------------ Global Preparations ---------------------------------

        self.test_config_path = 'PROJECT_CONFIG/scb_config_7Oct_Correct.yaml'
        test_spm_config_path = 'PROJECT_CONFIG/TEST_spmconfig.yaml'

        self.config = Config(self.test_config_path)
        self.spm_config_path = test_spm_config_path

        self.dbu = DatabaseUtilityFactory.get_database_utility(
            db_engine="sqlite", db_name="TEST_DB", recreate_on_schema_change=True, recreate_on_rerun=False)
        self.ARTIFACTS_PATH = os.path.join(root(), "_ARTIFACTS_TEST")

        self.cfg = self.config.read_config()
        self.spm = SPMClient(self.spm_config_path)
        self.migration_start_directory = self.cfg.get("migration_start_directory")

        # --------------------------- File Tracker -------------------------------------

        self.FT_4_DictionaryEntries = TaskWatch(
            watch_table=table_definitions.DictionaryEntries,
            track_file_path=os.path.join(self.ARTIFACTS_PATH, "FT_4_DictionaryEntires"),
            track_file_prefix="FT_4_DictionaryEntires",
            write_data_to_files_instead_db=True  # Default is False, must be set to True to write to files
        )

        self.FT_Models = TaskWatch(
            watch_table=table_definitions.dbModels,
            track_file_path=os.path.join(self.ARTIFACTS_PATH, "FT_Models"),
            track_file_prefix="FT_Models",
            write_data_to_files_instead_db=True  # Default is False, must be set to True to write to files
        )

    def STAGE_1_AMLParser(self):
        # AML Parser
        input_file_path = self.cfg.get('input_xml')
        parse_xml_file_flag = self.cfg.get('parse_xml_file', True)
        self.amlquery = AMLQuery(input_file_path, force_parse=parse_xml_file_flag)
        self.amlparser = AMLParser()
        self.amlparser.parse_aml(input_file_path, force_parse=parse_xml_file_flag)
        self.attribute_handler = AttributeHandler(self.cfg, self.spm, self.amlparser, self.amlquery)

    def STAGE_2_HierarchyParser(self):
        hierarchy_parser = HierarchyParser(self.cfg, self.amlparser.groups, self.amlparser.models)
        hierarchy_parser.parse_hierarchy()
        json_files.write_json_file(hierarchy_parser.hierarchy, "hierarchy_parser_output.json", "output")

    def STAGE_3_HierarchyBuilder(self):

        hierarchy = json_files.read_json_file('hierarchy_parser_output.json', 'output')
        hierarchy_builder = HierarchyBuilder(self.spm, self.cfg, hierarchy, self.FT_Models,
                                             root_directory_id=self.migration_start_directory, create_mapping_from_workspace=True)
        hierarchy_builder.build_hierarchy(remove_empty_directories=True)

    def STAGE_4_DictionaryHandler(self, prealod_glossary: bool, create_update_glossary: bool):

        self.dictionary_handler = DictionaryHandler(self.cfg, self.spm, self.amlparser, self.attribute_handler,
                                                    self.FT_4_DictionaryEntries, prealod_glossary)
        if create_update_glossary:
            self.dictionary_handler.create_dictionary_entries()

    def STAGE_5_Converter(self):
        converter = Converter(self.cfg, self.amlparser, self.attribute_handler, self.dictionary_handler, self.FT_4_DictionaryEntries, self.FT_Models)
        models_to_create = converter.get_models()
        json_files.write_json_file(models_to_create, "all_models.json", "output")
        # ConverterDataAdapter
        # transforms converter data into signavio bpmn structure
        # puts shapes into lanes
        # creates diagram data with x,y coordinates via diagramforge and vc_model_builder
        converter_data_adapter = ConverterDataAdapter(self.cfg, self.FT_Models, self.FT_4_DictionaryEntries) # self.amlparser, self.amlquery)
        converter_data_adapter.build_signavio_data()
        print()

    def STAGE_6_ModelCreation(self):
        # pushes prepared content to Signavio via API call
        model_creator = ModelCreator(self.cfg, self.spm, self.FT_Models)
        model_creator.update_signavio_models_with_aris_content()

    # ------------------------------------------------------------------------------
    # ------------------------ MIGRATION EXECUTION ---------------------------------
    # ------------------------------------------------------------------------------

    def run_migration(self):

        logger.info('START ARIS-Migration-Tool')
        preload_glossary = self.cfg.get('preload_dictionary_items_from_workspace')
        create_and_update_glossary = self.cfg.get('create_and_update_dictionary_items')

        self.STAGE_1_AMLParser()

        if self.cfg.get('run_stage_hierarchy_parser'):
            self.STAGE_2_HierarchyParser()

        if self.cfg.get('run_stage_hierarchy_builder'):
            self.STAGE_3_HierarchyBuilder()

        self.STAGE_4_DictionaryHandler(preload_glossary, create_and_update_glossary)

        if self.cfg.get('run_converter'):
            self.STAGE_5_Converter()

        if self.cfg.get('run_model_creator'):
            self.STAGE_6_ModelCreation()


if __name__ == '__main__':
    migration = Migration()

    @measure_execution_time
    def run():
        migration.run_migration()

    run()

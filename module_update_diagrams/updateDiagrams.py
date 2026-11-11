# Updates diagrams with risk management attribute
from pyutils.task_handler.FileTaskTracker import FileTaskTracker
from pyutils.task_handler.StageModelDefinitions import DictionaryEntries
from pyutils.task_handler.StageModelDefinitions import dbModels
from spmclient.spm.spmclient import SPMClient
from pyutils.logger_utility.logger import logger
from pyutils.general.helpers import root
import os
import copy
import pandas as pd


class UpdateDiagrams():

    def __init__(self, cfg, spm: SPMClient, dbu):
        self.dbu = dbu
        self.ARTIFACTS_PATH = os.path.join(root(), "_ARTIFACTS_TEST")

        self.FT_4_DictionaryEntries = FileTaskTracker(
            stage_model=DictionaryEntries,
            dbu=self.dbu,
            save_file_path=os.path.join(self.ARTIFACTS_PATH, "FT_4_DictionaryEntries"),
            save_file_prefix="FT_4_DictionaryEntries"
        )
        self.FT_Models = FileTaskTracker(
            stage_model=dbModels,
            dbu=self.dbu,
            save_file_path=os.path.join(self.ARTIFACTS_PATH, "FT_Models"),
            save_file_prefix="FT_Models"
        )

        self.spm = spm
        self.published_diagrams = []

    def transform_metaDataValues(self, input_data):
        # adds /glssary/ before id and removes unrequired data
        output_data = {}

        for key, value in input_data.items():
            if isinstance(value, dict):
                if 'id' in value:
                    output_data[key] = f"/glossary/{value['id']}"
                else:
                    output_data[key] = value
            elif isinstance(value, list):
                output_data[key] = []
                for item in value:
                    if isinstance(item, dict) and 'id' in item:
                        output_data[key].append(f"/glossary/{item['id']}")
                    else:
                        output_data[key].append(item)
            else:
                output_data[key] = value

        return output_data

    def get_all_risks_and_controls(self):
        list_of_dictionary_categories = ['e143ce2b4f164307a529e12e66704d8e', '0ea2110cd2314642a0d0d7c4f09835e5',
                                         'a07bea1e9a7f42948f60dc810c5242ce', '26f1c0ba0b86462c9c26fbae7c0bb487',
                                         'ccd7e95c6abf4c8086f1c11c080027f3', '5711ec4951f24901baea009713b74208',
                                         '5c8f51c7f54949bb8e2bf6395983451a', '18f135dc61344b0ab21ff07d3ec3bd95']
        category = ''
        limit = 1000
        offset = 0
        all_dictionary_items = []
        for category in list_of_dictionary_categories:
            logger.info(f'Start Fetching Dictionary Items in category: {category}')
            category_dict_items = self.spm.dictionary.get_all_entries_of_category(category, limit, offset)
            # save all dictionary items in a category to DB
            for item in category_dict_items:
                glossary_id = item.get('href', '').replace('/glossary/', '')
                data, data_exists = self.FT_4_DictionaryEntries.skip_task_or_data(id=glossary_id)
                if not data_exists:
                    data = {'json': item}
                    self.FT_4_DictionaryEntries.results_to_file(id=glossary_id, data=data)

            all_dictionary_items.extend(category_dict_items)

        logger.info('Fetched Total ' + str(len(all_dictionary_items)) + ' items in category ' + category)

    def read_diagram_data(self):
        # model_id = '7a5c70e2e85340ff94687d09c44d4f33'
        # get only bpmn diagrams from excel sheet
        df = pd.read_excel('input/Test_Diagrams.xlsx')
        for index, row in df.iterrows():
            row = row.to_dict()
            if (row['Type'] == 'BPMN 2.0'):
                model_id = row['ID']
                # check whether diagram is published or not
                header_info = {}
                try:
                    header_info = self.spm.model.get_header(model_id)
                except Exception as e:
                    logger.error(f'Header Info Error Model ID: <{model_id}> Error: <{str(e)}>')
                if header_info.get('errors'):
                    logger.error(f'Header Info Error Model ID: <{model_id}> Error: <{header_info.get('errors')}>')
                else:
                    granted_revision_number = header_info.get('granted_revision_number', '')
                    rev = header_info.get('rev', '')
                    if granted_revision_number != '' and granted_revision_number == rev:
                        # diagram published
                        self.published_diagrams.append(model_id)

                    diagram_json = {}
                    try:
                        diagram_json = self.spm.model.get_latest_json(model_id)
                    except Exception as e:
                        logger.error(f'Get Latest JSON Error Model ID: <{model_id}> Error: <{diagram_json.get('errors')}>')
                    if diagram_json.get('errors'):
                        logger.error(f'Get Latest JSON Error Model ID: <{model_id}> Error: <{diagram_json.get('errors')}>')
                    else:
                        data, data_exists = self.FT_Models.skip_task_or_data(id=model_id)
                        if not data_exists:
                            data = {'json': diagram_json}
                            self.FT_Models.results_to_file(id=model_id, data=data)

    def update_diagrams_with_risk_management(self):
        # get all records from DB
        records = self.FT_Models.yield_filtered_records()
        for model_id, data in records:

            model_json = data.get('json', {})
            # get risks controls
            diagram_risks = model_json.get('properties', {}).get('meta-risks', [])
            diagram_controls = model_json.get('properties', {}).get('meta-controls', [])
            risk_management_attribute, vodacom_risk_management_attribute = self.create_risk_management_attribute(diagram_risks, diagram_controls)

            # add risk management attribute to model_json
            if risk_management_attribute['totalCount'] > 0:
                model_json['properties']['meta-riskmanagement'] = copy.deepcopy(risk_management_attribute)
            if vodacom_risk_management_attribute['totalCount'] > 0:
                model_json['properties']['meta-vodacomriskmanagement'] = copy.deepcopy(vodacom_risk_management_attribute)

            # update shapes with risk-management attributes
            self.update_shapes_with_risk_management(model_json)

            # update model
            try:
                response = self.spm.model.update_model(model_id=model_id, model_json=model_json,
                                                       comment='Update models with risk management attribute')
                if not isinstance(response, list):
                    if response.get('errors'):
                        logger.error(f"Update Model ID: {model_id} - Error: {str(e)}")
            except Exception as e:
                logger.error(f"Update Model ID: {model_id} - Error: {str(e)}")

            # check if diagram is in published diagrams
            if model_id in self.published_diagrams:
                try:
                    response = self.spm.model.publish(model_id=model_id)
                    if response.get('errors'):
                        logger.error(f"Publish Model ID: {model_id} - Error: {str(e)}")
                except Exception as e:
                    logger.error(f"Publish Model ID: {model_id} - Error: {str(e)}")

    def update_shapes_with_risk_management(self, model_data):
        # check shape elements Tasks
        child_shapes = model_data.get("childShapes", "")

        if child_shapes and len(child_shapes) != 0:
            # check Tasks
            tasks = list(filter(lambda a: a['stencil']['id'] == 'Task', child_shapes))
            for task in tasks:
                task_risks = task.get('properties', {}).get('meta-risks', [])
                task_controls = task.get('properties', {}).get('meta-controls', [])
                risk_management_attribute, vodacom_risk_management_attribute = self.create_risk_management_attribute(task_risks, task_controls)
               # add risk management attribute to model_json
                if risk_management_attribute['totalCount'] > 0:
                    task['properties']['meta-riskmanagement'] = copy.deepcopy(risk_management_attribute)
                if vodacom_risk_management_attribute['totalCount'] > 0:
                    task['properties']['meta-vodacomriskmanagement'] = copy.deepcopy(vodacom_risk_management_attribute)

            if len(child_shapes) > 0:
                for child in child_shapes:
                    self.update_shapes_with_risk_management(child)

    def create_risk_management_attribute(self, risks, controls):
        risk_management_attribute = {"totalCount": 0, 'items': []}
        vodacom_risk_management_attribute = {"totalCount": 0, 'items': []}

        for risk_id in risks:
            # get risk data
            data_dictionary, data_exists = self.FT_4_DictionaryEntries.skip_task_or_data(id=risk_id.replace('/glossary/', ''))
            if not data_exists:
                logger.error(f'Risk ID: <{risk_id}> does not exist.')
            else:
                # check controls of the risk
                # check controls of the diagram
                risk_attached_controls = data_dictionary.get("json", {}).get('rep', {}).get('metaDataValues', {}).get('meta-controls', [])
                # if risk_attached_controls:
                # check glossary category of risk it should be either Risk or Vodacom Risk
                risk_glossary_category = data_dictionary.get("json", {}).get('rep', {}).get('category', '')
                if risk_glossary_category not in ['/glossarycategory/e143ce2b4f164307a529e12e66704d8e', '/glossarycategory/26f1c0ba0b86462c9c26fbae7c0bb487']:
                    continue
                new_risk = {}
                new_risk_metadata = data_dictionary.get("json", {}).get('rep', {}).get('metaDataValues', {})
                new_risk = self.transform_metaDataValues(new_risk_metadata)
                new_risk['itemHref'] = data_dictionary.get("json", {}).get('href')
                new_risk['attachments'] = ''
                new_risk["riskname"] = data_dictionary.get("json", {}).get('rep', {}).get('title', '')
                new_risk['description'] = data_dictionary.get("json", {}).get('rep', {}).get('description', '')
                new_risk["controls"] = {"totalCount": 0, 'items': []}
                for risk_attached_control in risk_attached_controls:
                    # if control exists in model & risk_attached_controls then add it
                    control_glossary_href = '/glossary/' + risk_attached_control.get('id', '')
                    if control_glossary_href in controls:
                        control_glossary_data, data_exists = self.FT_4_DictionaryEntries.skip_task_or_data(
                            id=risk_attached_control.get('id', '').replace('/glossary/', ''))
                        if not data_exists:
                            logger.error(f'Risk ID: <{risk_id}> does not exist.')
                        else:
                            new_control = {}
                            new_control_metadata = control_glossary_data.get("json", {}).get('rep', {}).get('metaDataValues', {})
                            new_control = self.transform_metaDataValues(new_control_metadata)
                            control_category = control_glossary_data.get("json", {}).get('rep', {}).get('category', '')
                            new_control['itemHref'] = control_glossary_data.get("json", {}).get('href')
                            new_control['attachments'] = ''
                            new_control["name"] = control_glossary_data.get("json", {}).get('rep', {}).get('title', '')
                            new_control['description'] = control_glossary_data.get("json", {}).get('rep', {}).get('description', '')
                            if risk_glossary_category == '/glossarycategory/e143ce2b4f164307a529e12e66704d8e' and control_category == '/glossarycategory/ccd7e95c6abf4c8086f1c11c080027f3':
                                # control category
                                new_risk["controls"]['items'].append(new_control)
                            elif risk_glossary_category == '/glossarycategory/26f1c0ba0b86462c9c26fbae7c0bb487' and control_category == '/glossarycategory/18f135dc61344b0ab21ff07d3ec3bd95':
                                # control category
                                new_risk["controls"]['items'].append(new_control)
                # update count
                new_risk["controls"]['totalCount'] = len(new_risk["controls"]['items'])
                if risk_glossary_category == '/glossarycategory/e143ce2b4f164307a529e12e66704d8e':
                    risk_management_attribute['items'].append(new_risk)
                elif risk_glossary_category == '/glossarycategory/26f1c0ba0b86462c9c26fbae7c0bb487':
                    vodacom_risk_management_attribute['items'].append(new_risk)

        risk_management_attribute['totalCount'] = len(risk_management_attribute['items'])
        vodacom_risk_management_attribute['totalCount'] = len(vodacom_risk_management_attribute['items'])
        return risk_management_attribute, vodacom_risk_management_attribute

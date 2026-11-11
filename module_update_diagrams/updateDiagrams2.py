# Updates diagrams with risk management attribute
from pyutils.task_handler.FileTaskTracker import FileTaskTracker
from pyutils.task_handler.StageModelDefinitions import DictionaryEntries
from pyutils.task_handler.StageModelDefinitions import dbModels
from spmclient.spm.spmclient import SPMClient
from pyutils.logger_utility.logger import logger
from pyutils.general.helpers import root
from pyutils.file_handler.json_files import write_json_file, read_json_file
import os
import copy
import pandas as pd


class UpdateDiagrams2():

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
        self.published_diagrams = set()
        self.diagrams_updated = set()

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

    def read_diagram_data(self):
        # model_id = '7a5c70e2e85340ff94687d09c44d4f33'
        # get only bpmn diagrams from excel sheet
        df_diagrams_in_ws = pd.read_excel('input/SAP_Standardisation_Missing_data.xlsx')
        df_diagrams_in_ws = df_diagrams_in_ws[df_diagrams_in_ws['WIP'] != '']
        df_diagrams_in_ws = df_diagrams_in_ws[df_diagrams_in_ws['WIP'].notna()]
        # Combine 'WIP' and 'Published' column values into a unique list
        wip_list = list(df_diagrams_in_ws['WIP'].astype(str))
        published_list = list(df_diagrams_in_ws['Published'].astype(str))
        diagram_ids = list(set(wip_list + published_list))
        print(f"Unique diagram IDs (WIP + Published): {diagram_ids}")

        df_update = copy.deepcopy(diagram_ids)

        #  filter df
       # for index, row in df_update.iterrows():
        #    row = row.to_dict()
        # check diagrams with the same name with df_diagrams_in_ws
        # matching_rows = df_diagrams_in_ws[df_diagrams_in_ws['Diagram'] == row['Diagram']]
        # if not matching_rows.empty:
        # check for each model id in matching_rows
        # for _, matching_row in matching_rows.iterrows():
        #    matching_row = matching_row.to_dict()
        #    model_id = matching_row['ID']
        #    if (matching_row['Type'] == 'BPMN 2.0'):
        # check whether diagram is published or not
        for model_id in diagram_ids:
            header_info = {}
            data, data_exists = self.FT_Models.skip_task_or_data(id=model_id)
            if not data_exists:
                try:
                    header_info = self.spm.model.get_header(model_id)
                except Exception as e:
                    logger.error(f'Header Info Error Model ID: <{model_id}> Error: <{str(e)}>')
                if header_info.get('errors'):
                    logger.error(f'Header Info Error Model ID: <{model_id}> Error: <{header_info.get('errors')}>')
                else:
                    if 'BPMN 2.0' not in header_info.get('type'):
                        logger.warning(f'Model ID: {model_id} is not a BPMN 2.0 diagram, skipping...')
                        continue
                    granted_revision_number = header_info.get('granted_revision_number', '')
                    rev = header_info.get('rev', '')
                    if granted_revision_number != '' and granted_revision_number == rev:
                        # diagram published
                        self.published_diagrams.add(model_id)

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
        write_json_file(list(self.published_diagrams), 'published_diagrams.json', 'output')

    def update_diagrams_with_attr(self):
        # get all records from DB
        # read published diagrams from file as list
        self.published_diagrams = read_json_file('published_diagrams.json', 'output')
        records = self.FT_Models.yield_filtered_records()
        for model_id, data in records:

            model_json = data.get('json', {})
            is_updated = self.update_shapes_with_sap_standardisation_attr(model_json)
            if is_updated:
                # update model
                try:
                    response = self.spm.model.update_model(model_id=model_id, model_json=model_json,
                                                           comment='Update models with sap standardisation attribute')
                    if not isinstance(response, list):
                        if response.get('errors'):
                            logger.error(f"Update Model ID: {model_id} - Error: {str(e)}")
                        else:
                            logger.success(f"Update Model ID: {model_id} - Successfully updated")
                            self.diagrams_updated.add(model_id)
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
            else:
                logger.info(f"Model ID: {model_id} - No changes made to the model.")

        write_json_file(list(self.diagrams_updated), 'diagrams_updated.json', 'output')

    def update_shapes_with_sap_standardisation_attr(self, model_data):
        # check shape elements Tasks
        child_shapes = model_data.get("childShapes", "")
        changed = False

        if child_shapes and len(child_shapes) != 0:
            # check Tasks
            tasks = list(filter(lambda a: a['stencil']['id'] == 'Task', child_shapes))
            for task in tasks:
                attr_value = task.get('properties', {}).get('meta-sapstandardisation', '')

                # check current value
                # Fully SAP Standard —> ci1749458684545699078740
                # Partially SAP Standard -> ci174945868454529947191
                # Not SAP Standard -> ci1749458684545605061802
                # Not applicable -> ci174945868454521425083
                if attr_value == 'ci1749458684545699078740':  # Fully SAP Standard
                    task["properties"]["meta-sapstandardisation"] = 'ci1753351583816188500500'
                    changed = True
                elif attr_value == 'ci174945868454529947191':  # Partially SAP Standard
                    task["properties"]["meta-sapstandardisation"] = 'ci1753351583816781558921'
                    changed = True
                elif attr_value == 'ci1749458684545605061802':  # Not SAP Standard
                    task["properties"]["meta-sapstandardisation"] = 'ci1753351583816489130562'
                    changed = True
                elif attr_value == 'ci174945868454521425083':  # Not applicable
                    task["properties"]["meta-sapstandardisation"] = 'ci1753351583816348816873'
                    changed = True
            if len(child_shapes) > 0:
                for child in child_shapes:
                    if self.update_shapes_with_sap_standardisation_attr(child):
                        changed = True
        return changed

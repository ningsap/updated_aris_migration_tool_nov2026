import json
import os
from alloy.logging.logger_utility import logger
from alloy.task_watch.task_watch import TaskWatch
from spmclient.spm.spmclient import SPMClient


class HierarchyBuilder:
    """
    A class to build and manage a hierarchical structure of directories and models,
    integrating ARIS and Signavio platforms.

    Attributes:
        spm: A Signavio Process Manager instance for API calls.
        hierarchy: A dictionary representing the hierarchy of directories and models.
        root_directory_id: The ID of the root directory in Signavio.
        create_mapping_from_workspace: A flag to indicate whether to create a new mapping file.
        tree: A dictionary representing the hierarchical tree structure.
        errors: A dictionary to store errors encountered during operations.
        aris_signavio_id_mapping_dict: A dictionary to map ARIS IDs to Signavio IDs.
        json_mapping_file_path: Path to the JSON file for storing the mapping.
        model_json_bpmn: A dictionary representing a template for BPMN models.
        model_json_vc: A dictionary representing a template for Value Chain models.
    """

    def __init__(self, spm: SPMClient, cfg, hierarchy, file_tracker: TaskWatch, root_directory_id=None, create_mapping_from_workspace=False):
        self.hierarchy = hierarchy
        self.file_tracker = file_tracker
        self.tree = {}
        self.spm = spm
        self.errors = {}
        self.aris_signavio_id_mapping_dict = {}
        self.root_directory_id = root_directory_id
        self.json_mapping_file_path = cfg.get('file_path_hierarchy_builder_json')  # TODO: remove
        self.secondary_workspace_language = cfg.get('secondary_workspace_language')

        if root_directory_id:
            self.is_root_directory_in_trash(root_directory_id)

        # ARIS - Signavio Mapping File
        if create_mapping_from_workspace:
            # Create new signavio-aris id mapping from existing signavio content
            self.get_aris_signavio_mapping()

        # Import Empty VC & BPMN Models
        with open('input/template_bpmn.json', 'r') as json_file:
            self.model_json_bpmn = json.load(json_file)

        with open('input/template_valueChain.json', 'r') as json_file:
            self.model_json_vc = json.load(json_file)

    def is_root_directory_in_trash(self, root_directory_id):
        url = self.spm._client.host + '/spm/v1/directory/' + root_directory_id + '/parents'
        directory_parents = self.spm._client.request_json('GET', url)
        directory_parents.append({'rep': self.spm.directory.get_info(root_directory_id)})

        for parent in directory_parents:
            if parent['rep'].get('deleted'):
                logger.warning(f'Hierarchy Builder Warning: START DIRECTORY {root_directory_id} IS DELETED. Please use a valid directory')
                raise ValueError(f'Hierarchy Builder: Invalid Start Directory {root_directory_id}')

    def count_directory_types(self, tree):
        """
        Count the number of each type of directory in the tree.

        Args:
            tree (dict): The hierarchical tree structure.

        Returns:
            dict: A dictionary with the counts of each type.
        """
        type_counts = {}

        def count_types(node):
            nonlocal type_counts
            if node['type'] in type_counts:
                type_counts[node['type']] += 1
            else:
                type_counts[node['type']] = 1

            for child_key, child_node in node['children'].items():
                count_types(child_node)

        for key, node in tree.items():
            count_types(node)

        return type_counts

    def build_hierarchy(self, remove_empty_directories):
        self.build_tree(remove_empty_directories)
        self.create_directories_and_models(self.tree, parent_id=self.root_directory_id)
        self.export_model_mapping_json(self.aris_signavio_id_mapping_dict)

    def build_tree(self, remove_empty_directories=False):
        """
        Build a hierarchical tree structure from the given hierarchy data.
        """
        tree = {}
        data = self.hierarchy

        # Identify root nodes
        for key, node in data.items():
            if node['pid'] not in data:
                name_keys = {k: v for k, v in node.items() if k.startswith("name")}
                tree[key] = {
                    'guid': node['guid'],
                    'type': node['type'],
                    'children': {}
                }
                tree[key] = tree[key] | name_keys

        # Link children recursively

        def add_children(parent_node, parent_id):
            has_children = False
            for key, node in data.items():
                if node['pid'] == parent_id and key != parent_id:
                    name_keys = {k: v for k, v in node.items() if k.startswith("name")}
                    child_node = {
                        'guid': node['guid'],
                        'type': node['type'],
                        'children': {}
                    }
                    child_node = child_node | name_keys
                    if add_children(child_node, key) or not remove_empty_directories or node['type'] != 'dir':
                        parent_node['children'][key] = child_node
                        has_children = True
            return has_children

        # Recursive linking from the identified root nodes
        for key in list(tree.keys()):
            add_children(tree[key], key)

        self.tree = tree
        logger.info('Tree created:')
        type_counts = self.count_directory_types(tree)
        logger.info(type_counts)

    def create_directories_and_models(self, tree, parent_id):
        """
        Create directories and models in Signavio based on the hierarchical tree structure.

        Args:
            tree (dict): The hierarchical tree structure.
            parent_id (str): The ID of the parent directory in Signavio.
        """
        for key, element in tree.items():
            element_type = element.get('type', '')
            name = element.get('name', '')
            aris_id = element.get('guid', '')
            name_keys = {k: v for k, v in element.items() if k.startswith("name")}
            model_header = {}
            header = {}
            response_updated = ''
            if not name:
                # if name_keys:
                #     if self.secondary_workspace_language:
                #         name_key = 'name_' + self.secondary_workspace_language
                #         if name_keys.get(name_key, ''):
                #             name = name_keys.get(name_key, '')
                #         else:
                #             # pick one of the languages
                #             value = next((v for v in name_keys.values() if v), None)
                #             if value:
                #                 name = value
                #     else:
                # pick one of the languages
                value = next((v for v in name_keys.values() if v), None)
                if value:
                    name = value

            if not name:
                # fallback to aris_id
                name = aris_id

            signavio_id = None
            print(f'{element_type} : {name}')

            # Check if aris guid is already in database
            data_exists, data = self.file_tracker.is_task_done(id=aris_id)
            if data_exists:
                # TODO: get parent id (signavio id of parent),
                #  otherwise signavio_id stays none and child cannot be created
                if element_type == 'dir':
                    # parent_id = data.get('signavio_id', None)
                    signavio_id = data.get('signavio_id', None)
                print(f'{aris_id} is already created in workspace')

            # if self.aris_signavio_id_mapping_dict.get(aris_id):
            #    print(f'{aris_id} is already created in workspace')

            # If not, create model / directory in Signavio
            else:

                if element_type == 'dir':
                    response = self.spm.directory.create(name, parent_id, aris_id)
                    signavio_id = response.get('href')
                    # Set aris_id as description
                    if signavio_id:
                        response_updated = self.spm.directory.update(signavio_id, name, parent_id, aris_id, name_translations=name_keys)
                        if not response_updated:
                            logger.error(f'Update Directory for MultiLang failed. Directory ARIS ID: {aris_id}')
                elif element_type == 'bpmn':
                    self.model_json_bpmn['properties']['meta-arisguid'] = aris_id
                    # namespace='http://b3mn.org/stencilset/bpmn2.0#')
                    response = self.spm.model.create(name, parent_id, self.model_json_bpmn, 'bpmn')
                    signavio_id = response.get('href')
                    if signavio_id:
                        # header = self.spm.model.get_header(model_id=signavio_id)
                        model_header = name_keys
                        response_updated = self.spm.model.update_info(model_id=signavio_id, model_header=model_header)
                        if not response_updated:
                            logger.error(f'Update Model VC for MultiLang failed. Model ARIS ID: {aris_id}')
                elif element_type == 'vc':
                    self.model_json_vc['properties']['meta-arisguid'] = aris_id
                    # namespace='http://www.signavio.com/stencilsets/processmap#')
                    response = self.spm.model.create(name, parent_id, self.model_json_vc, 'vc')
                    signavio_id = response.get('href')
                    if signavio_id:
                        # header = self.spm.model.get_header(model_id=signavio_id)
                        model_header = name_keys
                        response_updated = self.spm.model.update_info(model_id=signavio_id, model_header=model_header)
                        if not response_updated:
                            logger.error(f'Update Model for MultiLang failed. Model ARIS ID: {aris_id}')
                else:
                    error_string = f'Hierarchy Builder Create: Element Type {element_type} is not handled in the hierarchy builder'
                    logger.error(error_string)
                    self.errors[aris_id] = error_string

                if signavio_id:
                    # self.aris_signavio_id_mapping_dict[aris_id] = {'Id': signavio_id, 'data': response}

                    data = {'signavio_id': signavio_id,
                            'revision': '1',
                            'element_type': element_type,
                            'error': 'no',
                            'json': response
                            }
                    logger.info(f'Element type <{element_type}> ID: <{aris_id}> created successfully')
                    self.file_tracker.save_task_results(id=aris_id, data=data)
                else:
                    error_string = f'Hierarchy Builder Create: {element_type} : {name} ({aris_id}) was not created successfully'
                    logger.error(error_string)
                    self.errors[aris_id] = error_string

            children = element.get('children', {})
            if children:
                self.create_directories_and_models(children, signavio_id)

    def export_model_mapping_json(self, mapping_json):
        """
        TO DELETE
        Export the ARIS-Signavio model mapping to a JSON file.
        Prints the Number of models / directories and errors.

        Args:
            mapping_json (dict): The mapping dictionary to be exported.
        """
        # Export File Mapping
        with open(self.json_mapping_file_path, 'w') as json_file:
            json.dump(mapping_json, json_file, indent=4)

        model_count = 0
        directory_count = 0

        # Count models and directories
        for key, value in mapping_json.items():
            if value['Id'].startswith('/model/'):
                model_count += 1
            elif value['Id'].startswith('/directory/'):
                directory_count += 1

        print(f"'Directories': {directory_count}, Models: {model_count}")
        print(f"Errors: {str(self.errors)}")

    def get_aris_signavio_mapping(self):
        """
        Collect ARIS-Signavio mapping from the workspace data.
        """
        logger.info('Collecting ARIS-SIGNAVIO mapping from workspace data')
        # TODO: Wipe existing model db

        models, directories = self.spm.utils.get_directories_and_models(self.root_directory_id)

        for model in models:
            signavio_id = model.get('href')
            # print(signavio_id)
            model_json = self.spm.model.get_latest_json(signavio_id)
            aris_id = model_json.get('properties', {}).get('meta-arisguid', '')

            namespace = model_json['stencilset']['namespace']
            if 'bmpn' in namespace:
                element_type = 'bpmn'
            elif 'processmap' in namespace:
                element_type = 'vc'
            else:
                element_type = namespace

            if aris_id:
                self.aris_signavio_id_mapping_dict[aris_id] = {'Id': signavio_id, 'data': model_json}  # TODO : REMOVE

                data = {'signavio_id': signavio_id,
                        'revision': model.get('rep', {}).get('rev', ''),
                        'element_type': element_type,
                        'error': 'no',
                        'json': model_json
                        }
                self.file_tracker.save_task_results(id=aris_id, data=data)

        for directory in directories:
            signavio_id = directory.get('href')
            aris_id = directory.get('rep', {}).get('description', '')
            if aris_id:
                self.aris_signavio_id_mapping_dict[aris_id] = {'Id': signavio_id, 'data': directory}
                data = {'signavio_id': signavio_id,
                        'revision': '1',
                        'element_type': 'dir',
                        'error': 'no',
                        'json': {}
                        }
                self.file_tracker.save_task_results(id=aris_id, data=data)

        self.export_model_mapping_json(self.aris_signavio_id_mapping_dict)

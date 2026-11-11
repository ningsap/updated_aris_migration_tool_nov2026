from typing import Dict, List, Optional, Set
from alloy.logging.logger_utility import logger
from alloy.task_watch.task_watch import TaskWatch


class PreProcessor:
    """Handles all preprocessing operations before model conversion."""

    def __init__(self, cfg, models: dict, connections: dict, obj_definitions: dict, dictionary_items_file_tracker: TaskWatch):
        self.models = models
        self.connections = connections
        self.obj_definitions = obj_definitions
        self.dictionary_items_file_tracker = dictionary_items_file_tracker

        self.task_def_to_fad_mapping = {}
        self.task_def_to_data_model_mapping = {}
        self.models_to_parse_for_dict_item = {}
        self.task_def_to_dict_item_from_matrix_model = {}

        self.diagram_types = cfg.get('diagram_mapping')
        self.object_mapping = cfg.get('object_mapping')
        self.shape_mapping = cfg.get("shape_mapping")

        # Configuration
        self.converter_flag_to_process_data_models = cfg.get('process_data_models', False)
        self.converter_flag_to_process_matrix_models = cfg.get('process_matrix_models', False)
        self.converter_flag_to_process_dict_models = cfg.get('process_dict_models', False)
        self.column_symbol_type_in_matrix_model = cfg.get('column_symbol_type_in_matrix_model', [])
        self.filter_by_connection_type_for_matrix_model = cfg.get('filter_by_connection_type_for_matrix_model', [])

    def preprocess_all(self) -> None:
        """Run all preprocessing steps based on config flags."""
        self.preprocessing_fads()

        if self.converter_flag_to_process_data_models:
            self.processing_data_models()

        if self.converter_flag_to_process_matrix_models:
            self.preprocessing_matrix_models()

        if self.converter_flag_to_process_dict_models:
            self.processing_assigned_models()

    def preprocessing_fads(self) -> Dict:
        """Process FAD (Function Allocation Diagram) models."""
        fad_keys = [model_key for model_key in self.models
                    if self.models[model_key]['type'] == "MT_FUNC_ALLOC_DGM"]

        for model_key in fad_keys:
            shape_occurences = self.models.get(model_key, {}).get("occs", {})
            task_occs = [shape_key for shape_key in shape_occurences
                         if self._is_task_shape(shape_occurences[shape_key])]

            for task_occ_key in task_occs:
                self._process_task_occurrence(task_occ_key, model_key, shape_occurences)

        return self.task_def_to_fad_mapping

    def processing_data_models(self) -> Dict:
        """Process data models and their task definitions."""
        data_model_keys = [model_key for model_key in self.models
                           if self.models[model_key]['type'] == "MT_IEF_DATA_MDL"]

        for model_key in data_model_keys:
            # Get shape occurrences for the model
            shape_occurences = self.models.get(model_key, {}).get("occs", {})
            if not shape_occurences:
                continue
            task_occs = [shape_key for shape_key in shape_occurences
                         if self._is_task_shape(shape_occurences[shape_key])]

            # Process each task occurrence
            for task_occ_key in task_occs:
                # Get task definition and linked models
                shape_data = shape_occurences.get(task_occ_key, {})
                task_def_key = shape_data.get('def', '')

                if not task_def_key:
                    logger.warning(f"Task occurrence {task_occ_key} has no definition key")
                    continue

                task_def = self.obj_definitions.get(task_def_key, {})
                task_def_linked_models = task_def.get('linked_models', [])

                # Map task definition to data model
                self.task_def_to_data_model_mapping[task_def_key] = {
                    'data_model_id': model_key,
                    'linked_models': task_def_linked_models
                }

        return self.task_def_to_data_model_mapping

    def preprocessing_matrix_models(self) -> Dict:
        """Process matrix models and their definitions."""
        matrix_model_keys = [model_key for model_key in self.models
                             if self.models[model_key]['type'] == "MT_MATRIX_MOD"]

        logger.info(f'Number of Matrix Models being processed: {len(matrix_model_keys)}')

        for model_key in matrix_model_keys:
            self._process_single_matrix_model(model_key)

        return self.task_def_to_dict_item_from_matrix_model

    def _process_single_matrix_model(self, model_key: str) -> None:
        """
        Process a single matrix model and update task definition mappings.

        Args:
            model_key: Key of the matrix model to process
        """
        shape_occurrences = self.models.get(model_key, {}).get("occs", {})
        if not shape_occurrences:
            return

        # Store object definitions for all occurrences
        occurrence_definitions = {
            v["def"] for v in shape_occurrences.values()
        }

        for occ_id, occurrence in shape_occurrences.items():
            occ_symbol = occurrence.get("symbol", '')
            occ_derived_symbol = occurrence.get('derived_symbol', '')
            symbol_to_check = (
                occ_symbol if occ_symbol in self.column_symbol_type_in_matrix_model
                else occ_derived_symbol if occ_derived_symbol in self.column_symbol_type_in_matrix_model
                else occ_symbol
            )

            if not symbol_to_check in self.column_symbol_type_in_matrix_model:
                continue

            signavio_attr = self.object_mapping.get(symbol_to_check, {}).get('transform_attribute', '')
            if not signavio_attr:
                continue

            def_dict_id = occurrence.get('def', '')
            obj_def = self.obj_definitions.get(def_dict_id, {})
            dictionary_guid = obj_def.get('guid', '')

            if not dictionary_guid:
                continue

            self._process_connections(
                occurrence_definitions,
                dictionary_guid,
                signavio_attr,
                obj_def.get("incoming_cxns", {}) | obj_def.get("outgoing_cxns", {})
            )

    def _process_connections(self, occurrence_definitions: Set, dictionary_guid: str, signavio_attr: str, connections: Dict) -> None:
        """
        Process connections for a dictionary item.

        Args:
            occurrence_definitions: Set of occurrence definition IDs
            dictionary_guid: GUID of the dictionary item
            connections: Dictionary of connections to process
        """
        for obj_def_id, cxn_data in connections.items():
            if not self._is_valid_connection(obj_def_id, occurrence_definitions, cxn_data):
                continue

            dictionary_item = self.dictionary_items_file_tracker.dbu.get_by_id(self.dictionary_items_file_tracker.stage_model, dictionary_guid)
            if dictionary_item:
                dictionary_item = dictionary_item.signavio_id
            else:
                logger.error(
                    f'Matrix Model Preprocessing: Dictionary item : {dictionary_guid} is not available in Dictionary Items. Dictionary is not attached to Object Def: {obj_def_id}')

            self._update_task_mapping(obj_def_id, dictionary_item, signavio_attr)

    def _is_valid_connection(self, obj_def_id: str, occurrence_definitions: Set,
                             cxn_data: Dict) -> bool:
        """Check if connection is valid for processing."""
        return (obj_def_id in occurrence_definitions and
                cxn_data['type'] in self.filter_by_connection_type_for_matrix_model)

    def _update_task_mapping(self, obj_def_id: str, dictionary_item: str,
                             signavio_attr: str) -> None:
        """
        Update task definition to dictionary item mapping.

        Args:
            obj_def_id: Task definition ID
            dictionary_item: Dictionary item "/glossary/..."
            signavio_attr: Signavio attribute value
        """
        if obj_def_id not in self.task_def_to_dict_item_from_matrix_model:
            self.task_def_to_dict_item_from_matrix_model[obj_def_id] = {
                'linked_models': self.obj_definitions.get(obj_def_id, {}).get('linked_models', []),
                'dictionary_items': {}
            }

        items = self.task_def_to_dict_item_from_matrix_model[obj_def_id]['dictionary_items']

        if signavio_attr not in items:
            items[signavio_attr] = [dictionary_item]
        elif dictionary_item not in items[signavio_attr]:
            items[signavio_attr].append(dictionary_item)

    def _is_task_shape(self, shape: dict) -> bool:
        """Check if a shape is a task type."""
        return (shape.get("symbol", "") in self.shape_mapping and
                self.shape_mapping[shape.get("symbol", "")] == 'Task')

    def _process_task_occurrence(self, task_occ_key: str, model_key: str,
                                 shape_occurences: dict) -> None:
        """Process a single task occurrence in FAD."""
        task_def_key = shape_occurences.get(task_occ_key, {}).get('def', '')
        task_def_linked_models = self.obj_definitions.get(task_def_key, {}).get('linked_models', [])

        if task_def_key not in self.task_def_to_fad_mapping:
            self.task_def_to_fad_mapping[task_def_key] = {
                'fad_model_id': [model_key],
                'linked_models': task_def_linked_models
            }
        else:
            if model_key not in self.task_def_to_fad_mapping[task_def_key]['fad_model_id']:
                self.task_def_to_fad_mapping[task_def_key]['fad_model_id'].append(model_key)
            self._update_linked_models(task_def_key, task_def_linked_models)

    def _update_linked_models(self, task_def_key: str, new_linked_models: List[str]) -> None:
        """Update linked models for a task definition."""
        for linked_model_key in new_linked_models:
            if linked_model_key not in self.task_def_to_fad_mapping[task_def_key]['linked_models']:
                self.task_def_to_fad_mapping[task_def_key]['linked_models'].append(linked_model_key)

    def processing_assigned_models(self) -> dict:
        """
        Process and map assigned models for tasks in value chain diagrams.

        Returns:
            dict: Mapping of models to their dictionary items
        """

        # Get models that match configured diagram types
        models_to_create = [
            model_key for model_key in self.models
            if self.models[model_key]['type'] in self.diagram_types
        ]

        for model_key in models_to_create:
            self._process_model_shapes(model_key)

        return self.models_to_parse_for_dict_item

    def _process_model_shapes(self, model_key: str) -> None:
        """
        Process shapes in a model and their task definitions.

        Args:
            model_key: Key of the model to process
        """
        shape_occurrences = self.models.get(model_key, {}).get("occs", {})
        if not shape_occurrences:
            return

        # Get shapes that should be checked (Tasks, CollapsedProcess, etc)
        shape_occ_to_check = []
        for shape_key, shape in shape_occurrences.items():
            signavio_shape_type = self._get_signavio_shape_type(shape)
            if signavio_shape_type in ['Task', 'ProcessCollapsed', 'CollapsedSubprocess']:
                shape_occ_to_check.append(shape_key)

        # Process each shape's linked models
        for shape_key in shape_occ_to_check:
            self._process_shape_links(model_key, shape_key, shape_occurrences)

    def _get_signavio_shape_type(self, shape: dict) -> str:
        """
        Get the Signavio shape type for a given shape.

        Args:
            shape: Shape dictionary

        Returns:
            str: Signavio shape type or empty string if not found
        """
        shape_aris_type = shape.get("symbol", "")
        shape_derived_symbol = shape.get("derived_symbol", "")

        # Check main symbol first
        shape_key = self._check_shape_mapping(shape_aris_type)

        # If not found, check derived symbol
        if not shape_key and shape_derived_symbol:
            shape_key = self._check_shape_mapping(shape_derived_symbol)

        return self.shape_mapping.get(shape_key, "") if shape_key else ""

    def _check_shape_mapping(self, txt_shape: str, shape_mapping_list: list):
        """
        Returns the first string in shape_mapping_list that is a substring of txt_shape, or False if none found.
        """
        # list contains elements with the substring
        # txt_shape includes the search keyword
        for string in shape_mapping_list:
            if string in txt_shape:
                return string
        return False

    def _process_shape_links(self, model_key: str, shape_key: str,
                             shape_occurrences: dict) -> None:
        """
        Process linked models for a shape.

        Args:
            model_key: Current model key
            shape_key: Shape key to process
            shape_occurrences: Dictionary of shape occurrences
        """
        # Get task definition and linked models
        task_def_key = shape_occurrences.get(shape_key, {}).get('def', '')
        if not task_def_key:
            return

        task_def = self.obj_definitions.get(task_def_key, {})
        linked_model_keys = task_def.get('linked_models', [])

        # Get linked diagrams and dictionary models
        linked_diagrams = [
            model_key for model_key in linked_model_keys
            if (self.models[model_key]['type'] in self.diagram_types.keys() or
                self.models[model_key]['derived_type'] in self.diagram_types.keys())
        ]
        dictionary_types = [
            'MT_DMN_CONTEXT_DIAGRAM',
            'MT_BUSY_CONTR_DGM',
            'MT_BUSINESS_RULES_ALLOC_DGM',
            'MT_TOGAF_DIAGRAM'
        ]

        dictionary_models = [
            model_key for model_key in linked_model_keys
            if self.models[model_key]['type'] in dictionary_types
        ]

        # Update models to parse mapping
        self._update_models_to_parse(linked_diagrams, dictionary_models)

    def _update_models_to_parse(self, linked_diagrams: list,
                                dictionary_models: list) -> None:
        """
        Update models to parse mapping with linked diagrams and dictionary models.

        Args:
            linked_diagrams: List of linked diagram keys
            dictionary_models: List of dictionary model keys
        """
        for linked_model_key in linked_diagrams:
            if linked_model_key not in self.models_to_parse_for_dict_item:
                self.models_to_parse_for_dict_item[linked_model_key] = set()

            self.models_to_parse_for_dict_item[linked_model_key].update(
                dictionary_models
            )

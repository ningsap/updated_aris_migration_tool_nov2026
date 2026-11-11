import copy
import re
import time
import html
from typing import Optional

# Modules
from alloy.file_handler.json_files import read_json_file, write_json_file
from alloy.logging.logger_utility import logger
from alloy.task_watch.task_watch import TaskWatch
from module_attributes.attributeHandler import AttributeHandler
from module_dictionary_handler.dictionaryHandler import DictionaryHandler, get_meta_data_values
from .preprocessor import PreProcessor
from amlparser.amlparser import AMLParser


class Converter:

    def __init__(self, cfg, amlparser: AMLParser, attribute_handler: AttributeHandler, dictionary_hadler: DictionaryHandler,
                 dictionary_items_file_tracker: TaskWatch, model_file_tracker: TaskWatch):
        self.models = amlparser.models
        self.connections = amlparser.cxns
        self.obj_definitions = amlparser.defs
        self.txt_definitions = amlparser.txt_defs
        self.attribute_handler = attribute_handler
        self.dictionary_handler = dictionary_hadler
        self.dictionary_items_file_tracker = dictionary_items_file_tracker
        self.model_file_tracker = model_file_tracker
        self.models_to_create = {}
        # config
        self.diagram_types = cfg.get('diagram_mapping')
        self.shape_mapping = cfg.get("shape_mapping")
        self.object_mapping = cfg.get('object_mapping')
        self.pool_name = cfg.get('pool_name', 'Pool')

        self.aris_signavio_attribute_name_mapping = cfg.get('aris_signavio_attribute_name_mapping')
        self.attribute_mapping_based_on_connection_type = cfg.get('attribute_mapping_based_on_connection_type')

        self.linking_diagram_attr = cfg.get("more_than_one_linking_diagram_attribute")
        self.default_shape_names = cfg.get('default_shape_names_to_ignore')

        self.flag_to_attach_loose_shapes_to_task_as_attributes = cfg.get('attach_loose_shapes_to_task_in_FAD')
        self.attribute_value_mapping = cfg.get('aris_signavio_attribute_value_mapping')
        # self.dictionary_items_that_should_be_attached_from_model = cfg.get('list_of_dictionary_items_that_should_be_attached_to_task_from_model')
        # if self.dictionary_items_that_should_be_attached_from_model is None:
        #    self.dictionary_items_that_should_be_attached_from_model = []
        self.dictionary_items_that_should_be_attached_from_model = list(self.object_mapping.keys())
        self.diagram_types_that_dictionary_items_stored = cfg.get('diagram_types_that_dictionary_items_stored_for_converter')
        self.list_of_attributes_to_check_formatting = cfg.get('list_of_attributes_to_check_formatting', [])

        self.attach_linking_diagrams_from_custom_attribute = cfg.get('attach_linking_diagrams_from_custom_attribute', False)
        self.link_attributes_url_label_mapping = cfg.get('link_attributes_url_label_mapping', [])
        self.model_level_attributes_to_catchall = cfg.get('model_level_attributes_to_catchall', [])
        self.shape_level_attributes_to_catchall = cfg.get('shape_level_attributes_to_catchall', [])
        self.catch_all_attribute_name = cfg.get('catch_all_attribute_name', 'meta-catchall')

        self.is_remove_intermediate_events_after_exclusive_gateway = cfg.get(
            'remove_intermediate_events_after_exclusive_gateway', False)
        self.transform_process_interfaces_into_intermediate_link_events = cfg.get(
            'transform_process_interfaces_into_intermediate_link_events', False)
        self.process_interface_symbols = cfg.get(
            'process_interface_symbols', [])

        self.remove_intermediate_events_before_and_after_process_interfaces = cfg.get(
            'remove_intermediate_events_before_and_after_process_interfaces', False)
        self.list_of_process_interface_symbols_to_remove_intermediate_events_coming_before_and_after_process_interfaces = cfg.get(
            'list_of_process_interface_symbols_to_remove_intermediate_events_coming_before_and_after_process_interfaces', [])
        self.custom_attribute_at_signavio_derived_from_symbol_type = cfg.get('custom_attribute_at_signavio_derived_from_symbol_type', {})

        self.model_attribute_txt_to_glossary_entry = cfg.get('model_attribute_txt_to_glossary_entry', {})
        self.create_dictionary_entry_from_attribute = cfg.get('create_dictionary_entry_from_attribute', {})
        self.shape_attribute_txt_to_glossary_entry = cfg.get('shape_attribute_txt_to_glossary_entry', {})

        self.extract_email_from_attribute = cfg.get('extract_email_from_attribute', [])
        self.models_types_in_fad = cfg.get('models_types_in_fad', [])

        self.convert_tasks_to_collapsed_subprocess = cfg.get('convert_tasks_to_collapsed_subprocess', False)
        self.check_assigned_models_in_FAD = cfg.get('check_assigned_models_in_FAD', False)
        self.process_data_models = cfg.get('process_data_models', False)
        self.process_dict_models = cfg.get('process_dict_models', False)
        self.process_matrix_models = cfg.get('process_matrix_models', False)

        self.put_original_bpmn_diagrams_to_entry_field = cfg.get('put_original_bpmn_diagrams_to_entry_field', False)
        self.aris_bpmn_diagram_types = cfg.get('aris_bpmn_diagram_types', False)

        self.split_linking_diagrams_to_multiple_link_events = cfg.get('split_linking_diagrams_to_multiple_link_events', False)

        self.preprocessor = PreProcessor(cfg=cfg,
                                         models=self.models,
                                         connections=self.connections,
                                         obj_definitions=self.obj_definitions,
                                         dictionary_items_file_tracker=self.dictionary_items_file_tracker
                                         )
        self.preprocessor.preprocess_all()

        # Get preprocessed data
        self.task_def_to_fad_mapping = self.preprocessor.task_def_to_fad_mapping
        self.task_def_to_data_model_mapping = self.preprocessor.task_def_to_data_model_mapping
        self.task_def_to_dict_item_from_matrix_model = self.preprocessor.task_def_to_dict_item_from_matrix_model
        self.models_to_parse_for_dict_item = self.preprocessor.models_to_parse_for_dict_item

        self.__load_templates(cfg)
        self.__init_connection_types_for_responsible()

    def __load_templates(self, cfg):
        """Load template files."""
        self.template_bpmn = read_json_file("template_bpmn.json", "input")
        self.template_vc = read_json_file("template_valueChain.json", "input")
        self.template_signavio_shape_data = read_json_file(
            "template_signavio_shape_data.json", "input"
        )
        if cfg.get('file_path_hierarchy_builder_json', ''):
            self.aris_signavio_model_id_mapping = read_json_file(
                cfg.get('file_path_hierarchy_builder_json', ''), "output", file_name_is_path=True
            )
            # create a mapping between signavio key to aris guid mapping
            self.signavio_id_aris_mapping = {}
            for aris_guid in self.aris_signavio_model_id_mapping:
                signavio_id = self.aris_signavio_model_id_mapping[aris_guid].get('Id', '')
                self.signavio_id_aris_mapping[signavio_id] = aris_guid

    def __init_connection_types_for_responsible(self):
        self.connection_type_for_responsible = []
        for key, sub_dict in self.attribute_mapping_based_on_connection_type.items():
            if isinstance(sub_dict, dict):
                for sub_key, value in sub_dict.items():
                    if value == 'meta-responsible':
                        self.connection_type_for_responsible.append(key)

    def __find_connected_parent_guid(self, shape, shape_occurences, target_signavio_type):
        """
        Scan a shape's outgoing and incoming connections for an occurrence whose
        symbol maps to *target_signavio_type* (e.g. 'Pool' or 'Lane').
        Returns the ARIS-definition GUID of the first match, or '' if none found.
        """
        for cxns in (shape.get("outgoing_cxns", {}), shape.get("incoming_cxns", {})):
            for connected_occ_id in cxns:
                connected_occ = shape_occurences.get(connected_occ_id, {})
                symbol = connected_occ.get('symbol', '')
                derived = connected_occ.get('derived_symbol', '')
                key = self.is_keyword_in_list(symbol, list(self.shape_mapping.keys())) or \
                    self.is_keyword_in_list(derived, list(self.shape_mapping.keys()))
                if key and self.shape_mapping.get(key) == target_signavio_type:
                    def_id = connected_occ.get('def', '')
                    return self.obj_definitions.get(def_id, {}).get('guid', '')
        return ''

    def create_shape(self, shape_id, shape_type, properties=None, predecessors=[], model_guid=None, parent='', def_id='', aris_symbol_type='', dictionary_item_href=''):
        new_shape = copy.deepcopy(self.template_signavio_shape_data.get(shape_type))
        new_shape["resourceId"] = copy.deepcopy(shape_id)
        if properties:
            new_shape['properties'].update(copy.deepcopy(properties))
        if predecessors:
            new_shape['predecessor'] = copy.deepcopy(predecessors)
        else:
            new_shape['predecessor'] = []
        new_shape['def_id'] = copy.deepcopy(def_id)
        new_shape['aris_symbol_type'] = copy.deepcopy(aris_symbol_type)
        new_shape['parent'] = copy.deepcopy(parent)
        if dictionary_item_href:
            if '/glossary/' not in dictionary_item_href:
                dictionary_item_href = '/glossary/' + dictionary_item_href
            glossary_link = {"glossaryLinks": {"name": [dictionary_item_href]},
                             "labelDirtyStates": {"en_us": "CLEAN"}}
            new_shape.update(copy.deepcopy(glossary_link))

        if model_guid:
            self.models_to_create[model_guid]["shapes"][shape_id] = copy.deepcopy(new_shape)

        return new_shape

    def get_models(self):

        self.get_model_shapes()
        # write to file
        write_json_file(self.models_to_create, 'all_models.json', 'output')
        if self.is_remove_intermediate_events_after_exclusive_gateway:
            logger.info(f'Started removing intermediate events after gateways')
            self.remove_intermediate_events_after_exclusive_gateway()
            logger.info(f'Completed deletion of intermediate events after gateways')

        # checks parent of each shape
        # if lane is not created already, will create the lane and put the elements
        # Additionally, based on config, will transform shapes
        self.modify_model_shapes()

        # change shape ids, remove dots
        self.change_shape_ids()

        if self.split_linking_diagrams_to_multiple_link_events:
            self.__create_intermediate_link_events()

        if self.put_original_bpmn_diagrams_to_entry_field:
            self.__check_diagrams_in_linking_diagrams_attr()

        # write to file
        write_json_file(self.models_to_create, 'all_models.json', 'output')

        return self.models_to_create

    def __check_diagrams_in_linking_diagrams_attr(self):
        # If there is more than one linking diagrams via Intermediate Link Events,
        # then if the original model was a BPMN it must go into the standard field,
        # and if EPC into the custom linkingdiagrams field.
        # If only one linked model, it can go into the standard field.
        for model_guid in self.models_to_create:
            # type check
            # is_bpmn = self.models_to_create[model_guid]['type'] == 'bpmn'
            is_bpmn = "BPMN" in self.models[self.models_to_create[model_guid]["aris_id"]].get("type", "")
            if is_bpmn:
                continue
            model_shapes = self.models_to_create[model_guid]['shapes']
            for shape_id in model_shapes:
                # check entry field
                # linking diagrams field
                shape = model_shapes.get(shape_id, {})
                if shape.get('stencil', {}).get('id', '') in ['IntermediateLinkEventCatching', 'IntermediateLinkEventThrowing', 'ProcessCollapsed']:
                    linking_diagrams = shape['properties'].get(self.linking_diagram_attr, [])
                    entry = shape['properties']['entry']
                    entry_field = ""
                    if entry:
                        # check entry model type
                        model_type = self.__check_aris_model_type_via_signavio_model_link(entry)
                        if model_type in self.aris_bpmn_diagram_types:
                            continue
                        for linked_diagram in linking_diagrams:
                            model_type = self.__check_aris_model_type_via_signavio_model_link(linked_diagram)
                            if model_type in self.aris_bpmn_diagram_types:
                                entry_field = linked_diagram
                                break
                    if entry_field:
                        # update entry
                        linking_diagrams.append(entry)
                        # replace linking diagrams
                        linking_diagrams.remove(entry_field)
                        shape['properties']['entry'] = entry_field

    def __check_aris_model_type_via_signavio_model_link(self, signavio_link):
        aris_guid = self.signavio_id_aris_mapping.get(signavio_link)
        model_key = [model_key for model_key in self.models if self.models[model_key]['guid'] == aris_guid]
        if model_key:
            return self.models[model_key[0]]['type']
        else:
            return None

    def change_shape_ids(self):
        for model_guid in self.models_to_create:
            model_shapes = self.models_to_create[model_guid]['shapes']
            model_shapes_copy = copy.deepcopy(self.models_to_create[model_guid]['shapes'])
            for shape_id in model_shapes_copy:
                new_shape_id = shape_id.replace('.', '')
                model_shapes[new_shape_id] = copy.deepcopy(model_shapes.get(shape_id, {}))
                if '.' in shape_id:
                    del model_shapes[shape_id]
                # check resourceId
                model_shapes[new_shape_id]['resourceId'] = copy.deepcopy(
                    model_shapes[new_shape_id]['resourceId'].replace('.', ''))
                # check outgoing
                for outgoing in model_shapes[new_shape_id].get('outgoing', []):
                    outgoing['resourceId'] = outgoing['resourceId'].replace('.', '')
                # update target
                target = copy.deepcopy(model_shapes[new_shape_id].get('target', {})).get('resourceId',
                                                                                         '')
                if target:
                    model_shapes[new_shape_id]['target']['resourceId'] = target.replace('.', '')
                # check predecessor
                predecessor_copy = copy.deepcopy(model_shapes[new_shape_id].get('predecessor', []))
                for predecessor_key in predecessor_copy:
                    new_predecessor_key = copy.deepcopy(predecessor_key.replace('.', ''))
                    model_shapes[new_shape_id]['predecessor'].append(new_predecessor_key)
                    model_shapes[new_shape_id]['predecessor'].remove(predecessor_key)
                # check parent
                if model_shapes[new_shape_id].get('parent'):
                    new_parent_id = model_shapes[new_shape_id]['parent'].replace('.', '')
                    model_shapes[new_shape_id]['parent'] = copy.deepcopy(new_parent_id)

    def modify_model_shapes(self):
        """
        This method can be changed based on customer's data
        Current Implementation: Iterates over the shapes and converts 'Intermediate Events' into Start, End event or Throwing Intermediate Link Events
        Intermediate Event followed by Process Interface(collapsed subprocess) is converted to Throwing Intermediate Link Events
        For EPC's Lane is created based on dictionary entries, by using guid's of dictionary entries
        Function updates each shapes lane information, by updating "parent" key for shape
        :return:
        """
        # check events
        # if event has process interface as successor then change it to Throwing Intermediate Link Event
        # if event doesn't have a predecessor, change it to Start Event
        # if event has doesn't have a successor then change it to End Event
        for model_guid in self.models_to_create:
            model_shapes = self.models_to_create[model_guid]['shapes']
            model_shapes_copy = copy.deepcopy(self.models_to_create[model_guid]['shapes'])
            if self.models_to_create[model_guid]['type'] == 'bpmn':
                for shape_id in model_shapes_copy:
                    shape = model_shapes.get(shape_id, {})
                    # Convert Process Interfaces to Throwing/Catching Intermediate Link Events
                    # TODO: CONFIGURATION :
                    # converter_flag_to_transform_process_interfaces_into_intermediate_link_events should be set to True
                    # AND process interface symbol should be added to process_interface_symbols
                    if self.transform_process_interfaces_into_intermediate_link_events:
                        if shape and shape.get('aris_symbol_type') in self.process_interface_symbols:
                            # check successor, predecessor
                            successors = shape.get('outgoing', [])
                            predecessors = shape.get("predecessor", [])
                            parent = shape.get("parent", '')
                            aris_symbol_type = copy.deepcopy(shape.get('aris_symbol_type'))
                            shape_properties = self.__get_shape_properties(shape)
                            if successors == [] and predecessors == []:
                                # change Process Interface shape to intermediateLinkEventCatching
                                self.create_shape(shape_id, shape_type='IntermediateLinkEventCatching',
                                                  properties=shape_properties, model_guid=model_guid, parent=parent)
                                model_shapes[shape_id]['outgoing'] = copy.deepcopy(successors)
                                model_shapes[shape_id]['aris_symbol_type'] = copy.deepcopy(aris_symbol_type)
                            elif successors == []:
                                # change Process Interface shape to IntermediateLinkEventThrowing
                                self.create_shape(shape_id, shape_type='IntermediateLinkEventThrowing',
                                                  properties=shape_properties, predecessors=predecessors, model_guid=model_guid, parent=parent)
                                model_shapes[shape_id]['aris_symbol_type'] = copy.deepcopy(aris_symbol_type)
                            elif predecessors == []:
                                # change Process Interface shape to IntermediateLinkEventCatching
                                # set outgoing
                                self.create_shape(shape_id, shape_type='IntermediateLinkEventCatching',
                                                  properties=shape_properties, model_guid=model_guid, parent=parent)
                                model_shapes[shape_id]['outgoing'] = copy.deepcopy(successors)
                                model_shapes[shape_id]['aris_symbol_type'] = copy.deepcopy(aris_symbol_type)
                            # elif successors != [] and predecessors != []:
                                # change Process Interface shape to IntermediateLinkEventThrowing
                                # set predecessors
                            #    self.create_shape(shape_id, shape_type='IntermediateLinkEventThrowing',
                            #                      properties=shape_properties, predecessors=predecessors, model_guid=model_guid, parent=parent)
                            #    model_shapes[shape_id]['outgoing'] = copy.deepcopy(successors)
                            #    model_shapes[shape_id]['aris_symbol_type'] = copy.deepcopy(aris_symbol_type)

                    # If diagram has only ex.ST_EV and if the type of the event cannot be identified via attributes,
                    # TODO: CONFIGURATION
                    # In the config, configure it as IntermediateEvent
                    # following code will check predecessor and successor element and change it to StartNone or EndNone Event
                    if shape and shape.get('stencil', {}).get('id', '') == 'IntermediateEvent':
                        # check predecessor &  successor
                        successors = shape.get('outgoing', [])
                        predecessors = shape.get("predecessor", [])
                        # shape_properties = {key: value for key, value in shape.get('properties', {}).items() if
                        #                    key.startswith('name') or key.startswith('meta-') or key.startswith('documentation') or key.startswith('description') and key != 'namespace'}
                        shape_properties = self.__get_shape_properties(shape)

                        if predecessors == [] or (successors == [] and predecessors == []):  # and process_interface_exists is False:
                            # change it to Start Event
                            self.create_shape(shape_id, shape_type='StartNoneEvent',
                                              properties=shape_properties, predecessors=None, model_guid=model_guid)
                            model_shapes[shape_id]['outgoing'] = copy.deepcopy(successors)
                        elif successors == [] and predecessors != []:  # if successor is None
                            self.create_shape(shape_id, shape_type='EndNoneEvent',
                                              properties=shape_properties, predecessors=predecessors, model_guid=model_guid)

                        if self.remove_intermediate_events_before_and_after_process_interfaces:
                            if successors != [] and predecessors != []:
                                # check if successor element is Process Interface
                                # get name of Intermediate event
                                name_intermediate_event = model_shapes.get(
                                    shape_id, {}).get('properties', {}).get('name', '')
                                for successor in successors:
                                    successor_sequence_flow_id = successor.get('resourceId', '')
                                    # check outgoing of sequence flow
                                    element_id_to_check_type = model_shapes.get(
                                        successor_sequence_flow_id, {}).get('target', {}).get('resourceId', '')
                                    # mapped_sig_element = self.models_to_create[model_guid]['shapes'].get(element_id_to_check_type, {})
                                    element_shape_type = model_shapes.get(
                                        element_id_to_check_type, {}).get('aris_symbol_type')

                                    if element_shape_type in self.list_of_process_interface_symbols_to_remove_intermediate_events_coming_before_and_after_process_interfaces:
                                        # check predecessor of Intermediate Event , update the outgoing and target of sequence flow
                                        if len(predecessors) == 1:
                                            predecessor_id_sequence_flow = predecessors[0]
                                            if predecessor_id_sequence_flow in model_shapes:
                                                model_shapes[predecessor_id_sequence_flow]['outgoing'] = [
                                                    {'resourceId': element_id_to_check_type}]
                                                model_shapes[predecessor_id_sequence_flow]['target'] = {
                                                    'resourceId': element_id_to_check_type}
                                                # update name of sequence flow
                                                name_seq_flow = model_shapes[predecessor_id_sequence_flow].get(
                                                    'name', '')
                                                if len(name_seq_flow) != 0:
                                                    name_seq_flow = name_seq_flow + ' & ' + name_intermediate_event
                                                else:
                                                    name_seq_flow = name_intermediate_event
                                                model_shapes[predecessor_id_sequence_flow]['properties']['name'] = copy.deepcopy(
                                                    name_seq_flow)
                                                # update process interfaces predecessor
                                                if len(model_shapes[element_id_to_check_type]['predecessor']) > 0:
                                                    model_shapes[element_id_to_check_type]['predecessor'].remove(
                                                        successor_sequence_flow_id)
                                                    model_shapes[element_id_to_check_type]['predecessor'].append(
                                                        predecessor_id_sequence_flow)
                                                else:
                                                    model_shapes[element_id_to_check_type]['predecessor'] = [
                                                        predecessor_id_sequence_flow]
                                                # delete Intermediate Event
                                                del model_shapes[shape_id]
                                                # delete sequence flow coming after intermediate event
                                                del model_shapes[successor_sequence_flow_id]

                                # if intermediate event is not deleted continue with check to predecessor
                                if shape_id in model_shapes:
                                    for predecessor in predecessors:
                                        predecessor_sequence_flow_id = predecessor
                                        # check outgoing of sequence flow
                                        element_id_to_check_type = model_shapes.get(
                                            predecessor_sequence_flow_id, {}).get("predecessor", [])
                                        if len(element_id_to_check_type) > 0:
                                            element_id_to_check_type = element_id_to_check_type[0]
                                        # mapped_sig_element = self.models_to_create[model_guid]['shapes'].get(element_id_to_check_type, {})
                                        element_shape_type = model_shapes.get(
                                            element_id_to_check_type, {}).get('aris_symbol_type', '')
                                        if element_shape_type in self.list_of_process_interface_symbols_to_remove_intermediate_events_coming_before_and_after_process_interfaces:
                                            # check successor of Intermediate Event , update the predecessor of sequence flow
                                            if len(successors) == 1:
                                                successor_sequence_flow_id = successors[0].get('resourceId', '')
                                                if successor_sequence_flow_id in model_shapes:
                                                    if len(model_shapes[successor_sequence_flow_id]['predecessor']) > 0:
                                                        model_shapes[successor_sequence_flow_id]['predecessor'].remove(
                                                            shape_id)
                                                        model_shapes[successor_sequence_flow_id]['predecessor'].append(
                                                            element_id_to_check_type)
                                                    else:
                                                        model_shapes[successor_sequence_flow_id]['predecessor'] = [
                                                            element_id_to_check_type]
                                                    # update name of sequence flow
                                                    name_seq_flow = model_shapes[successor_sequence_flow_id].get(
                                                        'name', '')
                                                    if len(name_seq_flow) != 0:
                                                        name_seq_flow = name_seq_flow + ' & ' + name_intermediate_event
                                                    else:
                                                        name_seq_flow = name_intermediate_event

                                                    model_shapes[successor_sequence_flow_id]['properties']['name'] = copy.deepcopy(
                                                        name_seq_flow)
                                                    # update successor of Process Interface
                                                    model_shapes[element_id_to_check_type]['outgoing'] = [
                                                        {'resourceId': successor_sequence_flow_id}]
                                                    # delete Intermediate Event
                                                    del model_shapes[shape_id]
                                                    # delete predecessor of Intermediate Event
                                                    del model_shapes[predecessor_sequence_flow_id]

                    # Check parent/Lane information for shapes, if it doesn't exist in shapes, create Lane in shapes with corresponsding dictionary link
                    if shape and shape.get('stencil', {}).get('id', '') != 'Lane':
                        # check parent
                        lane_obj_guid = model_shapes.get(shape_id, {}).get('parent', '')
                        responsibles = model_shapes.get(shape_id, {}).get('properties', {}).get('meta-responsible', [])

                        if lane_obj_guid != 'Fallback_Lane' and lane_obj_guid != '' and lane_obj_guid not in model_shapes:

                            # get guid of object definition
                            shape_aris_id = lane_obj_guid
                            if shape_aris_id not in model_shapes:
                                if len(responsibles) == 1:
                                    dictionary_item_href = responsibles[0]
                                    # create lane
                                    # change shapes parent from obj occ to obj aris guid
                                    self.create_shape(shape_aris_id, shape_type='Lane', model_guid=model_guid, parent=shape_aris_id,
                                                      def_id='', aris_symbol_type='', dictionary_item_href=dictionary_item_href)
                                    model_shapes[shape_aris_id]["properties"]["meta-arisguid"] = shape_aris_id
                                else:
                                    # get guid of object definition
                                    guid_of_dict = lane_obj_guid
                                    # get dictionary item
                                    data_exist, dictionary_item_json = self.dictionary_items_file_tracker.is_task_done(guid_of_dict)
                                    if data_exist:
                                        dictionary_item_id = dictionary_item_json.get('json', {}).get('id', '')
                                        if dictionary_item_id:
                                            dictionary_item_href = '/glossary/' + dictionary_item_id
                                            # create lane
                                            # change shapes parent from obj occ to obj aris guid
                                            self.create_shape(shape_aris_id, shape_type='Lane', model_guid=model_guid, parent=shape_aris_id,
                                                              def_id='', aris_symbol_type='', dictionary_item_href=dictionary_item_href)
                                            model_shapes[shape_aris_id]["properties"]["meta-arisguid"] = shape_aris_id
                                    else:
                                        logger.error(
                                            f'Dictionary Item for Lane cannot be found in FileTracker. GUID: {guid_of_dict} for Shape ID: {shape_id}')

    def __create_intermediate_link_events(self):
        # create Inclusive Gateway
        # link new Intermediate Link Events to the Gateway
        for model_guid in self.models_to_create:
            model_shapes = self.models_to_create[model_guid]['shapes']
            model_shapes_copy = copy.deepcopy(self.models_to_create[model_guid]['shapes'])
            if self.models_to_create[model_guid]['type'] == 'bpmn':
                for shape_id in model_shapes_copy:
                    shape = model_shapes.get(shape_id, {})
                    if shape.get('stencil', {}).get('id', '') == 'IntermediateLinkEventCatching':
                        # check successor, predecessor
                        successors = copy.deepcopy(shape.get('outgoing', []))
                        predecessors = shape.get("predecessor", [])
                        shape_properties = self.__get_shape_properties(shape)
                        # check assigned models
                        assigned_models = shape.get("properties", {}).get(self.linking_diagram_attr, [])
                        counter = 1
                        successor_id = ''

                        if successors:
                            successor_id = successors[0].get('resourceId', '')
                        new_sequence_flow_ids = []
                        for new_model in assigned_models:
                            # create a new shape
                            # change Process Interface shape to intermediateLinkEventCatching
                            new_shape_id = shape_id + '-' + str(counter)
                            self.create_shape(shape_id=new_shape_id, model_guid=model_guid, shape_type='IntermediateLinkEventCatching',
                                              properties=shape_properties, parent=model_shapes[shape_id]["parent"])
                            model_shapes[new_shape_id]["properties"]['entry'] = copy.deepcopy(new_model)
                            model_shapes[new_shape_id]["properties"][self.linking_diagram_attr] = []

                            # update name of the event with model name
                            self.update_shape_name_with_linking_diagram(
                                model_guid=model_guid, shape_id=new_shape_id, linking_diagram_id_to_filter=new_model)

                            # TODO: update entry field of intermediate link event
                            # get one successor id
                            if successor_id:
                                new_sequenceflow_id = successor_id + '-SequenceFlow' + str(counter)
                                new_sequence_flow_ids.append(new_sequenceflow_id)
                                # create sequence flow
                                self.create_shape(shape_id=new_sequenceflow_id, model_guid=model_guid, shape_type='SequenceFlow', predecessors=[
                                                  new_shape_id], parent=model_shapes[shape_id]["parent"])

                                # set outgoing of new Intermediate link event
                                model_shapes[new_shape_id]['outgoing'] = copy.deepcopy(
                                    [{"resourceId": new_sequenceflow_id}])
                            counter += 1

                        # create Gateway and set predecessor and successor elements, update predecessor of Gateway
                        # create sequence flow
                        if assigned_models:
                            new_gateway_id = shape_id + '-' + 'Gateway'
                            # set successor of gateway
                            self.create_shape(shape_id=new_gateway_id, model_guid=model_guid, shape_type='InclusiveGateway',
                                              parent=model_shapes[shape_id]["parent"])
                            model_shapes[new_gateway_id]['outgoing'] = copy.deepcopy(successors)

                            for new_seq_flow_id in new_sequence_flow_ids:
                                model_shapes[new_gateway_id]["predecessor"].append(new_seq_flow_id)
                                # set sucessor of sequence flows
                                model_shapes[new_seq_flow_id]['outgoing'].append({"resourceId": new_gateway_id})
                                model_shapes[new_seq_flow_id]['target'] = {"resourceId": new_gateway_id}

                            # update sequence flows predecessor
                            for successor_sequence_flow_key in successors:
                                successor_sequence_flow_key = successor_sequence_flow_key.get('resourceId', '')
                                model_shapes[successor_sequence_flow_key]["predecessor"] = [
                                    copy.deepcopy(new_gateway_id)]

                            # change existing shapes successor element
                            # create a sequence flow
                            new_sequenceflow_id_for_shape = shape_id + '-SequenceFlow'
                            self.create_shape(shape_id=new_sequenceflow_id_for_shape, model_guid=model_guid, shape_type='SequenceFlow', predecessors=[
                                              copy.deepcopy(shape_id)], parent=model_shapes[shape_id]["parent"])
                            model_shapes[new_sequenceflow_id_for_shape]['outgoing'] = copy.deepcopy([
                                {"resourceId": new_gateway_id}])
                            model_shapes[new_sequenceflow_id_for_shape]['target'] = {"resourceId": new_gateway_id}

                            model_shapes[shape_id]["outgoing"] = copy.deepcopy(
                                [{"resourceId": new_sequenceflow_id_for_shape}])

                            # update assigned models field
                            model_shapes[shape_id]['properties'][self.linking_diagram_attr] = []

                            # update shapes name with linking diagram name
                            linked_model_via_original_shape = shape_properties.get('entry', '')
                            if linked_model_via_original_shape:
                                self.update_shape_name_with_linking_diagram(
                                    model_guid=model_guid, shape_id=shape_id, linking_diagram_id_to_filter=linked_model_via_original_shape)

                    elif shape.get('stencil', {}).get('id', '') == 'IntermediateLinkEventThrowing':

                        # check successor, predecessor
                        successors = copy.deepcopy(shape.get('outgoing', []))
                        predecessors = copy.deepcopy(shape.get("predecessor", []))
                        shape_properties = self.__get_shape_properties(shape)

                        # check assigned models
                        assigned_models = shape.get("properties", {}).get(self.linking_diagram_attr, [])
                        counter = 1
                        predecessor_id = ''
                        if predecessors:
                            predecessor_id = predecessors[0]
                        new_sequence_flow_ids = []
                        new_event_ids = []
                        for new_model in assigned_models:
                            # create a new shape
                            # change Process Interface shape to IntermediateLinkEventCatching
                            new_shape_id = shape_id + '-' + str(counter)
                            self.create_shape(shape_id=new_shape_id, model_guid=model_guid, shape_type="IntermediateLinkEventThrowing",
                                              properties=shape_properties, parent=model_shapes[shape_id]["parent"])
                            model_shapes[new_shape_id]["properties"]['entry'] = copy.deepcopy(new_model)
                            model_shapes[new_shape_id]["properties"][self.linking_diagram_attr] = []

                            # update name of the event with model name
                            self.update_shape_name_with_linking_diagram(
                                model_guid=model_guid, shape_id=new_shape_id, linking_diagram_id_to_filter=new_model)

                            new_event_ids.append(new_shape_id)
                            # get one successor id
                            if predecessor_id:
                                new_sequenceflow_id = predecessor_id + '-SequenceFlow' + str(counter)
                                new_sequence_flow_ids.append(new_sequenceflow_id)
                                # create sequence flow
                                # set predecessor and outgoing
                                self.create_shape(shape_id=new_sequenceflow_id, model_guid=model_guid, shape_type="SequenceFlow",
                                                  parent=model_shapes[shape_id]["parent"])

                                model_shapes[new_sequenceflow_id]['outgoing'] = copy.deepcopy([
                                    {"resourceId": new_shape_id}])

                                model_shapes[new_sequenceflow_id]['target'] = copy.deepcopy({
                                    "resourceId": new_shape_id})

                                # set outgoing of new Intermediate link event
                                model_shapes[new_shape_id]["predecessor"] = copy.deepcopy([new_sequenceflow_id])

                            counter += 1

                        # create Gateway and set predecessor and successor elements, update predecessor of Gateway
                        # create sequence flow
                        if assigned_models:
                            new_gateway_id = shape_id + '-' + 'Gateway'
                            model_shapes[new_gateway_id] = copy.deepcopy(
                                self.template_signavio_shape_data.get('InclusiveGateway', {}))
                            model_shapes[new_gateway_id]['resourceId'] = new_gateway_id
                            model_shapes[new_gateway_id]['outgoing'] = []
                            model_shapes[new_gateway_id]["parent"] = model_shapes[shape_id]["parent"]

                            # set successor and predecessor of gateway
                            model_shapes[new_gateway_id]["predecessor"] = copy.deepcopy(predecessors)

                            # update predecessors next element
                            for predecessor_sequence_flow_key in predecessors:
                                model_shapes[predecessor_sequence_flow_key]["outgoing"] = [
                                    {"resourceId": copy.deepcopy(new_gateway_id)}]
                                model_shapes[predecessor_sequence_flow_key]["target"] = {
                                    "resourceId": copy.deepcopy(new_gateway_id)}

                            for new_seq_flow_id in new_sequence_flow_ids:
                                model_shapes[new_gateway_id]['outgoing'].append({"resourceId": copy.deepcopy(new_seq_flow_id)})
                                # set predecessor of sequence flows
                                model_shapes[new_seq_flow_id]["predecessor"].append(new_gateway_id)

                            # change existing shapes successor element
                            # create a sequence flow
                            new_sequenceflow_id_for_shape = shape_id + '-SequenceFlow'

                            self.create_shape(shape_id=new_sequenceflow_id_for_shape, model_guid=model_guid, shape_type="SequenceFlow",
                                              parent=model_shapes[shape_id]["parent"], predecessors=[copy.deepcopy(new_gateway_id)])

                            model_shapes[new_sequenceflow_id_for_shape]['outgoing'] = [
                                {"resourceId": copy.deepcopy(shape_id)}]

                            model_shapes[new_sequenceflow_id_for_shape]['target'] = {"resourceId": copy.deepcopy(shape_id)}

                            model_shapes[shape_id]["predecessor"] = [new_sequenceflow_id_for_shape]
                            model_shapes[new_gateway_id]['outgoing'].append(
                                {"resourceId": new_sequenceflow_id_for_shape})

                            if successors != []:
                                # create new gateway
                                new_gateway_id = shape_id + '-' + 'Gateway2'
                                self.create_shape(shape_id=new_gateway_id, shape_type="InclusiveGateway", model_guid=model_guid,
                                                  parent=model_shapes[shape_id]["parent"])
                                model_shapes[new_gateway_id]['outgoing'] = copy.deepcopy(successors)

                                # successor sequence id
                                for new_event_id in new_event_ids:
                                    # create sequence flow
                                    new_sequenceflow_id_for_new_event = new_event_id + '-SequenceFlow'

                                    self.create_shape(shape_id=new_sequenceflow_id_for_new_event, shape_type="SequenceFlow", model_guid=model_guid, predecessors=[copy.deepcopy(new_event_id)],
                                                      parent=model_shapes[shape_id]["parent"])
                                    model_shapes[new_sequenceflow_id_for_new_event]['outgoing'] = copy.deepcopy(
                                        [{"resourceId": new_gateway_id}])

                                    model_shapes[new_sequenceflow_id_for_new_event]['target'] = {
                                        "resourceId": new_gateway_id}

                                    model_shapes[new_gateway_id]["predecessor"].append(
                                        new_sequenceflow_id_for_new_event)
                                    model_shapes[new_event_id]["outgoing"].append(
                                        copy.deepcopy({"resourceId": new_sequenceflow_id_for_new_event}))

                                # update existing shapes next element
                                # create sequence flow
                                new_sequenceflow_id_for_shape2 = shape_id + '-SequenceFlow2'

                                self.create_shape(shape_id=new_sequenceflow_id_for_shape2, shape_type="SequenceFlow", model_guid=model_guid, predecessors=[copy.deepcopy(shape_id)],
                                                  parent=model_shapes[shape_id]["parent"])

                                model_shapes[new_sequenceflow_id_for_shape2]['outgoing'] = copy.deepcopy([
                                    {"resourceId": new_gateway_id}])
                                model_shapes[new_sequenceflow_id_for_shape2]['target'] = {"resourceId": new_gateway_id}
                                model_shapes[new_gateway_id]["predecessor"].append(new_sequenceflow_id_for_shape2)
                                model_shapes[shape_id]["outgoing"] = copy.deepcopy(
                                    [{"resourceId": new_sequenceflow_id_for_shape2}])
                                # update sequence flows predecessor
                                for successor_sequence_flow_key in successors:
                                    successor_sequence_flow_key = successor_sequence_flow_key.get('resourceId', '')
                                    model_shapes[successor_sequence_flow_key]["predecessor"] = [
                                        copy.deepcopy(new_gateway_id)]

                            # update assigned models field
                            model_shapes[shape_id]['properties'][self.linking_diagram_attr] = []

                            # update shapes name with linking diagram name
                            linked_model_via_original_shape = shape_properties.get('entry', '')
                            if linked_model_via_original_shape:
                                self.update_shape_name_with_linking_diagram(
                                    model_guid=model_guid, shape_id=shape_id, linking_diagram_id_to_filter=linked_model_via_original_shape)

    def update_shape_name_with_linking_diagram(self, model_guid, shape_id, linking_diagram_id_to_filter):
        data_id = self.signavio_id_aris_mapping.get(linking_diagram_id_to_filter)
        if data_id:
            data_exists, result = self.model_file_tracker.is_task_done(data_id)
            new_name = result.get('json', {}).get('rep', {}).get('name') or result.get('json', {}).get('properties', {}).get('name')
            if new_name:
                self.models_to_create[model_guid]["shapes"][shape_id]['properties']['name'] = copy.deepcopy(new_name)

    def remove_intermediate_events_after_exclusive_gateway(self):
        for model_guid in self.models_to_create:
            model_shapes = self.models_to_create[model_guid]['shapes']
            model_shapes_copy = copy.deepcopy(self.models_to_create[model_guid]['shapes'])
            if self.models_to_create[model_guid]['type'] == 'bpmn':
                for shape_id in model_shapes_copy:
                    shape = model_shapes.get(shape_id, {})
                    if shape and 'Exclusive_Databased_Gateway' in shape.get('stencil', {}).get('id', ''):
                        # check successors
                        successors = shape.get('outgoing', [])
                        for successor in successors:
                            successor_sequence_flow_id = successor.get('resourceId', '')
                            # check outgoing of sequence flow
                            element_id_to_check_type = model_shapes.get(
                                successor_sequence_flow_id, {}).get('target', {}).get('resourceId', '')
                            mapped_sig_element = model_shapes.get(element_id_to_check_type, {})
                            element_shape_type = mapped_sig_element.get('stencil', {}).get('id', '')
                            name_of_intermediate_event = mapped_sig_element.get('properties', {}).get('name', '')
                            if element_shape_type == 'IntermediateEvent':
                                # check number of successors of IntermediateEvent
                                successors_of_int_event = mapped_sig_element.get('outgoing', [])
                                if len(successors_of_int_event) == 1:
                                    successor_sequence_flow_of_int_event = successors_of_int_event[0].get('resourceId', '')
                                    # get target element of sequence_flow
                                    target_element_id = model_shapes.get(
                                        successor_sequence_flow_of_int_event, {}).get('target', {}).get('resourceId', '')
                                    sequence_flow_properties = model_shapes.get(
                                        successor_sequence_flow_id, {}).get('properties', {})
                                    sequence_flow_name = ''
                                    new_sequence_flow_name = ''
                                    if sequence_flow_properties:
                                        sequence_flow_name = sequence_flow_properties.get('name', '')
                                    if sequence_flow_name != '':
                                        new_sequence_flow_name = sequence_flow_name + ' & ' + name_of_intermediate_event
                                    else:
                                        new_sequence_flow_name = name_of_intermediate_event
                                    if sequence_flow_properties:
                                        model_shapes[successor_sequence_flow_id]['properties']['name'] = copy.deepcopy(
                                            new_sequence_flow_name)

                                    # update sequence flows' outgoing and target
                                    model_shapes[successor_sequence_flow_id]['outgoing'] = [
                                        {'resourceId': target_element_id}]
                                    model_shapes[successor_sequence_flow_id]['target'] = {
                                        'resourceId': target_element_id}
                                    # update predecessor of target element
                                    predecessor_of_target = model_shapes[target_element_id].get('predecessor', [])
                                    if len(predecessor_of_target) > 0:
                                        predecessor_of_target.remove(successor_sequence_flow_of_int_event)

                                    predecessor_of_target.append(successor_sequence_flow_id)
                                    model_shapes[target_element_id]['predecessor'] = copy.deepcopy(
                                        predecessor_of_target)

                                    # delete intermediate event and successor sequence flow of intermediate event
                                    del model_shapes[element_id_to_check_type]
                                    del model_shapes[successor_sequence_flow_of_int_event]

    def get_model_shapes(self):
        # filter models VC and BPMNS
        model_keys = [model_key for model_key in self.models if self.models[model_key]['type'] in self.diagram_types]
        for model_key in model_keys:
            model_guid = self.models.get(model_key, {}).get("guid", "")
            #if model_guid != '8f835ec1-a59b-11ef-180f-5232495bb7aa':
            #    continue
            diagram_model_key = model_key
            pool_counter = 0

            if not model_guid:
                continue

            original_model_type = self.models.get(model_key, {}).get("type", "")
            model_type = self.diagram_types.get(original_model_type, "")
            if model_type == 'vc':
                self.models_to_create[model_guid] = copy.deepcopy(self.template_vc)
            elif model_type == 'bpmn':
                self.models_to_create[model_guid] = copy.deepcopy(self.template_bpmn)
            self.models_to_create[model_guid]["type"] = model_type
            self.models_to_create[model_guid]["aris_id"] = self.models.get(model_key, {}).get("id", "")
            self.models_to_create[model_guid]["aris_guid"] = model_guid
            self.models_to_create[model_guid]["properties"]["meta-arisguid"] = self.models_to_create[model_guid]["aris_guid"]
            # Get diagram level attributes
            # check object definitions that has linking diagram to current model being processed
            # then check the FAD of that object definition
            diagram_attributes_to_attach = {}
            object_def_key_for_model = [
                object_def_key
                for object_def_key in self.task_def_to_fad_mapping
                if self.models_to_create[model_guid]["aris_id"] in self.task_def_to_fad_mapping[object_def_key].get('linked_models', [])
            ]
            if object_def_key_for_model:
                if len(object_def_key_for_model) > 1:
                    logger.warning(
                        f'Model GUID: {model_guid}. Multiple task object definitions in FAD diagrams linking to current model being processed. Task Object Def IDs: {object_def_key_for_model}')
                object_def_key_for_model = object_def_key_for_model[0]
                diagram_attributes_to_attach, result_lane_ignored = self.get_dictionary_entries_attached_in_models(
                    object_def_key_for_model, model_type='fad', flag_attach_loose_elements_to_task=self.flag_to_attach_loose_shapes_to_task_as_attributes)

            if self.process_dict_models:
                models_to_check_for_dictionary_items = self.models_to_parse_for_dict_item.get(model_key, '')
                new_attributes_to_attach = {}
                if models_to_check_for_dictionary_items:
                    diagram_shapes_mapping = {
                        'MT_DMN_CONTEXT_DIAGRAM': ['ST_DMN_DECISION'],
                        'MT_BUSY_CONTR_DGM': ['ST_RISK_1', 'ST_RISK', 'ST_BUSINESS_RULE', 'ST_CONTR'],
                        'MT_BUSINESS_RULES_ALLOC_DGM': ['ST_RISK_1', 'ST_BUSINESS_RULE'],
                        'MT_TOGAF_DIAGRAM': ['ST_PRINCIPLE']
                    }
                    for model_key_to_check in models_to_check_for_dictionary_items:
                        model_data_to_check = self.models.get(model_key_to_check, '')
                        model_type = model_data_to_check.get('type', '')
                        filtered_shape_types = diagram_shapes_mapping.get(model_type, [])
                        shape_occs = model_data_to_check.get('occs', {})
                        self.get_dictionary_entries_attached(shape_occs, new_attributes_to_attach, filtered_shape_types)
                    if new_attributes_to_attach:
                        self.attach_items_to_attributes(new_attributes_to_attach, diagram_attributes_to_attach)

            if self.process_data_models:
                object_def_key_for_model = [
                    object_def_key
                    for object_def_key in self.task_def_to_data_model_mapping
                    if self.models_to_create[model_guid]["aris_id"] in self.task_def_to_data_model_mapping[object_def_key].get('linked_models', [])
                ]
                if object_def_key_for_model:
                    for object_def_key in object_def_key_for_model:
                        dictionary_items_to_attach_from_data_model, lane_ignored = self.get_dictionary_entries_attached_in_models(
                            object_def_key, model_type='data_model')
                        # update diagram_attributes_to_attach
                        if dictionary_items_to_attach_from_data_model:
                            self.attach_items_to_attributes(dictionary_items_to_attach_from_data_model, diagram_attributes_to_attach)

            if self.process_matrix_models:
                object_def_key_from_matrix_models = [
                    object_def_key
                    for object_def_key in self.task_def_to_dict_item_from_matrix_model
                    if self.models_to_create[model_guid]["aris_id"] in self.task_def_to_dict_item_from_matrix_model[object_def_key].get('linked_models', [])
                ]
                # Check Task Definition
                # Attach diagram attributes from matrix model
                for object_def_key_from_mat_mod in object_def_key_from_matrix_models:
                    dictionary_items_to_attach_from_matrix_model = self.task_def_to_dict_item_from_matrix_model.get(
                        object_def_key_from_mat_mod, {}).get('dictionary_items', [])
                    if dictionary_items_to_attach_from_matrix_model:
                        self.attach_items_to_attributes(dictionary_items_to_attach_from_matrix_model, diagram_attributes_to_attach)

            model_attrs = self.models.get(model_key, {}).get("attrs", {})
            model_attrs_to_attach = {}
            styles = copy.deepcopy(model_attrs.get('styles', {}))
            model_attrs['styles'] = {}
            for attr in model_attrs:
                if attr == 'styles':
                    continue
                current_style = styles.get(attr, '')
                sig_model_attr_name = self.attribute_handler.attribute_mapping.get(attr, None)
                attr_val = model_attrs[attr]
                attribute_name_without_suffix = copy.deepcopy(sig_model_attr_name)
                skip_other_langs = False
                for lang_key in attr_val:
                    if skip_other_langs:
                        break
                    aris_val_with_lang_key = attr_val[lang_key]
                    if attribute_name_without_suffix in self.attribute_handler.multilang_attributes:
                        if lang_key != self.attribute_handler.default_workspace_language:
                            # add language suffix to the attribute
                            sig_model_attr_name = attribute_name_without_suffix + '_' + lang_key
                        else:
                            sig_model_attr_name = attribute_name_without_suffix
                    else:
                        skip_other_langs = True

                    if sig_model_attr_name is None:
                        if attr in self.link_attributes_url_label_mapping.keys():
                            self.attribute_handler.convert_link_attribute(
                                aris_attribute_name=attr, aris_attributes=model_attrs, attributes_to_update=model_attrs_to_attach)
                        elif attr not in self.link_attributes_url_label_mapping.keys() and attr not in self.link_attributes_url_label_mapping.values():
                            logger.error(
                                "Attribute is not available in aris_signavio_attribute_name_mapping " + attr)

                    elif sig_model_attr_name.startswith('description'):
                        field_name = sig_model_attr_name.replace(
                            'description', 'documentation') if self.models_to_create[model_guid]['type'] == 'bpmn' else sig_model_attr_name
                        # Update attribute
                        existing_value = model_attrs_to_attach.get(field_name, '')
                        new_value = aris_val_with_lang_key
                        model_attrs_to_attach[field_name] = f"{existing_value} \n {new_value}" if existing_value else new_value

                        # Update style
                        existing_style = model_attrs['styles'].get(field_name, '')
                        model_attrs['styles'][field_name] = f"{existing_style} \n {current_style}" if existing_style else current_style

                    elif attr in self.link_attributes_url_label_mapping.keys():
                        self.attribute_handler.convert_link_attribute(
                            aris_attribute_name=attr, aris_attributes=model_attrs, attributes_to_update=model_attrs_to_attach)

                    else:
                        # Check model attribute txt to Dictionary Item mapping
                        if self.model_attribute_txt_to_glossary_entry and attr in self.model_attribute_txt_to_glossary_entry.keys():
                            aris_val_with_lang_key = aris_val_with_lang_key.strip()
                            category = self.model_attribute_txt_to_glossary_entry[attr]
                            if attr in self.extract_email_from_attribute:
                                aris_val_with_lang_key = aris_val_with_lang_key.lower()
                                aris_val_with_lang_key = self.extract_emails(aris_val_with_lang_key)  # returns list all the time
                            dict_value = None
                            # for category in categories:
                            if isinstance(aris_val_with_lang_key, list):
                                for attr_val_to_check in aris_val_with_lang_key:
                                    self.search_and_create_dict_item(attr, attr_val_to_check, sig_model_attr_name,
                                                                     model_guid, category, model_attrs_to_attach)
                            else:
                                self.search_and_create_dict_item(attr, attr_val, sig_model_attr_name, model_guid, category, model_attrs_to_attach)
                        elif aris_val_with_lang_key in self.attribute_value_mapping.keys():
                            aris_val_with_lang_key = self.attribute_value_mapping.get(aris_val_with_lang_key, '')
                            model_attrs_to_attach[sig_model_attr_name] = copy.deepcopy(aris_val_with_lang_key)
                        else:
                            model_attrs_to_attach[sig_model_attr_name] = aris_val_with_lang_key
                            if sig_model_attr_name in self.list_of_attributes_to_check_formatting:
                                existing_style = model_attrs['styles'].get(sig_model_attr_name, '')
                                model_attrs['styles'][sig_model_attr_name] = f"{existing_style} \n {current_style}" if existing_style else current_style

            diagram_attributes_to_attach.update(model_attrs_to_attach)
            formatted_attr_model = {}
            for attr_name in diagram_attributes_to_attach:
                '''if attr_name in self.model_level_attributes_to_catchall:
                    # check dictionary item glossary category name
                    attribute_value = diagram_attributes_to_attach[attr_name]
                    dict_hrefs = self.dictionary_items_file_tracker.dbu.retrieve_all_with_dynamic_filters(
                        self.dictionary_items_file_tracker.stage_model, filters={'signavio_id': attribute_value})
                    for dict_href in dict_hrefs:
                        if self.catch_all_attribute_name not in formatted_attr_model:
                            formatted_attr_model[self.catch_all_attribute_name] = 'Linked Dictionary Items:' + '\n'
                        formatted_attr_model[self.catch_all_attribute_name] = formatted_attr_model[self.catch_all_attribute_name] + \
                            '\n' + dict_href.get('category_name', '') + ' : ' + str(dict_href.get('signavio_id', ''))
                '''
                if self.models_to_create[model_guid]["type"] == 'bpmn':
                    formatted_attr_model.update(self.attribute_handler.get_property_in_correct_format(
                        attr_name, attribute_value=diagram_attributes_to_attach[attr_name], stencil='BPMNDiagram'))
                elif self.models_to_create[model_guid]["type"] == 'vc':
                    formatted_attr_model.update(self.attribute_handler.get_property_in_correct_format(
                        attr_name, attribute_value=diagram_attributes_to_attach[attr_name], stencil='Diagram'))

            self.models_to_create[model_guid]["properties"]["meta-aristype"] = self.models.get(model_key, {}).get("type", "")
            self.models_to_create[model_guid]["properties"].update(copy.deepcopy(formatted_attr_model))

            self.models_to_create[model_guid]["shapes"] = {}
            model_shapes = self.models_to_create[model_guid]["shapes"]
            shape_occurences = self.models.get(model_key, {}).get("occs", {})
            for shape_key in shape_occurences:  # shape_key is shape occ id
                shape = shape_occurences[shape_key]
                shape_id = shape.get("id", "")
                shape_def_id = shape.get("def", "")
                shape_def_guid = self.obj_definitions.get(shape_def_id, {}).get('guid', '')
                shape_aris_type = shape.get("symbol", "")
                shape_derived_symbol = shape.get("derived_symbol", "")

                #if shape_key == 'ObjOcc.-754Pqkhky_B-u-L--1roJvmVAAcf-x-L-33-c':
                #    print()

                # signavio_shape_type = self._get_signavio_shape_type(shape, list(self.shape_mapping.keys()))
                shape_key_exists = self.is_keyword_in_list(shape_aris_type, list(self.shape_mapping.keys()))
                shape_key_exists_derived_symbol = self.is_keyword_in_list(shape_derived_symbol, list(self.shape_mapping.keys()))
                if not shape_key_exists and shape_key_exists_derived_symbol:
                    shape_key_exists = shape_key_exists_derived_symbol
                    shape_aris_type = shape_derived_symbol

                if shape_key_exists:
                    signavio_shape_type = self.shape_mapping[shape_key_exists]
                    if isinstance(signavio_shape_type, dict):
                        signavio_shape_type = signavio_shape_type.get(self.models_to_create[model_guid]["type"], None)

                    initial_parent = ''
                    if signavio_shape_type == 'Lane':
                        # FOR LANES SET SHAPE ID as GUID
                        shape_id = shape_def_guid
                        # Check connections of the Lane for a Pool relation.
                        # In standard ARIS exports the Lane has an outgoing CT_BELONGS_TO_1 to its Pool,
                        # but fall back to incoming connections in case the export encodes it in reverse.
                        # If found, set the Pool's ARIS GUID as the Lane's parent.
                        initial_parent = self.__find_connected_parent_guid(shape, shape_occurences, 'Pool')

                    elif signavio_shape_type not in ('Pool',) and original_model_type in self.aris_bpmn_diagram_types:
                        # For BPMN diagrams, derive the parent Lane directly from the diagram's
                        # own connections instead of relying on the FAD.
                        initial_parent = self.__find_connected_parent_guid(shape, shape_occurences, 'Lane')

                    if signavio_shape_type:

                        self.create_shape(shape_id, shape_type=signavio_shape_type, model_guid=model_guid, parent=initial_parent,
                                          def_id=shape_def_id, aris_symbol_type=shape_key_exists)
                        model_shapes[shape_id]["properties"]["meta-arisguid"] = shape_def_guid

                        # For BPMN shapes where the parent Lane was derived from the diagram,
                        # also populate meta-responsible with the Lane's dictionary item href.
                        if original_model_type in self.aris_bpmn_diagram_types and initial_parent and signavio_shape_type in ('Task'):
                            _, lane_dict_item = self.dictionary_items_file_tracker.is_task_done(id=initial_parent)
                            if lane_dict_item:
                                lane_dict_item_id = lane_dict_item.get('json', {}).get('id', '')
                                if lane_dict_item_id:
                                    lane_dict_href = '/glossary/' + lane_dict_item_id
                                    model_shapes[shape_id]['properties']['meta-responsible'] = [lane_dict_href]

                        # SET ATTRIBUTES of shape from shape definition
                        object_definition = self.obj_definitions.get(shape_def_id, {})
                        attributes = object_definition.get("attrs", {})
                        signavio_attributes = {}
                        shape_styles = copy.deepcopy(attributes.get('styles', {}))
                        attributes['styles'] = {}
                        for attr in attributes:
                            if attr == 'styles':
                                continue
                            signavio_attribute_name = self.attribute_handler.attribute_mapping.get(attr, None)
                            current_shape_style = shape_styles.get(attr, '')
                            attribute_name_without_suffix = copy.deepcopy(signavio_attribute_name)
                            skip_other_langs = False
                            attr_val = attributes[attr]
                            for lang_key in attr_val:
                                signavio_attribute_name = self.attribute_handler.attribute_mapping.get(attr, None)
                                if skip_other_langs:
                                    continue
                                aris_val_with_lang_key = attr_val[lang_key]
                                if attribute_name_without_suffix in self.attribute_handler.multilang_attributes:
                                    if lang_key != self.attribute_handler.default_workspace_language:
                                        # add language suffix to the attribute
                                        signavio_attribute_name = attribute_name_without_suffix + '_' + lang_key
                                    else:
                                        signavio_attribute_name = attribute_name_without_suffix
                                else:
                                    skip_other_langs = True

                                if signavio_attribute_name is None:
                                    if attr in self.link_attributes_url_label_mapping.keys():
                                        self.attribute_handler.convert_link_attribute(
                                            aris_attribute_name=attr, aris_attributes=attributes, attributes_to_update=signavio_attributes)
                                    elif attr == 'AT_BPMN_ACTIVITY_TYPE':
                                        if aris_val_with_lang_key == "AVT_BPMN_CALL_ACTIVITY":
                                            signavio_attributes["callactivity"] = "true"
                                    elif attr == 'AT_BPMN_SUBPROCESS_TYPE':
                                        if aris_val_with_lang_key == "AVT_BPMN_TRANSACTION":
                                            signavio_attributes["isatransaction"] = "true"
                                        elif aris_val_with_lang_key == "AVT_BPMN_ADHOC_SUB_PROCESS":
                                            signavio_attributes["isadhoc"] = "true"
                                    elif attr not in self.link_attributes_url_label_mapping.keys() and attr not in self.link_attributes_url_label_mapping.values():
                                        logger.error("Attribute is not available in aris_signavio_attribute_name_mapping " + attr)
                                else:
                                    # Remove Default shape names
                                    if signavio_attribute_name.startswith('name'):
                                        if aris_val_with_lang_key in self.default_shape_names:
                                            signavio_attributes[signavio_attribute_name] = ''
                                        else:
                                            signavio_attributes[signavio_attribute_name] = aris_val_with_lang_key
                                        if signavio_attribute_name not in attributes['styles']:
                                            attributes['styles'][signavio_attribute_name] = current_shape_style
                                    elif (signavio_attribute_name.startswith('description')):
                                        # Determine field name based on model type
                                        field_name = signavio_attribute_name.replace(
                                            'description', 'documentation') if self.models_to_create[model_guid]['type'] == 'bpmn' else signavio_attribute_name

                                        # Update attribute value
                                        existing_value = signavio_attributes.get(field_name, '')
                                        signavio_attributes[field_name] = (
                                            f"{existing_value} \n {aris_val_with_lang_key}" if existing_value
                                            else aris_val_with_lang_key
                                        )
                                        # Update style
                                        existing_style = attributes['styles'].get(field_name, '')
                                        attributes['styles'][field_name] = (
                                            f"{existing_style} \n {current_shape_style}" if existing_style
                                            else current_shape_style
                                        )
                                    elif signavio_attribute_name == 'eventtype':
                                        event_type = aris_val_with_lang_key
                                        signavio_event_type = self.attribute_value_mapping.get(event_type, None)
                                        if signavio_event_type is None:
                                            logger.error(
                                                f'Event Type not available in configuration. Attribute: {attr}, Attribute Value: {event_type}. Model ID: {model_guid} Technical Shape ID: {shape_id}')
                                        else:
                                            # change event type
                                            current_shape_type = model_shapes.get(
                                                shape_id, {}).get('stencil', {}).get('id', '')
                                            if isinstance(signavio_event_type, dict):
                                                signavio_event_type = signavio_event_type.get(current_shape_type, None)
                                            if signavio_event_type:
                                                curr_aris_symbol_type = copy.deepcopy(model_shapes.get(shape_id, {}).get('aris_symbol_type', ''))
                                                existing_shape_properties = copy.deepcopy({key: value for key, value in model_shapes[shape_id]["properties"].items(
                                                ) if key in self.aris_signavio_attribute_name_mapping})
                                                self.create_shape(shape_id, shape_type=signavio_event_type, model_guid=model_guid,
                                                                  properties=existing_shape_properties, aris_symbol_type=curr_aris_symbol_type)
                                                model_shapes[shape_id]["properties"]["meta-arisguid"] = shape_id

                                            elif signavio_event_type is None:
                                                logger.error(
                                                    f'Event type is not available for shape type {current_shape_type}. Model ID: {model_guid} Shape ID: {shape_id}')
                                    elif signavio_attribute_name in ['tasktype', 'looptype']:
                                        task_type = aris_val_with_lang_key
                                        signavio_task_type = self.attribute_value_mapping.get(task_type, None)
                                        if signavio_task_type is None:
                                            logger.error(
                                                f'Task Type / Loop Type not available in configuration. Attribute: {attr}, Attribute Value: {task_type}. Model ID: {model_guid} Technical Shape ID: {shape_id}')
                                        else:
                                            signavio_attributes[signavio_attribute_name] = signavio_task_type
                                    elif signavio_attribute_name == 'meta-linkingdiagrams':
                                        logger.warning(
                                            f'Model ID {model_guid}, Shape ID: {shape_id}, Shape type: {model_shapes[shape_id]["aris_symbol_type"]} has custom attribute for linking diagrams. Shape is linking to model ' + attributes[attr])

                                        self.add_attribute_value(signavio_attributes, signavio_attribute_name, aris_val_with_lang_key)

                                        if self.attach_linking_diagrams_from_custom_attribute:
                                            diagrams_to_link = signavio_attributes[signavio_attribute_name]
                                            if len(diagrams_to_link) > 0:
                                                # check whether diagram to link exists in xml file
                                                model_guid_to_link = list(filter(lambda model_key: self.models[model_key]['type'] != self.diagram_types_that_dictionary_items_stored and (
                                                    self.models[model_key].get('guid') == diagrams_to_link[0]), self.models))
                                                signavio_model_id = None
                                                # get guid of the model
                                                if model_guid_to_link == []:
                                                    logger.error(
                                                        f"Model ID: {model_guid}, Shape ID {shape_id}, Diagram Def ID: {diagrams_to_link[0]} . Diagram linked by shape doesn't exist in xml file")
                                                else:
                                                    model_guid_to_link = diagrams_to_link[0]
                                                    signavio_model_id = copy.deepcopy(self.__get_signavio_model_id(
                                                        model_guid_to_link, model_guid, shape_id))
                                                    if signavio_model_id and signavio_model_id.startswith("/model/") and signavio_shape_type != 'Task' and model_shapes[shape_id]["properties"].get('entry', None) == '':
                                                        model_shapes[shape_id]["properties"]["entry"] = copy.deepcopy(signavio_model_id)

                                                # set other linking diagrams as an attribute
                                                if len(diagrams_to_link) >= 1 and signavio_model_id and signavio_shape_type != 'Task':
                                                    # remove first element, that is added as an entry
                                                    signavio_attributes[signavio_attribute_name].remove(diagrams_to_link[0])
                                    elif attr in self.link_attributes_url_label_mapping.keys():
                                        self.attribute_handler.convert_link_attribute(
                                            aris_attribute_name=attr, aris_attributes=attributes, attributes_to_update=signavio_attributes)
                                    else:
                                        # Check shape attribute txt to Dictionary Item mapping
                                        attr_val = aris_val_with_lang_key
                                        if self.shape_attribute_txt_to_glossary_entry and attr in self.shape_attribute_txt_to_glossary_entry.keys():
                                            attr_val = attr_val.strip()
                                            category = self.shape_attribute_txt_to_glossary_entry[attr]
                                            if attr in self.extract_email_from_attribute:
                                                attr_val = attr_val.lower()
                                                attr_val = self.extract_emails(attr_val)  # returns list all the time
                                            dict_value = None
                                            # for category in categories:
                                            if isinstance(attr_val, list):
                                                for attr_val_to_check in attr_val:
                                                    self.search_and_create_dict_item(attr, attr_val_to_check,
                                                                                     signavio_attribute_name, model_guid,
                                                                                     category, signavio_attributes)
                                            else:
                                                self.search_and_create_dict_item(attr, attr_val, signavio_attribute_name,
                                                                                 model_guid, category,
                                                                                 signavio_attributes)

                                        elif attr_val in self.attribute_value_mapping.keys():
                                            attr_val = self.attribute_value_mapping.get(attr_val, '')
                                            signavio_attributes[signavio_attribute_name] = copy.deepcopy(attr_val)
                                        else:
                                            signavio_attributes[signavio_attribute_name] = aris_val_with_lang_key
                                            if signavio_attribute_name in self.list_of_attributes_to_check_formatting:
                                                if signavio_attribute_name not in attributes['styles']:
                                                    attributes['styles'][signavio_attribute_name] = current_shape_style

                        # check custom_attribute_at_signavio_derived_from_symbol_type
                        if self.custom_attribute_at_signavio_derived_from_symbol_type:
                            # check shape type
                            for key in self.custom_attribute_at_signavio_derived_from_symbol_type:
                                attribute_name = key
                                attribute_val_from_config = self.custom_attribute_at_signavio_derived_from_symbol_type[key].get(
                                    model_shapes[shape_id]['aris_symbol_type'], '')
                                if attribute_val_from_config != '':
                                    signavio_attributes.update({attribute_name: attribute_val_from_config})

                        if signavio_attributes:
                            model_shapes[shape_id]["properties"].update(signavio_attributes)

                        # TextAnnotation uses "text"/"text_<lang>" instead of "name"/"name_<lang>"
                        if signavio_shape_type == 'TextAnnotation':
                            props = model_shapes[shape_id]["properties"]
                            for key in list(props.keys()):
                                if key == 'name' or key.startswith('name_'):
                                    new_key = 'text' + key[4:]
                                    props[new_key] = props.pop(key)

                        if signavio_shape_type in ('Lane', 'Pool'):
                            if signavio_shape_type == 'Lane':
                                model_shapes[shape_id]["properties"]["meta-occId"] = shape_occurences.get(shape_key, {}).get('id', '')
                            # update glossary link for Lane, and Pool
                            data_exist, dictionary_item_json = self.dictionary_items_file_tracker.is_task_done(id=shape_def_guid)
                            if dictionary_item_json:
                                dictionary_item_id = dictionary_item_json.get('json', {}).get('id', '')
                                if dictionary_item_id:
                                    dictionary_item_href = '/glossary/' + dictionary_item_id
                                    glossary_link = {"glossaryLinks": {"name": [dictionary_item_href]}, "labelDirtyStates": {"en_us": "CLEAN"}}
                                    model_shapes[shape_id].update(copy.deepcopy(glossary_link))
                            else:
                                logger.error(
                                    f'BPMN Lane cannot be created, dictionary item is missing. Shape ID: <{shape_id}>, Diagram ID: <{model_guid}>')

                        if signavio_shape_type == 'Pool':
                            pool_counter += 1

                        # if vc, change task to ProcessCollapsed
                        # Check whether Task has a linked model, which is different from the current model, if it is convert it to Collapsed Subprocess
                        if signavio_shape_type in ['Task', 'CollapsedSubprocess'] and self.models_to_create[model_guid]['type'] == 'vc':
                            # convert shape to ProcesCollapsed
                            signavio_shape_type = "ProcessCollapsed"
                            outgoing_element = copy.deepcopy(model_shapes[shape_id].get('outgoing', []))
                            # default properties, meta-responsible, parent should stay other dictionary items should be at diagram level not in shape level
                            current_shape_properties = copy.deepcopy(self.__get_shape_properties(model_shapes[shape_id]))
                            curr_aris_symbol_type = copy.deepcopy(model_shapes.get(shape_id, {}).get('aris_symbol_type', ''))
                            self.create_shape(shape_id=shape_id, shape_type=signavio_shape_type,
                                              model_guid=model_guid, properties=current_shape_properties, aris_symbol_type=curr_aris_symbol_type)
                            model_shapes[shape_id]["outgoing"] = copy.deepcopy(outgoing_element)
                            model_shapes[shape_id]["properties"]["meta-arisguid"] = shape_def_guid

                        # Link Diagrams to Shapes
                        if signavio_shape_type in ['ProcessCollapsed', 'CollapsedSubprocess', 'Task']:
                            # remove name attribute and set title for ProcessCollapses
                            if signavio_shape_type == 'ProcessCollapsed':
                                titles = {
                                    ("title" + key[4:]) if key == "name" or key.startswith("name") else key: value
                                    for key, value in model_shapes[shape_id]["properties"].items()
                                }
                                if titles:
                                    other_attributes = {k: v for k, v in model_shapes[shape_id]["properties"].items() if not k.startswith("name")}
                                    model_shapes[shape_id]["properties"] = {**other_attributes, **titles}

                            # get linking diagrams of the current object def
                            # check diagram types if it is in diagram_types and not FAD
                            # then find a mapping from hierarchy_builder_models_created
                            # add the respective link to shape properties
                            linked_models = object_definition.get("linked_models", {})
                            model_keys = list(filter(lambda model_key: self.models[model_key]
                                                     ['type'] in list(self.diagram_types.keys()), linked_models))
                            if len(model_keys) > 0:
                                if signavio_shape_type == 'Task':
                                    # set linking diagram for Collapsed Subprocess
                                    self.set_diagrams_linked_by_shape(model_keys, model_guid, shape_id, is_collapsed_subprocess=False)
                                else:
                                    # set linking diagram for Collapsed Subprocess
                                    self.set_diagrams_linked_by_shape(model_keys, model_guid, shape_id, is_collapsed_subprocess=True)

                        # For Pool and Lane, do not set any connections
                        if signavio_shape_type not in ('Pool', 'Lane'):

                            # SET SHAPE CONNECTIONS
                            incoming_connections = shape.get("incoming_cxns", {})
                            outgoing_connections = shape.get("outgoing_cxns", {})

                            # Create Connections and Set its Predecessor/Outgoing Target Elements
                            if incoming_connections:
                                for cxn in incoming_connections:
                                    for incoming in incoming_connections[cxn]:
                                        cxn_def_key = incoming.get('cxn_def_id', '')
                                        connection_occ_id = incoming.get('cxn_occ_id', '')
                                        connection = self.connections.get(cxn_def_key)
                                        if not connection_occ_id:
                                            continue

                                        connection_type = connection.get("type", "")
                                        connected_from = cxn

                                        shape_key_exists = self.is_keyword_in_list(
                                            connection_type, list(self.shape_mapping.keys()))
                                        connected_obj_shape_key_exists = True
                                        if shape_key_exists:
                                            cxn_signavio_shape_type = self.shape_mapping[shape_key_exists]
                                            if isinstance(cxn_signavio_shape_type, dict):
                                                cxn_signavio_shape_type = cxn_signavio_shape_type[self.models_to_create[model_guid]["type"]]

                                            # check connected objects shape type, if it is also in shape mapping then create connection
                                            connected_object_symbol = shape_occurences.get(connected_from, {}).get('symbol', '')
                                            connected_object_derived_symbol = shape_occurences.get(
                                                connected_from, {}).get('derived_symbol', '')
                                            connected_obj_shape_key_exists = self.is_keyword_in_list(
                                                connected_object_symbol, self.shape_mapping.keys())
                                            connected_obj_shape_key_exists_derived_symbol = self.is_keyword_in_list(
                                                connected_object_derived_symbol, list(self.shape_mapping.keys()))
                                            if not connected_obj_shape_key_exists and connected_obj_shape_key_exists_derived_symbol:
                                                connected_obj_shape_key_exists = connected_obj_shape_key_exists_derived_symbol

                                            if connected_obj_shape_key_exists and connection_occ_id not in model_shapes:

                                                # set attributes of connection
                                                cxn_attributes = self.attribute_handler.get_attributes_of_connection(
                                                    cxn_def_key, cxn_signavio_shape_type)
                                                # set from elements of connections
                                                if not isinstance(connected_from, list):
                                                    connected_from = [connected_from]
                                                self.create_shape(shape_id=connection_occ_id, shape_type=cxn_signavio_shape_type,
                                                                  model_guid=model_guid, aris_symbol_type=connection_type, properties=cxn_attributes, predecessors=connected_from)

                                                model_shapes[connection_occ_id]["outgoing"] = copy.deepcopy([{"resourceId": shape_id}])
                                                model_shapes[connection_occ_id]["properties"]["meta-arisguid"] = connection_occ_id
                                                # target should be set for SequenceFlow and ProcessLink
                                                model_shapes[connection_occ_id]["target"]["resourceId"] = copy.deepcopy(shape_id)

                                        if not shape_key_exists or not connected_obj_shape_key_exists:
                                            # check responsible
                                            shape_key_exists = self.is_keyword_in_list(
                                                connection_type, self.connection_type_for_responsible)
                                            # if not shape_key_exists:
                                            #    logger.warning('Incoming Connection (CXN) mapping does not exist in shape mapping config for responsible' + str(connection_type))
                                            if shape_key_exists:
                                                obj_att_mapping = self.attribute_mapping_based_on_connection_type.get(shape_key_exists, {})
                                                connected_object_symbol = shape_occurences.get(connected_from, {}).get('symbol', '')
                                                shape_key_exists = self.is_keyword_in_list(
                                                    connected_object_symbol, obj_att_mapping.keys())
                                                if shape_key_exists:
                                                    attribute_mapping = obj_att_mapping.get(shape_key_exists, '')
                                                    if isinstance(attribute_mapping, dict):
                                                        attribute_mapping = attribute_mapping.get('incoming', '')
                                                    if attribute_mapping == 'meta-responsible':
                                                        # set responsible
                                                        # put all responsibles into meta-responsible
                                                        parent = model_shapes.get(shape_id, {}).get('parent', '')
                                                        responsibles = model_shapes.get(shape_id, {}).get(
                                                            'properties', {}).get('meta-responsible', [])
                                                        diagram_responsibles = model_shapes.get(shape_id, {}).get(
                                                            'properties', {}).get('meta-diagramresponsible', [])

                                                        shape_obj_def = shape_occurences.get(connected_from, {}).get('def', '')
                                                        # get guid of object definition
                                                        guid_of_dict = self.obj_definitions.get(shape_obj_def, {}).get('guid', '')
                                                        # get dictionary item
                                                        data_exists, dict_href = self.dictionary_items_file_tracker.is_task_done(
                                                            id=guid_of_dict)
                                                        if dict_href:
                                                            dict_href = dict_href.get('signavio_id', '')
                                                            if not diagram_responsibles:
                                                                model_shapes[shape_id]['properties']['meta-diagramresponsible'] = []
                                                            if dict_href and dict_href not in diagram_responsibles:
                                                                model_shapes[
                                                                    shape_id]['properties']['meta-diagramresponsible'].append(dict_href)
                                                        if parent != '' and connected_from not in parent:
                                                            if dict_href not in responsibles and dict_href:
                                                                if not model_shapes[shape_id]['properties'].get('meta-responsible', []):
                                                                    model_shapes[shape_id]['properties']['meta-responsible'] = []
                                                                model_shapes[shape_id]['properties']['meta-responsible'].append(
                                                                    dict_href)
                                                            shape_name = model_shapes[shape_id].get(
                                                                'properties', {}).get('name', '')

                                                            model_link = copy.deepcopy(self.__get_signavio_model_id(
                                                                model_guid, model_guid, shape_id))
                                                            if model_link and model_link.startswith('/model/'):
                                                                model_link = model_link.split('/model/')[1]
                                                            logger.info(
                                                                f"Multiple Responsibles exist for shape {shape_id} with name {shape_name}. Diagram ID: {model_guid} Diagram link: https://editor.signavio.com/p/editor?id={model_link} Responsibles : {model_shapes[shape_id]['properties'].get('meta-responsible', '')}")
                                                        elif parent == '' and dict_href and original_model_type not in self.aris_bpmn_diagram_types:
                                                            model_shapes[shape_id]['properties']['meta-responsible'] = [dict_href]
                                                            parent_def_id = shape_occurences.get(connected_from).get('def', '')
                                                            parent_guid = self.obj_definitions.get(parent_def_id, {}).get('guid', '')
                                                            model_shapes[shape_id]["parent"] = copy.deepcopy(
                                                                parent_guid)  # connected_from

                                            # Check dictionary items that should be attached from model to task
                                            # dictionary items are defined in config in self.dictionary_items_that_should_be_attached_from_model
                                            if signavio_shape_type == 'Task':
                                                self.__add_dictionary_items_from_model(
                                                    model_guid, shape_id, shape_occurences, connected_from, connection_type, 'incoming')

                                        if connection_occ_id and connection_occ_id in model_shapes and (connection_occ_id not in model_shapes[shape_id]["predecessor"]):
                                            model_shapes[shape_id]["predecessor"].append(connection_occ_id)

                            if outgoing_connections:
                                for cxn in outgoing_connections:
                                    for outgoing in outgoing_connections[cxn]:
                                        cxn_def_key = outgoing.get('cxn_def_id', '')
                                        connection_occ_id = outgoing.get('cxn_occ_id', '')
                                        connection = self.connections.get(cxn_def_key)
                                        connected_obj_shape_key_exists = True

                                        if not connection_occ_id:
                                            continue

                                        connection_type = connection.get("type", "")
                                        connected_to = copy.deepcopy(cxn)
                                        shape_key_exists = self.is_keyword_in_list(
                                            connection_type, list(self.shape_mapping.keys()))
                                        if shape_key_exists:
                                            cxn_signavio_shape_type = self.shape_mapping[shape_key_exists]
                                            if isinstance(cxn_signavio_shape_type, dict):
                                                cxn_signavio_shape_type = cxn_signavio_shape_type[self.models_to_create[model_guid]["type"]]

                                            # check whether connected_to object is also in shape mapping, if it is then create a connection
                                            connected_object_symbol = shape_occurences.get(connected_to, {}).get('symbol', '')
                                            connected_object_derived_symbol = shape_occurences.get(connected_to, {}).get('derived_symbol', '')
                                            connected_obj_shape_key_exists = self.is_keyword_in_list(
                                                connected_object_symbol, self.shape_mapping.keys())
                                            connected_obj_shape_key_exists_derived_symbol = self.is_keyword_in_list(
                                                connected_object_derived_symbol, list(self.shape_mapping.keys()))
                                            if not connected_obj_shape_key_exists and connected_obj_shape_key_exists_derived_symbol:
                                                connected_obj_shape_key_exists = connected_obj_shape_key_exists_derived_symbol

                                            if connected_obj_shape_key_exists and connection_occ_id not in model_shapes:

                                                # set attributes of connection
                                                cxn_attributes = self.attribute_handler.get_attributes_of_connection(
                                                    cxn_def_key, cxn_signavio_shape_type)
                                                self.create_shape(shape_id=connection_occ_id, shape_type=cxn_signavio_shape_type,
                                                                  model_guid=model_guid, aris_symbol_type=connection_type, properties=cxn_attributes, predecessors=[copy.deepcopy(shape_id)])

                                                model_shapes[connection_occ_id]["outgoing"] = copy.deepcopy([
                                                    {"resourceId": connected_to}])
                                                model_shapes[connection_occ_id]["properties"]["meta-arisguid"] = connection_occ_id
                                                # target should be set for SequenceFlow and ProcessLink
                                                model_shapes[connection_occ_id]["target"]["resourceId"] = copy.deepcopy(
                                                    connected_to)

                                        if not shape_key_exists or not connected_obj_shape_key_exists:
                                            # check responsible for a shape
                                            shape_key_exists = self.is_keyword_in_list(
                                                connection_type, self.connection_type_for_responsible)
                                            if shape_key_exists:
                                                obj_att_mapping = self.attribute_mapping_based_on_connection_type.get(shape_key_exists, {})
                                                connected_object_symbol = shape_occurences.get(connected_to, {}).get('symbol', '')
                                                shape_key_exists = self.is_keyword_in_list(
                                                    connected_object_symbol, obj_att_mapping.keys())
                                                if shape_key_exists:
                                                    attribute_mapping = obj_att_mapping.get(shape_key_exists, '')
                                                    if isinstance(attribute_mapping, dict):
                                                        attribute_mapping = attribute_mapping.get('outgoing', '')
                                                    if attribute_mapping == 'meta-responsible':
                                                        # set responsible
                                                        # put all responsibles into meta-responsible
                                                        parent = model_shapes.get(
                                                            shape_id, {}).get('parent', '')
                                                        responsibles = model_shapes.get(
                                                            shape_id, {}).get('properties', {}).get('meta-responsible', [])
                                                        diagram_responsibles = model_shapes.get(
                                                            shape_id, {}).get('properties', {}).get('meta-diagramresponsible', [])

                                                        shape_obj_def = shape_occurences.get(connected_to, {}).get('def', '')
                                                        # get guid of object definition
                                                        guid_of_dict = self.obj_definitions.get(shape_obj_def, {}).get('guid', '')
                                                        # get dictionary item
                                                        data_exists, dict_href = self.dictionary_items_file_tracker.is_task_done(
                                                            id=guid_of_dict)
                                                        if data_exists:
                                                            dict_href = dict_href.get('signavio_id', '')
                                                            if not diagram_responsibles:
                                                                model_shapes[shape_id]['properties']['meta-diagramresponsible'] = []
                                                            if dict_href and dict_href not in diagram_responsibles:
                                                                model_shapes[shape_id]['properties']['meta-diagramresponsible'].append(
                                                                    dict_href)
                                                        if parent != '' and connected_to not in parent:
                                                            if dict_href not in responsibles and dict_href:
                                                                if not model_shapes[shape_id]['properties'].get('meta-responsible', []):
                                                                    model_shapes[shape_id]['properties']['meta-responsible'] = []
                                                                model_shapes[shape_id]['properties']['meta-responsible'].append(dict_href)
                                                            shape_name = model_shapes[shape_id].get('properties', {}).get('name', '')

                                                            model_link = copy.deepcopy(self.__get_signavio_model_id(
                                                                model_guid, model_guid, shape_id))
                                                            if model_link is not None and '/model/' in model_link:
                                                                model_link = model_link.split('/model/')[1]
                                                            logger.info(
                                                                f"Multiple Responsibles exist for shape {shape_id} with name {shape_name}. Diagram ID: {model_guid} Diagram link: https://editor.signavio.com/p/editor?id={model_link} Responsibles : {model_shapes[shape_id]['properties']['meta-responsible']}")
                                                        elif parent == '' and dict_href and original_model_type not in self.aris_bpmn_diagram_types:
                                                            model_shapes[shape_id]['properties']['meta-responsible'] = [dict_href]
                                                            parent_def_id = shape_occurences.get(connected_to).get('def', '')
                                                            parent_guid = self.obj_definitions.get(parent_def_id, {}).get('guid', '')
                                                            model_shapes[shape_id]["parent"] = copy.deepcopy(
                                                                parent_guid)

                                            # else:
                                            #    logger.info('Outgoing Connection (CXN) mapping does not exist in shape mapping config ' + str(connection_type))

                                            # Check dictionary items that should be attached from model to task
                                            # dictionary items are defined in config in self.dictionary_items_that_should_be_attached_from_model
                                            if signavio_shape_type == 'Task':
                                                self.__add_dictionary_items_from_model(
                                                    model_guid, shape_id, shape_occurences, connected_to, connection_type, 'outgoing')

                                        # add connection as an outgoing element for current shape
                                        if connection_occ_id and connection_occ_id in model_shapes and ({"resourceId": copy.deepcopy(connection_occ_id)} not in model_shapes[shape_id]["outgoing"]):
                                            model_shapes[shape_id]["outgoing"].append({"resourceId": copy.deepcopy(connection_occ_id)})

                        # check attribute formatting for shapes
                        shape_properties = self.__get_shape_properties(model_shapes[shape_id])
                        for property_name in shape_properties:
                            shape_properties.update(self.attribute_handler.get_property_in_correct_format(
                                property_name, attribute_value=shape_properties[property_name], stencil=model_shapes[shape_id]['stencil']['id']))

                        model_shapes[shape_id]["properties"].update(copy.deepcopy(shape_properties))
                        # check attributes of Task from FAD
                        if signavio_shape_type == 'Task':
                            attributes_to_attach, lane_from_fad = self.get_dictionary_entries_attached_in_models(
                                shape_def_id, model_type='fad', flag_attach_loose_elements_to_task=self.flag_to_attach_loose_shapes_to_task_as_attributes)
                            formatted_attr = {}
                            for attr_name in attributes_to_attach:
                                '''if attr_name in self.shape_level_attributes_to_catchall:
                                    # check dictionary item glossary category name
                                    attribute_val = attributes_to_attach[attr_name]
                                    dict_hrefs = self.dictionary_items_file_tracker.dbu.retrieve_all_with_dynamic_filters(
                                        self.dictionary_items_file_tracker.stage_model, filters={'signavio_id': attribute_val})

                                    if dict_hrefs:
                                        for dict_href in dict_hrefs:
                                            if self.catch_all_attribute_name not in formatted_attr:
                                                formatted_attr[self.catch_all_attribute_name] = 'Linked Dictionary Items:' + '\n'
                                            formatted_attr[self.catch_all_attribute_name] = formatted_attr[self.catch_all_attribute_name] + \
                                                '\n' + dict_href.category_name + ' : ' + str(dict_href.signavio_id)
                                '''
                                # check attributes of task
                                attribute_val = model_shapes[shape_id]["properties"].get(attr_name, [])
                                # combine tasks current properties with attributes to attach
                                if len(attribute_val) != 0 and isinstance(attribute_val, list):
                                    for val in attribute_val:
                                        if val not in attributes_to_attach[attr_name]:
                                            attributes_to_attach[attr_name].append(val)
                                elif len(attribute_val) != 0 and not isinstance(attribute_val, list):
                                    if attribute_val != attributes_to_attach[attr_name]:
                                        logger.error(
                                            f'Model id: {model_guid} Task ID: {shape_id} FAD and model has different dictionary items attached for the same task attribute Attribute Name: {attr_name} accepts only one value. Will keep the attribute value in FAD. FAD Value:{attributes_to_attach[attr_name]} Attribute Value: {attribute_val}')
                                # check formatting
                                formatted_attr.update(self.attribute_handler.get_property_in_correct_format(
                                    attr_name, attribute_value=attributes_to_attach[attr_name], stencil='Task'))

                            if lane_from_fad != {}:
                                # create lane
                                lane_shape_guid = list(lane_from_fad.keys())[0]
                                if lane_shape_guid and lane_shape_guid not in model_shapes:
                                    model_shapes[lane_shape_guid] = copy.deepcopy(
                                        lane_from_fad.get(lane_shape_guid, {}))
                                    if model_shapes[shape_id]['parent'] == '':
                                        model_shapes[shape_id]['parent'] = copy.deepcopy(lane_shape_guid)
                                    else:
                                        logger.warning(
                                            f'Model {model_guid} shape {shape_id} has mutliple responsibles. Lane already exists from model. Lane creation from FAD is being ignored. Attached dictionary item to meta-responsible')
                                elif lane_shape_guid in model_shapes:
                                    if model_shapes[shape_id]['parent'] == '':
                                        model_shapes[shape_id]['parent'] = copy.deepcopy(lane_shape_guid)
                                    else:
                                        logger.warning(
                                            f'Model {model_guid} shape {shape_id} has mutliple responsibles. Lane already exists from model. Lane creation from FAD is being ignored. Attached dictionary item to meta-responsible')

                            # set dictionary items from data models to Task
                            if self.process_data_models:
                                dictionary_items_to_attach_from_data_model, lane_ignored = self.get_dictionary_entries_attached_in_models(
                                    shape_def_id, model_type='data_model')
                                # update shape properties
                                if dictionary_items_to_attach_from_data_model:
                                    self.attach_items_to_attributes(dictionary_items_to_attach_from_data_model,
                                                                    model_shapes[shape_id]["properties"])

                            # set dictionary items from matrix models
                            if self.process_matrix_models:
                                dictionary_items_from_matrix_model = self.task_def_to_dict_item_from_matrix_model.get(shape_def_id, {})
                                # Check Task Definition
                                # Attach diagram attributes from matrix model
                                if dictionary_items_from_matrix_model != {}:
                                    linked_models_for_task = dictionary_items_from_matrix_model.get('linked_models', [])
                                    dictionary_items = dictionary_items_from_matrix_model.get('dictionary_items', [])
                                    if dictionary_items:
                                        self.attach_items_to_attributes(
                                            dictionary_items, model_shapes[shape_id]["properties"])

                            model_shapes[shape_id]["properties"].update(copy.deepcopy(formatted_attr))

                        # if it is a value chain diagram and shape is processcollapsed
                        # if it doesnt have any linked diagrams
                        # check FAD attached to the object
                        if self.models_to_create[model_guid]['type'] == 'vc' and signavio_shape_type == 'ProcessCollapsed':
                            linked_models = object_definition.get("linked_models", {})
                            model_keys = list(filter(lambda model_key: self.models[model_key]
                                                     ['type'] in list(self.diagram_types.keys()), linked_models))
                            if len(model_keys) == 0:
                                sid_model_keys = list(filter(lambda model_key: self.models[model_key]['type'] in [
                                                      'MT_FUNC_ALLOC_DGM'], linked_models))
                                if len(sid_model_keys) > 0:
                                    logger.warning(
                                        f'VC diagram Model GUID: <{model_guid}> Shape ID: <{shape_id}> has SID: <{sid_model_keys}>  and shape doesnt have linked bpmn model ')

                        # Check whether Task has a linked model, which is different from the current model, if it is convert it to Collapsed Subprocess
                        if signavio_shape_type in ['Task'] and self.convert_tasks_to_collapsed_subprocess:
                            # if task is linking to a diagram, then convert it to Subprocess
                            linked_models = object_definition.get("linked_models", {})
                            model_keys = list(filter(lambda model_key: self.models[model_key]
                                                     ['type'] in list(self.diagram_types.keys()), linked_models))
                            if len(model_keys) > 0:
                                # convert shape to CollapsedSubprocess
                                # default properties, meta-responsible, parent should stay other dictionary items should be at diagram level not in shape level
                                outgoing_copy = copy.deepcopy(model_shapes[shape_id].get('outgoing', ''))
                                current_shape_properties = copy.deepcopy(self.__get_shape_properties(model_shapes[shape_id]))
                                curr_aris_symbol_type = copy.deepcopy(model_shapes.get(shape_id, {}).get('aris_symbol_type', ''))
                                cs_predecessors = copy.deepcopy(model_shapes.get(shape_id, {}).get('predecessor'))
                                self.create_shape(shape_id=shape_id, shape_type="CollapsedSubprocess",
                                                  properties=current_shape_properties, model_guid=model_guid, parent=model_shapes[shape_id].get('parent', ''), aris_symbol_type=curr_aris_symbol_type, predecessors=cs_predecessors)
                                model_shapes[shape_id]["outgoing"] = copy.deepcopy(outgoing_copy)
                                model_shapes[shape_id]["properties"]["meta-arisguid"] = shape_def_guid

                                # set linking diagram
                                self.set_diagrams_linked_by_shape(model_keys, model_guid, shape_id, is_collapsed_subprocess=True)
                                # remove from linking diagram entry
                                if self.linking_diagram_attr in model_shapes[shape_id]["properties"]:
                                    if model_shapes[shape_id]["properties"]["entry"] in model_shapes[shape_id]["properties"][self.linking_diagram_attr]:
                                        model_shapes[shape_id]["properties"][self.linking_diagram_attr].remove(
                                            model_shapes[shape_id]["properties"]["entry"])

                        # set service type for some task symbols for VF
                        if shape_aris_type in ['ST_BPMN_SERVICE_TASK']:
                            model_shapes[shape_id]['properties']["tasktype"] = "Service"

                        # if responsible does not exist set it to "Fallback_Lane"
                        # for VC set lane as linked
                        # if needed for VC unlinked lane can be used based on customer requirement
                        if self.models_to_create[model_guid]['type'] == 'bpmn' and model_shapes[shape_id]["parent"] == "":
                            model_shapes[shape_id]["parent"] = "Fallback_Lane"
                        elif self.models_to_create[model_guid]['type'] == 'vc' and model_shapes[shape_id]["parent"] == "":
                            successor = model_shapes[shape_id].get('outgoing', [])
                            predecessor = model_shapes[shape_id].get('predecessor', [])
                            if not successor and not predecessor:
                                model_shapes[shape_id]["parent"] = "unlinked"
                            else:
                                model_shapes[shape_id]["parent"] = "linked"

                        # Add formats for shapes
                        model_shapes[shape_id]["formats"] = {}
                        # get attributes to prepare formats
                        attributes_for_format = {}
                        for attribute_name in self.list_of_attributes_to_check_formatting:
                            attr_multilang = {k: v for k, v in model_shapes[shape_id]["properties"].items() if k.startswith(attribute_name)}
                            attributes_for_format = {**attributes_for_format, **attr_multilang}
                        if attributes_for_format:
                            # get styles for the attributes
                            attr_styles = self.obj_definitions.get(shape_def_id, {}).get('attrs', {}).get('styles', {})
                            signavio_format_for_shape = self.prepare_formats_for_attributes(attributes_for_format, attr_styles)
                            new_formats = copy.deepcopy(signavio_format_for_shape)
                            names = {k: v for k, v in signavio_format_for_shape.items() if k.startswith('name')}
                            if names:
                                for name_key in names:
                                    new_formats, new_label = self.remove_dict_with_key(signavio_format_for_shape[name_key], 'style')
                                    signavio_format_for_shape[name_key] = copy.deepcopy(new_formats)
                                    if new_label:
                                        color = new_label.get('style', {}).get('color', '')
                                        if color:
                                            model_shapes[shape_id]['labels'] = [
                                                {
                                                    "ref": "text_name",
                                                    "styles": {
                                                        "fill": copy.deepcopy(color)
                                                    }
                                                }
                                            ]
                            model_shapes[shape_id]["formats"].update(signavio_format_for_shape)
                    else:
                        logger.error(f'Shape config incomplete. Value for {self.shape_mapping[shape_key_exists]} is not defined')

                elif shape_aris_type not in list(self.shape_mapping.keys()):
                    # logger.error(f"Shape type {shape_aris_type} cannot be found in shape mapping and object mapping config ")
                    shape = shape_occurences[shape_key]
                    shape_id = shape.get("id", "")
                    shape_def_id = shape.get("def", "")
                    shape_def_guid = self.obj_definitions.get(shape_def_id, {}).get('guid', '')
                    shape_aris_type = shape.get("symbol", "")
                    shape_derived_symbol = shape.get("derived_symbol", "")
                    # check connections of the element, it is not connected to anything else
                    incoming_connections = shape.get("incoming_cxns", {})
                    outgoing_connections = shape.get("outgoing_cxns", {})
                    if not incoming_connections and not outgoing_connections:
                        # TODO Check other unconnected elements and attach it as diagram level attributes
                        if shape_aris_type in list(self.object_mapping.keys()) or shape_derived_symbol in list(self.object_mapping.keys()):
                            signavio_attr_for_model = {}
                            model_properties = self.models_to_create[model_guid]["properties"]
                            self.get_attributes_to_attach(shape_occurences, shape_id, signavio_attr_for_model, model_properties, '')

            if pool_counter == 0 and model_shapes != {} and self.models_to_create[model_guid]['type'] == 'bpmn':
                # get Dictionary Item for Pool
                data_exists, dictionary_item_id_for_pool = self.dictionary_items_file_tracker.is_task_done(id='GUID_Pool')
                if dictionary_item_id_for_pool:
                    dictionary_item_id_for_pool = dictionary_item_id_for_pool.get('signavio_id', '')
                self.create_shape(shape_id='Pool', shape_type='Pool', model_guid=model_guid, dictionary_item_href=dictionary_item_id_for_pool)
                # set a default pool for bpmn diagram
                model_shapes["Pool"]["properties"]["name"] = self.pool_name

            # check textdefinitions attach it to diagram notes field
            self.__collect_floating_texts_into_diagramnotes(diagram_model_key, model_guid)

            # Add formats
            self.models_to_create[model_guid]["formats"] = {}
            # get attributes to prepare formats
            # description, documentation
            attributes_for_format = {}
            for attribute_name in self.list_of_attributes_to_check_formatting:
                # check attributes starting with attribute_name ( to support multilang )
                attr_multilang = {k: v for k, v in self.models_to_create[model_guid]["properties"].items() if k.startswith(attribute_name)}
                attributes_for_format = {**attributes_for_format, **attr_multilang}
            if attributes_for_format:
                attr_styles = self.models.get(model_key, {}).get("attrs", {}).get('styles', {})
                signavio_format_for_model = self.prepare_formats_for_attributes(attributes_for_format, attr_styles)
                self.models_to_create[model_guid]["formats"].update(signavio_format_for_model)

            # Different symbol for collapsed pools
            if pool_counter > 1:
                logger.warning(f'Model ID: {model_guid} Multiple pools exist for model ')

    def __add_dictionary_items_from_model(self, model_guid, shape_id, shape_occurences, connected_obj, connection_type, incoming_or_outgoing: str):
        # Check dictionary items that should be attached from model to task
        # dictionary items are defined in config in self.dictionary_items_that_should_be_attached_from_model
        shape_type_connected_to = shape_occurences.get(connected_obj, {}).get('symbol', '')
        shape_derived_type_connected_to = shape_occurences.get(connected_obj, {}).get('derived_symbol', '')
        signavio_attr_for_shape = {}
        # check first connection type of shape to decide correct attribute for dictionary
        shape_key_exists = self.is_keyword_in_list(connection_type, list(self.attribute_mapping_based_on_connection_type.keys()))
        if shape_key_exists in self.attribute_mapping_based_on_connection_type:
            signavio_attr_for_shape = self.attribute_mapping_based_on_connection_type.get(shape_key_exists, {})
        else:
            shape_key_exists = self.is_keyword_in_list(shape_type_connected_to, self.dictionary_items_that_should_be_attached_from_model)
            if shape_key_exists:
                signavio_attr_for_shape = {}
        if shape_key_exists:
            task_properties = self.models_to_create[model_guid]['shapes'][shape_id]["properties"]
            self.get_attributes_to_attach(shape_occurences, connected_obj, signavio_attr_for_shape, task_properties, incoming_or_outgoing)
            self.models_to_create[model_guid]['shapes'][shape_id]["properties"].update(copy.deepcopy(task_properties))

    def __get_shape_properties(self, shape):
        shape_properties = {key: value for key, value in
                            shape.get('properties', {}).items() if
                            key.startswith('name') or key.startswith('meta-') or key.startswith(
                                'documentation') or key.startswith(
                                'description') or key == 'entry' and key != 'namespace'}
        return shape_properties

    def __collect_floating_texts_into_diagramnotes(self, diagram_model_key, model_guid):
        # check textdefinitions attach it to diagram notes field
        txt_occs = self.models.get(diagram_model_key, {}).get('txt_occs', '')
        for txt_occ_key in txt_occs:
            txt_def = txt_occs.get(txt_occ_key).get('def_id', '')
            if txt_def:
                txt_def_obj = self.txt_definitions.get(txt_def)
                if txt_def_obj:
                    attribute_txt_obj_name = txt_def_obj.get('attrs', {}).get('AT_NAME', '')
                    if attribute_txt_obj_name:
                        for lang_key in attribute_txt_obj_name:
                            attribute_txt_obj_name_lang_value = attribute_txt_obj_name.get(lang_key, '')
                            if attribute_txt_obj_name_lang_value:
                                attribute_to_update = "meta-diagramnotes" + '_' + lang_key
                                current_val_comment = self.models_to_create[model_guid]["properties"].get(attribute_to_update, '')
                                if current_val_comment:
                                    self.models_to_create[model_guid]["properties"][attribute_to_update] = copy.deepcopy(
                                        current_val_comment) + "\n" + copy.deepcopy(attribute_txt_obj_name_lang_value)
                                else:
                                    self.models_to_create[model_guid]["properties"][attribute_to_update] = copy.deepcopy(
                                        attribute_txt_obj_name_lang_value)

    def get_dictionary_entries_attached(self, shape_occs, attributes_to_attach, filtered_shape_types):
        # check shape occs in fad
        # if shape has assigned models for library diagrams listed below
        # MT_BUSY_CONTR_DGM, MT_INFO_CARR_DGM, MT_ACS_DGM, MT_STRCT_DGM
        # get objects in these diagrams if they are part of shape mapping
        # return it and treat them as connected objects to Task
        for shape_occ_key in shape_occs:
            # check symbol
            shape_symbol = shape_occs.get(shape_occ_key).get('symbol', '')
            if shape_symbol in filtered_shape_types:
                self.get_attributes_to_attach(shape_occs, shape_occ_key, signavio_attr={}, attributes_to_attach=attributes_to_attach)

    def get_dictionary_entries_attached_in_models(self, object_def_id: str, model_type: str, flag_attach_loose_elements_to_task=False):
        # Linking dictionary items including RACI elements ( including responsibles)
        # return: attributes_to_attach : Dictionary object containing properties and respective values
        # For Function -> find definitions -> get attributes -> get assigned models and get the FAD from models

        attributes_to_attach = {}
        # get FAD from linked models of object definition

        if model_type == 'fad':
            model_keys = self.task_def_to_fad_mapping.get(object_def_id, {}).get('fad_model_id', '')  # There can be only FAD for function
        elif model_type == 'data_model':
            model_key = self.task_def_to_data_model_mapping.get(object_def_id, {}).get('data_model_id', '')
            model_keys = [model_key]

        responsible_lane = {}
        for model_key in model_keys:

            fad_for_task = self.models[model_key]
            shape_occs = fad_for_task.get('occs', {})
            # look for connections to current task
            connected_shape_occurences_to_task = []
            task_occurence_key_fad = list(filter(lambda shape_occ_id: shape_occs[shape_occ_id]['def'] == object_def_id, shape_occs))
            task_occurence_in_fad = {}
            if task_occurence_key_fad:
                task_occurence_key_fad = task_occurence_key_fad[0]
                task_occurence_in_fad = shape_occs.get(task_occurence_key_fad, {})
                # check incoming and outgoing cxns for task
                incoming_cxns = task_occurence_in_fad.get('incoming_cxns', {})
                outgoing_cxns = task_occurence_in_fad.get('outgoing_cxns', {})

                for connected_obj_occ_id in incoming_cxns:
                    if connected_obj_occ_id not in connected_shape_occurences_to_task:
                        connected_shape_occurences_to_task.append(connected_obj_occ_id)
                    signavio_attr = {}
                    for incoming in incoming_cxns[connected_obj_occ_id]:
                        cxn_def_id = incoming.get('cxn_def_id')
                        cxn_def = self.connections.get(cxn_def_id)
                        cxn_def_type = cxn_def.get('type', '')
                        result = self.is_keyword_in_list(cxn_def_type, list(self.attribute_mapping_based_on_connection_type.keys()))
                        if result in self.attribute_mapping_based_on_connection_type:
                            signavio_attr = self.attribute_mapping_based_on_connection_type.get(result, {})

                        # get object occurence's object definition
                        result_lane = self.get_attributes_to_attach(shape_occs, connected_obj_occ_id, signavio_attr, attributes_to_attach, 'incoming')
                        # check responsible/lane
                        if model_type == 'fad' and result_lane != {}:
                            lane_id = list(result_lane.keys())[0]
                            if lane_id not in responsible_lane:
                                responsible_lane[lane_id] = copy.deepcopy(result_lane[lane_id])

                # check outgoing connections
                for connected_obj_occ_id in outgoing_cxns:
                    signavio_attr = {}
                    for outgoing in outgoing_cxns[connected_obj_occ_id]:
                        cxn_def_id = outgoing.get('cxn_def_id')

                        if connected_obj_occ_id not in connected_shape_occurences_to_task:
                            connected_shape_occurences_to_task.append(connected_obj_occ_id)
                        # get definition and check type
                        # cxn_def = self.cxn_occurences.get(cxn_def_id, '')
                        cxn_def = self.connections.get(cxn_def_id)
                        cxn_def_type = cxn_def.get('type', '')
                        result = self.is_keyword_in_list(cxn_def_type, list(self.attribute_mapping_based_on_connection_type.keys()))
                        if result in self.attribute_mapping_based_on_connection_type:
                            signavio_attr = self.attribute_mapping_based_on_connection_type.get(result, {})

                        # get object occurence's object definition
                        result_lane = self.get_attributes_to_attach(shape_occs, connected_obj_occ_id, signavio_attr, attributes_to_attach, 'outgoing')
                        if model_type == 'fad' and result_lane != {}:
                            lane_id = list(result_lane.keys())[0]
                            if lane_id not in responsible_lane:
                                responsible_lane[lane_id] = copy.deepcopy(result_lane[lane_id])

            # check shapes not connected to task
            all_shape_occ_keys_in_fad = set(shape_occs.keys())
            difference = all_shape_occ_keys_in_fad - set(connected_shape_occurences_to_task)
            task_occ_symbol = ''
            # remove the task that FAD belongs from difference set
            if task_occurence_in_fad:
                task_occ_id = task_occurence_in_fad.get('id', '')
                task_occ_symbol = task_occurence_in_fad.get('symbol', '')
                if task_occ_id in difference:
                    difference.remove(task_occ_id)
            # check if other task elements exist
            multiple_tasks = []
            for shape_occ_key in difference:
                type_of_shape = shape_occs.get(shape_occ_key, '').get('symbol', '')
                if type_of_shape == task_occ_symbol:
                    multiple_tasks.append(shape_occ_key)

            difference.difference_update(multiple_tasks)
            if len(multiple_tasks) > 0:
                logger.warning(f'Multiple Tasks exist in FAD. Task IDs: {multiple_tasks}')
            if len(difference) > 0:
                logger.warning(f'Unconnected elements/Second level connected elements available in FAD. Shapes IDs: {difference}')

            if model_type == 'fad' and flag_attach_loose_elements_to_task:
                # get object occurence's object definition
                for shape_occ_key in difference:
                    result_lane = self.get_attributes_to_attach(shape_occs, shape_occ_key, signavio_attr={},
                                                                attributes_to_attach=attributes_to_attach)
                    if result_lane != {}:
                        lane_id = list(result_lane.keys())[0]
                        if lane_id not in responsible_lane:
                            responsible_lane[lane_id] = copy.deepcopy(result_lane[lane_id])

            # check assigned models in FAD
            if self.check_assigned_models_in_FAD:
                if not task_occurence_key_fad:
                    task_occurence_key_fad = ''
                self.check_assigned_models_to_shape_in_fad(shape_occs, attributes_to_attach, task_occurence_key_fad)

        lane = {}
        if model_type == 'fad':
            if len(list(responsible_lane.keys())) > 1:
                logger.warning(
                    f'Multiple responsibles exist in FAD. FAD Model ID: {model_key}. Task Object Def ID: {object_def_id}. Setting first one in the list as responsible')
            if len(list(responsible_lane.keys())) > 0:
                lane_id = list(responsible_lane.keys())[0]
                if lane_id:
                    lane[lane_id] = responsible_lane.get(lane_id, {})

        return attributes_to_attach, lane

    def get_attributes_to_attach(self, shape_occs_for_model: dict, shape_occ_key: str, signavio_attr: dict, attributes_to_attach: dict, direction=''):
        # shape_occs_for_model : shape occurences in FAD diagram
        # shape_occ_key : occurence key of dictionary item that should be attached
        # attributes_to_attach: JSON that holds attributes for the task in FAD
        # To set dictionary entries as attributes for shapes
        # updates the attributes_to_attach argument, add new attributes, attribute value would be always list
        shape_obj_occ = shape_occs_for_model.get(shape_occ_key, {})
        shape_obj_def = shape_obj_occ.get('def', '')
        lane = {}
        shape_obj_symbol = shape_obj_occ.get('symbol', '')
        shape_obj_derived_symbol = shape_obj_occ.get('derived_symbol', '')
        # get guid of object definition
        guid_of_dict = self.obj_definitions.get(shape_obj_def, {}).get('guid', '')
        if signavio_attr != {} and (shape_obj_symbol not in signavio_attr.keys() and shape_obj_derived_symbol not in signavio_attr.keys()):
            signavio_attr = ''
        elif signavio_attr != {} and shape_obj_symbol in signavio_attr.keys():
            signavio_attr = signavio_attr.get(shape_obj_symbol, '')
            if isinstance(signavio_attr, dict):
                signavio_attr = signavio_attr.get(direction, '')
        elif signavio_attr != {} and shape_obj_derived_symbol in signavio_attr.keys():
            signavio_attr = signavio_attr.get(shape_obj_derived_symbol, '')
            if isinstance(signavio_attr, dict):
                signavio_attr = signavio_attr.get(direction, '')

        if len(signavio_attr) == 0:
            # read signavio attribute from object_mapping
            shape_key_exists = self.is_keyword_in_list(shape_obj_symbol, list(self.object_mapping.keys()))
            if shape_key_exists:
                signavio_attr = self.object_mapping.get(shape_key_exists, {}).get('transform_attribute', '')
            else:
                # check derived symbol
                shape_key_exists = self.is_keyword_in_list(shape_obj_derived_symbol, list(self.object_mapping.keys()))
                if shape_key_exists:
                    signavio_attr = self.object_mapping.get(shape_key_exists, {}).get('transform_attribute', '')

        if signavio_attr:
            data_exists, dictionary_item_to_attach = self.dictionary_items_file_tracker.is_task_done(
                id=guid_of_dict)
            if dictionary_item_to_attach:
                dictionary_item_to_attach = dictionary_item_to_attach.get('signavio_id', '')
            attr_val = dictionary_item_to_attach
            if attr_val:
                new_dict = {signavio_attr: [attr_val]}
                self.attach_items_to_attributes(new_dict, attributes_to_attach)
            elif not attr_val:
                logger.error(f'Dictionary item : {guid_of_dict} is not available in Dictionary Items')

            if signavio_attr == 'meta-responsible' and dictionary_item_to_attach:
                # create lane
                lane[guid_of_dict] = {}
                lane[guid_of_dict] = self.create_shape(shape_id=guid_of_dict, shape_type='Lane', def_id=shape_obj_def,
                                                       aris_symbol_type=shape_obj_symbol, parent="Fallback_Lane", dictionary_item_href=dictionary_item_to_attach)
                lane[guid_of_dict]["properties"]["meta-arisguid"] = guid_of_dict

        return lane

    def search_and_create_dict_item(self, attr, attr_val_to_check, sig_model_attr_name, model_guid, category_to_check_dict_item, model_attrs_to_attach):
        if isinstance(attr_val_to_check, dict):
            attr_val_to_check = attr_val_to_check.get("en_us", "")
        data_exists, dict_value = self.dictionary_items_file_tracker.is_task_done(id=attr_val_to_check)
        if dict_value:
            if not isinstance(dict_value, list):
                dict_value = dict_value.get('signavio_id', '')
            elif isinstance(dict_value, list) and len(dict_value) >= 1:
                dict_value = dict_value[0].get('signavio_id', '')
                if len(dict_value) > 1:
                    logger.error(
                        f'Link model attribute to dict. Multiple values exist to link attribute to dictionary item. Values: {dict_value}. Mapping first item in the list: {dict_value[0]}')

        if not dict_value:
            # Create new entry
            # create new item
            
            attr_val_to_check = attr_val_to_check.replace("/", "_").replace("\\", "_").replace("\n", "_").replace("( &amp;", "_")
            aris_id = attr_val_to_check
            if attr in self.create_dictionary_entry_from_attribute.keys():
                name = self.create_dictionary_entry_from_attribute.get(attr, {}).get(attr_val_to_check, {}).get('name', '')
                meta_data_values = get_meta_data_values({}, aris_id)  # set aris id as the items attr_val to search for
            else:
                if isinstance(aris_id, dict):
                    aris_id = aris_id["en_us"].lower()
                else:
                    aris_id = aris_id.lower()
                meta_data_values = get_meta_data_values({"meta-emailaddress": aris_id}, aris_id)
                name = aris_id

            data = {
                'force': True,
                'title': name,
                'category': category_to_check_dict_item,
                'description': 'Created in Migration',
                'attachments': '',
                'metaDataValues': str(meta_data_values),
                'comment': 'Created in Migration'
            }
            if attr_val_to_check == 'Sundar, Raksha  -  Anandham, Vinoth':
                print()
            result, signavio_id = self.dictionary_handler.create_new_entry(data, aris_id, attr_val_to_check)
            if result is True:
                if signavio_id and isinstance(signavio_id, str) and '/glossary/' in signavio_id:
                    dict_value = signavio_id
                else:
                    data_exists, dict_value = self.dictionary_items_file_tracker.is_task_done(id=attr_val_to_check)
                    logger.success(
                        f'Model ID: {model_guid}. Created new dictionary entry from model attribute: {attr_val_to_check} in category {category_to_check_dict_item} for attribute {sig_model_attr_name} from ARIS attribute {attr}')
                    if dict_value:
                        if not isinstance(dict_value, list):
                            dict_value = dict_value.get('signavio_id', '')
                        elif isinstance(dict_value, list) and len(dict_value) >= 1:
                            dict_value = dict_value[0].get('signavio_id', '')
                            if len(dict_value) > 1:
                                logger.error(
                                    f'Link model attribute to dict. Multiple values exist to link attribute to dictionary item. Values: {dict_value}. Mapping first item in the list: {dict_value[0]}')
            else:
                logger.error(
                    f'Couldnt create dictionary item from model attribute for Model: {model_guid}. attribute: {sig_model_attr_name} value: {attr_val_to_check}  category:  {category_to_check_dict_item}  ARIS attribute {attr}')
        if dict_value:
            current_val = model_attrs_to_attach.get(sig_model_attr_name, '')
            if dict_value not in current_val:
                self.add_attribute_value(model_attrs_to_attach, sig_model_attr_name, dict_value)

    def add_attribute_value(self, attributes, key_to_check, new_value):
        # result is always list for attributes
        if key_to_check not in attributes:
            attributes[key_to_check] = []
        attributes[key_to_check] = self.merge_items(attributes[key_to_check], new_value)

    def set_diagrams_linked_by_shape(self, model_keys, model_guid, shape_id, is_collapsed_subprocess: bool):
        # This function sets diagrams linked by collapsed subprocess if is_collapsed_subprocess set to true
        # If it has more than one linking diagram it will use the first item in the list as linked diagram
        # and it will set other linking diagrams in a custom attribute which is defined in self.linking_diagram_attr
        # For tasks it will put all linking diagrams into custom attribute
        # get first model to link it
        model_keys = copy.deepcopy(model_keys)
        model_def_id_to_link = model_keys[0]
        # get guid of the model
        model_guid_to_link = self.models.get(model_def_id_to_link, {}).get('guid', "")
        signavio_model_id = ''
        model_shapes = self.models_to_create[model_guid]["shapes"]
        if model_guid_to_link == '':
            logger.error(
                f"Model ID: {model_guid}, Shape ID {shape_id}, Diagram Def ID: {model_keys[0]} . Diagram linked by shape doesn't exist in xml file")
        else:
            signavio_model_id = copy.deepcopy(self.__get_signavio_model_id(model_guid_to_link, model_guid, shape_id))

            if is_collapsed_subprocess and signavio_model_id.startswith('/model/') and model_shapes[shape_id]["properties"].get('entry', '') == '':
                model_shapes[shape_id]["properties"]["entry"] = copy.deepcopy(signavio_model_id)
            elif not is_collapsed_subprocess and signavio_model_id.startswith('/model/'):
                if self.linking_diagram_attr in model_shapes[shape_id]["properties"]:
                    if signavio_model_id not in model_shapes[shape_id]["properties"][self.linking_diagram_attr]:
                        model_shapes[shape_id]["properties"][self.linking_diagram_attr].append(signavio_model_id)
                else:
                    model_shapes[shape_id]["properties"][self.linking_diagram_attr] = [copy.deepcopy(signavio_model_id)]

        # set other linking diagrams as an attribute
        if len(model_keys) > 1:
            # remove first element
            if signavio_model_id.startswith('/model/'):
                model_keys.remove(model_def_id_to_link)
            linked_model_signavio_links = set()
            for model_def_id in model_keys:
                linked_model_guid = self.models.get(model_def_id).get('guid', '')
                if linked_model_guid == '':
                    logger.error(
                        f"Model ID: {model_guid}, Shape ID {shape_id}. {model_shapes[shape_id]['aris_symbol_type']} has linked models. Linked Diagram {model_def_id} doesn't exist in xml ")
                elif linked_model_guid not in linked_model_signavio_links:
                    signavio_model_id = copy.deepcopy(self.__get_signavio_model_id(linked_model_guid, model_guid, shape_id))

                if signavio_model_id.startswith('/model/'):
                    linked_model_signavio_links.add(signavio_model_id)

            if self.linking_diagram_attr in model_shapes[shape_id]["properties"]:
                linked_model_signavio_links.update(model_shapes[shape_id]["properties"][self.linking_diagram_attr])

            model_shapes[shape_id]["properties"][self.linking_diagram_attr] = list(linked_model_signavio_links)

    def __get_signavio_model_id(self, model_guid_to_link: str, parent_guid: str,
                                shape_id: str) -> Optional[str]:
        """Get Signavio model ID from file tracker."""
        exists, data = self.model_file_tracker.is_task_done(id=model_guid_to_link)
        if not exists:
            logger.error(f"Model ID: {parent_guid}, Shape ID {shape_id}, Diagram Link: {model_guid_to_link},  "
                         f" Diagram linked by shape doesn't exist in database. ")
            return ''
        return data.get('signavio_id', '')

    def check_assigned_models_to_shape_in_fad(self, shape_occs_in_fad, attributes_to_attach, task_occurence_key_fad):
        # check shape occs in fad
        # if shape has assigned models for library diagrams listed below
        # MT_BUSY_CONTR_DGM, MT_INFO_CARR_DGM, MT_ACS_DGM, MT_STRCT_DGM
        # get objects in these diagrams if they are part of shape mapping
        # return it and treat them as connected objects to Task

        for shape_occ_id in shape_occs_in_fad:
            # check whether objects have assignments to library diagrams
            if shape_occ_id == task_occurence_key_fad:  # skip task itself
                continue
            object_def_id = shape_occs_in_fad[shape_occ_id].get('def', '')
            obj_def = self.obj_definitions.get(object_def_id, {})
            assigned_models_to_object_def = obj_def.get('linked_models', [])
            # 'MT_APPL_SYS_TYPE_DGM' ( System Diagram) , 'MT_STRCT_DGM' ( Library) ,  'MT_ACS_DGM_PHYS' ( Interfaces)
            models_to_check_shapes = list(
                filter(lambda assigned_model_id: self.models[assigned_model_id]['type'] in self.models_types_in_fad, assigned_models_to_object_def))
            if models_to_check_shapes:
                # get shapes in library diagrams
                for model_id in models_to_check_shapes:
                    shape_occs_in_library_diagram = self.models[model_id].get('occs', [])
                    for shape_occ_key in shape_occs_in_library_diagram:
                        # check symbol
                        shape_symbol = shape_occs_in_library_diagram.get(shape_occ_key).get('symbol', '')
                        if shape_symbol in self.object_mapping:
                            self.get_attributes_to_attach(shape_occs_in_library_diagram, shape_occ_key,
                                                          signavio_attr={}, attributes_to_attach=attributes_to_attach)

    def extract_emails(self, text: str) -> list:
        """
        Extract all email addresses from the given text.
        """
        # Regular expression pattern for matching email addresses
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        # Find all matches in the text
        emails = re.findall(email_pattern, text)
        return emails

    def _get_signavio_shape_type(self, shape: dict, mapping_list: list) -> str:
        """
        Get the Signavio shape type for a given shape.
        """
        shape_aris_type = shape.get("symbol", "")
        shape_derived_symbol = shape.get("derived_symbol", "")

        # Check main symbol first
        shape_key = self.is_keyword_in_list(shape_aris_type, mapping_list)

        # If not found, check derived symbol
        if not shape_key and shape_derived_symbol:
            shape_key = self.is_keyword_in_list(shape_derived_symbol, mapping_list)

        return mapping_list.get(shape_key, "") if shape_key else ""

    def is_keyword_in_list(self, txt_shape: str, shape_mapping_list: list):
        """
        Returns the first string in shape_mapping_list that is a substring of txt_shape, or False if none found.
        """
        # list contains elements with the substring
        # txt_shape includes the search keyword
        for string in shape_mapping_list:
            if string in txt_shape:
                return string
        return False

    def prepare_formats_for_attributes(self, attribute_dict, attribute_styles):
        formats = {}

        for attribute_name in attribute_dict:
            # get style for the attribute name
            attr_text = ''
            if attribute_styles.get(attribute_name):
                attr_text = attribute_styles.get(attribute_name)
                # check language suffix
                if '_' in attribute_name:
                    lang_suffix = attribute_name.split('_', 1)[1]
                    attr_text = attr_text.get(lang_suffix, '')
                else:
                    lang_suffix = self.attribute_handler.default_workspace_language
                    attr_text = attr_text.get(lang_suffix, '')
            if not attr_text:
                attr_text = attribute_dict[attribute_name]
            format = self.prepare_signavio_format_for_model(attr_text)
            if format:
                formats.update({attribute_name: copy.deepcopy(format)})
        return formats

    def prepare_signavio_format_for_model(self, text):
        positions = []
        allowed_tags = {'br', 'b', 'i', 'u', 'ol', 'li', 'ul', 'font'}
        tag_names_without_closing_tag = ["br", "hr"]

        # replace characters that are not part of ASCII, Extended ASCII, Latin Extended A-Unicode Characters, as empty string
        non_printable_pattern = re.compile(r'[^\x20-\x7E\xA0-\xFF\u0100-\u017F\n\r]')
        text = non_printable_pattern.sub('', text)

        # Replace newline characters between </li> and <li> with nothing
        cleaned_text = re.sub(r'</li>\s*\n\s*<li>', '</li><li>', text)
        cleaned_text = re.sub(r'</ul>\s*\n\s*<ul>', '</ul><ul>', cleaned_text)

        clean_text = cleaned_text.replace('\u00a0', ' ').replace('&quot;', '\"').replace('"', '\"').replace('\r\n',
                                                                                                            '\n').replace('\n', '')
        # Build regex pattern for the tags
        pattern = r'</?(' + '|'.join(allowed_tags) + r')[^>]*>'
        # Remove tags
        cleaned_text_for_new_line = cleaned_text.replace('\u00a0', ' ').replace('&quot;', '\"').replace('"', '\"').replace('\r\n', '\n')
        cleaned_text_for_new_line = re.sub(pattern, '', cleaned_text_for_new_line)

        html_tags = re.findall(r'<[^>]+>', clean_text)

        if html_tags:
            stack = []

            index_counter = 0
            while index_counter < len(html_tags):
                tag = html_tags[index_counter]
                # if tag == 'font':
                #    print()
                formatted_tag = {}
                tag_index = clean_text.find(tag)
                clean_text = clean_text.replace(tag, "", 1)
                tag_name = tag.replace('</', '').replace('<', '').replace('>', '')
                if tag_name in tag_names_without_closing_tag:
                    formatted_tag = {'from': tag_index, 'tag': tag_name, 'to': tag_index}
                    positions.append(formatted_tag)
                # if it is a start tag
                elif not tag.startswith('</'):
                    # check next tag
                    if index_counter + 1 < len(html_tags):
                        next_tag = html_tags[index_counter + 1]
                        next_tag_name = next_tag.replace('</', '').replace('<', '').replace('>', '')

                        if next_tag.startswith('</') and tag_name == next_tag_name:
                            tag_index_closing = clean_text.find(next_tag)
                            clean_text = clean_text.replace(next_tag, "", 1)
                            if 'font' in next_tag:
                                color = next_tag.split('color=')
                                if color:
                                    color = '#' + color[1].replace('>', '')
                                    formatted_tag = {'from': tag_index, 'tag': 'font', "style": {"color": color},
                                                     'to': tag_index_closing}
                            else:
                                formatted_tag = {'from': tag_index, 'tag': tag_name,
                                                 'to': tag_index_closing}
                            positions.append(copy.deepcopy(formatted_tag))
                            index_counter += 1

                        # next tag is start tag
                        elif not next_tag.startswith('</'):
                            # put current tag to stack
                            formatted_tag = {'from': tag_index, 'tag': tag_name}
                            stack.append(formatted_tag)

                else:  # if it is a closing tag
                    if len(stack) > 0:
                        last_element = stack.pop()
                        if last_element.get('tag') == tag_name:
                            if 'font' in tag_name:
                                color = tag_name.split('color=')
                                if color:
                                    color = '#' + color[1].replace('>', '')
                                    last_element.update({'tag': 'font', "style": {"color": color},
                                                         'to': tag_index})
                            else:
                                last_element.update({'to': tag_index})
                            positions.append(copy.deepcopy(last_element))

                index_counter += 1

        new_line_positions = self.new_line_formatting(cleaned_text_for_new_line)
        positions.extend(new_line_positions)

        positions = self.reorder_tags(positions)

        return positions

    def reorder_tags(self, tags: list) -> list:
        """
        Reorder a list of tag dictionaries based on 'from' index and tag priority.
        """
        # Define tag priorities
        tag_priority = {'br': 1, 'ul': 2, 'ol': 2, 'li': 3}
        default_priority = 100
        return sorted(tags, key=lambda x: (x['from'], tag_priority.get(x['tag'], default_priority)))

    def new_line_formatting(self, text: str) -> list:
        """
        Find new line positions in text and return as formatting tags.
        """
        positions = []
        index = 0
        clean_text = text.replace('\u00a0', ' ').replace('\r\n', '*').replace('\n', '*')
        count_occurence_of_new_line = 0
        while index < len(clean_text):
            if clean_text[index] == '*':
                new_format = {"from": index - count_occurence_of_new_line, "tag": "br",
                              "to": index - count_occurence_of_new_line}
                if new_format not in positions:
                    positions.append(new_format)
                    count_occurence_of_new_line += 1
            index += 1
        return positions

    def remove_dict_with_key(self, data_list: list, target_key: str):
        """
        Remove the first dict in data_list containing target_key. Returns updated list and removed item.
        """
        for item in data_list:
            if target_key in item:
                data_list.remove(item)
                return data_list, item  # Return the updated list and the removed item
        return data_list, None

    def attach_items_to_attributes(self, source_dict, target_dict):
        """
        Attach dictionary items from a source dict to a target dict.
        """
        for item_key, item_value in source_dict.items():
            if item_key not in target_dict:
                target_dict[item_key] = copy.deepcopy(item_value)
            else:
                target_dict[item_key] = self.merge_items(target_dict[item_key], item_value)

    def merge_items(self, existing_items, new_items):
        """
        Merge new_items into existing_items, handling lists and nested values.
        """
        if isinstance(existing_items, list):
            if isinstance(new_items, list):
                for item in new_items:
                    if item not in existing_items:
                        existing_items.append(copy.deepcopy(item))
            else:
                if new_items not in existing_items:
                    existing_items.append(copy.deepcopy(new_items))
        else:
            existing_value = copy.deepcopy(existing_items)
            if existing_value:
                merged_list = [existing_value]
            else:
                merged_list = []
            if isinstance(new_items, list):
                for item in new_items:
                    if item not in merged_list:
                        merged_list.append(copy.deepcopy(item))
            else:
                if new_items not in merged_list:
                    merged_list.append(copy.deepcopy(new_items))
            return merged_list
        return existing_items

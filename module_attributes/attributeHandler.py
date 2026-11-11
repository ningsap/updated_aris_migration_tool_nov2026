import copy
import re

import spmclient.spm.utils
from spmclient.spm.spmclient import SPMClient
from alloy.logging.logger_utility import logger
from amlparser.amlparser import AMLParser
from amlparser.amlquery import AMLQuery
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import json


class AttributeHandler:
    def __init__(self, cfg: dict, spm: SPMClient, amlparser: AMLParser, aml_query: AMLQuery):

        self._spm = spm
        self.cfg = cfg
        self.attribute_mapping = cfg.get('aris_signavio_attribute_name_mapping', None)
        self.aris_signavio_attribute_value_mapping = cfg.get('aris_signavio_attribute_value_mapping', None)
        self.aris_signavio_attribute_value_mapping = {key.upper(): value for key, value in self.aris_signavio_attribute_value_mapping.items()}
        self.object_mapping = cfg.get('object_mapping', None)
        self.attribute_mapping_based_on_connection_type = cfg.get('attribute_mapping_based_on_connection_type', {})
        # self.languages = self._spm.configuration.get_active_languages()
        self.extract_email_from_attribute = cfg.get('extract_email_from_attribute', {})
        if self.extract_email_from_attribute is None:
            self.extract_email_from_attribute = {}
        self.dictionary_attributes_that_should_be_glossary_entries = cfg.get('dictionary_attributes_that_should_be_glossary_entries', {})
        if self.dictionary_attributes_that_should_be_glossary_entries is None:
            self.dictionary_attributes_that_should_be_glossary_entries = {}
        self.list_of_attributes_to_check_formatting = cfg.get('list_of_attributes_to_check_formatting', [])
        if self.list_of_attributes_to_check_formatting is None:
            self.list_of_attributes_to_check_formatting = []
        self.diagram_types_for_dictionary_handler = cfg.get('diagram_types_for_dictionary_handler', [])
        self.obj_definitions = amlparser.defs
        self.cxn_definitions = amlparser.cxns
        self.input_path = cfg.get('input_xml')
        self.meta_value_mapping = {}
        self.multilang_attributes = set()
        self.default_workspace_language = cfg.get('default_workspace_language', '')
        self.get_meta_value_mapping()
        self.linked_signavio_attribute = {}
        self.meta_attribute_mapping()
        self.amlquery = aml_query
        self.link_attributes_url_label_mapping = cfg.get(
            'link_attributes_url_label_mapping')
        self.dropdown_mapping_path = cfg.get(
            'dropdown_mapping_path', '')

        self.create_dropdown_mapping()
        self.get_model_shape_occurences()

    def get_model_shape_occurences(self):
        # filter models
        self.shape_defs_in_relevant_models = {}
        relevant_model_keys = list(filter(lambda model_key: self.amlquery.models.get(model_key).get('type')
                                   in self.diagram_types_for_dictionary_handler, self.amlquery.models))
        # get occurences in models
        for model_key in relevant_model_keys:
            shape_occs_of_model = self.amlquery.models.get(model_key, {}).get("occs", {})
            # get definition of shapes, with occ symbol, and model id
            for shape_occ_key in shape_occs_of_model:
                shape_occ = shape_occs_of_model.get(shape_occ_key)
                shape_def = shape_occ.get('def', '')
                shape_symbol = shape_occ.get('symbol', '')
                if shape_def not in self.shape_defs_in_relevant_models:
                    self.shape_defs_in_relevant_models[shape_def] = {model_key: [shape_symbol]}
                else:
                    if self.shape_defs_in_relevant_models[shape_def].get(model_key, ''):
                        if shape_symbol not in self.shape_defs_in_relevant_models[shape_def][model_key]:
                            self.shape_defs_in_relevant_models[shape_def][model_key].append(shape_symbol)
                    else:
                        self.shape_defs_in_relevant_models[shape_def][model_key] = [shape_symbol]

    def get_meta_value_mapping(self):
        '''
        return: JSON
        {
            key : Stencil , value : JSON {
                key: signavio attribute, value: JSON {
                keys [signavio_type, isList, items, dataFormat, category, glossaryBindings], values: values
                }
            }
        '''

        # This funciton returns a mapping for each stencilbinding and the meta-attributes belonging to that binding
        # it also includes the stencil "Dictionary" wich is a self made stencil and is not appering in signavio
        # this is mainly used for the creation of dicitonary items since it contains all the meta-attributes

        meta_values = self._spm.attributes.get()
        if meta_values:
            for item in meta_values:
                stencilset = item.get('rep').get('stencilsetBindings', [])
                for stencil in stencilset:
                    signavio_shape_type = stencil.get('stencil', '')
                    if signavio_shape_type:
                        if signavio_shape_type not in self.meta_value_mapping:
                            self.meta_value_mapping[signavio_shape_type] = {}

                        self.meta_value_mapping[signavio_shape_type].update({item.get('rep').get('id'): {
                            'signavio_type': item.get('rep').get('type'),
                            'isList': item.get('rep').get('isList', False),
                            'items': item.get('rep').get('items', []),
                            'dateFormat': item.get('rep').get('dateFormat', ''),
                            'category': item.get('rep').get('category', ''),
                            'glossaryBindings': item.get('rep').get('glossaryBindings', []),
                        }
                        })
                if 'Dictionary' not in self.meta_value_mapping:
                    self.meta_value_mapping['Dictionary'] = {}

                if item.get('rep').get('id') not in self.meta_value_mapping['Dictionary']:
                    self.meta_value_mapping['Dictionary'].update({item.get('rep').get('id'): {
                        'signavio_type': item.get('rep').get('type'),
                        'isList': item.get('rep').get('isList', False),
                        'items': item.get('rep').get('items', []),
                        'dateFormat': item.get('rep').get('dateFormat', ''),
                        'category': item.get('rep').get('category', ''),
                        'glossaryBindings': item.get('rep').get('glossaryBindings', [])
                    }})
                if item.get('rep').get('multilanguage', False):
                    self.multilang_attributes.add(item.get('rep').get('id'))
        # add name and description
        self.multilang_attributes.add('name')
        self.multilang_attributes.add('description')

    def meta_attribute_mapping(self):
        '''
        return: JSON
        {
            key : Aris Symbole type ,
            value : JSON {
                appears_as: What meta-attributes are using this category
                linked_attributes: which meta-attributes has this category (Category: Control has a Risk Attribte for example)
                keys [, linked_attributes], values: []
            }
        }
        '''

        # This functions creates a mapping for all glossary attributes
        # it returns the Symbole type defined in the objet mapping from the project config and then has
        # appears as and linked_attributes as key, value pairs to a specific meta attribute
        linked_meta_attributes = {}
        for k, v in self.meta_value_mapping['Dictionary'].items():
            if v.get('signavio_type') == 'MetaDataGlossaryLink':
                linked_meta_attributes[k] = v

        for obj_symbol, obj_value in self.object_mapping.items():
            parent_category = self.object_mapping.get(obj_symbol).get('main_category', '').replace('/glossarycategory/', '')
            other_categories = self.object_mapping.get(obj_symbol).get('other_categories', [])
            possible_glossary_categories = [item.replace("/glossarycategory/", "") for item in other_categories]
            for attribute, attr_value in linked_meta_attributes.items():
                # appears at
                if obj_symbol not in self.linked_signavio_attribute:
                    self.linked_signavio_attribute[obj_symbol] = {}

                # TODO Category can be an empty string. In that case all links could be added to the element. Is this something we have to take in to account?

                if attr_value.get('category') == parent_category or attr_value.get('category') in possible_glossary_categories:
                    if not self.linked_signavio_attribute[obj_symbol].get('appears_as'):
                        self.linked_signavio_attribute[obj_symbol]['appears_as'] = [
                        ]
                    self.linked_signavio_attribute[obj_symbol]['appears_as'].append(
                        attribute)

                # get all the Attributes
                if len(attr_value.get('glossaryBindings')) > 0:
                    for item in attr_value.get('glossaryBindings'):
                        if item.get('category') == parent_category or item.get('category') in possible_glossary_categories:
                            if not self.linked_signavio_attribute[obj_symbol].get('linked_attributes'):
                                self.linked_signavio_attribute[obj_symbol]['linked_attributes'] = []
                            self.linked_signavio_attribute[obj_symbol]['linked_attributes'].append(
                                {attribute: {'glossaryBinding': item.get('category'),
                                             'category_entry': attr_value.get('category')}})

    def get_mapped_attribute_key(self, aris_attribute):
        """
        Fetch Aris->Signavio mapped attribute
        Parameters
        ----------
        aris_attribute: str
            the attributes key (or xml-property, e.g. "@originKey")

        Returns
        -------
        str
            Aris attribute key (e.g. "meta-itsystem") if defined in projectconfig.yaml or None
        """
        return self.attribute_mapping.get(aris_attribute, None)

    def common_keys(self, json1, json2):
        return set(json1.keys()) & set(json2.keys())

    def convert_link_attribute(self, aris_attribute_name: str, aris_attributes: dict, attributes_to_update: dict):
        """
            prepares signavio attribute mapping for link attributes
            aris_attribute_name(str): name of aris attribute
            aris_attributes(dict): aris objects attributes
            return: dict key: signavio_attribute_name, value: { label: '' , url: '' }
        """
        signavio_attr_name = ''
        link = {}
        aris_attr_keyword = self.check_keyword_is_in_list_of_elements(aris_attribute_name, self.attribute_mapping.keys())
        if aris_attr_keyword:
            signavio_attr_name = self.attribute_mapping.get(aris_attr_keyword)
            aris_title = self.link_attributes_url_label_mapping.get(aris_attribute_name, '')
            url_value_with_lang = aris_attributes.get(aris_attribute_name, '')
            title_value_with_lang = aris_attributes.get(aris_title, '')
            unique_urls = set()
            url_value = ''
            for lang_keys in url_value_with_lang:
                url_value = url_value_with_lang.get(lang_keys, '')
                if url_value and url_value in unique_urls:
                    # skip if url is the same for another language dont add it twice
                    continue
                unique_urls.add(url_value)
                title_value = ''
                if title_value_with_lang:
                    title_value = title_value_with_lang.get(lang_keys, '')
                if not url_value:
                    continue
                if title_value == '' or aris_title is None:
                    link = {'label': url_value[0:30], 'url': url_value}
                else:
                    link = {'label': title_value, 'url': url_value}

                if signavio_attr_name and link:
                    if signavio_attr_name in attributes_to_update:
                        attributes_to_update[signavio_attr_name].append(copy.deepcopy(link))
                    else:
                        attributes_to_update[signavio_attr_name] = [copy.deepcopy(link)]

    def get_attributes_of_object(self, object_def_id, occ_data, stencil=''):
        '''
        return: JSON  key : signavio attribute , value : attribute value
        '''

        object_definition = self.obj_definitions.get(object_def_id, {})
        attributes = copy.deepcopy(object_definition.get("attrs", {}))

        # handle linked items is need at this position, since they kinda get attributes of an object.
        linked_items = self.linked_items(object_definition, occ_data, stencil)
        attribute_to_dict = {}

        signavio_attributes = {}
        styles = copy.deepcopy(attributes.get('styles', {}))
        attributes['styles'] = {}
        for attr in attributes:
            if attr == 'styles':
                continue
            # check language keys of attr
            skip_other_langs = False
            aris_vals_lang = attributes[attr]
            for lang_key in aris_vals_lang:
                if skip_other_langs:
                    break
                aris_val_with_lang_key = aris_vals_lang[lang_key]
                # check if attribute is multilang
                signavio_attribute_name = self.attribute_mapping.get(attr, None)
                if signavio_attribute_name == "meta-riskownernamerfo":
                    print()
                initial_attr_name = copy.deepcopy(signavio_attribute_name)
                if signavio_attribute_name:
                    if signavio_attribute_name in self.multilang_attributes:
                        if lang_key != self.default_workspace_language:
                            # add language suffix to the attribute
                            signavio_attribute_name = signavio_attribute_name + '_' + lang_key
                    if len(aris_vals_lang.keys()) > 1 and initial_attr_name not in self.multilang_attributes:
                        logger.error(
                            f'Attribute {signavio_attribute_name} is not configured as multilang attribute. Fetching only the first language entry and ignoring other languages!')
                        skip_other_langs = True

                current_style = styles.get(attr, '').get(lang_key, '')
                if signavio_attribute_name is None:
                    if attr in self.link_attributes_url_label_mapping.keys():
                        self.convert_link_attribute(attr, attributes, attributes_to_update=signavio_attributes)

                    elif attr not in self.link_attributes_url_label_mapping.keys() and attr not in self.link_attributes_url_label_mapping.values():
                        logger.error("Attribute is not available in object mapping " + attr)
                elif attr in self.link_attributes_url_label_mapping.keys():
                    self.convert_link_attribute(attr, attributes, attributes_to_update=signavio_attributes)

                elif signavio_attribute_name.startswith('meta-commentexample') or signavio_attribute_name.startswith('description'):
                    if signavio_attributes.get(signavio_attribute_name, ''):
                        signavio_attributes[signavio_attribute_name] = signavio_attributes.get(
                            signavio_attribute_name, '') + ' \n ' + copy.deepcopy(aris_val_with_lang_key)
                    else:
                        signavio_attributes[signavio_attribute_name] = copy.deepcopy(aris_val_with_lang_key)

                    if signavio_attribute_name not in attributes['styles']:
                        attributes['styles'][signavio_attribute_name] = current_style
                    else:
                        attributes['styles'][signavio_attribute_name] = attributes['styles'][signavio_attribute_name] + ' \n ' + current_style

                else:
                    if attr in self.dictionary_attributes_that_should_be_glossary_entries.keys():
                        # check email attributes
                        attr_value = self.aris_signavio_attribute_value_mapping.get(aris_val_with_lang_key.upper().strip()) or aris_val_with_lang_key
                        if attr not in attribute_to_dict:
                            if attr in self.extract_email_from_attribute:
                                attr_value = attr_value.lower()
                                attr_value = self.extract_emails(attr_value)
                            if attr_value:
                                attribute_to_dict[attr] = {
                                    'value': attr_value, 'categories_to_check': self.dictionary_attributes_that_should_be_glossary_entries[attr], 'signavio_attribute_name': signavio_attribute_name}
                    else:
                        attr_value = self.aris_signavio_attribute_value_mapping.get(aris_val_with_lang_key.upper().strip()) or aris_val_with_lang_key
                        if signavio_attribute_name.split('_')[0] in self.list_of_attributes_to_check_formatting:
                            if signavio_attribute_name not in attributes['styles']:
                                attributes['styles'][signavio_attribute_name] = current_style
                            else:
                                attributes['styles'][signavio_attribute_name] = attributes['styles'][signavio_attribute_name] + ' \n ' + current_style

                        formatted_property = self.get_property_in_correct_format(signavio_attribute_name, attr_value, stencil)
                        signavio_attributes.update(formatted_property)

        if stencil == 'Dictionary':
            return signavio_attributes, linked_items, attribute_to_dict, attributes['styles']
        else:
            return signavio_attributes

    def get_attributes_of_connection(self, connection_def_id, stencil=''):
        '''
        return: JSON  key : signavio attribute , value : attribute value
        '''

        object_definition = self.cxn_definitions.get(connection_def_id, {})
        attributes = object_definition.get("attrs", {})
        signavio_attributes = {}
        for attr in attributes:
            if attr == 'styles':
                continue
            # check language keys of attr
            skip_other_langs = False
            aris_vals_lang = attributes[attr]
            for lang_key in aris_vals_lang:
                if skip_other_langs:
                    break
                aris_val_with_lang_key = aris_vals_lang[lang_key]
                # check if attribute is multilang
                signavio_attribute_name = self.attribute_mapping.get(attr, None)
                if attr == 'AT_ID':
                    signavio_attribute_name = 'None'
                initial_attr_name = copy.deepcopy(signavio_attribute_name)
                if signavio_attribute_name:
                    if signavio_attribute_name in self.multilang_attributes:
                        if lang_key != self.default_workspace_language:
                            # add language suffix to the attribute
                            signavio_attribute_name = initial_attr_name + '_' + lang_key
                    if len(aris_vals_lang.keys()) > 1 and initial_attr_name not in self.multilang_attributes:
                        logger.error(
                            f'Attribute {signavio_attribute_name} is not configured as multilang attribute. Fetching only the first language entry and ignoring other languages!')
                        skip_other_langs = True

            if signavio_attribute_name is None:
                logger.error(
                    "Attribute is not available in object mapping " + attr)
            else:
                attr_value = aris_val_with_lang_key
                formatted_property = self.get_property_in_correct_format(signavio_attribute_name, attr_value, stencil)
                signavio_attributes.update(formatted_property)

        return signavio_attributes

    def get_attribute_value_for_dictionary_item(self, signavio_attr_name, attr_val, stencil):
        # return value
        signavio_attribute = {}
        if len(signavio_attr_name) != 0:
            signavio_attribute = self.get_property_in_correct_format(
                signavio_attr_name, attr_val, stencil)
            if signavio_attribute is None:
                signavio_attribute = {}
        return signavio_attribute.get(signavio_attr_name, '')

    def linked_items(self, object_definition, occ_data, stencil):

        outgoing_cnx = object_definition.get("outgoing_cxns", [])
        incoming_cnx = object_definition.get("incoming_cxns", [])
        # model_shape_occurences = self.amlquery.models.get(occ_data.get('model_id',''),{}).get('occs',{})

        linked_items = []
        linked_items_attribute = {}
        if stencil == 'Dictionary':
            for connected_obj_def_id in incoming_cnx:
                connected_obj_def = self.amlquery.get_obj_def({"def": connected_obj_def_id})
                # for cxn_id in incoming_cnx.get(connected_obj_def_id):
                type_of_cxn_def = incoming_cnx.get(connected_obj_def_id).get('type', '')
                # type_of_cxn_def = cxn_def.get('type','')
                # if type_of_cxn_def in self.attribute_mapping_based_on_connection_type:
                # check assigned models of connected_obj_def and check whether these models are defined in config and check occurences
                assigned_models = self.amlquery.get_assigned_models(connected_obj_def)
                connected_models = self.shape_defs_in_relevant_models.get(connected_obj_def_id, {})
                for model_key in connected_models:
                    connected_symbols = connected_models.get(model_key)
                    for connected_symbol in connected_symbols:
                        attribute = self.attribute_mapping_based_on_connection_type.get(type_of_cxn_def, {}).get(connected_symbol, '')
                        if isinstance(attribute, dict):
                            attribute = attribute['incoming']
                        if attribute != '':
                            data = copy.deepcopy(connected_obj_def)
                            data['attribute'] = attribute
                            if data not in linked_items:
                                linked_items.append(data)

            for connected_obj_def_id in outgoing_cnx:
                connected_obj_def = self.amlquery.get_obj_def({"def": connected_obj_def_id})
                # for cxn_id in incoming_cnx.get(connected_obj_def_id):
                type_of_cxn_def = outgoing_cnx.get(connected_obj_def_id).get('type', '')
                # type_of_cxn_def = cxn_def.get('type','')
                # if type_of_cxn_def in self.attribute_mapping_based_on_connection_type:
                # check assigned models of connected_obj_def and check whether these models are defined in config and check occurences
                assigned_models = self.amlquery.get_assigned_models(connected_obj_def)
                connected_models = self.shape_defs_in_relevant_models.get(connected_obj_def_id, {})
                for model_key in connected_models:
                    connected_symbols = connected_models.get(model_key)
                    for connected_symbol in connected_symbols:
                        attribute = self.attribute_mapping_based_on_connection_type.get(type_of_cxn_def, {}).get(connected_symbol, '')
                        if isinstance(attribute, dict):
                            attribute = attribute['outgoing']
                        if attribute != '':
                            data = copy.deepcopy(connected_obj_def)
                            data['attribute'] = attribute
                            if data not in linked_items:
                                linked_items.append(data)

            if len(linked_items) > 0:
                linked_items_attribute = self.handle_linked_items(linked_items, object_definition.get('symbol'))
        else:
            linked_items_attribute = {}

        return linked_items_attribute

    def handle_linked_items(self, linked_items, parent_shape):
        result = {}
        attributes = {}
        # if parent_shape == 'ST_RISK_1':
        #    logger.info('Here')

        if not parent_shape:
            return result
        infos_from_object_mapping = self.object_mapping.get(parent_shape)
        if not infos_from_object_mapping:
            return result
        glossary_category_of_parent = infos_from_object_mapping.get('main_category').replace('/glossarycategory/', '')
        other_categories = infos_from_object_mapping.get('other_categories', [])
        possible_glossary_categories_of_parent = [item.replace("/glossarycategory/", "") for item in other_categories]
        possible_glossary_categories_of_parent.append(glossary_category_of_parent)

        for linked_item in linked_items:
            symbol_of_linked_item = linked_item.get('symbol')
            if symbol_of_linked_item:
                object_mapping_of_linked_item = self.object_mapping.get(symbol_of_linked_item)
                if object_mapping_of_linked_item:
                    glossary_category_of_linked_item = object_mapping_of_linked_item.get('main_category').replace('/glossarycategory/', '')

                    other_categories_for_linked_item = object_mapping_of_linked_item.get('other_categories', [])
                    possible_glossary_category_for_linked_items = [item.replace(
                        "/glossarycategory/", "") for item in other_categories_for_linked_item]
                    possible_glossary_category_for_linked_items.append(glossary_category_of_linked_item)
                    attribute_to_set = linked_item.get('attribute', '')

                    if attribute_to_set == '':
                        attribute_to_set = object_mapping_of_linked_item.get('transform_attribute')

                    if self.linked_signavio_attribute.get(parent_shape):
                        if self.linked_signavio_attribute.get(parent_shape).get('linked_attributes'):
                            for linked_attribute in self.linked_signavio_attribute.get(parent_shape).get('linked_attributes'):
                                attribute_name = list(linked_attribute.keys())[0]
                                if attribute_to_set == attribute_name:
                                    # Check if the attribute has a stencil binding to the parent category
                                    if linked_attribute.get(attribute_name).get('glossaryBinding') in possible_glossary_categories_of_parent:
                                        # Check if attribute is same category as linked item
                                        if linked_attribute.get(attribute_name).get('category_entry') in possible_glossary_category_for_linked_items:
                                            if self.meta_value_mapping.get('Dictionary').get(attribute_name).get('isList'):
                                                # check if attribute is already existing
                                                if attributes.get(attribute_name):
                                                    if linked_item.get('guid') not in attributes[attribute_name]:
                                                        attributes[attribute_name].append(linked_item.get('guid'))
                                                else:
                                                    attributes.update({attribute_name: [linked_item.get('guid')]})
                                            else:
                                                # check if attribute is already existing
                                                if attributes.get(attribute_name):
                                                    attribute_with_error = attribute_name
                                                    logger.error('There is a second value for ' + attribute_with_error +
                                                                 ' but it is not a list. Correct the Attribute config in Signavio.')
                                                else:
                                                    attributes.update({attribute_name: linked_item.get('guid')})

            result.update(attributes)

        return result

    def clean_text(self, input_text: str) -> str:
        # Parse the HTML content
        soup = BeautifulSoup(input_text, "html.parser")
        self.remove_empty_tags(soup)
        # List of allowed tags
        allowed_tags = {'br', 'b', 'i', 'u', 'ol', 'li', 'ul'}

        # Remove all tags not in the allowed list
        for tag in soup.find_all():
            if tag.name not in allowed_tags:
                tag.unwrap()  # This removes the tag but keeps its contents

        # Return the cleaned HTML as a string
        return str(soup)

    def remove_empty_tags(self, soup):
        self_closing_tags = {'br', 'img', 'hr', 'input', 'link', 'meta'}
        stack = [soup]

        while stack:
            current = stack.pop()

            children = list(current.find_all(True, recursive=False))
            for child in children:
                stack.append(child)

            if current.name in self_closing_tags:
                continue
            if not current.contents or (current.string and not current.string.strip()):
                if current.parent is not None:
                    current.decompose()

    def contains_html_tags(self, s: str) -> bool:
        html_tag_pattern = re.compile(r'<[^>]+>')
        if isinstance(s, bool):
            return False
        elif isinstance(s, list):
            matched = False
            for entry in s:
                if bool(html_tag_pattern.search(entry)):
                    matched = True
            return matched
        else:
            return bool(html_tag_pattern.search(s))

    def get_property_in_correct_format(self, attribute_name, attribute_value, stencil):
        '''
        tested: MetaDataBoolean, MetaDataDate, MetaDataEnum
        According to Workspace content checks the attribute configuration
        If attribute is configured as a list returns list, if not returns the value
        If type or format of the value doesn't match with the workspace content logs the error
        The formatted attribute will always be returned with attribute_value in case we need to run a postmigration script
        return: formatted_attribute JSON key : attribute key, val : attribute value
        '''

        formatted_attribute = {}
        if attribute_name.startswith('meta-'):
            # check attribute is list or not
            attribute = self.meta_value_mapping.get(
                stencil, {}).get(attribute_name, {})
            if attribute == {}:
                logger.error(
                    'Attribute is not available in Signavio Workspace ' + attribute_name)
                formatted_attribute[attribute_name] = attribute_value
                return formatted_attribute

            is_attribute_list_in_ws = attribute.get('isList')

            if is_attribute_list_in_ws and not isinstance(attribute_value, list):
                logger.error(
                    f'For Attribute Name {attribute_name}: {attribute_value} should be list')
            elif not is_attribute_list_in_ws and isinstance(attribute_value, list):
                if len(attribute_value) == 1:
                    logger.warning(
                        f'For Attribute Name {attribute_name}: Attribute Value has only one item: {attribute_value}, Workspace accepts one item. Will set this single item instead of list ')
                    attribute_value = attribute_value[0]
                else:
                    logger.error(
                        f'For Attribute Name {attribute_name}: {attribute_value} should not be list')

            if attribute.get('signavio_type') == "MetaDataBoolean":
                # check value
                if isinstance(attribute_value, list):
                    # check format of array elements
                    attribute_value = list(filter(lambda a: True if attribute_value in ['true', '1'] else False, attribute_value))
                    # if len(item) > 0:
                    # logger.error(f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. All attribute values in the list should be boolean')
                    formatted_attribute[attribute_name] = attribute_value
                elif isinstance(attribute_value, bool):
                    if is_attribute_list_in_ws:
                        formatted_attribute[attribute_name] = [attribute_value]
                    else:
                        formatted_attribute[attribute_name] = attribute_value
                else:
                    # logger.error(f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value { attribute_value}. Attribute value type should be boolean')
                    if is_attribute_list_in_ws:
                        attribute_value = list(filter(lambda a: True if attribute_value in ['true', '1'] else False, attribute_value))
                        formatted_attribute[attribute_name] = [attribute_value]
                    else:
                        attribute_value = True if attribute_value in ['true', '1'] else False
                        formatted_attribute[attribute_name] = attribute_value

            elif attribute.get('signavio_type') == "MetaDataDate":
                # check format of attribute value
                dateFormat = attribute.get('dateFormat', '')
                # default date format
                if len(dateFormat) == 0 or '%' not in dateFormat:
                    dateFormat = '%d/%m/%Y'
                if isinstance(attribute_value, list):
                    item = list(filter(lambda a: self.is_valid_date(a, dateFormat) != True, attribute_value))
                    dates_to_set = attribute_value
                    if len(item) > 0:
                        dates_to_set = [self.convert_date(date, dateFormat) for date in attribute_value]
                        if False in dates_to_set:
                            logger.error(
                                f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. All attribute values in the list should be date')
                    formatted_attribute[attribute_name] = dates_to_set
                else:
                    correct_date_format = self.is_valid_date(attribute_value, dateFormat)
                    if not correct_date_format:
                        attribute_value = self.convert_date(attribute_value, dateFormat)
                        if not attribute_value:
                            logger.error(
                                f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. Attribute value should be Date in d/m/Y format')
                    if is_attribute_list_in_ws:
                        formatted_attribute[attribute_name] = [attribute_value]
                    else:
                        formatted_attribute[attribute_name] = attribute_value
            elif attribute.get('signavio_type') == "MetaDataEnum":
                # get enum values
                if attribute_value != "0" or attribute_value != 0:
                    enum_items = self.meta_value_mapping.get(
                        stencil, {}).get(attribute_name, {}).get('items', [])
                    item = list(filter(lambda a: a['title'] == attribute_value or a['value'] == attribute_value, enum_items))
                    if len(item) > 0:
                        cid = item[0].get('value', '')
                        formatted_attribute[attribute_name] = cid
                    else:
                        logger.error(
                            f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. Attribute value does not match with the drop down values')
                        formatted_attribute[attribute_name] = ''
            elif attribute.get('signavio_type') == "MetaDataComplex":
                # TODO: table
                pass
            elif attribute.get('signavio_type') == "MetaDataGlossaryLink":
                # check /glossary/ keyword
                if isinstance(attribute_value, list):
                    item = list(filter(lambda a: '/glossary/' not in a, attribute_value))
                    if len(item) > 0:
                        logger.error(
                            f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. All attribute values in the list should be glossary link')

                    attribute_value_to_set = list(filter(lambda a: '/glossary/' in a, attribute_value))
                    formatted_attribute[attribute_name] = attribute_value_to_set
                else:
                    if '/glossary/' not in attribute_value:
                        logger.error(
                            f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. Attribute values should be dictionary link')
                    else:
                        if is_attribute_list_in_ws:
                            if isinstance(attribute_value, list):
                                formatted_attribute[attribute_name] = attribute_value
                            else:
                                formatted_attribute[attribute_name] = [attribute_value]
                        else:
                            if isinstance(attribute_value, list):
                                formatted_attribute[attribute_name] = attribute_value[0]  # TODO
                            else:
                                formatted_attribute[attribute_name] = attribute_value

            elif attribute.get('signavio_type') == "MetaDataModelLink":
                # check /model/ keyword
                if isinstance(attribute_value, list):
                    item = list(
                        filter(lambda a: '/model/' not in a, attribute_value))
                    if len(item) > 0:
                        logger.error(
                            f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. All attribute values in the list should be model link')
                    formatted_attribute[attribute_name] = attribute_value
                else:
                    if '/model/' not in attribute_value:
                        logger.error(
                            f'Trying to set a wrong value for Attribute Name {attribute_name} Attribute Value {attribute_value}. Attribute values should be model link')
                    if is_attribute_list_in_ws:
                        formatted_attribute[attribute_name] = [attribute_value]
                    else:
                        formatted_attribute[attribute_name] = attribute_value

            elif attribute.get('signavio_type') == "MetaDataNumberInfo":
                if is_attribute_list_in_ws:
                    if isinstance(attribute_value, list):
                        formatted_attribute[attribute_name] = attribute_value
                    else:
                        formatted_attribute[attribute_name] = [attribute_value]
                else:
                    formatted_attribute[attribute_name] = attribute_value

            elif attribute.get('signavio_type') == "MetaDataStringInfo":
                # add text formatter
                if is_attribute_list_in_ws:
                    if isinstance(attribute_value, list):
                        formatted_attribute[attribute_name] = attribute_value
                    else:
                        formatted_attribute[attribute_name] = [attribute_value]
                else:
                    if not isinstance(attribute_value, list):
                        if self.contains_html_tags(attribute_value):
                            attribute_value = self.clean_text(attribute_value)
                        formatted_attribute[attribute_name] = attribute_value
                    elif isinstance(attribute_value, list):
                        cleaned_attribute_values = []
                        for attrib_val in attribute_value:
                            if self.contains_html_tags(attrib_val):
                                cleaned_attribute_values.append(
                                    self.clean_text(attrib_val))
                            else:
                                cleaned_attribute_values.append(attrib_val)
                        formatted_attribute[attribute_name] = cleaned_attribute_values

            elif attribute.get('signavio_type') == "MetaDataUrl":
                if is_attribute_list_in_ws:
                    if isinstance(attribute_value, list):
                        formatted_attribute[attribute_name] = attribute_value
                    else:
                        formatted_attribute[attribute_name] = [attribute_value]
                else:
                    formatted_attribute[attribute_name] = attribute_value
        else:
            # name, description, documentation
            if self.contains_html_tags(attribute_value):
                attribute_value = self.clean_text(attribute_value)
            formatted_attribute[attribute_name] = attribute_value

        return formatted_attribute

    def is_valid_date(self, date_str, dateFormat):
        try:
            # Try to parse the date string with the given data format
            datetime.strptime(date_str, dateFormat)
            return True
        except ValueError:
            return False

    def convert_date(self, date_str, dateFormat):
        try:
            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            # Convert the datetime object back to a string in dd/mm/yyyy format
            converted_date = date_obj.strftime(dateFormat)
            return converted_date
        except ValueError:
            return False

    def check_keyword_is_in_list_of_elements(self, txt_shape, shape_mapping_list):
        # list contains elements with the substring
        # txt_shape includes the search keyword
        for string in shape_mapping_list:
            if string in txt_shape:
                return string
        return False

    def get_dropdown_mapping_signavio(self):
        dropdowns_signavio = {}
        if self.meta_value_mapping.get('Dictionary'):
            # type: ignore
            for k, v in self.meta_value_mapping.get('Dictionary').items():
                if v.get('items'):
                    for dropdown_item in v.get('items'):
                        if k not in dropdowns_signavio:
                            dropdowns_signavio[k] = {dropdown_item.get(
                                'title'): dropdown_item.get('id')}
                        else:
                            dropdowns_signavio[k].update(
                                {dropdown_item.get('title'): dropdown_item.get('id')})
        return dropdowns_signavio

    def extract_non_object(self, text):
        # TODO place the array below in to the config!
        skip_list = ['Object', 'Capabilities Marker']
        # Find all values inside parentheses
        matches = pd.Series(text).str.findall(r'\((.*?)\)').explode()
        technical_attribute_name = matches[~matches.isin(skip_list)].iloc[0] if len(
            matches[~matches.isin(skip_list)]) > 0 else None
        # Extract the part before the first parentheses
        attribute_name = text.split('(')[0].strip()
        return attribute_name + ';' + technical_attribute_name

    def map_aris_dropdowns(self, items):

        all_items = items.split(',')
        mapping = {}
        # I encountered that values cound be in the format of "This, Spceial, Entry=ARISID"
        # the following flags take this in to account
        has_comma_in_title = False
        error_handling = ''
        for item in all_items:

            if '=' not in item and not has_comma_in_title:
                has_comma_in_title = True
                if error_handling == '':
                    error_handling = item
                    continue
                else:
                    error_handling = error_handling + ', ' + item
                    continue

            if '=' not in item and has_comma_in_title:
                if error_handling == '':
                    error_handling = item
                    continue
                else:
                    error_handling = error_handling + ', ' + item
                    continue

            if '=' in item and has_comma_in_title:
                error_handling = error_handling + ', ' + item

            if has_comma_in_title:
                tmp = error_handling.split('=')
                error_handling = ''
                has_comma_in_title = False
            else:
                tmp = item.split('=')

            mapping[tmp[0]] = tmp[1]
        return mapping

    def get_dropdown_mapping_aris(self):

        try:
            excel_file = 'input/SKF_Convention_Filter.xlsx'
            # Hier den genauen Namen des Reiters eintragen
            sheet_name = 'Object attribute types'
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            df['Attribute Name'] = df['Attribute Type'].apply(
                self.extract_non_object)
            df['Object Name'] = df['Object Type'].apply(
                self.extract_non_object)

            df_filtered = df.dropna(subset=['Value Mapping'])

            aris_dropdowns = {}
            for index, row in df_filtered.iterrows():
                object_type = row['Object Name']
                attribute_type = row['Attribute Name']
                values = row['Value Mapping']
                values_mapped = self.map_aris_dropdowns(values)

                if object_type not in aris_dropdowns:
                    aris_dropdowns[object_type] = {
                        attribute_type: values_mapped
                    }
                else:
                    if attribute_type not in aris_dropdowns.get(object_type):
                        aris_dropdowns[object_type].update(
                            {attribute_type: values_mapped}
                        )
                    else:
                        aris_dropdowns[object_type][attribute_type].update()
            return aris_dropdowns
        except:
            logger.error(
                'Attribute Handler - Could not form Aris Data for Drop Downs')
            return {}

    def transform_dropdown_mapping_to_config(self):
        excel_file = 'input/dropdownmapping.xlsx'
        sheet_name = 'Aris To Signavio'
        coloumns = ['Dropdown_Value', 'Suggested_Signavio_Value']
        df = pd.read_excel(excel_file, sheet_name=sheet_name, usecols=coloumns)
        df = df.dropna()

        column_key = 'Dropdown_Value'
        column_value = 'Suggested_Signavio_Value'

        aris_signavio_mapping = df.set_index(
            column_key)[column_value].to_dict()

        file_name = 'input/dropdown_mapping.json'

        with open(file_name, "w") as outfile:
            json.dump(aris_signavio_mapping, outfile)

    def create_dropdown_mapping(self):
        # read out the configuration out of signavio and map all dropdowns to (attribute: {dropdown_value:'Text'})
        try:
            signavio_dropdowns = self.get_dropdown_mapping_signavio()
        except:
            logger.error(
                'Attribute Handler - Could not retreive Signavio Dropdowns')
        # read out all the dropdowns from the report excel for Aris (attribute: {dropdown_value:'Text'})
        try:
            aris_dropdowns = self.get_dropdown_mapping_aris()
        except:
            logger.error(
                'Attribute Handler - Could not retreive Aris Dropdowns')
        # read config what attribute is mapped to what attribute
        # pre "sort" matching texts to each other
        # output excel, that can be adjusted fo further mapping
        just_dropdown_values_aris = {}
        counter = 0

        output_aris = []
        for object_name, object_attributes in aris_dropdowns.items():
            for object_attribute_name, dropdown_values in aris_dropdowns[object_name].items():
                signavio_dropdown_values = {}
                attribute_name = object_attribute_name.split(';')[1]
                if attribute_name in self.attribute_mapping:
                    if signavio_dropdowns.get(self.attribute_mapping.get(attribute_name)):
                        signavio_dropdown_values = signavio_dropdowns.get(
                            self.attribute_mapping.get(attribute_name), '')

                # if there is no correspoinding mapping
                # look for fitting signavio attributes that have fitting dropdown values
                else:
                    score = {}
                    for dropdown_name, dropdown_id in dropdown_values.items():
                        for meta_attribute, dropdown in signavio_dropdowns.items():
                            for dropdown_name_signavio, dropdown_id_signavio in dropdown.items():
                                if dropdown_name == dropdown_name_signavio:
                                    if meta_attribute not in score:
                                        score[meta_attribute] = 1
                                    else:
                                        score[meta_attribute] = score[meta_attribute] + 1
                    winner = ''
                    winner_score = 0
                    for meta_attribute, score_value in score.items():
                        if winner == '':
                            winner = meta_attribute
                            winner_score = score_value

                        if winner_score < score_value:
                            winner = meta_attribute
                            winner_score = score_value

                    if winner != '':
                        signavio_dropdown_values = signavio_dropdowns.get(
                            winner, '')

                for dropdown_name, dropdown_value in dropdown_values.items():
                    output_aris.append({
                        'Object_Name': object_name,
                        'Attribute_Name': object_attribute_name,
                        'Dropdown_Name': dropdown_name,
                        'Dropdown_Value': dropdown_value,
                        'Mapped_Signavio_Attributed': self.attribute_mapping.get(attribute_name, ''),
                        'Suggested_Signavio_Attributed': winner,
                        'Suggested_Signavio_Value': signavio_dropdown_values.get(dropdown_name, ''),
                        'Other_Signavio_Dropdown_Values': signavio_dropdown_values
                    })

        output_signavio = []
        for attribute_name, dropdown_values in signavio_dropdowns.items():
            for dropdown_name, dropdown_value in dropdown_values.items():
                output_signavio.append({
                    'Meta_Attribut': attribute_name,
                    'Dropdown_Name': dropdown_name,
                    'Dropdown_Value': dropdown_value
                })

        # Build suggestion mapping

        # Convert the arrays of dictionaries into DataFrames
        df1 = pd.DataFrame(output_aris)
        df2 = pd.DataFrame(output_signavio)

        # Write the DataFrames to different sheets in the same Excel file
        with pd.ExcelWriter('output/dropdownmapping.xlsx') as writer:
            df1.to_excel(writer, sheet_name='Aris To Signavio', index=False)
            df2.to_excel(writer, sheet_name='Signavio', index=False)

        # k object name
        # v all attributes of that object
        for k, v in aris_dropdowns.items():
            counter = counter + 1
            # k2 attribute name
            # v2 all dropdowns of that attribute
            for k2, v2 in aris_dropdowns[k].items():
                just_dropdown_values_aris.update(v2)

        just_dropdown_values_signavio = {}
        for k, v in signavio_dropdowns.items():
            just_dropdown_values_signavio.update(v)

        self.transform_dropdown_mapping_to_config()

    def extract_emails(self, text):
        # Regular expression pattern for matching email addresses
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        # Find all matches in the text
        emails = re.findall(email_pattern, text)
        return emails

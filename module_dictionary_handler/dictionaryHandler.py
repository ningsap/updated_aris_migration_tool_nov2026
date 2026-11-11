import copy
import json
import pandas as pd
import re
import os

# modules
import table_definitions as table_definitions
from module_attributes.attributeHandler import AttributeHandler
from alloy.logging.logger_factory import logger
from spmclient.spm.spmclient import SPMClient
from amlparser.amlparser import AMLParser
from alloy.task_watch.task_watch import TaskWatch


class DictionaryHandler:

    def __init__(self, cfg, spm: SPMClient, amlparser: AMLParser, attribute_handler: AttributeHandler,
                 file_tracker: TaskWatch, preload_glossary: bool):
        self.cfg = cfg
        self._spm = spm
        self.amlparser = amlparser
        self.file_tracker = file_tracker
        self.input_path = cfg.get('input_xml')
        self.new_glossary_entries = {}
        self.attributeHandler = attribute_handler
        self.object_mapping = cfg.get('object_mapping', None)
        self.model_types = cfg.get('diagram_types_for_dictionary_handler', None)
        self.excluded_obj_types = cfg.get('excluded_obj_types', None)
        if not self.object_mapping:
            logger.error("No object mapping defined")
        self.amlquery = attribute_handler.amlquery
        self.dictionary_content = {}
        if preload_glossary:
            self._preload_dictionary_categories()
        self.pool_name = cfg.get('pool_name', None)
        self.glossary_category_to_create_pool = cfg.get('glossary_category_to_create_pool', None)
        self.list_of_attributes_to_check_formatting = cfg.get('list_of_attributes_to_check_formatting', [])
        self.create_dictionary_entry_from_attribute = cfg.get('create_dictionary_entry_from_attribute', {})

        self.process_specific_roles_glossary_category = cfg.get('process_specific_roles_glossary_category', '')
        if self.process_specific_roles_glossary_category is None:
            self.process_specific_roles_glossary_category = ''

        self.default_workspace_language = cfg.get('default_workspace_language', '')
        # get workspace language to create pool title in every language
        self.active_languages = []
        self.title_keys = []
        self.description_keys = []
        try:
            self.active_languages = self._spm.configuration.get_active_languages()
        except RuntimeError as e:
            logger.error(e)

        if self.active_languages:
            language_suffixes = [item.get('rel') for item in self.active_languages if item.get('rel') != self.default_workspace_language]
            self.title_keys = ['title' + '_' + suffix for suffix in language_suffixes]
            self.description_keys = ['description' + '_' + suffix for suffix in language_suffixes]

    def _preload_dictionary_categories(self):
        """
        Loads all categories and entries within these categories into self.dictionary_content
        """
        """
        :return:
        """
        all_categories = self._spm.dictionary.get_all_categories()
        child_categories = []
        for category in list(filter(lambda cat: cat['rep']['childCategoryCount'] > 0, all_categories)):
            for child_category in category['rep']['childCategories']:
                c = {'rel': 'cat', 'href': child_category}
                child_categories.append(c)
        all_categories.extend(child_categories)
        for category in all_categories:
            logger.info(f"Reading dictionary content from category {category['href']}")
            category_items = self._spm.dictionary.get_all_entries_of_category(category['href'])
            for item in category_items:
                self.dictionary_content[item.get('href')] = item.get('rep')

        self.check_what_is_already_there()

    def check_what_is_already_there(self):
        for k, v in self.dictionary_content.items():
            # if items have an aris identifier, append to the list
            if v.get('metaDataValues').get('meta-arisguid'):
                aris_id = v.get('metaDataValues').get('meta-arisguid').replace("/", "_").replace("\\", "_").replace("\n", "_").replace("( &amp;", "_")
                data_exists, data = self.file_tracker.is_task_done(id=aris_id)
                if not data_exists:
                    data = {'json': v,
                            'signavio_id': k,
                            'category_id': v.get('category'),
                            'category_name': v.get('category_name'),
                            'creation_status': 'CREATED',
                            'creation_failed': False,
                            'has_linked_items': False,
                            'has_attributes_to_dict': False,
                            'needs_update': False,
                            'attribute_val_to_filter': ''}

                    self.file_tracker.save_task_results(id=aris_id, data=data, try_update=True)

    def get_all_new_entries(self):
        # These system attributes are not parsed as standard
        # "AT_CREATOR", "AT_CREATE_TIME_STMP", "AT_LAST_CHANG_2", "AT_USER"
        # Get Model ID and Model Data for every Model in the XML
        for model_id, model_data in self.amlquery.models.items():
            # check if model type is in defined scope of migration
            if model_data["type"] in self.model_types:
                # for all occurrences in a model get occurrence id an its data
                for occ_id, occ_data in model_data["occs"].items():
                    # Request the object definition of the occurrence
                    occ_def = self.amlquery.get_obj_def(occ_data)

                    # check if symbol type is in scope of object mapping (definition if dictionary entry or not)
                    if occ_data["symbol"] in self.object_mapping:
                        if occ_data["symbol"] == "ST_RISK_1":
                            print()
                        # check if it should be excluded
                        if occ_def["type"] not in self.excluded_obj_types:
                            # get attributes and linked objects
                            attributes, linked_items, attributes_to_dict, attribute_styles = self.attributeHandler.get_attributes_of_object(occ_data.get(
                                # ,self.object_mapping[occ_data.get('symbol')].get('dictionary_attributes_that_should_be_glossary_entries', {}))
                                'def'), occ_data, 'Dictionary')

                            occ_def['signavio_attributes'] = attributes
                            occ_def['linked_items'] = linked_items
                            occ_def['attributes_to_dict'] = attributes_to_dict

                            glossary_category = self.object_mapping[occ_data.get('symbol')].get('main_category')

                            # check glossary category of the dictionary item based on config
                            attribute_name_to_change_category_of_item = self.object_mapping[occ_data.get('symbol')].get(
                                'change_category_of_dictionary_item_based_on_attribute_name', '')
                            if attribute_name_to_change_category_of_item != '':
                                # check xml data for attributes directly for changing glossary category
                                attribute_value = occ_def.get('attrs', {}).get(attribute_name_to_change_category_of_item, '')
                                # set default main category if config doesn't exist
                                glossary_category = self.object_mapping[occ_data.get('symbol')].get('mapping_value_to_category', {}).get(
                                    attribute_value, self.object_mapping[occ_data.get('symbol')].get('main_category'))

                            # check second identifier
                            second_identifier = self.object_mapping[occ_data.get('symbol')].get('second_identifier', '')
                            attribute_value_to_filter = ''
                            if second_identifier:
                                attribute_value_to_filter = occ_def.get('signavio_attributes', {}).get(second_identifier, '')

                            #### NEW CODE ####
                            guid = occ_def.get('guid')
                            # check formats for attributes
                            signavio_formats = {}
                            attributes = occ_def.get('signavio_attributes', {})
                            attributes_for_format = {}
                            for attribute_name in self.list_of_attributes_to_check_formatting:
                                attr_multilang = {k: v for k, v in attributes.items() if k.startswith(attribute_name)}
                                attributes_for_format = {**attributes_for_format, **attr_multilang}

                            if attributes_for_format:
                                signavio_formats = self.prepare_formats_for_attributes(attributes_for_format, attribute_styles)

                            # Check if glossary item already exists in self.new_glossary_entries
                            if guid in self.new_glossary_entries:
                                existing_entry = self.new_glossary_entries[guid]
                                new_values = {
                                    'category': glossary_category,
                                    'linked_items': occ_def.get('linked_items', {}),
                                    'attributes_to_dict': occ_def.get('attributes_to_dict', {}),
                                    'signavio_attributes': occ_def.get('signavio_attributes', {}),
                                    'attribute_val_to_filter': attribute_value_to_filter,
                                    'formats': copy.deepcopy(signavio_formats)
                                }
                                titles = self.get_titles_from_name(occ_def.get('signavio_attributes', {}))
                                new_values = {**new_values, **titles}

                                # Update each field dynamically and assign back to self.new_glossary_entries
                                for key, new_value in new_values.items():
                                    existing_value = existing_entry.get(key)

                                    if isinstance(existing_value, dict) and isinstance(new_value, dict):
                                        # Merge dictionaries: only add new keys or update differing values
                                        merged_dict = {**existing_value}  # Copy existing dictionary
                                        for sub_key, sub_value in new_value.items():
                                            if merged_dict.get(sub_key) != sub_value:
                                                merged_dict[sub_key] = sub_value
                                        existing_entry[key] = merged_dict

                                    elif isinstance(existing_value, list) and isinstance(new_value, list):
                                        # If the values are lists, add unique new items
                                        existing_entry[key] = list(set(existing_value) | set(new_value))

                                    else:
                                        # For other types, replace only if the values differ
                                        if existing_value != new_value:
                                            existing_entry[key] = new_value

                                # Assign updated entry back to ensure all changes are saved
                                self.new_glossary_entries[guid] = copy.deepcopy(existing_entry)
                                #### NEW CODE END ####

                            else:
                                # Add glossary item to new_glossary_entries
                                titles = self.get_titles_from_name(occ_def.get('signavio_attributes', {}))
                                self.new_glossary_entries[occ_def.get('guid')] = {
                                    'aris_id': occ_def.get('guid'),
                                    'category': copy.deepcopy(glossary_category),
                                    'linked_items': occ_def['linked_items'],
                                    'attributes_to_dict': occ_def['attributes_to_dict'],
                                    'signavio_attributes': occ_def.get('signavio_attributes'),
                                    'attribute_val_to_filter': attribute_value_to_filter,
                                    'formats': copy.deepcopy(signavio_formats)
                                }
                                self.new_glossary_entries[occ_def.get('guid')] = {**self.new_glossary_entries[occ_def.get('guid')], **titles}

        # create Default pool dictionary item
        titles = {key: self.pool_name for key in self.title_keys}
        self.new_glossary_entries['GUID_Pool'] = {
            'title': self.pool_name,
            'aris_id': 'GUID_Pool',
            'category': self.glossary_category_to_create_pool,
            'linked_items': {},
            'attributes_to_dict': {},
            'signavio_attributes': {'description': 'Default Pool for Diagrams'},
            'attribute_val_to_filter': ''
        }
        self.new_glossary_entries['GUID_Pool'] = {**self.new_glossary_entries['GUID_Pool'], **titles}
        # Multiple Responsible Dictionary Item
        titles = {key: "Multiple Responsibles" for key in self.title_keys}
        self.new_glossary_entries['GUID_Multiple_Responsible'] = {
            'title': "Multiple Responsibles",
            'aris_id': 'GUID_Multiple_Responsible',
            'category': self.glossary_category_to_create_pool,
            'linked_items': {},
            'attributes_to_dict': {},
            'signavio_attributes': {'description': 'Default Multiple Responsible Dictionary Entry for Diagrams'},
            'attribute_val_to_filter': ''
        }
        self.new_glossary_entries['GUID_Multiple_Responsible'] = {**self.new_glossary_entries['GUID_Multiple_Responsible'], **titles}
        # Automation
        titles = {key: "Automation" for key in self.title_keys}
        self.new_glossary_entries['GUID_Automation'] = {
            'title': "Automation",
            'aris_id': 'GUID_Automation',
            'category': self.glossary_category_to_create_pool,
            'linked_items': {},
            'attributes_to_dict': {},
            'signavio_attributes': {'description': 'Default Automation Lane Dictionary Entry for Diagrams'},
            'attribute_val_to_filter': ''
        }
        self.new_glossary_entries['GUID_Automation'] = {**self.new_glossary_entries['GUID_Automation'], **titles}

    def create_entries(self):
        for aris_id, values in self.new_glossary_entries.items():
            attachments = values.get('signavio_attributes').get('attachments')
            description = values.get('signavio_attributes').get('description')
            meta_data_values = get_meta_data_values(values.get('signavio_attributes'), aris_id)
            signavio_formats = copy.deepcopy(values.get('formats'))

            titles = self.get_titles_and_description(values)
            
            if values.get('category') in ["/glossarycategory/ac2c63a7d1914bdd8f77738866297b83","/glossarycategory/9479410952484dbcb59dad06df4ba61d"]:
                description = ""
            #if values.get('category') in ["/glossarycategory/9479410952484dbcb59dad06df4ba61d"]: # If it is a Control
            #    if meta_data_values.get("meta-controlidentifier"):
            #        meta_data_values["meta-controlname"] = copy.deepcopy(values.get('title', ''))
            #        values['title'] = copy.deepcopy(meta_data_values.get("meta-controlidentifier", ""))
            #        del meta_data_values["meta-controlidentifier"]    
            
            data = {
                'force': True,
                'title': values.get('title', ''),
                'category': values.get('category'),
                'description': description or '',
                'attachments': attachments or '',
                'metaDataValues': json.dumps(meta_data_values),
                'formats': json.dumps(copy.deepcopy(signavio_formats)),
                'comment': 'Created in Migration Testing'
            }
            data = {**data, **titles}

            # data_values, data_exists = self.file_tracker.skip_task_or_data(aris_id)
            data_exists, data_values = self.file_tracker.is_task_done(id=aris_id)

            #### NEW CODE ####
            if data_exists:
                # Check if glossary item has changed since it was created in Signavio
                values['metaDataValues'] = meta_data_values
                values['description'] = description
                values['attachments'] = attachments  # data_values.get('json',{}).get('attachments', [])
                if not data_values.get('json'):  # means item creation failed before
                    data_exists = False
                else:
                    changed = self.data_changed(new_glossary_data=values, file_task_tracker_data=data_values)
                    if signavio_formats:
                        changed = True
                    if changed:
                        logger.info('-----------')
                        logger.info('Data has changed for glossary item: ' + aris_id)
                        # logger.info('New Glossary Item: ' + str(values))
                        # logger.info('File Task Tracker: ' + str(data_values))
                        logger.info('-----------')

                        additional_columns = {'signavio_id': '/glossary/' + data_values.get('json', {}).get('id'),
                                              'category_id': data.get('category'),
                                              'category_name': '',
                                              'creation_status': 'CREATED',
                                              'creation_failed': False,
                                              'has_linked_items': False,
                                              'has_attributes_to_dict': False,
                                              'needs_update': True,
                                              'attribute_val_to_filter': values.get('attribute_val_to_filter')}

                        values['id'] = data_values.get('json', {}).get('id')

                        if values.get('linked_items'):
                            data_stored = {
                                'json': values,
                                'items': values.get('linked_items'),
                                'attributes_to_dict': values.get('attributes_to_dict')
                            }
                            additional_columns['has_linked_items'] = True
                            if values.get('attributes_to_dict'):
                                additional_columns['has_attributes_to_dict'] = True
                        else:
                            if values.get('attributes_to_dict'):
                                data_stored = {
                                    'json': values,
                                    'attributes_to_dict': values.get('attributes_to_dict')
                                }
                                additional_columns['has_attributes_to_dict'] = True
                            else:
                                data_stored = {
                                    'json': values
                                }

                        data_stored = {**data_stored, **additional_columns}
                        self.file_tracker.save_task_results(id=aris_id, data=data_stored, try_update=True)

            #### NEW CODE END ####

            if not data_exists:
                response = self._spm.dictionary.create_new_entry(data=data)
                errors = None
                if response:
                    errors = response.get('errors', None)
                if response is None or errors is not None:
                    additional_columns = {'signavio_id': None,
                                          'category_id': data.get('category'),
                                          'category_name': data.get('categoryName'),
                                          'creation_status': 'FAILED',
                                          'creation_failed': True,
                                          'has_linked_items': False,
                                          'has_attributes_to_dict': False,
                                          'needs_update': False,
                                          'attribute_val_to_filter': values.get('attribute_val_to_filter')
                                          }

                    if values.get('linked_items'):
                        additional_columns['has_linked_items'] = True
                        additional_columns['needs_update'] = True
                        data['items'] = values.get('linked_items')

                    if values.get('attributes_to_dict'):
                        additional_columns['has_attributes_to_dict'] = True
                        additional_columns['needs_update'] = True
                        data['attributes_to_dict'] = values.get('attributes_to_dict')

                    logger.error('Dictionary Handler - Entry Creation: Creation of ' + aris_id + ' failed: ' + str(errors))

                    data = {**data, **additional_columns}
                    self.file_tracker.save_task_results(id=aris_id, data=data, try_update=True)
                else:
                    additional_columns = {'signavio_id': '/glossary/' + response.get('rep').get('id'),
                                          'category_id': response.get('rep').get('category'),
                                          'category_name': response.get('rep', {}).get('categoryName'),
                                          'creation_status': 'CREATED',
                                          'creation_failed': False,
                                          'has_linked_items': False,
                                          'has_attributes_to_dict': False,
                                          'needs_update': False,
                                          'attribute_val_to_filter': values.get('attribute_val_to_filter')}
                    if values.get('linked_items'):
                        data_stored = {
                            'json': response.get('rep'),
                            'items': values.get('linked_items'),
                            'attributes_to_dict': values.get('attributes_to_dict')
                        }
                        additional_columns['has_linked_items'] = True
                        if values.get('attributes_to_dict'):
                            additional_columns['has_attributes_to_dict'] = True
                        additional_columns['needs_update'] = True
                    else:
                        if values.get('attributes_to_dict'):
                            data_stored = {
                                'json': response.get('rep'),
                                'attributes_to_dict': values.get('attributes_to_dict')
                            }
                            additional_columns['has_attributes_to_dict'] = True
                            additional_columns['needs_update'] = True
                        else:
                            data_stored = {
                                'json': response.get('rep')
                            }
                    data_stored = {**data_stored, **additional_columns}
                    self.file_tracker.save_task_results(id=aris_id, data=data_stored, try_update=True)

    def update_entries(self):
        db = self.file_tracker.dbu.read(model_class=table_definitions.DictionaryEntries, multiple=True)

        for item in db:
            item = self.file_tracker.read_file(os.path.join(self.file_tracker.track_file_path,
                                               item.relative_file_path), file_name_is_path=True)

            if item.get('creation_status', '') != 'FAILED' and item.get('needs_update', ''):
                # file = self.file_tracker.data_from_file(item.id)
                gitem_json = copy.deepcopy(item.get('json', {}))
                item_to_update = item.get('signavio_id', '')
                logger.info('Item to update: ' + item_to_update)
                # Add linked items

                meta_data_values = copy.deepcopy(gitem_json.get('metaDataValues', {}))
                if item.get('has_linked_items', ''):
                    for k, v in item.get('items').items():
                        if type(v) is list:
                            value = []
                            for x in v:
                                data_exists, record = self.file_tracker.is_task_done(id=x)
                                if data_exists:
                                    value.append(record.get('signavio_id', ''))
                                else:
                                    logger.error(
                                        f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {x} for key : {k}")
                        else:
                            data_exists, value = self.file_tracker.is_task_done(id=v)
                            if data_exists:
                                value = value.get('signavio_id', '')
                            else:
                                logger.error(
                                    f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {v} for key : {k}")

                        if value is not None and value != []:
                            meta_data_values[k] = value

                # Add Attributes to dict
                if item.get('has_attributes_to_dict', '') and item.get('attributes_to_dict'):
                    for k, v in item.get('attributes_to_dict').items():
                        value = None
                        category = v.get('categories_to_check', '')
                        # txt drop down to dictionary item creation
                        if k in self.create_dictionary_entry_from_attribute:
                            # check whether item exists
                            id_to_search = v.get('value')
                            if self.create_dictionary_entry_from_attribute[k].get(id_to_search, {}).get('category', '') == self.process_specific_roles_glossary_category:
                                id_to_search = id_to_search.lower()

                            data_exists, value = self.file_tracker.is_task_done(id=id_to_search)
                            if not data_exists:
                                # create new item
                                aris_id = id_to_search
                                # If process specific roles add meta-emailaddress to metadatavalues
                                if self.create_dictionary_entry_from_attribute[k].get(id_to_search, {}).get('category', '') == self.process_specific_roles_glossary_category:
                                    aris_id = id_to_search.lower()
                                    meta_data_values_item_to_create = get_meta_data_values({"meta-emailaddress": aris_id}, aris_id)
                                else:
                                    meta_data_values_item_to_create = get_meta_data_values({}, aris_id)

                                data = {
                                    'force': True,
                                    'title': self.create_dictionary_entry_from_attribute[k].get(id_to_search, {}).get('name', ''),
                                    'category': self.create_dictionary_entry_from_attribute[k].get(id_to_search, {}).get('category', ''),
                                    'description': '',
                                    'attachments': '',
                                    'metaDataValues': json.dumps(meta_data_values_item_to_create),
                                    'comment': 'Created in Migration Testing'
                                }
                                titles = self.get_titles_from_name(self.create_dictionary_entry_from_attribute[k].get(id_to_search, {}))
                                data = {**data, **titles}
                                self.new_glossary_entries[id_to_search] = {
                                    'title': self.create_dictionary_entry_from_attribute[k].get(value, {}).get('name', ''),
                                    'aris_id': aris_id,
                                    'category': self.create_dictionary_entry_from_attribute[k].get(value, {}).get('category', ''),
                                    'linked_items': [],
                                    'attributes_to_dict': {},
                                    'signavio_attributes': '',
                                    'attribute_val_to_filter': ''
                                }
                                titles = self.get_titles_from_name(self.create_dictionary_entry_from_attribute[k].get(value, {}))
                                self.new_glossary_entries[id_to_search] = {**self.new_glossary_entries[id_to_search], **titles}
                                result, signavio_id = self.create_new_entry(data, aris_id, aris_id)
                                if result is True:
                                    if signavio_id is not None and isinstance(signavio_id, str) and '/glossary/' in signavio_id:
                                        value = signavio_id
                                    else:
                                        logger.error(
                                            f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {v} for key : {k}")
                            else:  # value exists
                                value = value.get('signavio_id', '')

                        elif v.get('value', '') != '':
                            final_list = None
                            if isinstance(v.get('value', ''), list):
                                final_list = []
                                for val in v.get('value', ''):
                                    item_to_create = copy.deepcopy(val.strip())
                                    if category == self.process_specific_roles_glossary_category:
                                        item_to_create = item_to_create.lower()

                                    data_exists, value = self.file_tracker.is_task_done(id=item_to_create)

                                    if not data_exists or value.get('creation_status', '') == 'FAILED':
                                        # searched db via aris_id and couldnt find the item need to create the item
                                        # ex. read email attribute and then map it to correct org unit element
                                        # if dict item doesnt exist, create new one
                                        # create new item
                                        value = self.search_db_via_attr_and_create_new(item_to_create, category, item, final_list, k, v)

                                    else:
                                        if value:
                                            if value.signavio_id not in final_list:
                                                final_list.append(value.signavio_id)
                            else:  # str
                                item_to_create = copy.deepcopy(v.get('value', '').strip())
                                if category == self.process_specific_roles_glossary_category:
                                    item_to_create = item_to_create.lower()

                                data_exists, value = self.file_tracker.is_task_done(id=item_to_create)

                                if not data_exists or not value:
                                    # searched db via attribute_val_to_filter and couldnt find the item
                                    # need to create the item ex. read email attribute and then map it to correct org unit element
                                    # if dict item doesnt exist, create new item
                                    value = self.search_db_via_attr_and_create_new(item_to_create, category, None, None, None, None)

                            if final_list is None or final_list == []:
                                if value is not None and not isinstance(value, str):
                                    if not isinstance(value, list):
                                        if isinstance(value, dict) :
                                             value = value.get("signavio_id","" ) 
                                        else:
                                            value = value.signavio_id
                                    elif isinstance(value, list) and len(value) == 1:
                                        if isinstance(value[0], dict):
                                            value = value[0].get("signavio_id","" )
                                        else:
                                            value = value[0].signavio_id
                                    elif isinstance(value, list) and len(value) > 1:
                                        if value != []:
                                            logger.error(
                                                f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {v} for key : {k} Multiple values exist to link attribute to dictionary item. Values: {value}. Mapping first item in the list: {value[0]}")
                                            if isinstance(value[0], dict):
                                                value = value[0].get("signavio_id","" )
                                            else:
                                                value = value[0].signavio_id
                                else:
                                    logger.error(
                                        f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {v} for key : {k}")
                            else:
                                value = final_list

                        if value is not None and value != []:
                            attribute_name = v.get('signavio_attribute_name', '')
                            if attribute_name in meta_data_values:
                                if isinstance(meta_data_values[attribute_name], list):
                                    if isinstance(value, list):
                                        meta_data_values[attribute_name].extend(value)
                                        meta_data_values[attribute_name] = list(set(meta_data_values[attribute_name]))
                                    else:
                                        if value not in meta_data_values[attribute_name]:
                                            meta_data_values[attribute_name].append(value)
                            else:
                                meta_data_values[attribute_name] = value

                # Update if data has changed
                if not item.get('has_attributes_to_dict', '') and not item.get('has_linked_items', ''):
                    entry = self.dictionary_content.get(item_to_update)
                    # todo: adjust with configuration
                    if not entry:
                        logger.error(f"Dictionary Handler - Update Entries: {item.get('json', {}).get('aris_id', '')} "
                                     f"error while updating: Could not find existing entry in Signavio to update")
                        continue
                    # print(item_to_update + ' : '  + str(entry))
                    metaData_signavio = transform_metaDataValues(entry.get('metaDataValues', {}))
                    metaData_filetracker = gitem_json.get('metaDataValues', {})

                    harmonized_metaDataValues = harmonize_metaDataValues(metaData_filetracker, metaData_signavio)

                    data = {
                        'force': True,
                        'title': gitem_json.get('title', ''),
                        'category': gitem_json.get('category', ''),
                        'description': gitem_json.get('description', ''),
                        'attachments': '',
                        'metaDataValues': json.dumps(harmonized_metaDataValues),
                        'formats': json.dumps(gitem_json.get('formats', '')),
                        'comment': 'Created in Migration Testing'
                    }
                    # get titles
                    titles = self.get_titles_and_description(gitem_json)
                    data = {**data, **titles}
                    gitem_json = data

                    logger.info(item_to_update)
                    logger.info(str(gitem_json))

                else:
                    # format metadata values
                    for key in meta_data_values:
                        formatted_property = self.attributeHandler.get_property_in_correct_format(key, meta_data_values[key], 'Dictionary')
                        meta_data_values.update(formatted_property)
                    gitem_json['metaDataValues'] = json.dumps(meta_data_values)
                    data = {
                        'force': True,
                        'title': gitem_json.get('title', ''),
                        'category': gitem_json.get('category', ''),
                        'description': gitem_json.get('description', ''),
                        'attachments': '',
                        'formats': json.dumps(gitem_json.get('formats', '')),
                        'metaDataValues': json.dumps(meta_data_values),
                        'comment': 'Created in Migration Testing'
                    }
                    titles = self.get_titles_and_description(gitem_json)
                    data = {**data, **titles}
                    gitem_json = copy.deepcopy(data)

                if gitem_json.get('category', '') in ["/glossarycategory/ac2c63a7d1914bdd8f77738866297b83","/glossarycategory/9479410952484dbcb59dad06df4ba61d"]:
                    gitem_json["description"] = ""

                #if gitem_json.get('category') in ["/glossarycategory/9479410952484dbcb59dad06df4ba61d"]: # If it is a Control
                #    if gitem_json.get('metaDataValues', {}).get("meta-controlidentifier"):
                #        gitem_json.get('metaDataValues', {})["meta-controlname"] = copy.deepcopy(gitem_json.get('title', ''))
                #        gitem_json['title'] = copy.deepcopy(gitem_json.get('metaDataValues', {}).get("meta-controlidentifier", ""))
                #        del gitem_json.get('metaDataValues', {})["meta-controlidentifier"] 

                response = self._spm.dictionary.update_entry(item_to_update, gitem_json)
                if response:
                    if response.get('error') or response.get('errors') or response.get('id') is None:
                        logger.error(
                            'Dictionary Handler - Update Entries: ' + item.get('json', {}).get('aris_id', '') + ' error while updating: ' + str(
                                response.get('errors')))
                    else:
                        additional_columns = {'signavio_id': '/glossary/' + response.get('id'),
                                              'category_id': response.get('category'),
                                              'category_name': response.get('rep', {}).get('categoryName'),
                                              'creation_status': 'UPDATED',
                                              'creation_failed': False,
                                              'has_linked_items': False,
                                              'needs_update': False,
                                              'has_attributes_to_dict': False,
                                              'attribute_val_to_filter': item.get('attribute_val_to_filter', '')}

                        data_stored = {
                            'json': response
                        }
                        data_stored = {**data_stored, **additional_columns}
                        # self.file_tracker.results_to_file(id=item.id, data=data_stored,
                        #                                  additional_columns=additional_columns)
                        self.file_tracker.save_task_results(id=item.get('json', {}).get('aris_id', ''), data=data_stored, try_update=True)
                else:
                    logger.error("Dictionary Handler - Update Entries: ' + item.get('json', {}).get('aris_id', '') + ' error while updating")

    def search_db_via_attr_and_create_new(self, item_to_create, dictionary_category, dict_item, final_list, k, v):
        # searched db via aris_id and couldnt find the item need to create the item
        # ex. read email attribute and then map it to correct org unit element
        # if dict item doesnt exist, create new one
        # create new item
        value = None
        aris_id = item_to_create
        # If process specific roles add meta-emailaddress to metadatavalues
        if dictionary_category == self.process_specific_roles_glossary_category:
            aris_id = item_to_create.lower()
            meta_data_values_item_to_create = get_meta_data_values({"meta-emailaddress": aris_id}, aris_id)
        else:
            meta_data_values_item_to_create = get_meta_data_values({}, aris_id)  # set aris id as the items attr_val to search for

        titles = {key: aris_id for key in self.title_keys}
        data = {
            'force': True,
            'title': aris_id,
            'category': dictionary_category,
            'description': '',
            'attachments': '',
            'metaDataValues': json.dumps(meta_data_values_item_to_create),
            'comment': 'Created in Migration Testing'
        }
        data = {**data, **titles}
        self.new_glossary_entries[aris_id] = {
            'title': aris_id,
            'aris_id': aris_id,
            'category': dictionary_category,
            'linked_items': {},
            'attributes_to_dict': {},
            'signavio_attributes': '',
            'attribute_val_to_filter': item_to_create
        }
        self.new_glossary_entries[aris_id] = {**self.new_glossary_entries[aris_id], **titles}
        result, signavio_id = self.create_new_entry(data, aris_id, aris_id)
        if result is True:
            if signavio_id is not None and isinstance(signavio_id, str) and '/glossary/' in signavio_id:
                value = signavio_id
                if final_list is not None and value not in final_list:
                    final_list.append(value)
            else:
                if dict_item is not None:
                    logger.error(
                        f"Dictionary Handler - Update Entries: {dict_item.get('json', {}).get('aris_id', '')}. Could not link an item cant find in DB, id: {v} for key : {k}")

        return value

    def create_new_entry(self, data, aris_id, attribute_val_to_filter=''):

        data_exists, data_values = self.file_tracker.is_task_done(id=aris_id)

        if data_values:
            if not data_values.get('json'):  # means item creation failed before
                data_exists = False
        if not data_exists:
            response = self._spm.dictionary.create_new_entry(data=data)
            if response.get('errors'):
                additional_columns = {'signavio_id': None,
                                      'category_id': data.get('category'),
                                      'category_name': data.get('categoryName'),
                                      'creation_status': 'FAILED',
                                      'creation_failed': True,
                                      'has_linked_items': False,
                                      'has_attributes_to_dict': False,
                                      'needs_update': False,
                                      'attribute_val_to_filter': attribute_val_to_filter
                                      }

                logger.error("Dictionary Handler - Entry Creation: Creation of " + aris_id + "failed.")
                data = {**data, **additional_columns}
                self.file_tracker.save_task_results(id=aris_id, data=data, try_update=True)
                return False, None
            else:
                additional_columns = {'signavio_id': '/glossary/' + response.get('rep').get('id'),
                                      'category_id': response.get('rep').get('category'),
                                      'category_name': response.get('rep', {}).get('categoryName'),
                                      'creation_status': 'CREATED',
                                      'creation_failed': False,
                                      'has_linked_items': False,
                                      'has_attributes_to_dict': False,
                                      'needs_update': False,
                                      'attribute_val_to_filter': attribute_val_to_filter
                                      }

                data_stored = {
                    'json': response.get('rep')
                }
                data_stored = {**data_stored, **additional_columns}
                self.file_tracker.save_task_results(id=aris_id, data=data_stored, try_update=True)
                signavio_id = '/glossary/' + response.get('rep').get('id')
                return True, signavio_id
        else:
            data_exists, record = self.file_tracker.is_task_done(id=aris_id)
            if record.get('creation_failed', ''):
                logger.error('Dictionary Handler - Retry Creation: Creation of ' + aris_id)
                return False, None
            else:
                if record.get('signavio_id', ''):
                    signavio_id = record.get('signavio_id', '')
                else:
                    signavio_id = None
                return True, signavio_id

    def get_titles_from_name(self, data):
        names = {k: v for k, v in data.items() if k.startswith("name")}
        titles = {
            ("title" + key[4:]) if key.startswith("name") else key: value
            for key, value in names.items()
        }

        return titles

    def get_titles_and_description(self, data):
        titles = {k: v for k, v in data.items() if k.startswith('title')}
        description = {k: v for k, v in data.items() if k.startswith('description')}
        result = {**titles, **description}
        return result

    def prepare_formats_for_attributes(self, attribute_dict, attribute_styles):
        formats = {}

        for attribute_name in attribute_dict:
            # get style for the attribute name
            attr_text = ''
            if attribute_styles.get(attribute_name):
                attr_text = copy.deepcopy(attribute_styles.get(attribute_name))
            if not attr_text:
                attr_text = copy.deepcopy(attribute_dict[attribute_name])
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
                if tag == 'font':
                    print()
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

    def reorder_tags(self, tags):
        """
        Reorder a list of tag dictionaries based on 'from' index and tag priority.

        Args:
            tags (list): List of dictionaries with 'from', 'tag', and 'to' keys.

        Returns:
            list: Reordered list of tag dictionaries.
        """
        # Define tag priorities
        tag_priority = {
            'br': 1,
            'ul': 2,
            'ol': 2,
            'li': 3
        }

        # Assign a default high priority to tags not in the priority list
        default_priority = 100

        # Sort the list based on 'from' index and tag priority
        sorted_tags = sorted(
            tags,
            key=lambda x: (x['from'], tag_priority.get(x['tag'], default_priority))
        )

        return sorted_tags

    def data_changed(self, new_glossary_data, file_task_tracker_data):
        # Helper function to determine if two values are effectively equal

        def is_equal(val1, val2):
            # Consider None, empty strings, empty lists, and empty dictionaries as equal
            if val1 in [None, '', [], {}] and val2 in [None, '', [], {}]:
                return True
            return val1 == val2

        # Normalize the relevant fields from file_task_tracker_data for comparison

        file_data = file_task_tracker_data['json']
        file_data_normalized = {
            'title': file_data.get('title'),
            'category': file_data.get('category'),
            'description': file_data.get('description'),
            'metaDataValues': file_data.get('metaDataValues', {}),
            'attributes_to_dict': file_task_tracker_data.get('attributes_to_dict', {}),
            'linked_items': file_task_tracker_data.get('items', [])
        }
        titles_desc = self.get_titles_and_description(file_data)
        file_data_normalized = {**file_data_normalized, **titles_desc}

        changes = []

        # Compare simple fields
        fields = ['title', 'category', 'description', 'linked_items']
        fields = list(set(fields) | set(self.title_keys) | set(self.description_keys))

        for field in fields:
            if not is_equal(new_glossary_data.get(field), file_data_normalized.get(field)):
                changes.append(
                    f"Field '{field}' changed: {new_glossary_data.get(field)} != {file_data_normalized.get(field)}")

        # Compare dictionaries (metaDataValues and attributes_to_dict)
        for dict_field in ['metaDataValues', 'attributes_to_dict']:
            dict1 = new_glossary_data.get(dict_field, {})
            dict2 = file_data_normalized.get(dict_field, {})

            # Check for differences in keys and values
            keys1, keys2 = set(dict1.keys()), set(dict2.keys())
            if keys1 != keys2:
                missing_in_dict2 = keys1 - keys2
                missing_in_dict1 = keys2 - keys1
                if missing_in_dict2:
                    changes.append(f"Keys missing in file's {dict_field}: {missing_in_dict2}")
                if missing_in_dict1:
                    changes.append(f"Keys missing in glossary's {dict_field}: {missing_in_dict1}")

            # Check for differences in values for matching keys
            for key in keys1.intersection(keys2):
                if not is_equal(dict1[key], dict2[key]):
                    changes.append(f"Value for key '{key}' in {dict_field} changed: {dict1[key]} != {dict2[key]}")

        if changes:
            logger.info("Changes detected:")
            for change in changes:
                logger.info(f" - {change}")
            return True

        return False

    def new_line_formatting(self, text):
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

    def create_dictionary_entries(self):
        logger.info('Start Dictionary Handler Started')
        self.get_all_new_entries()
        logger.info('All new entries are parsed')
        self.create_entries()
        logger.info('All new entries are created. Starting update, linked items')
        self.update_entries()
        logger.info('All entries are updated! Dictionary Handler Finished')


def get_meta_data_values(attributes, aris_id):
    result = {}
    if attributes:
        for k, v in attributes.items():
            if 'meta-' in k:
                result[k] = v
    result['meta-arisguid'] = aris_id
    return result


def transform_metaDataValues(input_data):
    # adds /glssary/ before id and removes unrequired data
    output_data = {}

    for key, value in input_data.items():
        if isinstance(value, dict):
            if 'id' in value:
                output_data[key] = f"/glossary/{value['id']}"
            else:
                output_data[key] = value
        elif isinstance(value, list):
            output_data[key] = [f"/glossary/{item['id']}" for item in value if isinstance(item, dict) and 'id' in item]
        else:
            output_data[key] = value

    return output_data


def harmonize_metaDataValues(dict_file_tracker, dict_signavio):
    # adds missing keys to metaDataValues
    combined_dict = {}

    all_keys = set(dict_file_tracker.keys()).union(set(dict_signavio.keys()))

    for key in all_keys:
        combined_dict[key] = dict_file_tracker.get(key, '')

    return combined_dict

import json
import yaml

from ..base_api import BaseApi
from ..spm.directory import Directory
from ..spm.model import Model
from ..spm.dictionary import Dictionary


class Utils(BaseApi):

    def get_replaced_item_dict(self, categories: list):
        '''
        :descriptin : for given list of categories return a mapping Replaced Item ID -> Head ID of Glossary Item
        :param categories: list
        :return: replaced_items: dict
        '''
        gitems = {}

        if not isinstance(categories, list):
            raise TypeError("Parameter categories should be type of list.")

        # get all items from given categories
        for category in categories:
            tmp = Dictionary.get_all_entries_of_category(self, category)
            for item in tmp:
                gitems[item['href']] = item

        # iterate all items
        replaced_items = {}
        for item in gitems:
            # get replaced item id's if any
            replaced_ids = gitems[item]['rep']['replacedItemIds']
            # iterate the id's if any
            for replaced_id in replaced_ids:
                # add to the replaced_items dict key: replaced item value: current id
                replaced_items[replaced_id] = gitems[item]['href'].replace('/glossary/', '')

        return replaced_items

    def get_published_and_latest_revision(self, directories_model):

        published_revision_id = directories_model['rep'].get('granted_revision', None)
        latest_revision_id = directories_model['rep'].get('revision', None)

        result = {}
        if latest_revision_id and published_revision_id != latest_revision_id:
            latest_revision_json = Model.get_revision_json(self, latest_revision_id)
            result['latest_revision'] = latest_revision_json

        if published_revision_id:
            published_revision_json = Model.get_revision_json(self, published_revision_id)
            result['published_revision'] = published_revision_json

        return result

    def get_all_sub_directories(self, directory, directories=[]):

        directory = Directory.get_content(self, directory_id=directory)

        for item in directory:

            if item['rel'] == 'dir':
                directories.append(item)
                self.get_all_sub_directories(item['href'], directories)

        return directories

    def get_directories_and_models(self, dir=None, model_filter=[], recursive=True, models=[],
                                   directories=[], excluded_directories=[], index=0):
        if not dir:
            dir = Directory.get_root_folder_content(self)
            dir = dir[0]['href']
        if dir not in excluded_directories:
            # todo: replace print with logger
            print('SEARCH CONTENT IN DIRECTORY: ' + dir)
            directory = Directory.get_content(self, dir)
            for item in directory:
                if item['rel'] == 'mod':
                    item['level'] = index
                    if model_filter:
                        if item['rep']['namespace'] in model_filter:
                            models.append(item)
                    else:
                        models.append(item)
                if item['rel'] == 'dir':
                    directories.append(item)
                if recursive:
                    if item['rel'] == 'dir':
                        self.get_directories_and_models(item['href'], model_filter, True, models, directories,
                                                        excluded_directories, index + 1)
        return models, directories

    def get_directories_models(self, dir=None, model_filter=[], recursive=True, models=[], excluded_directories=[],
                               index=0):
        if not dir:
            dir = Directory.get_root_folder_content(self)
            dir = dir[0]['href']
        if dir not in excluded_directories:
            print('SEARCH CONTENT IN DIRECTORY: ' + dir)
            directory = Directory.get_content(self, dir)
            for item in directory:
                if item['rel'] == 'mod':
                    item['level'] = index
                    if model_filter:
                        if item['rep']['namespace'] in model_filter:
                            models.append(item)
                    else:
                        models.append(item)
                if recursive:
                    if item['rel'] == 'dir':
                        self.get_directories_models(item['href'], model_filter, True, models,
                                                    excluded_directories, index + 1)
        return models

    def __search_in_meta(self, ci_id, meta_id, meta, inverse=False):
        found = False
        for m in meta:
            if m['rep']['id'] == meta_id:
                found = True
                if m['rep'].get('items'):
                    for item in m['rep']['items']:
                        if inverse:
                            if item['title'].lower() == ci_id.lower():
                                return item['id']
                        else:
                            if item['id'].lower() == ci_id.lower():
                                return item['title']
                    print(ci_id, 'not found in', meta_id)
                    return ci_id
                elif m['rep'].get('complexItems'):
                    for complex_item in m['rep']['complexItems']:
                        if complex_item.get('items'):
                            for item in complex_item['items']:
                                if item['id'] == ci_id:
                                    return item['title']
                else:
                    return ci_id
                break
        if not found:
            return ci_id

    def __helper_search_in_meta(self, ci_id, meta_id, meta):
        if ci_id:
            return self.__search_in_meta(ci_id, meta_id, meta)
        else:
            return ci_id

    def get_value_from_attribute_title(self, key, value, meta):
        return self.__search_in_meta(value, key, meta, inverse=True)

    def get_title_from_attribute_value(self, key, value, meta):
        if isinstance(value, list) and value:
            if isinstance(value[0], dict):
                if value[0].get('url'):
                    result = [url.get('url', '') for url in value]
                    return ','.join(result)
                elif value[0].get('title'):
                    result = [title.get('title', '') for title in value]
                    return ','.join(result)
                else:
                    return json.dumps(value)
        elif isinstance(value, dict) and value:
            if value.get('url'):
                return value['url']
            elif value.get('title'):
                return value['title']
            else:
                return json.dumps(value)
        else:
            return self.__helper_search_in_meta(value, key, meta)

    def get_all_shapes_with_stencil(self, shape, results, stencils=[], inverse=False):
        if shape.get('childShapes'):
            for child in shape['childShapes']:
                self.get_all_shapes_with_stencil(child, results, stencils, inverse)

        if len(stencils) > 0:
            if not inverse:
                if shape['stencil']['id'] in stencils:
                    results.append(shape)
            else:
                if shape['stencil']['id'] not in stencils:
                    results.append(shape)
        else:
            results.append(shape)
        return results

    def remove_non_gitems(self, list):
        for item in list:
            if item['rel'] != 'gitem':
                list.remove(item)
        return list

    def read_additional_project_config(self, config_file_path):
        with open(config_file_path) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        return config

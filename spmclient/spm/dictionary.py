import urllib

from ..base_api import BaseApi


class Dictionary(BaseApi):
    def get_all_categories(self, optional_id=''):

        if '/glossarycategory/' in optional_id:
            optional_id = optional_id.split('/glossarycategory/')[1]

        url = self._client.host + '/p/glossarycategory/' + optional_id

        return self._client.request_json('GET', url)

    def get_category(self, category_id):

        if '/glossarycategory/' in category_id:
            url = self._client.host + '/p' + category_id + '/info/'
        else:
            url = self._client.host + '/p/glossarycategory/' + category_id + '/info/'

        return self._client.request_json('GET', url)

    def get_all_entries_of_category(self, category_id, limit=1000, offset=0):

        if '/glossarycategory/' in category_id:
            base_url = self._client.host + '/p/glossary?category=' + category_id.split('/glossarycategory/')[1]
        else:
            base_url = self._client.host + '/p/glossary?category=' + category_id

        local_category = []
        base_url = base_url + '&sort=title'
        max_items = 1
        while offset < max_items:
            url = base_url + '&limit=' + str(limit) + '&offset=' + str(offset)
            category_part = self._client.request_json('GET', url)
            if category_part[-1]['rel'] == 'info':
                max_items = category_part[-1]['rep']['size']
                del category_part[-1]
            local_category.extend(category_part)
            offset = offset + limit

        return local_category

    def get_entry_rel_info(self, entry_id):

        if '/glossary/' in entry_id:
            url = self._client.host + '/p' + entry_id + '/info/'
        else:
            url = self._client.host + '/p/glossary/' + entry_id + '/info/'

        return self._client.request_json('GET', url)

    def get_entry_rel_link(self, entry_id):

        if '/glossary/' in entry_id:
            url = self._client.host + '/p' + entry_id + '/link/'
        else:
            url = self._client.host + '/p/glossary/' + entry_id + '/link/'

        return self._client.request_json('GET', url)

    def create_new_entry(self, data):

        url = self._client.host + '/p/glossary/'

        return self._client.request_json('POST', url=url, data=data)

    def update_entry(self, entry_id, data):

        if '/glossary/' not in entry_id:
            entry_id = '/glossary/' + entry_id

        url = self._client.host + '/p' + entry_id + '/info'

        return self._client.request_json('PUT', url, data)

    def update_entry_with_query(self, entry_id, data):

        if '/glossary/' not in entry_id:
            entry_id = '/glossary/' + entry_id

        url = self._client.host + '/p' + entry_id + '/info?' + urllib.parse.urlencode(data, doseq=True)

        return self._client.request_json('PUT', url)

    def delete_entry(self, entry_id):

        if '/glossary/' not in entry_id:
            entry_id = '/glossary/' + entry_id

        url = self._client.host + '/p' + entry_id

        return self._client.request_json('DELETE', url)

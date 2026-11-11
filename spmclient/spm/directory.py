from ..base_api import BaseApi
import html


class Directory(BaseApi):
    def get_root_folder_content(self):

        url = self._client.host + '/p/directory'

        return self._client.request_json('GET', url)

    def get_content(self, directory_id):

        if '/directory/' in directory_id:
            url = self._client.host + '/p' + directory_id
        else:
            url = self._client.host + '/p/directory/' + directory_id

        url = url + '?contentmode=explorer'

        return self._client.request_json('GET', url)

    def get_info(self, directory_id):

        if '/directory/' in directory_id:
            url = self._client.host + '/p' + directory_id + '/info'
        else:
            url = self._client.host + '/p/directory/' + directory_id + '/info'

        return self._client.request_json('GET', url)

    def create(self, name, parent, desc=''):

        url = self._client.host + '/p/directory'

        if '/directory/' not in parent:
            parent = '/directory/' + parent

        body = {
            'name': html.unescape(name),
            'description': desc,
            'parent': parent
        }

        return self._client.request_json('POST', url, body)

    def update(self, directory_id, name, parent, desc='', name_translations={}):
        """
        Updates the information of an existing directory in the system.

        For name_translations use the language codes with the respective names:

        {
            "name_de_de": "Deutscher Name",
            "name_en_gb": "British Name",
            ...
        }

        Args:
            directory_id (str): The unique identifier of the directory to update.
            name (str): The new name for the directory.
            parent (str): The unique identifier of the parent directory. 
            desc (str, optional): A description of the directory. Defaults to ''.
            name_translations (dict, optional): A dictionary of translated names for 
                                                the directory, where keys are 
                                                language codes and values are the 
                                                translated names. Defaults to {}.

        Returns:
            dict: A dictionary containing the updated directory information,
                mirroring the structure of the data sent in the request.
        """

        if '/directory/' not in directory_id:
            directory_id = '/directory/' + directory_id

        url = self._client.host + '/p' + directory_id + '/info'

        if '/directory/' not in parent:
            parent = '/directory/' + parent

        body = {
            'name': html.unescape(name),
            'description': desc,
            'parent': parent,
            **name_translations
        }

        return self._client.request_json('PUT', url, body)

    def move(self, directory_id, parent):

        if '/directory/' not in directory_id:
            directory_id = '/directory/' + directory_id

        url = self._client.host + '/p' + directory_id

        if '/directory/' not in parent:
            parent = '/directory/' + parent

        body = {
            'parent': parent
        }

        return self._client.request_json('PUT', url, body)

    def create_multilang(self, name, name_translations, parent, desc=''):

        create_data = self.create(
            name=name,
            parent=parent,
            desc=desc
        )

        if not create_data.get("href"):
            return None

        update_res = self.update(
            directory_id=create_data["href"],
            name=name,
            parent=parent,
            desc=desc,
            name_translations=name_translations
        )

        if not update_res.get("parent"):
            return None

        return create_data

import os

from ..base_api import BaseApi


class File(BaseApi):
    def get_content(self, file_id):

        if '/file/' in file_id:
            if 'https://editor.signavio.com/p/file/' in file_id:
                url = file_id
            else:
                url = self._client.host + '/p' + file_id + '/content'
        else:
            url = self._client.host + '/p/file/' + file_id + '/content'

        return self._client.request_data('GET', url)

    def get_info(self, file_id):

        if '/file/' in file_id:
            if '/content' in file_id:
                url = file_id.split('/content')[0] + '/info'
            else:
                url = self._client.host + '/p' + file_id + '/info'
        else:
            url = self._client.host + '/p/file/' + file_id + '/info'

        return self._client.request_json('GET', url)

    def upload_file(self, file):
        pass

    def import_bpmn_xml(self, file_path, directory):
        """
        Imports a BPMN (.bpmn) file into the specified directory.

        This method reads a BPMN XML file and uploads it to the server using
        a POST request.

        Parameters
        ----------
        file_path : str
            The path to the BPMN XML file to be imported.
        directory : str
            The target directory where the file should be stored.

        Returns
        -------
        dict
            A response dictionary containing the model ID.

        Raises
        ------
        IOError
            If the file cannot be read.
        RequestException
            If the request to the server fails.
        """
        url = self._client.host + "/p/bpmn2_0-import"
        file_name = os.path.basename(file_path)

        with open(file_path, 'r', encoding='utf-8') as file_import_stream:
            file_import_str = file_import_stream.read()

        files = {'bpmn2_0file': (file_name, file_import_str)}
        form = {'directory': directory}

        return self._client.request_json('post', url, form, files)

    def upload_aml_file(self, file_path, directory):
        url = self._client.host + '/p/aml-upload'

        file_name = os.path.basename(file_path)
        files = {
            'amlfile': (file_name, open(file_path, 'rb'), 'application/xml'),
        }

        directory = '/directory/' + directory.replace('/directory/', '')
        data = {
            'directory': directory
        }

        return self._client.request_json('POST', url, files=files, data=data, timeout=None)

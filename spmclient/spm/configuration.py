from ..base_api import BaseApi
import json


class Configuration(BaseApi):

    def __fetch_configuration(self):
        url = self._client.host + '/p/configuration'

        return self._client.request_json('GET', url)

    def get_active_languages(self):
        languages = list(filter(lambda c: c['rep']['name'] == 'languages', self.__fetch_configuration()))
        languages = json.loads(languages[0]['rep']['value'])
        return languages

import urllib
from ..base_api import BaseApi


class Meta(BaseApi):

    def create(self, data):

        url = self._client.host + '/p/meta'

        return self._client.request_json('POST', url, data=data)

    def delete(self, meta_id):

        url = self._client.host + '/p/meta/' + meta_id

        return self._client.request_json('DELETE', url)

    def get(self):
        url = self._client.host + '/p/meta'

        return self._client.request_json('GET', url)

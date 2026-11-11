import urllib
from ..base_api import BaseApi


class Search(BaseApi):

    def get_search(self, params):
        if isinstance(params, str):
            qs = params
        else:
            qs = urllib.parse.urlencode(params)
        url = self._client.host + '/p/search?' + qs

        return self._client.request_json('GET', url)

from ..base_api import BaseApi
import json


class Signal(BaseApi):
    def signal_query(self, query):

        url = self._client.host + '/g/api/pi-graphql/signal'
        param = {'query': query}

        return self._client.request_json('POST', url, data=json.dumps(param))
import urllib
import json
from ..base_api import BaseApi


class VariantManagement(BaseApi):

    def get(self):
        url = self._client.host + '/g/api/variant-management/v1/templates'

        return self._client.request_json('GET', url)

    def create(self, model_id_template: str, model_ids_variants: list, dimensionsAndValues: dict = {}) -> dict:

        model_id_template = model_id_template.replace('/model/', '')
        model_ids_variants = [item.replace('/model/', '') for item in model_ids_variants]

        data = {
            "referenceId": model_id_template,
            "dimensionsAndValues": dimensionsAndValues,
            "variantIds": model_ids_variants
        }

        url = self._client.host + '/g/api/variant-management/v2/templates'

        return self._client.request_json('POST', url, json=data)

    def update(self, model_id_template: str, model_ids_variants: list, dimensionsAndValues: dict = {}) -> dict:

        model_id_template = model_id_template.replace('/model/', '')
        model_ids_variants = [item.replace('/model/', '') for item in model_ids_variants]

        data = json.dumps({
            "referenceId": model_ids_variants,
            "dimensionsAndValues": dimensionsAndValues,
        })

        url = self._client.host + '/g/api/variant-management/v2/templates/' + model_id_template + '/variants'

        return self._client.request_json('PUT', url, json=data)

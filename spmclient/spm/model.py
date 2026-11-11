from ..base_api import BaseApi
import html
import json


class Model(BaseApi):
    def get_editordata(self, model_id, rev: str = None):

        if '/model/' in model_id:
            url = self._client.host + '/p/editordata?id=' + model_id.replace('/model/', '')
        else:
            url = self._client.host + '/p/editordata?id=' + model_id

        if rev:
            url = url + '&revision=' + str(rev)

        return self._client.request_json('GET', url)

    def get_latest_json(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/json'
        else:
            url = self._client.host + '/p/model/' + model_id + '/json'

        return self._client.request_json('GET', url)

    def get_revision_json(self, revision_id):

        if '/revision/' in revision_id:
            url = self._client.host + '/p' + revision_id + '/json'
        else:
            url = self._client.host + '/p/revision/' + revision_id + '/json'

        return self._client.request_json('GET', url)

    def get_linked_by(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/linkedBy'
        else:
            url = self._client.host + '/p/model/' + model_id + '/linkedBy'

        return self._client.request_json('GET', url)

    def get_linked_by_hierarchy(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/linkedByHierarchy'
        else:
            url = self._client.host + '/p/model/' + model_id + '/linkedByHierarchy'

        return self._client.request_json('GET', url)

    def get_parents(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/parents'
        else:
            url = self._client.host + '/p/model/' + model_id + '/parents'

        return self._client.request_json('GET', url)

    def get_all_revisions(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/revisions'
        else:
            url = self._client.host + '/p/model/' + model_id + '/revisions'

        return self._client.request_json('GET', url)

    def get_feed(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/notification'
        else:
            url = self._client.host + '/p/model/' + model_id + '/notification'

        return self._client.request_json('GET', url)

    def get_header(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/info'
        else:
            url = self._client.host + '/p/model/' + model_id + '/info'

        return self._client.request_json('GET', url)

    def get_svg(self, model_id):

        if '/model/' in model_id:
            url = self._client.host + '/p' + model_id + '/svg'
        else:
            url = self._client.host + '/p/model/' + model_id + '/svg'

        return self._client.request_data('GET', url)

    def update_info(self, model_id, model_header):

        url = self._client.host + '/p/model/' + model_id.replace('/model/', '') + '/info'
        all_names = {key: html.unescape(value) for key, value in model_header.items() if
                     key.startswith('name') and key != 'namespace'}
        for key, value in all_names.items():
            model_header[key] = value
        return self._client.request_json('PUT', url, model_header)

    def update_model(self, model_id, model_json, comment='', new_name=None, parent=None, description=''):

        if '/model/' not in model_id:
            model_id = '/model/' + model_id

        url = self._client.host + '/p' + model_id

        if not new_name or not parent:
            model_header = self.get_header(model_id)
            body = {
                'name': html.unescape(new_name or model_header['name']),
                'parent': parent or model_header['parent'],
                'description': model_header['description'],
                'comment': comment if comment else model_header['comment'],
                'json_xml': json.dumps(model_json)
            }
        else:
            body = {
                'name': html.unescape(new_name),
                'parent': parent,
                'description': description,
                'comment': comment,
                'json_xml': json.dumps(model_json)
            }
        return self._client.request_json('PUT', url, body)

    def move_model(self, model_id, parent):

        if '/model/' not in model_id:
            model_id = '/model/' + model_id

        url = self._client.host + '/p' + model_id

        body = {
            'parent': parent
        }

        return self._client.request_json('PUT', url, body)

    def publish(self, model_id):

        url = self._client.host + '/p/publish'

        if '/model/' in model_id:
            pass
        else:
            model_id = '/model/' + model_id

        body = {
            'models': model_id,
            'mode': 'publish'
        }

        return self._client.request_json('POST', url, body)

    def unpublish(self, diagram_id):

        url = self._client.host + '/p/publish'

        if '/model/' in diagram_id:
            pass
        else:
            diagram_id = '/model/' + diagram_id

        body = {
            'models': diagram_id,
            'mode': 'unpublish'
        }

        return self._client.request_json('POST', url, body)

    def create(self, name, parent, json_data, diagram_type='bpmn'):

        url = self._client.host + '/p/model'

        namespace = {
            "bpmn": "http://b3mn.org/stencilset/bpmn2.0#",
            "vc": "http://www.signavio.com/stencilsets/processmap#"
        }

        body = {
            'name': html.unescape(name),
            'parent': parent,
            'json_xml': json.dumps(json_data),
            'namespace': namespace[diagram_type]
        }

        return self._client.request_json('POST', url, body)

    def check_syntax(self, model_id, model_json, guideline_id):

        url = self._client.host + '/p/mgeditorchecker'

        if '/model/' in model_id:
            model_id = model_id.split('/model/')[1]

        body = {
            'id': model_id,
            'guideline_id': guideline_id,
            'model_json': json.dumps(model_json),
            'comments': json.dumps({})
        }

        return self._client.request_json('POST', url, body)

    def trigger_approval(self, revision_id, model_id, approval_id):

        if '/model/' not in model_id:
            model_id = f'/model/{model_id}'

        if '/revision/' not in revision_id:
            revision_id = f'/revision/{revision_id}'

        url = self._client.host + '/p' + revision_id + '/approval'

        body = {
            'processId': approval_id,
            'model': model_id,
            'revision': revision_id
        }

        return self._client.request_json('POST', url, body)

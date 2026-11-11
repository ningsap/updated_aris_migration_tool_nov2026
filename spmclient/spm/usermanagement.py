import json

from ..base_api import BaseApi


class UserManagementException(Exception):
    pass


class UserManagement(BaseApi):
    def get_user_groups(self):

        url = self._client.host + '/p/usergroup'

        return self._client.request_json('GET', url)

    def get_user_group(self, user_group_id):

        if '/usergroup/' not in user_group_id:
            url = self._client.host + '/p/user/' + user_group_id
        else:
            url = self._client.host + '/p' + user_group_id

        return self._client.request_json('GET', url)

    def get_users(self, exclude_licenses=True):
        if exclude_licenses:
            url = self._client.host + '/p/user?excludeLicenses=true'
        else:
            url = self._client.host + '/p/user?excludeLicenses=false'

        return self._client.request_json('GET', url)

    def update_user(self, user_id, user_groups=[]):

        if len(user_groups) > 0 and type(user_groups) == list:
            body = {
                'parents': user_groups
            }
        else:
            raise UserManagementException('Empty list or wrong type.')

        if '/user/' not in user_id:
            url = self._client.host + '/p/user/' + user_id
        else:
            url = self._client.host + '/p' + user_id

        return self._client.request_json('PUT', url, body)

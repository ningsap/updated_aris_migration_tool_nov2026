import logging

import yaml
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from .spm_logger import logger


class Client:
    def __init__(self, config_file_path):

        with open(config_file_path) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        self.host = config['host']

        req = requests.Session()

        headers = {
            'x-signavio-api-consumer': config.get('consumer_header', ''),
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'tokenonly': True,
            'name': config['mail'],
            'password': config['password'],
            'tenant': config['workspace']
        }

        url = self.host + "/p/login"

        response = req.post(url, data=data, headers=headers)

        # Response contains the basic HTML code in case if login failure. Otherwise a 32-character string
        if len(response.text) > 50:
            logging.error('Login failed.')
            return

        else:

            logging.info('Login successful.')
            server = ''
            server_region = ''

            for cookie_section in 'AWSELB', 'LBROUTEID':
                if cookie_section in response.cookies:
                    server_region = cookie_section
                    server = response.cookies[cookie_section]

            auth_cookies = {
                'JSESSIONID': response.cookies['JSESSIONID'],
                'identifier': response.cookies['identifier'],
                'login': response.cookies['login'],
                'token': response.text,
                server_region: server
            }

        self.auth_req = requests.Session()

        retry = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)

        self.auth_req.mount('http://', adapter)
        self.auth_req.mount('https://', adapter)

        auth_headers = {
            'x-signavio-api-consumer': config.get('consumer_header', 'sdk-technical-services'),
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'application/json',
            'x-signavio-id': response.text
        }

        self.auth_req.cookies.update(auth_cookies)
        self.auth_req.headers.update(auth_headers)

    def request_json(self, method, url, data={}, files=None, json=None, timeout=300):
        try:
            return self.auth_req.request(method, url, files=files, data=data, json=json, timeout=timeout).json()
        except Exception as e:
            logger.log_error(f"{method}-Request to {url} with exception {e} - check traceback | Excerpt from payload: {str(data)[:100]}")
            return None

    def request_data(self, method, url, data={}, files=None, timeout=300):
        try:
            return self.auth_req.request(method, url, files=files, data=data, timeout=timeout).content
        except Exception as e:
            logger.log_error(f"{method}-Request to {url} with exception {e} - check traceback | Excerpt from payload: {data[:100]}")
            return None

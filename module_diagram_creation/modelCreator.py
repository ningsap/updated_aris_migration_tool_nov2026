# External
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Submodules
from alloy.logging.logger_factory import logger
from alloy.task_watch.task_watch import TaskWatch
from spmclient.spm.spmclient import SPMClient


MAX_CONCURRENT_REQUESTS = 10


class ModelCreator:

    def __init__(self, cfg, spm: SPMClient, file_tracker: TaskWatch):
        self.spm = spm
        self.file_tracker = file_tracker
        self.json_converted_models_file_path = cfg.get('file_path_converted_models_json')
        self._tracker_lock = threading.Lock()
        self.use_threading = cfg.get('use_threading_for_model_creator', True)

        try:
            with open(self.json_converted_models_file_path, 'r') as json_file:
                self.models = json.load(json_file)
        except:
            logger.error(f'ModelCreator Import: {self.json_converted_models_file_path} does not exist')

    def _update_single_model(self, aris_guid, data):
        signavio_id = data.get('signavio_id')
        model_json = data.get('transformed_model_json', {})

        if not model_json:
            logger.error(
                f"Model with GUID {aris_guid} cannot be transformed correctly. Transformed model JSON doesnt exist. Check the Data and Config")
            return

        response = self.spm.model.update_model(signavio_id, model_json, comment='ARIS Migration Tool')

        if isinstance(response, list):
            info_responses = list(filter(lambda resp: resp.get('rel', '') == 'info', response))
            if len(info_responses) > 0:
                response = info_responses[0]
                namespace = response['rep']['namespace']
                if 'bpmn' in namespace:
                    element_type = 'bpmn'
                elif 'processmap' in namespace:
                    element_type = 'vc'
                else:
                    element_type = namespace

                if signavio_id:
                    save_data = {
                        'signavio_id': signavio_id,
                        'json': response,
                        'transformed_model_json': model_json,
                        'revision': response['rep']['rev'],
                        'element_type': element_type,
                        'error': 'no'
                    }
                    with self._tracker_lock:
                        self.file_tracker.save_task_results(id=aris_guid, data=save_data, try_update=True)
                    logger.success(f'Updated Model <{aris_guid}> sucessfully')
                else:
                    logger.error(f'ModelCreator Update: Signavio ID for ARIS GUID {aris_guid} not found')
        else:
            if isinstance(response, dict) and 'errors' in response:
                logger.error(
                    f"Couldn't Update Model: {aris_guid} Received an error from SPMClient : {response.get('errors', '')}, 'Message: ' {response.get('message', '')}")

    def update_signavio_models_with_aris_content(self):
        tasks = []
        for key, entry in self.models.items():
            aris_guid = entry.get('aris_guid')
            data_exists, data = self.file_tracker.is_task_done(id=aris_guid)
            if data_exists:
                tasks.append((aris_guid, data))
            else:
                logger.error(f"Model with GUID {aris_guid} doesn't exist in FileTracker")

        if self.use_threading:
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
                futures = {executor.submit(self._update_single_model, aris_guid, data): aris_guid
                           for aris_guid, data in tasks}
                for future in as_completed(futures):
                    aris_guid = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"An error occurred processing model {aris_guid}: {e}")
        else:
            for aris_guid, data in tasks:
                try:
                    if data.get("signavio_id","").replace("/model/", "") in ["15425121ca394ef9814d34f9aebe7004", "bedcbd48586c4039b297923074a64740",""
                    "fd4108bb38ad41e4b72cdfd95a6ace3f", "c2398f7701d14c0384536aba3963165e","7af8fd4eea0d4775ada70b3ee5bf7490","259f4ec789dc47d5a2bdc95d55e24db7",
                    "47b179a029174794926f212ac8cbe940","eafef11194a14a5ab6b872f9d69f9ae1","c5220966fb2e4fb99af98cc0e35bcc42","e38232e8f392423283cdd3f074e50ad3","50a63b8dccc44ac0881fa8778264b690""cc6026b954ae4fe1b60cd231b9752f6a","43fc5fc746c84573abcb1d54665b9a20"]:
                    #if aris_guid in ['8f835ec1-a59b-11ef-180f-5232495bb7aa']:
                        self._update_single_model(aris_guid, data)
                except Exception as e:
                    logger.error(f"An error occurred processing model {aris_guid}: {e}")
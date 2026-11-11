import yaml
from alloy.logging.logger_utility import logger

class ProjectConfigurationException(Exception):
    def __init__(self, message: str = "", *args: object) -> None:
        logger.error(message)
        super().__init__(*args)


class Config:

    def __init__(self, cfg_file):
        self.cfg_file = cfg_file

    def read_config(self):
        with open(self.cfg_file) as file:
            cfg = yaml.load(file, Loader=yaml.FullLoader)
        return cfg

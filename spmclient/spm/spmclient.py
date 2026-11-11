from .search import Search
from .meta import Meta
from .variantmanagement import VariantManagement
from .client import Client
from .directory import Directory
from .model import Model
from .dictionary import Dictionary
from .utils import Utils
from .file import File
from .signal import Signal
from .usermanagement import UserManagement
from .configuration import Configuration
import json
from .spm_logger import spm_logger


class SPMClient:
    def __init__(self, config_file_path):

        spm_logger.info("Initializing SPM Client...")

        self._client = Client(config_file_path)
        self.search = Search(self._client)
        self.attributes = Meta(self._client)
        self.directory = Directory(self._client)
        self.model = Model(self._client)
        self.dictionary = Dictionary(self._client)
        self.utils = Utils(self._client)
        self.file = File(self._client)
        self.signal = Signal(self._client)
        self.usermanagement = UserManagement(self._client)
        self.variantmanagement = VariantManagement(self._client)
        self.configuration = Configuration(self._client)

        spm_logger.success("SPM Client initialized.")

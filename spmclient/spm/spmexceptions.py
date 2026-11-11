class SPMConfigFileNotFound(Exception):

    def __init__(self):
        self.message = 'SPM config file (spmconfig.yaml.yaml) not found. Make sure that file is within your project directory.'
        super().__init__(self.message)

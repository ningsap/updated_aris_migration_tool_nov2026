from ARIS_Migration_Tool_SCB_Nov2026.alloy.logging.logger_factory import logger


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            logger.warning(f"The <{cls.__name__}> class is a Singleton, returning existing instance.")
        return cls._instances[cls]

    @classmethod
    def delete_instance(cls, cls_type):
        if cls_type in cls._instances:
            del cls._instances[cls_type]

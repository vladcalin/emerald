import os


class Configuration(object):
    def __init__(self, config_file=None):
        self.config_file = config_file

    def get(self, value_name):
        to_return = self.get_from_env(value_name)
        if not to_return:
            to_return = self.get_from_config_file(value_name)
        if not to_return:
            to_return = self.get_default(value_name)
        return to_return

    def get_from_env(self, value_name):
        return os.environ.get("SERVREG_" + value_name.upper())

    def get_from_config_file(self, value_name):
        pass

    def get_default(self, value_name):
        pass

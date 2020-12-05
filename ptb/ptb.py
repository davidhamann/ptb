import sys
import logging
import configparser
from pathlib import Path
from typing import Optional, Tuple
from const import CONFIG_SECTIONS


class Configuration:
    def __init__(self, config_file: Optional[str]):
        self.config_file = config_file
        self.config = configparser.ConfigParser()

    def load(self) -> bool:
        """Loads config and makes sure all values are set

        Loads from config file, if set, and/or prompts user for
        any missing config values
        """
        key_config: Tuple

        if self.config_file:
            self._load_from_file()

        for section in CONFIG_SECTIONS:
            if section not in self.config.sections():
                self.config[section] = {}

            for key in CONFIG_SECTIONS[section]:
                try:
                    value = self.config[section][key[0]]
                except KeyError:
                    # ask for config value
                    help_text = key[1]
                    help_text += f' (default: {key[2]})' if key[2] else ''
                    value = input(f'> {help_text} ')

                if not value:
                    # set default if nothing was given
                    value = key[2]

                if not value:
                    logging.info(
                        'No value given for "%s" in section "%s"',
                        key[0], section)
                    logging.info('Cancelling...')
                    return False

                logging.info(
                    'Config value for "%s" in section "%s": %s',
                    key[0], section, value)
        return True

    def _load_from_file(self) -> None:
        if not self.config_file.exists():
            logging.warning(('Confile file %s given, but does not exist.'
                             % self.config_file))
            return

        try:
            self.config.read(self.config_file)
        except configparser.Error:
            logging.warning('Failed to read config file %s' % self.config_file)
            return

        logging.info(('Loaded config file with sections: %s' %
                      self.config.sections()))


class Ptb:
    def __init__(self, config: Configuration):
        self.config = config

    def set_up(self):
        logging.info('Starting to set up pentest box')
        return True


def configure_logging():
    logging.basicConfig(
        format='[%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)],
        level=logging.DEBUG)


def main():
    '''CLI entry point'''
    configure_logging()
    res = True
    config_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    confirm = 'y'  # input('Configure this box? [Y/n]: ')

    if confirm in ['', 'Y', 'y']:
        config = Configuration(config_file)
        if config.load():
            ptb = Ptb(config)
            ptb.set_up()
    else:
        print('Cancelling...')

    sys.exit(0) if res else sys.exit(1)

import sys
import logging
from pathlib import Path
from .config import Config


class Ptb:
    def __init__(self, config: Config):
        self.config = config

    def set_up(self):
        logging.info('Starting to set up pentest box')
        return True


def main():
    '''CLI entry point'''

    logging.basicConfig(
        format='[%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)],
        level=logging.DEBUG)

    res = True
    config_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    confirm = 'y'  # input('Configure this box? [Y/n]: ')

    if confirm in ['', 'Y', 'y']:
        config = Config(config_file)
        if config.load():
            ptb = Ptb(config)
            ptb.set_up()
    else:
        print('Cancelling...')

    sys.exit(0) if res else sys.exit(1)

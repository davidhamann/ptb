import sys
import logging
import subprocess
from typing import List
from pathlib import Path
from .config import Config


def exec(command: List) -> subprocess.CompletedProcess:
    assert isinstance(command, type([]))
    logging.info('Running %s' % ' '.join(command))

    try:
        return subprocess.run(command, encoding='ascii',
                              capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        logging.error(
            'Command "%s" failed with code %d.\n%s\n%s',
            ' '.join(command), error.returncode, error.stdout, error.stderr)
    except FileNotFoundError:
        logging.error('%s cannot be found' % command[0])

    return False


class Ptb:
    def __init__(self, config: Config):
        self.config = config

    def set_up(self):
        logging.info('Starting to set up pentest box')

        if not exec(['id']):
            return False

        return True


def main():
    '''CLI entry point'''
    result: bool = True

    logging.basicConfig(
        format='[%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)],
        level=logging.DEBUG)
    config_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    confirm = 'y'  # input('Configure this box? [Y/n]: ')

    if confirm in ['', 'Y', 'y']:
        config = Config(config_file)
        if config.load():
            ptb = Ptb(config)
            result = ptb.set_up()
    else:
        print('Cancelling...')

    sys.exit(0) if result else sys.exit(1)

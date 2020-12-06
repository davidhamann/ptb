import os
import time
import sys
import logging
import subprocess
from typing import List
from pathlib import Path
from ptb.config import Config
from ptb.const import REQUIRED_PACKAGES, VNC_PACKAGES


def exec(command: List, verbose=False) -> int:
    assert isinstance(command, type([]))
    logging.info('Running %s' % ' '.join(command))

    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    except FileNotFoundError:
        logging.error('%s cannot be found' % command[0])
        return -1

    while True:
        out = proc.stdout.readline()
        if proc.poll() is not None and out == b'':
            break
        if verbose and out:
            logging.info(out.decode('utf-8').strip())
        time.sleep(0.1)

    result = proc.poll()
    if result != 0:
        logging.error('Command "%s" failed. Return code: %d', ' '.join(command), result)
    return result


class Ptb:
    def __init__(self, config: Config):
        self.config = config

    def set_up(self, verbose=False):
        logging.info('Starting to set up pentest box')

        # FIXME: wrap those calls in an exception, then try all except PtbError or such
        if exec(['apt-get', 'update']) != 0:
            return False

        if self.config.parser['Local'].getboolean('Upgrade'):
            if exec(['apt-get', 'upgrade', '-y'], verbose) != 0:
                return False

        if self.config.parser['Local'].getboolean('DistUpgrade'):
            if exec(['apt-get', 'dist-upgrade', '-y'], verbose) != 0:
                return False

        if exec(['apt-get', 'install', '-y'] + REQUIRED_PACKAGES, verbose) != 0:
            return False

        if self.config.parser['Local'].getboolean('SetupVNC'):
            if exec(['apt-get', 'install', '-y'] + VNC_PACKAGES, verbose) != 0:
                return False

        additional_packages = self.config.parser['Local']['AdditionalPackages']
        if additional_packages != '' and additional_packages != 'none':
            package_list  = additional_packages.split(' ')
            if exec(['apt-get', 'install', '-y'] + package_list, verbose) != 0:
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

    if not os.geteuid() == 0:
        logging.error('Please run as root')
        sys.exit(1)

    confirm = 'y'  # input('Configure this box? [Y/n]: ')
    if confirm in ['', 'Y', 'y']:
        config = Config(config_file)
        if config.load():
            ptb = Ptb(config)
            result = ptb.set_up(verbose=True)
    else:
        print('Cancelling...')

    sys.exit(0) if result else sys.exit(1)

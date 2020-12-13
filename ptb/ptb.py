import os
import re
import time
import sys
import logging
import subprocess
from getpass import getpass
from typing import Optional, List, TextIO
from pathlib import Path
from ptb.config import Config
from ptb.const import (
        REQUIRED_PACKAGES, VNC_PACKAGES,
        SSH_KEY_PATH, HOME_PATH, SERVICE_TEMPLATE,
        WEBCMD_PATH, WEBCMD_APP, TIMER_TEMPLATE)


def exec(command: List, verbose: bool = False, stdout: Optional[TextIO] = None) -> int:
    assert isinstance(command, type([]))
    joined = ' '.join(command)
    logging.info('Running %s' % joined)

    if stdout:
        # use given file handle for redirection
        try:
            return subprocess.run(command, check=True, stdout=stdout).returncode
        except subprocess.CalledProcessError as error:
            logging.error('Command "%s" failed with return %d' % (joined, error.returncode))
            return error.returncode

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

        # enable openssh server
        if exec(['systemctl', 'enable', 'ssh'], verbose) != 0:
            return False

        # -----------

        ssh_host = self.config.parser['RemoteSSH']['Host']
        ssh_port = self.config.parser['RemoteSSH']['RemotePort']

        # delete previous key if existing
        if exec(['rm', '-f', str(SSH_KEY_PATH)], verbose) != 0:
            return False

        # generate keypair for remote server
        if exec(['ssh-keygen', '-f', str(SSH_KEY_PATH), '-N', ''], verbose) != 0:
            return False

        # clean known_hosts and re-add remote server
        exec(['touch', str(HOME_PATH / '.ssh/known_hosts')], verbose)
        if exec(['ssh-keygen', '-R', ssh_host + ':' + ssh_port], verbose) != 0:
            return False

        with open(HOME_PATH / '.ssh/known_hosts', 'a') as known_hosts:
            if exec(['ssh-keyscan', '-H', '-p', ssh_port, ssh_host],
                  verbose, stdout=known_hosts) != 0:
                return False

        # upload key to remote server
        ssh_user = self.config.parser['RemoteSSH']['User']
        os.environ['SSHPASS'] = getpass(
                f'Enter the password for the user {ssh_user} '
                f'at {ssh_host} (for key upload): ')

        if exec(['sshpass', '-e', 'ssh-copy-id', '-i',
                 str(SSH_KEY_PATH), '-p', ssh_port,
                 f'{ssh_user}@{ssh_host}'], verbose) != 0:
            return False

        # test login
        logging.info('Testing login...')
        if exec(['ssh', '-q', '-o', 'BatchMode=yes', '-i',
            str(SSH_KEY_PATH), f'{ssh_user}@{ssh_host}', '-p', ssh_port, 'true']) != 0:
            return False
        logging.info('Login works!')

        # add autossh service
        logging.info('Writing service file for autossh')
        with open('/etc/systemd/system/ptb.service', 'w') as service:
            replacements = {
                    '{{remote_forward_port}}': self.config.parser['RemoteSSH']['LocalPort'],
                    '{{port}}': self.config.parser['RemoteSSH']['RemotePort'],
                    '{{user}}': ssh_user,
                    '{{host}}': ssh_host,
                    '{{key_path}}': str(SSH_KEY_PATH)
                    }
            replacements = dict((re.escape(k), v) for k, v in replacements.items())
            pattern = re.compile("|".join(replacements.keys()))
            service_config = pattern.sub(
                    lambda x: replacements[re.escape(x.group(0))], SERVICE_TEMPLATE)
            service.write(service_config)



        # starting services
        logging.info('Enabling openssh-server')
        if exec(['systemctl', 'enable', 'ssh'], verbose) != 0:
            return False

        logging.info('Starting openssh-server')
        if exec(['systemctl', 'start', 'ssh'], verbose) != 0:
            return False

        logging.info('Enabling autossh service')
        if exec(['systemctl', 'enable', 'ptb.service'], verbose) != 0:
            return False

        logging.info('Starting autossh service')
        if exec(['systemctl', 'start', 'ptb.service'], verbose) != 0:
            return False
        logging.info('Installing webcmd systemd timer')
        if exec(['mkdir', '-p', WEBCMD_PATH], verbose) != 0:
            return False

        with open(WEBCMD_PATH + '/' + WEBCMD_APP, 'w') as f:
            f.write(TIMER_TEMPLATE\
                    .replace('{{host}}', self.config.parser['RemoteWeb']['Host'])\
                    .replace('{{filename}}', self.config.parser['RemoteWeb']['FileName']))

        if exec(['chmod', '+x', WEBCMD_PATH + '/' + WEBCMD_APP], verbose) != 0:
            return False

        print('Setup done. You should now be able to connect to the pentest box '
              'from anywhere via a proxy jump (you will likely use a different '
              'key than the one we generated here):\n\nssh -o ProxyCommand="ssh '
              f'-i ~/.ssh/key-to-remote -W %h:%p -p {ssh_port} remote-user@remote-ip" '
              f'-p {self.config.parser["RemoteSSH"]["LocalPort"]} pentestbox-user@'
              '127.0.0.1\n\n(Add -D 1080, if you would like to run a SOCKS proxy on '
              'your local box for local tools.)')

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

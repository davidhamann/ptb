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
from ptb.exceptions import PtbProcessException
from ptb.const import (
        REQUIRED_PACKAGES, VNC_PACKAGES,
        SSH_KEY_PATH, HOME_PATH, SSH_SERVICE_TEMPLATE,
        WEBCMD_PATH, WEBCMD_APP, WEBCMD_SCRIPT_TEMPLATE, WEBCMD_CRON)


class Ptb:
    def __init__(self, config: Config, verbose=False):
        self.config = config
        self.verbose = verbose

    def exec(self, command: List[str], stdout: Optional[TextIO] = None) -> int:
        """Wrapper for executing external commands."""
        assert isinstance(command, type([]))
        joined = ' '.join(command)
        logging.info('Running %s' % joined)

        if stdout:
            # use given file handle for redirection
            try:
                exit = subprocess.run(
                    command, check=True, stdout=stdout).returncode
            except subprocess.CalledProcessError as error:
                raise PtbProcessException(
                    'Command "%s" failed with return %d' %
                    (joined, error.returncode))
        else:
            try:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            except FileNotFoundError:
                raise PtbProcessException('%s cannot be found' % command[0])

            # print stdout until process exits
            while True:
                out = proc.stdout.readline()
                if proc.poll() is not None and out == b'':
                    break
                if self.verbose and out:
                    logging.info(out.decode('utf-8').strip())
                time.sleep(0.1)

            exit = proc.poll()

        if exit != 0:
            raise PtbProcessException('Command "%s" failed. Return code: %d',
                                      ' '.join(command), exit)

        return exit

    def install_packages(self) -> None:
        """Install required and optional packages, optionally upgrade dist."""
        exec(['apt-get', 'update'])

        if self.config.parser['Local'].getboolean('Upgrade'):
            exec(['apt-get', 'upgrade', '-y'])

        if self.config.parser['Local'].getboolean('DistUpgrade'):
            exec(['apt-get', 'dist-upgrade', '-y'])

        exec(['apt-get', 'install', '-y'] + REQUIRED_PACKAGES)

        if self.config.parser['Local'].getboolean('SetupVNC'):
            exec(['apt-get', 'install', '-y'] + VNC_PACKAGES)

        add_packages = self.config.parser['Local']['AdditionalPackages']
        if add_packages != '' and add_packages != 'none':
            package_list = add_packages.split(' ')
            exec(['apt-get', 'install', '-y'] + package_list)

    def configure_ssh(self) -> None:
        """Enable local SSH server, then set up keys for remote
        communication."""
        ssh_user = self.config.parser['RemoteSSH']['User']
        ssh_host = self.config.parser['RemoteSSH']['Host']
        ssh_port = self.config.parser['RemoteSSH']['RemotePort']

        # enable openssh server on pentest box
        exec(['systemctl', 'enable', 'ssh'])

        # delete previous key if existing
        exec(['rm', '-f', str(SSH_KEY_PATH)])

        # generate keypair for remote server
        exec(['ssh-keygen', '-f', str(SSH_KEY_PATH), '-N', ''])

        # clean known_hosts and re-add remote server
        exec(['touch', str(HOME_PATH / '.ssh/known_hosts')])
        exec(['ssh-keygen', '-R', ssh_host + ':' + ssh_port])

        with open(HOME_PATH / '.ssh/known_hosts', 'a') as known_hosts:
            exec(['ssh-keyscan', '-H', '-p', ssh_port, ssh_host],
                 stdout=known_hosts)

        # prompt for one-time remote login pass and upload key to remote server
        os.environ['SSHPASS'] = getpass(
                f'Enter the password for the user {ssh_user} '
                f'at {ssh_host} (for key upload): ')

        exec(['sshpass', '-e', 'ssh-copy-id', '-i', str(SSH_KEY_PATH),
              '-p', ssh_port, f'{ssh_user}@{ssh_host}'])

        # test login
        logging.info('Testing login...')
        exec(['ssh', '-q', '-o', 'BatchMode=yes', '-i', str(SSH_KEY_PATH),
              f'{ssh_user}@{ssh_host}', '-p', ssh_port, 'true'])
        logging.info('Login with key works!')

    def install_service(self) -> None:
        """Install service to keep SSH alive."""
        ssh_user = self.config.parser['RemoteSSH']['User']
        ssh_host = self.config.parser['RemoteSSH']['Host']

        with open('/etc/systemd/system/ptb-ssh.service', 'w') as service:
            replacements = {
                '{{remote_forward_port}}':
                    self.config.parser['RemoteSSH']['LocalPort'],
                '{{port}}': self.config.parser['RemoteSSH']['RemotePort'],
                '{{user}}': ssh_user,
                '{{host}}': ssh_host,
                '{{key_path}}': str(SSH_KEY_PATH)
                }
            replacements = dict(
                (re.escape(k), v) for k, v in replacements.items())
            pattern = re.compile("|".join(replacements.keys()))
            service_config = pattern.sub(
                    lambda x: replacements[re.escape(x.group(0))],
                    SSH_SERVICE_TEMPLATE)
            service.write(service_config)

    def install_cron(self) -> None:
        """Write-out webcmd script and set up cron to call it."""
        exec(['mkdir', '-p', WEBCMD_PATH])

        with open(WEBCMD_PATH + '/' + WEBCMD_APP, 'w') as f:
            f.write(
                WEBCMD_SCRIPT_TEMPLATE
                .replace('{{host}}', self.config.parser['RemoteWeb']['Host'])
                .replace('{{filename}}', self.config.parser['RemoteWeb']['FileName']))

        exec(['chmod', '+x', WEBCMD_PATH + '/' + WEBCMD_APP])

        with open('/etc/cron.d/webcmd', 'w') as cron:
            cron.write(WEBCMD_CRON)

    def enable_services(self) -> None:
        logging.info('Enabling openssh-server')
        exec(['systemctl', 'enable', 'ssh'])

        logging.info('Starting openssh-server')
        exec(['systemctl', 'start', 'ssh'])

        logging.info('Enabling autossh service')
        exec(['systemctl', 'enable', 'ptb-ssh.service'])

        logging.info('Starting autossh service')
        exec(['systemctl', 'start', 'ptb-ssh.service'])

    def set_up(self) -> bool:
        logging.info('Starting to set up pentest box')

        try:
            # update, upgrade and install packages
            logging.info('Starting with package install')
            self.install_packages()

            # set up openssh server and set up key pair for remote
            logging.info('Setting up local SSH and keypair for remote access')
            self.configure_ssh()

            # add autossh service
            logging.info('Installing service for keeping SSH alive')
            self.install_service()

            logging.info('Starting services')
            self.enable_services()

            logging.info('Setting up cron for fetching web commands')
            self.install_cron()

        except PtbProcessException as exc:
            logging.error(exc)
            return False

        print('Setup done. You should now be able to connect to the pentest '
              'box from anywhere via a proxy jump (you will likely use a '
              'different key than the one we generated here):\n')
        print('ssh -o ProxyCommand="ssh -i ~/.ssh/key-to-remote -W %h:%p -p '
              f'{self.config.parser["RemoteSSH"]["RemotePort"]} remote-user@'
              f'remote-ip" -p {self.config.parser["RemoteSSH"]["LocalPort"]} '
              'pentestbox-user@127.0.0.1\n\n(Add -D 1080, if you would like to'
              'run a SOCKS proxy on your local box for local tools.)')

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

    confirm = input('Configure this box? [Y/n]: ')
    if confirm in ['', 'Y', 'y']:
        config = Config(config_file)
        if config.load():
            ptb = Ptb(config, verbose=False)
            result = ptb.set_up()
    else:
        print('Cancelling...')

    sys.exit(0) if result else sys.exit(1)

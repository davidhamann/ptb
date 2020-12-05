CONFIG_SECTIONS = {
    'RemoteSSH': [
        ('host', 'IP of remote SSH server:', ''),
        ('remote_port', 'Port of remote SSH server:', 443),
        ('local_port',
         'Local port on remote SSH server for forwarding:', 2200)
    ],
    'RemoteWeb': [
        ('host',
         'Hostname or IP of remote web server for commands:', ''),
        ('file_name',
         'Name of hosted file containing the commands to execute:',
         'cmd.txt')
    ],
    'Local': [
        ('setup_vnc',
         'Should a VNC server be set up on the pentest box? '
         '(won\'t start automatically)',
         'no')
    ]
}

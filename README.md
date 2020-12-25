# PTB - Pentest Box

This is a small app for setting up connectivity on a pentest dropbox. It will install packages, configure an autossh service (systemd), and set up a cronjob that checks for remote commands from a webserver for troubleshooting in case the SSH connection drops.

IPs, hostnames, packages, etc. can be configured in a config file (see `config.sample.ini`). If no config file is found, the app will ask for the values it needs.

I made this just now for experimentation and to have a quicker setup. Please test thoroughly if it fits *your* case before using it in a real assessment.

## Install & Usage

```
pip install .
ptb my-config.ini
```

After this is done, you should be able to connect to the box via a proxy jump:

```
ssh -o ProxyCommand="ssh -i ~/.ssh/<key-to-remote> -W %h:%p -p <remote-port> <remote-user>@<remote-ip>" -p <local-port> pentestbox-user@127.0.0.1

# Add -D 1080, if you would like to run a SOCKS proxy on your local box for local tools.
```

Commands from the webserver are checked and executed every two minutes. If the last published commands have already been executed, they won't be executed a second time.

## Notes

The app won't do anything to secure your pentest box. Make sure to configure your host firewall/iptables, encrypted volumes, etc. yourself. `ptb` is only a helper for the connection setup plus a few extras.

More importantly, make sure that your remote SSH server and webserver are secure. Otherwise, once *they* are pwned, your dropbox is basically rooted as well :-)

## Requirements

You need a remote SSH server (with a static IP) to be used as proxy and a webserver to fetch commands from (simple text file).

Tested on Kali Linux, but should run on any Debian based Linux.

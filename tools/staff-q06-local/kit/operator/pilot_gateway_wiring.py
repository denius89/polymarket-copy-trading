"""Staff composition for the existing mTLS paper gateway."""
from datetime import datetime, timezone
import ipaddress
import os
from pathlib import Path
import stat

from gateway_core import GatewayUnavailable
from pilot_gateway import PilotEdge, PilotPrivateHttp, pilot_handler, stamp


def protected_key(path):
    file = Path(path)
    if not file.is_absolute() or file.resolve() != file:
        raise ValueError('noncanonical pilot key path')
    parent = file.parent.stat()
    if parent.st_mode & 0o022 or parent.st_uid not in {0, os.geteuid()}:
        raise ValueError('pilot key parent is writable')
    with os.fdopen(os.open(file, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        mode = os.fstat(stream.fileno())
        if (not stat.S_ISREG(mode.st_mode) or stat.S_IMODE(mode.st_mode) not in {0o400, 0o440, 0o600, 0o640}
                or mode.st_uid not in {0, os.geteuid()} or mode.st_size != 32):
            raise ValueError('invalid pilot key file')
        key = stream.read(33)
    if len(key) != 32:
        raise ValueError('invalid pilot key length')
    return key


def trusted_client_ip(handler):
    # Installed only inside the outer pinned-client-certificate handler.
    values = handler.headers.get_all('X-Shadow-Pilot-Client-IP', [])
    if len(values) != 1 or '%' in values[0]:
        raise GatewayUnavailable('missing trusted pilot client IP')
    try:
        return str(ipaddress.ip_address(values[0]))
    except ValueError:
        raise GatewayUnavailable('invalid trusted pilot client IP') from None


def attach_pilot(base, origin, config):
    required = {'format', 'enabled', 'deploymentDigest', 'cutoffAt', 'auth', 'reader', 'networkKeyFile'}
    if (type(config) is not dict or set(config) != required or config['format'] != 'pilot-edge-v1'
            or config['enabled'] is not True):
        raise ValueError('invalid pilot gateway profile')
    cutoff = stamp(config['cutoffAt'])
    if datetime.now(timezone.utc) >= cutoff:
        raise ValueError('pilot cutoff expired')
    peers, secrets, addresses = {}, [protected_key(config['networkKeyFile'])], set()
    for role in ('auth', 'reader'):
        p = config[role]
        if type(p) is not dict or set(p) != {'host', 'port', 'ingressKeyFile'}:
            raise ValueError('invalid pilot peer configuration')
        ip = ipaddress.IPv4Address(p['host'])
        private_ranges = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
        if (not any(ip in ipaddress.ip_network(network) for network in private_ranges)
                or type(p['port']) is not int or not 1024 <= p['port'] <= 65535
                or ip in addresses):
            raise ValueError('pilot peer needs its own private address')
        addresses.add(ip)
        key = protected_key(p['ingressKeyFile'])
        if key in secrets:
            raise ValueError('pilot keys must be independent')
        secrets.append(key)
        peers[role] = PilotPrivateHttp(str(ip), p['port'], lambda value=key: value)
    edge = PilotEdge(origin, config['deploymentDigest'], peers, lambda: secrets[0], lambda: True, cutoff)
    return pilot_handler(base, edge, trusted_client_ip)

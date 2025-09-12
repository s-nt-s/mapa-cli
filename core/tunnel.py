from atexit import register
from sshtunnel import SSHTunnelForwarder
from os.path import expanduser
from paramiko import SSHConfig
import socket
from core.tp.config import HostPort
import logging

logger = logging.getLogger()

LOCAL_HOST='127.0.0.1'


def get_ips(host: str):
    infos = _original_getaddrinfo(host, None)
    return tuple(sorted({info[4][0] for info in infos}))
        


class SSHTunnel():
    INSTANCES: dict[HostPort, "SSHTunnel"] = dict()

    @staticmethod
    def get_ssh_config(ssh_config: str, ssh_alias: str):
        ssh_conf = SSHConfig()
        with open(expanduser(ssh_config)) as f:
            ssh_conf.parse(f)
        return ssh_conf.lookup(ssh_alias)

    @classmethod
    def init(
            cls,
            *remotes: HostPort,
            ssh_alias: str,
            ssh_config: str = "~/.ssh/config"
        ):
        for remote in remotes:
            if remote not in cls.INSTANCES:
                obj = cls(ssh_alias=ssh_alias, remote=remote, ssh_config=ssh_config)
                cls.INSTANCES[remote] = obj
                for ip in get_ips(remote.host):
                    cls.INSTANCES[HostPort(
                        host=ip,
                        port=remote.port
                    )] = obj

    def __init__(
        self,
        ssh_alias: str,
        remote: HostPort,
        ssh_config: str = "~/.ssh/config"
    ):
        if remote in self.__class__.INSTANCES:
            raise ValueError(f"Ya hay un tunnel para {remote}")
        self.__tunnel = None
        self.__remote = remote
        register(self.close)
        conf = SSHTunnel.get_ssh_config(ssh_config, ssh_alias)
        self.__jump_by = HostPort(
            host=conf["hostname"],
            port=int(conf['port'])
        )
        self.__tunnel = SSHTunnelForwarder(
            self.__jump_by.host,
            self.__jump_by.port,
            ssh_username=conf['user'],
            ssh_pkey=conf['identityfile'][0],
            allow_agent=True,
            remote_bind_address=(self.__remote.host, self.__remote.port),
            local_bind_address=(LOCAL_HOST, 0)
        )
        SSHTunnel.INSTANCES[self.__remote] = self

    def __start(self):
        if not self.__tunnel.is_active:
            try:
                self.__tunnel.stop(force=True)
            except:
                pass
            self.__tunnel.start()
            return True
        return False
            
    def start(self):
        if self.__start():
            logger.info(f"{self.__remote} = {self.local}")
        
    @property
    def local(self):
        if not self.__tunnel.is_active:
            None
        return HostPort(
            host=LOCAL_HOST,
            port=self.__tunnel.local_bind_port
        )
        
    @property
    def jump_by(self):
        return self.__jump_by
    
    @property
    def remote(self):
        return self.__remote

    def close(self):
        for k, v in list(self.__class__.INSTANCES.items()):
            if self == v:
                del self.__class__.INSTANCES[k]
        if self.__tunnel is not None:
            self.__tunnel.stop(force=True)
            

_original_connect = socket.socket.connect
_original_getaddrinfo = socket.getaddrinfo

def _patched_connect(self, address):
    remote = HostPort(
        host=address[0],
        port=int(address[1])
    )
    t = SSHTunnel.INSTANCES.get(remote)
    if t is None:
        return _original_connect(self, address)
    t.start()
    return _original_connect(self, (t.local.host, t.local.port))


def _patched_getaddrinfo(host, port, *args, **kwargs):
    remote = HostPort(
        host=host,
        port=int(port) if port else None
    )
    t = SSHTunnel.INSTANCES.get(remote)
    if t is None:
        return _original_getaddrinfo(host, port, *args, **kwargs)
    t.start()
    return _original_getaddrinfo(t.local.host, t.local.port, *args, **kwargs)


socket.socket.connect = _patched_connect
socket.getaddrinfo = _patched_getaddrinfo
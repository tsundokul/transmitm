from abc import ABCMeta, abstractstaticmethod, abstractmethod
from ipaddress import ip_address, IPv4Address, IPv6Address


class Proxy(metaclass=ABCMeta):
    """Interface for Proxy classes
    """
    def __init__(self,
                 server_ip,
                 server_port,
                 bind_port=0,
                 interface='127.0.0.1'):
        """
        Args:
            server_ip (str): Target server IP to which the connections are
                proxyfied
            server_port (int): Target server port
            bind_port (int, optional): Proxy bind port. Defaults to 0 (random).
            interface (str, optional): Proxy bind interface. Defaults to
                '127.0.0.1'.
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.bind_port = bind_port
        self.interface = interface
        self.taps = list()

    def add_tap(self, tap):
        """Connect a tap instance to the proxy's instance

        Args:
            tap (Tap): Tap object; add order defines the interception chain
        """
        self.taps.append(tap)

    def __hash__(self):
        """Override comparison methods for Proxy objects
        This way you can have multiple proxies pointing to same server tuple
        as long as the proxy bind ports differ (see __eq__)
        """
        return (self.server_ip, self.server_port, self.bind_port,
                self.__class__).__hash__()

    def __eq__(self, other):
        """Called during comparison if __hash__() is the same for two objects
        In this case it says that bind_port will not collide when set arbitrary
        """
        return self.bind_port != 0

    @staticmethod
    def get_bind_interface(address):
        IFACES = {
            IPv4Address: {
                True: '127.0.0.1',
                False: '0.0.0.0'
            },
            IPv6Address: {
                True: '::1',
                False: '::0'
            }
        }
        ip = ip_address(address)
        return IFACES[type(ip)][ip.is_private]

    @staticmethod
    def socket_tuple(socket):
        """Helper that returns an IP tuple for a connected socket

        Args:
            socket (socket.socket): a connected socket object

        Returns:
            tuple: (peer_ip_tuple, local_ip_tuple)
        """
        return (socket.getpeername(), socket.getsockname())

    @abstractmethod
    def spawn(self):
        """Method called by Dispatcher when registering a Proxy instance;
        e.g. starts listeners
        """
        pass

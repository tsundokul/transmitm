from . import udp
from . import tcp
from abc import ABCMeta, abstractmethod
from twisted.internet import reactor


class Tap(metaclass=ABCMeta):
    """Interface for Tap classes
    """
    @abstractmethod
    def handle(self, data, ip_tuple):
        """Handles packet data manipulation; data must always be returned
        since it's meant to be passed to the next tap or sent on the wire

        Args:
            data (bytes): SDU bytes; the transport's protocol payload
            ip_tuple (tuple): (peer_tuple, proxy_tuple, tap_class)
        """
        pass


class Dispatcher:
    """Manages intercepting proxies

    Raises:
        TypeError: on instantiation
    """
    proxies = set()

    @classmethod
    def add_proxies(disp, proxies):
        """Register a proxy object to the proxies pool

        Args:
            disp (Dispatcher): self class
            proxies (list): a list with proxy instances to be registered in a
            given order

        Raises:
            RuntimeError: on adding proxies that bind to the same tuple
        """
        for proxy in proxies:
            proxy.spawn()
            disp.proxies.add(proxy)

    @classmethod
    def add_proxy(disp, proxy):
        disp.add_proxies([proxy])

    @staticmethod
    def run():
        """Starts twisted reactor; blocking method
        """
        reactor.run()

    @classmethod
    def __new__(cls, *args, **kwargs):
        """Prevent creating instances of Dispatcher"""
        if cls is Dispatcher:
            raise TypeError("Dispatcher class cannot be instantiated")

from functools import wraps
from .proxy import Proxy
from twisted.internet import protocol, reactor


class TCPProxy(Proxy):
    def spawn(self):
        factory = TCPServerFactory(self.server_ip,
                                   self.server_port,
                                   proxy=self)
        factory.protocol = TCPServerProtocol
        listener = reactor.listenTCP(self.bind_port,
                                     factory,
                                     interface=self.interface)

        if not self.bind_port:
            self.bind_port = listener.getHost().port

    @staticmethod
    def intercept(dataReceived):
        """Decorator used to "tap" into twisted whenever data is received
        """
        @wraps(dataReceived)
        def _intercept(proto, data):
            taps = proto.factory.proxy.taps

            for tap in taps:
                data = tap.handle(data, proto.ip_tuple)

            dataReceived(proto, data)

        return _intercept


class TCPProto(protocol.Protocol):
    def write(self, data):
        if data:
            self.transport.write(data)


class TCPServerFactory(protocol.ServerFactory):
    def __init__(self, server_ip, server_port, proxy):
        self.server_ip = server_ip
        self.server_port = server_port
        self.proxy = proxy


class TCPServerProtocol(TCPProto):
    """Acts as a proxy between the actual client(s) and target server
    ServerProtocol forwards data to the server through ClientProtocol or back
    """
    def __init__(self):
        self.buffer = None
        self.client = None

    def connectionMade(self):
        """When connection is received from client via tranparent proxying rule,
        the client factory spawns a connection to the with the target server
        """
        # Disable Nagle's algorithm
        self.transport.setTcpNoDelay(True)
        self.ip_tuple = Proxy.socket_tuple(self.transport.socket)
        factory = protocol.ClientFactory()
        factory.protocol = TCPClientProtocol
        factory.proxy = self.factory.proxy
        factory.server = self
        reactor.connectTCP(self.factory.server_ip, self.factory.server_port,
                           factory)

    @TCPProxy.intercept
    def dataReceived(self, data):
        """When data is received from the client (that should talk with the
        target server), send it to the tap to have it mutated then back to
        actual client
        """
        if (self.client is not None):
            self.client.write(data)
        else:
            self.buffer = data


class TCPClientProtocol(TCPProto):
    """Acts as intermediary client and speaks directly to the target server
    """
    def connectionMade(self):
        # Disable Nagle's algorithm
        self.transport.setTcpNoDelay(True)
        self.ip_tuple = Proxy.socket_tuple(self.transport.socket)
        self.factory.server.client = self
        self.write(self.factory.server.buffer)
        self.factory.server.buffer = b''

    @TCPProxy.intercept
    def dataReceived(self, data):
        """When data is received from the target server send it back rightaway
        """
        self.factory.server.write(data)

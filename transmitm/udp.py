from .proxy import Proxy
from functools import wraps
from socket import SOL_SOCKET, SO_RCVBUF, SO_SNDBUF
from twisted.internet import protocol, reactor, error


class UDPProxy(Proxy):
    def spawn(self):
        factory = UDPServerProtocol(self.server_ip,
                                    self.server_port,
                                    proxy=self)
        listener = reactor.listenUDP(self.bind_port,
                                     factory,
                                     interface=self.interface)
        if not self.bind_port:
            self.bind_port = listener.getHost().port

    @staticmethod
    def intercept(datagramReceived):
        """Decorator used to "tap" into twisted whenever data is received
        """
        @wraps(datagramReceived)
        def _intercept(proto, data, ip_tuple):
            taps = proto.proxy.taps

            for tap in taps:
                data = tap.handle(data, ip_tuple)

            return datagramReceived(proto, data, ip_tuple)

        return _intercept


class UDPProto(protocol.DatagramProtocol):
    BUFFERSIZE = 2 * 1024 * 1024

    @UDPProxy.intercept
    def tap(self, data, ip_tuple):
        return data

    def _set_buffer_size(self):
        """Increase SEND and RECV buffer size to minimize packet lost when
        processing large ammounts of traffic
        """
        sock = self.transport.getHandle()
        sock.setsockopt(SOL_SOCKET, SO_RCVBUF, self.BUFFERSIZE)
        sock.setsockopt(SOL_SOCKET, SO_SNDBUF, self.BUFFERSIZE)


class UDPServerProtocol(UDPProto):
    """Acts as intermediary client for the UDP protocol
    """
    def __init__(self, server_ip, server_port, proxy):
        self.server_tuple = (server_ip, server_port)
        self.proxy = proxy
        self.clients = dict()

    def startProtocol(self):
        self._set_buffer_size()
        self.listen_addr = self.transport.socket.getsockname()

    def datagramReceived(self, data, peer):
        """When data is received from the target server create an intermediary
        socket to map server responses toq one particular client
        """
        if self.clients.get(peer).__class__ is not UDPClientProtocol:
            factory = UDPClientProtocol(self.server_tuple,
                                        proxy=self.proxy,
                                        parent=self,
                                        source=peer)

            # Get bind interface for proxy client socket
            bind_iface = Proxy.get_bind_interface(self.server_tuple[0])

            # Attempt to reuse port
            _bind_port = self.clients.get(peer) or 0
            try:
                listener = reactor.listenUDP(_bind_port,
                                             factory,
                                             interface=bind_iface)
            except error.CannotListenError:
                listener = reactor.listenUDP(0, factory, interface=bind_iface)

            factory.bind_port = listener.getHost().port
            self.clients[peer] = factory

        data = self.tap(data, ip_tuple=(peer, self.listen_addr))
        self.clients[peer].transport.write(data)


class UDPClientProtocol(UDPProto):
    def __init__(self, server_tuple, proxy, parent, source):
        self.server_tuple = server_tuple
        self.proxy = proxy
        self.parent = parent
        self.source = source

    def startProtocol(self):
        self._set_buffer_size()
        self.transport.connect(*self.server_tuple)
        self.self_tuple = Proxy.socket_tuple(self.transport.socket)

    def datagramReceived(self, data, peer):
        data = self.tap(data, self.self_tuple)
        self.parent.transport.write(data, self.source)

    def stopProtocol(self):
        """Save bind_port for later reuse"""
        self.parent.clients[self.source] = self.bind_port

"""Contains system tests for the module
"""
import pytest
import socket
import time
import transmitm
from ipaddress import ip_address, IPv4Address
from functools import wraps
from twisted.internet import reactor, protocol, threads, defer, address, error


class ForwardTap(transmitm.Tap):
    """Just pass the data
    """
    def handle(self, data, ip_tuple):
        return data


class MangleTap(transmitm.Tap):
    """Just pass the data
    """
    def __init__(self, needle, replace):
        self.needle = needle
        self.replace = replace

    def handle(self, data, ip_tuple):
        return data.replace(self.needle, self.replace)


def test_dispatcher_run():
    """Tests if Dispatcher.run starts the reactor
    """
    with pytest.raises(error.ReactorAlreadyRunning):
        transmitm.Dispatcher.run()


class EchoTCP(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write(data)


class BaseTest:
    def init(self):
        self.data = b'Hello, World!'
        self.lo = '127.0.0.1'
        self.lo6 = '::1'

    def teardown_method(self):
        """Block until listener cleans up until starting a new test
        """
        d = defer.maybeDeferred(self.echoer.stopListening)
        d.callback(None)

    def _send_data(self, dst_ip, dst_port):
        """Send data to a specified destination using a manually created socket
        """
        if type(ip_address(dst_ip)) is IPv4Address:
            socket_proto = socket.AF_INET
            conn_tuple = (dst_ip, dst_port)
        else:
            socket_proto = socket.AF_INET6
            conn_tuple = (dst_ip, dst_port, 0, 0)

        sock_type = socket.SOCK_STREAM if type(self) is TestTCP \
            else socket.SOCK_DGRAM

        sock = socket.socket(socket_proto, sock_type, 0)
        sock.settimeout(1)
        sock.connect(conn_tuple)

        if not sock.send(self.data):
            raise RuntimeError('Error sending data')

        data = sock.recv(1024)
        sock.close()
        return data


class TestTCP(BaseTest):
    def setup_method(self):
        """Setup a twised echoer to act as the server
        """
        self.init()
        factory = protocol.Factory()
        factory.protocol = EchoTCP

        # Listen on both IPv4 and IPv6 loopback addresses
        self.echoer = reactor.listenTCP(0, factory, interface='::0')
        self.port = self.echoer.getHost().port

    @defer.inlineCallbacks
    def test_echo_v4(self):
        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  self.port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_v6(self):
        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  self.port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v4(self):
        tcp_proxy = transmitm.TCPProxy(self.lo, self.port)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  tcp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v6(self):
        tcp_proxy = transmitm.TCPProxy(self.lo6, self.port, interface=self.lo6)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  tcp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v4_to_v6(self):
        tcp_proxy = transmitm.TCPProxy(self.lo6, self.port, interface=self.lo)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  tcp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v6_to_v4(self):
        tcp_proxy = transmitm.TCPProxy(self.lo, self.port, interface=self.lo6)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  tcp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_tap(self):
        tap = ForwardTap()
        tcp_proxy = transmitm.TCPProxy(self.lo, self.port)
        tcp_proxy.add_tap(tap)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  tcp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_tap_mangle(self):
        tap = MangleTap(b'World', b'Galaxy')
        tcp_proxy = transmitm.TCPProxy(self.lo, self.port)
        tcp_proxy.add_tap(tap)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  tcp_proxy.bind_port)
        assert echoed_data == b'Hello, Galaxy!'

    @defer.inlineCallbacks
    def test_echo_proxy_tap_chain(self):
        tap1 = MangleTap(b'World', b'Galaxy')
        tap2 = MangleTap(b'Galaxy', b'Universe')
        tcp_proxy = transmitm.TCPProxy(self.lo, self.port)
        tcp_proxy.add_tap(tap1)
        tcp_proxy.add_tap(tap2)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, tcp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  tcp_proxy.bind_port)
        assert echoed_data == b'Hello, Universe!'


class EchoUDP(protocol.DatagramProtocol):
    def datagramReceived(self, datagram, address):
        self.transport.write(datagram, address)


class TestUDP(BaseTest):
    def setup_method(self):
        """Setup a twised echoer to act as the server
        """
        self.init()
        # Listen on both IPv4 and IPv6 loopback addresses
        self.echoer = reactor.listenUDP(0, EchoUDP(), interface='::0')
        self.port = self.echoer.getHost().port

    @defer.inlineCallbacks
    def test_echo_v4(self):
        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  self.port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_v6(self):
        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  self.port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v4(self):
        udp_proxy = transmitm.UDPProxy(self.lo, self.port)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  udp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v6(self):
        udp_proxy = transmitm.UDPProxy(self.lo6, self.port, interface=self.lo6)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  udp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v4_to_v6(self):
        udp_proxy = transmitm.UDPProxy(self.lo6, self.port, interface=self.lo)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  udp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_v6_to_v4(self):
        udp_proxy = transmitm.UDPProxy(self.lo, self.port, interface=self.lo6)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo6,
                                                  udp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_tap(self):
        tap = ForwardTap()
        udp_proxy = transmitm.UDPProxy(self.lo, self.port)
        udp_proxy.add_tap(tap)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  udp_proxy.bind_port)
        assert echoed_data == self.data

    @defer.inlineCallbacks
    def test_echo_proxy_tap_mangle(self):
        tap = MangleTap(b'World', b'Galaxy')
        udp_proxy = transmitm.UDPProxy(self.lo, self.port)
        udp_proxy.add_tap(tap)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)
        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  udp_proxy.bind_port)
        assert echoed_data == b'Hello, Galaxy!'

    @defer.inlineCallbacks
    def test_echo_proxy_tap_chain(self):
        tap1 = MangleTap(b'World', b'Galaxy')
        tap2 = MangleTap(b'Galaxy', b'Universe')
        udp_proxy = transmitm.UDPProxy(self.lo, self.port)
        udp_proxy.add_tap(tap1)
        udp_proxy.add_tap(tap2)

        yield threads.deferToThread(transmitm.Dispatcher.add_proxy, udp_proxy)

        echoed_data = yield threads.deferToThread(self._send_data, self.lo,
                                                  udp_proxy.bind_port)
        assert echoed_data == b'Hello, Universe!'

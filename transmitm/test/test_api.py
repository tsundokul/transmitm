import transmitm
import pytest


def test_api():
    """Test imported names"""
    assert all([
        hasattr(transmitm, '__version__'),
        hasattr(transmitm, 'Dispatcher'),
        hasattr(transmitm, 'Tap'),
        hasattr(transmitm, 'TCPProxy'),
        hasattr(transmitm, 'UDPProxy'),
        hasattr(transmitm, 'Proxy')
    ]) is True


def test_tap_bad():
    """Tap subclasses should define a handle method"""
    class BadTap(transmitm.Tap):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class*"):
        BadTap()


def test_tap_api():
    assert hasattr(transmitm.Tap, 'handle') is True


def test_proxy_bad():
    """Proxy subclasses should define a spawn method"""
    class BadProxy(transmitm.Proxy):
        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class*"):
        BadProxy()


def test_proxy_api():
    assert hasattr(transmitm.Proxy, 'spawn') is True


def test_dispatcher_instance():
    """Dispatcher should not be instantiable"""
    with pytest.raises(TypeError,
                       match="Dispatcher class cannot be instantiated"):
        transmitm.Dispatcher()

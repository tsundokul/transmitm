transmitm
==========================

`transmitm` is a Twisted-based Python module that provides transparent intercepting proxying at transport level.

Transports supported as of the latest version:
* TCP
* UDP

# Install
`transmitm` requires a `3.5` minimum version of Python
```
pip install transmitm
```

## Operation
Transparent proxying requires traffic redirection to the app using a third party utility such as `iptables` or `nftables`.

`iptables` example to redirect TCP traffic targeting server port 80 to proxy port 8080
```bash
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
```

`transmitm` uses the concept of taps. `Tap` is a class whose instances receive transport SDUs (Service Data Units) from transitioning packets and perform some sort of operation on them; multiple taps are chained.

Taps get attached to `Proxy` objects (`TCPProxy`, `UDPProxy`) that handle packets on two arms - both from the client and the server. 

`Dispatcher` class holds a list of proxy instances; it cannot be instantiated. 
```
             +---------------------------------------------+
             |                    proxy                    |
             |     +--------+   +--------+   +-------+     |
             |     |        |   |        |   |       |     |
            SDU    |        |   |        |   |       |     |
client ------>-----+  tap 1 +---> tap 2  |...| tap n +---------> server
             |     |        |   |        |   |       |     |
             |     |        |   |        |   |       |     |
             |     +--------+   +--------+   +-------+     |
             +---------------------------------------------+
                                 gateway
```
## Usage / API

The following script illustrate the module's API 
```python
#!/usr/bin/env python3
from transmitm import Tap, Dispatcher, TCPProxy, UDPProxy

# Define Tap classes that handle data (SDUs)
# At minimum, they must implement the 'handle' method
# The returned value gets passed to the next tap in chain
class PktLogger(Tap):
    """Prints packet size to stdout
    """

    def handle(self, data, ip_tuple):
        """Not altering data parameter causes returning
        the same object reference"""
        peer, proxy = ip_tuple
        print(f"Got {len(data)} bytes from {peer} on {proxy}")
        return data


class Mangler(Tap):
    """Do a search and replace in packet bytes
    """

    def __init__(self, search, replace):
        self.search = search
        self.replace = replace

    def handle(self, data, ip_tuple):
        return data.replace(self.search, self.replace)


# Create proxy instances
# A Proxy object requires at least a destination server's IP and port number
# Listen on TCP 8081 and forward to 127.0.0.1:8080
tcp_proxy_8080 = TCPProxy("127.0.0.1", 8080, bind_port=8081)

# Bind port may be omitted for getting a random one
# You can also specify a bind interface; by default all proxies are bind to localhost
udp_proxy_53 = UDPProxy("1.1.1.1", 53, bind_port=53)

# The proxy can be used as a connector between IPv4 and IPv6 endpoints
udp_proxy_rnd = UDPProxy("1.1.1.1", 53, interface='::0')

# Create tap instances that will process packets
logger = PktLogger()
path_mangler = Mangler(
    search=b'/api',
    replace=b'/forbidden'
)

# Attach taps instances to the proxies
# The order in which the taps are added defines the tap chaining
tcp_proxy_8080.add_tap(path_mangler)
tcp_proxy_8080.add_tap(logger)

# Just logging for DNS packets
udp_proxy_53.add_tap(logger)

# When registering multiple proxies make sure you add those with a specified
# bind_port first, to avoid collision with randomly assigned ones
Dispatcher.add_proxies([
    tcp_proxy_8080,
    udp_proxy_53,
    udp_proxy_rnd
])

# If not provided, bind port is randomly assigned and can be retrieved
# after adding the proxy to the Dispatcher
print("Registered proxies:")
for proxy in Dispatcher.proxies:
    print(
        proxy.__class__.__name__,
        proxy.interface,
        proxy.bind_port,
        '->',
        proxy.server_ip,
        proxy.server_port
    )

# Blocking method, should be called last
Dispatcher.run()
```

## TODO
- Add UNIX Domain sockets support
- Add packet routing capabilities

## Bug reporting
* Open a new issue
* Explain expected vs actual behavior
* Add code snippet that reproduces the issue

## Contributing
This project uses [poetry](https://python-poetry.org) for package management during development. Development dependencies require a `>=3.7` version of Python. To get a working environment use the following commands
```bash
# Install poetry
pip install poetry
# or...
# curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

# Install module's development dependencies
poetry install --no-root

# Check the setup by running the test
pytest
```
* Fork the repo
* Check out a feature or bug branch
* Add your changes
* Add test cases
* Update README when needed
* Ensure tests are passing
* Submit a pull request to upstream repo
* Add description of your changes
* Ensure branch is mergeable

_MIT License, 2020_ [@tim17d](https://twitter.com/tim17d)
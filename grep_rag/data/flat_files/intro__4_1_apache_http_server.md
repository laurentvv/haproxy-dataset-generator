# SECTION: 4.1. Apache HTTP server
# URL: https://docs.haproxy.org/3.2/intro.html#4.1
# DEPTH: 2
# PAGE: intro
---

##  [4.1.](https://docs.haproxy.org/3.2/intro.html#4.1) Apache HTTP server
```
Apache is the de-facto standard HTTP server. It's a very complete and modular
project supporting both file serving and dynamic contents. It can serve as a
frontend for some application servers. It can even proxy requests and cache
responses. In all of these use cases, a front load balancer is commonly needed.
Apache can work in various modes, some being heavier than others. Certain
modules still require the heavier pre-forked model and will prevent Apache from
scaling well with a high number of connections. In this case HAProxy can provide
a tremendous help by enforcing the per-server connection limits to a safe value
and will significantly speed up the server and preserve its resources that will
be better used by the application.

Apache can extract the client's address from the X-Forwarded-For header by using
the "mod_rpaf" extension. HAProxy will automatically feed this header when
"option forwardfor" is specified in its configuration. HAProxy may also offer a
nice protection to Apache when exposed to the internet, where it will better
resist a wide number of types of DoS attacks.

```
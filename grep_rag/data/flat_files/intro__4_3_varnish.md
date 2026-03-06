# SECTION: 4.3. Varnish
# URL: https://docs.haproxy.org/3.2/intro.html#4.3
# DEPTH: 2
# PAGE: intro
---

##  [4.3.](https://docs.haproxy.org/3.2/intro.html#4.3) Varnish
```
Varnish is a smart caching reverse-proxy, probably best described as a web
application accelerator. Varnish doesn't implement SSL/TLS and wants to dedicate
all of its CPU cycles to what it does best. Varnish also implements HAProxy's
PROXY protocol so that HAProxy can very easily be deployed in front of Varnish
as an SSL offloader as well as a load balancer and pass it all relevant client
information. Also, Varnish naturally supports decompression from the cache when
a server has provided a compressed object, but doesn't compress however. HAProxy
can then be used to compress outgoing data when backend servers do not implement
compression, though it's rarely a good idea to compress on the load balancer
unless the traffic is low.

When building large caching farms across multiple nodes, HAProxy can make use of
consistent URL hashing to intelligently distribute the load to the caching nodes
and avoid cache duplication, resulting in a total cache size which is the sum of
all caching nodes. In addition, caching of very small dumb objects for a short
duration on HAProxy can sometimes save network round trips and reduce the CPU
load on both the HAProxy and the Varnish nodes. This is only possible is no
processing is done on these objects on Varnish (this is often referred to as
the notion of "favicon cache", by which a sizeable percentage of useless
downstream requests can sometimes be avoided). However do not enable HAProxy
caching for a long time (more than a few seconds) in front of any other cache,
that would significantly complicate troubleshooting without providing really
significant savings.

```
# SECTION: 4.4. Alternatives
# URL: https://docs.haproxy.org/3.2/intro.html#4.4
# DEPTH: 2
# PAGE: intro
---

##  [4.4.](https://docs.haproxy.org/3.2/intro.html#4.4) Alternatives
```
Linux Virtual Server (LVS or IPVS) is the layer 4 load balancer included within
the Linux kernel. It works at the packet level and handles TCP and UDP. In most
cases it's more a complement than an alternative since it doesn't have layer 7
knowledge at all.

Pound is another well-known load balancer. It's much simpler and has much less
features than HAProxy but for many very basic setups both can be used. Its
author has always focused on code auditability first and wants to maintain the
set of features low. Its thread-based architecture scales less well with high
connection counts, but it's a good product.

Pen is a quite light load balancer. It supports SSL, maintains persistence using
a fixed-size table of its clients' IP addresses. It supports a packet-oriented
mode allowing it to support direct server return and UDP to some extents. It is
meant for small loads (the persistence table only has 2048 entries).

NGINX can do some load balancing to some extents, though it's clearly not its
primary function. Production traffic is used to detect server failures, the
load balancing algorithms are more limited, and the stickiness is very limited.
But it can make sense in some simple deployment scenarios where it is already
present. The good thing is that since it integrates very well with HAProxy,
there's nothing wrong with adding HAProxy later when its limits have been
reached.

Varnish also does some load balancing of its backend servers and does support
real health checks. It doesn't implement stickiness however, so just like with
NGINX, as long as stickiness is not needed that can be enough to start with.
And similarly, since HAProxy and Varnish integrate so well together, it's easy
to add it later into the mix to complement the feature set.

```
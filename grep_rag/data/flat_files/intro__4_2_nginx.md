# SECTION: 4.2. NGINX
# URL: https://docs.haproxy.org/3.2/intro.html#4.2
# DEPTH: 2
# PAGE: intro
---

##  [4.2.](https://docs.haproxy.org/3.2/intro.html#4.2) NGINX
```
NGINX is the second de-facto standard HTTP server. Just like Apache, it covers a
wide range of features. NGINX is built on a similar model as HAProxy so it has
no problem dealing with tens of thousands of concurrent connections. When used
as a gateway to some applications (e.g. using the included PHP FPM) it can often
be beneficial to set up some frontend connection limiting to reduce the load
on the PHP application. HAProxy will clearly be useful there both as a regular
load balancer and as the traffic regulator to speed up PHP by decongesting
it. Also since both products use very little CPU thanks to their event-driven
architecture, it's often easy to install both of them on the same system. NGINX
implements HAProxy's PROXY protocol, thus it is easy for HAProxy to pass the
client's connection information to NGINX so that the application gets all the
relevant information. Some benchmarks have also shown that for large static
file serving, implementing consistent hash on HAProxy in front of NGINX can be
beneficial by optimizing the OS' cache hit ratio, which is basically multiplied
by the number of server nodes.

```
# SECTION: 3.2. How HAProxy works
# URL: https://docs.haproxy.org/3.2/intro.html#3.2
# DEPTH: 2
# PAGE: intro
---

##  [3.2.](https://docs.haproxy.org/3.2/intro.html#3.2) How HAProxy works
```
HAProxy is an event-driven, non-blocking engine combining a very fast I/O layer
with a priority-based, multi-threaded scheduler. As it is designed with a data
forwarding goal in mind, its architecture is optimized to move data as fast as
possible with the least possible operations. It focuses on optimizing the CPU
cache's efficiency by sticking connections to the same CPU as long as possible.
As such it implements a layered model offering bypass mechanisms at each level
ensuring data doesn't reach higher levels unless needed. Most of the processing
is performed in the kernel, and HAProxy does its best to help the kernel do the
work as fast as possible by giving some hints or by avoiding certain operation
when it guesses they could be grouped later. As a result, typical figures show
15% of the processing time spent in HAProxy versus 85% in the kernel in TCP or
HTTP close mode, and about 30% for HAProxy versus 70% for the kernel in HTTP
keep-alive mode.

A single process can run many proxy instances; configurations as large as
300000 distinct proxies in a single process were reported to run fine. A single
core, single CPU setup is far more than enough for more than 99% users, and as
such, users of containers and virtual machines are encouraged to use the
absolute smallest images they can get to save on operational costs and simplify
troubleshooting. However the machine HAProxy runs on must never ever swap, and
its CPU must not be artificially throttled (sub-CPU allocation in hypervisors)
nor be shared with compute-intensive processes which would induce a very high
context-switch latency.

Threading allows to exploit all available processing capacity by using one
thread per CPU core. This is mostly useful for SSL or when data forwarding
rates above 40 Gbps are needed. In such cases it is critically important to
avoid communications between multiple physical CPUs, which can cause strong
bottlenecks in the network stack and in HAProxy itself. While counter-intuitive
to some, the first thing to do when facing some performance issues is often to
reduce the number of CPUs HAProxy runs on.

HAProxy only requires the haproxy executable and a configuration file to run.
For logging it is highly recommended to have a properly configured syslog daemon
and log rotations in place. Logs may also be sent to stdout/stderr, which can be
useful inside containers. The configuration files are parsed before starting,
then HAProxy tries to bind all listening sockets, and refuses to start if
anything fails. Past this point it cannot fail anymore. This means that there
are no runtime failures and that if it accepts to start, it will work until it
is stopped.

Once HAProxy is started, it does exactly 3 things :

  - process incoming connections;

  - periodically check the servers' status (known as health checks);

  - exchange information with other haproxy nodes.

Processing incoming connections is by far the most complex task as it depends
on a lot of configuration possibilities, but it can be summarized as the 9 steps
below :

  - accept incoming connections from listening sockets that belong to a
    configuration entity known as a "frontend", which references one or multiple
    listening addresses;

  - apply the frontend-specific processing rules to these connections that may
    result in blocking them, modifying some headers, or intercepting them to
    execute some internal applets such as the statistics page or the CLI;

  - pass these incoming connections to another configuration entity representing
    a server farm known as a "backend", which contains the list of servers and
    the load balancing strategy for this server farm;

  - apply the backend-specific processing rules to these connections;

  - decide which server to forward the connection to according to the load
    balancing strategy;

  - apply the backend-specific processing rules to the response data;

  - apply the frontend-specific processing rules to the response data;

  - emit a log to report what happened in fine details;

  - in HTTP, loop back to the second step to wait for a new request, otherwise
    close the connection.

Frontends and backends are sometimes considered as half-proxies, since they only
look at one side of an end-to-end connection; the frontend only cares about the
clients while the backend only cares about the servers. HAProxy also supports
full proxies which are exactly the union of a frontend and a backend. When HTTP
processing is desired, the configuration will generally be split into frontends
and backends as they open a lot of possibilities since any frontend may pass a
connection to any backend. With TCP-only proxies, using frontends and backends
rarely provides a benefit and the configuration can be more readable with full
proxies.

```
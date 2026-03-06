# SECTION: Introduction
# URL: https://docs.haproxy.org/3.2/intro.html
# DEPTH: 1
# PAGE: intro
---

Toggle navigation [HAProxy Documentation](https://docs.haproxy.org/)
  * [Starter Guide](https://docs.haproxy.org/3.2/intro.html)
  * [Configuration Manual](https://docs.haproxy.org/3.2/configuration.html)
  * [Management Guide](https://docs.haproxy.org/3.2/management.html)


  * [HAProxy Home Page](http://www.haproxy.org/)


  * [Summary](https://docs.haproxy.org/3.2/intro.html#tab-summary)


**1.** |  [**Available documentation**](https://docs.haproxy.org/3.2/intro.html#1) |
---|---|---

**2.** |  [
**Quick introduction to load balancing and load balancers**](https://docs.haproxy.org/3.2/intro.html#2) |

**3.** |  [
**Introduction to HAProxy**](https://docs.haproxy.org/3.2/intro.html#3) |
3.1. |  [What HAProxy is and is not](https://docs.haproxy.org/3.2/intro.html#3.1) |
3.2. |  [How HAProxy works](https://docs.haproxy.org/3.2/intro.html#3.2) |
3.3. |  [Basic features](https://docs.haproxy.org/3.2/intro.html#3.3) |
3.3.1. |  [Proxying](https://docs.haproxy.org/3.2/intro.html#3.3.1) |
3.3.2. |  [SSL](https://docs.haproxy.org/3.2/intro.html#3.3.2) |
3.3.3. |  [Monitoring](https://docs.haproxy.org/3.2/intro.html#3.3.3) |
3.3.4. |  [High availability](https://docs.haproxy.org/3.2/intro.html#3.3.4) |
3.3.5. |  [Load balancing](https://docs.haproxy.org/3.2/intro.html#3.3.5) |
3.3.6. |  [Stickiness](https://docs.haproxy.org/3.2/intro.html#3.3.6) |
3.3.7. |  [Logging](https://docs.haproxy.org/3.2/intro.html#3.3.7) |
3.3.8. |  [Statistics](https://docs.haproxy.org/3.2/intro.html#3.3.8) |
3.4. |  [Standard features](https://docs.haproxy.org/3.2/intro.html#3.4) |
3.4.1. |  [Sampling and converting information](https://docs.haproxy.org/3.2/intro.html#3.4.1) |
3.4.2. |  [Maps](https://docs.haproxy.org/3.2/intro.html#3.4.2) |
3.4.3. |  [ACLs and conditions](https://docs.haproxy.org/3.2/intro.html#3.4.3) |
3.4.4. |  [Content switching](https://docs.haproxy.org/3.2/intro.html#3.4.4) |
3.4.5. |  [Stick-tables](https://docs.haproxy.org/3.2/intro.html#3.4.5) |
3.4.6. |  [Formatted strings](https://docs.haproxy.org/3.2/intro.html#3.4.6) |
3.4.7. |  [HTTP rewriting and redirection](https://docs.haproxy.org/3.2/intro.html#3.4.7) |
3.4.8. |  [Server protection](https://docs.haproxy.org/3.2/intro.html#3.4.8) |
3.5. |  [Advanced features](https://docs.haproxy.org/3.2/intro.html#3.5) |
3.5.1. |  [Management](https://docs.haproxy.org/3.2/intro.html#3.5.1) |
3.5.2. |  [System-specific capabilities](https://docs.haproxy.org/3.2/intro.html#3.5.2) |
3.5.3. |  [Scripting](https://docs.haproxy.org/3.2/intro.html#3.5.3) |
3.5.4. |  [Advanced features: Tracing](https://docs.haproxy.org/3.2/intro.html#3.5.4) |
3.6. |  [Sizing](https://docs.haproxy.org/3.2/intro.html#3.6) |
3.7. |  [How to get HAProxy](https://docs.haproxy.org/3.2/intro.html#3.7) |

**4.** |  [
**Companion products and alternatives**](https://docs.haproxy.org/3.2/intro.html#4) |
4.1. |  [Apache HTTP server](https://docs.haproxy.org/3.2/intro.html#4.1) |
4.2. |  [NGINX](https://docs.haproxy.org/3.2/intro.html#4.2) |
4.3. |  [Varnish](https://docs.haproxy.org/3.2/intro.html#4.3) |
4.4. |  [Alternatives](https://docs.haproxy.org/3.2/intro.html#4.4) |

**5.** |  [
**Contacts**](https://docs.haproxy.org/3.2/intro.html#5) |
Keyboard navigation :
You can use **left** and **right** arrow keys to navigate between chapters.

Converted with [haproxy-dconv](https://github.com/cbonte/haproxy-dconv) v**0.4.2-15** on **2026/02/25**
# [![](https://docs.haproxy.org/img/HAProxyCommunityEdition_60px.png?0.4.2-15)](http://www.haproxy.org/ "HAProxy")
## Starter Guide
**version 3.2.13-15**


```
This document doesn't provide any configuration help or hints, but it explains
where to find the relevant documents. The summary below is meant to help you
search sections by name and navigate through the document.

Note to documentation contributors :
    This document is formatted with 80 columns per line, with even number of
    spaces for indentation and without tabs. Please follow these rules strictly
    so that it remains easily printable everywhere. If you add sections, please
    update the summary below for easier searching.

```

# Summary
**1.** |  [**Available documentation**](https://docs.haproxy.org/3.2/intro.html#1) |
---|---|---

**2.** |  [
**Quick introduction to load balancing and load balancers**](https://docs.haproxy.org/3.2/intro.html#2) |

**3.** |  [
**Introduction to HAProxy**](https://docs.haproxy.org/3.2/intro.html#3) |
3.1. |  [What HAProxy is and is not](https://docs.haproxy.org/3.2/intro.html#3.1) |
3.2. |  [How HAProxy works](https://docs.haproxy.org/3.2/intro.html#3.2) |
3.3. |  [Basic features](https://docs.haproxy.org/3.2/intro.html#3.3) |
3.3.1. |  [Proxying](https://docs.haproxy.org/3.2/intro.html#3.3.1) |
3.3.2. |  [SSL](https://docs.haproxy.org/3.2/intro.html#3.3.2) |
3.3.3. |  [Monitoring](https://docs.haproxy.org/3.2/intro.html#3.3.3) |
3.3.4. |  [High availability](https://docs.haproxy.org/3.2/intro.html#3.3.4) |
3.3.5. |  [Load balancing](https://docs.haproxy.org/3.2/intro.html#3.3.5) |
3.3.6. |  [Stickiness](https://docs.haproxy.org/3.2/intro.html#3.3.6) |
3.3.7. |  [Logging](https://docs.haproxy.org/3.2/intro.html#3.3.7) |
3.3.8. |  [Statistics](https://docs.haproxy.org/3.2/intro.html#3.3.8) |
3.4. |  [Standard features](https://docs.haproxy.org/3.2/intro.html#3.4) |
3.4.1. |  [Sampling and converting information](https://docs.haproxy.org/3.2/intro.html#3.4.1) |
3.4.2. |  [Maps](https://docs.haproxy.org/3.2/intro.html#3.4.2) |
3.4.3. |  [ACLs and conditions](https://docs.haproxy.org/3.2/intro.html#3.4.3) |
3.4.4. |  [Content switching](https://docs.haproxy.org/3.2/intro.html#3.4.4) |
3.4.5. |  [Stick-tables](https://docs.haproxy.org/3.2/intro.html#3.4.5) |
3.4.6. |  [Formatted strings](https://docs.haproxy.org/3.2/intro.html#3.4.6) |
3.4.7. |  [HTTP rewriting and redirection](https://docs.haproxy.org/3.2/intro.html#3.4.7) |
3.4.8. |  [Server protection](https://docs.haproxy.org/3.2/intro.html#3.4.8) |
3.5. |  [Advanced features](https://docs.haproxy.org/3.2/intro.html#3.5) |
3.5.1. |  [Management](https://docs.haproxy.org/3.2/intro.html#3.5.1) |
3.5.2. |  [System-specific capabilities](https://docs.haproxy.org/3.2/intro.html#3.5.2) |
3.5.3. |  [Scripting](https://docs.haproxy.org/3.2/intro.html#3.5.3) |
3.5.4. |  [Advanced features: Tracing](https://docs.haproxy.org/3.2/intro.html#3.5.4) |
3.6. |  [Sizing](https://docs.haproxy.org/3.2/intro.html#3.6) |
3.7. |  [How to get HAProxy](https://docs.haproxy.org/3.2/intro.html#3.7) |

**4.** |  [
**Companion products and alternatives**](https://docs.haproxy.org/3.2/intro.html#4) |
4.1. |  [Apache HTTP server](https://docs.haproxy.org/3.2/intro.html#4.1) |
4.2. |  [NGINX](https://docs.haproxy.org/3.2/intro.html#4.2) |
4.3. |  [Varnish](https://docs.haproxy.org/3.2/intro.html#4.3) |
4.4. |  [Alternatives](https://docs.haproxy.org/3.2/intro.html#4.4) |

**5.** |  [
**Contacts**](https://docs.haproxy.org/3.2/intro.html#5) |
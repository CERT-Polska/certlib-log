# Copyright (c) 2026, CERT Polska. All rights reserved.
#
# This file's content is free software; you can redistribute and/or
# modify it under the terms of the *BSD 3-Clause "New" or "Revised"
# License* (see the `LICENSE.txt` file in the source code repository:
# https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt).


# (The following module-level docstring contains
# the **User's Guide** part of the documentation.)

"""
## **Introduction**

The primary reason for creating the `certlib.log` library was to
make it easier to configure *structured logging* across various
systems created and used by [CERT Polska](https://cert.pl/en/)
-- in a possibly *consistent way* and with *minimal impact* on
existing code.

However, despite a few opinionated defaults, the library is quite
versatile, so it may prove useful for a much broader audience of
developers and system administrators. Apart from the *structured
logging* stuff, it also offers a few other features...

!!! note

    `certlib.log` uses *only* the Python's standard library,
    i.e., it **does *not* depend on any third-party packages**.

***

### How to Install

You can install the `certlib.log` library by running the following
command (typically, you will do this within a Python [*virtual
environment*](https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments)):

```bash
python3 -m pip install certlib.log
```

The library is compatible with Python 3.10 and all newer versions of
Python.

!!! note

    The canonical name of the *distribution package* is `certlib-log`
    (with a hyphen), but *pip* and other tools accept also the
    `certlib.log` form (with a dot); the latter may feel more natural,
    as it is also the *importable module*'s name (used in Python code).

***

### TL;DR: How to Quickly Enable *Structured Logging*

* Does your program already make use of the standard [`logging`][]
  facilities *and* do you want it to start emitting *structured*
  JSON-serialized log entries? Just make your configuration of logging
  include [`certlib.log.StructuredLogsFormatter`][] as a *formatter*.
  To do that easily, you may want to look at one of these examples
  (please also read the comments included there):

    * [`logging.config.dictConfig`-Style Configuration Example](#loggingconfigdictconfig-style-configuration-example), or
    * [`logging.config.fileConfig`-Style Configuration Example](#loggingconfigfileconfig-style-configuration-example).

* The `system`, `component` and `component_type` keys (which you can
  see in those examples) are intended to be set with the following
  semantics in mind:

    * `system` -- the name of the *entire system* or *project* your
      script/application is part of;

    * `component` -- the name of a particular *script* or *application*
      being executed (for a CLI script: its *basename*);

    * `component_type` -- a conventional label of the *type* of that
      script or application, agreed upon in your organization (such
      as: `"web"`, `"parser"`, `"collector"`...).

* And that's it! Everything else is optional (but probably worth a try,
  so you might want to read on).

***

### Library Overview

The tools provided by `certlib.log` are intended for use with the standard
[`logging`][] module's toolset. Essentially, they enhance that toolset with
the following possibilities:

* to emit *structured* log entries -- each being a [`dict`][], hereinafter
  referred to as *output data* (serialized in JSON format before actually
  being emitted);

* to permanently assign to selected output data keys: *not only* constant
  *defaults*, but also dynamic factories of values, hereinafter referred
  to as *auto-makers*; each *auto-maker* is just an argumentless function
  (or method, or other callable), automatically called to produce a value
  for the respective key -- whenever a new [log record][logging.LogRecord]
  object is created by a logger (*always* in the thread in which the
  respective logger method call is made), before the log record is
  processed by any *handlers*, *filters* and *formatters*;

* to replace the legacy `%`-based style of log message formatting with
  the modern and more convenient `{}`-based one, or (when what you need
  to log is just data) to omit passing the text message altogether; both
  gained by giving a little tweak to each logger method call...

While it is possible to use each of these capabilities independently of
the others, the `certlib.log`'s stuff encourages combining them.

The next few sections discuss the two main tools provided by the library:
[`StructuredLogsFormatter`][] and [`xm`][].

***

## **Tool: `StructuredLogsFormatter`**

To make the standard [`logging`][] module's machinery able
to emit structured log entries (each being a JSON-serialized
[`dict`][]), you need to configure it to employ an instance
of [`certlib.log.StructuredLogsFormatter`][] as a *formatter*.

!!! note

    Directly below it is shown how to do that in an *imperative* manner.
    You may prefer, however, a more *declarative* approach (especially
    if your program is not just a small script). In that case, please
    check out at least one of the following subsections (but first
    **read everything above them as well!**):

    * **[`logging.config.dictConfig`-Style Configuration Example](#loggingconfigdictconfig-style-configuration-example)**,
    * **[`logging.config.fileConfig`-Style Configuration Example](#loggingconfigfileconfig-style-configuration-example)**.

***

### Basic Configuration

Let us start by creating our [`StructuredLogsFormatter`][] instance
(obviously, the concrete values used in the following code snippet
are just sample ones -- to be replaced with values appropriate for
your program/system):

```python
import itertools
import json
import logging
import sys
from certlib.log import StructuredLogsFormatter

structured_logs_formatter = StructuredLogsFormatter(
    defaults={
        # Each key in this dict should be an *output data* key.
        # Each value specifies the *default value* for that key.
        # For example:
        "system": "MyOwn",
        "component": "Portal",
        "component_type": "web",
        "example_custom_default": 42,
    },
    auto_makers={
        # Each key in this dict should be an *output data* key.
        # Each value should be either some argumentless callable
        # (function) or a *dotted path* to such a callable. In
        # particular, that callable *may* be the `get()` method
        # of some `ContextVar` instance (see
        # https://docs.python.org/3/library/contextvars.html).
        # For example:

        # (here: dotted paths pointing to callables)
        "client_ip": "myown.portal.client_ip_context_var.get",
        "example_nano_time": "time.time_ns",

        # (here: a callable passed directly)
        "example_local_counter": itertools.count(1).__next__,
    },
    # The value of `serializer` should be either a callable (function)
    # that accepts exactly one argument (being a JSON-serializable dict)
    # and returns a str object, or a *dotted path* to such a callable.
    # Note: the following serializer is the default -- so, in fact, you
    # do not need to specify it. But the possibility to define a custom
    # serializer comes in handy when you want to use, e.g., a faster
    # alternative to the standard `json.dumps()` function (or even a
    # tool which serializes data in some other format...).
    serializer=json.dumps,
)
```

!!! info "See also"

    You may also want to look at the *reference documentation* for
    the **[`StructuredLogsFormatter`][]** class.

Technically, each of the three keyword arguments accepted by the
[`StructuredLogsFormatter`][] constructor is *optional*. However,
when it comes to the **`defaults`** and **`auto_makers`** ones,
you need to consider that:

* It is *required* that each of the following keys appears in *at least
  one* of those two mappings (in `defaults` and/or `auto_makers`):

    * `"system"` (the name of the *entire system* or *project* your
      script/application is part of; e.g.: `"My Funny System"`,
      [`"MWDB"`](https://github.com/CERT-Polska/mwdb-core),
      [`"n6"`](https://github.com/CERT-Polska/n6), etc.),

    * `"component"` (the name of a particular *script* or *application*
      being executed; for a CLI script it should be its *basename*),

    * `"component_type"` (a conventional label of the *type* of that
      script or application, agreed upon in your organization; e.g.:
      `"web"`, `"parser"`, `"collector"`...).

        * _[maybe TBD: suggest a list of **valid values** of `component_type`?]_

    !!! note

        If it is OK for you/your organization that some (or all) of the
        *output data* items listed above will remain unspecified, you can
        provide such a **`defaults`** mapping in which some (or all) of
        the aforementioned keys will be mapped to **[`None`][]** values.
        Then, the said requirement will still be met, even though such
        *void* items will be automatically omitted from the ultimate
        **[`defaults`][StructuredLogsFormatter.defaults]** collection.

        See also: **[`StructuredLogsFormatter.get_output_keys_required_in_defaults_or_auto_makers`][]**
        (the method which defines the said requirement).

* It is *recommended* (though not enforced) that each of the following
  keys, *if it is relevant* to the particular `component_type`, appears in
  *at least one* of those two mappings (in `defaults` and/or `auto_makers`,
  typically in the latter):

    * `"client_ip"` (the *real* IP of the client who communicates with us;
      for this information to be reliable, the way it is obtained needs
      to follow best practices specific to the protocol being used; for
      example, when it comes to HTTP, see:
      [https://httptoolkit.com/blog/what-is-x-forwarded-for](https://httptoolkit.com/blog/what-is-x-forwarded-for/));

    * `"user_id"`, `"request_id"`, etc.

    * _[TBD: more of the **recommended output data keys** to be suggested here]_.

!!! tip

    If the presence of some *output data* key makes sense only in
    a certain context (e.g., when handling a HTTP request...), just
    make the respective *auto-maker* return **[`None`][]** in any
    other contexts. Such *void* items are automatically omitted from
    *output data*.

Now we will prepare the *root logger*, attaching to it some handler
*with our formatter* set on it:

```python
# (continuing with the previous example)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.name = "stderr"
stderr_handler.setFormatter(structured_logs_formatter)  # <- Our formatter

root_logger.addHandler(stderr_handler)
```

!!! info "See also"

    You may also want to take a look at the relevant parts of the
    documentation for the standard **[`logging`][]** module.

***

### Basic Usage

OK. Once the stuff is configured, let us emit some structured log entries!

We can do that in the legacy (standard, yet old-fashioned) manner...

```python
import datetime as dt
import logging
import sys

logger = logging.getLogger(__name__)

# [...]

logger.info("Hello world!")

logger.warning("Hello %s!", sys.platform)

logger.error(
    "Here we have %x and %r.", sys.maxsize, sys.byteorder,
    extra={
        "example_stuff": [1, "foo", False],
        "other_example_item": {42: dt.datetime.now()},
    },
    exc_info=True,
)
```

...or (*better!*) by making use of the **[`certlib.log.xm`][]** tool:

```python
import datetime as dt
import ipaddress
import logging
import sys
from certlib.log import xm

logger = logging.getLogger(__name__)

# [...]

logger.info(xm("Hello world!"))

logger.warning(xm("Hello {}!", sys.platform))

logger.error(xm(
    "Here we have {:x} and {!r}.", sys.maxsize, sys.byteorder,
    example_stuff=[1, "foo", False],
    other_example_item={42: dt.datetime.now()},
    exc_info=True,
))

pure_data_dict = {
    'this': 123,
    'that': ipaddress.IPv4Address('192.168.0.42'),
    'there': 'example.com',
    'then': dt.datetime(2026, 1, 2, 3, 4, 56, tzinfo=dt.timezone.utc),
}
logger.info(xm(pure_data_dict))  # <- No text message at all.

logger.warning(xm(
    "{who} owns {fract:.2%} of all issues of {title!r} magazine.",
    who="John",
    fract=0.87239,
    title="Bajtek",
    first_issue_date=dt.date(1985, 9, 1),
))
```

!!! info "See also"

    To learn more about using the **`xm`** tool, see this guide's section
    **[Tool: `xm`](#tool-xm)** (below).

Regarding the last `logger.warning(...)` call in the example above, the
resultant JSON-serialized *output data* dict (i.e., the ultimate content
of the log entry to be emitted) could look like the following (note that
the serialized data presented here contains arbitrary example values for
many keys, and -- just for visual clarity -- we present it here as being
sorted by key, and with extra newlines/indentation):

```json
{
    "client_ip": "192.168.0.123",
    "component": "Portal",
    "component_type": "web",
    "example_custom_default": 42,
    "example_local_counter": 6,
    "example_nano_time": 1771629287019638820,
    "first_issue_date": "1985-09-01",
    "fract": 0.87239,
    "func": "<module>",
    "level": "WARNING",
    "levelno": 30,
    "lineno": 253,
    "logger": "myown.portal.example_module",
    "message": "John owns 87.24% of all issues of 'Bajtek' magazine.",
    "message_base": {
        "pattern": "{who} owns {fract:.2%} of all issues of {title!r} magazine."
    },
    "pid": 324485,
    "process_name": "MainProcess",
    "py_ver": "3.14.3.final.0",
    "script_args": [
        "/opt/MyOwn/conf/web/portal.wsgi"
    ],
    "src": "/opt/MyOwn/py/myown/portal/example_module.py",
    "system": "MyOwn",
    "thread_id": 139781835344768,
    "thread_name": "MainThread",
    "timestamp": "2026-02-20 23:14:47.019574Z",
    "title": "Bajtek",
    "who": "John"
}
```

!!! note

    As you can see, the **[`dt.date`][datetime.date]** instance provided
    as **`first_issue_date`**, before becoming an *output data* value,
    was converted to a string -- thanks to an automatic invocation of the
    **[`prepare_value`][StructuredLogsFormatter.prepare_value]** method
    (*before* the actual data serialization).

    All *output data* values are subject to preparation by that method
    (which processes them differenttly depending on their types...). By
    extending/overriding it in your **[`StructuredLogsFormatter`][]**
    subclass you can gain full control over that preparation.

    Nevertheless, you can get quite well just by sticking with the default
    implementation of that method.

***

### `logging.config.dictConfig`-Style Configuration Example

```python
import logging.config

logging_configuration_dict = {
    "formatters": {
        "structured": {
            "()": "certlib.log.StructuredLogsFormatter",
            "defaults": {
                # Each key in this dict should be an *output data* key.
                # Each value specifies the *default value* for that key.
                # For example:
                "system": "MyOwn",
                "component": "Portal",
                "component_type": "web",
                "example_custom_default": 42
                # ^ Important: by default, each of the "system", "component"
                #   and "component_type" keys is *required* to be included
                #   either *here* or in "auto_makers" (below). Note: *here*
                #   each of them can be assigned None -- if excluding this
                #   key from *output data* is OK for you/your organization.
            },
            "auto_makers": {
                # Each key in this dict should be an *output data* key.
                # Each value should be either some argumentless callable
                # (function) or a *dotted path* to such a callable. In
                # particular, that callable *may* be the `get()` method
                # of some `ContextVar` instance (see
                # https://docs.python.org/3/library/contextvars.html).
                # For example:
                "client_ip": "myown.portal.client_ip_context_var.get",
                "example_nano_time": "time.time_ns"
            },
            # The value of "serializer", if specified, should be either
            # a callable (function) which accepts exactly one argument
            # (being a JSON-serializable dict) and returns a str object,
            # or a *dotted path* to such a callable.
            "serializer": "some_package.faster_replacement_for_json_dumps"
        }
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stderr"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["stderr"]
    },
    "disable_existing_loggers": False,
    "version": 1
}

logging.config.dictConfig(logging_configuration_dict)
```

!!! tip

    Typically, applications load such a configuration dict from some file
    (usually in **[TOML][tomllib]**, **[YAML](https://pypi.org/project/PyYAML/)**
    or **[JSON][json]** format).

!!! info "See also"

    You can learn more about the **[`logging.config.dictConfig`][]**-specific
    configuration dict schema by referring to the **[relevant
    section](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema)**
    of the documentation for the standard `logging.config` module.

***

### `logging.config.fileConfig`-Style Configuration Example

```ini
[loggers]
keys = root

[handlers]
keys = stderr

[formatters]
keys = structured

[logger_root]
level = INFO
handlers = stderr

[handler_stderr]
class = StreamHandler
formatter = structured
args = (sys.stderr,)

[formatter_structured]
class = certlib.log.StructuredLogsFormatter
format = {
    "defaults": {
        # Each key in this dict should be an *output data* key.
        # Each value specifies the *default value* for that key.
        # For example:
        "system": "MyOwn",
        "component": "Portal",
        "component_type": "web",
        "example_custom_default": 42,
        # ^ Important: by default, each of the "system", "component"
        #   and "component_type" keys is *required* to be included
        #   either *here* or in "auto_makers" (below). Note: *here*
        #   each of them can be assigned None -- if excluding this
        #   key from *output data* is OK for you/your organization.
    },
    "auto_makers": {
        # Each key in this dict should be an *output data* key.
        # Each value should be a *dotted path* to some argumentless
        # callable (function). In particular, that callable *may* be
        # the `get()` method of some `ContextVar` instance (see
        # https://docs.python.org/3/library/contextvars.html).
        # For example:
        "client_ip": "myown.portal.client_ip_context_var.get",
        "example_nano_time": "time.time_ns",
    },
    # The value of "serializer", if specified, should be a *dotted path*
    # to a callable (function) which accepts exactly one argument (being
    # a JSON-serializable dict) and returns a str object.
    "serializer": "some_package.faster_replacement_for_json_dumps",
  }
# ^ *Note:* all non-comment and non-blank continuation lines, *including*
#   the one with the closing `}`, *must be indented* (by at least 1 space).
```

!!! tip

    If **[`logging.config.fileConfig`][]** is called by your code (rather
    than automatically by some framework/library...), you may want to set
    the **`disable_existing_loggers`** argument to **[`False`][]** (because
    if its default value, **[`True`][]**, is in effect, then some loggers
    created before that call may be turned off, which is usually not what
    you want). This is a general advice (not specific to `certlib.log`).

!!! info "See also"

    You can learn more about the **[`logging.config.fileConfig`][]**-specific
    configuration format by referring to the **[relevant
    section](https://docs.python.org/3/library/logging.config.html#logging-config-fileformat)**
    of the documentation for the standard `logging.config` module.

***

## **Tool: `xm`**

Essentially, the purpose of [`xm`][] is two-fold:

* to make it more convenient to emit *structured log entries* (each being
  representable as a [`dict`][]), especially if a [`StructuredLogsFormatter`][]
  is in use;

* if you choose the traditional *text-message-focused style* of logging
  (rather than a *pure-data-focused*, messageless one) -- to easily replace
  the legacy `%`-based log message formatting style with the modern and
  more convenient `{}`-based one (regardless of what formatter is in use).

!!! note

    **[`xm`][]** is just a convenience alias of **[`ExtendedMessage`][]**
    (the latter is the actual name of the class, but the former is
    definitely more handy when you want to log a message or data).

Let examples speak...

***

### Dealing with Pure Data

Below -- a couple of examples of logging just some data (without the need
to specify any text message).

```python
import logging
from certlib.log import xm

logger = logging.getLogger(__name__)

# Logging pure data:
logger.info(xm(
    some_key=["example", "data"],
    another=lambda: 42,  # (<- function/method: to be called by formatter)
    yet_another={"abc": 1.0, "qwerty": [True, False]},
))

# Same as above, but here we pass our data just *as one dict*:
my_data = {
    "some_key": ["example", "data"],
    "another": lambda: 42,  # (<- function/method: to be called by formatter)
    "yet_another": {"abc": 1.0, "qwerty": [True, False]},
}
logger.info(xm(my_data))
```

!!! tip

    Regarding the `"another"` item in the above examples as well as some
    of the items/arguments that appear in the next subsection's examples:
    if you pass a function/method (in particular, a `lambda` expression)
    instead of a plain value, then it will be *called* (by a formatter of
    any type, not necessarily a `StructuredLogsFormatter`) to obtain the
    actual value. Note that, by default, the mechanism is applied *only*
    if you pass a *function* or *method* object -- *not* just an arbitrary
    callable object.

    In practice, this feature is useful in cases when the creation of
    certain values is costly, so that you would prefer that to be done
    *only* if the log entry is to be actually formatted and emitted.

***

### Modern Formatting Style

Below there are a few examples of traditional *text-message-focused*
logging, but -- what using the [`xm`][] tool makes possible -- with the
modern and convenient [`{}`-based style of message formatting](https://docs.python.org/3/library/string.html#format-string-syntax)
(rather than the legacy, less convenient and less powerful, `%`-based one).

```python
import datetime as dt
import logging
from certlib.log import xm

logger = logging.getLogger(__name__)

some_name = "foo"
some_value = "Bar"

logger.info(xm(
    "Note: {} is {!r} (in {:%Y-%m})",
    some_name, some_value,
    dt.date.today,  # (<- function/method: to be called by formatter)
))
```

The resultant message will be: `"Note: foo is 'Bar' (in 2026-02)"`
(assuming that, for this particular example, the [`dt.date.today`][datetime.date.today]
class method would return an instance of [`dt.date`][datetime.date]
representing a *February 2026* date, e.g., one equal to `dt.date(2026,
2, 21)`).

What it means when the logging system is configured to employ a
[`StructuredLogsFormatter`][], is that:

* the formatted message will appear in the JSON-serialized *output
  data* as the item: `"message": "Note: foo is 'Bar' (in 2026-02)"`,
* and the raw message pattern will also be included, like this:
  `"message_base": {"pattern": "Note: {} is {!r} (in {:%Y-%m})"}`.

!!! info

    Please note that when you use **[`xm`][]**, you still benefit from
    the standard mechanism of deferring message formatting until the log
    entry really needs to be emitted (regardless of what formatter is in
    use).

The code in the next example does the same as above; the only difference
is that here the *replacement fields* in the message pattern are explicitly
numbered:

```python
logger.info(xm(
    "Note: {0} is {1!r} (in {2:%Y-%m})",
    some_name, some_value,
    dt.date.today,  # (<- function/method: to be called by formatter)
))
```

Below there is an example similar to the previous two, but with some of the
replacement fields being *named* (and, therefore, with the corresponding
*keyword arguments* specifying the values to be interpolated):

```python
logger.info(xm(
    "Note: {} is {val!r} (in {today:%Y-%m})",
    some_name,
    val=some_value,
    today=dt.date.today,  # (<- function/method: to be called by formatter)
))
```

It is worth noting that if a [`StructuredLogsFormatter`][] is in use,
then any *keyword arguments* (*named* ones) passed to [`xm`][], apart
from being used to fill in the respective replacement fields, are also
included as *output data* items. For example, *output data* resulting
from the `logger.info(...)` call in the last example will contain, among
others, the following items:

* `"message": "Note: foo is 'Bar' (in 2026-02)"`,
* `"message_base": {"pattern": "Note: {} is {val!r} (in {today:%Y-%m})"}`,
* `"val": "Bar"`,
* `"today": "2026-02-21"`.

And below there is almost the same call as previously, but with a couple
of extra keyword arguments (conveying some additional data, unrelated to
message formatting):

```python
logger.info(xm(
    "Note: {} is {val!r} (in {today:%Y-%m})",
    some_name,
    val=some_value,
    today=dt.date.today,          # (<- function/method: to be called...)
    something=lambda: 123456789,  # (<- function/method: to be called...)
    something_more=(1, 2, 3, 4, True, None, {5: [6789, 10]}),
))
```

In this case, the resultant *output data* generated by the
[`StructuredLogsFormatter`][]'s machinery will contain,
among others, the following items:

* `"message": "Note: foo is 'Bar' (in 2026-02)"`,
* `"message_base": {"pattern": "Note: {} is {val!r} (in {today:%Y-%m})"}`,
* `"val": "Bar"`,
* `"today": "2026-02-21"`,
* `"something": 123456789`,
* `"something_more": [1, 2, 3, 4, true, null, {"5": [6789, 10]}]`.

The entire resultant JSON-serialized *output data* (i.e., the ultimate
content of the log entry to be emitted) could look like the following
(note that the serialized data presented here contains arbitrary example
values for many keys, and -- just for visual clarity -- we present it
here as being sorted by key, and with extra newlines/indentation):

```json
{
    "client_ip": "192.168.0.123",
    "component": "Portal",
    "component_type": "web",
    "example_custom_default": 42,
    "example_local_counter": 4,
    "example_nano_time": 1771631594315719605,
    "func": "<module>",
    "level": "INFO",
    "levelno": 20,
    "lineno": 179,
    "logger": "myown.portal.another_example_module",
    "message": "Note: foo is 'Bar' (in 2026-02)",
    "message_base": {
        "pattern": "Note: {} is {val!r} (in {today:%Y-%m})"
    },
    "pid": 327578,
    "process_name": "MainProcess",
    "py_ver": "3.14.3.final.0",
    "script_args": [
        "/opt/MyOwn/conf/web/portal.wsgi"
    ],
    "something": 123456789,
    "something_more": [
        1, 2, 3, 4, true, null, {
            "5": [
                6789, 10
            ]
        }
    ],
    "src": "/opt/MyOwn/py/myown/portal/another_example_module.py",
    "system": "MyOwn",
    "thread_id": 140062429502336,
    "thread_name": "MainThread",
    "timestamp": "2026-02-20 23:53:14.315296Z",
    "today": "2026-02-21",
    "val": "Bar"
}
```

!!! info "See also"

    You may also want to look at the *reference documentation* for the
    **[`ExtendedMessage`][]** class (among other things, you will find
    there information about three special arguments you can also pass
    to **`xm`** -- namely: **`exc_info`**, **`stack_info`** and
    **`stacklevel`**).

***

## **Advanced Topics and Finer Points**

### More About `StructuredLogsFormatter` (Including Subclassing)

If you have not read the *reference documentation* for the
[`StructuredLogsFormatter`][] class yet, you are strongly encouraged to
do so. Among other things, you will find there a list of hook methods
that can be extended/overridden in your subclasses. Apart from that, the
said documentation includes (also in the individual descriptions of
those hook methods) valuable information about other elements of the
`StructuredLogsFormatter`'s interface and behavior.

***

### Other Stuff Provided by `certlib.log`

Besides [`StructuredLogsFormatter`][] and [`xm`][] ([`ExtendedMessage`][]),
the `certlib.log` module provides the following public stuff:

* the [`make_constant_value_provider`][] function (a minor helper,
  useful when you need to create an *auto-maker* that will always
  return the same value);

* the [`register_log_record_attr_auto_maker`][] and
  [`unregister_log_record_attr_auto_maker`][] functions
  (typically, they do not need to be used directly --
  see the *reference documentation* for each of them...);

* the [`COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS`][] constant (its value
  is returned by the `StructuredLogsFormatter`'s default implementation of
  the [`get_output_keys_required_in_defaults_or_auto_makers`][.StructuredLogsFormatter.get_output_keys_required_in_defaults_or_auto_makers]
  method);

* the [`STANDARD_RECORD_ATTR_TO_OUTPUT_KEY`][] constant
  (defines the standard mapping of [log record attribute
  names](https://docs.python.org/3/library/logging.html#logrecord-attributes)
  to actual *output data* keys; that mapping is used by the
  `StructuredLogsFormatter`'s default implementation of the
  [`make_base_record_attr_to_output_key`][.StructuredLogsFormatter.make_base_record_attr_to_output_key]
  method).

***

### Roadmap Outline

Future ideas under consideration include:

* [`StructuredLogsFormatter`][]: add the ability to specify keys related
  to *sensitive* data -- so that values assigned to them in *output data*
  will be automatically masked/anonymized.

* [`xm`][]: add dedicated suport for [`pattern`][ExtendedMessage.pattern]
  of type [`string.templatelib.Template`][] (available in Python 3.14 and
  newer).
"""


# mypy: disable_error_code = "unused-ignore"


from __future__ import annotations

import ast
import dataclasses
import datetime as dt
import decimal
import enum
import fractions
import functools
import importlib
import ipaddress
import json
import logging
import os.path
import reprlib
import sys
import threading
import traceback
import types
import uuid
from collections.abc import (
    Callable,
    Iterator,
    Mapping,
    Sequence,
    Set,
)
from inspect import (
    Parameter,
    signature,
)
from typing import (
    Any,
    ClassVar,
    Final,
    Literal,
    TypeVar,
    cast,
    overload,
)


__all__ = (
    'COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS',
    'STANDARD_RECORD_ATTR_TO_OUTPUT_KEY',
    'StructuredLogsFormatter',
    'ExtendedMessage',
    'xm',
    'make_constant_value_provider',
    'register_log_record_attr_auto_maker',
    'unregister_log_record_attr_auto_maker',
)


COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS: Final[Set[str]] = frozenset({
    # These items are to be provided automatically (at least by default)
    # by the `StructuredLogsFormatter`'s machinery.
    'py_ver',
    'script_args',

    # These items *need* to be provided individually per system/component
    # (in `StructuredLogsFormatter` configuration, or by subclassing...).
    'system',
    'component',
    'component_type',
})


STANDARD_RECORD_ATTR_TO_OUTPUT_KEY: Final[Mapping[str, str | None]] = types.MappingProxyType({
    'asctime': 'timestamp',
    'exc_info': 'exc_info',
    'exc_text': 'exc_text',
    'funcName': 'func',
    'levelname': 'level',
    'levelno': 'levelno',
    'lineno': 'lineno',
    'message': 'message',
    'msg': 'message_base',
    'name': 'logger',
    'pathname': 'src',
    'process': 'pid',
    'processName': 'process_name',
    'stack_info': 'stack_info',
    'thread': 'thread_id',
    'threadName': 'thread_name',
    'taskName': 'async_task_name',

    # The following log record attributes are
    # to be *discarded* (at least by default):
    'args': None,       # <- Info it conveys is typically redundant (with respect to `message`).
    'created': None,    # <- The `asctime` attribute provides sufficient info.
    'filename': None,   # <- The `pathname` attribute provides sufficient info.
    'module': None,     # <- Redundant and confusing (just `filename` without its suffix).
    'msecs': None,      # <- The `asctime` attribute provides sufficient info.
    'relativeCreated': None,   # <- Confusing and hardly useful. (Uptime in milliseconds? Meh...)
})


class StructuredLogsFormatter(logging.Formatter):

    """
    A subclass of [`logging.Formatter`][] to form structured log entries.

    ***

    **Constructor arguments** (all *keyword-only*, all *optional*):

    * **`defaults`** (a [`dict`][] or other mapping; default: `{}`):
      maps *output data* keys to values each of which specifies
      the *default value* for the respective key (see also the
      [`make_base_defaults`][] method...).

    * **`auto_makers`** (a [`dict`][] or other mapping; default: `{}`):
      maps *output data* keys to respective *auto-makers* (argumentless
      value factories). Each *auto-maker* can be specified either
      directly or as a string being a *dotted path* (*importable
      dotted name*) that points to an *auto-maker* (see also the
      [`make_base_auto_makers`][] method...).

    * **`serializer`** (a function or other callable; default: [`json.dumps`][]):
      expected to take one argument being a (JSON-serializable) [`dict`][]
      and return a [`str`][] (presumably, a JSON-serialized form of
      the given data, even though you may decide to use some other
      serialization format if it is OK for you/your organization).
      A string being a *dotted path* (*importable dotted name*)
      pointing to such a function (callable) can also be passed.

    **Alternatively**, a mapping (especially a [`dict`][]) of keyword
    arguments compatible with the primary signature described above, or
    an [`ast.literal_eval`][]-evaluable string representing such a mapping
    (`dict`), can be passed to the [`StructuredLogsFormatter`][] constructor
    as the *first positional argument*. In that case, any extra arguments
    specific to the [`logging.Formatter`][] constructor are *accepted but
    ignored* -- *provided that* the value of each is equivalent to its
    default value (if not, [`TypeError`][] is raised). This allows you
    to configure a `StructuredLogsFormatter` even if you are using the
    [`logging.config.fileConfig`][]-specific configuration format (which,
    despite its limitations, is still quite popular).

    !!! warning "Interface restriction"

        The **`serializer`** callable should *not* mutate the argument it
        takes or anything inside it (regardless of the level of nesting,
        if any nested data is present). If some data needs to be modified,
        a completely *new* object should be created. Doing otherwise will
        result in undefined behavior.

    This class defines the following extendable/overridable hook methods:

    * [`get_output_keys_required_in_defaults_or_auto_makers`][]
    * [`make_base_defaults`][]
    * [`make_base_auto_makers`][]
    * [`make_base_record_attr_to_output_key`][]
    * [`format_timestamp`][]
    * [`get_prepared_output_data`][]
    * [`prepare_value`][]
    * [`prepare_submapping_key`][]
    * [`serialize_prepared_output_data`][]

    In some of the individual descriptions of these methods, several other
    elements of the `StructuredLogsFormatter`'s interface and behavior are
    also discussed -- in particular, the following instance attributes:

    * [`defaults`][]
    * [`auto_makers`][]
    * [`auto_made_record_attr_prefix`][]
    * [`record_attr_to_output_key`][]
    * [`serializer`][]

    !!! warning "Interface restriction"

        Once an instance of **`StructuredLogsFormatter`** is initialized,
        the instance attributes listed above should be treated as
        _**read-only**_ and _**immutable**_ ones (together with all their
        contents, regardless of the level of nesting, if any nested data
        is present). Doing otherwise will result in undefined behavior.

    !!! note

        When it comes to customizing the format of log entry *timestamps*,
        the related attributes defined by the [`logging.Formatter`][] base
        class (`converter`, `default_time_format`, `default_msec_format`)
        are _**ignored**_ by the machinery of **`StructuredLogsFormatter`**.

        To learn how to actually *customize timestamp formatting*, please
        refer to the description of the **`StructuredLogsFormatter`**'s
        **[`format_timestamp`][]** method.


    !!! warning "Additional requirement"

        Regarding the initialization of a **`StructuredLogsFormatter`**
        instance, it is also required that every *output data* key (just
        *key*, as we are *not* talking about *output data* values here)
        appearing in any of the mappings listed below -- be a *string*
        and *not* exceed 200 characters (otherwise, respectively,
        [`TypeError`][] or [`ValueError`][] will be raised by the
        constructor). The mappings covered by this requirement are:

        * that returned by the **[`make_base_defaults`][]** method,

        * the **`defaults`** argument to the
          [constructor][StructuredLogsFormatter] (if actually passed),

        * that returned by the **[`make_base_auto_makers`][]** method,

        * the **`auto_makers`** argument to the
          [constructor][StructuredLogsFormatter] (if actually passed),

        * that returned by the **[`make_base_record_attr_to_output_key`][]**
          method (note that the said requirement applies to *output data*
          keys -- which, when it comes to this mapping, are its *values*,
          not its *keys*; and note that this mapping's values are also
          allowed to be [`None`][]).

    !!! info "See also"

        For extra information about **`StructuredLogsFormatter`**,
        including a bunch of usage examples and configuration tips,
        see the **[Tool: `StructuredLogsFormatter`](guide.md#certlib.log--tool-structuredlogsformatter)**
        section of the *User's Guide*.
    """

    #
    # Attributes and instance lifecycle (public stuff)

    # * This-class-specific instance attributes:

    defaults: Final[Mapping[str, Any]]
    auto_makers: Final[Mapping[str, Callable[[], object]]]
    auto_made_record_attr_prefix: Final[str]
    record_attr_to_output_key: Final[Mapping[str, str | None]]
    serializer: Final[Callable[[dict[str, Any]], str]]

    # * Instance-lifecycle-related stuff:

    @overload
    def __init__(
        self,
        *,
        defaults: Mapping[str, object] | None = None,
        auto_makers: Mapping[str, str | Callable[[], object]] | None = None,
        serializer: str | Callable[[dict[str, Any]], str] = json.dumps,
    ):
        ...

    @overload
    # A variant for cases when passing real *keyword arguments* is
    # impossible (e.g., when using `logging.config.fileConfig()`)
    def __init__(
        self,

        # This is required to be a mapping (e.g., a dict) of keyword
        # arguments compatible with the first `__init__()` signature
        # variant (declared above), or a string that will result in
        # such a mapping if evaluated with `ast.literal_eval()`.
        dict_of_kwargs_compatible_with_primary_signature: str | Mapping[str, Any],
        /,

        # Any extra `logging.Formatter`-specific arguments are to be
        # accepted -- and ignored -- as long as the value of each is
        # equivalent to the respective `logging.Formatter`'s default.
        *args_ignored_if_matching_respective_logging_Formatter_defaults: Any,     # noqa
        **kwargs_ignored_if_matching_respective_logging_Formatter_defaults: Any,  # noqa
    ):
        ...

    def __init__(self, *args: Any, **kwargs: Any):
        arguments = self._resolve_init_arguments(*args, **kwargs)

        given_defaults = arguments.pop('defaults', None) or {}
        given_auto_makers = arguments.pop('auto_makers', None) or {}
        given_serializer = arguments.pop('serializer', json.dumps)

        if arguments:
            raise TypeError(
                f'{type(self).__init__.__qualname__}() got unexpected '
                f'keyword arguments: {", ".join(map(ascii, arguments))}'
            )

        super().__init__()

        unfiltered_defaults = self._get_unfiltered_defaults(given_defaults)
        unprefixed_auto_makers = self._get_unprefixed_auto_makers(given_auto_makers)
        self._check_output_keys_required_in_defaults_or_auto_makers(
            unfiltered_defaults,
            unprefixed_auto_makers,
        )

        actual_defaults = self._get_actual_defaults(unfiltered_defaults)
        auto_made_record_attr_prefix = self._get_auto_made_record_attr_prefix()
        actual_auto_makers = self._get_actual_auto_makers(
            auto_made_record_attr_prefix,
            unprefixed_auto_makers,
        )
        self.defaults = actual_defaults
        self.auto_makers = actual_auto_makers
        self.auto_made_record_attr_prefix = auto_made_record_attr_prefix

        self.record_attr_to_output_key = self._get_record_attr_to_output_key()
        self.serializer = self._get_actual_serializer(given_serializer)

        for rec_attr, auto_maker in self.auto_makers.items():
            register_log_record_attr_auto_maker(rec_attr, auto_maker)

    def unregister_auto_makers(self) -> None:
        """
        A rarely useful method: you should invoke it on an instance
        of `StructuredLogsFormatter` *only when* you need to stop
        using that instance but continue using any `logging` stuff
        during further program execution (this does not seem to be
        a common case).
        """
        for rec_attr in self.auto_makers.keys():
            unregister_log_record_attr_auto_maker(rec_attr)

    #
    # Overridden/extended methods of `logging.Formatter`

    def format(self, record: logging.LogRecord) -> str:
        """
        Overrides the [`logging.Formatter`'s
        implementation][logging.Formatter.format] with
        a `StructuredLogsFormatter`-specific one.

        In *some* respects, the `StructuredLogsFormatter`'s implementation
        of this method is similar to the `logging.Formatter`'s original. In
        particular, it makes use of the [`usesTime`][], [`formatTime`][],
        [`formatMessage`][] and [`formatException`][logging.Formatter.formatException]
        methods in a similar way, and assigns values to the same log record
        attributes: [`message`, `asctime` and `exc_text`](https://docs.python.org/3/library/logging.html#logrecord-attributes),
        making doing so subject to the same conditions (where applicable).
        However, it differs from the original in the following ways:

        * of the methods mentioned above, the `formatMessage` one is
          always invoked last (in particular, *after* the log record's
          `exc_text` attribute is possibly set to a value returned by
          `formatException`);

        * the string returned by `formatMessage` becomes the return value
          of *this* method (so this method *never* appends to that string
          any *formatted traceback* or *formatted stack information*, and
          it does *not* invoke [`formatStack`][logging.Formatter.formatStack]
          either); that string is supposed to represent the *output data*
          dict after serialization (therefore, it should already include,
          among others, any exception/stack information, if such stuff was
          requested and obtained);

        * regarding how the target value of the log record's `message`
          attribute is determined: if the `msg` attribute of the given
          log record is an instance of [`ExtendedMessage`][] ([`xm`][]),
          then that instance's [`get_message_value`][ExtendedMessage.get_message_value]
          method is invoked (directly), *instead* of the log record's
          method [`getMessage`][logging.LogRecord.getMessage].
        """
        # (Compare to the source code of `logging.Formatter.format()`...)
        msg = getattr(record, 'msg', None)
        if isinstance(msg, ExtendedMessage):
            if args := getattr(record, 'args', None):
                raise TypeError(
                    f"the specified log message base is an instance "
                    f"of {ExtendedMessage.__qualname__} ({msg=!a}); "
                    f"in such a case, any positional arguments to "
                    f"format the log message should have been passed "
                    f"to the `{ExtendedMessage.__qualname__}(...)` "
                    f"(or `xm(...)`) call, not to the logger method "
                    f"call itself (*args passed to it: {args!a})"
                )
            record.message = msg.get_message_value()
        else:
            record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        return self.formatMessage(record)

    def usesTime(self) -> bool:
        """
        Overrides the [`logging.Formatter`][]'s implementation with one
        that always returns [`True`][].
        """
        return True

    def formatTime(
        self,
        record: logging.LogRecord,
        datefmt: str | None = None,
    ) -> str:
        """
        Overrides the [`logging.Formatter`'s
        implementation][logging.Formatter.formatTime] with one that
        delegates its entire job to the [`format_timestamp`][] method
        (a `StructuredLogsFormatter`-specific one), but first checks
        if the **`datefmt`** argument is [`None`][] (if it is anything
        else, [`TypeError`][] is raised).
        """
        if datefmt is not None:
            slf = StructuredLogsFormatter.__qualname__
            slf_format_timestamp = f'{StructuredLogsFormatter.format_timestamp.__qualname__}()'
            slf_formatTime = f'{StructuredLogsFormatter.formatTime.__qualname__}()'  # noqa
            raise TypeError(
                f"{datefmt=!a}, whereas for a `{__name__}.{slf}`-derived "
                f"formatter it should be None. To customize timestamp "
                f"formatting in your logs, instead of trying to set "
                f"`datefmt` or other `logging.Formatter`-specific stuff "
                f"(*not* used by the `{slf}`'s machinery!), you should "
                f"rather extend/override (in your custom subclass) the "
                f"`{slf_format_timestamp}` method. (Alternatively, instead "
                f"of that, you might decide to completely override the "
                f"`{slf_formatTime}` method, providing an implementation "
                f"which, for example, would use the `logging.Formatter`'s "
                f"legacy timestamp-formatting-related stuff, without any "
                f"use of the `{slf_format_timestamp}` method...)"
            )
        return self.format_timestamp(record)

    def formatMessage(self, record: logging.LogRecord) -> str:
        """
        Overrides the [`logging.Formatter`][]'s implementation with
        one that:

        * obtains a ready *output data* dict by applying the
          [`get_prepared_output_data`][] method to the given
          log record;

        * applies the [`serialize_prepared_output_data`][]
          method to the obtained *output data* dict, and
          returns the result.

        !!! note

            The **`formatMessage`** name may be slightly misleading. Let
            us emphasize that the job of this method is *always* -- also
            in the case of the original **`logging.Formatter`** class --
            to format the crux of the _**entire**_ log entry, _**not**_
            just the value of the log record's **`message`** attribute.
            Formatting the latter is the job of the log record's
            **[`getMessage`][logging.LogRecord.getMessage]** method,
            or -- when the machinery of **`StructuredLogsFormatter`**
            deals with an **[`ExtendedMessage`][]** (**[`xm`][]**)
            instance -- of the **[`get_message_value`][ExtendedMessage.get_message_value]**
            method of that instance.
        """
        output_data = self.get_prepared_output_data(record)
        return self.serialize_prepared_output_data(output_data)

    #
    # This-class-specific overridable/extendable hooks (+ related constants)

    def get_output_keys_required_in_defaults_or_auto_makers(self) -> Set[str]:
        """
        A hook method: extend it in a subclass to impose (more)
        *output data* keys *required to be specified* for the
        purpose of setting [`defaults`][] and [`auto_makers`][].

        !!! note

            You can also extend/override this method to define *fewer*
            required keys than by default (perhaps even *no* one) if this
            is OK for you/your organization.

        To be more precise: this method's return value defines the set of
        keys *required to be included* in *at least one* of the following
        mappings:

        * that returned by the [`make_base_defaults`][] method,

        * the **`defaults`** argument to the
          [constructor][StructuredLogsFormatter] (if actually passed),

        * that returned by the [`make_base_auto_makers`][] method,

        * the **`auto_makers`** argument to the
          [constructor][StructuredLogsFormatter] (if actually passed).

        Whether this requirement is satisfied is checked during the
        formatter initialization. If the check fails, [`KeyError`][]
        is raised.

        !!! info

            The said requirement is considered satisfied _**also**_ if
            some (or all) of the required items are provided *only as
            defaults* (i.e., only by the **[`make_base_defaults`][]**'s
            result or the **`defaults`** constructor argument) *and* some
            (or all) of them define such *default values* that -- after
            being transformed by the **[`prepare_value`][]** method --
            are *void* values, such as [`None`][] (despite the fact that
            such *void* values are always *excluded* from the ultimate
            collection of *default values* -- see the *Related interfaces*
            note in the **[`make_base_defaults`][]** method's description).

        The default implementation of this method just uses the set of
        keys defined as [`COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS`][]
        (here it is worth noting that, because the default implementation
        of [`make_base_auto_makers`][] already provides *auto-makers*
        for certain keys, the *only* keys for which it is *required*
        to specify *default values* or *auto-makers* when invoking the
        [`StructuredLogsFormatter`][] constructor -- are: `"system"`,
        `"component"` and `"component_type"`).
        """
        assert isinstance(COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS, frozenset)
        return COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS

    def make_base_defaults(self) -> Mapping[str, object]:
        """
        A hook method: extend it in a subclass to define basic *default
        values* for output.

        Automatically invoked on the formatter initialization. Each key in
        the resultant mapping needs to be an *output data* key, and each
        value in that mapping needs to be the desired *default value* for
        that key.

        The default implementation of this method returns an empty mapping.

        !!! info "Related interfaces"

            For every instance, the **[`defaults`][]** mapping (which is
            supposed to specify all *default values* for any *output data*
            to be generated by the instance) is based on this method's
            result, but is then updated with all items from the **`defaults`**
            [constructor argument][StructuredLogsFormatter] (if given), and
            adjusted by applying the **[`prepare_value`][]** method to each
            value, and -- then -- by deleting each key to which a *void*
            value is assigned (by *void* value we mean any *falsy* value
            that is *not equal* to `0`, for example: [`None`][], `""`,
            `[]` or `{}` -- but _**not:**_ [`False`][], `0`, `0.0`, etc.).
        """
        return {}

    def make_base_auto_makers(self) -> Mapping[str, str | Callable[[], object]]:
        """
        A hook method: extend it in a subclass to define (more)
        *auto-makers* for output.

        Automatically invoked on the formatter initialization. Each key
        in the resultant mapping needs to be an *output data* key, and
        each value in that mapping needs to be either an *auto-maker*
        or a *dotted path* (*importable dotted name*) that points to an
        *auto-maker*. Each *auto-maker* is supposed to be an *argumentless
        function* (or *callable object* of some other type) returning --
        whenever it is called -- a candidate for an *output data* value
        (to be assigned to the respective *output data* key).

        !!! info "See also"

            You may want to learn more about *auto-makers*
            themselves by referring to the description of the
            **[`register_log_record_attr_auto_maker`][]** function
            (the machinery of **`StructuredLogsFormatter`**
            automatically makes use of that function, as appropriate).

        It should also be noted, given how the default implementation of the
        [`get_prepared_output_data`][] method works, that every candidate for
        an *output data* value -- including those produced by *auto-makers*
        -- will be transformed by applying the [`prepare_value`][] method
        to it. Furthermore, whenever the result of this transformation
        is a *void* value (by which we mean any *falsy* value *not equal*
        to `0`, for example: [`None`][], `""`, `[]` or `{}` -- but
        _**not**_ [`False`][], `0`, `0.0`, etc.), then the respective
        key will *not* be included in the *output data* dict (*even*
        if a *default value* is defined for that key; and *even* if
        that key was among those included in the set returned by the
        [`get_output_keys_required_in_defaults_or_auto_makers`][] method
        when the formatter instance was initialized).

        The default implementation of this method provides a couple
        of *auto-makers* which acquire some basic information about
        the execution environment (e.g., the Python version).

        !!! info "Related interfaces"

            For every instance, the **[`auto_makers`][]** mapping
            (which is supposed to specify all *auto-makers* related
            to the instance) is based on this method's result, but
            is then updated with all items from the **`auto_makers`**
            [constructor argument][StructuredLogsFormatter] (if given),
            and -- then -- adjusted by prefixing each key with the value
            of the **[`auto_made_record_attr_prefix`][]** attribute
            (which is an automatically generated string -- *different*
            for each instance of **`StructuredLogsFormatter`**).

            (Therefore -- concerning the stuff produced by a particular
            formatter instance's *auto-makers* -- the respective
            *output data* items will be obtained by picking those
            log record object's attributes whose names are prefixed
            with the formatter's **`auto_made_record_attr_prefix`**
            and using those names *with that prefix removed* as the
            corresponding *output data* keys. On the other hand, the
            formatter will *ignore* any record attribute names prefixed
            with **`auto_made_record_attr_prefix`** of any *other*
            formatter instances, as if such attributes did not exist.
            Thanks to that, more than one **`StructuredLogsFormatter`**
            can be used -- and they will work independently of each
            other, handling just one's own *auto-made* stuff.)
        """
        return {
            key: make_constant_value_provider(value)
            for key, value in (
                ('py_ver', '.'.join(map(str, (sys.version_info or ())))),
                ('script_args', tuple(sys.argv or ())),
            )
        }

    def make_base_record_attr_to_output_key(self) -> Mapping[str, str | None]:
        """
        A hook method: extend it in a subclass to modify the mapping of
        [log record attribute names](https://docs.python.org/3/library/logging.html#logrecord-attributes)
        to actual *output data* keys.

        Automatically invoked on the formatter initialization. Each key
        in the resultant mapping needs to be the name of a (perhaps just
        hypothetic) log record attribute, and each value in that mapping
        needs to be either the corresponding *output data* key or [`None`][].
        In the latter case -- given how the default implementation of the
        [`get_prepared_output_data`][] method works -- the attribute will
        always be omitted whenever *output data* is generated (note that
        this does *not* apply to log record attributes *not included* in
        the mapping).

        The default implementation of this method returns a mapping that
        contains all items of [`STANDARD_RECORD_ATTR_TO_OUTPUT_KEY`][].
        In many cases this will be quite sufficient.

        !!! info "Related interfaces"

            For every instance, the **[`record_attr_to_output_key`][]**
            mapping (which is supposed to specify the ultimate mapping of
            log record objects' attribute names to actual keys in *output
            data*) is based on this method's result, but is then updated
            with items suitably derived from **[`auto_makers`][]** (to
            cause that any log record attribute name prefixed with the
            instance's **[`auto_made_record_attr_prefix`][]** is mapped
            to an *output data* key being just the unprefixed version of
            that name; see the *Related interfaces* note in the description
            of the **[`make_base_auto_makers`][]** method).
        """
        return dict(STANDARD_RECORD_ATTR_TO_OUTPUT_KEY)

    def format_timestamp(
        self,
        record: logging.LogRecord,
        *,
        timezone: dt.tzinfo | None = dt.timezone.utc,
        timestamp_as_datetime: Callable[[float, dt.tzinfo | None], dt.datetime] = (
            dt.datetime.fromtimestamp
        ),
        utc_offset_to_custom_suffix: Mapping[dt.timedelta | None, str] = types.MappingProxyType({
            # By default, if the suffix were to be
            # `+00:00`, we want it to be `Z` instead
            # (as it means the same but is shorter).
            dt.timedelta(0): 'Z',

            # By default, if there is no explicit
            # timezone information, we want to
            # emphasize this in a visible way.
            None: ' <UNCERTAIN TIMEZONE>',
        }),
    ) -> str:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how, for each log entry, the *formatted timestamp* (`asctime`) is
        determined.

        This method is invoked by the [`formatTime`][] method, with a log
        record (typically, an instance of [`logging.LogRecord`][]) as the
        sole argument. The log record is expected to have its [`created`
        attribute](https://docs.python.org/3/library/logging.html#logrecord-attributes)
        already set to a [`float`][] number representing a Unix timestamp.

        What should be returned by this method is a string (presumably,
        derived somehow from the aforementioned `created` attribute of
        the log record) that will later be assigned (by the [`format`][]
        method) to the log record's `asctime` attribute.

        The default implementation of this method should be sufficient
        in most cases. It converts the value of the given log record's
        `created` attribute to a string being an *ISO-8601-compliant*
        date and time representation, with *microsecond* resolution.
        If *no optional keyword arguments* are given (which is how
        this method is invoked by `formatTime`), the resultant time
        representation is a *UTC* one (with `Z`, rather than `+00:00`,
        as its suffix), e.g.: `"2026-03-15 13:48:56.726403Z"`.

        !!! info

            The [`logging.Formatter`][]-specific attributes related to
            timestamp formatting (`converter`, `default_time_format` and
            `default_msec_format`) are _**ignored**_.

        !!! tip

            When extending this method in a subclass, you may want to make
            your custom implementation invoke the default one with some
            keyword arguments specified. In such a case, you may want to
            reach for their default values defined by the signature of
            **[`StructuredLogsFormatter.format_timestamp`][]**; if so, refer
            to the **[`StructuredLogsFormatter.FORMAT_TIMESTAMP_DEFAULT_KWARGS`][]**
            mapping. For example:

            ```python
            import datetime as dt
            import types
            from certlib.log import StructuredLogsFormatter

            class EstTimezoneOrientedStructuredLogsFormatter(StructuredLogsFormatter):

                UTC_OFFSET_FOR_EST = dt.timedelta(hours=(-5))

                DEFAULT_TIMEZONE = dt.timezone(UTC_OFFSET_FOR_EST)
                DEFAULT_UTC_OFFSET_TO_CUSTOM_SUFFIX = types.MappingProxyType({

                    # Let's use the base class's stuff in a *DRY* manner...
                    **StructuredLogsFormatter.FORMAT_TIMESTAMP_DEFAULT_KWARGS[
                        'utc_offset_to_custom_suffix'
                    ],

                    # ...and extend it with this-class-specific stuff:
                    **{
                        # If the suffix were to be `-05:00`,
                        # we want it to be ` EST` instead.
                        UTC_OFFSET_FOR_EST: ' EST',
                    },
                })

                def format_timestamp(
                    self,
                    record,
                    *,
                    timezone=DEFAULT_TIMEZONE,
                    utc_offset_to_custom_suffix=DEFAULT_UTC_OFFSET_TO_CUSTOM_SUFFIX,
                    **kwargs,
                ):
                    return super().format_timestamp(
                        record,
                        timezone=timezone,
                        utc_offset_to_custom_suffix=utc_offset_to_custom_suffix,
                        **kwargs,
                    )
            ```
        """
        dt_timestamp = timestamp_as_datetime(record.created, timezone)
        custom_suffix = utc_offset_to_custom_suffix.get(dt_timestamp.utcoffset())
        if custom_suffix is None:
            return dt_timestamp.isoformat(' ', 'microseconds')
        dt_without_tzinfo = dt_timestamp.replace(tzinfo=None)
        return f"{dt_without_tzinfo.isoformat(' ', 'microseconds')}{custom_suffix}"

    # Note: the `type: ignore` comment below prevents type checkers from
    # rejecting `Final` nested in `ClassVar` (which is OK in Python 3.13
    # and newer; and we use `from __future__ import annotations` anyway,
    # so at runtime we are safe regardless of Python version).
    FORMAT_TIMESTAMP_DEFAULT_KWARGS: ClassVar[Final[   # type: ignore
        Mapping[str, Any]
    ]] = types.MappingProxyType({
        p.name: p.default
        for p in signature(format_timestamp).parameters.values()
        if p.kind is Parameter.KEYWORD_ONLY
    })
    """
    Default values of all [`StructuredLogsFormatter.format_timestamp`][]'s
    *keyword-only* parameters (this mapping may come in handy when you
    extend that method in a subclass...).
    """

    def get_prepared_output_data(self, record: logging.LogRecord) -> dict[str, Any]:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how an *output data* dict is obtained from a log record object
        (which, at least typically, is a [`logging.LogRecord`][] instance).

        !!! warning "Subclass behavior restriction"

            This method should *not* mutate the given log record or any
            data it carries (regardless of the level of nesting, if any
            nested data is present). If some data needs to be modified,
            a completely *new* object should be created. Doing otherwise
            will result in undefined behavior.

        The default implementation of this method should be sufficient
        in most cases. To build a new *output data* dict, it digs into
        the given log record (and if that log record's `msg` attribute is
        an [`ExtendedMessage`][] instance -- also into that instance...).
        While doing that, it also looks at the formatter attributes:
        [`record_attr_to_output_key`][] (when determining *output data*
        keys; see also: [`make_base_record_attr_to_output_key`][]) and
        [`defaults`][] (to suitably complement the extracted *output
        data* with *default items*; see also: [`make_base_defaults`][]),
        as well as makes intensive use of the [`prepare_value`][] method
        (to ensure that each value in the resultant *output data* dict
        will be prepared for serialization). To make this description
        comprehensive, several details -- regarding the resultant *output
        data* dict's **top-level** *keys* and *values* -- need to be
        clarified:

        * when those **keys** and **values** are being determined based
          on the log record's contents, any log record attributes that
          have been created by *auto-makers* belonging to some *other*
          instances of `StructuredLogsFormatter` (i.e., *not* belonging
          to `self`) are *excluded* from consideration, meaning no *output
          data* items are created from them (for some low-level details,
          see the *Related interfaces* note in the description of the
          [`make_base_auto_makers`][] method...);

        * all existing log record attributes whose names are mapped in
          [`record_attr_to_output_key`][] to some *output data* **keys**
          -- are being *included* in the *output data* dict; this applies,
          in particular, to any log record attributes that have been
          created by *auto-makers* belonging to *this* (`self`) instance
          of `StructuredLogsFormatter` (see the *Related interfaces* note
          in the description of the [`make_base_record_attr_to_output_key`][]
          method...);

        * all existing log record attributes whose names are mapped
          in `record_attr_to_output_key` to [`None`][] -- are being
          *excluded*;

        * all existing log record attributes *not* created by any
          *auto-maker* and *not* included in `record_attr_to_output_key`
          -- are being *included* (!) in the *output data* dict, using
          each record attribute name as the corresponding *output data*
          **key** (as if it was mapped in `record_attr_to_output_key` to
          itself);

        * *only* **keys** that are instances of [`str`][] are ever included
          (meaning that any non-string keys, even if they appeared at some
          stage of processing, are always *excluded*), and every key is
          *truncated* to a maximum length of 200 characters (if it was
          longer); compare this with the treatment of *nested keys* (see
          the description of the [`prepare_submapping_key`][] method...);

        * when it comes to transforming every **value** by applying the
          aforementioned `prepare_value` method to it, if the result of
          this transformation turns out to be a *void* value (by which
          we mean any *falsy* value *not equal* to `0`, for example:
          [`None`][], `""`, `[]` or `{}` -- but _**not:**_ [`False`][],
          `0`, `0.0`, etc.), then the respective **key** is *excluded*
          (*even* if it should be included according to any other rule
          described above; and *even* if some *default value* is defined
          for that key!); note that *nested* values, even if *void*, are
          *never* subject to such an *exclusion* (at least if the default
          implementation of `prepare_value` is in use);

        * potential *item collisions* (which might occur, for example,
          when some **key** is present *both* in the `ExtendedMessage`'s
          [`data`][ExtendedMessage.data] mapping *and* among other data
          obtained from the log record's content, and the **value** to be
          assigned to that key varies depending on which of those two
          sources of information is checked) -- are avoided by suffixing
          problematic keys with one or more underscore character(s), as
          needed to prevent duplication; such cases are expected to be
          rare.

        !!! note

            The said key truncation occurs *before* the said key
            deduplication -- so it is possible, although very rare
            in practice, that appending underscore(s) to certain keys
            (as described above) will result in some keys ending up
            a little longer than 200 characters.
        """
        output_data: dict[str, Any] = {}
        actual_defaults = dict(self.defaults)
        handle_output_item = functools.partial(
            self._handle_output_item,
            self._DESIRED_MAX_KEY_LENGTH,
            self.prepare_value,
            actual_defaults,
            output_data,
        )

        xm_instance = getattr(record, 'msg', None)
        if isinstance(xm_instance, ExtendedMessage):
            self._extract_output_from_xm(record, xm_instance, handle_output_item)
        else:
            xm_instance = None

        self._extract_output_from_record(record, xm_instance, handle_output_item)

        for key, value_prepared in actual_defaults.items():
            output_data.setdefault(key, value_prepared)

        return output_data

    def prepare_value(
        self,
        value: object,
        *,
        to_str_types: tuple[type, ...] = (
            dt.date, dt.datetime, dt.time,
            decimal.Decimal, enum.Enum, fractions.Fraction,
            ipaddress.IPv4Address, ipaddress.IPv4Interface, ipaddress.IPv4Network,
            ipaddress.IPv6Address, ipaddress.IPv6Interface, ipaddress.IPv6Network,
            uuid.UUID,
        ),
        pass_thru_types: tuple[type, ...] = (str, int, float, bool, type(None)),
        exclude_from_seq_types: tuple[type, ...] = (str, bytes, bytearray),
        is_dataclass: Callable[[object], bool] = dataclasses.is_dataclass,  # type: ignore
        dataclass_as_dict: Callable[[Any], dict] = dataclasses.asdict,      # type: ignore
        last_resort: Callable[[object], str] = repr,
        **kwargs: Any,
    ) -> Any:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how every *value* in an *output data* dict is prepared before the
        actual data serialization.

        !!! warning "Subclass behavior restriction"

            This method should *not* mutate its argument or anything inside
            it (regardless of the level of nesting, if any nested data
            is present). If some data needs to be modified, a completely
            *new* object should be created. Doing otherwise will result
            in undefined behavior.

        The default implementation of this method should be sufficient
        in most cases. It converts any *value* (even such one that is
        deeply nested inside sequences/mappings -- thanks to recursive
        calls, always passing all keyword arguments from the parent
        call...) to a form that can be serialized with [`json.dumps`][]
        (and which is -- hopefully -- short yet still readable, especially
        regarding instances of such types as: [*exceptions*][BaseException],
        [*dataclasses*][], typical [*named tuples*][collections.namedtuple],
        [`enum.Enum`][], [`uuid.UUID`][] as well as the essential types
        from the [`datetime`][] and [`ipaddress`][] modules). When it
        comes to preparing any *keys* contained in a *value* which is
        a mapping (e.g., a [`dict`][]) -- see the
        [`prepare_submapping_key`][] method...

        !!! tip

            When extending this method in a subclass, you may want to make
            your custom implementation invoke the default one with some
            keyword arguments specified. In such a case, you may want to
            reach for their default values defined by the signature of
            **[`StructuredLogsFormatter.prepare_value`][]**; if so, refer to
            the **[`StructuredLogsFormatter.PREPARE_VALUE_DEFAULT_KWARGS`][]**
            mapping. For example:

            ```python
            import array, pprint
            import attrs   # <- 3rd party package used just in this example
            from certlib.log import StructuredLogsFormatter

            _BASE_KWARGS = StructuredLogsFormatter.PREPARE_VALUE_DEFAULT_KWARGS

            class MyEnhancedStructuredLogsFormatter(StructuredLogsFormatter):

                @staticmethod
                def default_is_dataclass(obj):
                    base_is_dataclass = _BASE_KWARGS['is_dataclass']
                    return base_is_dataclass(obj) or attrs.has(type(obj))

                @staticmethod
                def default_dataclass_as_dict(obj):
                    base_is_dataclass = _BASE_KWARGS['is_dataclass']
                    base_dataclass_as_dict = _BASE_KWARGS['dataclass_as_dict']
                    return (base_dataclass_as_dict(obj) if base_is_dataclass(obj)
                            else attrs.asdict(obj))

                def prepare_value(
                    self,
                    value,
                    *,
                    exclude_from_seq_types = (
                        *_BASE_KWARGS['exclude_from_seq_types'],
                        memoryview,
                        array.array,
                    ),
                    is_dataclass=default_is_dataclass,
                    dataclass_as_dict=default_dataclass_as_dict,
                    last_resort=pprint.pformat,
                    **kwargs,
                ):
                    return super().prepare_value(
                        value,
                        exclude_from_seq_types=exclude_from_seq_types,
                        is_dataclass=is_dataclass,
                        dataclass_as_dict=dataclass_as_dict,
                        last_resort=last_resort,
                        **kwargs,
                    )
            ```
        """
        if isinstance(value, to_str_types):
            return str(value)

        if isinstance(value, pass_thru_types):
            return value

        kwargs.update(
            to_str_types=to_str_types,
            pass_thru_types=pass_thru_types,
            exclude_from_seq_types=exclude_from_seq_types,
            is_dataclass=is_dataclass,
            dataclass_as_dict=dataclass_as_dict,
            last_resort=last_resort,
        )

        if isinstance(value, Mapping):
            # Any *mapping* => convert it to a *dict*.
            prepare_key = self.prepare_submapping_key
            prepare_value = self.prepare_value
            return {
                prepare_key(key): prepare_value(val, **kwargs)
                for key, val in value.items()
            }

        if isinstance(value, type):
            # A runtime *type* (*class*) => convert it to a *str*...
            module = getattr(value, '__module__', '<unknown module>')
            qualname = getattr(value, '__qualname__', '<unknown type>')
            full_qualified_type_name = (
                qualname if module == 'builtins'
                else f'{module}.{qualname}'
            )
            return self.prepare_value(full_qualified_type_name, **kwargs)

        if isinstance(value, BaseException):
            # An *exception instance* => convert it to a *dict* of the
            # crucial exception's components (type, arguments, etc.).
            exc_components = {
                key: val
                for key, val in (
                    ('exc_type', type(value)),
                    ('args', getattr(value, 'args', None)),
                    ('dict', getattr(value, '__dict__', None)),
                )
                if val
            }
            return self.prepare_value(exc_components, **kwargs)

        if isinstance(value, Sequence) and not isinstance(value, exclude_from_seq_types):
            seq = cast(Sequence[object], value)

            if (len(seq) == 3
                  and seq[0] is type(seq[1])
                  and isinstance(seq[1], BaseException)
                  and (seq[2] is None
                       or type(seq[2]).__name__ == 'traceback')):
                # A sequence of 3 items: exception type, that type's
                # instance and traceback (or None) => treat it as if
                # it was just the *exception instance*...
                return self.prepare_value(seq[1], **kwargs)

            if (isinstance(seq, tuple)
                  and callable(dict_from_this := getattr(seq, '_asdict', None))):
                # A tuple (presumably, a *named tuple*) with an
                # `_asdict()` method => try to use that method
                # to convert this tuple (presumably, to a *dict*).
                try:
                    d = dict_from_this()
                except TypeError:
                    pass
                else:
                    return self.prepare_value(d, **kwargs)

            # Some other sequence => convert it to a *list*.
            prepare_value = self.prepare_value
            return [
                prepare_value(val, **kwargs)
                for val in seq
            ]

        if is_dataclass(value):
            # A *dataclass instance* (we're sure it's not a type, see the
            # type-dedicated check earlier...) => convert it to a *dict*.
            return self.prepare_value(dataclass_as_dict(value), **kwargs)

        # Any other object...
        return last_resort(value)

    # Note: the `type: ignore` comment below prevents type checkers from
    # rejecting `Final` nested in `ClassVar` (which is OK in Python 3.13
    # and newer; and we use `from __future__ import annotations` anyway,
    # so at runtime we are safe regardless of Python version).
    PREPARE_VALUE_DEFAULT_KWARGS: ClassVar[Final[   # type: ignore
        Mapping[str, Any]
    ]] = types.MappingProxyType({
        p.name: p.default
        for p in signature(prepare_value).parameters.values()
        if p.kind is Parameter.KEYWORD_ONLY
    })
    """
    Default values of all [`StructuredLogsFormatter.prepare_value`][]'s
    *keyword-only* parameters (this mapping may come in handy when you
    extend that method in a subclass...).
    """

    def prepare_submapping_key(self, key: object) -> str:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how to prepare, before the actual data serialization, every *key*
        in every mapping (e.g., in a [`dict`][]) being a *value* inside an
        *output data* dict (possibly deeply nested within it).

        The default implementation of this method should be sufficient in
        most cases. It applies [`str`][] to the given key (converting it
        to a string if it was not one already) and truncates the result to
        a maximum length of 200 characters (if longer).

        !!! note

            **[`prepare_value`][]** is what invokes this method -- so (let
            us stress that!) this method is *not* applied to top-level
            keys in the *output data* dict, but *is* applied to *each key*
            in every mapping that **`prepare_value`** takes as an input
            *value* (also, in every dict created by **`prepare_value`**
            as a result of converting an *exception*, *named tuple* or
            *dataclass* instance...). All of this is true for the default
            implementation of **`prepare_value`**. It is recommended
            (yet not enforced) that any custom implementations of the
            **`prepare_value`** method make use of *this* method in a
            similar way.
        """
        key_str = str(key)
        if len(key_str) > self._DESIRED_MAX_KEY_LENGTH:
            key_str = key_str[:self._DESIRED_MAX_KEY_LENGTH]
        return key_str

    def serialize_prepared_output_data(self, output_data: dict[str, Any]) -> str:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        the *output data serialization* procedure.

        !!! warning "Subclass behavior restriction"

            This method should *not* mutate the given *output data* dict
            or anything inside it (regardless of the level of nesting, if
            any nested data is present). If some data needs to be modified,
            a completely *new* object should be created. Doing otherwise
            will result in undefined behavior.

        The default implementation of this method should be sufficient in
        most cases. It just applies the [`serializer`][] callable to the
        given *output data* dict, and returns the result.

        !!! info "Related interfaces"

            By default, the **[`serializer`][]** attribute is set to the
            standard [`json.dumps`][] function, but this can be changed
            by specifying the **`serializer`** argument when invoking the
            **[`StructuredLogsFormatter`][]** constructor.
        """
        return self.serializer(output_data)

    #
    # Internals (should not be used or extended/overridden outside this module!)

    _DESIRED_MAX_KEY_LENGTH: Final[int] = 200

    _COMMON_PART_OF_PER_FORMATTER_AUTO_MADE_RECORD_ATTR_PREFIX: Final[str] = '_auto-made-for#'

    def _resolve_init_arguments(
        self,
        # (Compare to the signature of `logging.Formatter.__init__()`...)
        fmt: str | Mapping[str, Any] | None = None,
        datefmt: Literal[''] | None = None,
        style: Literal['%'] = '%',
        validate: Literal[True] = True,
        **arguments: Any,
    ) -> dict[str, Any]:
        if fmt and isinstance(fmt, str):
            try:
                fmt = ast.literal_eval(fmt)
            except Exception as exc:
                raise ValueError(
                    f'an error occurred when trying to evaluate '
                    f'(as a Python expression) the string ({fmt!a}) '
                    f'passed as the first argument (`fmt`) to '
                    f'{type(self).__init__.__qualname__}() '
                    f'({type(exc).__qualname__}: {exc})'
                ) from exc
        if isinstance(fmt, Mapping):
            if arguments:
                raise TypeError(
                    f'for {type(self).__init__.__qualname__}(), '
                    f'when you pass a mapping as the first argument '
                    f'(`fmt`), as an alternative means of providing '
                    f'keyword arguments, you should not pass real '
                    f'keyword arguments (whereas you did pass some: '
                    f'{", ".join(map(ascii, arguments))})'
                )
            arguments = dict(fmt)
        elif fmt:
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), the first '
                f'argument (`fmt`), if specified, is expected to be a '
                f'mapping (or an `ast.literal_eval()`-evaluable string '
                f'representing a mapping), as an alternative means of '
                f'providing keyword arguments (in contexts when passing '
                f'real keyword arguments is not possible); got: {fmt!a} '
                f'(not a mapping)'
            )
        if datefmt:
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `datefmt` is not customizable'
            )
        if style != '%':
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `style` is not customizable'
            )
        if not validate:
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `validate` is not customizable'
            )
        return arguments

    def _get_unfiltered_defaults(
        self,
        given_defaults: Mapping[str, object],
    ) -> Mapping[str, Any]:
        raw_defaults = dict(self.make_base_defaults())
        raw_defaults.update(given_defaults)
        return dict(sorted(
            (self._validate_output_key(key), self.prepare_value(value))
            for key, value in raw_defaults.items()
        ))

    def _get_unprefixed_auto_makers(
        self,
        given_auto_makers: Mapping[str, str | Callable[[], object]],
    ) -> Mapping[str, Callable[[], object]]:
        raw_auto_makers = dict(self.make_base_auto_makers())
        raw_auto_makers.update(given_auto_makers)
        return dict(sorted(
            self._normalize_and_validate_auto_maker_item(key, auto_maker)
            for key, auto_maker in raw_auto_makers.items()
        ))

    def _normalize_and_validate_auto_maker_item(
        self,
        key: str,
        auto_maker: str | Callable[[], _T],
    ) -> tuple[str, Callable[[], _T]]:
        key = self._validate_output_key(key)
        if isinstance(auto_maker, str):
            resolved: Callable[[], _T] = _resolve_dotted_path(auto_maker)
            auto_maker = resolved
        if not callable(auto_maker):
            raise TypeError(
                f'the {key!a} auto-maker does not appear '
                f'to be a callable object: {auto_maker!a}'
            )
        return key, auto_maker

    def _check_output_keys_required_in_defaults_or_auto_makers(
        self,
        unfiltered_defaults: Mapping[str, Any],
        unprefixed_auto_makers: Mapping[str, Callable[[], object]],
    ) -> None:
        provided_keys = unfiltered_defaults.keys() | unprefixed_auto_makers.keys()
        required_keys = self.get_output_keys_required_in_defaults_or_auto_makers()
        if missing_keys := (required_keys - provided_keys):
            missing_keys_listing = ', '.join(map(ascii, sorted(missing_keys)))
            raise KeyError(
                f'missing default values or auto-makers '
                f'for keys: {missing_keys_listing}'
            )

    def _get_actual_defaults(
        self,
        unfiltered_defaults: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return {
            key: value_prepared
            for key, value_prepared in unfiltered_defaults.items()
            # If `value_prepared` is *non-numeric* and, at the same time,
            # is *falsy* (i.e., is an object which is considered *false*
            # in a boolean context) => we skip it as a *void* value (that
            # is, a value assumed to carry *no sufficiently significant*
            # information).
            if value_prepared or value_prepared == 0
        }

    def _get_auto_made_record_attr_prefix(self) -> str:
        return f'{self._COMMON_PART_OF_PER_FORMATTER_AUTO_MADE_RECORD_ATTR_PREFIX}{id(self):x}:'

    def _get_actual_auto_makers(
        self,
        auto_made_record_attr_prefix: str,
        unprefixed_auto_makers: Mapping[str, Callable[[], object]],
    ) -> Mapping[str, Callable[[], object]]:
        return {
            auto_made_record_attr_prefix + key: auto_maker
            for key, auto_maker in unprefixed_auto_makers.items()
        }

    def _get_record_attr_to_output_key(self) -> Mapping[str, str | None]:
        base_mapping = self.make_base_record_attr_to_output_key()
        assert all(
            rec_attr.startswith(self.auto_made_record_attr_prefix)
            for rec_attr in self.auto_makers.keys()
        )
        return dict(
            # Note that here any `rec_attr` duplication
            # (hardly possible!) would cause TypeError.
            **{
                rec_attr: (
                    self._validate_output_key(key) if key is not None
                    else None
                )
                for rec_attr, key in base_mapping.items()
            },
            **{
                rec_attr: rec_attr.removeprefix(self.auto_made_record_attr_prefix)
                for rec_attr in self.auto_makers.keys()
            },
        )

    def _validate_output_key(self, key: str) -> str:
        if not isinstance(key, str):
            raise TypeError(f'{key=!a} is not a str')
        if len(key) > self._DESIRED_MAX_KEY_LENGTH:
            raise ValueError(
                f'{key=!a} is longer than '
                f'{self._DESIRED_MAX_KEY_LENGTH} characters'
            )
        return str(key)

    def _get_actual_serializer(
        self,
        given_serializer: str | Callable[[dict[str, Any]], str],
    ) -> Callable[[dict[str, Any]], str]:
        serializer: Callable[[dict[str, Any]], str] = (
            _resolve_dotted_path(given_serializer) if isinstance(given_serializer, str)
            else given_serializer
        )
        if not callable(serializer):
            raise TypeError(
                f'{serializer=!a} does not appear '
                f'to be a callable object'
            )
        return serializer

    def _extract_output_from_xm(
        self,
        record: logging.LogRecord,
        xm_instance: ExtendedMessage,
        handle_output_item: Callable[[object, object], None],
    ) -> None:
        attr_to_key = self.record_attr_to_output_key

        # Extract from the given `ExtendedMessage` instance and handle...

        # * ...its attributes related to the text message (if any):
        msg_key = attr_to_key.get('msg', 'msg')
        if msg_key is not None:
            msg_value = xm_instance.get_dict_with_non_falsy_pattern_and_args(
                args_output_key=attr_to_key.get('args', 'args'),
            )
            if msg_value:
                handle_output_item(msg_key, msg_value)

        # * ...its `exc_info` attribute (if worth including):
        ei_key = attr_to_key.get('exc_info', 'exc_info')
        if (ei_key is not None
            and (xm_ei := xm_instance.exc_info)
            and self._is_xm_exc_info_significant(xm_ei, record.exc_info)
        ):
            if xm_ei == (None, None, None):
                xm_ei = None
            handle_output_item(ei_key, xm_ei)


        # * ...its `stack_info` attribute (if worth including):
        si_key = attr_to_key.get('stack_info', 'stack_info')
        if (si_key is not None
            and (xm_si := xm_instance.stack_info)
            and self._is_xm_stack_info_significant(xm_si, record.stack_info)
        ):
            handle_output_item(si_key, xm_si)

        # * ...and any *extra data* (stored in its `data` attribute):
        for key, value in xm_instance.data.items():
            handle_output_item(key, value)

    @staticmethod
    def _is_xm_exc_info_significant(xm_ei: Any, rec_ei: Any) -> bool:
        return (not rec_ei) or (
            # If `record.exc_info` is *not* a *falsy* object, then the
            # `ExtendedMessage` instance's `exc_info` attribute -- to
            # be considered *significant* -- needs to be **either** an
            # exception which is *different* from the one conveyed by
            # `record.exc_info` **or** an *exc info* tuple *different*
            # from `record.exc_info`. So, in particular, a flag value
            # (such as True) is considered *insignificant* in such a
            # case.
            xm_ei is not rec_ei  # (<- Fast check first)
            and (
                isinstance(xm_ei, BaseException)
                and rec_ei != (type(xm_ei), xm_ei, xm_ei.__traceback__)
                or
                isinstance(xm_ei, tuple)
                and xm_ei != rec_ei
            )
        )

    @staticmethod
    def _is_xm_stack_info_significant(xm_si: bool | str, rec_si: str | None) -> bool:
        return (not rec_si) or (
            # If `record.stack_info` is *not* a *falsy* object, then
            # the `ExtendedMessage` instance's `stack_info` attribute,
            # -- to be considered *significant* -- needs to be a `str`
            # *different* from `record.stack_info`. So a flag value
            # (True) is considered *insignificant* in such a case.
            xm_si is not rec_si  # (<- Fast check first)
            and isinstance(xm_si, str)
            and xm_si != rec_si
        )

    def _extract_output_from_record(
        self,
        record: logging.LogRecord,
        xm_instance: ExtendedMessage | None,
        handle_output_item: Callable[[object, object], None],
    ) -> None:
        common_auto_prefix = self._COMMON_PART_OF_PER_FORMATTER_AUTO_MADE_RECORD_ATTR_PREFIX
        attr_to_key = self.record_attr_to_output_key

        for rec_attr, value in record.__dict__.items():
            if not isinstance(rec_attr, str):
                # (Rather unlikely, but just in case...)
                continue

            if rec_attr.startswith(common_auto_prefix):
                # The encountered record attribute has been created by an
                # auto-maker registered by *some* `StructuredLogsFormatter`.
                # Note that, below, `key` will be set to None -- *unless*
                # that auto-maker has been registered by *this* instance
                # of `StructuredLogsFormatter`, i.e., by `self` (remember
                # that `auto_made_record_attr_prefix` is *different* for
                # each `StructuredLogsFormatter` instance).
                key = attr_to_key.get(rec_attr)
            elif (value is xm_instance is not None) and rec_attr == 'msg':
                # Already handled by `_extract_output_from_xm()`.
                continue
            else:
                if rec_attr == 'exc_info' and value == (None, None, None):
                    value = None
                key = attr_to_key.get(rec_attr, rec_attr)

            if key is not None:
                handle_output_item(key, value)

    @staticmethod
    def _handle_output_item(
        # Shared (output-data-dict-wide) arguments:
        desired_max_key_length: int,
        prepare_value: Callable[[object], Any],
        actual_defaults: dict[str, Any],
        output_data: dict[str, Any],

        # Individual (per-output-data-item) arguments:
        key: object,
        value: object,
    ) -> None:

        if not isinstance(key, str):
            return
        # Note: the `type: ignore` comments in this function (below) just
        # silence certain silly typing tools (*other* than `mypy`!) which
        # do not comprehend that, from this point, `key` is always a str.

        if len(key) > desired_max_key_length:
            # Truncate the key (it's a rare case, hopefully).
            key = key[:desired_max_key_length]

        value_prepared = prepare_value(value)
        if (not value_prepared) and value_prepared != 0:
            # If `value_prepared` is *non-numeric* and, at the same time,
            # is *falsy* (i.e., is an object which is considered *false*
            # in a boolean context) => we skip it as a *void* value (that
            # is, a value assumed to carry *no sufficiently significant*
            # information); then, however, we also prevent the respective
            # *default value* (if any) from being set.
            actual_defaults.pop(key, None)  # type: ignore
            return

        # Finally, set the prepared item.
        actually_set_value = output_data.setdefault(key, value_prepared)  # type: ignore
        if actually_set_value is value_prepared:
            return

        # Wait! Key deduplication may be needed (it's a rare case, hopefully).
        while actually_set_value != value_prepared:
            # Note that, in this case, the key length may
            # become longer than `desired_max_key_length`.
            key = f'{key}_'
            actually_set_value = output_data.setdefault(key, value_prepared)  # type: ignore

            # (Comparing also identities -- for cases of such
            # an object that never compares equal to itself.)
            if actually_set_value is value_prepared:
                return


class ExtendedMessage:

    """
    A tool thanks to which you can:

    * conveniently emit structured log entries, especially if
      [`StructuredLogsFormatter`][] is in use;

    * use the modern `{}`-based style of log message formatting, or --
      if you just need to log pure data -- simply omit passing the text
      message pattern (regardless of what formatter is in use);

    * defer the creation of some values (if it is costly) until the log
      entry is to be actually emitted (regardless of what formatter is
      in use).

    There is a convenience alias of this class: **[`xm`][]**. As being
    very short, it is simply much more ergonomic than the actual class
    name -- given that this tool is intended to be used every time you
    log something. For example:

    ```python
    import datetime, hashlib, ipaddress, logging, sys
    from certlib.log import xm

    logging.info(xm("Hello {}!", sys.platform))
    logging.info(xm("Maxsize is {maxsize:x}", maxsize=sys.maxsize))
    logging.warning(xm(
        connection_count=42,
        client_ip=ipaddress.IPv4Address("192.168.0.121"),
        local_time=datetime.datetime.now(),
        # Value creation deferred until the log entry is to be emitted:
        payload_hash=lambda: hashlib.sha256(b'...payload...').hexdigest(),
    ))
    some_data_dict = globals()
    logging.debug(xm(some_data_dict))
    ```

    ***

    **Constructor arguments** (all *optional*):

    * _**first positional argument**_ (default: `""`):
      the text message pattern. Expected to be a string, or any *truthy*
      object that could be converted to a string by applying [`str`][]
      to it. The pattern may contain [`{}`-formatting-style *replacement
      fields*](https://docs.python.org/3/library/string.html#format-string-syntax)
      (perhaps with a `'!'`-separated *conversion* marker, and/or a
      `':'`-separated *format spec*). The given object is assigned to
      the [`pattern`][] attribute intact, unless it is *falsy* -- then
      it is ignored, and just `""` (empty string) is assigned to that
      attribute.

    * _**extra positional arguments**_ (if any):
      positional *args* to format the text message (they need to match
      positional/numbered *replacement fields* in the text message
      pattern -- see the *first positional argument* described above).
      A [`tuple`][] of these arguments is assigned to the [`args`][]
      attribute.

    * **`exc_info`** (*keyword-only*; default: [`None`][]):
      its usage and related behavior are nearly identical to those of
      the same-named argument to `logging.Logger`'s methods (see [the
      relevant fragment](https://docs.python.org/3/library/logging.html#logging.Logger.debug)
      of the documentation for the `logging` module). This argument is
      assigned to the [`exc_info`][] attribute.

    * **`stack_info`** (*keyword-only*; default: [`False`][]):
      its usage and related behavior are nearly identical to those of
      the same-named argument to `logging.Logger`'s methods (see [the
      relevant fragment](https://docs.python.org/3/library/logging.html#logging.Logger.debug)
      of the documentation for the `logging` module). This argument is
      assigned to the [`stack_info`][] attribute.

    * **`stacklevel`** (*keyword-only*; default: `1`):
      its usage and related behavior are nearly identical to those of
      the same-named argument to `logging.Logger`'s methods (see [the
      relevant fragment](https://docs.python.org/3/library/logging.html#logging.Logger.debug)
      of the documentation for the `logging` module). This argument is
      assigned to the [`stacklevel`][] attribute.

    * _**extra keyword arguments**_ (if any):
      all of them become *extra data* items -- to be included in the
      *output data* dict if [`StructuredLogsFormatter`][] is used, or
      to be appended to the text message (in a form resembling the
      keyword arguments syntax) if some other formatter is in use. A
      [`dict`][] of those *extra data* items is always stored as the
      [`data`][] attribute. Moreover, any items whose names match some
      *named replacement fields* in the text message pattern (specified
      as the *first positional argument*) will take part in formatting
      the actual text message (regardless of what formatter is in use).

    **Alternatively**, a mapping (e.g., a [`dict`][]) of *extra data*
    items can be passed to the [constructor][ExtendedMessage] as the
    *first positional argument*. Then any *extra positional or keyword
    arguments* are forbidden -- except **`exc_info`**, **`stack_info`**
    and **`stacklevel`**. The effect is the same as passing each of
    that mapping's items as an *extra keyword argument* (without passing
    a message pattern as the *first positional argument*). The mapping,
    after conversion to a `dict`, is assigned to the [`data`][] attribute.

    When it comes to the arguments **`exc_info`**, **`stack_info`** and
    **`stacklevel`**, they should *not* be included in that mapping (each
    of them, if to be specified, should *only* be specified as a real
    keyword argument).

    !!! warning "Interface restriction"

        If you pass a **`stack_info`** and/or **`stacklevel`** argument
        to the **[`ExtendedMessage`][]** (**[`xm`][]**) constructor, you
        should *not* pass **`stack_info`** or **`stacklevel`** to the
        related [logger method call](https://docs.python.org/3/library/logging.html#logging.Logger.debug)
        (doing so will result in undefined behavior).

        ```python
        # All WRONG (!!!):
        logger.info(xm('Foo', stack_info=True), stack_info=True)
        logger.info(xm('Foo', stack_info=True), stacklevel=2)
        logger.info(xm('Foo', stacklevel=2), stack_info=True)
        logger.info(xm('Foo', stacklevel=2), stacklevel=2)
        logger.info(xm('Foo', stack_info=True), stack_info=True, stacklevel=2)
        logger.info(xm('Foo', stack_info=True, stacklevel=2), stack_info=True)
        logger.info(xm('Foo', stack_info=True, stacklevel=2), stack_info=True, stacklevel=2)
        # (and similar...)
        ```

        ```python
        # OK:
        logger.info(xm('Foo', stack_info=True))
        logger.info(xm('Foo', stacklevel=2))
        logger.info(xm('Foo', stack_info=True, stacklevel=2))

        # Also OK:
        logger.info(xm('Foo'), stack_info=True)
        logger.info(xm('Foo'), stacklevel=2)
        logger.info(xm('Foo'), stack_info=True, stacklevel=2)
        ```

    Whenever a formatter (of any type) processes a log record whose `msg`
    attribute (which typically is just what has been passed to the logger
    method call as the first positional argument) is an `ExtendedMessage`
    (`xm`) instance, that instance's method [`get_message_value`][] is
    invoked: either *directly* -- by the [`StructuredLogsFormatter`][]'s
    machinery; or *indirectly*, via [`__str__`][] -- by the standard
    machinery that other formatter types use.

    !!! warning "Interface restriction"

        When you pass an instance of **`ExtendedMessage`**
        as the first positional argument to a [logger method
        call](https://docs.python.org/3/library/logging.html#logging.Logger.debug),
        you should *not* pass to that call any other *positional*
        arguments (doing so will result in undefined behavior).

        ```python
        # WRONG (!!!):
        logger.info(xm('{}, {} and {}'), 'Athos', 'Porthos', 'Aramis')
        ```

        ```python
        # OK:
        logger.info(xm('{}, {} and {}', 'Athos', 'Porthos', 'Aramis'))
        ```

    !!! note

        If a text message pattern (*not* a mapping) is passed to the
        **[`ExtendedMessage`][]** (**[`xm`][]**) constructor as the
        *first positional argument* _**and**_ no *extra positional
        or keyword arguments* are provided (except **`exc_info`**,
        **`stack_info`** and **`stacklevel`**) -- that is, if both
        of the attributes **[`args`][]** and **[`data`][]** of the
        resultant **`ExtendedMessage`** instance are *empty* -- then
        the **[`get_message_value`][]** method will *not* attempt to
        format the text message with [`str.format`][]; instead, it
        will treat the pattern as an *already formatted* text message.

        ```python
        logger.info(xm('answer: {}', 42))  # message will be 'answer: 42'
        logger.info(xm('answer: {}'))      # message will be 'answer: {}'  [sic!]
        ```

        This mimics how the standard [`logging`][] machinery handles
        a log record whose `args` attribute is empty (when only a
        text message pattern is specified, without any values to be
        interpolated).

    If any *extra positional or keyword arguments* to the [constructor][ExtendedMessage]
    -- except **`exc_info`**, **`stack_info`** and **`stacklevel`** --
    or any values included in the *extra data* mapping (if passed to the
    constructor as the *first positional argument*) are *function* or
    *method* objects (precisely: instances of any types included in
    [`ExtendedMessage.recognized_callable_arg_or_data_item_types`][]),
    then -- as part of processing the `ExtendedMessage` instance by a
    formatter -- each of those functions/methods will be *called* to
    obtain the *actual value*, which will then replace (respectively,
    in [`args`][] or [`data`][]) the called function/method.

    Let us be precise: all those calls and replacements will be
    triggered when *any* of the following methods is invoked on the
    `ExtendedMessage` instance for the first time: [`get_message_value`][],
    [`get_dict_with_non_falsy_pattern_and_args`][], [`__str__`][] or
    [`iter_str_parts`][] (with the proviso that the last one returns an
    [iterator](https://docs.python.org/3/glossary.html#term-iterator)
    which, to achieve the said effect, needs to be iterated over,
    at least partially). Each of the said calls and replacements will
    be made at most *once* per instance of `ExtendedMessage` (see the
    [`_ensure_callable_args_and_data_items_resolved`][] method's
    description...).

    Thanks to that mechanism, if the creation of some value is expected
    to be costly, you can wrap it in a function/method (in particular,
    in an argumentless `lambda`) to defer that costly operation until
    the value becomes necessary (which may never happen if, for example,
    the specified log level is lower than the configured threshold).
    Such a function/method is expected to take no arguments (therefore,
    if it is a method, it should already be bound to some instance or
    class).

    !!! warning "Multithreading-related restriction"

        *None* of those functions/methods should acquire any locks
        that might also be acquired by any code making use of some
        [`logging`][] stuff (because, in particular, that could result in
        a [*deadlock*](https://docs.python.org/3/glossary.html#term-deadlock)).

    !!! info "See also"

        For extra information about **`ExtendedMessage`** (**`xm`**),
        including a bunch of usage examples, see the **[Tool:
        `xm`](guide.md#certlib.log--tool-xm)** section of the
        *User's Guide*.
    """

    __slots__ = (
        'pattern',
        'args',
        'data',
        'exc_info',
        'stack_info',
        'stacklevel',

        '_callable_args_and_data_items_already_resolved',
        '_callable_args_and_data_items_resolving_lock',
        '_cached_message',
    )

    #
    # Public stuff

    pattern: object
    args: tuple[object, ...]
    data: dict[str, object]
    exc_info: Any
    stack_info: bool
    stacklevel: int

    recognized_callable_arg_or_data_item_types: ClassVar[   # type: ignore[type-arg]
        tuple[type[Callable], ...]
    ] = (
        types.FunctionType,
        types.BuiltinFunctionType,
        types.MethodType,
        types.MethodWrapperType,
    )
    """
    For `ExtendedMessage`, this tuple contains the runtime types of
    *function* and *bound method* objects -- both in the *user-defined*
    and *built-in* variants (precisely: [`types.FunctionType`][],
    [`types.BuiltinFunctionType`][], [`types.MethodType`][] and
    [`types.MethodWrapperType`][]). You can override this attribute in
    your subclass to redefine the runtime types of values in [`args`][]
    and [`data`][] that shall be *called* to obtain the *actual values*
    (see the part of the [`ExtendedMessage`][] constructor's description
    containing a reference to this attribute...).
    """

    @overload
    def __init__(
        self,
        pattern: str = '',
        /,
        *args: object,

        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,

        **data: object,
    ):
        ...

    @overload
    def __init__(
        self,
        data: Mapping[str, object],
        /,
        *,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
    ):
        ...

    @overload
    def __init__(
        self,
        pattern: object,  # (anything convertible to str, but *not* a mapping)
        /,
        *args: object,

        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,

        **data: object,
    ):
        ...

    def __init__(
        self,
        first_arg: object | Mapping[str, object] = '',
        /,
        *args: object,
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        **data: object,
    ):
        # Note: it is not necessary to protect the following 4
        # lines with a lock, because each call to the function
        # `_ensure_internal_record_hook_is_set_up()` is itself
        # **thread-safe** and **idempotent**; so any redundant
        # (even if concurrent) calls to that function are safe.
        if self._setup_of_record_hooks_still_needs_to_be_done:
            _ensure_internal_record_hook_is_set_up(self._exc_info_record_hook)
            _ensure_internal_record_hook_is_set_up(self._stack_stuff_record_hook)
            self.__class__._setup_of_record_hooks_still_needs_to_be_done = False

        pattern: object
        if isinstance(first_arg, Mapping):
            if args or data:
                raise TypeError(
                    f"{type(self).__qualname__}'s *extra data* items, "
                    f"if any, must be passed to its constructor either "
                    f"by keyword arguments or as a mapping being the "
                    f"only positional argument (not both)"
                )
            pattern = ''
            data = dict(first_arg)
        else:
            pattern = first_arg

        self.pattern = pattern or ''
        self.args = args
        self.data = data
        self.exc_info = exc_info
        self.stack_info = stack_info
        self.stacklevel = stacklevel

        self._callable_args_and_data_items_already_resolved: bool = False
        self._callable_args_and_data_items_resolving_lock: threading.Lock | None = None
        self._cached_message: str | None = None

    def get_message_value(self) -> str:
        """
        Automatically invoked by the [`StructuredLogsFormatter`][]'s
        machinery to obtain a string to be assigned to the log record's
        [`message` attribute](https://docs.python.org/3/library/logging.html#logrecord-attributes).

        !!! warning "Interface restriction"

            Once this method is invoked on an **`ExtendedMessage`** instance,
            any attempts (regarding that instance) to replace/mutate any of
            the objects assigned to the **[`pattern`][]**, **[`args`][]** and
            **[`data`][]** attributes or anything inside them (regardless of
            the level of nesting, if any nested data is present) -- are *no
            loger* allowed. Doing so will result in undefined behavior.

        The default implementation of this method should be sufficient
        in most cases. It converts [`pattern`][] to a string, and then
        -- *only* if [`args`][] and/or [`data`][] contain any items --
        invokes that string's [`format`][str.format] method, passing to
        it all items of `args` as *positional arguments* and all items
        of `data` as *keyword arguments*. A string being the result of
        the above operation(s) is cached (for any further invocations
        of this method on the same instance) and returned.

        !!! warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_callable_args_and_data_items_resolved`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.

        !!! note

            Apart from the aforementioned use by the machinery
            of **`StructuredLogsFormatter`**, this method is also
            invoked by the **`ExtendedMessage`**'s implementation
            of **[`__str__`][]** (which is important for formatters
            that are *not* instances of **`StructuredLogsFormatter`**).
        """
        self._ensure_callable_args_and_data_items_resolved()

        # (Compare to the source code of `logging.LogRecord.getMessage()`...)
        message = self._cached_message
        if message is None:
            message = str(self.pattern)
            if self.args or self.data:
                message = message.format(*self.args, **self.data)

            # (Such assignments are assumed to be *atomic* operations.)
            self._cached_message = message

        return message

    def get_dict_with_non_falsy_pattern_and_args(
        self,
        *,
        pattern_output_key: str | None = 'pattern',
        args_output_key: str | None = 'args',
    ) -> dict[str, object]:
        """
        Automatically invoked by the [`StructuredLogsFormatter`][]'s
        machinery to get a value to be included in the *output data*
        dict under the key corresponding to the log record's `msg`
        attribute. The returned value is supposed to be a dict
        that conveys relevant information from the `ExtendedMessage`
        instance -- to the extent that corresponds to the information
        typically conveyed by the `msg` and `args` attributes of log
        records when `ExtendedMessage` is not used.

        !!! warning "Interface restriction"

            Once this method is invoked on an **`ExtendedMessage`** instance,
            any attempts (regarding that instance) to replace/mutate any of
            the objects assigned to the **[`args`][]** and **[`data`][]**
            attributes or anything inside them (regardless of the level
            of nesting, if any nested data is present) -- are *no loger*
            allowed. Doing so will result in undefined behavior.

        The default implementation should be sufficient in most cases. It
        returns a dict containing zero, one or two items. Specifically --
        *each* of the following *if* the key is not [`None`][] and the
        value is not *falsy*:

        * the given **`pattern_output_key`** -- mapped to the value of the
          [`pattern`][] attribute,

        * the given **`args_output_key`** --  mapped to the value of the
          [`args`][] attribute.

        !!! warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_callable_args_and_data_items_resolved`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_callable_args_and_data_items_resolved()

        # Certain typing tools (*other* than `mypy`!) are too silly...
        return {   # type: ignore
            key: val
            for key, val in (
                (pattern_output_key, self.pattern),
                (args_output_key, self.args),
            )
            if (key is not None) and val
        }

    def __str__(self) -> str:
        """
        Invoked when [`str`][] is applied to an `ExtendedMessage` instance.
        This is done, in particular, by the machinery related to typical
        non-`StructuredLogsFormatter` formatters (specifically, by the
        log record method [`getMessage`][logging.LogRecord.getMessage])
        -- to obtain a string to be assigned to the [`message`
        attribute](https://docs.python.org/3/library/logging.html#logrecord-attributes)
        of the log record.

        !!! warning "Interface restriction"

            Once this method is invoked on an **`ExtendedMessage`** instance,
            any attempts (regarding that instance) to replace/mutate any of
            the objects assigned to the **[`pattern`][]**, **[`args`][]** and
            **[`data`][]** attributes or anything inside them (regardless of
            the level of nesting, if any nested data is present) -- are *no
            loger* allowed. Doing so will result in undefined behavior.

        The default implementation of this method should be sufficient
        in most cases. It invokes the [`iter_str_parts`][] method
        (which, in particular, invokes [`get_message_value`][]...)
        and concatenates any yielded strings (if more than one) using
        `" | "` as the separator.

        !!! warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_callable_args_and_data_items_resolved`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_callable_args_and_data_items_resolved()

        return ' | '.join(self.iter_str_parts())

    @reprlib.recursive_repr(fillvalue='<...>')
    def __repr__(self) -> str:
        """
        Invoked when [`repr`][] is applied to an `ExtendedMessage`
        instance (typically, for debug purposes).

        The default implementation of this method should be sufficient
        in most cases. It invokes the [`iter_argument_reprs`][] method,
        concatenates any yielded strings (if more than one) using `", "`
        as the separator, adds the parentheses, and prefixes the whole
        thing with the class name.
        """
        type_name = type(self).__qualname__
        arguments_repr = ', '.join(self.iter_argument_reprs())
        return f'{type_name}({arguments_repr})'

    def iter_str_parts(self) -> Iterator[str]:
        """
        Invoked by the [`__str__`][] method.

        !!! warning "Interface restriction"

            Once this method is invoked on an **`ExtendedMessage`** instance,
            any attempts (regarding that instance) to replace/mutate any of
            the objects assigned to the **[`pattern`][]**, **[`args`][]** and
            **[`data`][]** attributes or anything inside them (regardless of
            the level of nesting, if any nested data is present) -- are *no
            loger* allowed. Doing so will result in undefined behavior.

        The default implementation of this method yields zero, one
        or two strings. Specifically -- *each* of the following *if
        not empty*:

        * the result of an invocation of the [`get_message_value`][]
          method,

        * a representation of the [`data`][] mapping's items (formatted
          in a way that resembles the syntax for specifying keyword
          arguments, but without the parentheses).

        !!! warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_callable_args_and_data_items_resolved`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_callable_args_and_data_items_resolved()

        if formatted_message := self.get_message_value():
            yield formatted_message
        if formatted_data_items := ', '.join(
            f'{key}={val!a}' for key, val in self.data.items()
        ):
            yield formatted_data_items

    def iter_argument_reprs(self) -> Iterator[str]:
        """
        Invoked by the [`__repr__`][] method.

        The default implementation of this method yields string
        representations of the arguments to the [`ExtendedMessage`][]
        ([`xm`][]) constructor which would be needed to create an
        instance equivalent to this one (`self`).
        """
        if self.args or self.pattern:
            yield repr(self.pattern)
        if self.args:
            yield from map(repr, self.args)
        if self.exc_info is not None:
            yield f'exc_info={self.exc_info!r}'
        if self.stack_info is not False:  # noqa
            yield f'stack_info={self.stack_info!r}'
        if self.stacklevel != 1 or type(self.stacklevel) is not int:
            yield f'stacklevel={self.stacklevel!r}'
        for key, val in self.data.items():
            yield f'{key}={val!r}'

    #
    # Semi-protected method (allowed to be invoked in subclasses)

    def _ensure_callable_args_and_data_items_resolved(self) -> None:
        """
        This method processes the items of [`args`][] and [`data`][] --
        by *calling* each value that is an instance of any type included
        in [`ExtendedMessage.recognized_callable_arg_or_data_item_types`][],
        and then *replacing* that value with the result of that call. Each
        call is made without arguments.

        This method can be safely invoked multiple times on the same
        instance, *even* in the case of *concurrent* invocations. The
        implementation guarantees that *none* of the said calls to
        callable values will be made more than *once* per instance of
        `ExtendedMessage`.

        !!! warning "Interface restriction"

            This method _**is not part of the public API**_ -- _**except
            that**_ it is allowed to be invoked by any methods implemented
            by possible subclasses of **`ExtendedMessage`**.

        !!! warning "Interface restriction"

            Once this method is invoked on an **`ExtendedMessage`**
            instance, any other attempts (regarding that instance)
            to replace/mutate any of the objects assigned to the
            **[`args`][]** and **[`data`][]** attributes or anything
            inside them (regardless of the level of nesting, if any
            nested data is present) -- are *no loger* allowed. Doing
            so will result in undefined behavior.
        """
        if self._callable_args_and_data_items_already_resolved:
            # OK, already resolved (fast path).
            return

        with self._callable_args_and_data_items_resolving_meta_lock:
            # Obtain the instance's lock in a thread-safe manner...
            lock = self._callable_args_and_data_items_resolving_lock
            if lock is None:
                # (We want to defer its creation until this moment, so that
                # `ExtendedMessage.__init__()` remains as fast as possible.)
                lock = self._callable_args_and_data_items_resolving_lock = (
                    threading.Lock()
                )

        if not lock.acquire(timeout=self._CALLABLE_ARGS_AND_DATA_RESOLVING_LOCK_TIMEOUT):
            raise RuntimeError(
                f'could not acquire the lock that protects the procedure '
                f'of ensuring that relevant callable items of the `args` '
                f'and `data` collections will be resolved'
            )
        try:
            if self._callable_args_and_data_items_already_resolved:
                # OK, already resolved.
                return
            self._resolve_callable_args_and_data_items()

            # (Such assignments are assumed to be *atomic* operations.)
            self._callable_args_and_data_items_already_resolved = True
        finally:
            lock.release()

    #
    # Internals (should not be used or extended/overridden outside this module!)

    _CALLABLE_ARGS_AND_DATA_RESOLVING_LOCK_TIMEOUT: Final[float] = 9.0

    _setup_of_record_hooks_still_needs_to_be_done: ClassVar[bool] = True
    _callable_args_and_data_items_resolving_meta_lock: ClassVar[threading.Lock] = threading.Lock()

    @staticmethod
    def _exc_info_record_hook(record: logging.LogRecord) -> None:
        if record.exc_info:
            return

        instance = getattr(record, 'msg', None)
        if not isinstance(instance, ExtendedMessage):
            return

        # (Compare to the `exc_info`-related fragments of
        # the source code of `logging.Logger._log()`...)
        exc_info = instance.exc_info
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
            record.exc_info = cast(Any, exc_info)

    @staticmethod
    def _stack_stuff_record_hook(record: logging.LogRecord) -> None:
        if record.stack_info:
            return

        instance = getattr(record, 'msg', None)
        if not isinstance(instance, ExtendedMessage):
            return

        if (getattr(record, 'lineno', None) == 0
              and getattr(record, 'pathname', None) == '(unknown file)'
              and getattr(record, 'funcName', None) == '(unknown function)'):
            # It seems that any calls to `logging.Logger.findCaller()`
            # are either doomed to failure or should not be attempted
            # because `logging._srcfile` has been set to None...
            return

        stack_info = instance.stack_info
        stacklevel = instance.stacklevel
        if (not stack_info) and stacklevel == 1:
            return

        # Let's exclude our internals from stack introspection.
        if _PY_3_11_OR_NEWER:
            if stacklevel >= 1:
                stacklevel += 2
        else:
            # A bit weird, but oh well... :)
            if stacklevel > 1:
                stacklevel += 3
            elif stacklevel == 1:
                stacklevel += 2

        # (Compare to the `fn`/`lno`/`func`/`sinfo`-related fragments of
        # the source code of `logging.Logger._log()`...)
        try:
            found = logging.Logger.findCaller(
                # Here we pass None as a substitute for a logger instance
                # (the `findCaller()` method makes no use of it anyway).
                None,  # type: ignore
                stack_info,
                stacklevel,
            )
        except ValueError:
            return

        pathname, lineno, func, sinfo = found
        if (lineno == 0
              and pathname == '(unknown file)'
              and func == '(unknown function)'):
            return

        # (Compare to the `pathname`/`lineno`/`funcName`/`stack_info`/
        # /`filename`/`module`-related fragments of the source code of
        # `logging.LogRecord.__init__()`...)
        record.pathname = pathname
        record.lineno = lineno
        record.funcName = func
        record.stack_info = sinfo
        try:
            record.filename = os.path.basename(record.pathname)
            record.module = os.path.splitext(record.filename)[0]
        except (TypeError, ValueError, AttributeError):
            record.filename = record.pathname
            record.module = "Unknown module"

    def _resolve_callable_args_and_data_items(self) -> None:
        recognized_callable_types = (
            self.recognized_callable_arg_or_data_item_types
        )
        args: tuple[Any, ...] = self.args
        data: dict[str, Any] = self.data

        # (Such assignments are assumed to be *atomic* operations.)
        self.args = tuple([
            val() if isinstance(val, recognized_callable_types) else val
            for val in args
        ])
        for key, val in data.items():
            if isinstance(val, recognized_callable_types):
                # (Such assignments are assumed to be *atomic* operations.)
                data[key] = val()


xm: Final = ExtendedMessage
"""[`xm`][] is a convenience alias of [`ExtendedMessage`][]."""


def make_constant_value_provider(value: _T) -> Callable[[], _T]:
    """
    A trivial (yet sometimes useful) helper: given an arbitrary object
    (**`value`**), create an argumentless function that will always
    return that object (note that such an argumentless function can
    be used as an *auto-maker*).
    """
    return (lambda: value)


def register_log_record_attr_auto_maker(
    rec_attr: str,
    auto_maker: Callable[[], object],
) -> None:
    """
    For the specified log record attribute name (**`rec_attr`**),
    register the given *auto-maker* callable (**`auto_maker`**).

    What this means is that by calling this function you ensure that,
    from now on, the specified attribute will be automatically set on
    every new [log record][logging.LogRecord] object (*shortly after*
    it is created by a [logger](https://docs.python.org/3/howto/logging.html#loggers),
    and *before* being processed by any [handlers](https://docs.python.org/3/howto/logging.html#handlers),
    [filters](https://docs.python.org/3/library/logging.html#filter) and
    [formatters](https://docs.python.org/3/howto/logging.html#formatters))
    -- to a value returned by the specified *auto-maker*.

    The *auto-maker* needs to be an argumentless function or any other
    object that can be called with no arguments. A call to it will be
    made once for each newly created log record (in the thread in which
    the respective logger method call is being executed). Obviously, the
    returned values are allowed to vary depending on the context (or even
    per each call).

    If, for the specified attribute name, some *auto-maker* is already
    registered, this method raises [`KeyError`][].

    !!! note

        Typically, you _**do not need**_ to use this function directly,
        because the machinery of **[`StructuredLogsFormatter`][]** does
        it for you (on the creation of a **`StructuredLogsFormatter`**
        instance; see also the description of the
        **[`StructuredLogsFormatter.make_base_auto_makers`][]** method).
        That machinery will also take care of avoiding record attribute
        name collisions.

    !!! warning

        If you use this function *directly*, you need to take care of
        avoiding record attribute name collisions by yourself. When
        the internal *auto-makers* machinery attempts to assign an
        *auto-maker*-produced value to the respective attribute of
        a log record but the log record already has that attribute set,
        then [`KeyError`][] is raised (which will typically bubble up
        to the caller of the currently executed logger method). This
        behavior mimics how the machinery of the standard [`logging`][]
        module reacts to collisions between *extra* items and existing
        attributes of a log record.
    """
    with _auto_makers_registry_and_internal_record_hooks_maintenance_lock:
        _ensure_record_factory_with_auto_makers_and_record_hooks_is_set()
        _add_to_auto_makers_registry(rec_attr, auto_maker)


def unregister_log_record_attr_auto_maker(
    rec_attr: str,
) -> None:
    """
    For the given log record attribute name (**`rec_attr`**), unregister
    the previously registered *auto-maker*.

    If, for the specified attribute name, no *auto-maker* is currently
    registered, this method raises [`KeyError`][].
    """
    with _auto_makers_registry_and_internal_record_hooks_maintenance_lock:
        _remove_from_auto_makers_registry(rec_attr)


#
# Internal constants and helpers (should be used only within this module!)
#


_PY_3_11_OR_NEWER = sys.version_info[:2] >= (3, 11)


#
# Machinery of *auto-makers* + internal *log record hooks*


_auto_makers_registry_and_internal_record_hooks_maintenance_lock = threading.Lock()
_auto_makers_registry: Sequence[tuple[str, Callable[[], object]]] = ()
_internal_record_hooks: Sequence[Callable[[logging.LogRecord], None]] = ()


def _add_to_auto_makers_registry(
    rec_attr: str,
    auto_maker: Callable[[], object],
) -> None:
    global _auto_makers_registry

    rec_attr_to_auto_maker = dict(_auto_makers_registry)
    if rec_attr in rec_attr_to_auto_maker:
        raise KeyError(f'{rec_attr=!a} already in auto-makers registry')
    rec_attr_to_auto_maker[rec_attr] = auto_maker
    new_registry = tuple(rec_attr_to_auto_maker.items())

    # (Such assignments are assumed to be *atomic* operations.)
    _auto_makers_registry = new_registry


def _remove_from_auto_makers_registry(
    rec_attr: str,
) -> None:
    global _auto_makers_registry

    rec_attr_to_auto_maker = dict(_auto_makers_registry)
    if rec_attr not in rec_attr_to_auto_maker:
        raise KeyError(f'{rec_attr=!a} not in auto-makers registry')
    del rec_attr_to_auto_maker[rec_attr]
    new_registry = tuple(rec_attr_to_auto_maker.items())

    # (Such assignments are assumed to be *atomic* operations.)
    _auto_makers_registry = new_registry


def _ensure_internal_record_hook_is_set_up(
    rec_hook: Callable[[logging.LogRecord], None],
) -> None:
    global _internal_record_hooks

    with _auto_makers_registry_and_internal_record_hooks_maintenance_lock:
        if rec_hook in _internal_record_hooks:
            return

        _ensure_record_factory_with_auto_makers_and_record_hooks_is_set()
        new_sequence = (*_internal_record_hooks, rec_hook)

        # (Such assignments are assumed to be *atomic* operations.)
        _internal_record_hooks = new_sequence


def _ensure_record_factory_with_auto_makers_and_record_hooks_is_set() -> None:
    if not _is_record_factory_with_auto_makers_and_record_hooks_impl_already_in_use():
        record_factory_being_wrapped = logging.getLogRecordFactory()
        new_record_factory = functools.partial(
            _record_factory_with_auto_makers_and_record_hooks_impl,
            record_factory_being_wrapped,
        )
        logging.setLogRecordFactory(new_record_factory)


def _is_record_factory_with_auto_makers_and_record_hooks_impl_already_in_use() -> bool:
    current_record_factory = logging.getLogRecordFactory()
    flag: list[None] = []
    try:
        # (Compare to the call to `_logRecordFactory()` in
        # the source code of `logging.makeLogRecord()`...)
        current_record_factory(
            None, None, '', 0, '', (), None, None,
            _record_factory_with_auto_makers_and_record_hooks_impl_confirm_flag=flag,
        )
    except Exception:  # noqa
        pass
    return bool(flag)


def _record_factory_with_auto_makers_and_record_hooks_impl(
    record_factory_being_wrapped: Callable[..., logging.LogRecord],
    /,
    *args: Any,
    _record_factory_with_auto_makers_and_record_hooks_impl_confirm_flag: list[None] | None = None,
    **kwargs: Any,
) -> logging.LogRecord:
    flag = _record_factory_with_auto_makers_and_record_hooks_impl_confirm_flag
    if flag is not None:
        flag.append(None)  # (<- Making the `flag` list *truthy*)

    record = record_factory_being_wrapped(*args, **kwargs)
    record_attrs: dict[str, object] = record.__dict__

    rec_attr: str
    auto_maker: Callable[[], object]
    for rec_attr, auto_maker in _auto_makers_registry:
        try:
            value = auto_maker()
        except RecursionError:
            raise
        except Exception:  # noqa
            # (Compare to the source code of `logging.Handler.handleError()`...)
            if logging.raiseExceptions and sys.stderr:
                sys.stderr.write(
                    f"--- Logging error ({__name__!a}-related) ---\n"
                    f"FAILED to auto-make log record's {rec_attr!a}!\n"
                    f"{traceback.format_exc()}\n"
                )
            continue

        actually_set_value = record_attrs.setdefault(rec_attr, value)
        if actually_set_value is not value:
            # (Compare to `KeyError(...)` in `logging.Logger.makeRecord()`...)
            raise KeyError(
                f"attempt to overwrite log record's {rec_attr!a} "
                f"(existing value: {actually_set_value!a}; "
                f"new rejected value: {value!a})"
            )

    for rec_hook in _internal_record_hooks:
        rec_hook(record)

    return record


def _clear_auto_makers_and_internal_record_hooks_related_global_state() -> None:
    # This function is intended to be used *in tests only*.

    global _auto_makers_registry
    global _internal_record_hooks

    with _auto_makers_registry_and_internal_record_hooks_maintenance_lock:
        _auto_makers_registry = ()
        _internal_record_hooks = ()
        ExtendedMessage._setup_of_record_hooks_still_needs_to_be_done = True


#
# Miscellaneous helpers


_T = TypeVar('_T')


def _resolve_dotted_path(dotted_path: str) -> Any:
    """
    Import an object specified by the given *dotted path*.

    >>> mod = _resolve_dotted_path('collections.abc')
    >>> import collections.abc
    >>> mod is collections.abc
    True

    >>> obj = _resolve_dotted_path('logging.handlers.SocketHandler')
    >>> from logging.handlers import SocketHandler
    >>> obj is SocketHandler
    True

    >>> _resolve_dotted_path('no_such_module_i_hope')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: cannot resolve dotted_path='no_such_module_i_hope' (ModuleNotFoundError...)

    >>> _resolve_dotted_path('logging.no_such_stuff_i_hope')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    ValueError: cannot resolve dotted_path='logging.no_such_stuff_i_hope' (ModuleNotFoundError...)
    """
    # (Compare to the source code of the -- semantically very similar
    # -- `logging.config.BaseConfigurator.resolve()` method...)
    importable_name, *rest_parts = dotted_path.split('.')
    try:
        obj = importlib.import_module(importable_name)
        for part in rest_parts:
            importable_name += f'.{part}'
            try:
                obj = getattr(obj, part)
            except AttributeError:
                importlib.import_module(importable_name)
                obj = getattr(obj, part)
    except ImportError as exc:
        raise ValueError(
            f'cannot resolve {dotted_path=!a} '
            f'({type(exc).__qualname__}: {exc})'
        ) from exc
    return obj

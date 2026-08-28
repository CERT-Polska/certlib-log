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
developers and system administrators.

Apart from the *structured logging* stuff, it also offers a few other
features...

***

### How to Install

You can install the `certlib.log` library by running the following
command (typically, you will do this within a Python [*virtual
environment*](https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments)):

```bash
python3 -m pip install certlib.log
```

!!! info "Requirements"

    The library is compatible with Python 3.10 and all newer versions of
    Python.

    It uses *only* the Python standard library -- it **does *not* depend
    on any third-party packages**.

!!! note

    The canonical name of the *distribution package* is `certlib-log`
    (with a hyphen), but *pip* and other tools accept also the
    `certlib.log` form (with a dot); the latter may feel more natural,
    as it is also the *importable module*'s name (used in Python code).

***

### TL;DR: How to Quickly Enable *Structured Logging*

Does your program already make use of the standard [`logging`][]
facilities *and* do you want it to start emitting *structured*
JSON-serialized log entries? Just make your logging setup include
[`certlib.log.StructuredLogsFormatter`][] as a *formatter* --
which can be as simple as:

```python
import logging, certlib.log

some_handler = logging.StreamHandler()
some_handler.setFormatter(
    certlib.log.StructuredLogsFormatter()
)
logging.getLogger().addHandler(some_handler)
```

That's it!

!!! tip

    Would you prefer a more *declarative* style? Here you go:

    ```python
    import logging.config

    logging.config.dictConfig({
        "formatters": {"fmt": {"()": "certlib.log.StructuredLogsFormatter"}},
        "handlers": {"some": {"class": "logging.StreamHandler", "formatter": "fmt"}},
        "root": {"handlers": ["some"]},
        "version": 1, "disable_existing_loggers": False
    })
    ```

Everything else is optional -- but probably worth a try, so you might
want to read on...


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
  (or callable of any other type), automatically called to produce a value
  for the respective key -- whenever a new [log record][logging.LogRecord]
  object is created by a logger (which only occurs if the logger is enabled
  for the specified log level), before the log record is processed by any
  *handlers*, *filters* and *formatters*;

* to replace the legacy `%`-based style of log message formatting with
  the modern and more convenient `{}`-based one, or (when what you need
  to log is just data) to omit passing the text message altogether; both
  gained by giving a little tweak to logger method calls...

While it is possible to use each of these capabilities independently of
the others, the `certlib.log`'s stuff encourages combining them.

The following sections will discuss the two main tools provided by the
library: [`StructuredLogsFormatter`][] and [`xm`][].

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
    check out at least one of these subsections (it is, however, still
    recommended to read also all earlier subsections!):

    * **[`logging.config.dictConfig`-Style Configuration Example](#loggingconfigdictconfig-style-configuration-example)**,
    * **[`logging.config.fileConfig`-Style Configuration Example](#loggingconfigfileconfig-style-configuration-example)**.

***

### Basic Configuration

Let us start by creating our [`StructuredLogsFormatter`][] instance
(obviously, the specific values used in the following code snippet
are just sample ones):

```python
import itertools
import json
import logging
import sys
from certlib.log import StructuredLogsFormatter

structured_logs_formatter = StructuredLogsFormatter(
    defaults={
        # * Each key in this dict should be an *output data* key.
        # * Each value specifies the *default value* for that key
        #   (to be used if no value is obtained by other means).
        # For example:
        "system": "MyOwn",
        "component": "Portal",
        "component_type": "web",
        "the_answer": 42,
    },
    auto_makers={
        # * Each key in this dict should be an *output data* key.
        # * Each value should be either some argumentless callable
        #   (function) or a *dotted path* to such a callable. In
        #   particular, the callable *may* be the `get()` method
        #   of some instance of `contextvars.ContextVar` (see:
        #   https://docs.python.org/3/library/contextvars.html).
        # For example:

        # (here: a callable passed directly)
        "just_local_counter": itertools.count(1).__next__,

        # (here: dotted paths pointing to callables)
        "nano_time": "time.time_ns",
        "client_ip": "myown.portal.client_ip_context_var.get",
    },
    # The value of `serializer` should be either a callable (function)
    # that accepts exactly one argument (being a JSON-serializable dict)
    # and returns a str object, or a *dotted path* to such a callable.
    # Note: the following serializer is the default -- so, in fact, it
    # is not necessary to specify it here. But the possibility to define
    # a custom serializer comes in handy when you want to use, e.g., a
    # faster alternative to the standard `json.dumps()` function (or
    # even a tool which serializes data in some other format...).
    serializer=json.dumps,
)
```

!!! note

    It is worth emphasizing that all arguments the
    **[`StructuredLogsFormatter`][]** constructor
    accepts are optional.

Whereas the purpose of the **`defaults`** and **`serializer`** arguments
seems quite obvious, the **`auto_makers`** one deserves more attention.
The ability to configure automatic inclusion of necessary information
(typically, dynamically collected) in every emitted log entry -- just
by assigning *auto-maker* callables to *output data* keys -- greatly
facilitates tailoring log contents to the needs of a specific program
or system, while also helping to maintain consistency.

Referring to the *auto-makers* specified in the example above:

* `just_local_counter` is a callable (precisely: an interator's *bound
  method*) -- which will provide each log entry with its sequential
  number;

* `nano_time` points (via a *dotted path*) to a Python standard library
  function -- employed here to ensure that every log entry will include
  a nanosecond-precise timestamp;

* `client_ip` points (via a *dotted path*) to a custom callable --
  presumably, the [`get`][contextvars.ContextVar.get] method of a
  *context variable* (suppossed to be already populated, which could
  have been done, e.g., by an HTTP request handler) -- the current
  value of which will be included in each (relevant) log entry.

!!! tip

    If the presence of some *output data* key makes sense only in a
    certain context (e.g., when handling an HTTP request...), just
    make the respective *auto-maker* return **[`None`][]** in any
    other contexts. Such *void* items will be automatically omitted
    from *output data*.

    For a context variable's **[`get`][contextvars.ContextVar.get]**,
    this can be achieved just by defining the variable's default value
    as **`None`**, like so:

    ```python
    client_ip_context_var = contextvars.ContextVar('client_ip_context_var', default=None)
    ```

Now that we have our [`StructuredLogsFormatter`][] instance created, the
next step is to prepare the *root logger*, and then add a *handler* to it
with our *formatter* attached:

```python
# (continuing with our main example)

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

    To learn more about using the **[`xm`][]** tool, see the
    **[Tool: `xm`](#tool-xm)** section of this guide (below).

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
    "first_issue_date": "1985-09-01",
    "just_local_counter": 6,
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
    "nano_time": 1771629287019638820,
    "pid": 324485,
    "process_name": "MainProcess",
    "src": "/opt/MyOwn/py/myown/portal/example_module.py",
    "system": "MyOwn",
    "the_answer": 42,
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

!!! tip

    One could ask:

    > _Where are my favorite old-fashioned
    > **[names](https://docs.python.org/3/library/logging.html#logrecord-attributes)**
    > of log record fields?! Where's **`asctime`**, **`funcName`**,
    > **`threadName`**?!_

    Apparently, one doesn't like our opinionated
    **[mapping][certlib.log.STANDARD_RECORD_ATTR_TO_OUTPUT_KEY]**
    of log record attributes to *output data* keys... (snifff)

    OK. It's great that we don't all like the same things! And
    many features of **`StructuredLogsFormatter`** can be easily
    **[customized](#more-about-structuredlogsformatter-including-subclassing)**
    by extending or entirely overriding some of its *hook methods*
    in a subclass... For example, if you or your organization are
    demanding the original record attribute names, just define and
    use such a class:

    ```python
    class MyDreamFormatter(StructuredLogsFormatter):
        def make_base_record_attr_to_output_key(self):
            return {}
    ```

***

### `logging.config.dictConfig`-Style Configuration Example

```python
import logging.config

logging_configuration_dict = {
    "formatters": {
        "structured": {
            "()": "certlib.log.StructuredLogsFormatter",
            "defaults": {
                # * Each key in this dict should be an *output data* key.
                # * Each value specifies the *default value* for that key
                #   (to be used if no value is obtained by other means).
                # For example:
                "system": "MyOwn",
                "component": "Portal",
                "component_type": "web",
                "the_answer": 42,
            },
            "auto_makers": {
                # * Each key in this dict should be an *output data* key.
                # * Each value should be either some argumentless callable
                #   (function) or a *dotted path* to such a callable. In
                #   particular, the callable *may* be the `get()` method
                #   of some instance of `contextvars.ContextVar` (see:
                #   https://docs.python.org/3/library/contextvars.html).
                # For example:
                "client_ip": "myown.portal.client_ip_context_var.get",
                "nano_time": "time.time_ns",
            },
            # The value of "serializer", if specified, should be either
            # a callable (function) which accepts exactly one argument
            # (being a JSON-serializable dict) and returns a str object,
            # or a *dotted path* to such a callable. If "serializer" is
            # not specified, the standard `json.dumps()` function will
            # be used.
            "serializer": "some_package.faster_replacement_for_json_dumps",
        },
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stderr",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["stderr"],
    },
    "disable_existing_loggers": False,
    "version": 1,
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
        # * Each key in this dict should be an *output data* key.
        # * Each value specifies the *default value* for that key
        #   (to be used if no value is obtained by other means).
        # For example:
        "system": "MyOwn",
        "component": "Portal",
        "component_type": "web",
        "the_answer": 42,
    },
    "auto_makers": {
        # * Each key in this dict should be an *output data* key.
        # * Each value should be a *dotted path* to some argumentless
        #   callable (function). In particular, the callable *may* be
        #   the `get()` method of some `contextvars.ContextVar` instance
        #   (see: https://docs.python.org/3/library/contextvars.html).
        # For example:
        "client_ip": "myown.portal.client_ip_context_var.get",
        "nano_time": "time.time_ns",
    },
    # The value of "serializer", if specified, should be a *dotted path*
    # to a callable (function) which accepts exactly one argument (being
    # a JSON-serializable dict) and returns a str object. If "serializer"
    # is not specified, the standard `json.dumps()` function will be used.
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

### Configuration Validation and Adjustments

Regardless of the configuration style you choose, you may need to
perform customized *validation* and/or *adjustments* concerning your
[`StructuredLogsFormatter`][] configuration while the formatter is
initialized. If so, define your custom *configuration corrector*
function and specify it as yet another argument to the
`StructuredLogsFormatter` constructor: **`conf_corrector`**.

Since the technical details are discussed in the [reference documentation
for the constructor][StructuredLogsFormatter], here we will focus on a
practical example.

Let us implement a simple *configuration corrector*:

```python
# Let's place it, e.g., in a module importable as `myown.log_helpers`.

def my_conf_corrector(conf: dict) -> dict:
    # The given dict always contains:
    # * "defaults" -- dict: *output data* keys to default values
    # * "auto_makers" -- dict: *output data* keys to *auto-maker* callables
    # * "serializer" -- callable
    # * "base_record_attr_to_output_key" -- dict: log record attribute
    #   names (str) to *output data* keys (str) or None values
    # * "conf_corrector_params" -- dict of custom parameters for the
    #   corrector, useful when you need to provide your corrector with
    #   some extra information (by default, just like here, it is empty)

    # *** Validation ***
    # Requiring certain keys to always be present in
    # the `defaults` and/or `auto_makers` mapping(s):
    required = {"env_type", "python_version"}
    provided = conf["defaults"].keys() | conf["auto_makers"].keys()
    missing = required - provided
    if missing:
        raise ValueError(
            f"missing keys in `defaults` and"
            f"/or `auto_makers`: {missing!r}"
        )

    # *** Adjustment ***
    # Another (alternative to subclassing) way to force the use of
    # the original log record attribute names as *output data* keys
    # (disregarding the `STANDARD_RECORD_ATTR_TO_OUTPUT_KEY` mapping):
    conf["base_record_attr_to_output_key"].clear()

    # Every *configuration corrector* function -- unless it raises
    # an exception -- should return a dict with a structure similar
    # to that of the dict received as the argument (it can even be
    # the same dict).
    return conf
```

Now, all we need to do is update [our `StructuredLogsFormatter`
setup](#basic-configuration) by setting **`conf_corrector`** to our
*corrector* (or a *dotted path* pointing to it), plus adjusting the
**`defaults`** and **`auto_makers`** mappings to accommodate the new
requirements the *corrector* imposes on them:

```python
# ...snipped for brevity...
from certlib.log import StructuredLogsFormatter
from myown.log_helpers import my_conf_corrector       # added

structured_logs_formatter = StructuredLogsFormatter(
    defaults={
        # ...snipped...
        "env_type": "prod",                           # added
    },
    auto_makers={
        # ...snipped...
        "python_version": "platform.python_version",  # added
    }
    # ...snipped...
    conf_corrector=my_conf_corrector,                 # added (!)
)
# ...snipped...
```

!!! note

    Of course, the above update can be applied to a
    **[`dictConfig`-style](#loggingconfigdictconfig-style-configuration-example)** or
    **[`fileConfig`-style](#loggingconfigfileconfig-style-configuration-example)**
    configuration as well:

    ```python
        # ...snipped...
        "defaults": {
            # ...snipped...
            "env_type": "prod",
        },
        "auto_makers": {
            # ...snipped...
            "python_version": "platform.python_version",
        }
        # ...snipped...
        "conf_corrector": "myown.log_helpers.my_conf_corrector",
        # ...snipped...
    ```

There is one more argument accepted by the [`StructuredLogsFormatter`][]
constructor: **`conf_corrector_params`**. It makes it possible to provide
the *corrector* with arbitrary extra information.

For example, we could enhance the *corrector* defined above by adding
the ability to specify (at the level of formatter setup, i.e., in the
formatter instantiation code, or an equivalent configuration file) a set
of extra required *output data* keys. So that it would be possible to
update our setup like so:

```python
# ...snipped...
structured_logs_formatter = StructuredLogsFormatter(
    defaults={
        # ...snipped...
        "env_type": "prod",
    },
    auto_makers={
        # ...snipped...
        "python_version": "platform.python_version",
        "platform": "platform.platform",              # added
        "architecture": "platform.architecture",      # added
    },
    # ...snipped...
    conf_corrector=my_conf_corrector,
    conf_corrector_params={                           # added (!)
        "extra_required_keys": ["platform", "architecture"],
    },
)
# ...snipped...
```

!!! note

    In the case of a
    **[`dictConfig`-style](#loggingconfigdictconfig-style-configuration-example)** or
    **[`fileConfig`-style](#loggingconfigfileconfig-style-configuration-example)**
    configuration -- it would be:

    ```python
        # ...snipped...
        "defaults": {
            # ...snipped...
            "env_type": "prod",
            "platform": "platform.platform",
            "architecture": "platform.architecture",
        },
        "auto_makers": {
            # ...snipped...
            "python_version": "platform.python_version",
        },
        # ...snipped...
        "conf_corrector": "myown.log_helpers.my_conf_corrector",
        "conf_corrector_params": {
            "extra_required_keys": ["platform", "architecture"],
        },
        # ...snipped...
    ```

Then, the enhanced implementation of our *corrector* might look like this:

```python
# ...in a module importable as `myown.log_helpers`.

def my_conf_corrector(conf: dict) -> dict:
    # [...all comments omitted for brevity...]
    params = conf["conf_corrector_params"]
    extra_required_keys = set(params.get("extra_required_keys", []))
    required = {"env_type", "python_version"} | extra_required_keys
    provided = conf["defaults"].keys() | conf["auto_makers"].keys()
    missing = required - provided
    if missing:
        raise ValueError(
            f"missing keys in `defaults` and"
            f"/or `auto_makers`: {missing!r}"
        )
    conf["base_record_attr_to_output_key"].clear()
    return conf
```

In summary, a custom *configuration corrector* may validate and/or
adjust a [`StructuredLogsFormatter`][]'s configuration in any way
you choose. In an extreme case, it could even replace your initial
static configuration with completely different, dynamically generated,
settings...

!!! tip

    In the source code of the `certlib.log` module, you can find a more
    sophisticated *configuration corrector* than the one drafted above:
    **`_opinionated_conf_corrector`**. Studying its implementation may
    be instructive.

    !!! exclusion "Interface exclusion"

        **`_opinionated_conf_corrector`** is _**not**_ part of the
        `certlib.log` public API. This means that any elements of
        that *corrector* may be changed or removed in *minor* or
        *patch* versions of the library (including the possibility
        of completely removing that *corrector*).

***

## **Tool: `xm`**

Essentially, the purpose of [`xm`][] is two-fold:

* to make it more convenient to emit *structured log entries* (each being
  representable as a [`dict`][]), especially if a [`StructuredLogsFormatter`][]
  is in use;

* if you choose the traditional *text-message-focused style* of logging
  (rather than a *pure-data-focused*, message-less one) -- to easily
  replace the legacy `%`-based log message formatting style with the
  modern and more convenient `{}`-based one (regardless of what formatter
  is in use).

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
    if you pass a function/method (also a [**`lambda`**](https://docs.python.org/3/tutorial/controlflow.html#lambda-expressions)
    expression) instead of a plain value, it will be automatically
    called -- at the log entry formatting stage -- to obtain the
    actual value (by a formatter of any type, i.e., not necessarily a
    **`StructuredLogsFormatter`**; and in a *lazy* manner -- not more
    than once per **`xm`** instance).

    In practice, this feature is useful if the creation of a certain
    value is costly -- and you prefer it to be created when (and if)
    the log entry is actually about to be formatted and emitted.

    !!! note

        By default, the mechanism is applied *only* if you pass a
        *function* or *method* object -- *not* just an arbitrary
        callable (as that could lead to inadvertent calls...).

    !!! note

        Do not confuse this mechanism (in which the value creation is
        triggered just for a particular log record object -- once it
        arrives at any formatter) with the mechanism of [*auto-makers*](#basic-configuration)
        (triggered automatically for *every* log record object right
        after its creation -- which happens *before* any formatter-specific
        activity comes into play).

        What is actually common to these two distinct mechanisms is that
        the value creation will never happen if the logger being used is
        not [enabled](https://docs.python.org/3/library/logging.html#logging.Logger.isEnabledFor)
        for the requested log level (note that, in such cases, no log
        record object is created at all).

***

### Modern Formatting Style

Below there are a few examples of traditional *text-message-focused*
logging, but -- what using the [`xm`][] tool makes possible -- with the
modern and convenient [`{}`-based style of message formatting](https://docs.python.org/3/library/string.html#format-string-syntax)
(rather than the legacy, less convenient and less powerful, `%`-based one).

!!! note

    What we are discussing here concerns the formatting of *text
    messages* themselves (i.e., the contents of log records’ `message`),
    rather than the formatting of *entire log entries* (where `message`
    is just one field). Note that the latter is completely orthogonal
    to the former. Whereas the standard tools provided by the `logging`
    module [*do* support](https://docs.python.org/3/library/logging.html#formatter-objects)
    the `{}`-based formatting style for the latter, they do *not* support
    it for the former.

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

What that means if the logging system is configured to employ a
[`StructuredLogsFormatter`][], is that:

* the formatted message will appear in the JSON-serialized *output
  data* as the item: `"message": "Note: foo is 'Bar' (in 2026-02)"`,
* and the raw message pattern will also be included, like this:
  `"message_base": {"pattern": "Note: {} is {!r} (in {:%Y-%m})"}`.

!!! info

    When you use **[`xm`][]**, you still benefit from the standard
    mechanism of deferring message formatting until the log entry
    really needs to be emitted (regardless of what formatter is in
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
    "func": "<module>",
    "just_local_counter": 4,
    "level": "INFO",
    "levelno": 20,
    "lineno": 179,
    "logger": "myown.portal.another_example_module",
    "message": "Note: foo is 'Bar' (in 2026-02)",
    "message_base": {
        "pattern": "Note: {} is {val!r} (in {today:%Y-%m})"
    },
    "nano_time": 1771631594315719605,
    "pid": 327578,
    "process_name": "MainProcess",
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
    "the_answer": 42,
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

***

### More About `StructuredLogsFormatter` (Including Subclassing)

If you have not read the *reference documentation* for the
[`StructuredLogsFormatter`][] class yet, you are strongly encouraged to
do so. Among other things, you will find there a list of hook methods
that can be extended/overridden in your subclasses. Apart from that,
the documentation in question includes (especially, in the individual
descriptions of those hook methods) valuable information about other
elements of the `StructuredLogsFormatter`'s interface and behavior.

***

### Other Stuff Provided by `certlib.log`

Besides [`StructuredLogsFormatter`][] and [`xm`][] ([`ExtendedMessage`][]),
the `certlib.log` module's public API includes:

* the [`make_constant_value_provider`][] function (a minor helper,
  useful when you need to create an *auto-maker* that will always
  return the same value);

* the [`register_log_record_attr_auto_maker`][] and
  [`unregister_log_record_attr_auto_maker`][] functions
  (typically, they do not need to be used directly --
  see their *reference documentation*...);

* the [`STANDARD_RECORD_ATTR_TO_OUTPUT_KEY`][] constant
  (defines the default mapping of [log record attribute
  names](https://docs.python.org/3/library/logging.html#logrecord-attributes)
  to actual *output data* keys; this mapping is used by the
  `StructuredLogsFormatter`'s default implementation of the
  [`make_base_record_attr_to_output_key`][StructuredLogsFormatter.make_base_record_attr_to_output_key]
  method);

* a few [static typing helpers](reference.md#static-typing-helpers)
  (ancillary stuff you do not usually need to pay much attention to).

***

### Roadmap Outline

Future ideas under consideration include:

* [`StructuredLogsFormatter`][]: add the ability to specify keys related
  to *sensitive* data -- so that values assigned to them in *output data*
  will be automatically masked/anonymized.

* [`xm`][]: add dedicated suport for [`pattern`][ExtendedMessage.pattern]
  of type [`string.templatelib.Template`][] (instances of which can be
  created by evaluating [*t-strings*](https://docs.python.org/3/library/stdtypes.html#stdtypes-tstrings)
  -- available in Python 3.14 and newer). Additionaly, to support passing
  such *t-string*-made *template* objects directly to logger methods, add
  an opt-in mechanism that will automatically wrap such *templates* in
  [`xm`][] objects -- so that, e.g., you could just do:
  `logger.info(t"Hello, {name}")`.
"""


# mypy: disable_error_code = "unused-ignore"


from __future__ import annotations

import abc
import ast
import collections
import dataclasses
import datetime as dt
import decimal
import enum
import fractions
import functools
import importlib
import ipaddress
import itertools
import json
import logging
import math
import os.path
import reprlib
import sys
import textwrap
import threading
import traceback
import types
import uuid
from collections.abc import (
    Callable,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from copy import deepcopy
from inspect import (
    Parameter,
    getdoc,
    signature,
)
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal,
    Protocol,
    TypeVar,
    TypedDict,
    cast,
    overload,
)
if TYPE_CHECKING:
    from typing import TypeAlias


__all__ = (
    'STANDARD_RECORD_ATTR_TO_OUTPUT_KEY',

    'StructuredLogsFormatter',
    'ExtendedMessage',
    'xm',

    'make_constant_value_provider',
    'register_log_record_attr_auto_maker',
    'unregister_log_record_attr_auto_maker',

    'ValueProvider',
    'OutputSerializer',
    'DottedPath',
    'KwargsMappingAsLiteralEvaluableString',
    'ConfCorrector',
    'ConfDict',
    'CorrectedConfDict',
)


#
# Global constants
#


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

    # The following log record attributes are *not*
    # to be included in *output data* by default:
    'args': None,       # <- Info it conveys is typically redundant (with respect to `message`).
    'created': None,    # <- The `asctime` attribute provides sufficient info.
    'filename': None,   # <- The `pathname` attribute provides sufficient info.
    'module': None,     # <- Redundant and confusing (just `filename` without its suffix).
    'msecs': None,      # <- The `asctime` attribute provides sufficient info.
    'relativeCreated': None,   # <- Confusing and hardly useful. (Uptime in milliseconds? Meh...)
})


#
# Actual tools
#


class StructuredLogsFormatter(logging.Formatter):

    """
    A subclass of [`logging.Formatter`][] to form structured log entries.

    !!! tip

        If the three call signatures defined by the
        **[`StructuredLogsFormatter`][]** constructor seem
        overwhelming, do not worry. In most cases, you will
        only really be interested in the first one (the
        *main* signature). The details are provided below.

    **Constructor arguments** (all *keyword-only*, all *optional*):

    * **`defaults`** (a [`dict`][] or other mapping; default: `{}`):
      maps *output data* keys to values each of which specifies
      the *default value* for the respective key (see also the
      [`make_base_defaults`][] method...).

    * **`auto_makers`** (a [`dict`][] or other mapping; default: `{}`):
      maps *output data* keys to respective *auto-makers* (argumentless
      factories of *output data* values -- to be automatically called
      whenever a log entry is created). Each *auto-maker* can be
      specified either directly or as a string being a *dotted path*
      (*importable dotted name*) that points to an *auto-maker* (see
      also the [`make_base_auto_makers`][] method...).

        ??? warning "Output key validation"

            It is required that every *output data* key (just *key*,
            as we are *not* talking about *output data* values here)
            appearing in any of the mappings listed below -- be a
            *string* and *not* exceed 200 characters (otherwise,
            respectively, [`TypeError`][] or [`ValueError`][] will be
            raised by the constructor). The mappings covered by this
            requirement are:

            * that returned by the **[`make_base_defaults`][]** method,

            * the **`defaults`** argument described above (if actually
              passed),

            * that returned by the **[`make_base_auto_makers`][]** method,

            * the **`auto_makers`** argument described above (if actually
              passed),

            * that returned by the **[`make_base_record_attr_to_output_key`][]**
              method (note that the requirement in question applies to *output
              data* keys -- which, when it comes to this mapping, are its
              *values*, not its *keys*; and note that this mapping's values
              are also allowed to be [`None`][]).

    * **`serializer`** (a function or other callable; default: [`json.dumps`][]):
      a callable that takes one argument being an *output data* [`dict`][]
      and returns a string (presumably, a JSON-serialized form of that
      dict, even though you may decide to use some other serialization
      format, if this is OK for you/your organization). Alternatively,
      **`serializer`** can be a *dotted path* string (*importable dotted
      name*) that points to such a callable.

        ??? note "Output data typing"

            The type of every *output data* dict (taken by **`serializer`**)
            is annotated as **`dict[str, OutputValue]`**. Essentially, the
            **[`OutputValue`][]** element denotes all types of values that
            might be returned by the actually used implementation of the
            **[`prepare_value`][]** method. In other words, that method is
            what determines those types.

            Note that the default implementation of that method always
            returns values of [`json.dumps`][]-compatible types.

        ??? warning "Mutability restriction"

            While **`serializer`** is allowed to add, remove or replace
            *top-level* items in an *output data* dict it takes, it should
            *never* mutate any object inside that dict (regardless of the
            level of nesting). If some data needs to be changed, completely
            *new* data object(s) should be created as a replacement for the
            original one(s). Doing otherwise will result in undefined
            behavior.

    * **`conf_corrector`** (a function or other callable, or [`None`][]
      -- which is the default): a custom callable that is automatically
      invoked for extra validation and/or adjustments regarding the
      instance configuration (including also the arguments described
      above); it can also be a *dotted path* string (*importable
      dotted name*) that points to such a callable. In the rest of
      the documentation, a callable specified via this argument is
      referred to as a *configuration corrector* (or just *corrector*).
      The `StructuredLogsFormatter` constructor executes the *corrector*
      just once -- before the main part of the formatter initialization.

        ??? info "Corrector interface"

            Every *configuration corrector* should comply with the
            **[`ConfCorrector`][]** protocol -- which requires it to be
            a callable object that:

            * accepts one positional argument: a [`dict`][] (hereinafter
              referred to as the *given* dict), structured according to
              the **[`ConfDict`][]** specification;

            * *either* raises an exception (typically, but not necessarily,
              a [`ValueError`][]), *or* returns a [`dict`][] (hereinafter
              referred to as the *returned* dict), structured according
              to the **[`CorrectedConfDict`][]** specification.

            The *returned* dict is allowed -- but *not* required -- to be
            equal to the *given* dict, and/or to be the same dict object
            (modified or not). Any exception, if raised, will bubble up
            to the caller of the **`StructuredLogsFormatter`** constructor.

            The *given* dict, created by the constructor, always contains
            the following items:

            * `"defaults"`: a **[`make_base_defaults`][]**-produced
              mapping merged with the constructor's **`defaults`**
              argument (described earlier), then converted to a [`dict`][]
              and [deep-copied][copy.deepcopy]; all its keys have already
              been verified as valid *output data* keys -- but its values
              have _**not**_ been transformed with **[`prepare_value`][]**
              yet (see the *Related interfaces* note in the description of
              the **[`make_base_defaults`][]** method...);

            * `"auto_makers"`: a **[`make_base_auto_makers`][]**-produced
              mapping merged with the constructor's **`auto_makers`**
              argument (described earlier), then converted to a [`dict`][]
              and [deep-copied][copy.deepcopy] -- ready to be set as the
              **[`auto_makers`][]** formatter attribute (i.e., with all
              keys already verified as valid *output data* keys, all
              *dotted path* values already resolved, and *all* values
              already verified as being callable objects);

            * `"serializer"`: the callable specified as the constructor's
              **`serializer`** argument (described earlier) -- ready to be
              set as the **[`serializer`][]** formatter attribute (i.e.,,
              already resolved if given as a *dotted path*, and verified
              as being a callable object);

            * `"base_record_attr_to_output_key"`: a
              **[`make_base_record_attr_to_output_key`][]**-produced mapping,
              converted to a [`dict`][] and [deep-copied][copy.deepcopy],
              with all values already verified as valid *output data* keys
              or [`None`][];

            * `"conf_corrector_params"`: a mapping received
              by the `StructuredLogsFormatter` constructor
              via **`conf_corrector_params`** (see below...),
              converted to a [`dict`][] and [deep-copied][copy.deepcopy].

            The required structure of the *returned* dict is generally
            similar, but fewer restrictions apply to it (compare
            **[`ConfDict`][]** vs. **[`CorrectedConfDict`][]**). In
            particular, the *returned* dict is allowed to include a
            subset of the keys listed above, instead of including all of
            them (the absence of an item is equivalent to including it
            unchanged from its initial form the *given* dict included).

            !!! warning "Forward compatibility requirement"

                In future versions of the library, including *non-major*
                ones, other items may also appear in the *given* dict (in
                addition to the five items listed above). Therefore, every
                *corrector* should ignore any unrecognized keys in the
                *given* dict. Also, it should *not* add to the *returned*
                dict any keys that were not present in the *given* dict.

            As you can see, the *given* dict's items are automatically
            processed (converted/deep-copied/verified/resolved, as
            described above) -- before the *corrector* is executed. It
            should be added here that the *returned* dict's items are
            processed in the same way -- after the *corrector* is
            executed (yet still before using them in the main part of
            the formatter initialization). One exception: the *returned*
            dict's `"conf_corrector_params"` item (if present at all) is
            ignored.

    * **`conf_corrector_params`** (a [`dict`][] or other mapping; default: `{}`):
      additional custom data the **`conf_corrector`** callable will get.
      Ignored if **`conf_corrector`** is [`None`][] or unspecified.

    **Alternatively**, a mapping (especially a [`dict`][]) of keyword
    arguments compatible with the main signature described above, or an
    [`ast.literal_eval`][]-evaluable string representing such a dict,
    can be passed to the [`StructuredLogsFormatter`][] constructor as
    the *first positional argument*.

    **Moreover**, *extra* arguments that match -- by *position* or
    by *name* -- any _**non**-keyword-only_ parameters defined by the
    [`logging.Formatter`][] base class are *accepted but ignored* by
    the `StructuredLogsFormatter` constructor, *provided that* the
    value of each (if given) is the default value of the respective
    parameter; that is:

    * the *first* or **`fmt`** argument -- needs to be [`None`][] (except
      that it is fine for the *first* argument to be a mapping or a string
      representing a mapping, as described above...);

    * the *second* or **`datefmt`** argument -- needs to be [`None`][];

    * the *third* or **`style`** argument -- needs to be the `"%"` string
      (remember, it will be ignored anyway);

    * the *fourth* or **`validate`** argument -- needs to be [`True`][].

    If any of them does not comply, [`TypeError`][] is raised (and,
    generally, any surplus arguments to the `StructuredLogsFormatter`
    constructor cause [`TypeError`][] as well).

    !!! note

        Thanks to the interface extensions described above, you can
        configure a **`StructuredLogsFormatter`** even if you are
        using the [`logging.config.fileConfig`][]-specific configuration
        format (which, despite its limitations, is still quite popular).

        See the **`formatter_structured`** section of the `fileConfig`-style
        [configuration example](guide.md#certlib.log--loggingconfigfileconfig-style-configuration-example)
        in the *User's Guide*.

    !!! warning "Deep-copyable mapping items"

        Regardles of the constructor call variant, every mapping/dict
        involved in the formatter initialization (whether it has been
        passed to the constructor; or obtained by resolving a *dotted
        path*; or returned by any customized **`make_base_*`** hook
        method -- see below; or returned by a *configuration corrector*)
        needs to contain only items that can be passed to the
        **[`copy.deepcopy`][]** function.

        !!! tip

            This requirement is not as scary as it may sound, given
            that most built-in types and many custom types meet it
            *out-of-the-box*. Usually, you will not need to worry
            about it at all.

        ??? note

            It is also worth emphasizing that when the **`deepcopy`**
            operation's input is a non-collection object (or, generally,
            any object whose entire content -- at all levels of nesting
            when it comes to nested data structures -- is considered
            immutable), then it is perfectly OK if that operation returns
            the exact same object (without actually copying anything).
            For example, this is the case for function and method
            objects...

    This class defines the following *hook methods* that can be
    extended/overridden in subclasses:

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

    !!! warning "Mutability restriction"

        Modifying any nested mutable data within any of the aforementioned
        atributes (in particular, any mutable values in **[`defaults`][]**)
        is forbidden. Doing so will result in undefined behavior.

    When it comes to customizing the format of log entry *timestamps*, the
    related attributes defined by the [`logging.Formatter`][] base class
    (namely: `converter`, `default_time_format` and `default_msec_format`)
    are _**ignored**_ by the machinery of `StructuredLogsFormatter`.

    To learn how to actually customize *timestamp formatting*, please
    refer to the description of the [`format_timestamp`][] method.

    !!! info "See also"

        For practical information about **`StructuredLogsFormatter`**,
        including a bunch of examples and configuration tips, see the
        **[Tool: `StructuredLogsFormatter`](guide.md#certlib.log--tool-structuredlogsformatter)**
        section of the *User's Guide*.
    """

    #
    # Attributes and instance lifecycle (public stuff)

    # * This-class-specific instance attributes:

    defaults: Final[Mapping[str, OutputValue]]
    auto_makers: Final[Mapping[str, ValueProvider[object]]]
    auto_made_record_attr_prefix: Final[str]
    record_attr_to_output_key: Final[Mapping[str, str | None]]
    serializer: Final[OutputSerializer]

    # * Instance-lifecycle-related stuff:

    @overload
    # The main signature
    def __init__(
        self, /,
        *,
        defaults: Mapping[str, object] | None = None,
        auto_makers: Mapping[str, ValueProvider[object] | DottedPath] | None = None,
        serializer: OutputSerializer | DottedPath = json.dumps,
        conf_corrector: ConfCorrector | DottedPath | None = None,
        conf_corrector_params: Mapping[str, Any] | None = None,
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
        mapping_of_kwargs_compatible_with_main_signature: (
            Mapping[
                Literal[
                    'defaults',
                    'auto_makers',
                    'serializer',
                    'conf_corrector',
                    'conf_corrector_params',
                ],
                Any,
            ]
            | KwargsMappingAsLiteralEvaluableString
        ),
        /,

        # These three `logging.Formatter`-specific arguments are to
        # be *accepted and ignored* as long as the value of each is
        # the respective `logging.Formatter`-specific default value.
        datefmt: None = None,
        style: Literal['%'] = '%',
        validate: Literal[True] = True,
    ):
        ...

    @overload
    # A variant provided for completeness...
    def __init__(
        self, /,

        # These four `logging.Formatter`-specific arguments are to
        # be *accepted and ignored* as long as the value of each is
        # the respective `logging.Formatter`-specific default value.
        fmt: None = None,
        datefmt: None = None,
        style: Literal['%'] = '%',
        validate: Literal[True] = True,

        *,
        defaults: Mapping[str, object] | None = None,
        auto_makers: Mapping[str, ValueProvider[object] | DottedPath] | None = None,
        serializer: OutputSerializer | DottedPath = json.dumps,
        conf_corrector: ConfCorrector | DottedPath | None = None,
        conf_corrector_params: Mapping[str, Any] | None = None,
    ):
        ...

    def __init__(self, /, *args: Any, **kwargs: Any):
        arguments = self._extract_meaningful_arguments(args, *args, **kwargs)

        given_defaults = arguments.pop('defaults', None) or {}
        given_auto_makers = arguments.pop('auto_makers', None) or {}
        given_serializer = arguments.pop('serializer', json.dumps)
        given_conf_corrector = arguments.pop('conf_corrector', None)
        given_conf_corrector_params = arguments.pop('conf_corrector_params', None) or {}

        if arguments:
            raise TypeError(
                f'{type(self).__init__.__qualname__}() got unexpected '
                f'keyword argument(s): {", ".join(map(ascii, arguments))}'
            )

        super().__init__()

        raw_defaults = self._as_ready_raw_defaults({
            **self.make_base_defaults(),
            **given_defaults,
        })
        auto_makers = self._as_ready_auto_makers({
            **self.make_base_auto_makers(),
            **given_auto_makers,
        })
        base_attr_to_key = self._as_ready_base_attr_to_key(
            self.make_base_record_attr_to_output_key(),
        )
        serializer = self._resolve_serializer(given_serializer)

        if given_conf_corrector is not None:
            conf_corrector = self._resolve_conf_corrector(given_conf_corrector)
            conf_corrector_params = self._sorted_dict_deepcopy(
                given_conf_corrector_params,
            )
            conf: ConfDict = {
                'defaults': raw_defaults,
                'auto_makers': auto_makers,
                'serializer': serializer,
                'base_record_attr_to_output_key': base_attr_to_key,
                'conf_corrector_params': conf_corrector_params,
            }

            corrected: CorrectedConfDict = conf_corrector(conf)

            if 'defaults' in corrected:
                raw_defaults = self._as_ready_raw_defaults(corrected['defaults'])
            if 'auto_makers' in corrected:
                auto_makers = self._as_ready_auto_makers(corrected['auto_makers'])
            if 'serializer' in corrected:
                serializer = self._resolve_serializer(corrected['serializer'])
            if 'base_record_attr_to_output_key' in corrected:
                base_attr_to_key = self._as_ready_base_attr_to_key(
                    corrected['base_record_attr_to_output_key'],
                )

        self.defaults = self._prepare_and_filter_defaults(raw_defaults)
        self.auto_makers = auto_makers
        self.auto_made_record_attr_prefix = self._make_auto_made_record_attr_prefix()
        self.record_attr_to_output_key = self._make_record_attr_to_output_key(
            base_attr_to_key,
        )
        self.serializer = serializer

        for rec_attr, auto_maker in self._get_record_attr_to_auto_maker().items():
            register_log_record_attr_auto_maker(rec_attr, auto_maker)

    def unregister_auto_makers(self) -> None:
        """
        A rarely useful method: you may want to invoke it on an instance
        of `StructuredLogsFormatter` *only when* you need to stop using
        that instance but continue using any `logging` stuff during
        further program execution (this does not seem to be a common
        case).
        """
        for rec_attr in self._get_record_attr_to_auto_maker().keys():
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

        * if the log record's `exc_info` attribute is a `(None, None,
          None)` tuple, then it is treated as if it were *falsy* (the
          `formatException` method is *not* invoked, and the log record's
          `exc_text` attribute is *not* set);

        * the string returned by `formatMessage` becomes the return value
          of *this* method (so this method *never* appends to that string
          any *formatted traceback* or *formatted stack information*, and
          it does *not* invoke [`formatStack`][logging.Formatter.formatStack]
          either); the returned string is supposed to represent the *output
          data* dict after serialization -- therefore, it should already
          include, among others, any exception/stack information, if such
          stuff was requested and obtained;

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
                args_repr = self._get_record_args_repr(args)
                raise TypeError(
                    f"the specified log message base is an instance "
                    f"of {ExtendedMessage.__qualname__} ({msg=!a}); "
                    f"in such a case, any positional arguments to "
                    f"format the log message should have been passed "
                    f"to the `{ExtendedMessage.__qualname__}(...)` "
                    f"(or `xm(...)`) call, not to the logger method "
                    f"call itself (*args obtained by it: {args_repr})"
                )
            record.message = msg.get_message_value()
        else:
            record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        if (record.exc_info
              and record.exc_info != (None, None, None)
              and not record.exc_text):
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
        else, [`TypeError`][] is raised -- which then, typically, is
        suppressed and, possibly, printed to [`sys.stderr`][] by
        [`logging.Handler.handleError`][]...).
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
                f"of this, you might decide to completely override the "
                f"`{slf_formatTime}` method, providing an implementation "
                f"which, for example, would use the `logging.Formatter`'s "
                f"legacy timestamp-formatting-related stuff, without any "
                f"use of the `{slf_format_timestamp}` method...)"
            )
        return self.format_timestamp(record)

    def formatMessage(self, record: logging.LogRecord) -> str:
        """
        Overrides the [`logging.Formatter`][]'s implementation with such
        one that:

        * obtains a ready *output data* dict by applying the
          [`get_prepared_output_data`][] method to the given
          log record;

        * applies the [`serialize_prepared_output_data`][]
          method to the obtained *output data* dict, and
          returns the result.

        ??? note "Details"

            The **`formatMessage`** name may be slightly misleading. Let
            us emphasize that the job of this method is *always* -- also
            in the case of the original **[`logging.Formatter`][]** class
            -- to format the crux of the _**entire**_ log entry, _**not**_
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

    def make_base_defaults(self) -> Mapping[str, object]:
        """
        A hook method: extend/override it in a subclass to define basic
        *default values* for output.

        Automatically invoked on the formatter initialization. Each key in
        the resultant mapping needs to be an *output data* key, and each
        value in that mapping needs to be the desired *default value* for
        that key.

        The default implementation of this method returns an empty mapping.

        !!! info "Related interfaces"

            For every instance, the mapping assigned to the instance's
            **[`defaults`][]** attribute (supposed to specify *default
            values* for *output data* items to be generated by the
            instance) is based on this method's result, first converted
            to a [`dict`][], updated with all items from the **`defaults`**
            argument to the [constructor][StructuredLogsFormatter] (if
            given), and [deep-copied][copy.deepcopy]; then -- adjusted
            by applying the **[`prepare_value`][]** method to each value;
            and then, filtered by deleting each key to which a *void*
            value is assigned (by *void* value we mean any *falsy* value
            that is *not equal* to `0`, for example: [`None`][], `""`,
            `[]` or `{}` -- but _**not:**_ [`False`][], `0`, `0.0`, etc.).
        """
        return {}

    def make_base_auto_makers(self) -> Mapping[str, ValueProvider[object] | DottedPath]:
        """
        A hook method: extend/override it in a subclass to define basic
        *auto-makers* for output.

        Automatically invoked on the formatter initialization. Each key
        in the resultant mapping needs to be an *output data* key, and
        each value in that mapping needs to be either an *auto-maker*
        or a *dotted path* (*importable dotted name*) that points to an
        *auto-maker*. Each *auto-maker* is supposed to be an argumentless
        function (or a callable object of some other type) returning --
        whenever it is called -- a candidate for an *output data* value
        (to be assigned to the respective *output data* key).

        !!! info "See also"

            You may want to learn more about *auto-makers*
            themselves by referring to the description of the
            **[`register_log_record_attr_auto_maker`][]** function.

        It should also be noted, given how the default implementation of the
        [`get_prepared_output_data`][] method works, that every candidate for
        an *output data* value -- including those produced by *auto-makers*
        -- will be transformed by applying the [`prepare_value`][] method
        to it. Furthermore, whenever the result of that transformation is
        a *void* value (by which we mean any *falsy* value *not equal* to
        `0`, for example: [`None`][], `""`, `[]` or `{}` -- but _**not**_
        [`False`][], `0`, `0.0`, etc.), it will *not* be included in the
        *output data* dict (instead, the corresponding value from the
        [`defaults`][] mapping will be included, if available).

        The default implementation of this method returns an empty mapping.

        !!! info "Related interfaces"

            For every instance, the mapping assigned to the instance's
            **[`auto_makers`][]** attribute (supposed to specify all
            *auto-makers* related to the instance) is based on this
            method's result, first converted to a [`dict`][], updated
            with all items from the **`auto_makers`** argument to the
            [constructor][StructuredLogsFormatter] (if given), and
            [deep-copied][copy.deepcopy]; then -- adjusted by resolving
            any values that are *dotted paths* (*importable dotted
            names*) to actual *auto-maker* callables.

            Finally, the **`StructuredLogsFormatter`** constructor
            automatically registers each of the *auto-makers* by calling
            the **[`register_log_record_attr_auto_maker`][]** function
            with the `rec_attr` argument set to the *auto-maker*'s
            *output data* key prefixed with the value of the formatter
            instance's **[`auto_made_record_attr_prefix`][]** attribute
            (see the *Related interfaces* note in the description of the
            **[`make_base_record_attr_to_output_key`][]** method...).

        ??? note "Side remark"

            Admittedly, the mechanism of *auto-makers* goes beyond the
            typical formatter responsibilities. However, the convenience
            of configuring your *auto-makers* as part of the formatter
            setup (perhaps, just in a configuration file, without having
            to write any boilerplate code) seems worth such an unorthodox
            design.
        """
        return {}

    def make_base_record_attr_to_output_key(self) -> Mapping[str, str | None]:
        """
        A hook method: extend it in a subclass to modify the mapping of
        [log record attribute names](https://docs.python.org/3/library/logging.html#logrecord-attributes)
        to ultimate *output data* keys.

        Automatically invoked on the formatter initialization. Each key
        in the resultant mapping needs to be the name of a (perhaps just
        hypothetic) log record attribute, and each value in that mapping
        needs to be either the corresponding *output data* key or [`None`][].
        In the latter case -- given how the default implementation of the
        [`get_prepared_output_data`][] method works -- the attribute will
        always be omitted whenever *output data* is generated (note that
        this does *not* apply to log record attributes *not included* in
        the mapping; they will be treated as if they were *included* --
        each mapped to an *output data* key identical to the attribute's
        own name).

        The default implementation of this method returns a mapping that
        contains all items from [`STANDARD_RECORD_ATTR_TO_OUTPUT_KEY`][].
        In many cases this will be quite sufficient.

        !!! info "Related interfaces"

            For every instance, the mapping assigned to the instance's
            **[`record_attr_to_output_key`][]** attribute (supposed to
            specify the ultimate mapping of names of log record object
            attributes to actual *output data* keys) is based on this
            method's result, first converted to a [`dict`][] (and also
            [deep-copied][copy.deepcopy], even though it is not very
            important in this case), then updated with keys derived from
            all the keys the instance's **[`auto_makers`][]** mapping
            contains -- each modified by *prefixing* it with the value of
            the **[`auto_made_record_attr_prefix`][]** attribute, and each
            mapped to the same key, but *without* that prefix. The prefix
            itself is an auto-generated string, guaranteed to be *unique*
            (different for each instance of **`StructuredLogsFormatter`**)
            within a Python interpreter run; it always starts with the
            **[`StructuredLogsFormatter.COMMON_AUTO_PREFIX`][]**'s value.

            ??? note "Details"

                The effect is that -- narrowing the discussion just to
                *auto-maker*-provided attributes of log records -- the
                respective *output data* items will always be obtained
                by picking only those log record attributes whose names
                are prefixed with the particular formatter instance's
                **[`auto_made_record_attr_prefix`][]** -- using those
                names *with that prefix removed* as the corresponding
                *output data* keys.

                On the other hand, the formatter will *ignore* any record
                attribute names prefixed with other formatter instances'
                **`auto_made_record_attr_prefix`**, as if those attributes
                did not exist.

            Thanks to all that, multiple **`StructuredLogsFormatter`**
            instances can be used simultaneously -- and each will work
            independently of any others, handling only its own *auto-made*
            data.
        """
        return dict(STANDARD_RECORD_ATTR_TO_OUTPUT_KEY)

    # *Note*: the `type: ignore[...]` comment below prevents *mypy* from
    # rejecting `Final` nested in `ClassVar` (which is OK in Python 3.13
    # and newer; and we use `from __future__ import annotations` anyway,
    # so at runtime we are safe regardless of Python version).
    COMMON_AUTO_PREFIX: ClassVar[Final[str]] = '_auto-made-for#'   # type: ignore[valid-type]
    """
    An arbitrary marker that every [`auto_made_record_attr_prefix`][]
    string starts with.
    """

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

        !!! note

            The [`logging.Formatter`][]-specific attributes related to
            timestamp formatting (`converter`, `default_time_format` and
            `default_msec_format`) are _**ignored**_.

        ??? tip "Subclass implementation tip"

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
                        "utc_offset_to_custom_suffix"
                    ],

                    # ...and extend it with this-class-specific stuff:
                    **{
                        # If the suffix were to be `-05:00`,
                        # we want it to be ` EST` instead.
                        UTC_OFFSET_FOR_EST: " EST",
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

    # *Note*: the `type: ignore[...]` comment below prevents *mypy* from
    # rejecting `Final` nested in `ClassVar` (which is OK in Python 3.13
    # and newer; and we use `from __future__ import annotations` anyway,
    # so at runtime we are safe regardless of Python version).
    FORMAT_TIMESTAMP_DEFAULT_KWARGS: ClassVar[Final[   # type: ignore[valid-type]
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

    def get_prepared_output_data(self, record: logging.LogRecord) -> dict[str, OutputValue]:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how an *output data* dict is obtained from a log record object
        (which, at least typically, is a [`logging.LogRecord`][] instance).

        ??? warning "Subclass behavior restriction"

            This method should *not* mutate the given log record or any
            data it carries (regardless of the level of nesting, if any
            nested data is present). If some data needs to be changed,
            completely *new* object(s) should be created. Doing otherwise
            will result in undefined behavior.

            Moreover, each *output data* dict returned by this method
            should be a *newly created* [`dict`][] (*never* the original
            log record's `__dict__` itself), so that during later stages
            of processing it will be safe to add, remove or replace any
            *top-level* items in that dict.

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
          data* items are created from them (for certain low-level details,
          see the *Related interfaces* notes in the descriptions of the
          [`make_base_auto_makers`][] and
          [`make_base_record_attr_to_output_key`][] methods...);

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
          `0`, `0.0`, etc.), then it is *excluded* (*even* if it should
          be included according to any other rule described above); note
          that *nested* values, even if *void*, are *never* subject to
          such an *exclusion* (at least if the default implementations
          of `prepare_value` and `prepare_submapping_key` are used);

        * potential *item collisions* (which might occur, for example,
          when some **key** is present *both* in the `ExtendedMessage`'s
          [`data`][ExtendedMessage.data] mapping *and* among other data
          obtained from the log record's content, and the **value** to be
          assigned to that key varies depending on which of those two
          sources of information is checked) -- are avoided by suffixing
          problematic keys with one or more underscore character(s), as
          needed to prevent key duplication; such cases are expected to
          be rare;

            ??? info "Edge case"

                The said key truncation occurs *before* the said key
                deduplication -- so it is possible, although very rare
                in practice, that appending underscore(s) to certain keys
                (as described above) will result in some keys ending up
                a little longer than 200 characters.

        * finally, every **key** present in the formatter's [`defaults`][]
          mapping which is still missing from the *output data* dict is
          being *included* in it -- with the **value** it has in `defaults`.

            ??? note "Reminder"

                All values in the **[`defaults`][]** mapping are already
                in a **[`prepare_value`][]**-made form, and there are no
                *void* values among them (see the *Related interfaces*
                note in the description of the **[`make_base_defaults`][]**
                method).
        """
        output_data: dict[str, OutputValue] = {}
        handle_output_item = functools.partial(
            self._handle_output_item,
            self._DESIRED_MAX_KEY_LENGTH,
            self.prepare_value,
            output_data,
        )

        xm_instance = getattr(record, 'msg', None)
        if isinstance(xm_instance, ExtendedMessage):
            self._extract_output_from_xm(record, xm_instance, handle_output_item)
        else:
            xm_instance = None

        self._extract_output_from_record(record, xm_instance, handle_output_item)

        for key, value_prepared in self.defaults.items():
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
        prepare_nonfinite_float: Callable[[float], OutputValue] | None = str,
        pass_thru_types: tuple[type, ...] = (str, int, float, bool, type(None)),
        exclude_from_seq_types: tuple[type, ...] = (str, bytes, bytearray),
        is_dataclass: Callable[[object], bool] = dataclasses.is_dataclass,
        dataclass_as_dict: Callable[[Any], dict[str, object]] = dataclasses.asdict,
        last_resort: Callable[[object], str] = repr,
        **kwargs: Any,
    ) -> OutputValue:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        how every *value* in an *output data* dict is prepared before the
        actual data serialization.

        ??? warning "Mutability restriction"

            If you ever customize the behavior of this method (whether
            by extending/overriding it in a subclass, or perhaps just
            by providing it with some non-default values of keyword
            arguments), you need to ensure that it does *not* mutate its
            argument or anything inside it (regardless of the level of
            nesting, if any nested data is present). If some data needs
            to be changed, a completely *new* value should be created
            (to be returned as the prepared value), *without* mutating
            existing object(s). Doing otherwise will result in undefined
            behavior.

        The default implementation of this method should be sufficient
        in most cases. It converts any *value* (even such one that is
        deeply nested inside sequences/mappings -- thanks to recursive
        calls, always passing all keyword arguments from the parent
        call...) to a form that can be serialized with [`json.dumps`][]
        (and which is -- hopefully -- short yet still readable, especially
        regarding instances of such types as: [*exceptions*][BaseException],
        [*dataclasses*][], typical [*named tuples*][collections.namedtuple],
        [`enum.Enum`][], [`uuid.UUID`][] as well as the essential types
        from the [`datetime`][] and [`ipaddress`][] modules). Every value
        being a mapping is converted to a [`dict`][] -- and each *key*
        contained in that mapping is transformed by applying to it the
        [`prepare_submapping_key`][] method. On the other hand, a value
        of a sequence type, if that type is *not* included in the tuple
        received via the **`exclude_from_seq_types`** parameter, is (at
        least typically) converted to a [`list`][]...

        ??? tip "Subclass implementation tip"

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
                    base_is_dataclass = _BASE_KWARGS["is_dataclass"]
                    return base_is_dataclass(obj) or attrs.has(type(obj))

                @staticmethod
                def default_dataclass_as_dict(obj):
                    base_is_dataclass = _BASE_KWARGS["is_dataclass"]
                    base_dataclass_as_dict = _BASE_KWARGS["dataclass_as_dict"]
                    return (base_dataclass_as_dict(obj) if base_is_dataclass(obj)
                            else attrs.asdict(obj))

                def prepare_value(
                    self,
                    value,
                    *,
                    exclude_from_seq_types = (
                        *_BASE_KWARGS["exclude_from_seq_types"],
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

        if (prepare_nonfinite_float is not None
              and isinstance(value, float)
              and not math.isfinite(value)):
            # Let us be, by default, compliant with JSON specification
            # (which does not include NaN/Infinity/-Infinity numbers).
            return prepare_nonfinite_float(value)

        if isinstance(value, pass_thru_types):
            return value

        kwargs.update(
            to_str_types=to_str_types,
            prepare_nonfinite_float=prepare_nonfinite_float,
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

    # *Note*: the `type: ignore[...]` comment below prevents *mypy* from
    # rejecting `Final` nested in `ClassVar` (which is OK in Python 3.13
    # and newer; and we use `from __future__ import annotations` anyway,
    # so at runtime we are safe regardless of Python version).
    PREPARE_VALUE_DEFAULT_KWARGS: ClassVar[Final[   # type: ignore[valid-type]
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

        The default implementation of this method should be sufficient
        in most cases. It coerces the given key to a string (by applying
        [`str`][] to it) and truncates the result to a maximum length of
        200 characters (if longer).

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

    def serialize_prepared_output_data(self, output_data: dict[str, OutputValue]) -> str:
        """
        A hook method: extend/override it in a subclass to modify/redefine
        the *output data serialization* procedure.

        ??? warning "Subclass behavior restriction"

            While it is OK to add, remove or replace *top-level* items
            in the given *output data* dict, this method should *never*
            mutate any object inside it (regardless of the level of
            nesting). If some data needs to be changed, completely
            *new* data object(s) should be created as a replacement
            for the original one(s). Doing otherwise will result in
            undefined behavior.

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

    # * Initialization-related:

    _auto_made_record_attr_prefix_creation_lock: Final[threading.Lock] = threading.Lock()
    _auto_made_record_attr_prefix_creation_count: Final[Iterator[int]] = itertools.count(start=1)

    def _extract_meaningful_arguments(
        self,
        raw_positional_args: Sequence[Any],
        /,

        # (Compare to the signature of `logging.Formatter.__init__()`...)
        fmt: Mapping[str, Any] | KwargsMappingAsLiteralEvaluableString | None = None,
        datefmt: None = None,
        style: Literal['%'] = '%',
        validate: Literal[True] = True,

        *excessive_positional_args: object,
        **meaningful_arguments: Any,
    ) -> dict[str, Any]:
        if excessive_positional_args:
            raise TypeError(
                f'{type(self).__init__.__qualname__}() '
                f'got excessive positional argument(s): '
                f'{", ".join(map(ascii, excessive_positional_args))})'
            )
        if fmt is not None:
            if not raw_positional_args:
                raise TypeError(
                    f'for {type(self).__init__.__qualname__}(), '
                    f'argument `fmt` is not customizable'
                )
            first_arg = raw_positional_args[0]
            assert fmt is first_arg
            if isinstance(first_arg, str):
                try:
                    first_arg = ast.literal_eval(first_arg)
                except Exception as exc:
                    raise ValueError(
                        f'an error occurred when trying to evaluate (as '
                        f'a Python expression) the string ({first_arg!a}) '
                        f'passed as the first positional argument to '
                        f'{type(self).__init__.__qualname__}() '
                        f'({type(exc).__qualname__}: {exc})'
                    ) from exc
            if not isinstance(first_arg, Mapping):
                raise TypeError(
                    f'for {type(self).__init__.__qualname__}(), the first '
                    f'positional argument, if specified and not None, is '
                    f'expected to be a mapping (or an `ast.literal_eval()`'
                    f'-evaluable string representing a mapping), as an '
                    f'alternative means of providing keyword arguments '
                    f'(in contexts when passing real keyword arguments '
                    f'is not possible); got: {first_arg!a} (not a mapping)'
                )
            if meaningful_arguments:
                listing = ', '.join(map(ascii, meaningful_arguments))
                raise TypeError(
                    f'for {type(self).__init__.__qualname__}(), when '
                    f'you pass a mapping (or an `ast.literal_eval()`-'
                    f'evaluable string representing a mapping) as the '
                    f'first positional argument, as an alternative '
                    f'means of providing keyword arguments, you should '
                    f'not pass real keyword arguments (whereas you did '
                    f'pass some: {listing})'
                )
            meaningful_arguments = dict(first_arg)
        if datefmt is not None:
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `datefmt` is not customizable'
            )
        if style != '%':
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `style` is not customizable'
            )
        if validate is not True:  # noqa
            raise TypeError(
                f'for {type(self).__init__.__qualname__}(), '
                f'argument `validate` is not customizable'
            )
        return meaningful_arguments

    def _as_ready_raw_defaults(
        self,
        unready_raw_defaults: Mapping[str, object],
    ) -> dict[str, object]:
        raw_defaults = self._sorted_dict_deepcopy(unready_raw_defaults)
        self._validate_mapping_keys_as_output_keys(raw_defaults)
        return raw_defaults

    def _as_ready_auto_makers(
        self,
        unready_auto_makers: Mapping[str, ValueProvider[object] | DottedPath],
    ) -> dict[str, ValueProvider[object]]:
        auto_makers = self._sorted_dict_deepcopy(unready_auto_makers)
        self._validate_mapping_keys_as_output_keys(auto_makers)
        return self._resolve_auto_makers(auto_makers)

    def _as_ready_base_attr_to_key(
        self,
        unready_base_attr_to_key: Mapping[str, str | None],
    ) -> dict[str, str | None]:
        base_attr_to_key = self._sorted_dict_deepcopy(unready_base_attr_to_key)
        self._validate_base_attr_to_key(base_attr_to_key)
        return base_attr_to_key

    def _sorted_dict_deepcopy(
        self,
        mapping: Mapping[HashableT, T],
    ) -> dict[HashableT, T]:
        return deepcopy({
            key: mapping[key]
            for key in sorted(mapping.keys(), key=str)
        })

    def _validate_mapping_keys_as_output_keys(
        self,
        mapping: Mapping[str, object],
    ) -> None:
        for key in mapping.keys():
            self._verify_output_key_is_valid(key)

    def _validate_base_attr_to_key(
        self,
        base_attr_to_key: Mapping[str, str | None],
    ) -> None:
        for key in base_attr_to_key.values():  # [sic!]
            if key is not None:
                self._verify_output_key_is_valid(key)

    def _verify_output_key_is_valid(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError(f'{key=!a} is not a str')
        if len(key) > self._DESIRED_MAX_KEY_LENGTH:
            raise ValueError(
                f'{key=!a} is longer than '
                f'{self._DESIRED_MAX_KEY_LENGTH} characters'
            )

    def _resolve_auto_makers(
        self,
        auto_makers: Mapping[str, ValueProvider[object] | DottedPath]
    ) -> dict[str, ValueProvider[object]]:
        return {
            key: self._get_resolved_callable(
                auto_maker,
                descr=f'{key!a} auto-maker',
            )
            for key, auto_maker in auto_makers.items()
        }

    def _resolve_serializer(
        self,
        given_serializer: OutputSerializer | DottedPath,
    ) -> OutputSerializer:
        return self._get_resolved_callable(
            given_serializer,
            descr='serializer'
        )

    def _resolve_conf_corrector(
        self,
        given_conf_corrector: ConfCorrector | DottedPath,
    ) -> ConfCorrector:
        return self._get_resolved_callable(
            given_conf_corrector,
            descr='configuration corrector'
        )

    def _get_resolved_callable(
        self,
        obj: CallableT | DottedPath,
        descr: str,
    ) -> CallableT:
        resolved: CallableT = (
            _resolve_dotted_path(obj) if isinstance(obj, str) else obj
        )
        if not callable(resolved):
            raise TypeError(
                f'the {descr} does not appear to be '
                f'a callable object: {resolved!a}'
            )
        return resolved

    def _prepare_and_filter_defaults(
        self,
        raw_defaults: dict[str, object],
    ) -> dict[str, OutputValue]:
        prepared_unfiltered = sorted(
            (key, self.prepare_value(value))
            for key, value in raw_defaults.items()
        )
        return {
            key: value_prepared
            for key, value_prepared in prepared_unfiltered
            # If `value_prepared` is *non-numeric* and, at the same time,
            # is *falsy* (i.e., is an object which is considered *false*
            # in a boolean context) => we skip it as a *void* value (that
            # is, a value assumed to carry *no sufficiently significant*
            # information).
            if value_prepared or value_prepared == 0
        }

    def _make_auto_made_record_attr_prefix(self) -> str:
        with self._auto_made_record_attr_prefix_creation_lock:
            unique_num = next(self._auto_made_record_attr_prefix_creation_count)
            return f'{self.COMMON_AUTO_PREFIX}{unique_num:02}:'

    def _make_record_attr_to_output_key(
        self,
        base_attr_to_key: Mapping[str, str | None],
    ) -> dict[str, str | None]:
        return dict(
            # Note that here any `rec_attr` duplication
            # (hardly possible!) would cause TypeError.
            **base_attr_to_key,
            **{
                rec_attr: key
                for rec_attr, key in zip(
                    self._get_record_attr_to_auto_maker().keys(),
                    self.auto_makers.keys(),
                )
            },
        )

    def _get_record_attr_to_auto_maker(self) -> dict[str, ValueProvider[object]]:
        return {
            self.auto_made_record_attr_prefix + key: auto_maker
            for key, auto_maker in self.auto_makers.items()
        }

    # * Formatter-activity-related:

    def _get_record_args_repr(self, args: object) -> str:
        no_seq = (str, bytes, bytearray)
        return (
            ', '.join(map(ascii, args))
            if isinstance(args, Sequence) and not isinstance(args, no_seq)
            else ascii(args)  # In particular, it may be a dict.
        )

    def _extract_output_from_xm(
        self,
        record: logging.LogRecord,
        xm_instance: ExtendedMessage,
        handle_output_item: Callable[[object, object], bool],
    ) -> None:
        attr_to_key = self.record_attr_to_output_key

        # Extract from the given `ExtendedMessage` instance and handle...

        # * ...its components conveying the information equivalent
        #   to the standard `msg` and `args` log record attributes:
        msg_key = attr_to_key.get('msg', 'msg')
        if msg_key is not None:
            msg_value = xm_instance.get_record_msg_and_args_equivalent_info(
                pattern_result_key='pattern',
                args_result_key=attr_to_key.get('args', 'args'),
            )
            handle_output_item(msg_key, msg_value)

        # * ...its `exc_info` attribute (if worth including;
        #   and, optionally, an *exception text* derived from
        #   that `exc_info` by using `self.formatException()`):
        ei_key = attr_to_key.get('exc_info', 'exc_info')
        etx_key = attr_to_key.get('exc_text', 'exc_text')
        if ((ei_key is not None or etx_key is not None)
            and (xm_ei := xm_instance.exc_info)
        ):
            if isinstance(xm_ei, BaseException):
                xm_ei = (type(xm_ei), xm_ei, xm_ei.__traceback__)
            if self._is_xm_exc_info_significant(xm_ei, record.exc_info):
                if xm_ei == (None, None, None):
                    xm_ei = etx_key = None
                if ei_key is not None:
                    ei_added = handle_output_item(ei_key, xm_ei)
                    if not ei_added:
                        etx_key = None
                if etx_key is not None and isinstance(xm_ei, tuple):
                    etx_value = self.formatException(xm_ei)  # noqa
                    handle_output_item(etx_key, etx_value)

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
            # `ExtendedMessage` instance's `exc_info` attribute -- to be
            # considered *significant* -- needs to be an *exc info* tuple
            # (or an exception which we converted to such a tuple) that
            # is *different* from `record.exc_info`. So, in particular, a
            # flag value (such as True) is considered *insignificant* in
            # such a case.
            xm_ei is not rec_ei  # (<- Fast check first)
            and isinstance(xm_ei, tuple)
            and xm_ei != rec_ei
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
        handle_output_item: Callable[[object, object], bool],
    ) -> None:
        common_auto_prefix = self.COMMON_AUTO_PREFIX
        attr_to_key = self.record_attr_to_output_key
        exc_info_3none = (record.exc_info == (None, None, None))

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
                if (exc_info_3none and rec_attr in ('exc_info', 'exc_text')
                    or (rec_attr == 'exc_text' and not record.exc_info)  # [sic!]
                ):
                    value = None
                key = attr_to_key.get(rec_attr, rec_attr)

            if key is not None:
                handle_output_item(key, value)

    @staticmethod
    def _handle_output_item(
        # Shared (output-data-dict-wide) arguments:
        desired_max_key_length: int,
        prepare_value: Callable[[object], OutputValue],
        output_data: dict[str, OutputValue],

        # Individual (per-output-data-item) arguments:
        key: object,
        value: object,
    ) -> bool:

        if not isinstance(key, str):
            return False

        if len(key) > desired_max_key_length:
            # Truncate the key (it's a rare case, hopefully).
            key = key[:desired_max_key_length]

        value_prepared = prepare_value(value)
        if (not value_prepared) and value_prepared != 0:
            # If `value_prepared` is *non-numeric* and, at the same time,
            # is *falsy* (i.e., is an object which is considered *false*
            # in a boolean context) => we skip it as a *void* value (that
            # is, a value assumed to carry *no sufficiently significant*
            # information).
            return False

        # Finally, set the prepared item.
        actually_set_value = output_data.setdefault(key, value_prepared)
        if actually_set_value is value_prepared:
            return True

        # Wait! Key deduplication may be needed (it's a rare case, hopefully).
        while actually_set_value != value_prepared:
            # Note that, in this case, the key length may
            # become longer than `desired_max_key_length`.
            key = f'{key}_'
            actually_set_value = output_data.setdefault(key, value_prepared)

            # (Comparing also identities -- for cases of such
            # an object that never compares equal to itself.)
            if actually_set_value is value_prepared:
                break

        return True


class ExtendedMessage:

    """
    A tool thanks to which you can:

    * conveniently emit structured log entries, especially if
      [`StructuredLogsFormatter`][] is in use;

    * use the modern `{}`-based style of log message formatting, or --
      if you just need to log pure data -- simply omit passing the text
      message pattern (regardless of what formatter is in use);

    * defer the creation of some values (if it is costly) until the log
      entry is actually about to be emitted (regardless of what formatter
      is in use).

    There is a convenience alias of this class: **[`xm`][]**. As being
    very short, it is simply much more ergonomic than the actual class
    name -- given that this tool is intended to be used every time you
    log something...

    A few usage examples:

    ```python
    import datetime as dt, hashlib, ipaddress, logging, sys
    from certlib.log import xm

    logging.info(xm("Hello {}!", sys.platform))
    logging.info(xm("Maxsize is {maxsize:x}", maxsize=sys.maxsize))
    logging.warning(xm(
        connection_count=42,
        client_ip=ipaddress.IPv4Address("192.168.0.121"),
        local_time=dt.datetime.now(),
        # Value creation deferred until log entry is about to be emitted:
        payload_hash=lambda: hashlib.sha256(b'...payload...').hexdigest(),
    ))
    some_data_dict = globals()
    logging.debug(xm(some_data_dict))
    ```

    !!! info "See also"

        For more usage examples, see the **[Tool:
        `xm`](guide.md#certlib.log--tool-xm)**
        section of the *User's Guide*.

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

        ??? warning "Interface restriction"

            It is *not* allowed to pass a [`string.templatelib.Template`][]
            instance (typically, created by evaluating a
            *[t-string](https://docs.python.org/3/library/stdtypes.html#stdtypes-tstrings)*)
            as the *first positional argument*. This possibility is
            reserved for future versions of `certlib.log`, in which
            dedicated support for such objects is likely to be implemented.

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

        ??? warning "Interface restriction"

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

    * _**extra keyword arguments**_ (if any):
      all of them become *extra data* items -- to be included in the
      *output data* dict if [`StructuredLogsFormatter`][] is used, or
      to be appended to the text message (in a form resembling the
      keyword arguments syntax) if some other formatter is in use. A
      [`dict`][] of those *extra data* items is always stored as the
      [`data`][] attribute. Moreover, any items whose names match a
      *named replacement field* in the text message pattern (see above)
      will take part in formatting the actual text message (regardless
      of what formatter is in use).

    **Alternatively**, a mapping (e.g., a [`dict`][]) of *extra data*
    items can be passed to the [constructor][ExtendedMessage] as the
    *first positional argument*. The effect is the same as if each of
    its items was passed as an *extra keyword argument*, without passing
    any positional arguments. A shallow copy of the mapping, converted
    to a `dict`, is assigned to the [`data`][] attribute.

    ??? warning "Interface restriction"

        If a mapping is passed as the *first positional argument*,
        then passing any other arguments except **`exc_info`**,
        **`stack_info`** and **`stacklevel`** causes [`TypeError`][].

        When it comes to the **`exc_info`**, **`stack_info`** and
        **`stacklevel`** arguments, they should *not* be included in
        that mapping (doing so will result in undefined behavior). Each
        of them, if to be specified, should *only* be specified as a
        real keyword argument.

    Whenever a formatter (of any type) processes a log record with its
    `msg` attribute (obtained as the first argument to the logger method
    call) being an `ExtendedMessage` (`xm`) instance, that instance's
    [`get_message_value`][] method is always invoked -- either *directly*
    (by the machinery of [`StructuredLogsFormatter`][]) or *indirectly*
    (via [`__str__`][], by the standard machinery that other formatter
    types use).

    ??? info "Edge case"

        If a text message pattern (*not* a mapping, see above...) was
        given as the *first positional argument* to the
        **[`ExtendedMessage`][]** (**[`xm`][]**) constructor _**and**_
        neither *extra positional arguments* nor *keyword arguments*
        other than **`exc_info`**, **`stack_info`** and **`stacklevel`**
        were given -- that is, if the resultant **`ExtendedMessage`**
        instance's **[`args`][]** and **[`data`][]** containers are both
        *empty* -- then the **[`get_message_value`][]** method will *not*
        attempt to format the text message with [`str.format`][]; instead,
        it will treat the pattern as an *already formatted* text message.

        ```python
        logger.info(xm('answer: {}', 42))  # message will be 'answer: 42'
        logger.info(xm('answer: {}'))      # message will be 'answer: {}'  [sic!]
        ```

        This mimics how the standard [`logging`][] machinery handles
        a log record whose `args` attribute is empty (when only a
        text message pattern is specified, without any values that
        could be interpolated).

    ??? warning "Interface restriction"

        When passing an **`ExtendedMessage`** to a [logger method
        call](https://docs.python.org/3/library/logging.html#logging.Logger.debug),
        you should *not* pass any other *positional* arguments to that
        call (doing so will result in undefined behavior).

        ```python
        # WRONG (!!!):
        logger.info(xm('{}, {} and {}'), 'Athos', 'Porthos', 'Aramis')
        ```

        ```python
        # OK:
        logger.info(xm('{}, {} and {}', 'Athos', 'Porthos', 'Aramis'))
        ```

    !!! warning "Dangers of mutability"

        Although replacing objects assigned to the **`ExtendedMessage`**'s
        instance attributes or mutating their contents (where applicable)
        is not strictly forbidden, caution is strongly advised. Generally,
        you are on your own when you do that.

        In particular, nothing will stop you from inadvertently making
        those attributes invalid or out-of-sync.

        Also, generally, those attributes are *not* protected against
        concurrent access -- and in this context you need to take into
        account not only the obvious fact that the logging machinery needs
        to reach for their values (at various points during its operation),
        but also that an important part of the *deferred value creation*
        mechanism (described below) is to *replace/mutate* some of them.

        Moreover:

        * *after* the **`message`** formatting is triggered, further
          changes to the relevant attributes may not be reflected in
          the text message;
        * placing any callables matching
          **[`recognized_deferred_value_creator_types`][]** in the
          relevant collections *after* the aforementioned *deferred
          value creation* mechanism is triggered may leave those
          callables *never* called and replaced.

        A separate concern is the risk of inadvertently mutating some
        shared data (which, for example, might have been passed to the
        `xm(...)` call).

        To put it briefly, _**you have been warned**_.

    As noted earlier, the `ExtendedMessage` (`xm`) tool
    offers also a mechanism of *deferred value creation*
    in [`args`][] and/or [`data`][]: if you pass a *function*
    or *method* object (precisely: an instance of any type included
    in [`ExtendedMessage.recognized_deferred_value_creator_types`][])
    as any *extra positional or keyword argument* to the [constructor][ExtendedMessage]
    (except for **`exc_info`**, **`stack_info`** and **`stacklevel`**)
    or as a value in the *extra data* mapping -- then that function
    or method will be *called* just after the log record owning the
    `ExtendedMessage` instance arrives at a formatter (no matter what
    the formatter type will be). The result of that call will then
    *replace* the called function/method object in (respectively)
    [`args`][] or [`data`][]. Every such function/method is expected
    to take no arguments (so, if it is a method, it should already be
    bound to an instance or class).

    ??? note "Details"

        For a particular instance of **`ExtendedMessage`**, all such
        calls-and-replacements are triggered when *any* of the following
        methods is invoked for the first time: **[`get_message_value`][]**,
        **[`get_record_msg_and_args_equivalent_info`][]**, **[`__str__`][]** or
        **[`iter_str_parts`][]** (with the proviso that the last one returns
        an [iterator](https://docs.python.org/3/glossary.html#term-iterator)
        which, to achieve the effect in question, needs to be iterated
        over, at least partially). Each of those calls-and-replacements
        is made at most *once* per **`ExtendedMessage`** instance (see the
        **[`_ensure_deferred_values_created`][]** method's
        description...).

    Thanks to this mechanism, if the creation of some value is
    expected to be costly, you can wrap it in a function/method (in
    particular, in an argumentless `lambda`) to defer that costly
    operation until the value becomes actually needed (which may
    never happen if -- based on the [actually configured filtering
    rules](https://docs.python.org/3/howto/logging.html#logging-flow)
    -- the log entry is prevented from being emitted).

    ??? warning "Multithreading-related restriction"

        Those *value creating* functions/methods should *never* acquire
        locks that might also be acquired by any code making use of the
        [`logging`][] stuff (because, in particular, that could result in
        a [*deadlock*](https://docs.python.org/3/glossary.html#term-deadlock)).
    """

    __slots__ = (
        'pattern',
        'args',
        'data',
        'exc_info',
        'stack_info',
        'stacklevel',

        '_deferred_values_already_created',
        '_deferred_value_creation_lock',
        '_cached_message',
    )

    #
    # Public stuff

    pattern: object
    args: tuple[object | ValueProvider[object], ...]
    data: dict[str, object | ValueProvider[object]]
    exc_info: Any
    stack_info: bool
    stacklevel: int

    recognized_deferred_value_creator_types: ClassVar[
        tuple[type[ValueProvider[object]], ...]
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
    your subclass to redefine the runtime types of callable values in
    [`args`][] and [`data`][] recognized by the *deferred value creation*
    mechanism (see the part of the [`ExtendedMessage`][] constructor's
    description in which that mechanism is discussed).
    """

    @overload
    def __init__(
        self,
        pattern: str = '',
        /,
        *args: object | ValueProvider[object],

        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,

        **data: object | ValueProvider[object],
    ):
        ...

    @overload
    def __init__(
        self,
        data: Mapping[str, object | ValueProvider[object]],
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
        *args: object | ValueProvider[object],

        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,

        **data: object | ValueProvider[object],
    ):
        ...

    def __init__(
        self,
        first_arg: object | Mapping[str, object | ValueProvider[object]] = '',
        /,
        *args: object | ValueProvider[object],
        exc_info: Any = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        **data: object | ValueProvider[object],
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

        self._deferred_values_already_created: bool = False
        self._deferred_value_creation_lock: threading.Lock | None = None
        self._cached_message: str | None = None

    def get_message_value(self) -> str:
        """
        Automatically invoked by the [`StructuredLogsFormatter`][]'s
        machinery to obtain a string to be assigned to the log record's
        [`message` attribute](https://docs.python.org/3/library/logging.html#logrecord-attributes).

        The default implementation of this method should be sufficient
        in most cases. It converts [`pattern`][] to a string, and then
        -- *only* if [`args`][] and/or [`data`][] contain any items --
        invokes that string's [`format`][str.format] method, passing
        to it all `args` items as *positional arguments* and all `data`
        items as *keyword arguments*. A string being the result of the
        above operation(s) is cached (for any further invocations of
        this method on the same instance) and returned.

        ??? warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_deferred_values_created`][]**
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
        self._ensure_deferred_values_created()

        # (Compare to the source code of `logging.LogRecord.getMessage()`...)
        message = self._cached_message
        if message is None:
            message = str(self.pattern)
            if self.args or self.data:
                message = message.format(*self.args, **self.data)

            # (Such assignments are assumed to be *atomic* operations.)
            self._cached_message = message

        return message

    def get_record_msg_and_args_equivalent_info(
        self,
        *,
        pattern_result_key: str | None,
        args_result_key: str | None,
    ) -> Mapping[str, object]:
        """
        Automatically invoked by the [`StructuredLogsFormatter`][]'s
        machinery to get a value to be included in the *output data*
        dict under the key corresponding to the log record's `msg`
        attribute. The returned value is supposed to be a mapping
        that conveys relevant information from the `ExtendedMessage`
        instance -- to the extent that corresponds to the information
        typically conveyed by the `msg` and `args` attributes of log
        records when `ExtendedMessage` is not used.

        The default implementation should be sufficient in most cases. It
        returns a mapping containing zero, one or two items. Specifically
        -- *each* of the following *if* the key is not [`None`][] and the
        value is not *falsy*:

        * the given **`pattern_result_key`** -- mapped to the value of the
          [`pattern`][] attribute,

        * the given **`args_result_key`** --  mapped to the value of the
          [`args`][] attribute.

        ??? warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_deferred_values_created`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_deferred_values_created()

        return {
            key: val
            for key, val in (
                (pattern_result_key, self.pattern),
                (args_result_key, self.args),
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

        The default implementation of this method should be sufficient
        in most cases. It invokes the [`iter_str_parts`][] method
        (which, in particular, invokes [`get_message_value`][]...)
        and concatenates any yielded strings (if more than one) using
        `" | "` as the separator.

        ??? warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_deferred_values_created`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_deferred_values_created()

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

        The default implementation of this method yields zero, one
        or two strings. Specifically -- *each* of the following *if
        not empty*:

        * the result of an invocation of the [`get_message_value`][]
          method,

        * a representation of the [`data`][] mapping's items (formatted
          in a way that resembles the syntax for specifying keyword
          arguments, but without the parentheses).

        ??? warning "Subclass behavior requirement"

            This method should *always* invoke the
            **[`_ensure_deferred_values_created`][]**
            method before starting the actual work (the default
            implementation already does that). Failing to do so
            will result in undefined behavior.
        """
        self._ensure_deferred_values_created()

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

    def _ensure_deferred_values_created(self) -> None:
        """
        !!! exclusion "Interface exclusion"

            This method is _**not**_ part of the API -- _**except that**_
            it is allowed to be invoked in any methods implemented by
            possible subclasses of **`ExtendedMessage`**.

        This method processes the items in [`args`][] and [`data`][] --
        by *calling* each encountered instance of any type included in
        [`ExtendedMessage.recognized_deferred_value_creator_types`][],
        and then *replacing* that instance with the result of that call.
        Each of those calls is made without arguments.

        This method can be safely invoked multiple times on the same
        instance, *even* in the case of *concurrent* invocations. The
        implementation guarantees that *none* of the calls in question
        will be made more than *once* per instance of `ExtendedMessage`.
        """
        if self._deferred_values_already_created:
            # OK, already done (fast path).
            return

        with self._deferred_value_creation_meta_lock:
            # Obtain the instance's lock in a thread-safe manner...
            lock = self._deferred_value_creation_lock
            if lock is None:
                # (We want to defer its creation until this moment, so that
                # `ExtendedMessage.__init__()` remains as fast as possible.)
                lock = self._deferred_value_creation_lock = (
                    threading.Lock()
                )

        if not lock.acquire(timeout=self._DEFERRED_VALUE_CREATION_LOCK_TIMEOUT):
            raise RuntimeError(
                f'could not acquire the lock that protects '
                f'the mechanism of deferred value creation '
            )
        try:
            if self._deferred_values_already_created:
                # OK, already done.
                return
            self._perform_deferred_value_creation()

            # (Such assignments are assumed to be *atomic* operations.)
            self._deferred_values_already_created = True
        finally:
            lock.release()

    #
    # Internals (should not be used or extended/overridden outside this module!)

    _DEFERRED_VALUE_CREATION_LOCK_TIMEOUT: Final[float] = 9.0

    _deferred_value_creation_meta_lock: Final[threading.Lock] = threading.Lock()
    _setup_of_record_hooks_still_needs_to_be_done: ClassVar[bool] = True

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
            record.exc_info = exc_info

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
                None,   # type: ignore[arg-type]
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

    def _perform_deferred_value_creation(self) -> None:
        recognized_callable_types = (
            self.recognized_deferred_value_creator_types
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


def make_constant_value_provider(value: T) -> ValueProvider[T]:
    """
    A trivial (yet sometimes useful) helper: given an arbitrary object
    (**`value`**), create an argumentless function that will always
    return that object (note that such argumentless functions can be
    used as [*auto-makers*][register_log_record_attr_auto_maker]).
    """
    return (lambda: value)


def register_log_record_attr_auto_maker(
    rec_attr: str,
    auto_maker: ValueProvider[object],
) -> None:
    """
    For the specified log record attribute name (**`rec_attr`**),
    register the given *auto-maker* callable (**`auto_maker`**).

    By calling this function you ensure that, from now on, the specified
    attribute will be *automatically* set on every *new* [log record][logging.LogRecord]
    object -- to a value returned by the specified *auto-maker*.

    The _**auto-maker**_ needs to be an argumentless function or
    any other object that can be called with no arguments (see:
    [`ValueProvider`][]). A call to it will be made *at most once*
    for each newly created log record (*only* if the logger [is
    enabled](https://docs.python.org/3/library/logging.html#logging.Logger.isEnabledFor)
    for the respective log level), in the thread in which the current
    logger method call is being executed (shortly *after* the log record
    is created by a [logger](https://docs.python.org/3/howto/logging.html#loggers),
    yet *before* any [handlers](https://docs.python.org/3/howto/logging.html#handlers),
    [filters](https://docs.python.org/3/library/logging.html#filter) and
    [formatters](https://docs.python.org/3/howto/logging.html#formatters)
    process that record). Obviously, the returned values are allowed to
    vary depending on the context (or even with each call).

    If, for the specified attribute name, some *auto-maker* is already
    registered, this function raises [`KeyError`][].

    !!! tip

        The [`get`][contextvars.ContextVar.get] method of
        a [`ContextVar`][contextvars.ContextVar] may be a
        good candidate for an *auto-maker*.

    !!! note

        Typically, you _**do not need**_ to use the
        **`register_log_record_attr_auto_maker`** function directly,
        because the machinery of the **`StructuredLogsFormatter`** class
        does this for you -- at instantiation time (see the descriptions
        of the **[`StructuredLogsFormatter`][]** constructor's
        **`auto_makers`** argument as well as the **`StructuredLogsFormatter`**'s
        **[`make_base_auto_makers`][StructuredLogsFormatter.make_base_auto_makers]**
        and **[`make_base_record_attr_to_output_key`][StructuredLogsFormatter.make_base_record_attr_to_output_key]**
        methods).

        The **`StructuredLogsFormatter`** machinery will also take care
        of avoiding record attribute name collisions.

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
    registered, this function raises [`KeyError`][].
    """
    with _auto_makers_registry_and_internal_record_hooks_maintenance_lock:
        _remove_from_auto_makers_registry(rec_attr)


#
# Static typing helpers
#


# *Not* part of the public API.
T = TypeVar('T')

# *Not* part of the public API.
HashableT = TypeVar('HashableT', bound=Hashable)

# *Not* part of the public API.
CallableT = TypeVar('CallableT', bound=Callable[..., object])

# *Not* part of the public API.
Value = TypeVar('Value', covariant=True)


class ValueProvider(Protocol[Value]):
    """
    ```python
    __call__() -> Value
    ```

    A [*protocol*][typing.Protocol] which describes any callable object
    (e.g., a function) that takes *no arguments* and returns some value
    (returned values may vary with each call). It is worth noting that,
    in particular, every *auto-maker* is supposed to be such a callable
    object.

    ??? info "Typing details"

        * In the above `__call__()` signature, the **`Value`** element
          is a [*type variable*](https://typing.python.org/en/latest/spec/generics.html#generics).

        * That variable has no [*upper
          bound*](https://typing.python.org/en/latest/spec/generics.html#type-variables-with-an-upper-bound)
          (or, in other words, its *upper bound* is [`object`][]).

        * The **`ValueProvider`** protocol is
          [*generic*](https://typing.python.org/en/latest/spec/protocol.html#generic-protocols).
          It is [*covariant*](https://typing.python.org/en/latest/spec/generics.html#variance)
          in that variable.
    """
    def __call__(self) -> Value: ...


class OutputSerializer(Protocol):
    """
    ```python
    __call__(output_data: dict[str, OutputValue], /) -> str
    ```

    A [*protocol*][typing.Protocol] which describes a callable object
    (e.g., a function) that takes an *output data* dict (supposedly,
    returned by [`StructuredLogsFormatter.get_prepared_output_data`][])
    as the sole positional argument, and returns a string representing
    that dict in *serialized* form (typically, but not necessarily, in
    JSON format).

    !!! warning "Mutability restriction"

        While it is OK to add, remove or replace *top-level* items in an
        *output data* dict, a callable used as an **[`OutputSerializer`][]**
        should *never* mutate any object inside that dict (regardless of the
        level of nesting). If some data needs to be changed, completely
        *new* data object(s) should be created as a replacement for the
        original one(s). Doing otherwise will result in undefined behavior.
    """
    def __call__(self, output_data: dict[str, OutputValue], /) -> str: ...


OutputValue: TypeAlias = Any
"""
A [*type alias*](https://typing.python.org/en/latest/spec/aliases.html#type-aliases)
which is used to annotate top-level *values* in *output data* dicts.

!!! warning "Runtime compatibility requirement"

    Typically, an *output data* dict (annotated as **`dict[str,
    OutputValue]`**) is:

    * created by **[`StructuredLogsFormatter.get_prepared_output_data`][]**
      -- with each *value* obtained by invoking **[`StructuredLogsFormatter.prepare_value`][]**
      (whose return type annotation is **[`OutputValue`][]**);

    * passed to **[`StructuredLogsFormatter.serialize_prepared_output_data`][]**
      -- and then passed by it to **[`StructuredLogsFormatter.serializer`][]**
      (which is annotated as **[`OutputSerializer`][]**).

    So every **[`serializer`][StructuredLogsFormatter.serializer]** is
    required to be capable of serializing any dict that maps strings to
    values whose types, generally referred to as **[`OutputValue`][]**,
    are decided by the (default or customized) implementation of
    **[`prepare_value`][StructuredLogsFormatter.prepare_value]**
    (and/or by customized implementations of
    **[`get_prepared_output_data`][StructuredLogsFormatter.get_prepared_output_data]** and/or
    **[`serialize_prepared_output_data`][StructuredLogsFormatter.serialize_prepared_output_data]**,
    if they change something in this regard).

    !!! note

        The [`json.dumps`][] function, which is the default
        **[`serializer`][StructuredLogsFormatter.serializer]**,
        satisfies this requirement for the default implementations
        of **[`prepare_value`][StructuredLogsFormatter.prepare_value]**,
        **[`get_prepared_output_data`][StructuredLogsFormatter.get_prepared_output_data]** and
        **[`serialize_prepared_output_data`][StructuredLogsFormatter.serialize_prepared_output_data]**.

    ??? info "Typing details"

        Accurately expressing the above requirement using static
        types would be difficult (at least without making things
        overly complicated), so that approach is not taken. Instead,
        **[`OutputValue`][]** is defined just as an alias for the
        [`Any`][] special type.
"""


DottedPath: TypeAlias = str
"""
A [*type alias*](https://typing.python.org/en/latest/spec/aliases.html#type-aliases)
which is used to annotate strings being a *dotted path* (*importable
dotted name*).
"""


KwargsMappingAsLiteralEvaluableString: TypeAlias = str
"""
A [*type alias*](https://typing.python.org/en/latest/spec/aliases.html#type-aliases)
which is used to annotate strings being an [`ast.literal_eval`][]-evaluable
representation of a mapping (dict) of keyword arguments that are compatible
with the main (first) signature of the [`StructuredLogsFormatter`][]
constructor.
"""


class ConfCorrector(Protocol):
    """
    ```python
    __call__(conf: ConfDict) -> CorrectedConfDict
    ```

    A [*protocol*][typing.Protocol] which describes a callable object
    (e.g., a function) that takes a [`ConfDict`][]-compliant dict (see
    below...) as the sole positional argument, and either raises an
    exception or returns a [`CorrectedConfDict`][]-compliant dict (see
    below...). The latter is allowed (but definitely *not* required) to
    be the same dict object as the former (modified or not).

    Objects compliant with the `ConfCorrector` protocol can be passed to
    the [`StructuredLogsFormatter`][] constructor as **`conf_corrector`**.
    """
    def __call__(self, conf: ConfDict, /) -> CorrectedConfDict: ...


class ConfDict(TypedDict):
    """
    ```python
    ConfDict = TypedDict(
        "ConfDict", {
            "defaults": dict[str, object],
            "auto_makers": dict[str, ValueProvider[object]],
            "serializer": OutputSerializer,
            "base_record_attr_to_output_key": dict[str, str | None],
            "conf_corrector_params": dict[str, Any],
        },
    )
    ```

    A [`TypedDict`][typing.TypedDict] which describes a [`dict`][] accepted
    as the sole positional argument by every [`ConfCorrector`][]-compliant
    callable object.

    !!! warning "Forward compatibility requirement"

        In future versions of the library, including *non-major* ones,
        other items may be defined in addition to the five items defined
        here. Any code that deals with a **`ConfDict`** needs to take
        this possibility into account.

    !!! info "See also"

        In the part of the **[`StructuredLogsFormatter`][]** constructor's
        description that covers the **`conf_corrector`** argument, there
        is a subpart titled *Corrector interface* -- you can find there a
        bulleted list detailing each of the **`ConfDict`** items.
    """
    defaults: dict[str, object]
    auto_makers: dict[str, ValueProvider[object]]
    serializer: OutputSerializer
    base_record_attr_to_output_key: dict[str, str | None]
    conf_corrector_params: dict[str, Any]


class CorrectedConfDict(TypedDict, total=False):
    """
    ```python
    CorrectedConfDict = TypedDict(
        "CorrectedConfDict", {
            "defaults": dict[str, object],
            "auto_makers": dict[str, ValueProvider[object] | DottedPath],
            "serializer": OutputSerializer | DottedPath,
            "base_record_attr_to_output_key": dict[str, str | None],
            "conf_corrector_params": dict[str, Any],
        },
        total=False,
    )
    ```

    A [`TypedDict`][typing.TypedDict] which describes a [`dict`][]
    *returned* by every [`ConfCorrector`][]-compliant callable object.

    It is similar to [`ConfDict`][], but wider -- i.e., more forgiving
    -- as it *also* allows for:

    * lack of some (or even all) of the keys (note the `total=False` flag
      in the definition);
    * **`"auto_makers"`** including values being *dotted path* strings
      (not yet resolved; expected to point to [`ValueProvider`][]-compliant
      targets);
    * **`"serializer"`** being a *dotted path* string (not yet resolved;
      expected to point to an [`OutputSerializer`][]-compliant target).

    !!! warning "Forward compatibility requirement"

        In future versions of the library, including *non-major*
        ones, other *optional* items may be defined in addition
        to the five items defined here. Any code that deals with
        a **`CorrectedConfDict`** needs to take this possibility
        into account.
    """
    defaults: dict[str, object]
    auto_makers: dict[str, ValueProvider[object] | DottedPath]
    serializer: OutputSerializer | DottedPath
    base_record_attr_to_output_key: dict[str, str | None]
    conf_corrector_params: dict[str, Any]


#
# Internal constants and helpers (should be used only within this module!)
#


_PY_3_11_OR_NEWER = sys.version_info[:2] >= (3, 11)


#
# Machinery of *auto-makers* + internal *log record hooks*


_auto_makers_registry_and_internal_record_hooks_maintenance_lock = threading.Lock()
_auto_makers_registry: Sequence[tuple[str, ValueProvider[object]]] = ()
_internal_record_hooks: Sequence[Callable[[logging.LogRecord], None]] = ()


def _add_to_auto_makers_registry(
    rec_attr: str,
    auto_maker: ValueProvider[object],
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
    auto_maker: ValueProvider[object]
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


#
# Unofficial extra stuff (*not* part of the public API)
#


#
# Base stuff for submodules providing reusable *auto-makers*


_AUTO_MAKERS_TOP_SUBMODULE_NAME = f'{__name__}._auto_makers'

# To be set in `_BaseAutoMakersSubmodule._ensure_top_submodule()`
_auto_makers: types.ModuleType


class _BaseAutoMakersSubmodule(abc.ABC):

    # Must be set *manually* in each *concrete* subclass:
    _leaf_name_: ClassVar[str | None] = None

    # Typically, besides *auto-makers* themselves, this
    # will be the only public method of each subclass:
    @classmethod
    def get_auto_makers(cls) -> dict[str, ValueProvider[object]]:
        """Get a dict with all *auto-makers* provided by this submodule."""
        return {
            key: obj
            for key, obj in cls._iter_public_members()
            if key != 'get_auto_makers' and callable(obj)
        }

    def __init_subclass__(cls, /, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls._leaf_name_ is not None:
            # `cls` is a *concrete* subclass
            if '_leaf_name_' not in vars(cls):
                raise TypeError(
                    f'{cls.__qualname__} needs to have its '
                    f'own unique `_leaf_name_` attribute '
                    f'(not inherited from a superclass)'
                )
            other_qualname = cls.__leaf_name_to_cls_qualname.get(cls._leaf_name_)
            if other_qualname is not None:
                raise ValueError(
                    f'`{cls.__qualname__}._leaf_name_` should be unique, '
                    f'while it duplicates `{other_qualname}._leaf_name_` '
                    f'- both are equal to {cls._leaf_name_!a}'
                )
            submodule = cls._make_submodule()
            cls.__leaf_name_to_cls_qualname[cls._leaf_name_] = cls.__qualname__
            cls._expose_submodule(submodule)

    __leaf_name_to_cls_qualname: ClassVar[dict[str, str]] = {}

    @classmethod
    def _make_submodule(cls) -> types.ModuleType:
        submodule_name = f'{_AUTO_MAKERS_TOP_SUBMODULE_NAME}.{cls._leaf_name_}'
        submodule_doc = cls.__doc__
        submodule = types.ModuleType(submodule_name, submodule_doc)
        public_members = dict(cls._iter_public_members())
        vars(submodule).update(public_members)
        vars(submodule)['__all__'] = list(public_members.keys())
        vars(submodule)['__getattr__'] = lambda attr_name: getattr(cls, attr_name)
        assert submodule.__name__ == submodule_name
        assert submodule.__name__.startswith(f'{_AUTO_MAKERS_TOP_SUBMODULE_NAME}.')
        assert submodule.__doc__ == submodule_doc
        return submodule

    @classmethod
    def _iter_public_members(cls) -> Iterator[tuple[str, object]]:
        for name in dir(cls):
            if not name.startswith('_'):
                yield name, getattr(cls, name)

    @classmethod
    def _expose_submodule(cls, submodule: ModuleType) -> None:
        top_submodule = cls._ensure_top_submodule()
        assert cls._leaf_name_ is not None
        setattr(top_submodule, cls._leaf_name_, submodule)
        sys.modules[submodule.__name__] = submodule

    @classmethod
    def _ensure_top_submodule(cls) -> types.ModuleType:
        global _auto_makers
        try:
            top_submodule = sys.modules[_AUTO_MAKERS_TOP_SUBMODULE_NAME]
        except KeyError:
            top_submodule = types.ModuleType(_AUTO_MAKERS_TOP_SUBMODULE_NAME)
            _auto_makers = top_submodule
            sys.modules[_AUTO_MAKERS_TOP_SUBMODULE_NAME] = top_submodule
        else:
            if top_submodule is not _auto_makers:
                raise RuntimeError(
                    f'{top_submodule!a} is not the same module object as '
                    f'`{_AUTO_MAKERS_TOP_SUBMODULE_NAME}` ({_auto_makers!a})'
                )
        assert top_submodule is _auto_makers
        assert top_submodule.__name__ == _AUTO_MAKERS_TOP_SUBMODULE_NAME
        return top_submodule


class _BaseWebAutoMakersSubmodule(_BaseAutoMakersSubmodule):
    TRUSTED_PROXIES_ENV_VAR = 'CERT_LOG_TRUSTED_PROXIES'
    REQUEST_ID_HEADER = 'X-CERT-Request-ID'

    @classmethod
    @abc.abstractmethod
    def request_path(cls) -> str | None:
        """The path the current request was sent to."""
        return None

    @classmethod
    @abc.abstractmethod
    def query_string(cls) -> str | None:
        """The query string from the current request."""
        return None

    @classmethod
    @abc.abstractmethod
    def host(cls) -> str | None:
        """The domain name or host requested by the client."""
        return None

    @classmethod
    @abc.abstractmethod
    def remote_addr(cls) -> str | None:
        # TODO: ^ Decide - 'remote_addr' or perhaps 'client_ip'/`remote_ip`/???
        # TODO: Decide whether it is *OK* to fallback to the direct TCP peer IP!
        #       And determine the ultimate content of the docstring:
        #       - the current one?
        #       - or perhaps something like this:
        #           The *real* IP of the peer (client) that sent the request.
        #           Note that for this information to be reliable, the way
        #           it is obtained needs to rely on trustworthy data (see:
        #           https://httptoolkit.com/blog/what-is-x-forwarded-for/).
        """
        The real IP address of the client that sent the current HTTP
        request (actually, this is just the address of the TCP peer,
        unless the peer is one of the configured trusted proxies and
        `X-Forwarded-For` header is set).
        """
        return None

    @classmethod
    @abc.abstractmethod
    def direct_remote_addr(cls) -> str | None:
        """IP address of the TCP peer (which may be a reverse proxy)."""
        return None

    @classmethod
    @abc.abstractmethod
    def method(cls) -> str | None:
        """The current request's HTTP method ('GET', 'POST', etc.)"""
        return None

    @classmethod
    @abc.abstractmethod
    def user_agent(cls) -> str | None:
        """The current request's User-Agent."""
        return None

    @classmethod
    @abc.abstractmethod
    def request_id(cls) -> str | None:
        """Internal request ID used for correlation between systems."""
        return None


#
# Concrete submodules providing reusable *auto-makers*


class _CommonAutoMakers(_BaseAutoMakersSubmodule):
    """
    Module `certlib.log._auto_makers.common`: general-use *auto-makers*.

    Any *auto-maker* defined here can be imported by executing:

        from certlib.log._auto_makers.common import <auto-maker key>

    Within your formatter configuration, you can refer to it with
    `"certlib.log._auto_makers.common.<auto-maker key>"`.

    A dict of all those *auto-makers* can be gained by executing:

        certlib.log._auto_makers.common import get_auto_makers
        d = get_auto_makers()
    """
    _leaf_name_ = 'common'

    py_ver = make_constant_value_provider(
        '.'.join(map(str, (sys.version_info or ())))
    )
    script_args = make_constant_value_provider(
        # TODO: decide whether it is needed, and (if so) whether
        #       its size should be hard-limited in some way...
        tuple(sys.argv or ())
    )
    tid = threading.get_native_id


class _FlaskAutoMakers(_BaseWebAutoMakersSubmodule):
    """
    Module `certlib.log._auto_makers.flask`: Flask-dedicated *auto-makers*.

    Any *auto-maker* defined here can be imported by executing:

        from certlib.log._auto_makers.flask import <auto-maker name>

    Within your formatter configuration, you can refer to it with
    `"certlib.log._auto_makers.flask.<auto-maker name>"`.

    A dict of all those *auto-makers* can be gained by executing:

        certlib.log._auto_makers.flask import get_auto_makers
        d = get_auto_makers()
    """
    _leaf_name_ = 'flask'

    @classmethod
    def request_path(cls) -> str | None:
        if request := cls._get_request():
            return request.path                    # type: ignore[no-any-return]
        return None

    @classmethod
    def query_string(cls) -> str | None:
        if request := cls._get_request():
            return request.query_string.decode()   # type: ignore[no-any-return]
        return None

    @classmethod
    def host(cls) -> str | None:
        if request := cls._get_request():
            return request.host                    # type: ignore[no-any-return]
        return None

    @classmethod
    def remote_addr(cls) -> str | None:
        if request := cls._get_request():
            trusted_proxies = os.environ.get(cls.TRUSTED_PROXIES_ENV_VAR, '').split(':')
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for and request.remote_addr in trusted_proxies:
                return forwarded_for               # type: ignore[no-any-return]
            # TODO: Verify/decide whether it is *OK* to
            #       fallback to the direct TCP peer IP!
            return request.remote_addr             # type: ignore[no-any-return]
        return None

    @classmethod
    def direct_remote_addr(cls) -> str | None:
        if request := cls._get_request():
            return request.remote_addr             # type: ignore[no-any-return]
        return None

    @classmethod
    def method(cls) -> str | None:
        if request := cls._get_request():
            return request.method                  # type: ignore[no-any-return]
        return None

    @classmethod
    def user_agent(cls) -> str | None:
        if request := cls._get_request():
            return str(request.user_agent)
        return None

    @classmethod
    def request_id(cls) -> str | None:
        if request := cls._get_request():
            return request.headers.get(cls.REQUEST_ID_HEADER)   # type: ignore[no-any-return]
        return None

    #
    # Internals

    @classmethod
    def _get_request(cls) -> Any | None:
        from flask import has_request_context, request   # type: ignore[import-not-found]

        if has_request_context():
            assert request
            return request

        return None


#
# Example *configuration corrector* implementation


class _OpinionatedConfCorrectorImpl:

    r"""
    An opinionated *configuration corrector* implementation.

    Example use:

    ```python
    import logging.config
    logging.config.dictConfig({
        "formatters": {
            "structured": {
                "()": "certlib.log.StructuredLogsFormatter",
                "defaults": {
                    "system": "MyOwn",
                    "component": "Portal",
                    "component_type": "web",
                },
                "conf_corrector": "certlib.log._opinionated_conf_corrector",
                "conf_corrector_params": {
                    "extra_auto_makers_from": [
                        "certlib.log._auto_makers.common",
                        "certlib.log._auto_makers.flask",
                    ],
                },
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["stderr"],
        },
        "disable_existing_loggers": False,
        "version": 1,
    })
    ```

    Optional params (i.e., recognized items in `conf_corrector_params`):

    * `extra_auto_makers_from` -- a list of objects (e.g., modules), or
      *dotted paths* pointing to objects, each of which is expected to
      provide a `get_auto_makers` member being a callable that takes no
      arguments and returns a mapping that maps *output data* keys to
      *auto-maker* callables (or *dotted paths* pointing to *auto-maker*
      callables). At most one *extra auto-maker* can be specified per
      *output data* key (i.e., any key conflicts between the mappings
      got from `get_auto_makers()` calls will cause an error). Moreover,
      only those of the *extra auto-makers* whose *output data* keys are
      *not* already present in the `auto_makers` dict obtained by the
      corrector are added to that dict. The rest (if any) are ignored.

    * `base_record_attr_to_output_key_overrides` -- a mapping to be used
      to update the `base_record_attr_to_output_key` dict received by
      the corrector (after updating the latter with some common stuff --
      see the `_BASE_RECORD_ATTR_TO_OUTPUT_KEY_COMMON_OVERRIDES` class
      attribute).

    * `simple_format` -- if specified (and not `None`), it should be
      *either* a [`str.format_map`][]-compatible *format string* (e.g.,
      `"{level}: {message}"`) *or* a boolean-flag-like value (`True`,
      `"true"`, `"t"`, `"1"`, `"yes"` or `"y"` -- representing *logical
      truth*; or `False`, `"false"`, `"f"`, `"0"`, `"no"`, `"n"` or empty
      string -- representing *logical falsehood*; a flag-like string is
      always examined in its `.lower()`-ed and `.strip()`-ed form). In
      the latter case, if the flag-like value represents *logical truth*,
      the default *format string* (see the `_SIMPLE_FORMAT_DEFAULT` class
      attribute) is used; on the other hand, any flag-like value that
      represents *logical falsehood* disables the feature explicitly. If
      the feature is enabled, a [`str.format_map`][]-based *serializer*
      is created. It will form log entries according to the determined
      *format string*, always substituting any missing *output data*
      values with empty strings, and automatically adding `stack_info`
      and/or `exc_text` *output data* values if available. The *simple
      format* feature is intended to be used in developers' environments
      (where real structured logs might be inconvenient).

    * `level_colors` -- if specified (and not `None`), it should be
      *either* a mapping (or an `ast.literal_eval()`-evaluable string
      representing a mapping) that maps `.lower()`-ed log level names
      (such as `"info"`, `"warning"`, `"error"`...) to ANSI color codes
      (such as `"\x1b[34m"`, `"\x1b[1;33m"`, `"\x1b[43m"`...) *or* a
      boolean-flag-like value (`True`, `"true"`, `"t"`, `"1"`, `"yes"`
      or `"y"` -- representing *logical truth*; or `False`, `"false"`,
      `"f"`, `"0"`, `"no"`, `"n"` or empty string -- representing
      *logical falsehood*; a flag-like string is always examined in its
      `.lower()`-ed and `.strip()`-ed form). In the latter case, if the
      flag-like value represents *logical truth*, the default *level
      colors* mapping (see the `_LEVEL_COLORS_DEFAULT` class attribute)
      is used; on the other hand, any flag-like value that represents
      *logical falsehood* disables the feature explicitly. If the feature
      is enabled, so that some *level colors* mapping is determined, then
      any *serializer* that was supposed to be used is being wrapped --
      to colorize every serialized output by prefixing it with the ANSI
      code corresponding (according to that mapping) to the level of the
      log entry. The param can also be set to a string that, after being
      `.lower()`-ed and `.strip()`-ed, is equal to `"auto"` -- then the
      effect depends on whether the *simple format* feature is enabled:
      if it is, the default *level colors* mapping is used; if not, the
      colorizing feature is disabled.

    Supported environment variables:

    * `CERT_LOG_SIMPLE_FORMAT` -- same as the `simple_format` param,
      but with lower priority (i.e., not used at all if the param is
      specified and not `None`).

    * `CERT_LOG_LEVEL_COLORS` -- same as the `level_colors` param,
      but with lower priority (i.e., not used at all if the param is
      specified and not `None`).

    Default behaviors:

    * Not specifying the `simple_format` param (or setting it to `None`)
      *and also* not specifying the `CERT_LOG_SIMPLE_FORMAT` environment
      variable -- is equivalent to the **`false`** setting. In other
      words, the *simple format* feature is *not* used *by default*.

    * Not specifying the `level_colors` param (or setting it to `None`)
      *and also* not specifying the `CERT_LOG_LEVEL_COLORS` environment
      variable -- is equivalent to the **`auto`** setting (!). In other
      words, the *default* behavior is that whether the *level colors*
      feature is used depends on whether the *simple format* feature
      is used.
    """

    #
    # Actual *corrector* callable

    @classmethod
    def _perform_conf_correction(cls, conf: ConfDict) -> CorrectedConfDict:
        inst = cls(conf)
        inst.adjust()
        inst.verify()
        return inst._corr_conf

    #
    # Implementation

    # * Constants:

    _OUTPUT_KEYS_ALWAYS_REQUIRED_IN_CONF: Final[Mapping[str, str]] = {
        'system': '''
            The name of the *entire system* or *project* your script/application
            is part of (e.g.: "My System", "MWDB", "n6"...).
        ''',
        'component': '''
            The name of a particular *script* or *application* being executed.
            For a CLI script it should be its basename.
        ''',
        'component_type': '''
            A conventional label of the *type* of the script/application being
            executed, agreed upon in your organization (e.g.: "web", "worker",
            "collector", "parser"...).
        ''',
    }

    _COMPONENT_TYPE_TO_OUTPUT_KEYS_REQUIRED_IN_CONF: Final[Mapping[
        str, Mapping[str, str]
    ]] = {
        'web': {
            key: (getdoc(obj) or '<not documented yet>')
            for key, obj in _BaseWebAutoMakersSubmodule.get_auto_makers().items()
        },
        'worker': {
            # TODO: description:
            'worker_id': '''
                TBD...
            '''
            # TODO: decide whether more stuff should be added here...
        },
    }

    #_VALID_COMPONENT_TYPES: Set[str] = TODO: decide whether worth defining...

    _BASE_RECORD_ATTR_TO_OUTPUT_KEY_COMMON_OVERRIDES: Final[
        Mapping[str, str | None]
    ] = {
        'thread': None,  # (let's use `tid` instead; see `_CommonAutoMakers.tid`...)
        #'processName': None,
        # ^ TODO: decide whether `processName` is useful... (universally? in some cases?)
    }

    _SIMPLE_FORMAT_ENV_VAR = 'CERT_LOG_SIMPLE_FORMAT'
    _SIMPLE_FORMAT_DEFAULT = '{level}:{func:.20}:{lineno} - {message}'

    _LEVEL_COLORS_ENV_VAR = 'CERT_LOG_LEVEL_COLORS'
    _LEVEL_COLORS_DEFAULT: Final[Mapping[str, str]] = {
        'debug': '\x1b[90m',               # grey
        'info': '\x1b[34m',                # blue
        'warning': '\x1b[1;33m',           # bold yellow
        'error': '\x1b[1;31m',             # bold red
        'critical': '\x1b[1;31m\x1b[43m',  # bold red with yellow background
    }
    _COLOR_RESET = '\x1b[0m'

    # * Initialization:

    def __init__(self, conf: ConfDict):
        corr_conf, params = self._get_corr_conf_and_params(conf)
        self._corr_conf = corr_conf
        self._params = params
        self._auto_maker_sources = self._get_auto_maker_sources(params)

    _corr_conf: Final[CorrectedConfDict]
    _params: Final[dict[str, Any]]
    _auto_maker_sources: Final[list[DottedPath | object]]

    def _get_corr_conf_and_params(
        self,
        conf: ConfDict,
    ) -> tuple[CorrectedConfDict, dict[str, Any]]:
        corr_conf = cast(CorrectedConfDict, dict(conf))
        params = dict[str, Any](corr_conf.pop('conf_corrector_params'))
        self._ensure_valid_component_type_in_defaults(corr_conf, params)
        return corr_conf, params

    def _ensure_valid_component_type_in_defaults(
        self,
        corr_conf: CorrectedConfDict,
        params: dict[str, Any],
    ) -> None:
        key = 'component_type'
        defaults = corr_conf['defaults']
        assert isinstance(defaults, dict)
        if key in defaults:
            if key in params and params[key] != defaults[key]:
                raise ValueError(
                    f'`{key}` in `conf_corrector_params` is '
                    f'different than `{key}` in `defaults` '
                    f'({params[key]!a} != {defaults[key]!a})'
                )
        elif key in params:
            defaults[key] = params[key]
        else:
            raise ValueError(
                f'`{key}` is not specified (it should be '
                f'provided as a {key!a} item in `defaults` '
                f'or `conf_corrector_params`)'
            )
        if not isinstance(defaults[key], str):
            raise TypeError(
                f'specified `{key}` is a non-string '
                f'object: {defaults[key]!a}'
            )

    def _get_auto_maker_sources(
        self,
        params: dict[str, Any],
    ) -> list[DottedPath | object]:
        sources = params.get('extra_auto_makers_from', ())
        if isinstance(sources, str) or not isinstance(sources, Iterable):
            return [sources]
        return list(sources)

    def __repr__(self) -> str:
        if self.__class__ is _OpinionatedConfCorrectorImpl:
            return f'<the `{__name__}._opinionated_conf_corrector` object>'
        return super().__repr__()

    # * Formatter configuration adjustment:

    def adjust(self) -> None:
        for key, auto_maker in self._iter_auto_maker_items():
            self._corr_conf['auto_makers'].setdefault(key, auto_maker)
        self._corr_conf['base_record_attr_to_output_key'].update({
            **self._BASE_RECORD_ATTR_TO_OUTPUT_KEY_COMMON_OVERRIDES,
            **self._params.get('base_record_attr_to_output_key_overrides', {}),
        })
        if sf_serializer := self._make_simple_format_serializer():
            self._corr_conf['serializer'] = sf_serializer
        if sc_wrapper := self._make_serializer_colorizing_wrapper(
            simple_format_in_use=bool(sf_serializer),
        ):
            self._corr_conf['serializer'] = sc_wrapper

    def _iter_auto_maker_items(self) -> Iterator[tuple[str, ValueProvider[object]]]:
        err_messages: list[str] = []
        key_to_source_seq = collections.defaultdict[str, list[object]](list)

        for source in self._auto_maker_sources:
            if isinstance(source, str):
                try:
                    source = _resolve_dotted_path(source)
                except Exception as exc:
                    err_messages.append(
                        f'* {source=!a} could not be resolved ({exc!a})'
                    )
                    continue
            get_auto_makers = getattr(source, 'get_auto_makers', None)
            if callable(get_auto_makers):
                for key, auto_maker in get_auto_makers().items():
                    key_to_source_seq[key].append(source)
                    yield key, auto_maker
            else:
                err_messages.append(
                    f'* {source!a} does not expose callable `get_auto_makers()`'
                )

        err_messages += (
            (
                f'* {key=!a} is claimed by more than one auto-maker'
                f' (from: {", ".join(map(ascii, sources_seq))})'
            )
            for key, sources_seq in key_to_source_seq.items()
            if len(sources_seq) > 1
        )
        if err_messages:
            listing = '\n\n'.join(sorted(err_messages))
            raise RuntimeError(
                f'Some auto-makers could not be included '
                f'because of the following errors:'
                f'\n\n{listing}'
            )

    def _make_simple_format_serializer(self) -> OutputSerializer | None:
        simple_format = self._determine_simple_format()
        if simple_format is None:
            return None

        si_attr = 'stack_info'
        et_attr = 'exc_text'
        attr_to_key = self._corr_conf['base_record_attr_to_output_key']

        def _yield_extra_parts_for(
            attr_name: str,
            output_data: dict[str, OutputValue],
        ) -> Iterator[str]:
            key = attr_to_key.get(attr_name, attr_name)
            if key is not None and (value := output_data.get(key)):
                yield '^'
                yield str(value).rstrip()

        def simple_format_serializer(
            output_data: dict[str, OutputValue],
        ) -> str:
            data_mapping = collections.defaultdict(str, output_data)
            main_part = simple_format.format_map(data_mapping)
            if extra_parts := [
                *_yield_extra_parts_for(si_attr, output_data),
                *_yield_extra_parts_for(et_attr, output_data),
            ]:
                return '\n'.join((main_part.rstrip(), *extra_parts, ''))
            return main_part

        return simple_format_serializer

    def _make_serializer_colorizing_wrapper(
        self,
        *,
        simple_format_in_use: bool,
    ) -> OutputSerializer | None:
        level_colors = self._determine_level_colors(simple_format_in_use)
        if level_colors is None:
            return None

        color_reset = self._COLOR_RESET
        level_attr = 'levelname'
        attr_to_key = self._corr_conf['base_record_attr_to_output_key']
        serializer_raw = self._corr_conf['serializer']
        serializer: OutputSerializer = (
            _resolve_dotted_path(serializer_raw)
            if isinstance(serializer_raw, str)
            else serializer_raw
        )

        def _get_color_if_any(
            output_data: dict[str, OutputValue],
        ) -> str | None:
            level_key = attr_to_key.get(level_attr, level_attr)
            if level_key is None:
                return None
            level = output_data.get(level_key)
            if not isinstance(level, str):
                return None
            return level_colors.get(level.lower())

        def serializer_colorizing_wrapper(
            output_data: dict[str, OutputValue],
        ) -> str:
            color = _get_color_if_any(output_data)
            serialized_output = serializer(output_data)
            if color is None:
                return serialized_output
            return f'{color}{serialized_output}{color_reset}'

        return serializer_colorizing_wrapper

    def _determine_simple_format(self) -> str | None:
        simple_format = self._params.get('simple_format')
        if simple_format is None:
            simple_format = os.environ.get(self._SIMPLE_FORMAT_ENV_VAR)
            if simple_format is None:
                return None
        if isinstance(simple_format, bool):
            simple_format = str(simple_format)
        if isinstance(simple_format, str):
            flag_str = simple_format.lower().strip()
            if flag_str in ('false', 'f', '0', 'no', 'n', ''):
                return None
            if flag_str in ('true', 't', '1', 'yes', 'y'):
                simple_format = self._SIMPLE_FORMAT_DEFAULT
            assert simple_format
            return simple_format
        raise TypeError(
            f'wrong type of {simple_format=!a}: '
            f'{type(simple_format).__qualname__}'
        )

    def _determine_level_colors(
        self,
        simple_format_in_use: bool,
    ) -> Mapping[str, str] | None:
        level_colors = self._params.get('level_colors')
        if level_colors is None:
            level_colors = os.environ.get(self._LEVEL_COLORS_ENV_VAR, 'auto')
        if isinstance(level_colors, bool):
            level_colors = str(level_colors)
        if isinstance(level_colors, str):
            flag_str = level_colors.lower().strip()
            if flag_str in ('false', 'f', '0', 'no', 'n', ''):
                return None
            if flag_str in ('true', 't', '1', 'yes', 'y'):
                return self._LEVEL_COLORS_DEFAULT
            if flag_str == 'auto':
                if simple_format_in_use:
                    return self._LEVEL_COLORS_DEFAULT
                return None
            level_colors = ast.literal_eval(level_colors)
        if isinstance(level_colors, Mapping):
            if level_colors:
                return level_colors
            return None
        raise TypeError(
            f'wrong type of {level_colors=!a}: '
            f'{type(level_colors).__qualname__}'
        )

    # * Formatter configuration verification:

    def verify(self) -> None:
        if err_messages := list(self._iter_err_messages()):
            listing = '\n\n'.join(err_messages)
            raise ValueError(
                f'According to {self!a}, some formatter '
                f'configuration elements are not valid...'
                f'\n\n{listing}'
            )

    def _iter_err_messages(self) -> Iterator[str]:
        yield from self._iter_err_messages_for_missing_output_keys(
            required=self._OUTPUT_KEYS_ALWAYS_REQUIRED_IN_CONF,
            header_message=(
                'The following commonly expected *output data* keys are '
                'missing (each of them should be included in `defaults` '
                'and/or `auto_makers`):'
            ),
        )
        ct = self._get_component_type()
        yield from self._iter_err_messages_for_missing_output_keys(
            required=self._COMPONENT_TYPE_TO_OUTPUT_KEYS_REQUIRED_IN_CONF.get(ct, {}),
            header_message=(
                f'The following *output data* keys, expected for the '
                f'{ct!a} component type, are missing (each of them should '
                f'be included in `defaults` and/or `auto_makers`):'
            ),
        )
        ct_key = 'component_type'
        if ct_key in self._corr_conf['auto_makers']:
            yield (
                f'The {ct_key!a} key should be included in `defaults` '
                f'or `conf_corrector_params`, *not* in `auto_makers`!'
            )

    def _iter_err_messages_for_missing_output_keys(
        self, required: Mapping[str, str], header_message: str
    ) -> Iterator[str]:
        if missing := sorted(
            required.keys()
            - self._corr_conf['defaults'].keys()
            - self._corr_conf['auto_makers'].keys()
        ):
            yield header_message
            for key in missing:
                description = self._get_indented_text(required[key])
                yield f'* {key!a}:\n{description}'.rstrip()

    def _get_indented_text(self, text: str, *, indent: int = 4) -> str:
        dedented = textwrap.dedent(text).removeprefix('\n')
        indented = textwrap.indent(dedented, indent * ' ')
        return indented

    def _get_component_type(self) -> str:
        ct = self._corr_conf['defaults']['component_type']
        assert isinstance(ct, str)
        return ct


# Our *configuration corrector* callable exposed at module level
# (note: you can refer to it within your formatter configuration
# with the "certlib.log._opinionated_conf_corrector" dotted path).
_opinionated_conf_corrector = _OpinionatedConfCorrectorImpl._perform_conf_correction

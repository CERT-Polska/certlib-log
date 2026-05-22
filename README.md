# certlib.log

...is a library that extends the standard [logging](https://docs.python.org/3/library/logging.html)
toolbox. It allows you to introduce _**structured logging**_ with minimal
fuss, and/or leverage some other _**logging goodies**_ (e.g., `{}`-style
message formatting).


## Basic Info

- **Documentation:** [certlib-log.readthedocs.io](https://certlib-log.readthedocs.io)
- **Repository:** [github.com/CERT-Polska/certlib-log](https://github.com/CERT-Polska/certlib-log)
- **Package:** [pypi.org/project/certlib-log](https://pypi.org/project/certlib-log/)

You can install the `certlib.log` library by running (typically, in a
[*virtual environment*](https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments))
the command:

    python3 -m pip install certlib.log

The library is compatible with Python 3.10 and all newer versions of
Python. It uses *only* the Python standard library, i.e., **it does
*not* depend on any third-party packages**.


## Principles and Benefits

The primary reason for creating `certlib.log` was to make it easier to
configure *structured logging* across various systems created and used
by [CERT Polska](https://cert.pl/en/) -- in a possibly consistent way
and without requiring extensive adjustments.

An important **design decision** was to build the library on top of
the standard [logging](https://docs.python.org/3/library/logging.html)
mechanisms (rather than introducing alternative machinery).

This approach **makes it possible to**:

- just start using the library in existing projects (especially, to
  enable [*structured logging*](https://certlib-log.readthedocs.io/page/guide/#certlib.log--tldr-how-to-quickly-enable-structured-logging))
  -- usually without changing a single line of code;

- depending on the needs, gradually introduce selected features provided
  by the library (such as [*`{}`-style*](https://certlib-log.readthedocs.io/page/guide/#certlib.log--modern-formatting-style)
  message formatting, data-only [*message-less*](https://certlib-log.readthedocs.io/page/guide/#certlib.log--dealing-with-pure-data)
  log records, or [*auto-making*](https://certlib-log.readthedocs.io/page/reference/#certlib.log.register_log_record_attr_auto_maker)
  of log record fields, e.g., from [context variables](https://docs.python.org/3/library/contextvars.html)...);

- retain existing logging configuration methods (whether
  using an [`*.ini` file](https://docs.python.org/3/library/logging.config.html#configuration-file-format)
  or loading a [configuration dict](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig)).


## Examples

### Configuring *Structured Logging* and *Auto-Makers*

```python
import logging.config

logging.config.dictConfig({
    "formatters": {
        "structured": {
            "()": "certlib.log.StructuredLogsFormatter",
            "defaults": {
                # Each key in this dict should be an *output data* key.
                # Each value should specify the respective *default value*.
                "system": "MyExample",
                "component": "MyAPI",
                "component_type": "web"
            },
            "auto_makers": {
                # Each key in this dict should be an *output data* key.
                # Each value should specify an *argumentless callable*
                # (for example, the `get()` method of some `ContextVar`).
                "client_ip": "myexample.myapi.client_ip_context_var.get",
                "nano_time": "time.time_ns"
            }
        }
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "structured"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["stderr"]
    },
    "disable_existing_loggers": False,
    "version": 1
})
```

### Logging Stuff With *`{}`-Formatted Text Message* or *No Text Message*

```python
import datetime as dt
import ipaddress
import logging
from certlib.log import xm   # Note: `xm` is short for `ExtendedMessage`

logger = logging.getLogger(__name__)

...

def example_with_text_message_formatting(city, humidity, error_summary=None):
    if error_summary:
        logger.error(xm(
            'An error occurred: {!r}', error_summary,
            exc_info=True, stack_info=True, stacklevel=2,
        ))

    logger.warning(xm('Humidity in {} is {:.1%}', city, humidity))

    logger.info(xm(
        # (Here: making use of `datetime`-specific format codes...)
        'Today is day #{today:%j} of the year {today:%Y}',
        today=dt.date.today(),

        # Arbitrary data items can also be given (which is especially
        # useful when `certlib.log.StructuredLogsFormatter` is in use).
        some_extra_item=42,
        other_arbitrary_stuff={'foo': [
            {'my-ip': ipaddress.IPv4Address('192.168.0.1')},
            dt.time(12, 59),
        ]},
    ))

def example_with_no_text(temperature, pressure, debug_data_dict, calm=True):
    # (The possibility to focus on pure data, *without* the need
    # to pass any *text-message*-related arguments, is especially
    # handy when `certlib.log.StructuredLogsFormatter` is in use.)

    if calm:
        logger.info(xm(
            # Just data:
            temperature=temperature,
            pressure=pressure,
        ))
    else:
        logger.error(xm(
            # Just data:
            temperature=temperature,
            pressure=pressure,

            # Special arguments:
            exc_info=True,
            stack_info=True,
            stacklevel=2,
        ))

    # Single dict providing data is also OK:
    logger.debug(xm(debug_data_dict))
```

You can find more examples in the [User's Guide](https://certlib-log.readthedocs.io/page/guide/).


## Copyright and License

Copyright (c) 2026, [CERT Polska](https://cert.pl/en/). All rights reserved.

The [`certlib.log`](https://github.com/CERT-Polska/certlib-log) library
is free software; you can redistribute and/or modify it under the terms
of the *BSD 3-Clause "New" or "Revised" License* (see the [`LICENSE.txt`](https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt)
file in the source code repository).

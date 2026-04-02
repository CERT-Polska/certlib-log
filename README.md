# `certlib.log`

...is a library that extends the standard [`logging`](https://docs.python.org/3/library/logging.html)
toolset. Among other things, it makes it possible to introduce
*structured logging* with minimal fuss, and/or to start using the
modern `{}`-based style of log message formatting (gradually if
required).


## Basic Info

- **Documentation:** [certlib-log.readthedocs.io](https://certlib-log.readthedocs.io)
- **Home page:** [github.com/CERT-Polska/certlib-log](https://github.com/CERT-Polska/certlib-log)
- **Contributing:** [github.com/CERT-Polska/certlib-log/pulls](https://github.com/CERT-Polska/certlib-log/pulls)

You can install the [`certlib.log`](https://pypi.org/project/certlib-log/)
library by running (typically, in a [*virtual environment*](https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments))
the command: **`python3 -m pip install certlib.log`**

The library is compatible with Python 3.10 and all newer versions of
Python. It makes use *only* of the Python's standard library, i.e.,
it **does *not* depend on any third-party packages**.


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
                "component_type": "web",
            },
            "auto_makers": {
                # Each key in this dict should be an *output data* key.
                # Each value should specify an *argumentless callable*
                # (for example, the `get()` method of some `ContextVar`).
                "client_ip": "myexample.myapi.client_ip_context_var.get",
                "nano_time": "time.time_ns",
            },
        },
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "structured",
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

    logger.warning(xm('Humidity in {} is {:.2%}', city, humidity))

    logger.info(xm(
        'Today is day #{today:%j} of the year {today:%Y}',
        today=dt.date.today(),

        # (arbitrary data items can be given, which this is especially
        # useful when `certlib.log.StructuredLogsFormatter` is in use)
        some_extra_item=42,
        other_arbitrary_stuff={'foo': [
            {'my-ip': ipaddress.IPv4Address('192.168.0.1')},
            dt.time(12, 59),
        ]},
    ))

def example_with_no_text(temperature, pressure, debug_data_dict, calm=True):
    # (especially useful when `certlib.log.StructuredLogsFormatter` is in
    # use => then any *text-message*-related output keys are just omitted)

    if calm:
        logger.info(xm(
            temperature=temperature,
            pressure=pressure,
        ))
    else:
        logger.error(xm(
            # just data:
            temperature=temperature,
            pressure=pressure,

            # special arguments:
            exc_info=True,
            stack_info=True,
            stacklevel=2,
        ))

    # single dict argument is also OK:
    logger.debug(xm(debug_data_dict))
```


## Copyright and License

Copyright (c) 2026, [CERT Polska](https://cert.pl/en/). All rights reserved.

The `certlib.log` library is free software; you can redistribute and/or
modify it under the terms of the *BSD 3-Clause "New" or "Revised" License*
(see the [`LICENSE.txt`](https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt)
file in the source code repository).

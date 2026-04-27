# Copyright (c) 2026, CERT Polska. All rights reserved.
#
# This file's content is free software; you can redistribute and/or
# modify it under the terms of the *BSD 3-Clause "New" or "Revised"
# License* (see the `LICENSE.txt` file in the source code repository:
# https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt).

from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import datetime as dt
import decimal
import fractions
import functools
import hashlib
import inspect
import ipaddress
import json
import logging
import logging.config
import math
import operator
import os
import pathlib
import re
import sys
import textwrap
import time as time_module
import uuid
from collections.abc import (
    Callable,
    Generator,
    Iterable,
    Mapping,
    Sequence,
    Set,
)
from copy import deepcopy
from enum import (
    Enum,
    auto,
)
from types import ModuleType as Module
from typing import (
    Any,
    Literal,
    NamedTuple,
    TypeVar,
)
from unittest.mock import sentinel

import pytest

project_root_path = pathlib.Path(__file__).resolve(strict=True).parent.parent
sys.path.insert(0, str(project_root_path / 'src'))
import certlib.log
from certlib.log import (
    StructuredLogsFormatter,
    _clear_auto_makers_and_internal_record_hooks_related_global_state,
    make_constant_value_provider,
    xm,
)


#
# Test helpers/constants (especially example data)
#


PY_3_11_OR_NEWER = sys.version_info[:2] >= (3, 11)

HELPER_IMPORTABLE_MODULE_NAME = (
    f'_helper_importable_module_for_certlib_log_tests_'
    f'{hashlib.sha224(ascii(__name__).encode()).hexdigest()}'
)
HELPER_IMPORTABLE_MODULE = sys.modules[HELPER_IMPORTABLE_MODULE_NAME] = (
    Module(HELPER_IMPORTABLE_MODULE_NAME)
)

EXAMPLE_LOGGER_NAME = 'some.example.logger'

EXAMPLE_TIMESTAMP_IN_NANOSECONDS = 1_770_903_450_848_759_680
EXAMPLE_TIMESTAMP_FORMATTED = '2026-02-12 13:37:30.848760Z'
EXAMPLE_COMPONENT = 'some_example_parser'
EXAMPLE_COMPONENT_TYPE = 'parser'
EXAMPLE_SYSTEM = 'My Example System'

EXAMPLE_SERIALIZER = HELPER_IMPORTABLE_MODULE.EXAMPLE_SERIALIZER = functools.partial(
    json.dumps,
    indent=4,
    sort_keys=True,
)


class ExampleClassWithCustomStrAndRepr:
    def __str__(self): return '-> STR <-'
    def __repr__(self): return '-> REPR <-'

class ExampleEnum(Enum):
    FOO = auto()
    BAR = auto()

class ExampleNamedTuple(NamedTuple):
    label: str
    blob: bytes

@dataclasses.dataclass
class ExampleDataClass:
    my_data: Any
    comment: str = ''


EXAMPLE_CUSTOM_ITEMS = {
    'foo': 'bar',
    'π': lambda: math.pi,  # `xm`-specific feature: a function/method to be called to get the value
    'SomeSpam': ExampleClassWithCustomStrAndRepr(),
    'my enum member...': ExampleEnum.FOO,
    'IPv4 address': ipaddress.IPv4Address('10.20.30.40'),
    'my_subdict': {
        (1, 2): (1, (1, (1, {1: 0.0}))),
        ExampleClassWithCustomStrAndRepr(): ExampleClassWithCustomStrAndRepr(),
        42: ExampleNamedTuple(
            'Forty two! 🍀',
            b'Do you know it?',
        ),
        'some time stuff': {
            't': dt.time(12, 38, 49),
            'd': dt.date(2026, 2, 16),
            'dt': dt.datetime(
                1989, 6, 4, 11, 59, 59, 999999,
                tzinfo=dt.timezone(dt.timedelta(hours=2)),
            ),
            'td': dt.timedelta(seconds=1),
            'tz': dt.timezone.utc,
        },
        'example exception': ipaddress.AddressValueError('blah blah blah'),
        'Numbers': [
            0,
            decimal.Decimal('123.456000'),
            2.34,
            fractions.Fraction(10, -8),
        ],
        'Singletons': [None, True, False],
        'Types': [
            int,
            dt.time,
            logging.LogRecord,
            ValueError,
            ipaddress.AddressValueError,
        ],
        'other stuff': {
            'my other enum member': ExampleEnum.BAR,
            'ipv4address': ipaddress.IPv4Address('192.168.0.1'),
            'ipv4iface': ipaddress.IPv4Interface('192.168.0.1/24'),
            'ipv4network': ipaddress.IPv4Network('192.168.0.0/24'),
            'ipv6address': ipaddress.IPv6Address('2001:0db8:85a3:0000:0000:8a2e:0370:7334'),
            'ipv6iface': ipaddress.IPv6Interface('2001:0db8:85a3:0000:0000:8a2e:0370:7334/124'),
            'ipv6network': ipaddress.IPv6Network('2001:0db8:85a3:0000:0000:8a2e:0370:7330/124'),
            'uuid': str(uuid.UUID('12345678-1234-5678-1234-567812345678')),
        },
        # (Below: very long key...)
        (' b r r R R r r R' * 1000): ExampleDataClass(
            my_data=(1, '2', bytearray(b'three'), ''),
        ),
    },
    # (Below: very long key...)
    ('-key-' * 1000): ('-value-' * 1000),
}

# (Compare to `EXAMPLE_CUSTOM_ITEMS` above...)
EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS = {
    'foo': 'bar',
    'π': math.pi,
    'SomeSpam': '-> REPR <-',
    'my enum member...': 'ExampleEnum.FOO',
    'IPv4 address': '10.20.30.40',
    'my_subdict': {
        '(1, 2)': [1, [1, [1, {'1': 0.0}]]],
        '-> STR <-': '-> REPR <-',
        '42': {
            'label': 'Forty two! 🍀',
            'blob': "b'Do you know it?'",
        },
        'some time stuff': {
            't': '12:38:49',
            'd': '2026-02-16',
            'dt': '1989-06-04 11:59:59.999999+02:00',
            'td': 'datetime.timedelta(seconds=1)',
            'tz': 'datetime.timezone.utc',
        },
        'example exception': {
            'exc_type': 'ipaddress.AddressValueError',
            'args': ['blah blah blah'],
        },
        'Numbers': [
            0,
            '123.456000',
            2.34,
            '-5/4',
        ],
        'Singletons': [None, True, False],
        'Types': [
            'int',
            'datetime.time',
            'logging.LogRecord',
            'ValueError',
            'ipaddress.AddressValueError',
        ],
        'other stuff': {
            'my other enum member': 'ExampleEnum.BAR',
            'ipv4address': '192.168.0.1',
            'ipv4iface': '192.168.0.1/24',
            'ipv4network': '192.168.0.0/24',
            'ipv6address': '2001:db8:85a3::8a2e:370:7334',
            'ipv6iface': '2001:db8:85a3::8a2e:370:7334/124',
            'ipv6network': '2001:db8:85a3::8a2e:370:7330/124',
            'uuid': '12345678-1234-5678-1234-567812345678',
        },
        # (Below: key trimmed to 200 characters.)
        (' b r r R R r r R' * 12 + ' b r r R'): {
            'my_data': [1, '2', "bytearray(b'three')", ''],
            'comment': '',
        },
    },
    # (Below: key trimmed to 200 characters.)
    ('-key-' * 40): ('-value-' * 1000),
}


class AnyOfType:

    def __init__(self, tp: type):
        self.tp = tp

    def __eq__(self, other: object) -> bool:
        return self.tp is type(other)

    def __repr__(self) -> str:
        return f'<any of type {self.tp!r}>'


class TimeModuleFakingProxy:

    def __init__(self, timestamp_ns: int = EXAMPLE_TIMESTAMP_IN_NANOSECONDS):
        timestamp = timestamp_ns / 10**9
        self.__time = lambda: timestamp
        self.__time_ns = lambda: timestamp_ns

    def __getattribute__(self, name) -> Any:
        if name == 'time':
            return super().__getattribute__('_TimeModuleFakingProxy__time')
        if name == 'time_ns':
            return super().__getattribute__('_TimeModuleFakingProxy__time_ns')
        return getattr(time_module, name)


class FormatterInitKwargsPassingVariant(Enum):
    DIRECT = 'real keyword arguments'
    MAPPING = 'mapping (dict) - passed as first positional argument'
    STRING = "`literal_eval()`-evaluable repr of dict - passed as first positional argument"


class FormatterInitIgnoredRedundantStandardArguments(Enum):
    NONE = 'no redundant std Formatter.__init__() arguments'
    POSITIONAL = 'redundant std Formatter.__init__() arguments: defaults as positional ones'
    KEYWORD = 'redundant std Formatter.__init__() arguments: defaults as keyword ones'
    VARIOUS = "redundant std Formatter.__init__() arguments: defaults' equivalents as mixed ones"


class ListLogHandler(logging.Handler):

    def __init__(self):
        super().__init__()
        self.serialized_output_list: list[str] = []
        self.deserializer: Callable[[str], Any] = json.loads

    def emit(self, record):
        serialized_output: str = self.format(record)
        self.serialized_output_list.append(serialized_output)

    @property
    def output_list(self) -> list[Any]:
        return list(map(self.deserializer, self.serialized_output_list))

    @property
    def last_output(self) -> Any:
        if self.output_list:
            return self.output_list[-1]
        raise AssertionError(f'no log entry emitted by {self!a}')


class ExampleSubclassOfStructuredLogsFormatter(StructuredLogsFormatter):

    def get_output_keys_required_in_defaults_or_auto_makers(self) -> Set[str]:
        return frozenset(
            super().get_output_keys_required_in_defaults_or_auto_makers()
        ) | {'zero'}

    def make_base_defaults(self) -> Mapping[str, object]:
        return dict(super().make_base_defaults()) | {
            'system': EXAMPLE_SYSTEM,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'xyz': 'abc',
            'zero': ['a default TO BE OVERRIDDEN...'],
        }

    def make_base_auto_makers(self) -> Mapping[str, str | Callable[[], object]]:
        return dict(super().make_base_auto_makers()) | {
            'component': make_constant_value_provider(EXAMPLE_COMPONENT),
            'zero': make_constant_value_provider(0),
        }

    def make_base_record_attr_to_output_key(self) -> Mapping[str, str | None]:
        return dict(super().make_base_record_attr_to_output_key()) | {
            'attr_name_with_typo': 'attr_name_without_typo',
            'one_silly_undesired_attr': None,
        }

    def format_timestamp(self, record: logging.LogRecord, **kwargs) -> str:
        # (This is a contrived implementation that, for the test data we
        # use, gets the same results as the default implementation -- but
        # computed in a different, obscure way...)
        kwargs.setdefault('timezone', dt.timezone(dt.timedelta(hours=2)))
        kwargs.setdefault('timestamp_as_datetime', (
            lambda timestamp, tz: dt.datetime.fromtimestamp(timestamp - 7200, tz)
        ))
        kwargs.setdefault('utc_offset_to_custom_suffix', {
            dt.timedelta(hours=2): 'Z',
        })
        return super().format_timestamp(record, **kwargs)

    def get_prepared_output_data(self, record: logging.LogRecord) -> dict[str, Any]:
        output_data = super().get_prepared_output_data(record)
        if lemon := output_data.pop('lemon ', None):
            output_data['lime'] = lemon
        return output_data

    def prepare_value(self, value: object, **kwargs) -> Any:
        prepared = super().prepare_value(value, **kwargs)
        if isinstance(prepared, dict):
            prepared = dict(sorted(prepared.items()))
        return prepared

    def prepare_submapping_key(self, key: object) -> str:
        if isinstance(key, ExampleNamedTuple):
            return 'Pomidor'
        return super().prepare_submapping_key(key)

    def serialize_prepared_output_data(self, output_data: dict[str, Any]) -> str:
        output_data = dict(sorted(output_data.items()))
        return super().serialize_prepared_output_data(output_data)


class ConstantValueAutoMaker:

    # This helper class exists *just to facilitate writing some tests*.
    # It is somewhat similar to `make_constant_value_provider()`, but
    # is equipped with extra stuff -- especially a method to obtain an
    # *importable dotted name* (aka *dotted path*) which points just
    # to the instance (that is, to the `self` object itself), and with
    # `__repr__()` returning an `ast.literal_eval()`-evaluable string
    # representing that *importable dotted name*...

    _name: str
    _value: object

    def __new__(cls, value: object) -> ConstantValueAutoMaker:
        name = cls._get_name(value)
        instance = getattr(HELPER_IMPORTABLE_MODULE, name, None)
        if instance is None:
            instance = super().__new__(cls)
            instance._name = name
            instance._value = value
            setattr(HELPER_IMPORTABLE_MODULE, name, instance)
        return instance

    @classmethod
    def _get_name(cls, value: object) -> str:
        value_repr_hash = hashlib.sha224(ascii(value).encode()).hexdigest()
        return f'_{cls.__name__}_name_{value_repr_hash}'

    def __call__(self) -> Any:
        return self._value

    def get_importable_dotted_name(self) -> str:
        return f'{HELPER_IMPORTABLE_MODULE_NAME}.{self._name}'

    def __repr__(self) -> str:
        return repr(self.get_importable_dotted_name())

    def __deepcopy__(self, *_) -> ConstantValueAutoMaker:
        return self


_ExceptionT = TypeVar('_ExceptionT', bound=BaseException)

def exc_maker(
    factory: Callable[..., _ExceptionT],
    *,
    args: Sequence[Any],
    instance_attrs: dict[str, Any] | None = None,
    notes: Sequence[str] = (),
) -> Callable[[], _ExceptionT]:

    def make_exc() -> _ExceptionT:
        exc = factory(*args)
        exc.__dict__.update(instance_attrs or ())
        if PY_3_11_OR_NEWER:
            for n in notes:
                exc.add_note(n)
        elif notes:
            exc.__notes__ = list(notes)
        return exc

    return make_exc


def get_output_base(
    *,
    level: Literal[
        'DEBUG',
        'INFO',
        'WARNING',
        'ERROR',
        'CRITICAL',
    ],
) -> dict[str, Any]:
    levelno = getattr(logging, level)
    assert isinstance(levelno, int)

    logger = EXAMPLE_LOGGER_NAME
    pid = os.getpid()
    py_ver = '.'.join(map(str, sys.version_info))
    timestamp = EXAMPLE_TIMESTAMP_FORMATTED

    return {
        'func': AnyOfType(str),
        'level': level,
        'levelno': levelno,
        'lineno': AnyOfType(int),
        'logger': logger,
        'pid': pid,
        'process_name': AnyOfType(str),
        'py_ver': py_ver,
        'script_args': AnyOfType(list),
        'src': AnyOfType(str),
        'thread_id': AnyOfType(int),
        'thread_name': AnyOfType(str),
        'timestamp': timestamp,
    }


#
# Module-global *autouse* fixtures
#


@pytest.fixture(autouse=True)
def ensure_initial_log_record_factory_is_restored():
    initial = logging.getLogRecordFactory()
    yield
    logging.setLogRecordFactory(initial)


@pytest.fixture(autouse=True)
def ensure_module_global_internal_state_is_cleaned_up():
    _clear_auto_makers_and_internal_record_hooks_related_global_state()
    yield
    _clear_auto_makers_and_internal_record_hooks_related_global_state()


@pytest.fixture(autouse=True)
def monkeypatch_relevant_time_functions(monkeypatch):
    monkeypatch.setattr(logging, 'time', TimeModuleFakingProxy())


#
# Actual tests (with their local fixtures/helpers)
#


class TestStructuredLogsFormatter:

    @pytest.fixture(params=[StructuredLogsFormatter])
    def formatter_factory(
        self,
        request,
    ) -> Callable[..., StructuredLogsFormatter]:
        return request.param

    @pytest.fixture(params=[
        dict(
            defaults={
                'system': EXAMPLE_SYSTEM,
                'component_type': EXAMPLE_COMPONENT_TYPE,
            },
            auto_makers={
                'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
            }
        ),
    ])
    def formatter_init_kwargs(
        self,
        request,
    ) -> Generator[dict[str, Any]]:
        yield deepcopy(request.param)

    @pytest.fixture(params=[FormatterInitKwargsPassingVariant.DIRECT])
    def formatter_init_kwargs_passing_variant(
        self,
        request,
    ) -> FormatterInitKwargsPassingVariant:
        return request.param

    @pytest.fixture(params=[FormatterInitIgnoredRedundantStandardArguments.NONE])
    def formatter_init_ignored_redundant_standard_arguments(
        self,
        request,
        formatter_init_kwargs_passing_variant,
    ) -> tuple[Sequence[Any], Mapping[str, Any]]:
        ign_args: Sequence[Any]
        ign_kwargs: dict[str, Any]
        if request.param is FormatterInitIgnoredRedundantStandardArguments.NONE:
            ign_args = ()
            ign_kwargs = {}
        elif request.param is FormatterInitIgnoredRedundantStandardArguments.POSITIONAL:
            ign_args = (
                None,  # `fmt`
                None,  # `datefmt`
                '%',   # `style`
                True,  # `validate`
            )
            ign_kwargs = {}
        elif request.param is FormatterInitIgnoredRedundantStandardArguments.KEYWORD:
            ign_args = ()
            ign_kwargs = {
                'fmt': None,
                'datefmt': None,
                'style': '%',
                'validate': True,
            }
        elif request.param is FormatterInitIgnoredRedundantStandardArguments.VARIOUS:
            ign_args = (
                '',   # `fmt`
                '',   # `datefmt`
            )
            ign_kwargs = {
                'style': '%',
                'validate': 'some truthy value',
            }
        else:
            raise AssertionError(f'{request.param=}')
        if formatter_init_kwargs_passing_variant is not FormatterInitKwargsPassingVariant.DIRECT:
            # The actual arguments (as a dict or its repr) are to be
            # passed as the first (`fmt`) argument to `__init__()`...
            ign_args = ign_args[1:]
            ign_kwargs.pop('fmt', None)
        return ign_args, ign_kwargs

    @pytest.fixture
    def formatter(
        self,
        formatter_factory,
        formatter_init_kwargs,
        formatter_init_kwargs_passing_variant,
        formatter_init_ignored_redundant_standard_arguments,
    ) -> Generator[StructuredLogsFormatter]:
        ign_args, ign_kwargs = formatter_init_ignored_redundant_standard_arguments
        if formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.DIRECT:
            f = formatter_factory(*ign_args, **ign_kwargs, **formatter_init_kwargs)
        elif formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.MAPPING:
            f = formatter_factory(formatter_init_kwargs, *ign_args, **ign_kwargs)
        elif formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.STRING:
            f = formatter_factory(repr(formatter_init_kwargs), *ign_args, **ign_kwargs)
        else:
            raise AssertionError(f'{formatter_init_kwargs_passing_variant=}')
        yield f
        f.unregister_auto_makers()

    @pytest.fixture
    def log_handler(self, formatter) -> Generator[ListLogHandler]:
        h = ListLogHandler()
        h.setFormatter(formatter)
        yield h
        h.close()

    @pytest.fixture
    def logger(self, log_handler) -> Generator[logging.Logger]:
        log = logging.getLogger(EXAMPLE_LOGGER_NAME)
        initial_level = log.level
        initial_propagate = log.propagate
        try:
            log.propagate = False
            try:
                log.setLevel(logging.DEBUG)
                try:
                    log.addHandler(log_handler)
                    yield log
                finally:
                    log.removeHandler(log_handler)
            finally:
                log.setLevel(initial_level)
        finally:
            log.propagate = initial_propagate

    @pytest.fixture
    def example_custom_items(self) -> Mapping[str, Any]:
        return deepcopy(EXAMPLE_CUSTOM_ITEMS)


    def test_log_message_using_legacy_style(
        self,
        logger,
        log_handler,
    ):
        logger.info(
            "Let's log this: %s=%r, %s=%.6f",
            'foo', 'bar', 'π', math.pi,
        )

        assert log_handler.output_list == [{
            **get_output_base(level='INFO'),
            'message': "Let's log this: foo='bar', π=3.141593",
            'message_base': "Let's log this: %s=%r, %s=%.6f",
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    def test_log_message_using_xm(
        self,
        logger,
        log_handler,
    ):
        logger.warning(xm(
            "Let's log this: {}={!r}, {}={:.6f}",
            'foo', 'bar', 'π', math.pi,
        ))

        assert log_handler.output_list == [{
            **get_output_base(level='WARNING'),
            'message': "Let's log this: foo='bar', π=3.141593",
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {}={:.6f}",
            },
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    def test_log_message_using_xm_with_args_explicitly_numbered_in_message_pattern(
        self,
        logger,
        log_handler,
    ):
        logger.error(xm(
            "Let's log this: {0}={1!r}, {2}={3:.6f}",
            'foo', lambda: 'bar', lambda: 'π', math.pi,
        ))

        assert log_handler.output_list == [{
            **get_output_base(level='ERROR'),
            'message': "Let's log this: foo='bar', π=3.141593",
            'message_base': {
                'pattern': "Let's log this: {0}={1!r}, {2}={3:.6f}",
            },
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    def test_log_message_using_xm_also_with_kwargs(
        self,
        logger,
        log_handler,
    ):
        logger.critical(xm(
            "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            'foo', 'bar', const_symbol='π', const_value=lambda: math.pi,
        ))

        assert log_handler.output_list == [{
            **get_output_base(level='CRITICAL'),
            'message': "Let's log this: foo='bar', π=3.141593",
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            },
            'const_symbol': 'π',      # <- Note extra item
            'const_value': math.pi,   # <- Note extra item
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    def test_log_message_using_xm_also_with_kwargs_including_extra_data(
        self,
        logger,
        log_handler,
        example_custom_items,
    ):
        logger.debug(xm(
            "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            lambda: 'foo', 'bar', const_symbol=lambda: 'π', const_value=math.pi,
            **example_custom_items,
        ))

        assert log_handler.output_list == [{
            **get_output_base(level='DEBUG'),
            'message': "Let's log this: foo='bar', π=3.141593",
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            },
            'const_symbol': 'π',                      # <- Note extra item
            'const_value': math.pi,                   # <- Note extra item
            **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,   # <- Note extra items not used in message
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    def test_log_just_data_using_xm_with_kwargs(
        self,
        logger,
        log_handler,
        example_custom_items,
    ):
        logger.info(xm(**example_custom_items))

        assert log_handler.output_list == [{
            **get_output_base(level='INFO'),
            **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        # (See `EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS`...)
        n, t, f = log_handler.last_output['my_subdict']['Singletons']
        assert n is None
        assert t is True
        assert f is False


    def test_log_just_data_using_xm_with_dict_as_one_argument(
        self,
        logger,
        log_handler,
        example_custom_items,
    ):
        logger.warning(xm(example_custom_items))

        assert log_handler.output_list == [{
            **get_output_base(level='WARNING'),
            **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        # (See `EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS`...)
        n, t, f = log_handler.last_output['my_subdict']['Singletons']
        assert n is None
        assert t is True
        assert f is False


    @pytest.mark.parametrize(
        ('logger_method_call', 'expected_output_base'),
        [
            (
                lambda logger: logger.error(
                    'Error occurred!',
                    exc_info=True,
                ),
                {
                    **get_output_base(level='ERROR'),
                    'message': 'Error occurred!',
                    'message_base': 'Error occurred!',
                },
            ),
            (
                lambda logger: logger.critical(
                    'Error occurred! %d',
                    123,
                    exc_info=True,
                ),
                {
                    **get_output_base(level='CRITICAL'),
                    'message': 'Error occurred! 123',
                    'message_base': 'Error occurred! %d',
                },
            ),
            (
                lambda logger: logger.debug(
                    xm('Error occurred!'),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='DEBUG'),
                    'message': 'Error occurred!',
                    'message_base': {'pattern': 'Error occurred!'},
                },
            ),
            (
                lambda logger: logger.info(
                    xm('Error occurred!', exc_info=True),
                ),
                {
                    **get_output_base(level='INFO'),
                    'message': 'Error occurred!',
                    'message_base': {'pattern': 'Error occurred!'},
                },
            ),
            (
                lambda logger: logger.warning(
                    xm('Error occurred! {n}', n=123),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='WARNING'),
                    'message': 'Error occurred! 123',
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.error(
                    xm('Error occurred! {n}', n=123, exc_info=True)
                ),
                {
                    **get_output_base(level='ERROR'),
                    'message': 'Error occurred! 123',
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.critical(
                    xm(),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='CRITICAL'),
                },
            ),
            (
                lambda logger: logger.debug(
                    xm(exc_info=True),
                ),
                {
                    **get_output_base(level='DEBUG'),
                },
            ),
            (
                lambda logger: logger.info(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                {
                    **get_output_base(level='INFO'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                lambda logger: logger.warning(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                {
                    **get_output_base(level='WARNING'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.error(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.log(
                    logging.CRITICAL,
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='CRITICAL'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                lambda logger: logger.exception(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS)),
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                lambda logger: logger.exception(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS)),
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.exception(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.exception(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        ('make_exc', 'expected_exc_info'),
        [
            (
                exc_maker(KeyboardInterrupt, args=()),
                {
                    'exc_type': 'KeyboardInterrupt',
                },
            ),
            (
                exc_maker(ValueError, args=('auć',)),
                {
                    'exc_type': 'ValueError',
                    'args': ['auć'],
                },
            ),
            (
                exc_maker(KeyError, args=(), instance_attrs={'x': 1, 'y': 0}),
                {
                    'exc_type': 'KeyError',
                    'dict': {'x': 1, 'y': 0},
                },
            ),
            (
                exc_maker(
                    ipaddress.AddressValueError,
                    args=('auć', 0.0, None),
                    instance_attrs={
                        'foo': {42: ('spam', 'parrot')},
                        'bar': dt.datetime(
                            2025, 12, 24, 16, 1, 12,
                            tzinfo=dt.timezone.utc,
                        ),
                    },
                    notes=('abc', 'Efg Hi Jkl'),
                ),
                {
                    'exc_type': 'ipaddress.AddressValueError',
                    'args': ['auć', 0.0, None],
                    'dict': {
                        'foo': {'42': ['spam', 'parrot']},
                        'bar': '2025-12-24 16:01:12+00:00',
                        '__notes__': ['abc', 'Efg Hi Jkl'],
                    },
                },
            ),
        ],
    )
    def test_log_with_exc_info_set_to_true_while_exception_is_being_handled(
        self,
        make_exc,
        logger,
        logger_method_call,
        log_handler,
        expected_output_base,
        expected_exc_info,
    ):
        try:
            raise make_exc()
        except BaseException:            # noqa
            logger_method_call(logger)   # noqa

        assert log_handler.output_list == [{
            **expected_output_base,
            'exc_info': expected_exc_info,
            'exc_text': AnyOfType(str),
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        exc_text = log_handler.last_output['exc_text']
        assert exc_text.startswith('Traceback (most recent call last):\n')
        assert 'test_log_with_exc_info_set_to_true_while_exception_is_being_handled' in exc_text
        assert expected_exc_info['exc_type'] in exc_text


    @pytest.mark.parametrize(
        ('logger_method_call', 'expected_output_base'),
        [
            (
                lambda logger: logger.debug(
                    'Some happened!',
                    stack_info=True,
                ),
                {
                    **get_output_base(level='DEBUG'),
                    'message': 'Some happened!',
                    'message_base': 'Some happened!',
                },
            ),
            (
                lambda logger: logger.info(
                    'Some happened! %d',
                    123,
                    stack_info=True,
                ),
                {
                    **get_output_base(level='INFO'),
                    'message': 'Some happened! 123',
                    'message_base': 'Some happened! %d',
                },
            ),
            (
                lambda logger: logger.warning(
                    xm('Some happened!'),
                    stack_info=True,
                ),
                {
                    **get_output_base(level='WARNING'),
                    'message': 'Some happened!',
                    'message_base': {'pattern': 'Some happened!'},
                },
            ),
            (
                lambda logger: logger.error(
                    xm('Some happened!', stack_info=True),
                ),
                {
                    **get_output_base(level='ERROR'),
                    'message': 'Some happened!',
                    'message_base': {'pattern': 'Some happened!'},
                },
            ),
            (
                lambda logger: logger.critical(
                    xm('Some happened! {n}', n=123),
                    stack_info=True,
                ),
                {
                    **get_output_base(level='CRITICAL'),
                    'message': 'Some happened! 123',
                    'message_base': {'pattern': 'Some happened! {n}'},
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.debug(
                    xm('Some happened! {n}', n=123, stack_info=True)
                ),
                {
                    **get_output_base(level='DEBUG'),
                    'message': 'Some happened! 123',
                    'message_base': {'pattern': 'Some happened! {n}'},
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.info(
                    xm(),
                    stack_info=True,
                ),
                {
                    **get_output_base(level='INFO'),
                },
            ),
            (
                lambda logger: logger.warning(
                    xm(stack_info=True),
                ),
                {
                    **get_output_base(level='WARNING'),
                },
            ),
            (
                lambda logger: logger.error(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), stack_info=True),
                ),
                {
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            (
                lambda logger: logger.critical(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), stack_info=True),
                ),
                {
                    **get_output_base(level='CRITICAL'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
        ],
    )
    def test_log_with_stack_info_set_to_true(
        self,
        logger,
        logger_method_call,
        log_handler,
        expected_output_base,
    ):
        def a(): logger_method_call(logger)
        def b(): a()
        def c(): b()

        c()

        assert log_handler.output_list == [{
            **expected_output_base,
            'func': '<lambda>',
            'stack_info': AnyOfType(str),
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        stack_lines = log_handler.last_output['stack_info'].splitlines()
        assert stack_lines[0] == 'Stack (most recent call last):'
        assert stack_lines[-10].endswith('in test_log_with_stack_info_set_to_true')
        assert stack_lines[-9].endswith('  c()')
        assert stack_lines[-8].endswith('in c')
        assert stack_lines[-7].endswith('  def c(): b()')
        assert stack_lines[-6].endswith('in b')
        assert stack_lines[-5].endswith('  def b(): a()')
        assert stack_lines[-4].endswith('in a')
        assert stack_lines[-3].endswith('  def a(): logger_method_call(logger)')
        assert stack_lines[-2].endswith('in <lambda>')
        assert '  lambda logger: logger.' in stack_lines[-1]


    @pytest.mark.parametrize(
        'stacklevel',
        [1, 2, 3],
    )
    @pytest.mark.parametrize(
        'pass_kwargs_to_xm',
        [False, True],
    )
    def test_log_with_stack_info_set_to_true_and_stacklevel_specified(
        self,
        logger,
        log_handler,
        stacklevel,
        pass_kwargs_to_xm,
    ):
        stack_related_kwargs = dict(
            stack_info=True,
            stacklevel=stacklevel,
        )

        def a():
            logger.info(
                xm(
                    **deepcopy(EXAMPLE_CUSTOM_ITEMS),
                    **(stack_related_kwargs if pass_kwargs_to_xm else {}),
                ),
                **({} if pass_kwargs_to_xm else stack_related_kwargs),
            )
        def b(): a()
        def c(): b()

        expected_stack_line_suffixes = [
            'in test_log_with_stack_info_set_to_true_and_stacklevel_specified',
            '  c()',
            'in c',
            '  def c(): b()',
            'in b',
            '  def b(): a()',
            'in a',
            '  logger.info(',
        ][:(10 - 2 * stacklevel)]

        expected_func = [
            'a',
            'b',
            'c',
        ][stacklevel - 1]

        expected_output_base = {
            **get_output_base(level='INFO'),
            **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
            'func': expected_func,
        }

        c()

        assert log_handler.output_list == [{
            **expected_output_base,
            'stack_info': AnyOfType(str),
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        stack_lines = log_handler.last_output['stack_info'].splitlines()
        assert stack_lines[0] == 'Stack (most recent call last):'
        for i, suffix in enumerate(reversed(expected_stack_line_suffixes), start=1):
            assert stack_lines[-i].endswith(suffix)


    # @pytest.mark.skip('...not implemented yet...')
    # def test_TODO_more_cases(self, formatter):
    #     TODO


    @pytest.mark.parametrize(
        ('formatter_factory', 'formatter_init_kwargs'),
        [
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'zero': ConstantValueAutoMaker(0),
                    }
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'blah_blah_blah': 2222,
                        'component_type': 'a default TO BE OVERRIDDEN...',
                        'system': EXAMPLE_SYSTEM,
                        'zero': 0,
                    },
                    auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        'component': (
                            ConstantValueAutoMaker(EXAMPLE_COMPONENT)
                            .get_importable_dotted_name()
                        ),
                        'blah_blah_blah': (
                            ConstantValueAutoMaker(None)  # (<- A void value masks the default...)
                            .get_importable_dotted_name()
                        ),
                        'xyz': ConstantValueAutoMaker('abc'),
                    },
                    serializer=f'{HELPER_IMPORTABLE_MODULE_NAME}.EXAMPLE_SERIALIZER',
                ),
            ),
            (
                ExampleSubclassOfStructuredLogsFormatter,
                dict(),
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        'formatter_init_kwargs_passing_variant',
        list(FormatterInitKwargsPassingVariant),
        indirect=True,
    )
    @pytest.mark.parametrize(
        'formatter_init_ignored_redundant_standard_arguments',
        list(FormatterInitIgnoredRedundantStandardArguments),
        indirect=True,
    )
    @pytest.mark.parametrize(
        ('logger_method_calls', 'expected_output_list'),
        [
            pytest.param(
                [
                    lambda logger: logger.info(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                    ),
                    lambda logger: logger.warning(
                        xm(
                            'Example message - {}, {!r}, {:04}, {{}}',
                            'Foo', 'spam', 42,
                        ),
                    ),
                    lambda logger: logger.error(
                        xm(
                            'Example message - {0}, {1!r}, {2:04}, {{}}',
                            'Foo', 'spam', 42,
                        ),
                    ),
                    lambda logger: logger.critical(
                        xm(
                            'Example message - {}, {!r}, {:04}, {{}}',
                            'Foo', 'spam', 42,
                            bar='B',
                            component='CCC',
                            system='S',
                        ),
                    ),
                    lambda logger: logger.debug(
                        xm(
                            'Example message - {}, {!r}, {:04}, {{}}',
                            'Foo', 'spam', 42,
                            bar='B',
                            component='CCC',
                            system='S',
                        ),
                        extra=dict(
                            bar='B-2',
                            component='CCC-2',
                            system='S-2',
                        ),
                    ),
                    lambda logger: logger.info(
                        xm(
                            'Example message - {}, {!r}, {:04}, {{}}',
                            'Foo', 'spam', 42,
                            bar='B',
                            component=EXAMPLE_COMPONENT,
                            system='S',
                        ),
                        extra=dict(
                            bar='B',
                            component=EXAMPLE_COMPONENT,
                            system='S',
                        ),
                    ),
                ],
                [
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {0}, {1!r}, {2:04}, {{}}',
                        },
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'bar': 'B',
                        'component': 'CCC',                # [sic!]
                        'component_': EXAMPLE_COMPONENT,   # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': 'S',     # [sic!]
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'bar': 'B',        # [sic!]
                        'bar_': 'B-2',     # [sic!]
                        'component': 'CCC',                # [sic!]
                        'component_': EXAMPLE_COMPONENT,   # [sic!]
                        'component__': 'CCC-2',            # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': 'S',      # [sic!]
                        'system_': 'S-2',   # [sic!]
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'bar': 'B',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': 'S',
                        'xyz': 'abc',
                        'zero': 0,
                    },
                ],
                id='message_formating_with_args',
            ),
            pytest.param(
                [
                    lambda logger: logger.warning(
                        'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        dict(
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                    ),
                    lambda logger: logger.error(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                    ),
                    lambda logger: logger.critical(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            asctime='What time is it?',
                            bar='spam',
                            baz=42,
                            foo='Foo',
                            spam='ham',
                            system='Śmystem',
                            timestamp='Śmajstamp',
                        ),
                        extra=dict(
                            timestamp='And now for something completely different!',
                        ),
                    ),
                    lambda logger: logger.debug(
                        xm(
                            'Example message - {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                    ),
                ],
                [
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'asctime': 'What time is it?',
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'spam': 'ham',
                        'system': 'Śmystem',
                        'xyz': 'abc',
                        'zero': 0,
                    } | (
                        {
                            # Under PyPy, the order of keys in a log record's
                            # `__dict__` may be different from insertion order
                            # (see: https://github.com/pypy/pypy/issues/5436).
                            # This affects the order in which *output data* keys
                            # are inserted and deduplicated with `_` suffixes...
                            'timestamp': 'Śmajstamp',
                            'timestamp_': AnyOfType(str),
                            'timestamp__': AnyOfType(str),
                        } if sys.implementation.name == 'pypy'
                        else {
                            'timestamp': 'Śmajstamp',
                            'timestamp_': 'And now for something completely different!',
                            'timestamp__': EXAMPLE_TIMESTAMP_FORMATTED,
                        }
                    ),
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'message': 'Example message - {}',   # [sic!]
                        'message_base': {
                            'pattern': 'Example message - {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                ],
                id='message_formating_with_dict_or_kwargs',
            ),
            pytest.param(
                [
                    lambda logger: logger.info(
                        'Example message - %s, %r, %04d, %%',
                    ),
                    lambda logger: logger.warning(
                        'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                    ),
                    lambda logger: logger.error(
                        'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        extra=dict(foo='Foo', bar='spam', baz=42),
                    ),
                    lambda logger: logger.critical(
                        '',
                    ),
                    lambda logger: logger.debug(
                        '',
                        extra=dict(foo='Foo', bar='spam', baz=42),
                    ),
                    lambda logger: logger.info(
                        xm('Example message - {}, {!r}, {:04}, {{}}'),
                    ),
                    lambda logger: logger.warning(
                        xm('Example message - {}, {!r}, {baz:04}, {{}}'),
                    ),
                    lambda logger: logger.error(
                        xm('Example message - {foo}, {bar!r}, {baz:04}, {{}}'),
                        extra=dict(foo='Foo', bar='spam', baz=42),
                    ),
                    lambda logger: logger.critical(
                        xm(),
                    ),
                    lambda logger: logger.debug(
                        xm(''),
                    ),
                    lambda logger: logger.info(
                        xm(foo='Foo', bar='spam', baz=42),
                    ),
                    lambda logger: logger.warning(
                        xm(dict(foo='Foo', bar='spam', baz=42)),
                    ),
                    lambda logger: logger.error(
                        xm(),
                        extra=dict(foo='Foo', bar='spam', baz=42),
                    ),
                    lambda logger: logger.critical(
                        xm(foo='Foo', bar='spam'),
                        extra=dict(foo='Foo', baz=42),
                    ),
                    lambda logger: logger.debug(
                        xm(foo='Foo', bar='spam'),
                        extra=dict(foo='ooooooo', baz=42),
                    ),
                    lambda logger: logger.info(
                        xm(dict(foo='Foo', bar='spam')),
                        extra=dict(foo='ooooooo', baz=42),
                    ),
                    lambda logger: logger.warning(
                        xm('', foo='Foo', bar='spam'),
                        extra=dict(foo='ooooooo', baz=42),
                    ),
                ],
                [
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %s, %r, %04d, %%',
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {}, {!r}, {:04}, {{}}',
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'foo_': 'ooooooo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'foo_': 'ooooooo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'foo_': 'ooooooo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                ],
                id='no_message_formatting',
            ),
            pytest.param(
                [
                    lambda logger: logger.error(
                        xm(
                            'Example message - {}, {!r}, {baz:04}, {{}}',
                            'Foo', 'spam',
                            baz=42,
                        ),
                    ),
                    lambda logger: logger.log(
                        logging.CRITICAL,
                        xm(
                            'Example message - {}, {!r}, {baz:04}, {{}}',
                            'Foo', 'spam',
                            baz=42,
                            something_else=[{42: 42}],
                            system='',
                        ),
                    ),
                    lambda logger: logger.debug(
                        xm(
                            'Example message - {}, {!r}, {baz}, {{}}',
                            'Foo', 'spam',
                            bar='',
                            baz=None,
                            component=None,
                            system='',
                        ),
                        extra=dict(
                            bar=2.0,
                            baz=3,
                            something_else=[{42: 42}],
                            system='S-2',
                        ),
                    ),
                    lambda logger: logger.info(
                        xm(
                            'Example message - {}, {!r}, {baz:04}, {{}}',
                            'Foo', 'spam',
                            baz=42,
                            something_else=[{42: 42}],
                            system='',
                        ),
                        extra=dict(
                            bar=2.0,
                            baz=3,
                            component='',
                            something_else=[{'42': 42}],
                            system=None,
                        ),
                    ),
                ],
                [
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'baz': 42,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'baz': 42,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'something_else': [{'42': 42}],
                        # No 'system' [sic!] (the default has been masked by a void value)
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', None, {}",   # [sic!]
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz}, {{}}',
                        },
                        'bar': 2.0,
                        'baz': 3,    # [sic!]
                        'component': EXAMPLE_COMPONENT,   # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'something_else': [{'42': 42}],
                        'system': 'S-2',   # [sic!]
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'bar': 2.0,
                        'baz': 42,    # [sic!]
                        'baz_': 3,    # [sic!]
                        'component': EXAMPLE_COMPONENT,   # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'something_else': [{'42': 42}],
                        # No 'system' [sic!] (the default has been masked by a void value)
                        'xyz': 'abc',
                        'zero': 0,
                    },
                ],
                id='message_formatting_with_args_and_kwargs',
            ),
            pytest.param(
                [
                    lambda logger: logger.warning(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                        stacklevel=2,
                    ),
                    lambda logger: logger.error(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                        stacklevel=2,
                    ),
                    lambda logger: logger.critical(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                            stacklevel=2,
                        ),
                    ),
                    lambda logger: logger.debug(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                        stacklevel=1,
                    ),
                    lambda logger: logger.info(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                        stacklevel=1,
                    ),
                    lambda logger: logger.warning(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                            stacklevel=1,
                        ),
                    ),
                    lambda logger: logger.error(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                        stacklevel=0,
                    ),
                    lambda logger: logger.critical(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                        stacklevel=0,
                    ),
                    lambda logger: logger.debug(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                            stacklevel=0,
                        ),
                    ),
                    lambda logger: logger.info(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                        stacklevel=-1,
                    ),
                    lambda logger: logger.warning(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                        stacklevel=-1,
                    ),
                    lambda logger: logger.error(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                            stacklevel=-1,
                        ),
                    ),
                    lambda logger: logger.critical(
                        'Example message - %s, %r, %04d, %%',
                        'Foo', 'spam', 42,
                        stacklevel=-10,
                    ),
                    lambda logger: logger.debug(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                        ),
                        stacklevel=-10,
                    ),
                    lambda logger: logger.info(
                        xm(
                            'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                            foo='Foo',
                            bar='spam',
                            baz=42,
                            stacklevel=-10,
                        ),
                    ),
                ],
                [
                    {
                        **get_output_base(level='WARNING'),
                        'func': (
                            'test_a_bunch_of_cases_including_some_more_complex_or_contrived_ones'
                        ),
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': (
                            'test_a_bunch_of_cases_including_some_more_complex_or_contrived_ones'
                        ),
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': (
                            'test_a_bunch_of_cases_including_some_more_complex_or_contrived_ones'
                        ),
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        # (Note: for the `stacklevel < 1` corner case,
                        # older Python versions behave differently...)
                        'func': 'findCaller' if PY_3_11_OR_NEWER else '<lambda>',
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                ],
                id='with_stacklevel_specified',
            ),
        ],
    )
    def test_a_bunch_of_cases_including_some_more_complex_or_contrived_ones(
        self,
        logger,
        logger_method_calls,
        log_handler,
        expected_output_list,
    ):
        for call in logger_method_calls:
            call(logger)

        assert log_handler.output_list == expected_output_list


# @pytest.mark.skip('...not implemented yet...')
# class TestExtendedMessage:
#     def test_TODO(self):
#         TODO


# @pytest.mark.skip('...not implemented yet...')
# class TestAutoMakersRegistry:
#     def test_TODO(self):
#         TODO


def test_make_constant_value_provider():
    auto_maker = make_constant_value_provider(sentinel.VALUE)
    assert auto_maker() is sentinel.VALUE


class TestSnippetsInDocumentation:

    class _SnippetFinder:

        _SNIPPET_REGEX = re.compile(
            # *Note*: here false positives (which are likely to cause
            # errors) are considered better than any unnoticed stuff!
            # In particular, we *want* to match also *invalid* syntax
            # labels (we reject them at a later stage of processing).
            r'''
                ^             # <- beginning of line
                [^\S\n]*      # <- zero or more whitespace characters except '\n'
                ```           # <- backticks denoting beginning of snippet

                (?P<syntax_label>  # syntax (language) label, e.g., "python" or "json":
                    [^\n]*?   # <- zero or more characters: *any* except '\n'
                )             #    (consumed in *non-greedy* manner)

                [^\S\n]*      # <- zero or more whitespace characters except '\n'
                \n            # <- obligatory newline character
                \s*           # <- zero or more whitespace characters (may include '\n')

                (?P<content>       # snippet's significant content: 
                    ^         # <- beginning of line
                    .*?       # <- zero or more characters: *any*
                )             #    (consumed in *non-greedy* manner)

                \s*           # <- zero or more whitespace characters (may include '\n')
                ^             # <- beginning of line
                [^\S\n]*      # <- zero or more whitespace characters except '\n'
                ```           # <- backticks denoting end of snippet
                [^\S\n]*      # <- zero or more whitespace characters except '\n'
                $             # <- end of line/file
            ''',
            re.DOTALL | re.MULTILINE | re.VERBOSE,
        )

        @dataclasses.dataclass(frozen=True)
        class _Snippet:
            syntax_label: str
            dedented_content: str
            start_lineno: int = dataclasses.field(compare=False)

            def __post_init__(self):
                if not (self.syntax_label.isidentifier()
                        and self.syntax_label.isascii()):
                    raise AssertionError(
                        f'{self.syntax_label!r} is not a valid syntax '
                        f'label, regarding the snippet:\n\n{self}'
                    )

            def __str__(self):
                header = f'starting at line #{self.start_lineno}'
                underline = len(header) * '~'
                return (
                    f"{header}\n{underline}\n"
                    f"```{self.syntax_label}\n"
                    f"{self.dedented_content}\n"
                    f"```\n"
                )

        def __init__(self, source_module_or_path: Module | pathlib.Path | str):
            self._source_module_or_path = source_module_or_path
            self._source_descr = (
                repr(source_module_or_path).removeprefix('<').removesuffix('>')
                if isinstance(source_module_or_path, Module)
                else f'file {str(source_module_or_path)!r}'
            )
            self._snippets_already_covered = set()

        _source_module_or_path: Module | pathlib.Path | str
        _source_descr: str
        _snippets_already_covered: set[_Snippet]

        @functools.cache
        def lookup(
            self,
            substring: str,
            *,
            syntax_label: str = 'python',
            mark_as_covered: bool = True,
        ) -> str:

            matching_snippets = [
                snippet
                for snippet in self._all_snippets_sorted_by_start_lineno
                if (snippet.syntax_label == syntax_label
                    and substring in snippet.dedented_content)
            ]
            if not matching_snippets:
                raise AssertionError(
                    f'no matching snippet found in {self._source_descr} '
                    f'({syntax_label=}, {substring=})'
                )
            try:
                [the_snippet] = matching_snippets
            except ValueError as exc:
                listing = '\n'.join(map(str, matching_snippets))
                raise AssertionError(
                    f'{len(matching_snippets)} (more than one) '
                    f'matching snippets found in {self._source_descr} '
                    f'({syntax_label=}, {substring=}):\n\n{listing}'
                ) from exc

            if mark_as_covered:
                self._snippets_already_covered.add(the_snippet)

            return the_snippet.dedented_content

        def assert_all_snippets_covered(self):
            if not_covered := self._get_snippets_still_not_covered():
                raise AssertionError(
                    f'{len(not_covered)} snippet(s) (from '
                    f'{self._source_descr}) not covered:\n\n'
                    f'{self._format_snippets_listing(not_covered)}'
                )

        def _get_snippets_still_not_covered(self) -> Set[_Snippet]:
            return self._all_snippets - self._snippets_already_covered

        def _format_snippets_listing(self, snippets: Iterable[_Snippet]) -> str:
            sort_key = operator.attrgetter('start_lineno')
            sorted_seq = sorted(snippets, key=sort_key)
            return '\n'.join(map(str, sorted_seq))

        @functools.cached_property
        def _all_snippets_sorted_by_start_lineno(self) -> Sequence[_Snippet]:
            sort_key = operator.attrgetter('start_lineno')
            return sorted(self._all_snippets, key=sort_key)

        @functools.cached_property
        def _all_snippets(self) -> Set[_Snippet]:
            return frozenset(self._generate_all_snippets())

        def _generate_all_snippets(self) -> Generator[_Snippet]:
            index = 0
            lineno = 1
            for match in self._SNIPPET_REGEX.finditer(self._source):
                prev_index = index
                index = match.start()
                lineno += self._source.count('\n', prev_index, index)
                yield self._Snippet(
                    syntax_label=match['syntax_label'],
                    dedented_content=textwrap.dedent(match['content']),
                    start_lineno=lineno,
                )

        @functools.cached_property
        def _source(self) -> str:
            if isinstance(self._source_module_or_path, Module):
                return inspect.getsource(self._source_module_or_path)
            abs_path = project_root_path / self._source_module_or_path
            return abs_path.read_text()


    class _DateClassFakingProxy:

        def __init__(self, timestamp: float):
            # (Here we just reproduce relations between timestamps and
            # `dt.date.today()`'s results specific to our snippets...)
            one_hour_offset_tz = dt.timezone(dt.timedelta(hours=1))
            date = dt.datetime.fromtimestamp(timestamp, one_hour_offset_tz).date()
            self.__fake_today = lambda: date

        def __getattribute__(self, name, *, __orig_date_class=dt.date) -> Any:
            if name == 'today':
                return super().__getattribute__('_DateClassFakingProxy__fake_today')
            return getattr(__orig_date_class, name)

        def __call__(self, *args, __orig_date_class=dt.date) -> dt.date:
            return __orig_date_class(*args)


    @staticmethod
    @contextlib.contextmanager
    def _finally_undoing_our_tweaks_to_root_logger() -> Generator[None]:
        root_logger = logging.getLogger()
        initial_level = root_logger.level
        yield
        try:
            for handler in list(root_logger.handlers):
                if handler.name == 'stderr':
                    assert type(handler) is logging.StreamHandler
                    root_logger.removeHandler(handler)
                    handler.close()
        finally:
            root_logger.setLevel(initial_level)


    @pytest.fixture(scope='class')
    def snippet_finder(self) -> Generator[_SnippetFinder]:
        snippet_finder = self._SnippetFinder(certlib.log)
        yield snippet_finder
        snippet_finder.assert_all_snippets_covered()

    @pytest.fixture(scope='class', autouse=True)
    def mark_uninteresting_snippets_as_covered(self, snippet_finder):
        # Testing these code snippets would
        # not be easy and/or very beneficial:
        snippet_finder.lookup(substring='install', syntax_label='bash')
        snippet_finder.lookup(substring='# WRONG (!!!):')
        snippet_finder.lookup(substring='# All WRONG (!!!):')

    @pytest.fixture(scope='class')
    def client_ip_context_var(self) -> contextvars.ContextVar[ipaddress.IPv4Address]:
        default = ipaddress.IPv4Address('192.168.0.123')
        return contextvars.ContextVar('client_ip_context_var', default=default)

    @pytest.fixture
    def myown_package(self, monkeypatch, client_ip_context_var) -> Module:
        myown = Module('myown')
        myown.portal = Module('myown.portal')
        myown.portal.example_module = Module('myown.portal.example_module')
        myown.portal.another_example_module = Module('myown.portal.another_example_module')
        monkeypatch.setattr(
            myown.portal,
            'client_ip_context_var',
            client_ip_context_var,
            raising=False,
        )
        monkeypatch.setitem(sys.modules, 'myown', myown)
        monkeypatch.setitem(sys.modules, 'myown.portal', myown.portal)
        monkeypatch.setitem(
            sys.modules,
            'myown.portal.example_module',
            myown.portal.example_module,
        )
        monkeypatch.setitem(
            sys.modules,
            'myown.portal.another_example_module',
            myown.portal.another_example_module,
        )
        return myown

    @pytest.fixture
    def customized_formatter_cls_module_and_name(self) -> tuple[str, str] | None:
        return None  # Overridden in some tests...

    @pytest.fixture(params=['imperative', 'dictConfig', 'fileConfig'])
    def config_snippet_label(self, request) -> str:
        return request.param

    @pytest.fixture
    def config_snippet(
        self,
        snippet_finder,
        customized_formatter_cls_module_and_name,
        config_snippet_label,
    ) -> str:
        mark_as_covered = not customized_formatter_cls_module_and_name

        match config_snippet_label:
            case 'imperative':
                config_snippet = '\n'.join([
                    snippet_finder.lookup(
                        substring='structured_logs_formatter = StructuredLogsFormatter(',
                        mark_as_covered=mark_as_covered,
                    ),
                    snippet_finder.lookup(
                        substring='# (continuing with the previous example)',
                        mark_as_covered=mark_as_covered,
                    ),
                ])
            case 'dictConfig':
                config_snippet = snippet_finder.lookup(
                    substring='logging.config.dictConfig(logging_configuration_dict)',
                    mark_as_covered=mark_as_covered,
                )
            case 'fileConfig':
                config_snippet = snippet_finder.lookup(
                    substring='class = certlib.log.StructuredLogsFormatter',
                    syntax_label='ini',
                    mark_as_covered=mark_as_covered,
                )
            case _:
                raise AssertionError(f'{config_snippet_label=}')

        if customized_formatter_cls_module_and_name:
            module_name, cls_name = customized_formatter_cls_module_and_name
            config_snippet = config_snippet.replace(certlib.log.__name__, module_name)
            config_snippet = config_snippet.replace(StructuredLogsFormatter.__name__, cls_name)

        return config_snippet

    @pytest.fixture
    def logging_configured_from_config_snippet(
        self,
        monkeypatch,
        tmp_path,
        myown_package,
        config_snippet,
        config_snippet_label,
    ) -> Callable[[], contextlib.AbstractContextManager[str]]:

        if config_snippet_label in ('dictConfig', 'fileConfig'):
            # ^ Both refer to `some_package.faster_replacement_for_json_dumps`.
            some_package = Module('some_package')
            some_package.faster_replacement_for_json_dumps = json.dumps
            monkeypatch.setitem(sys.modules, 'some_package', some_package)

        if config_snippet_label == 'fileConfig':
            def set_up_logging_using_config_snippet():
                config_path = tmp_path / 'test-logging.ini'
                config_path.write_text(config_snippet)
                logging.config.fileConfig(
                    str(config_path),
                    disable_existing_loggers=False,
                )
        else:
            def set_up_logging_using_config_snippet():
                exec(config_snippet, {})

        @contextlib.contextmanager
        def logging_configured_from_config_snippet_impl():
            with self._finally_undoing_our_tweaks_to_root_logger():
                set_up_logging_using_config_snippet()
                yield config_snippet_label

        return logging_configured_from_config_snippet_impl

    @pytest.fixture
    def get_actual_output_list(
        self,
        capsys,
    ) -> Callable[[], list[dict[str, Any]]]:

        def _iter_actual_output_entries():
            errors = []
            stderr_raw = capsys.readouterr().err
            stderr_lines = stderr_raw.splitlines()
            for lineno, line in enumerate(stderr_lines, start=1):
                try:
                    yield json.loads(line)
                except ValueError as exc:
                    errors.append(
                        f'stderr line #{lineno} is not '
                        f'valid JSON ({line=}, {exc=})'
                    )
            if errors:
                raise AssertionError(
                    f'error(s) occurred: {"; ".join(errors)}\n'
                    f'entire stderr output:\n{stderr_raw}'
                )

        def get_actual_output_list_impl():
            return list(_iter_actual_output_entries())

        return get_actual_output_list_impl

    @pytest.fixture
    def expected_utc_formatted_timestamp(self, request) -> str:
        return '2026-02-20 23:14:47.019574Z'  # Overridden in some tests...

    @pytest.fixture
    def commonly_expected_output_items(
        self,
        config_snippet_label,
        expected_utc_formatted_timestamp,
    ) -> dict[str, Any]:
        # (*Note*: also here we neglect actual values of
        # a few items by using `AnyOfType` placeholders.)
        items: dict[str, Any] = {
            'func': '<module>',
            'system': 'MyOwn',
            'component': 'Portal',
            'component_type': 'web',
            'timestamp': expected_utc_formatted_timestamp,
            'client_ip': '192.168.0.123',
            'example_custom_default': 42,
            'example_nano_time': AnyOfType(int),
        }
        if config_snippet_label == 'imperative':
            # Not included in `dictConfig`/`fileConfig` config snippets:
            items['example_local_counter'] = AnyOfType(int)
        return items

    @pytest.fixture
    def extract_and_adjust_json_snippet_items(
        self,
        snippet_finder,
        config_snippet_label,
    ) -> Callable[..., dict[str, Any]]:

        def extract_and_adjust_json_snippet_items_impl(substring):
            snippet = snippet_finder.lookup(substring, syntax_label='json')
            items = json.loads(snippet) | {
                'pid': os.getpid(),
                'py_ver': '.'.join(map(str, sys.version_info)),
            }
            if config_snippet_label in ('dictConfig', 'fileConfig'):
                # Not included in `dictConfig`/`fileConfig` config snippets:
                del items['example_local_counter']
            return items

        return extract_and_adjust_json_snippet_items_impl

    # Overrides the same-named global fixture (defined earlier)
    @pytest.fixture(autouse=True)
    def monkeypatch_relevant_time_functions(
        self,
        monkeypatch,
        expected_utc_formatted_timestamp,
    ):
        without_tz = expected_utc_formatted_timestamp.removesuffix('Z')
        timestamp = dt.datetime.fromisoformat(f'{without_tz}+00:00').timestamp()
        timestamp_ns = 10**3 * int(10**6 * timestamp)
        monkeypatch.setattr(logging, 'time', TimeModuleFakingProxy(timestamp_ns))
        monkeypatch.setattr(dt, 'date', self._DateClassFakingProxy(timestamp))


    def test_user_guide_formatter_old_fashioned_usage_snippet(
        self,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
    ):
        snippet = snippet_finder.lookup(
            substring='logger.warning("Hello %s!", sys.platform)'
        )

        with logging_configured_from_config_snippet():
            exec(snippet, myown_package.portal.example_module.__dict__)

        assert get_actual_output_list() == [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': 'Hello world!',
                'message_base': 'Hello world!',
            },
            {
                **get_output_base(level='WARNING'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': f'Hello {sys.platform}!',
                'message_base': 'Hello %s!',
            },
            {
                **get_output_base(level='ERROR'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': f'Here we have {sys.maxsize:x} and {sys.byteorder!r}.',
                'message_base': 'Here we have %x and %r.',
                'example_stuff': [1, 'foo', False],
                'other_example_item': {'42': AnyOfType(str)},
            },
        ]


    def test_user_guide_formatter_with_xm_usage_snippet(
        self,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
        extract_and_adjust_json_snippet_items,
    ):
        snippet = snippet_finder.lookup(
            substring='logger.warning(xm("Hello {}!", sys.platform))'
        )

        with logging_configured_from_config_snippet():
            exec(snippet, myown_package.portal.example_module.__dict__)

        assert get_actual_output_list() == [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': 'Hello world!',
                'message_base': {
                    'pattern': 'Hello world!',
                },
            },
            {
                **get_output_base(level='WARNING'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': f'Hello {sys.platform}!',
                'message_base': {
                    'pattern': 'Hello {}!',
                },
            },
            {
                **get_output_base(level='ERROR'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': f'Here we have {sys.maxsize:x} and {sys.byteorder!r}.',
                'message_base': {
                    'pattern': 'Here we have {:x} and {!r}.',
                },
                'example_stuff': [1, 'foo', False],
                'other_example_item': {'42': AnyOfType(str)},
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'this': 123,
                'that': '192.168.0.42',
                'there': 'example.com',
                'then': '2026-01-02 03:04:56+00:00',
            },
            last_expected_output := {
                **get_output_base(level='WARNING'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.example_module',
                'message': f"John owns 87.24% of all issues of 'Bajtek' magazine.",
                'message_base': {
                    'pattern': (
                        '{who} owns {fract:.2%} of all issues of {title!r} magazine.'
                    ),
                },
                'who': 'John',
                'fract': 0.87239,
                'title': 'Bajtek',
                'first_issue_date': '1985-09-01',
            },
        ]
        assert last_expected_output == extract_and_adjust_json_snippet_items(
            substring='"logger": "myown.portal.example_module"',
        )


    def test_user_guide_xm_pure_data_snippet(
        self,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
    ):
        snippet = snippet_finder.lookup(
            substring='some_key=["example", "data"]'
        )

        with logging_configured_from_config_snippet():
            exec(snippet, myown_package.portal.another_example_module.__dict__)

        assert get_actual_output_list() == 2 * [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                "some_key": ["example", "data"],
                "another": 42,
                "yet_another": {"abc": 1.0, "qwerty": [True, False]},
            },
        ]


    @pytest.mark.parametrize(
        # (Overriding fixture `expected_utc_formatted_timestamp`...)
        'expected_utc_formatted_timestamp',
        ['2026-02-20 23:53:14.315296Z'],
    )
    def test_user_guide_xm_modern_formatting_snippets(
        self,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
        extract_and_adjust_json_snippet_items,
    ):
        joint_snippet = '\n'.join(
            snippet_finder.lookup(substring)
            for substring in [
                '"Note: {} is {!r} (in {:%Y-%m})"',
                '"Note: {0} is {1!r} (in {2:%Y-%m})"',
                'today=dt.date.today,  # (<- function/method',
                'today=dt.date.today,          # (<- function/method',
            ]
        )

        with logging_configured_from_config_snippet():
            exec(joint_snippet, myown_package.portal.another_example_module.__dict__)

        assert get_actual_output_list() == [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {} is {!r} (in {:%Y-%m})',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {0} is {1!r} (in {2:%Y-%m})',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {} is {val!r} (in {today:%Y-%m})',
                },
                'val': 'Bar',
                'today': '2026-02-21',
            },
            last_expected_output := {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {} is {val!r} (in {today:%Y-%m})',
                },
                'val': 'Bar',
                'today': '2026-02-21',
                'something': 123456789,
                'something_more': [1, 2, 3, 4, True, None, {'5': [6789, 10]}],
            },
        ]
        assert last_expected_output == extract_and_adjust_json_snippet_items(
            substring='"logger": "myown.portal.another_example_module"',
        )


    @pytest.mark.parametrize(
        # (Overriding fixture `customized_formatter_cls_module_and_name`...)
        'customized_formatter_cls_module_and_name',
        [
            (
                'myown.portal.example_module',
                'EstTimezoneOrientedStructuredLogsFormatter',
            )
        ],
    )
    def test_formatter_format_timestamp_snippet(
        self,
        monkeypatch,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
    ):
        snippet = snippet_finder.lookup(
            substring='EstTimezoneOrientedStructuredLogsFormatter'
        )
        logger = logging.getLogger(EXAMPLE_LOGGER_NAME)

        exec(snippet, myown_package.portal.example_module.__dict__)
        with logging_configured_from_config_snippet():
            logger.critical('')

        assert get_actual_output_list() == [
            {
                **get_output_base(level='CRITICAL'),
                **commonly_expected_output_items,
                'func': 'test_formatter_format_timestamp_snippet',
                'timestamp': '2026-02-20 18:14:47.019574 EST',
            },
        ]


    @pytest.mark.parametrize(
        # (Overriding fixture `customized_formatter_cls_module_and_name`...)
        'customized_formatter_cls_module_and_name',
        [
            (
                'myown.portal.another_example_module',
                'MyEnhancedStructuredLogsFormatter',
            )
        ],
    )
    def test_formatter_prepare_value_snippet(
        self,
        monkeypatch,
        snippet_finder,
        myown_package,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
    ):
        snippet = snippet_finder.lookup(
            substring='MyEnhancedStructuredLogsFormatter'
        )
        # Prepare module `attrs` with necessary stubs:
        attrs_module = Module('attrs')
        attrs_module.has = lambda obj_type: obj_type is type(sentinel.ABC)
        attrs_module.asdict = lambda obj: ExampleNamedTuple(str(obj), b'foo')
        monkeypatch.setitem(sys.modules, 'attrs', attrs_module)
        logger = logging.getLogger(EXAMPLE_LOGGER_NAME)

        exec(snippet, myown_package.portal.another_example_module.__dict__)
        with logging_configured_from_config_snippet():
            logger.info(xm(
                '* {some_value} * {some_collection} *',
                some_value=sentinel.EXAMPLE,
                some_collection={
                    'sub': [{
                        '1': sentinel.spam,
                        24: sentinel.Bar,
                    }],
                },
            ))

        assert get_actual_output_list() == [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'func': 'test_formatter_prepare_value_snippet',
                'message': (
                    "* sentinel.EXAMPLE * "
                    "{'sub': [{'1': sentinel.spam, 24: sentinel.Bar}]} *"
                ),
                'message_base': {
                    'pattern': '* {some_value} * {some_collection} *',
                },
                'some_value': {
                    'label': 'sentinel.EXAMPLE',
                    'blob': "b'foo'",
                },
                'some_collection': {
                    'sub': [{
                        '1': {
                            'label': 'sentinel.spam',
                            'blob': "b'foo'",
                        },
                        '24': {
                            'label': 'sentinel.Bar',
                            'blob': "b'foo'",
                        },
                    }],
                },
            },
        ]


    def test_xm_constructor_snippets(
        self,
        snippet_finder,
        logging_configured_from_config_snippet,
        get_actual_output_list,
        commonly_expected_output_items,
    ):
        main_snippet = snippet_finder.lookup(
            substring='logging.warning(xm('
        )
        joint_extra_snippets = '\n'.join(
            snippet_finder.lookup(substring)
            for substring in [
                ".info(xm('Foo', stack_info=True, stacklevel=2))",
                ".info(xm('{}, {} and {}', 'Athos', 'Porthos', 'Aramis'))",
                ".info(xm('answer: {}'))",
            ]
        )

        with logging_configured_from_config_snippet():
            exec(main_snippet, {})
            exec(joint_extra_snippets, {
                'xm': xm,
                'logger': logging.getLogger(EXAMPLE_LOGGER_NAME),
            })

        assert get_actual_output_list() == [
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'root',
                'message': f'Hello {sys.platform}!',
                'message_base': {
                    'pattern': 'Hello {}!',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'root',
                'message': f'Maxsize is {sys.maxsize:x}',
                'message_base': {
                    'pattern': 'Maxsize is {maxsize:x}',
                },
                'maxsize': sys.maxsize,
            },
            {
                **get_output_base(level='WARNING'),
                **commonly_expected_output_items,
                'logger': 'root',
                'connection_count': 42,
                'client_ip': '192.168.0.121',
                'client_ip_': '192.168.0.123',  # [sic!]
                'local_time': AnyOfType(str),
                'payload_hash': (
                    '1bf982a3e009728aad3077fdd6977a7f'
                    '53c92c04c3cec6b60906e58e846e42ce'
                ),
            },
            *(2 * [
                {
                    **get_output_base(level='INFO'),
                    **commonly_expected_output_items,
                    'logger': EXAMPLE_LOGGER_NAME,
                    'message': 'Foo',
                    'message_base': {
                        'pattern': 'Foo',
                    },
                    'stack_info': AnyOfType(str),
                },
                {
                    **get_output_base(level='INFO'),
                    **commonly_expected_output_items,
                    'func': 'test_xm_constructor_snippets',  # [sic!]
                    'logger': EXAMPLE_LOGGER_NAME,
                    'message': 'Foo',
                    'message_base': {
                        'pattern': 'Foo',
                    },
                },
                {
                    **get_output_base(level='INFO'),
                    **commonly_expected_output_items,
                    'func': 'test_xm_constructor_snippets',  # [sic!]
                    'logger': EXAMPLE_LOGGER_NAME,
                    'message': 'Foo',
                    'message_base': {
                        'pattern': 'Foo',
                    },
                    'stack_info': AnyOfType(str),
                },
            ]),
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': EXAMPLE_LOGGER_NAME,
                'message': 'Athos, Porthos and Aramis',
                'message_base': {
                    'pattern': '{}, {} and {}',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': EXAMPLE_LOGGER_NAME,
                'message': 'answer: 42',
                'message_base': {
                    'pattern': 'answer: {}',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': EXAMPLE_LOGGER_NAME,
                'message': 'answer: {}',
                'message_base': {
                    'pattern': 'answer: {}',
                },
            },
        ]


    readme_path = project_root_path / 'README.md'

    @pytest.mark.skipif(
        not readme_path.exists(),
        reason=f'file {str(readme_path)!r} not found',
    )
    def test_readme_snippets(
        self,
        monkeypatch,
        client_ip_context_var,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        snippet_finder = self._SnippetFinder(self.readme_path)
        # Prepare the necessary modules:
        myexample = Module('myexample')
        myexample.lib = Module('myexample.lib')
        myexample.myapi = Module('myexample.myapi')
        monkeypatch.setattr(
            myexample.myapi,
            'client_ip_context_var',
            client_ip_context_var,
            raising=False,
        )
        monkeypatch.setitem(sys.modules, 'myexample', myexample)
        monkeypatch.setitem(sys.modules, 'myexample.lib', myexample.lib)
        monkeypatch.setitem(sys.modules, 'myexample.myapi', myexample.myapi)

        with self._finally_undoing_our_tweaks_to_root_logger():
            exec(
                snippet_finder.lookup(substring='logging.config.dictConfig'),
                myexample.__dict__,
            )
            exec(
                snippet_finder.lookup(substring='from certlib.log import xm'),
                myexample.lib.__dict__,
            )
            # Let's test the functions defined in the second snippet...
            myexample.lib.example_with_text_message_formatting(
                city='Warsaw',
                humidity=0.191,
            )
            try:
                1 / 0
            except ZeroDivisionError:
                myexample.lib.example_with_text_message_formatting(
                    city='Paris',
                    humidity=0.6968,
                    error_summary="someone divided by zero again",
                )
                myexample.lib.example_with_no_text(
                    temperature=17,
                    pressure=1018,
                    debug_data_dict=deepcopy(EXAMPLE_CUSTOM_ITEMS),
                    calm=False,
                )
            logging.getLogger().setLevel(logging.DEBUG)
            myexample.lib.example_with_no_text(
                temperature=17,
                pressure=1018,
                debug_data_dict=deepcopy(EXAMPLE_CUSTOM_ITEMS),
            )

        snippet_finder.assert_all_snippets_covered()
        readme_specific_expected_output_items = {
            'client_ip': '192.168.0.123',
            'nano_time': AnyOfType(int),
            'system': 'MyExample',
            'component': 'MyAPI',
            'component_type': 'web',
            'timestamp': expected_utc_formatted_timestamp,
        }
        assert get_actual_output_list() == [
            {
                **get_output_base(level='WARNING'),
                **readme_specific_expected_output_items,
                'func': 'example_with_text_message_formatting',
                'logger': 'myexample.lib',
                'message': 'Humidity in Warsaw is 19.1%',
                'message_base': {
                    'pattern': 'Humidity in {} is {:.1%}',
                },
            },
            {
                **get_output_base(level='INFO'),
                **readme_specific_expected_output_items,
                'func': 'example_with_text_message_formatting',
                'logger': 'myexample.lib',
                'message': 'Today is day #052 of the year 2026',
                'message_base': {
                    'pattern': 'Today is day #{today:%j} of the year {today:%Y}',
                },
                'today': '2026-02-21',
                'some_extra_item': 42,
                'other_arbitrary_stuff': {'foo': [
                    {'my-ip': '192.168.0.1'},
                    '12:59:00',
                ]},
            },
            {
                **get_output_base(level='ERROR'),
                **readme_specific_expected_output_items,
                'func': 'test_readme_snippets',  # [sic!]
                'logger': 'myexample.lib',
                'message': "An error occurred: 'someone divided by zero again'",
                'message_base': {
                    'pattern': 'An error occurred: {!r}',
                },
                'exc_info': {
                    'exc_type': 'ZeroDivisionError',
                    'args': [AnyOfType(str)],
                },
                'exc_text': AnyOfType(str),
                'stack_info': AnyOfType(str),
            },
            {
                **get_output_base(level='WARNING'),
                **readme_specific_expected_output_items,
                'func': 'example_with_text_message_formatting',
                'logger': 'myexample.lib',
                'message': 'Humidity in Paris is 69.7%',
                'message_base': {
                    'pattern': 'Humidity in {} is {:.1%}',
                },
            },
            {
                **get_output_base(level='INFO'),
                **readme_specific_expected_output_items,
                'func': 'example_with_text_message_formatting',
                'logger': 'myexample.lib',
                'message': 'Today is day #052 of the year 2026',
                'message_base': {
                    'pattern': 'Today is day #{today:%j} of the year {today:%Y}',
                },
                'today': '2026-02-21',
                'some_extra_item': 42,
                'other_arbitrary_stuff': {'foo': [
                    {'my-ip': '192.168.0.1'},
                    '12:59:00',
                ]},
            },
            {
                **get_output_base(level='ERROR'),
                **readme_specific_expected_output_items,
                'func': 'test_readme_snippets',  # [sic!]
                'logger': 'myexample.lib',
                'temperature': 17,
                'pressure': 1018,
                'exc_info': {
                    'exc_type': 'ZeroDivisionError',
                    'args': [AnyOfType(str)],
                },
                'exc_text': AnyOfType(str),
                'stack_info': AnyOfType(str),
            },
            {
                **get_output_base(level='INFO'),
                **readme_specific_expected_output_items,
                'func': 'example_with_no_text',
                'logger': 'myexample.lib',
                'temperature': 17,
                'pressure': 1018,
            },
            {
                **get_output_base(level='DEBUG'),
                **readme_specific_expected_output_items,
                'func': 'example_with_no_text',
                'logger': 'myexample.lib',
                **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
            },
        ]

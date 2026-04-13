# Copyright (c) 2026, CERT Polska. All rights reserved.
#
# This file's content is free software; you can redistribute and/or
# modify it under the terms of the *BSD 3-Clause "New" or "Revised"
# License* (see the `LICENSE.txt` file in the source code repository:
# https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt).

from __future__ import annotations

import dataclasses
import datetime as dt
import decimal
import fractions
import functools
import hashlib
import ipaddress
import json
import logging
import math
import os
import pathlib
import sys
import time as time_module
import uuid
from collections.abc import (
    Callable,
    Generator,
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

sys.path.insert(0, str(
    pathlib.Path(__file__).resolve(strict=True).parent.parent / 'src'
))
from certlib.log import (
    StructuredLogsFormatter,
    _clear_auto_makers_and_internal_record_hooks_related_global_state,
    make_constant_value_provider,
    xm,
)


#
# Test helpers and example data
#


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

PY_3_11_OR_NEWER = sys.version_info[:2] >= (3, 11)


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


class LoggingTimeModuleFakingProxy:

    def __getattribute__(self, name) -> Any:
        if name == 'time':
            return lambda: EXAMPLE_TIMESTAMP_IN_NANOSECONDS / 10**9
        if name == 'time_ns':
            return lambda: EXAMPLE_TIMESTAMP_IN_NANOSECONDS
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

    def emit(self, record) -> None:
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

    def make_base_defaults(self) -> Mapping[str, object]:
        return dict(super().make_base_defaults()) | {
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
            'xyz': 'abc',
            'zero': ['a default TO BE OVERRIDDEN...'],
        }

    def make_base_auto_makers(self) -> Mapping[str, str | Callable[[], object]]:
        return dict(super().make_base_auto_makers()) | {
            'component': make_constant_value_provider(EXAMPLE_COMPONENT),
            'zero': make_constant_value_provider(0),
        }

    def get_output_keys_required_to_be_included_in_defaults_or_auto_makers(self) -> Set[str]:
        return frozenset(
            super().get_output_keys_required_to_be_included_in_defaults_or_auto_makers()
        ) | {'zero'}

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

    def __new__(cls, value: object) -> ConstantValueAutoMaker:
        name = cls._get_name(value)
        instance = getattr(HELPER_IMPORTABLE_MODULE, name, None)
        if instance is None:
            instance = super().__new__(cls)
            instance._value = value
            instance.__name__ = instance.__qualname__ = name      # <- Just for completeness :)
            instance.__module__ = HELPER_IMPORTABLE_MODULE_NAME   # <- Just for completeness :)
            setattr(HELPER_IMPORTABLE_MODULE, name, instance)
        return instance

    @classmethod
    def _get_name(cls, value: object) -> str:
        value_repr_hash = hashlib.sha224(ascii(value).encode()).hexdigest()
        return f'_{cls.__name__}__name___{value_repr_hash}'

    def __call__(self) -> Any:
        return self._value

    def get_importable_dotted_name(self) -> str:
        return f'{HELPER_IMPORTABLE_MODULE_NAME}.{self.__name__}'

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
# Module-global fixtures
#


@pytest.fixture(autouse=True)
def _ensure_initial_log_record_factory_is_restored():
    initial = logging.getLogRecordFactory()
    yield
    logging.setLogRecordFactory(initial)


@pytest.fixture(autouse=True)
def _monkeypatch_to_fake_relevant_time_functions(monkeypatch):
    monkeypatch.setattr(logging, 'time', LoggingTimeModuleFakingProxy())


@pytest.fixture(autouse=True)
def _ensure_module_global_internal_state_is_cleaned_up():
    _clear_auto_makers_and_internal_record_hooks_related_global_state()
    yield
    _clear_auto_makers_and_internal_record_hooks_related_global_state()


#
# Actual tests (with their local fixtures)
#


class TestStructuredLogsFormatter:  # noqa

    @pytest.fixture(params=[StructuredLogsFormatter])
    def formatter_factory(self, request) -> Callable[..., StructuredLogsFormatter]:
        return request.param

    @pytest.fixture(params=[
        dict(
            defaults={
                'component_type': EXAMPLE_COMPONENT_TYPE,
                'system': EXAMPLE_SYSTEM,
            },
            auto_makers={
                'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
            }
        ),
    ])
    def formatter_init_kwargs(self, request) -> Generator[dict[str, Any]]:
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
        log.propagate = False
        log.setLevel(logging.DEBUG)
        log.addHandler(log_handler)
        yield log
        log.removeHandler(log_handler)

    @pytest.fixture
    def example_custom_items(self):
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
            'message_base': "Let's log this: %s=%r, %s=%.6f",
            'message': "Let's log this: foo='bar', π=3.141593",
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {}={:.6f}",
            },
            'message': "Let's log this: foo='bar', π=3.141593",
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'message_base': {
                'pattern': "Let's log this: {0}={1!r}, {2}={3:.6f}",
            },
            'message': "Let's log this: foo='bar', π=3.141593",
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            },
            'message': "Let's log this: foo='bar', π=3.141593",
            'const_symbol': 'π',      # <- Note extra item
            'const_value': math.pi,   # <- Note extra item
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'message_base': {
                'pattern': "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            },
            'message': "Let's log this: foo='bar', π=3.141593",
            'const_symbol': 'π',                      # <- Note extra item
            'const_value': math.pi,                   # <- Note extra item
            **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,   # <- Note extra items not used in message
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
                    'message_base': 'Error occurred!',
                    'message': 'Error occurred!',
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
                    'message_base': 'Error occurred! %d',
                    'message': 'Error occurred! 123',
                },
            ),
            (
                lambda logger: logger.debug(
                    xm('Error occurred!'),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='DEBUG'),
                    'message_base': {'pattern': 'Error occurred!'},
                    'message': 'Error occurred!',
                },
            ),
            (
                lambda logger: logger.info(
                    xm('Error occurred!', exc_info=True),
                ),
                {
                    **get_output_base(level='INFO'),
                    'message_base': {'pattern': 'Error occurred!'},
                    'message': 'Error occurred!',
                },
            ),
            (
                lambda logger: logger.warning(
                    xm('Error occurred! {n}', n=123),
                    exc_info=True,
                ),
                {
                    **get_output_base(level='WARNING'),
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'message': 'Error occurred! 123',
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.error(
                    xm('Error occurred! {n}', n=123, exc_info=True)
                ),
                {
                    **get_output_base(level='ERROR'),
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'message': 'Error occurred! 123',
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
        except BaseException:  # noqa
            logger_method_call(logger)

        assert log_handler.output_list == [{
            **expected_output_base,
            'exc_info': expected_exc_info,
            'exc_text': AnyOfType(str),
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
                    'message_base': 'Some happened!',
                    'message': 'Some happened!',
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
                    'message_base': 'Some happened! %d',
                    'message': 'Some happened! 123',
                },
            ),
            (
                lambda logger: logger.warning(
                    xm('Some happened!'),
                    stack_info=True,
                ),
                {
                    **get_output_base(level='WARNING'),
                    'message_base': {'pattern': 'Some happened!'},
                    'message': 'Some happened!',
                },
            ),
            (
                lambda logger: logger.error(
                    xm('Some happened!', stack_info=True),
                ),
                {
                    **get_output_base(level='ERROR'),
                    'message_base': {'pattern': 'Some happened!'},
                    'message': 'Some happened!',
                },
            ),
            (
                lambda logger: logger.critical(
                    xm('Some happened! {n}', n=123),
                    stack_info=True,
                ),
                {
                    **get_output_base(level='CRITICAL'),
                    'message_base': {'pattern': 'Some happened! {n}'},
                    'message': 'Some happened! 123',
                    'n': 123,
                },
            ),
            (
                lambda logger: logger.debug(
                    xm('Some happened! {n}', n=123, stack_info=True)
                ),
                {
                    **get_output_base(level='DEBUG'),
                    'message_base': {'pattern': 'Some happened! {n}'},
                    'message': 'Some happened! 123',
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
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'system': EXAMPLE_SYSTEM,
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
                        'component_type': 'a default TO BE OVERRIDDEN...',
                        'system': EXAMPLE_SYSTEM,
                        'blah_blah_blah': 2222,
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {0}, {1!r}, {2:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'asctime': 'What time is it?',
                        'bar': 'spam',
                        'baz': 42,
                        'foo': 'Foo',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'spam': 'ham',
                        'system': 'Śmystem',
                        'timestamp': 'Śmajstamp',                                     # [sic!]
                        'timestamp_': 'And now for something completely different!',  # [sic!]
                        'timestamp__': EXAMPLE_TIMESTAMP_FORMATTED,                   # [sic!]
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {{}}',
                        },
                        'message': 'Example message - {}',   # [sic!]
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message_base': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - %(foo)s, %(bar)r, %(baz)04d, %%',
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
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {:04}, {{}}',
                        },
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {}, {!r}, {:04}, {{}}',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='WARNING'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        # Value of 'message' kept raw (*not* formatted) [!]
                        'message': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
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
                        'baz': 42,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        'baz': 42,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
                        'something_else': [{'42': 42}],
                        # No 'system' [sic!] (the default has been masked by a void value)
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        'bar': 2.0,
                        'baz': 3,    # [sic!]
                        'component': EXAMPLE_COMPONENT,   # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'message': "Example message - Foo, 'spam', None, {}",   # [sic!]
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz}, {{}}',
                        },
                        'something_else': [{'42': 42}],
                        'system': 'S-2',   # [sic!]
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'bar': 2.0,
                        'baz': 42,    # [sic!]
                        'baz_': 3,    # [sic!]
                        'component': EXAMPLE_COMPONENT,   # [sic!]
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'message': "Example message - Foo, 'spam', 0042, {}",
                        'message_base': {
                            'pattern': 'Example message - {}, {!r}, {baz:04}, {{}}',
                        },
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': 'abc',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='INFO'),
                        'func': '<lambda>',
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'message': "Example message - Foo, 'spam', 0042, %",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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
                        'message_base': {
                            'pattern': 'Example message - {foo}, {bar!r}, {baz:04}, {{}}',
                        },
                        'message': "Example message - Foo, 'spam', 0042, {}",
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

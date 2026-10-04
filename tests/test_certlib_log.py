# Copyright (c) 2026, CERT Polska. All rights reserved.
#
# This file's content is free software; you can redistribute and/or
# modify it under the terms of the *BSD 3-Clause "New" or "Revised"
# License* (see the `LICENSE.txt` file in the source code repository:
# https://github.com/CERT-Polska/certlib-log/blob/main/LICENSE.txt).

# mypy: disable_error_code = "attr-defined, func-returns-value, no-any-return, no-untyped-call, no-untyped-def, unused-ignore"

from __future__ import annotations

import ast
import collections
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
import random
import re
import sys
import textwrap
import time as time_module
import types
import uuid
from collections.abc import (
    Callable,
    Generator,
    Hashable,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
    Set,
)
from copy import deepcopy
from enum import (
    Enum,
    auto,
)
from types import (
    FunctionType as Function,
    ModuleType as Module,
    SimpleNamespace,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NamedTuple,
    TypeVar,
)
if TYPE_CHECKING:
    from typing import Self   # <- Availability at runtime: Python 3.11+ only
from unittest.mock import (
    Mock,
    call,
    sentinel,
)

import pytest

project_root_path = pathlib.Path(__file__).resolve(strict=True).parent.parent
sys.path.insert(0, str(project_root_path / 'src'))
import certlib.log
from certlib.log import (
    STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
    StructuredLogsFormatter,
    _clear_auto_makers_and_internal_record_hooks_related_global_state,
    make_constant_value_provider,
    register_log_record_attr_auto_maker,
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

EMPTY_MAPPING: Mapping[Any, Any] = types.MappingProxyType({})

EXAMPLE_LOGGER_NAME = 'some.example.logger'
EXAMPLE_SYSTEM = 'My Example System'
EXAMPLE_COMPONENT = 'some_example_parser'
EXAMPLE_COMPONENT_TYPE = 'parser'
EXAMPLE_PY_VER = '.'.join(map(str, (sys.version_info or ())))
EXAMPLE_SCRIPT_ARGS = ('prog', 'arg1', 'arg2')

EXAMPLE_TIMESTAMP_IN_NANOSECONDS = 1_770_903_450_848_759_680
EXAMPLE_TIMESTAMP_FORMATTED = '2026-02-12 13:37:30.848760Z'
EXAMPLE_TIMESTAMP_DT = dt.datetime.fromisoformat(
    EXAMPLE_TIMESTAMP_FORMATTED.removesuffix('Z') + '+00:00'
)
assert EXAMPLE_TIMESTAMP_DT == dt.datetime.fromtimestamp(
    EXAMPLE_TIMESTAMP_IN_NANOSECONDS / 10**9,
    dt.timezone.utc,
)
assert EXAMPLE_TIMESTAMP_DT.strftime('%Y-%m-%d %H:%M:%S.%f') + 'Z' == (
    EXAMPLE_TIMESTAMP_FORMATTED
)


class ExampleNonDictMutableMapping(MutableMapping[Any, Any]):
    def __init__(self, items=(), /, **kw): self._d = dict(items, **kw)
    def __len__(self): return len(self._d)
    def __iter__(self): return iter(self._d)
    def __getitem__(self, key): return self._d[key]
    def __setitem__(self, key, val): self._d[key] = val
    def __delitem__(self, key): del self._d[key]

class ExampleSomethingWithCustomStrAndRepr:
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
    'SomeSpam': ExampleSomethingWithCustomStrAndRepr(),
    'my enum member...': ExampleEnum.FOO,
    'IPv4 address': ipaddress.IPv4Address('10.20.30.40'),
    'simple namespace': SimpleNamespace(a=42, b=[1, 2, 3]),
    'my_subdict': {
        (1, 2): (1, (1, (1, {1: 0.0, float('inf'): float('inf')}))),
        ExampleSomethingWithCustomStrAndRepr(): ExampleSomethingWithCustomStrAndRepr(),
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
            float('nan'),
            -float('inf'),
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
        'other stuff': ExampleNonDictMutableMapping({
            'my other enum member': ExampleEnum.BAR,
            'ipv4address': ipaddress.IPv4Address('192.168.0.1'),
            'ipv4iface': ipaddress.IPv4Interface('192.168.0.1/24'),
            'ipv4network': ipaddress.IPv4Network('192.168.0.0/24'),
            'ipv6address': ipaddress.IPv6Address('2001:0db8:85a3:0000:0000:8a2e:0370:7334'),
            'ipv6iface': ipaddress.IPv6Interface('2001:0db8:85a3:0000:0000:8a2e:0370:7334/124'),
            'ipv6network': ipaddress.IPv6Network('2001:0db8:85a3:0000:0000:8a2e:0370:7330/124'),
            'uuid': uuid.UUID('12345678-1234-5678-1234-567812345678'),
            'ns': SimpleNamespace(a=42, sub=SimpleNamespace(c=None)),
        }),
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
    'simple namespace': {'a': 42, 'b': [1, 2, 3]},
    'my_subdict': {
        '(1, 2)': [1, [1, [1, {'1': 0.0, 'inf': 'inf'}]]],
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
            'nan',
            '-inf',
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
            'ns': {'a': 42, 'sub': {'c': None}},
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


class FormatterInitIgnoredRedundantStandardArgumentsVariant(Enum):
    NONE = 'no redundant std Formatter.__init__() arguments'
    POSITIONAL = 'redundant std Formatter.__init__() arguments: defaults as positional ones'
    KEYWORD = 'redundant std Formatter.__init__() arguments: defaults as keyword ones'
    MIXED = "redundant std Formatter.__init__() arguments: defaults as positional/keyword ones"


class ListLogHandler(logging.Handler):

    def __init__(self):
        super().__init__()
        self.serialized_output_list: list[str] = []
        self.deserializer: Callable[[str], dict[str, Any]] = json.loads

    def emit(self, record):
        serialized_output: str = self.format(record)
        self.serialized_output_list.append(serialized_output)

    @property
    def output_list(self) -> list[dict[str, Any]]:
        return list(map(self.deserializer, self.serialized_output_list))

    @property
    def last_output(self) -> dict[str, Any]:
        if self.output_list:
            return self.output_list[-1]
        raise AssertionError(f'no log entry emitted by {self!r}')


class ExampleSubclassOfStructuredLogsFormatter(StructuredLogsFormatter):

    def make_base_defaults(self) -> Mapping[str, object]:
        return dict(super().make_base_defaults()) | {
            'system': EXAMPLE_SYSTEM,
            'component_type': EXAMPLE_COMPONENT_TYPE,
            'xyz': dt.date(2026, 4, 27),
            'zero': ['default value of `zero` item...'],
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
        if lemon := output_data.pop('lemon', None):
            output_data['lime'] = lemon
        return output_data

    def prepare_value(self, value: object, **kwargs) -> Any:
        prepared = super().prepare_value(value, **kwargs)
        if isinstance(prepared, dict):
            prepared = dict(sorted(prepared.items()))
        elif prepared == ['mar', 'chew', 'ka']:
            prepared = 'Marchewka'
        return prepared

    def prepare_submapping_key(self, key: object) -> str:
        if key in [('pom', 'i', 'dor'), ('po', 'mid', 'or')]:
            return 'Pomidor'
        return super().prepare_submapping_key(key)

    def serialize_prepared_output_data(self, output_data: dict[str, Any]) -> str:
        output_data = dict(sorted(output_data.items()))
        return super().serialize_prepared_output_data(output_data)


def make_StructuredLogsFormatter_subclass(   # noqa
    *,
    extra_accepted_kwarg_names: Set[str] = frozenset(),

    base_defaults: Mapping[str, object] | None = None,
    base_auto_makers: Mapping[str, str | Callable[[], object]] | None = None,
    base_record_attr_to_output_key: Mapping[str, str | None] | None = None,

    format_timestamp_kwargs: Mapping[str, Any] | None = None,
    prepare_value_kwargs: Mapping[str, Any] | None = None,

    prepare_submapping_key: Callable[[object], str] | None = None,
    before_get_prepared_output_data: (
        Callable[[logging.LogRecord], logging.LogRecord] | None
    ) = None,
    before_serialize_prepared_output_data: (
        Callable[[dict[str, Any]], dict[str, Any]] | None
    ) = None,
) -> type[StructuredLogsFormatter]:

    def _without_extra_accepted_kwargs(
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            name: value
            for name, value in kwargs.items()
            if name not in extra_accepted_kwarg_names
        }

    def _literal_evaluated_or_none(s: str) -> object:
        try:
            return ast.literal_eval(s)
        except Exception:   # noqa
            return None

    class cls(StructuredLogsFormatter):   # noqa
        if extra_accepted_kwarg_names:
            def __init__(self, *args, **kwargs):
                truthy_arg = args[0] if (args and args[0]) else None
                adjusted_arg: Any
                if isinstance(truthy_arg, Mapping):
                    adjusted_arg = _without_extra_accepted_kwargs(truthy_arg)
                    args = (adjusted_arg,) + args[1:]
                elif isinstance(truthy_arg, str):
                    evaluated_arg = _literal_evaluated_or_none(truthy_arg)
                    if isinstance(evaluated_arg, Mapping):
                        adjusted_arg = repr(_without_extra_accepted_kwargs(evaluated_arg))
                        args = (adjusted_arg,) + args[1:]
                else:
                    kwargs = _without_extra_accepted_kwargs(kwargs)
                super().__init__(*args, **kwargs)

        if base_defaults is not None:
            def make_base_defaults(self):
                return base_defaults

        if base_auto_makers is not None:
            def make_base_auto_makers(self):
                return base_auto_makers

        if base_record_attr_to_output_key is not None:
            def make_base_record_attr_to_output_key(self):
                return base_record_attr_to_output_key

        if format_timestamp_kwargs is not None:
            def format_timestamp(self, record, **call_kwargs):
                kwargs = {**format_timestamp_kwargs, **call_kwargs}
                return super().format_timestamp(record, **kwargs)

        if prepare_value_kwargs is not None:
            def prepare_value(self, value, **call_kwargs):
                kwargs = {**prepare_value_kwargs, **call_kwargs}
                return super().prepare_value(value, **kwargs)

        if before_get_prepared_output_data is not None:
            def get_prepared_output_data(self, record):
                return super().get_prepared_output_data(
                    before_get_prepared_output_data(record)
                )

        if before_serialize_prepared_output_data is not None:
            def serialize_prepared_output_data(self, output_data):
                return super().serialize_prepared_output_data(
                    before_serialize_prepared_output_data(output_data)
                )

    if prepare_submapping_key is not None:
        cls.prepare_submapping_key = staticmethod(   # type: ignore[method-assign]
            prepare_submapping_key                   # type: ignore[assignment]
        )

    return cls


class ImportableWrapper:

    # An object wrapper with a few useful attributes, in particular one
    # that provides an *importable dotted name* (*dotted path*) always
    # pointing to `self`; and with implementations of special methods:
    # `__repr__()` -- returns an `ast.literal_eval()`-evaluable string
    # that represents that *importable dotted name* (thanks to this, it
    # is easier to write and parametrize tests for certain `certlib.log`
    # APIs that allow to specify some objects both directly and by their
    # *importable dotted names*...); `__copy__()` and `__deepcopy__()`
    # -- each of which just returns `self`.

    wrapped_object: object

    def __new__(cls, wrapped_object: object, /) -> Self:
        inst = super().__new__(cls)
        inst.wrapped_object = wrapped_object
        setattr(HELPER_IMPORTABLE_MODULE, inst.importable_dotted_name_unique_tip, inst)
        return inst

    @functools.cached_property
    def importable_dotted_name(self) -> str:
        return f'{HELPER_IMPORTABLE_MODULE_NAME}.{self.importable_dotted_name_unique_tip}'

    @functools.cached_property
    def importable_dotted_name_unique_tip(self) -> str:
        self_id = id(self)
        id_based_suffix = f'{abs(self_id):x}' + ('p' if self_id >= 0 else 'n')
        return f'_{type(self).__name__}_by_id_{id_based_suffix}'

    def __repr__(self) -> str:
        # An `ast.literal_eval()`-evaluable representation of
        # the string assigned to `self.importable_dotted_name`.
        return repr(self.importable_dotted_name)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


class ConstantValueAutoMaker(ImportableWrapper):

    # A helper somewhat similar to `make_constant_value_provider()`
    # but equipped with extra stuff provided by the base class
    # `ImportableWrapper`, plus a mechanism that guarantees that
    # only one instance will ever be created per wrapped value.

    __value_to_inst: dict[Hashable, Self] = {}

    def __new__(cls, value: Hashable) -> Self:
        inst = cls.__value_to_inst.get(value)
        if inst is None:
            inst = cls.__value_to_inst[value] = super().__new__(cls, value)
        return inst

    def __call__(self) -> Hashable:
        return self.wrapped_object


class CallableImportableWrapper(ImportableWrapper):

    wrapped_object: Callable[..., Any]

    def __call__(self, *args, **kwargs) -> Any:
        return self.wrapped_object(*args, **kwargs)


class ExampleConfCorrector(CallableImportableWrapper):

    def __new__(
        cls,
        *,
        defaults: Mapping[str, Any] | Any = EMPTY_MAPPING,
        auto_makers: Mapping[str, Any] | Any  = EMPTY_MAPPING,
        base_record_attr_to_output_key: Mapping[str, Any] | Any  = EMPTY_MAPPING,
        serializer: Any | None = None,
        required_keys: Set[str] = frozenset(),
        _prng=random.Random('** arbitrary deterministic seed **'),
    ) -> Self:

        def _get_updated(orig, changes):
            updated: dict[str, Any]
            if changes is sentinel.DELETE_ALL:
                updated = {}
            else:
                updated = deepcopy(dict(orig))
                for key, val in changes.items():
                    if val == sentinel.DELETE:
                        del updated[key]
                    else:
                        updated[key] = val
            if _prng.choice([True, False]):
                # (Example of non-dict mapping)
                return types.MappingProxyType(updated)
            return updated

        def conf_corrector_impl(conf):
            corrected_conf: dict[str, Any] = {
                'defaults': _get_updated(
                    conf['defaults'],
                    defaults,
                ),
                'auto_makers': _get_updated(
                    conf['auto_makers'],
                    auto_makers,
                ),
                'base_record_attr_to_output_key': _get_updated(
                    conf['base_record_attr_to_output_key'],
                    base_record_attr_to_output_key,
                ),
                'serializer': (
                    conf['serializer'] if serializer is None
                    else serializer
                ),
            }
            all_required_keys = required_keys | set(
                conf['conf_corrector_params'].get('extra_required_keys', ())
            )
            all_provided_keys = (
                corrected_conf['defaults'].keys()
                | corrected_conf['auto_makers'].keys()
            )
            missing_keys = all_required_keys - all_provided_keys
            if missing_keys:
                raise ValueError(f'{missing_keys=}')
            return corrected_conf

        return super().__new__(cls, conf_corrector_impl)


example_serializer = CallableImportableWrapper(
    functools.partial(
        json.dumps,
        indent=4,
        sort_keys=True,
    ),
)


@dataclasses.dataclass(frozen=True)
class LogCase:
    logger_method_call: Callable[[logging.Logger], None]
    expected_output_base: Mapping[str, Any]


@dataclasses.dataclass(frozen=True)
class SpecificLogCase:
    logger_method_call: Callable[[logging.Logger], None]
    expected_output: Mapping[str, Any]


_ExceptionT = TypeVar('_ExceptionT', bound=BaseException)

def exc_maker(
    factory: Callable[..., _ExceptionT],
    *,
    args: Sequence[Any],
    instance_attrs: Mapping[str, Any] = EMPTY_MAPPING,
    notes: Sequence[str] = (),
) -> Callable[[], _ExceptionT]:

    def make_exc() -> _ExceptionT:
        exc = factory(*args)
        exc.__dict__.update(instance_attrs)
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
    timestamp = EXAMPLE_TIMESTAMP_FORMATTED

    return {
        'func': AnyOfType(str),
        'level': level,
        'levelno': levelno,
        'lineno': AnyOfType(int),
        'logger': logger,
        'pid': pid,
        'process_name': AnyOfType(str),
        'src': AnyOfType(str),
        'thread_id': AnyOfType(int),
        'thread_name': AnyOfType(str),
        'timestamp': timestamp,
    }


#
# Module-wide *autouse* fixtures
#


@pytest.fixture(scope='session', autouse=True)
def seen_formatter_auto_made_record_attr_prefixes() -> Generator[list[str]]:
    seen: list[str] = []
    yield seen
    # Check whether each per-instance prefix is unique:
    assert sorted(seen) == sorted(set(seen))


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

    # (This fixture is overridden for some tests...)
    @pytest.fixture(params=[
        StructuredLogsFormatter,

        make_StructuredLogsFormatter_subclass(
            extra_accepted_kwarg_names={'some_unused'},
            # (Examples of non-dict mappings)
            base_defaults=ExampleNonDictMutableMapping({
                # (See `formatter_init_kwargs` fixture's params...)
                'system': ['...to-be-overridden...'],
            }),
            base_auto_makers=types.MappingProxyType({
                **StructuredLogsFormatter.make_base_auto_makers(sentinel.self),
                'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
            }),
            base_record_attr_to_output_key=collections.ChainMap(
                {'some_unused_rec_attr': 'respective_unused_output_key'},
                dict(STANDARD_RECORD_ATTR_TO_OUTPUT_KEY),
            ),
        ),
    ])
    def formatter_factory(
        self,
        request,
    ) -> Callable[..., StructuredLogsFormatter]:
        return request.param

    # (This fixture is overridden for some tests...)
    @pytest.fixture(params=[
        dict(
            defaults={
                'system': EXAMPLE_SYSTEM,
                'component_type': {'...not-used...'},
            },
            auto_makers={
                'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT).importable_dotted_name,
                'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
            },
            serializer=example_serializer,
        ),
        dict(
            defaults=types.MappingProxyType({
                # (Example of non-dict mapping)
                'system': EXAMPLE_SYSTEM,
                'component': EXAMPLE_COMPONENT,
                'component_type': EXAMPLE_COMPONENT_TYPE,
            }),
        ),
        dict(
            auto_makers=ExampleNonDictMutableMapping({
                # (Example of non-dict mapping)
                'system': ConstantValueAutoMaker(EXAMPLE_SYSTEM),
                'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
            }),
        ),
        dict(
            defaults={
                'component': {'...not-used...'},
            },
            auto_makers={
                'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
            },
            serializer=(
                # Not a valid serializer, yet it will be overridden by
                # the `conf_corrector`-provided serializer (see below).
                'time.time'
            ),
            conf_corrector=ExampleConfCorrector(
                defaults={
                    'system': EXAMPLE_SYSTEM,
                },
                auto_makers=types.MappingProxyType({
                    # (Example of non-dict mapping)
                    'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT).importable_dotted_name,
                }),
                serializer=example_serializer,
                required_keys={'system', 'component', 'component_type'},
            ),
            conf_corrector_params={'Nu!': 'My Liege!'},
        ),
    ])
    def formatter_init_kwargs(
        self,
        request,
    ) -> dict[str, Any]:
        return request.param

    # (This fixture is overridden for some tests...)
    @pytest.fixture(params=list(FormatterInitKwargsPassingVariant))
    def formatter_init_kwargs_passing_variant(
        self,
        request,
    ) -> FormatterInitKwargsPassingVariant:
        return request.param

    # (This fixture is overridden for some tests...)
    @pytest.fixture(params=list(FormatterInitIgnoredRedundantStandardArgumentsVariant))
    def formatter_init_ignored_redundant_standard_arguments_variant(
        self,
        request
    ) -> FormatterInitIgnoredRedundantStandardArgumentsVariant:
        return request.param

    # (This fixture is overridden for some tests...)
    @pytest.fixture
    def formatter_init_ignored_redundant_standard_arguments(
        self,
        formatter_init_ignored_redundant_standard_arguments_variant,
    ) -> tuple[Sequence[Any], Mapping[str, Any]]:
        ign_args: Sequence[Any]
        ign_kwargs: Mapping[str, Any]

        # TODO: restore `match` after dropping unofficial support for Py3.9
        if formatter_init_ignored_redundant_standard_arguments_variant is FormatterInitIgnoredRedundantStandardArgumentsVariant.NONE:  # noqa
        # match formatter_init_ignored_redundant_standard_arguments_variant:
        #     case FormatterInitIgnoredRedundantStandardArgumentsVariant.NONE:
                ign_args = ()
                ign_kwargs = {}
        elif formatter_init_ignored_redundant_standard_arguments_variant is FormatterInitIgnoredRedundantStandardArgumentsVariant.POSITIONAL:  # noqa
            # case FormatterInitIgnoredRedundantStandardArgumentsVariant.POSITIONAL:
                ign_args = (
                    None,  # `fmt`
                    None,  # `datefmt`
                    '%',   # `style`
                    True,  # `validate`
                )
                ign_kwargs = {}
        elif formatter_init_ignored_redundant_standard_arguments_variant is FormatterInitIgnoredRedundantStandardArgumentsVariant.KEYWORD:  # noqa
            # case FormatterInitIgnoredRedundantStandardArgumentsVariant.KEYWORD:
                ign_args = ()
                ign_kwargs = {
                    'fmt': None,
                    'datefmt': None,
                    'style': '%',
                    'validate': True,
                }
        elif formatter_init_ignored_redundant_standard_arguments_variant is FormatterInitIgnoredRedundantStandardArgumentsVariant.MIXED:  # noqa
            # case FormatterInitIgnoredRedundantStandardArgumentsVariant.MIXED:
                ign_args = (
                    None,  # `fmt`
                    None,  # `datefmt`
                )
                ign_kwargs = {
                    'style': '%',
                    'validate': True,
                }
        else:
            raise AssertionError(f'unrecognized_variant={formatter_init_ignored_redundant_standard_arguments_variant!r}')  # noqa
            # case unrecognized_variant:
            #     raise AssertionError(f'{unrecognized_variant=}')

        return ign_args, ign_kwargs

    # (This fixture is overridden for some tests...)
    @pytest.fixture
    def prepare_formatter_init_kwargs_mapping(self) -> Callable[
        [dict[str, Any]],
        Mapping[str, Any],
    ]:
        return dict

    # (This fixture is overridden for some tests...)
    @pytest.fixture
    def prepare_formatter_init_kwargs_string(self) -> Callable[
        [dict[str, Any]],
        str,
    ]:
        def prepare_formatter_init_kwargs_string_impl(d: dict[str, Any]) -> str:
            return repr({
                k: (dict(v) if isinstance(v, Mapping) else v)
                for k, v in d.items()
            })

        return prepare_formatter_init_kwargs_string_impl

    @pytest.fixture
    def make_formatter(
        self,
        formatter_factory,
        formatter_init_kwargs,
        formatter_init_kwargs_passing_variant,
        formatter_init_ignored_redundant_standard_arguments,
        prepare_formatter_init_kwargs_mapping,
        prepare_formatter_init_kwargs_string,
        seen_formatter_auto_made_record_attr_prefixes,
    ) -> Callable[..., StructuredLogsFormatter]:

        ign_args, ign_kwargs = formatter_init_ignored_redundant_standard_arguments
        if formatter_init_kwargs_passing_variant is not FormatterInitKwargsPassingVariant.DIRECT:
            # The actual arguments (as a dict or its repr) are to be
            # passed as the first positional argument to `__init__()`.
            ign_args = ign_args[1:]
            ign_kwargs = {
                k: v for k, v in ign_kwargs.items()
                if k != 'fmt'
            }

        def make_formatter_impl(
            *,
            extra_args: Sequence[Any] = (),
            extra_kwargs: Mapping[str, Any] = EMPTY_MAPPING,
        ) -> StructuredLogsFormatter:
            # TODO: restore `match` after dropping unofficial support for Py3.9
            if formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.DIRECT:
            # match formatter_init_kwargs_passing_variant:
            #     case FormatterInitKwargsPassingVariant.DIRECT:
                    args = (*ign_args, *extra_args)
                    kwargs = dict(**ign_kwargs, **extra_kwargs, **formatter_init_kwargs)
            elif formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.MAPPING:  # noqa
                # case FormatterInitKwargsPassingVariant.MAPPING:
                    m = prepare_formatter_init_kwargs_mapping(formatter_init_kwargs)
                    args = (m, *ign_args, *extra_args)
                    kwargs = dict(**ign_kwargs, **extra_kwargs)
            elif formatter_init_kwargs_passing_variant is FormatterInitKwargsPassingVariant.STRING:
                # case FormatterInitKwargsPassingVariant.STRING:
                    s = prepare_formatter_init_kwargs_string(formatter_init_kwargs)
                    args = (s, *ign_args, *extra_args)
                    kwargs = dict(**ign_kwargs, **extra_kwargs)
            else:
                raise AssertionError(f'unrecognized_variant={formatter_init_kwargs_passing_variant!r}')  # noqa
                # case unrecognized_variant:
                #     raise AssertionError(f'{unrecognized_variant=}')
            f = formatter_factory(*args, **kwargs)
            seen_formatter_auto_made_record_attr_prefixes.append(f.auto_made_record_attr_prefix)
            return f

        return make_formatter_impl

    @pytest.fixture
    def formatter(self, make_formatter) -> Generator[StructuredLogsFormatter]:
        f = make_formatter()
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

    @pytest.fixture(params=[
        LogCase(
            lambda logger: logger.info(
                'Answer: %d', 42,
            ),
            expected_output_base={
                **get_output_base(level='INFO'),
                'message': 'Answer: 42',
                'message_base': 'Answer: %d',
            },
        ),
        LogCase(
            lambda logger: logger.error(
                xm('Answer: {answer}', answer=42),
            ),
            expected_output_base={
                **get_output_base(level='ERROR'),
                'message': 'Answer: 42',
                'message_base': {
                    'pattern': 'Answer: {answer}',
                },
                'answer': 42,
            },
        ),
        LogCase(
            lambda logger: logger.debug(
                xm(deepcopy(EXAMPLE_CUSTOM_ITEMS)),
            ),
            expected_output_base={
                **get_output_base(level='DEBUG'),
                **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
            },
        ),
    ])
    def typical_log_case(
        self,
        request,
        example_custom_items,
    ) -> LogCase:
        return deepcopy(request.param)


    #
    # Initialization-focused tests


    @pytest.mark.parametrize(
        (
            # (Overriding fixtures `formatter_factory` and `formatter_init_kwargs`)
            'formatter_factory',
            'formatter_init_kwargs',
            'expected_public_attrs',
        ),
        [
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={},
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    defaults={},
                    auto_makers={},
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector(),
                    conf_corrector_params={},
                ),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={},
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                # * Formatter factory:
                make_StructuredLogsFormatter_subclass(
                    base_defaults={},
                    base_auto_makers={},
                    base_record_attr_to_output_key={},
                ),
                # * Arguments:
                dict(),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={},
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={},
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    defaults=ExampleNonDictMutableMapping({
                        'system': None,          # (*void* value)
                        'component': None,       # (*void* value)
                        'component_type': None,  # (*void* value)
                    }),
                ),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={},
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                        'zero': 0,
                        'D' * 200: {'L' * 10000: ['L' * 10000]},
                    },
                    auto_makers=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker('ZER0').importable_dotted_name,
                    }),
                    serializer=example_serializer,
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'xyz': {"('pom', 'i', 'dor')": 1111},
                        'zero': 0,
                        'D' * 200: {'L' * 200: ['L' * 10000]},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker('ZER0'),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        '<PREFIX>component': 'component',
                        '<PREFIX>foo': 'foo',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    conf_corrector=ExampleConfCorrector(
                        defaults={
                            'system': EXAMPLE_SYSTEM,
                            'component_type': EXAMPLE_COMPONENT_TYPE,
                            'vege': ['mar', 'chew', 'ka'],
                            'void_value_that_will_be_omitted': [],
                            'xyz': {('pom', 'i', 'dor'): 1111},
                            'zero': 0,
                            'D' * 200: {'L' * 10000: ['L' * 10000]},
                        },
                        auto_makers=types.MappingProxyType({
                            # (Example of non-dict mapping)
                            'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                            'foo': ConstantValueAutoMaker(None),
                            'zero': ConstantValueAutoMaker('ZER0').importable_dotted_name,
                        }),
                        serializer=example_serializer,
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'xyz': {"('pom', 'i', 'dor')": 1111},
                        'zero': 0,
                        'D' * 200: {'L' * 200: ['L' * 10000]},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker('ZER0'),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        '<PREFIX>component': 'component',
                        '<PREFIX>foo': 'foo',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                        'zero': 0,
                        'D' * 200: {'L' * 10000: ['L' * 10000]},
                    },
                    auto_makers=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker('ZER0').importable_dotted_name,
                    }),
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector(
                        defaults=sentinel.DELETE_ALL,
                        auto_makers=sentinel.DELETE_ALL,
                        base_record_attr_to_output_key=sentinel.DELETE_ALL,
                        serializer='json.dumps',
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={},
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={},
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                StructuredLogsFormatter,
                # * Arguments:
                dict(
                    auto_makers={
                        'system': ConstantValueAutoMaker(None),
                        'component': ConstantValueAutoMaker(None).importable_dotted_name,
                        'component_type': ConstantValueAutoMaker(None),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                    },
                    serializer='json.dumps',
                    conf_corrector=ExampleConfCorrector(
                        auto_makers={
                            'py_ver': (
                                ConstantValueAutoMaker(EXAMPLE_PY_VER).importable_dotted_name
                            ),
                            'script_args': lambda: EXAMPLE_SCRIPT_ARGS,
                        },
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={},
                    auto_makers={
                        'system': ConstantValueAutoMaker(None),
                        'component': ConstantValueAutoMaker(None),
                        'component_type': ConstantValueAutoMaker(None),
                        'py_ver': ConstantValueAutoMaker(EXAMPLE_PY_VER),
                        'script_args': AnyOfType(Function),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        '<PREFIX>system': 'system',
                        '<PREFIX>component': 'component',
                        '<PREFIX>component_type': 'component_type',
                        '<PREFIX>py_ver': 'py_ver',
                        '<PREFIX>script_args': 'script_args',
                        f"<PREFIX>{'A' * 200}": 'A' * 200,
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                ExampleSubclassOfStructuredLogsFormatter,
                # * Arguments:
                dict(),
                # * Expected public attributes:
                dict(
                    defaults={
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
                        'zero': ['default value of `zero` item...'],
                    },
                    auto_makers={
                        'component': AnyOfType(Function),
                        'zero': AnyOfType(Function),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'attr_name_with_typo': 'attr_name_without_typo',
                        'one_silly_undesired_attr': None,
                        '<PREFIX>component': 'component',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                ExampleSubclassOfStructuredLogsFormatter,
                # * Arguments:
                dict(
                    conf_corrector=ExampleConfCorrector(
                        base_record_attr_to_output_key=sentinel.DELETE_ALL,
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
                        'zero': ['default value of `zero` item...'],
                    },
                    auto_makers={
                        'component': AnyOfType(Function),
                        'zero': AnyOfType(Function),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        '<PREFIX>component': 'component',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                ExampleSubclassOfStructuredLogsFormatter,
                # * Arguments:
                dict(
                    defaults=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'system': (),  # (*void* value)
                        'component_type': {('pom', 'i', 'dor'): 1111},
                        'blah_blah_blah': [
                            42,
                            {('po', 'mid', 'or'): 2222},
                        ],
                        'to_be_omitted': {},          # (*void* value)
                        'to_be_omitted_as_well': '',  # (*void* value)
                        'vege': ['mar', 'chew', 'ka'],
                        'zero': 0,
                    }),
                    auto_makers=ExampleNonDictMutableMapping({
                        # (Example of non-dict mapping)
                        'component': ConstantValueAutoMaker('coś tam').importable_dotted_name,
                        'component_type': ConstantValueAutoMaker('czegoś tam'),
                        'xyz': ConstantValueAutoMaker(dt.date(2026, 4, 27)),
                    }),
                    serializer=(
                        # Not a valid serializer, yet it will be overridden by
                        # the `conf_corrector`-provided serializer (see below).
                        'time.time'
                    ),
                    conf_corrector=(
                        ExampleConfCorrector(
                            required_keys={'component', 'vege', 'zero'},
                            serializer=example_serializer.importable_dotted_name,
                        ).importable_dotted_name
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'component_type': {'Pomidor': 1111},
                        'blah_blah_blah': [
                            42,
                            {'Pomidor': 2222},
                        ],
                        'vege': 'Marchewka',
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker('coś tam'),
                        'component_type': ConstantValueAutoMaker('czegoś tam'),
                        'xyz': ConstantValueAutoMaker(dt.date(2026, 4, 27)),
                        'zero': AnyOfType(Function),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'attr_name_with_typo': 'attr_name_without_typo',
                        'one_silly_undesired_attr': None,
                        '<PREFIX>component': 'component',
                        '<PREFIX>component_type': 'component_type',
                        '<PREFIX>xyz': 'xyz',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                # * Formatter factory:
                make_StructuredLogsFormatter_subclass(
                    extra_accepted_kwarg_names={'foo', 'bar'},
                    base_defaults={
                        'a': 0.0,
                        'abcdefgh': 'ijklmnop',
                        'd': {'ddd': 'DDD'},
                        'qq': None,    # (*void* value)
                        'ryq': None,   # (*void* value)
                        'napa': None,  # (*void* value)
                        'tyku': None,  # (*void* value)
                        'D' * 200: {'L' * 10000: ['L' * 10000]},
                    },
                    base_auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                        'tyku': ConstantValueAutoMaker('T'),
                        'qwerty': ConstantValueAutoMaker('asdfgh'),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                    },
                    base_record_attr_to_output_key={
                        'a': 'A???',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                        'R' * 10000: 'K' * 200,
                    },
                    prepare_value_kwargs=dict(to_str_types=(float, dt.time)),
                    prepare_submapping_key=(lambda key: f'-*-{key!r}-*-'),
                ),
                # * Arguments:
                dict(
                    foo=["FOO"],
                    bar={"BAR": 42},
                    serializer='json.dumps',
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'a': '0.0',
                        'abcdefgh': 'ijklmnop',
                        'd': {"-*-'ddd'-*-": 'DDD'},
                        'D' * 200: {f"-*-{'L' * 10000!r}-*-": ['L' * 10000]},
                    },
                    auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                        'tyku': ConstantValueAutoMaker('T'),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                        'qwerty': ConstantValueAutoMaker('asdfgh'),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        'a': 'A???',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                        'R' * 10000: 'K' * 200,
                        '<PREFIX>b': 'b',
                        '<PREFIX>napa': 'napa',
                        '<PREFIX>tyku': 'tyku',
                        '<PREFIX>qwerty': 'qwerty',
                        f"<PREFIX>{'A' * 200}": 'A' * 200,
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                make_StructuredLogsFormatter_subclass(
                    extra_accepted_kwarg_names={'foo', 'bar'},
                    base_defaults={
                        'a': 0.0,
                        'abcdefgh': 'ijklmnop',
                        'd': {'ddd': 'DDD'},
                        'qq': None,    # (*void* value)
                        'ryq': None,   # (*void* value)
                        'napa': None,  # (*void* value)
                        'tyku': None,  # (*void* value)
                        'D' * 200: {'L' * 10000: ['L' * 10000]},
                    },
                    base_auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                        'tyku': ConstantValueAutoMaker('T'),
                        'qwerty': ConstantValueAutoMaker('asdfgh'),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                    },
                    base_record_attr_to_output_key={
                        'a': 'A???',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                        'R' * 10000: 'K' * 200,
                    },
                    prepare_value_kwargs=dict(to_str_types=(float, dt.time)),
                    prepare_submapping_key=(lambda key: f'-*-{key!r}-*-'),
                ),
                # * Arguments:
                dict(
                    foo=["FOO"],
                    bar={"BAR": 42},
                    serializer='json.dumps',
                    conf_corrector=ExampleConfCorrector(
                        defaults={
                            'a': 999999.42,
                            'abcdefgh': sentinel.DELETE,
                            'ryq': 'mój ty basałyku',
                            'A ja?': 42,
                        },
                        auto_makers={
                            'qwerty': sentinel.DELETE,
                            'zxcvbn': ConstantValueAutoMaker(12345678),
                        },
                        base_record_attr_to_output_key={
                            'a': 'A',
                            'aaaa': 'AAAA',
                        },
                        required_keys={
                            'a',
                            'b',
                        },
                        serializer=example_serializer,
                    ),
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'a': '999999.42',
                        'd': {"-*-'ddd'-*-": 'DDD'},
                        'D' * 200: {f"-*-{'L' * 10000!r}-*-": ['L' * 10000]},
                        'ryq': 'mój ty basałyku',
                        'A ja?': 42,
                    },
                    auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                        'tyku': ConstantValueAutoMaker('T'),
                        'A' * 200: ConstantValueAutoMaker('L' * 10000),
                        'zxcvbn': ConstantValueAutoMaker(12345678),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        'a': 'A',
                        'aaaa': 'AAAA',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                        'R' * 10000: 'K' * 200,
                        '<PREFIX>b': 'b',
                        '<PREFIX>napa': 'napa',
                        '<PREFIX>tyku': 'tyku',
                        '<PREFIX>zxcvbn': 'zxcvbn',
                        f"<PREFIX>{'A' * 200}": 'A' * 200,
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                # * Formatter factory:
                make_StructuredLogsFormatter_subclass(
                    base_defaults=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'a': 0.0,
                        'ryq': 'Na-na-na-na-na...',
                        'tyku': None,  # (*void* value)
                        'v': 1.0,
                        'zebra-1': [],  # (*void* value)
                        'zebra-2': {},  # (*void* value)
                        'zebra-3': ['Three shall be the number thou shalt count'],
                    }),
                    base_auto_makers=ExampleNonDictMutableMapping({
                        # (Example of non-dict mapping)
                        'napa': ConstantValueAutoMaker(3333333333),
                        'tyku': ConstantValueAutoMaker('T'),
                    }),
                    base_record_attr_to_output_key=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'a': 'A',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                    }),
                    prepare_value_kwargs=dict(to_str_types=(float, dt.time)),
                    prepare_submapping_key=(lambda key: f'-*-{key!r}-*-'),
                ),
                # * Arguments:
                dict(
                    defaults=ExampleNonDictMutableMapping({
                        # (Example of non-dict mapping)
                        'd': {'ddd': 'DDD'},
                        'qq': None,  # (*void* value)
                        'ryq': None,  # (*void* value)
                        'napa': None,  # (*void* value)
                        'v': 2.0,
                        'zebra-1': '',  # (*void* value)
                        'zebra-2': ['2nd'],
                        'zebra-3': (),  # (*void* value)
                    }),
                    auto_makers=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                    }),
                    conf_corrector=ExampleConfCorrector().importable_dotted_name,
                    conf_corrector_params={
                        'extra_required_keys': {
                            'a',
                            'b',
                            'v',
                            'napa',
                            'tyku',
                        },
                    },
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'a': '0.0',
                        'd': {"-*-'ddd'-*-": 'DDD'},
                        'v': '2.0',
                        'zebra-2': ['2nd'],
                    },
                    auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'napa': ConstantValueAutoMaker('N'),
                        'tyku': ConstantValueAutoMaker('T'),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        'a': 'A',
                        'c': 'C',
                        'tyku': 'qqryq napatyku',
                        '<PREFIX>b': 'b',
                        '<PREFIX>napa': 'napa',
                        '<PREFIX>tyku': 'tyku',
                    },
                    serializer=json.dumps,
                ),
            ),
            (
                # * Formatter factory:
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'system': 'Śmystem',
                        'późno ⏰': dt.time(23, 59),
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                        'D' * 200: 'Macarron?',
                    },
                    base_auto_makers=ExampleNonDictMutableMapping({
                        # (Example of non-dict mapping)
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        'zero': ConstantValueAutoMaker(777777777).importable_dotted_name,
                    }),
                    base_record_attr_to_output_key=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'strawberries': '🍓🍓',
                        'tomatoes': '🍅🍅🍅',
                    }),
                    prepare_value_kwargs=dict(to_str_types=(float, dt.time)),
                    prepare_submapping_key=(lambda key: f'-*-{key!r}-*-'),
                ),
                # * Arguments:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'vege': ['mar', 'chew', 'ka'],
                        'D' * 200: 'No, Chacarron.',
                    },
                    auto_makers=types.MappingProxyType({
                        # (Example of non-dict mapping)
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'zero': ConstantValueAutoMaker('𝋠'),
                    }),
                    serializer=CallableImportableWrapper(json.dumps),
                    conf_corrector=ExampleConfCorrector(
                        defaults={
                            'component_type': 'with a... herring!',
                            'component': 123.456,
                            'vege': ['🥕', '🥒', '🍅'],
                            'void_value_that_will_be_omitted': {},
                            'xyz': {('pom', 'i', 'dor'): {'🍅': '🚪'}},
                            'D' * 200: {'L' * 10000: ['L' * 10000]},
                        },
                        auto_makers=types.MappingProxyType({
                            # (Example of non-dict mapping)
                            'foo': ConstantValueAutoMaker(None),
                            'późno ⏰': ConstantValueAutoMaker(dt.time(22, 22)),
                            'zero': ConstantValueAutoMaker(0).importable_dotted_name,
                        }),
                        base_record_attr_to_output_key=ExampleNonDictMutableMapping({
                            # (Example of non-dict mapping)
                            'cucumbers': '🥒🥒🥒🥒',
                            'strawberries': '🍓🍓🍓🍓🍓',
                        }),
                        serializer=example_serializer,
                    ),
                    conf_corrector_params={
                        'extra_required_keys': {
                            'system',
                            'component_type',
                            'component',
                            'foo',
                            'późno ⏰',
                            'vege',
                            'xyz',
                            'zero',
                            'D' * 200,
                        },
                    },
                ),
                # * Expected public attributes:
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': 'with a... herring!',
                        'component': '123.456',
                        'późno ⏰': '23:59:00',
                        'vege': ['🥕', '🥒', '🍅'],
                        'xyz': {
                            "-*-('pom', 'i', 'dor')-*-": {"-*-'🍅'-*-": '🚪'},
                        },
                        'D' * 200: {f"-*-{'L' * 10000!r}-*-": ['L' * 10000]},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        'foo': ConstantValueAutoMaker(None),
                        'późno ⏰': ConstantValueAutoMaker(dt.time(22, 22)),
                        'zero': ConstantValueAutoMaker(0),
                    },
                    auto_made_record_attr_prefix=AnyOfType(str),
                    record_attr_to_output_key={
                        'cucumbers': '🥒🥒🥒🥒',
                        'strawberries': '🍓🍓🍓🍓🍓',
                        'tomatoes': '🍅🍅🍅',
                        '<PREFIX>component': 'component',
                        '<PREFIX>component_type': 'component_type',
                        '<PREFIX>foo': 'foo',
                        '<PREFIX>późno ⏰': 'późno ⏰',
                        '<PREFIX>zero': 'zero',
                    },
                    serializer=example_serializer,
                ),
            ),
        ],
    )
    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_init_kwargs_passing_variant',
            'prepare_formatter_init_kwargs_mapping',
        ),
        [
            (FormatterInitKwargsPassingVariant.DIRECT, sentinel.UNUSED),
            (FormatterInitKwargsPassingVariant.MAPPING, dict),
            (FormatterInitKwargsPassingVariant.MAPPING, ExampleNonDictMutableMapping),
            (FormatterInitKwargsPassingVariant.MAPPING, types.MappingProxyType),
            (FormatterInitKwargsPassingVariant.STRING, sentinel.UNUSED),
        ],
    )
    def test_init_ok(
        self,
        make_formatter,
        expected_public_attrs,
    ):
        formatter = make_formatter()

        expected_public_attrs = expected_public_attrs.copy()
        expected_public_attrs['record_attr_to_output_key'] = {
            rec_attr.replace('<PREFIX>', formatter.auto_made_record_attr_prefix): obj
            for rec_attr, obj in expected_public_attrs['record_attr_to_output_key'].items()
        }
        actual_public_attrs = {
            attr: val
            for attr, val in vars(formatter).items()
            if attr != 'datefmt' and not attr.startswith('_')
        }
        assert actual_public_attrs == expected_public_attrs
        assert formatter.auto_made_record_attr_prefix.startswith(
            StructuredLogsFormatter.COMMON_AUTO_PREFIX
        )


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                StructuredLogsFormatter,
                dict(
                    foo=42,  # (unrecognized argument)
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    foo=42,  # (unrecognized argument)
                    bar='43',  # (unrecognized argument)
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker(0).importable_dotted_name,
                    },
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector().importable_dotted_name,
                    conf_corrector_params={
                        'extra_required_keys': {
                            'system',
                            'component',
                            'component_type',
                        },
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    extra_accepted_kwarg_names={'foo', 'bar'},
                ),
                dict(
                    foo=42,
                    bar='43',
                    spam=b'44',  # (unrecognized argument)
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
        ]
    )
    def test_init_with_unrecognized_kwargs_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'unexpected keyword argument'):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                StructuredLogsFormatter,
                {
                    'defaults': {
                        'system': None,
                        'component': None,
                        'component_type': None,
                    },
                    42: 'whatever',  # (unrecognized + with wrong type of key)
                },
            ),
        ]
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.MAPPING,
            FormatterInitKwargsPassingVariant.STRING,
        ],
    )
    def test_init_with_non_string_key_in_kwargs_mapping_passed_as_first_arg_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'unexpected keyword argument'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [None],

                # **kwargs
                {
                    'fmt': None,
                },
            ),
            (
                # *args
                [
                    {'defaults': {'foo': 'bar'}},
                ],

                # **kwargs
                {
                    'fmt': None,
                    'datefmt': None,
                },
            ),
            (
                # *args
                [
                    {'defaults': {'foo': 'bar'}},
                ],

                # **kwargs
                {
                    'fmt': None,
                    'validate': True,
                },
            ),
            (
                # *args
                [None],

                # **kwargs
                {
                    'fmt': None,
                    'datefmt': None,
                    'style': '%',
                    'validate': True,
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.DIRECT,
        ],
    )
    def test_init_with_both_first_arg_given_and_fmt_passed_as_real_kwarg_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'multiple.*\bfmt\b'):
            make_formatter()


    @pytest.mark.parametrize(
        'excessive_positional_args',
        [
            [42],
            ['abc', object(), sentinel.WHATEVER],
        ]
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments_variant',
        [
            FormatterInitIgnoredRedundantStandardArgumentsVariant.POSITIONAL,
        ],
    )
    def test_init_with_excessive_positional_args_raises_type_error(
        self,
        make_formatter,
        excessive_positional_args,
    ):
        with pytest.raises(TypeError, match=r'excessive positional argument'):
            make_formatter(extra_args=excessive_positional_args)


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.STRING,
        ],
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'prepare_formatter_init_kwargs_string',
        [
            (lambda _: '<not an `ast.literal_eval()`-evaluable string>'),
            (lambda _: ''),
        ],
    )
    def test_init_with_first_arg_being_string_not_evaluable_by_litera_eval_raises_value_error(
        self,
        make_formatter,
    ):
        with pytest.raises(ValueError, match=r'error.*when trying to evaluate'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [
                    0,  # (unsupported type of first positional arg)
                ],

                # **kwargs
                {},
            ),
            (
                # *args
                [
                    object(),  # (unsupported type of first positional arg)
                ],

                # **kwargs
                {
                    'validate': True,
                },
            ),
            (
                # *args
                [
                    False,  # (unsupported type of first positional arg)
                    None,
                ],

                # **kwargs
                {
                    'style': '%',
                    'validate': True,
                },
            ),
            (
                # *args
                [
                    [('x', 42)],  # (unsupported type of first positional arg)
                ],

                # **kwargs
                {
                    'datefmt': None,
                    'style': '%',
                    'validate': True,
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.DIRECT,
        ],
    )
    def test_init_with_first_arg_not_being_mapping_or_str_or_none_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'expected.*mapping.*or.*literal_eval'):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding fixtures `formatter_factory` and `formatter_init_kwargs`)
            'formatter_factory',
            'formatter_init_kwargs',
            'real_extra_kwargs',
        ),
        [
            (
                StructuredLogsFormatter,

                # Mapping of kwargs to be passed as first positional arg
                dict(
                    defaults={},
                ),

                # Real **kwargs
                dict(foo=42),
            ),
            (
                StructuredLogsFormatter,

                # Mapping of kwargs to be passed as first positional arg
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker(0).importable_dotted_name,
                    },
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector(
                        required_keys={
                            'system',
                            'component_type',
                            'component',
                        },
                    ),
                    conf_corrector_params={'Nu!': 'My Liege!'},
                ),

                # Real **kwargs
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'vege': ['mar', 'chew', 'ka'],
                        'void_value_that_will_be_omitted': [],
                        'xyz': {('pom', 'i', 'dor'): 1111},
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'foo': ConstantValueAutoMaker(None),
                        'zero': ConstantValueAutoMaker(0).importable_dotted_name,
                    },
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector(
                        required_keys={
                            'system',
                            'component_type',
                            'component',
                        },
                    ),
                    conf_corrector_params={'Nu!': 'My Liege!'},
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    extra_accepted_kwarg_names={'foo', 'bar'},
                ),

                # Mapping of kwargs to be passed as first positional arg
                dict(
                    foo=42,
                    bar=43,
                ),

                # Real **kwargs
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
        ]
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.MAPPING,
            FormatterInitKwargsPassingVariant.STRING,
        ],
    )
    def test_init_with_kwargs_passed_both_directly_and_as_first_arg_raises_type_error(
        self,
        make_formatter,
        real_extra_kwargs,
    ):
        with pytest.raises(TypeError, match=r'should not pass real keyword arguments'):
            make_formatter(extra_kwargs=real_extra_kwargs)


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [],

                # **kwargs
                {
                    'fmt': '',  # (unallowed: `fmt` kwarg not being None)
                },
            ),
            (
                # *args
                [],

                # **kwargs
                {
                    'fmt': [],  # (unallowed: `fmt` kwarg not being None)
                    'datefmt': None,
                },
            ),
            (
                # *args
                [],

                # **kwargs
                {
                    'fmt': object(),  # (unallowed: `fmt` kwarg not being None)
                    'style': '%',
                },
            ),
            (
                # *args
                [],

                # **kwargs
                {
                    'fmt': b'tro-lo-lo',  # (unallowed: `fmt` kwarg not being None)
                    'style': '%',
                    'validate': True,
                },
            ),
        ]
    )
    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs_passing_variant',
        [
            FormatterInitKwargsPassingVariant.DIRECT,
        ],
    )
    def test_init_with_unallowed_customization_of_fmt_passed_as_real_kwarg_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'`fmt` is not customizable'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [
                    None,
                    '',  # (unallowed: `datefmt` not being None)
                ],

                # **kwargs
                dict(),
            ),
            (
                # *args
                [],

                # **kwargs
                dict(
                    datefmt=False,  # (unallowed: `datefmt` not being None)
                ),
            ),
            (
                # *args
                [None],

                # **kwargs
                dict(
                    datefmt=object(),  # (unallowed: `datefmt` not being None)
                    style='%',
                    validate=True,
                )
            ),
        ]
    )
    def test_init_with_unallowed_customization_of_datefmt_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'`datefmt` is not customizable'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [
                    None,
                    None,
                    '$',  # (unallowed: `style` not equal to '%')
                ],

                # **kwargs
                dict(),
            ),
            (
                # *args
                [],

                # **kwargs
                dict(
                    fmt=None,
                    style='{',  # (unallowed: `style` not equal to '%')
                ),
            ),
            (
                # *args
                [None, None],

                # **kwargs
                dict(
                    style='',  # (unallowed: `style` not equal to '%')
                    validate=True,
                )
            ),
        ]
    )
    def test_init_with_unallowed_customization_of_style_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'`style` is not customizable'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_ignored_redundant_standard_arguments',
        [
            (
                # *args
                [
                    None,
                    None,
                    '%',
                    False,  # (unallowed: `validate` not being True)
                ],

                # **kwargs
                dict(),
            ),
            (
                # *args
                [],

                # **kwargs
                dict(
                    fmt=None,
                    datefmt=None,
                    style='%',
                    validate=None,  # (unallowed: `validate` not being True)
                ),
            ),
            (
                # *args
                [None, None, '%'],

                # **kwargs
                dict(
                    validate=[123],  # (unallowed: `validate` not being True)
                )
            ),
            (
                # *args
                [None],

                # **kwargs
                dict(
                    validate=1,  # (unallowed: `validate` not being True)
                ),
            ),
        ]
    )
    def test_init_with_unallowed_customization_of_validate_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'`validate` is not customizable'):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                formatter_factory,
                formatter_init_kwargs,
            )
            for unresolvable_dotted_path in [
                'some_NON_EXISTENT_MODULE.whatever',
                'collections.abc.some_NON_EXISTENT_OBJECT',
            ]
            for formatter_factory, formatter_init_kwargs in [
                (
                    StructuredLogsFormatter,
                    dict(
                        defaults={
                            'system': EXAMPLE_SYSTEM,
                        },
                        auto_makers={
                            'component': unresolvable_dotted_path,
                            'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        },
                        serializer=example_serializer,
                    ),
                ),
                (
                    make_StructuredLogsFormatter_subclass(
                        base_auto_makers={
                            'foo': unresolvable_dotted_path,
                        },
                    ),
                    dict(
                        defaults={
                            'system': EXAMPLE_SYSTEM,
                        },
                        auto_makers={
                            'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                            'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        },
                    ),
                ),
            ]
        ],
    )
    def test_init_with_unresolvable_auto_maker_dotted_path_raises_value_error(
        self,
        make_formatter,
    ):
        with pytest.raises(ValueError, match=r'cannot resolve dotted_path='):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                formatter_factory,
                formatter_init_kwargs,
            )
            for wrong_auto_maker in [
                # (both wrong, as being/pointing to a *non-callable* object)
                ImportableWrapper(None),
                ImportableWrapper(None).importable_dotted_name,
            ]
            for formatter_factory, formatter_init_kwargs in [
                (
                    StructuredLogsFormatter,
                    dict(
                        defaults={
                            'system': EXAMPLE_SYSTEM,
                        },
                        auto_makers={
                            'component': wrong_auto_maker,
                            'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        },
                        serializer=example_serializer,
                    ),
                ),
                (
                    make_StructuredLogsFormatter_subclass(
                        base_auto_makers={   # noqa
                            'foo': wrong_auto_maker,   # type: ignore[dict-item]
                        },
                    ),
                    dict(
                        defaults={
                            'system': EXAMPLE_SYSTEM,
                        },
                        auto_makers={
                            'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                            'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        },
                    ),
                ),
            ]
        ],
    )
    def test_init_with_non_callable_auto_maker_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'auto-maker.*not.*callable'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs',
        [
            dict(serializer=unresolvable_dotted_path)
            for unresolvable_dotted_path in [
                'some_NON_EXISTENT_MODULE.whatever',
                'collections.abc.some_NON_EXISTENT_OBJECT',
            ]
        ],
    )
    def test_init_with_unresolvable_serializer_dotted_path_raises_value_error(
        self,
        make_formatter,
    ):
        with pytest.raises(ValueError, match=r'cannot resolve dotted_path='):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs',
        [
            dict(serializer=wrong_serializer)
            for wrong_serializer in [
                # (both wrong, as being/pointing to a *non-callable* object)
                ImportableWrapper(None),
                ImportableWrapper(None).importable_dotted_name,
            ]
        ],
    )
    def test_init_with_non_callable_serializer_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'serializer.*not.*callable'):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs',
        [
            dict(conf_corrector=unresolvable_dotted_path)
            for unresolvable_dotted_path in [
                'some_NON_EXISTENT_MODULE.whatever',
                'collections.abc.some_NON_EXISTENT_OBJECT',
            ]
        ],
    )
    def test_init_with_unresolvable_conf_corrector_dotted_path_raises_value_error(
        self,
        make_formatter,
    ):
        with pytest.raises(ValueError, match=r'cannot resolve dotted_path='):
            make_formatter()


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_init_kwargs',
        [
            dict(conf_corrector=wrong_conf_corrector)
            for wrong_conf_corrector in [
                # (both wrong, as being/pointing to a *non-callable* object)
                ImportableWrapper(None),
                ImportableWrapper(None).importable_dotted_name,
            ]
        ],
    )
    def test_init_with_non_callable_conf_corrector_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'conf.*corrector.*not.*callable'):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                    },
                    auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                    serializer=example_serializer,
                    conf_corrector=ExampleConfCorrector(
                        required_keys={
                            'system',
                            'component_type',
                            'component',       # <- missing
                        },
                    ),
                    conf_corrector_params={'Nu!': 'My Liege!'},
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'component': EXAMPLE_COMPONENT_TYPE,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                    conf_corrector=(
                        ExampleConfCorrector(
                            required_keys={
                                'system',      # <- missing
                                'component_type',
                                'component',
                            },
                        ).importable_dotted_name
                    ),
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                    },
                    conf_corrector=ExampleConfCorrector(
                        auto_makers={
                            'system': ConstantValueAutoMaker(EXAMPLE_SYSTEM),
                        },
                    ),
                    conf_corrector_params={
                        'extra_required_keys': {
                            'system',
                            'component_type',  # <- missing
                            'component',
                        },
                    },
                ),
            ),
            (
                # (missing *output data* keys: 'bb', 'qq')
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'a': 0.0,
                    },
                    base_auto_makers={
                        'b': ConstantValueAutoMaker('bbb'),
                        'q': ConstantValueAutoMaker('qqq'),
                    },
                ),
                dict(
                    defaults={
                        'QQ': 'R dza',
                        'v': 42,
                    },
                    auto_makers={
                        'c': ConstantValueAutoMaker('ccc'),
                    },
                    conf_corrector=ExampleConfCorrector(
                        required_keys={
                            'a',
                            'b',
                            'bb',
                            'c',
                            'qq',
                            'QQ',
                        },
                    ),
                ),
            ),
        ],
    )
    def test_init_with_conf_corrector_raising_error(
        self,
        make_formatter,
    ):
        # Note: the particular *correctors* used in this test raise a
        # `ValueError` as shown below -- but other *correctors* could
        # raise entirely different exceptions.
        with pytest.raises(ValueError, match=r'missing_keys='):
            make_formatter()


    @pytest.mark.skip('...test not implemented yet...')
    def test_init_with_conf_corrector_producing_invalid_result(
        # TODO in particular:
        #   * with missing keys -> KeyError...
        #   * not a mapping -> TypeError...
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={   # noqa
                        42: 'whatever',   # type: ignore[dict-item]
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                    base_auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                dict(),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        42: 'whatever',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                    auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_auto_makers={   # noqa
                        42: ConstantValueAutoMaker('whatever'),   # type: ignore[dict-item]
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    auto_makers={
                        42: ConstantValueAutoMaker(sentinel.WHATEVER),
                        'system': ConstantValueAutoMaker(EXAMPLE_SYSTEM),
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'system': EXAMPLE_SYSTEM,
                    },
                    base_record_attr_to_output_key={   # noqa
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'some_rec_attr': 42,   # type: ignore[dict-item]
                    },
                ),
                dict(
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
            ),
        ]
    )
    def test_init_with_non_string_output_key_raises_type_error(
        self,
        make_formatter,
    ):
        with pytest.raises(TypeError, match=r'is not a str'):
            make_formatter()


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'D' * 201: 'whatever',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                    base_auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                dict(),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'D' * 201: 'whatever',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                    auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                    serializer=example_serializer,
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_auto_makers={
                        'A' * 201: ConstantValueAutoMaker('whatever'),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                dict(
                    defaults={
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    auto_makers={
                        'A' * 201: ConstantValueAutoMaker(sentinel.WHATEVER),
                        'system': ConstantValueAutoMaker(EXAMPLE_SYSTEM),
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'system': EXAMPLE_SYSTEM,
                    },
                    base_record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'some_rec_attr': 'K' * 201,
                    },
                ),
                dict(
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
            ),
        ]
    )
    def test_init_with_too_long_output_key_raises_value_error(
        self,
        make_formatter,
    ):
        with pytest.raises(ValueError, match=r'longer than 200 characters'):
            make_formatter()


    #
    # Usage-focused tests


    def test_log_message_using_legacy_style(
        self,
        log_handler,
        logger,
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
        log_handler,
        logger,
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
        log_handler,
        logger,
    ):
        logger.error(xm(
            "Let's log this: {0}={1!r}, {2}={3:.6f}",
            'foo',
            lambda: 'bar',
            lambda: 'π', math.pi,
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
        log_handler,
        logger,
    ):
        logger.critical(xm(
            "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            'foo',
            'bar',
            const_symbol='π',
            const_value=lambda: math.pi,
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
        log_handler,
        logger,
        example_custom_items,
    ):
        logger.debug(xm(
            "Let's log this: {}={!r}, {const_symbol}={const_value:.6f}",
            lambda: 'foo',
            'bar',
            const_symbol=lambda: 'π',
            const_value=math.pi,
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
        log_handler,
        logger,
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
        log_handler,
        logger,
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
        # (Overriding fixture)
        'formatter_factory',
        [
            make_StructuredLogsFormatter_subclass(
                base_record_attr_to_output_key={
                    **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                    'args': 'args',         # (By default it is mapped to None => excluded)
                    'asctime': 'time',      # (By default it is mapped to 'timestamp')
                    'msg': 'msg-base',      # (By default it is mapped to 'message_pattern')
                    'message': 'msg-text',  # (By default it is mapped to 'message' itself)
                    'name': None,           # (By default it is mapped to 'logger')
                    'date': 'date_descr',
                    'foo': 'bar',
                    'system': 'sys',
                    'component': 'c',
                    'component_type': 'ct',
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        'log_case',
        [
            SpecificLogCase(
                lambda logger: logger.error(
                    'Here they are (not): %d %s.',
                    43,
                    'cheeses',
                    extra={'foo': 123.456},
                ),
                expected_output={
                    **{
                        k: v
                        for k, v in get_output_base(level='ERROR').items()
                        # Note that, for this test, 'asctime' is mapped
                        # to 'time', not to 'timestamp'; also, 'name' is
                        # mapped to None (=> is excluded), not to 'logger'.
                        if k not in {'timestamp', 'logger'}
                    },
                    'msg-text': 'Here they are (not): 43 cheeses.',
                    'msg-base': 'Here they are (not): %d %s.',
                    'args': [43, 'cheeses'],
                    'bar': 123.456,
                    'time': EXAMPLE_TIMESTAMP_FORMATTED,

                    # Note that keys specified with `defaults` or
                    # `auto_makers` stuff are *not* subject to
                    # `record_attr_to_output_key`-based mapping:
                    'system': EXAMPLE_SYSTEM,                  # ('system', not 'sys')
                    'component': EXAMPLE_COMPONENT,            # ('component', not 'c')
                    'component_type': EXAMPLE_COMPONENT_TYPE,  # ('component', not 'ct')
                },
            ),
            SpecificLogCase(
                lambda logger: logger.critical(
                    xm(
                        'Here they are (not): {} {} (on {date}).',
                        43,
                        'cheeses',
                        date='May the 4th',
                    ),
                    extra={
                        'foo': 123.456,
                    },
                ),
                expected_output={
                    **{
                        k: v
                        for k, v in get_output_base(level='CRITICAL').items()
                        # Note that, for this test, 'asctime' is mapped
                        # to 'time', not to 'timestamp'; also, 'name' is
                        # mapped to None (=> is excluded), not to 'logger'.
                        if k not in {'timestamp', 'logger'}
                    },
                    'msg-text': 'Here they are (not): 43 cheeses (on May the 4th).',
                    'msg-base': {
                        'pattern': 'Here they are (not): {} {} (on {date}).',
                        'args': [43, 'cheeses'],
                    },
                    'bar': 123.456,
                    'time': EXAMPLE_TIMESTAMP_FORMATTED,

                    # Note that keys passed to `xm()` or specified with
                    # `defaults`/`auto_makers` stuff are *not* subject
                    # to `record_attr_to_output_key`-based mapping:
                    'date': 'May the 4th',                     # ('date', not 'date_descr')
                    'system': EXAMPLE_SYSTEM,                  # ('system', not 'sys')
                    'component': EXAMPLE_COMPONENT,            # ('component', not 'c')
                    'component_type': EXAMPLE_COMPONENT_TYPE,  # ('component', not 'ct')
                },
            ),
        ],
    )
    def test_log_using_formatter_subclass_with_customized_record_attr_to_output_key(
        self,
        logger,
        log_handler,
        log_case,
    ):
        log_case.logger_method_call(logger)

        assert log_handler.output_list == [log_case.expected_output]


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_factory',
        [
            make_StructuredLogsFormatter_subclass(
                format_timestamp_kwargs=dict(
                    timezone=dt.timezone(
                        offset=dt.timedelta(hours=2),
                        name='UTC+2',
                    ),
                    timestamp_as_datetime=lambda timestamp, tz: (
                        StructuredLogsFormatter.FORMAT_TIMESTAMP_DEFAULT_KWARGS[
                            'timestamp_as_datetime'
                        ](timestamp, tz) - dt.timedelta(minutes=10)
                    ),
                    utc_offset_to_custom_suffix={
                        dt.timedelta(hours=2): ' UTC + 2h',
                    },
                ),
            ),
        ],
    )
    def test_log_using_formatter_subclass_with_customized_format_timestamp(
        self,
        logger,
        log_handler,
        typical_log_case,
    ):
        expected_timestamp_dt = (
            EXAMPLE_TIMESTAMP_DT.replace(tzinfo=None)
            + dt.timedelta(hours=1, minutes=50)
        )
        expected_timestamp_formatted = (
            f"{expected_timestamp_dt.strftime('%Y-%m-%d %H:%M:%S.%f')} UTC + 2h"
        )

        typical_log_case.logger_method_call(logger)

        assert log_handler.output_list == [{
            **typical_log_case.expected_output_base,
            'timestamp': expected_timestamp_formatted,
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'formatter_factory',
        [
            make_StructuredLogsFormatter_subclass(
                before_get_prepared_output_data=lambda rec: (
                    setattr(rec, 'Arthur Jackson', {2: 'Sheds'})   # noqa
                    or rec
                )
            ),
        ],
    )
    def test_log_using_formatter_subclass_with_customized_get_prepared_output_data(
        self,
        logger,
        log_handler,
        typical_log_case,
    ):
        typical_log_case.logger_method_call(logger)

        assert log_handler.output_list == [{
            **typical_log_case.expected_output_base,
            'Arthur Jackson': {'2': 'Sheds'},
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]


    @pytest.mark.skip('...test not implemented yet...')
    def test_log_using_formatter_subclass_with_customized_prepare_value(
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.skip('...test not implemented yet...')
    def test_log_using_formatter_subclass_with_customized_prepare_submapping_key(
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.skip('...test not implemented yet...')
    def test_log_using_formatter_subclass_with_customized_serialize_prepared_output_data(
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.parametrize(
        (
            # (Overriding fixtures `formatter_factory` and `formatter_init_kwargs`)
            'formatter_factory',
            'formatter_init_kwargs',
            'log_case',
        ),
        [
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'HAM': '...NOT-used...',
                        'SPAM': '...also-NOT-used...',
                        '🥐': '...NOT-used-as-well...',
                        'system': EXAMPLE_SYSTEM,
                    },
                    auto_makers={
                        'EGGS': ConstantValueAutoMaker(('🥚', '🥚', '🥚', 'from auto-maker')),
                        'HAM': ConstantValueAutoMaker('Hold And Modify, from auto-maker'),
                        'SPAM': ConstantValueAutoMaker('from auto-maker'),
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                SpecificLogCase(
                    lambda logger: logger.debug(
                        xm({
                            'HAM': {42: 'from xm'},
                            'SPAM': 'from xm',
                            '🥐': [{'Lagun?'}, 'from xm'],
                        }),
                        extra={
                            'EGGS': 'from extra dict, you know...',
                            'SPAM': 'from extra dict',
                            '🥐': 'lagun from extra dict!',
                        },
                    ),
                    expected_output={
                        **get_output_base(level='DEBUG'),
                        'EGGS': ['🥚', '🥚', '🥚', 'from auto-maker'],
                        'EGGS_': 'from extra dict, you know...',
                        'HAM': {'42': 'from xm'},
                        'HAM_': 'Hold And Modify, from auto-maker',
                        'SPAM': 'from xm',
                        'SPAM_': 'from auto-maker',
                        'SPAM__': 'from extra dict',
                        '🥐': ["{'Lagun?'}", 'from xm'],
                        '🥐_': 'lagun from extra dict!',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'message_base': '...NOT-used...',
                        'msg': ['foo', 'bar', 'from defaults!'],
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                    auto_makers={
                        'message_base': ConstantValueAutoMaker('from auto-maker'),
                    },
                ),
                SpecificLogCase(
                    lambda logger: logger.info(
                        'actual msg passed, %d',
                        42,
                        extra={
                            'message_base': 'from extra dict',
                        },
                    ),
                    expected_output={
                        **get_output_base(level='INFO'),
                        'message': 'actual msg passed, 42',
                        'message_base': 'actual msg passed, %d',
                        'message_base_': 'from auto-maker',
                        'message_base__': 'from extra dict',
                        'msg': ['foo', 'bar', 'from defaults!'],
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'message_base': '...NOT-used...',
                        'msg': '...NOT-used-as-well...',
                        'Sir Galahad': '...also-NOT-used...',
                        'system': EXAMPLE_SYSTEM,
                    },
                    base_auto_makers={
                        'message_base': ConstantValueAutoMaker('from auto-maker'),
                        'Sir Galahad': ConstantValueAutoMaker('Galahad-from-auto-maker'),
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                    },
                    base_record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'Sir Galahad': 'message_base',
                        'Sir Lancelot': 'message_base',
                        'message_base_from_extra_dict': 'message_base',
                    },
                ),
                dict(
                    defaults={
                        'message_base': '...NOT-to-be-used...',
                        'Sir Lancelot': '...NOT-to-be-used-either...',
                    },
                    auto_makers={
                        'message': ConstantValueAutoMaker('message from auto-maker'),
                        'Sir Lancelot': ConstantValueAutoMaker('Lancelot-from-auto-maker'),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                SpecificLogCase(
                    lambda logger: (
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='message_base',
                            auto_maker=ConstantValueAutoMaker('from extra auto-maker'),
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Lancelot',
                            auto_maker=ConstantValueAutoMaker('the Brave'),
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Galahad',
                            auto_maker=ConstantValueAutoMaker('the Pure'),
                        ) or
                        logger.warning(   # noqa
                            xm(
                                'actual msg passed, {}',
                                42,
                                message_base='from xm',
                                msg='Tro-lo-lo-lo-lo!',
                            ),
                            extra={
                                'message_base_from_extra_dict': 'from extra dict',
                            },
                        )
                    ),
                    expected_output={
                        **get_output_base(level='WARNING'),
                        **(
                            {
                                # Under PyPy, the order of keys in a log record's
                                # `__dict__` may be different from insertion order
                                # (see: https://github.com/pypy/pypy/issues/5436).
                                # In some cases, this affects the order in which
                                # *output data* keys are inserted and deduplicated
                                # with `_` suffixes...
                                'message': AnyOfType(str),
                                'message_': AnyOfType(str),
                            } if sys.implementation.name == 'pypy'
                            else {
                                'message': 'message from auto-maker',
                                'message_': 'actual msg passed, 42',
                            }
                        ),
                        'message_base': {
                            'pattern': 'actual msg passed, {}',
                        },
                        'message_base_': 'from xm',
                        'message_base__': 'from auto-maker',
                        'message_base___': 'from extra auto-maker',
                        'message_base____': 'the Brave',
                        'message_base_____': 'the Pure',
                        'message_base______': 'from extra dict',
                        'msg': 'Tro-lo-lo-lo-lo!',
                        'Sir Galahad': 'Galahad-from-auto-maker',
                        'Sir Lancelot': 'Lancelot-from-auto-maker',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'message_base': '...NOT-used...',  # (to be shadowed by *void* default)
                        'msg': 'Ni!',
                        'Sir Galahad': '',  # (*void* value)
                        'system': EXAMPLE_SYSTEM,
                    },
                    base_auto_makers={
                        'message_base': ConstantValueAutoMaker(''),  # (*void* value)
                        'Sir Galahad': ConstantValueAutoMaker(()),  # (*void* value)
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                    },
                    base_record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'Sir Galahad': 'message_base',
                        'Sir Lancelot': 'message_base',
                        'message_base_from_extra_dict': 'message_base',
                    },
                ),
                dict(
                    defaults={
                        'message_base': '',  # (*void* value, shadowing that from `base_defaults`)
                        'Sir Lancelot': None,  # (*void* value)
                    },
                    auto_makers={
                        'message': ConstantValueAutoMaker(''),  # (*void* value)
                        'Sir Lancelot': ConstantValueAutoMaker(''),  # (*void* value)
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                SpecificLogCase(
                    lambda logger: (
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='message_base',
                            auto_maker=ConstantValueAutoMaker(None),  # (*void* value)
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Lancelot',
                            auto_maker=ConstantValueAutoMaker(()),  # (*void* value)
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Galahad',
                            auto_maker=ConstantValueAutoMaker(''),  # (*void* value)
                        ) or
                        logger.warning(   # noqa
                            xm(
                                'actual msg passed, {}',
                                42,
                                message_base='',  # (*void* value)
                                msg=None,  # (*void* value)
                            ),
                            extra={
                                'message_base_from_extra_dict': (),  # (*void* value)
                            },
                        )
                    ),
                    expected_output={
                        **get_output_base(level='WARNING'),
                        'message': 'actual msg passed, 42',
                        'message_base': {
                            'pattern': 'actual msg passed, {}',
                        },
                        'msg': 'Ni!',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'message_base': '...NOT-used...',  # (to be shadowed by *void* default)
                        'msg': '',  # (*void* value)
                        'Sir Galahad': '',  # (*void* value)
                        'system': EXAMPLE_SYSTEM,
                    },
                    base_auto_makers={
                        'message_base': ConstantValueAutoMaker(''),  # (*void* value)
                        'Sir Galahad': ConstantValueAutoMaker(()),  # (*void* value)
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                    },
                    base_record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'Sir Galahad': 'message_base',
                        'Sir Lancelot': 'message_base',
                        'message_base_from_extra_dict': 'message_base',
                    },
                ),
                dict(
                    defaults={
                        'message_base': '',  # (*void* value, shadowing that from `base_defaults`)
                        'Sir Lancelot': None,  # (*void* value)
                    },
                    auto_makers={
                        'message': ConstantValueAutoMaker(''),  # (*void* value)
                        'Sir Lancelot': ConstantValueAutoMaker(''),  # (*void* value)
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                    },
                ),
                SpecificLogCase(
                    lambda logger: (
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='message_base',
                            auto_maker=ConstantValueAutoMaker(None),  # (*void* value)
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Lancelot',
                            auto_maker=ConstantValueAutoMaker(()),  # (*void* value)
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Galahad',
                            auto_maker=ConstantValueAutoMaker(''),  # (*void* value)
                        ) or
                        logger.warning(   # noqa
                            xm(
                                message_base='',  # (*void* value)
                                msg=None,  # (*void* value)
                            ),
                            extra={
                                'message_base_from_extra_dict': (
                                    'Ekke Ekke Ekke Ekke Ptang Zoo Boing!'
                                ),
                            },
                        )
                    ),
                    expected_output={
                        **get_output_base(level='WARNING'),
                        'message_base': 'Ekke Ekke Ekke Ekke Ptang Zoo Boing!',
                        'system': EXAMPLE_SYSTEM,
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
            (
                make_StructuredLogsFormatter_subclass(
                    base_defaults={
                        'exc_info': 'Ha! (from base defaults!)',
                    },
                    base_auto_makers={
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        'err': ConstantValueAutoMaker('from auto-maker'),
                    },
                    base_record_attr_to_output_key={
                        **STANDARD_RECORD_ATTR_TO_OUTPUT_KEY,
                        'exc_info': 'err',
                        'exc_text': 'err',
                        'Sir Bedevere': 'err',
                        'Sir Robin': 'err',
                    },
                ),
                dict(
                    defaults={
                        'system': 'Default System',
                        'exc_text': (
                            'Not-Appearing-in-this-Film, because '
                            'kwarg to xm() will override this...'
                        ),
                    },
                    auto_makers={
                        'component': ConstantValueAutoMaker(EXAMPLE_COMPONENT),
                    },
                ),
                SpecificLogCase(
                    lambda logger: (
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='err',
                            auto_maker=ConstantValueAutoMaker('from extra auto-maker'),
                        ) or
                        register_log_record_attr_auto_maker(   # noqa
                            rec_attr='Sir Bedevere',
                            auto_maker=ConstantValueAutoMaker('the Wise'),
                        ) or
                        logger.error(   # noqa
                            xm(
                                exc_text='from `exc_text` kwarg to xm(): override the default',
                                err='from `err` kwarg to xm()',
                                exc_info=(ValueError, ValueError('from xm!!!'), None),
                                component=[],  # (*void* value)
                                component_type=['Ho-ho-ho-ho-ho!'],
                            ),
                            exc_info=NameError(42, 'from `exc_info` kwarg to logger.error()'),
                            extra={
                                'Sir Robin': 'Not-Quite-So-Brave-as-Sir-Lancelot',
                                'system': None,  # (*void* value)
                                'component': {
                                    "Gimli's line": 'Stick an arrow in his gob!',
                                },
                            },
                        )
                    ),
                    expected_output={
                        **get_output_base(level='ERROR'),

                        # From `xm`'s `exc_info`:
                        'err': {
                            'exc_type': 'ValueError',
                            'args': ['from xm!!!'],
                        },
                        # `xm`'s `exc_text`:
                        'err_': 'ValueError: from xm!!!',

                        'err__': 'from `err` kwarg to xm()',

                        # From log record's `exc_info`:
                        'err___': {
                            'exc_type': 'NameError',
                            'args': [42, 'from `exc_info` kwarg to logger.error()'],
                        },
                        # Log record's `exc_text`:
                        'err____': "NameError: (42, 'from `exc_info` kwarg to logger.error()')",

                        'err_____': 'from auto-maker',
                        'err______': 'from extra auto-maker',
                        'err_______': 'the Wise',
                        'err________': 'Not-Quite-So-Brave-as-Sir-Lancelot',

                        'exc_info': 'Ha! (from base defaults!)',
                        'exc_text': 'from `exc_text` kwarg to xm(): override the default',

                        'system': 'Default System',
                        'component': EXAMPLE_COMPONENT,
                        'component_': {
                            "Gimli's line": 'Stick an arrow in his gob!',
                        },
                        'component_type': ['Ho-ho-ho-ho-ho!'],
                        'component_type_': EXAMPLE_COMPONENT_TYPE,
                    },
                ),
            ),
        ]
    )
    def test_log_deduplicating_some_output_keys(
        self,
        log_handler,
        logger,
        log_case,
    ):
        log_case.logger_method_call(logger)

        assert log_handler.output_list == [log_case.expected_output]


    @pytest.mark.parametrize(
        'log_case',
        [
            LogCase(
                lambda logger: logger.error(
                    'Error occurred!',
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    'message': 'Error occurred!',
                    'message_base': 'Error occurred!',
                },
            ),
            LogCase(
                lambda logger: logger.critical(
                    'Error occurred! %d',
                    123,
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='CRITICAL'),
                    'message': 'Error occurred! 123',
                    'message_base': 'Error occurred! %d',
                },
            ),
            LogCase(
                lambda logger: logger.debug(
                    xm('Error occurred!'),
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='DEBUG'),
                    'message': 'Error occurred!',
                    'message_base': {'pattern': 'Error occurred!'},
                },
            ),
            LogCase(
                lambda logger: logger.info(
                    xm('Error occurred!', exc_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='INFO'),
                    'message': 'Error occurred!',
                    'message_base': {'pattern': 'Error occurred!'},
                },
            ),
            LogCase(
                lambda logger: logger.warning(
                    xm('Error occurred! {n}', n=123),
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='WARNING'),
                    'message': 'Error occurred! 123',
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'n': 123,
                },
            ),
            LogCase(
                lambda logger: logger.error(
                    xm('Error occurred! {n}', n=123, exc_info=True)
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    'message': 'Error occurred! 123',
                    'message_base': {'pattern': 'Error occurred! {n}'},
                    'n': 123,
                },
            ),
            LogCase(
                lambda logger: logger.critical(
                    xm(),
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='CRITICAL'),
                },
            ),
            LogCase(
                lambda logger: logger.debug(
                    xm(exc_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='DEBUG'),
                },
            ),
            LogCase(
                lambda logger: logger.info(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),   # type: ignore[call-overload]   # noqa
                ),
                expected_output_base={
                    **get_output_base(level='INFO'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                lambda logger: logger.warning(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='WARNING'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.error(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),   # type: ignore[call-overload]   # noqa
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.log(
                    logging.CRITICAL,
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                    exc_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='CRITICAL'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                lambda logger: logger.exception(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS)),   # type: ignore[call-overload]   # noqa
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                lambda logger: logger.exception(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS)),
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.exception(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),   # type: ignore[call-overload]   # noqa
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                # (Rather a contrived case, yet still properly handled)
                lambda logger: logger.exception(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), exc_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        ('make_exc', 'expected_exc_based_output_items'),
        [
            (
                None,
                {},
            ),
            (
                exc_maker(KeyboardInterrupt, args=()),
                {
                    'exc_info': {
                        'exc_type': 'KeyboardInterrupt',
                    },
                    'exc_text': AnyOfType(str),
                },
            ),
            (
                exc_maker(ValueError, args=('auć',)),
                {
                    'exc_info': {
                        'exc_type': 'ValueError',
                        'args': ['auć'],
                    },
                    'exc_text': AnyOfType(str),
                },
            ),
            (
                exc_maker(KeyError, args=(), instance_attrs={'x': 1, 'y': 0}),
                {
                    'exc_info': {
                        'exc_type': 'KeyError',
                        'dict': {'x': 1, 'y': 0},
                    },
                    'exc_text': AnyOfType(str),
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
                    'exc_info': {
                        'exc_type': 'ipaddress.AddressValueError',
                        'args': ['auć', 0.0, None],
                        'dict': {
                            'foo': {'42': ['spam', 'parrot']},
                            'bar': '2025-12-24 16:01:12+00:00',
                            '__notes__': ['abc', 'Efg Hi Jkl'],
                        },
                    },
                    'exc_text': AnyOfType(str),
                },
            ),
        ],
    )
    def test_log_with_exc_info_set_to_true(
        self,
        make_exc,
        logger,
        log_handler,
        log_case,
        expected_exc_based_output_items,
    ):
        if make_exc is None:
            log_case.logger_method_call(logger)
        else:
            try:
                raise make_exc()
            except BaseException:   # noqa
                log_case.logger_method_call(logger)

        assert log_handler.output_list == [{
            **log_case.expected_output_base,
            **expected_exc_based_output_items,
            'system': EXAMPLE_SYSTEM,
            'component': EXAMPLE_COMPONENT,
            'component_type': EXAMPLE_COMPONENT_TYPE,
        }]
        exc_info = log_handler.last_output.get('exc_info')
        exc_text = log_handler.last_output.get('exc_text')
        if make_exc is None:
            assert not expected_exc_based_output_items
            assert exc_info is None
            assert exc_text is None
        else:
            assert expected_exc_based_output_items.keys() == {'exc_info', 'exc_text'}
            assert exc_info
            assert exc_text
            assert exc_text.startswith('Traceback (most recent call last):\n')
            assert 'test_log_with_exc_info_set_to_true' in exc_text
            assert exc_info['exc_type'] in exc_text


    @pytest.mark.skip('...test not implemented yet...')
    def test_log_with_exc_info_set_to_exception_or_exc_info_tuple(
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.parametrize(
        'log_case',
        [
            LogCase(
                lambda logger: logger.debug(
                    'Something happened!',
                    stack_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='DEBUG'),
                    'message': 'Something happened!',
                    'message_base': 'Something happened!',
                },
            ),
            LogCase(
                lambda logger: logger.info(
                    'Something happened! %d',
                    123,
                    stack_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='INFO'),
                    'message': 'Something happened! 123',
                    'message_base': 'Something happened! %d',
                },
            ),
            LogCase(
                lambda logger: logger.warning(
                    xm('Something happened!'),
                    stack_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='WARNING'),
                    'message': 'Something happened!',
                    'message_base': {'pattern': 'Something happened!'},
                },
            ),
            LogCase(
                lambda logger: logger.error(
                    xm('Something happened!', stack_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    'message': 'Something happened!',
                    'message_base': {'pattern': 'Something happened!'},
                },
            ),
            LogCase(
                lambda logger: logger.critical(
                    xm('Something happened! {n}', n=123),
                    stack_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='CRITICAL'),
                    'message': 'Something happened! 123',
                    'message_base': {'pattern': 'Something happened! {n}'},
                    'n': 123,
                },
            ),
            LogCase(
                lambda logger: logger.debug(
                    xm('Something happened! {n}', n=123, stack_info=True)
                ),
                expected_output_base={
                    **get_output_base(level='DEBUG'),
                    'message': 'Something happened! 123',
                    'message_base': {'pattern': 'Something happened! {n}'},
                    'n': 123,
                },
            ),
            LogCase(
                lambda logger: logger.info(
                    xm(),
                    stack_info=True,
                ),
                expected_output_base={
                    **get_output_base(level='INFO'),
                },
            ),
            LogCase(
                lambda logger: logger.warning(
                    xm(stack_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='WARNING'),
                },
            ),
            LogCase(
                lambda logger: logger.error(
                    xm(**deepcopy(EXAMPLE_CUSTOM_ITEMS), stack_info=True),   # type: ignore[call-overload]   # noqa
                ),
                expected_output_base={
                    **get_output_base(level='ERROR'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
            LogCase(
                lambda logger: logger.critical(
                    xm(deepcopy(EXAMPLE_CUSTOM_ITEMS), stack_info=True),
                ),
                expected_output_base={
                    **get_output_base(level='CRITICAL'),
                    **EXAMPLE_PREPARED_CUSTOM_OUTPUT_ITEMS,
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        'while_exception_is_being_handled',
        [False, True],
    )
    def test_log_with_stack_info_set_to_true(
        self,
        logger,
        log_handler,
        log_case,
        while_exception_is_being_handled,
    ):
        def a(): log_case.logger_method_call(logger)
        def b():
            if while_exception_is_being_handled:
                try: 1/0
                except ZeroDivisionError:
                    a()
            else:
                a()
        def c(): b()

        c()

        assert log_handler.output_list == [{
            **log_case.expected_output_base,
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
        assert stack_lines[-5].endswith('  a()')
        assert stack_lines[-4].endswith('in a')
        assert stack_lines[-3].endswith('  def a(): log_case.logger_method_call(logger)')
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
    @pytest.mark.parametrize(
        'while_exception_is_being_handled',
        [False, True],
    )
    def test_log_with_stack_info_set_to_true_and_stacklevel_specified(
        self,
        log_handler,
        logger,
        stacklevel,
        pass_kwargs_to_xm,
        while_exception_is_being_handled,
    ):
        stack_related_kwargs = dict(
            stack_info=True,
            stacklevel=stacklevel,
        )

        def a():
            logger.info(
                xm(   # type: ignore[call-overload]
                    **deepcopy(EXAMPLE_CUSTOM_ITEMS),
                    **(stack_related_kwargs if pass_kwargs_to_xm else {}),
                ),
                **({} if pass_kwargs_to_xm else stack_related_kwargs),
            )
        def b():
            if while_exception_is_being_handled:
                try: 1/0
                except ZeroDivisionError:
                    a()
            else:
                a()
        def c(): b()

        expected_stack_line_suffixes = [
            'in test_log_with_stack_info_set_to_true_and_stacklevel_specified',
            '  c()',
            'in c',
            '  def c(): b()',
            'in b',
            '  a()',
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


    @pytest.mark.skip('...test not implemented yet...')
    def test_log_with_formatTime_obtaining_non_none_datefmt_causes_printing_type_error_to_stderr(   # noqa
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.skip('...test not implemented yet...')
    def test_multiple_formatters_used_simultaneously_work_independently_of_each_other(
        # TODO: in particular, each uses the stuff produced by its own *auto-makers*,
        #       ignoring any stuff produced by other formatter instances.
        self,
    ):
        TODO   # type: ignore[name-defined]


    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_factory',
            'formatter_init_kwargs',
        ),
        [
            (
                StructuredLogsFormatter,
                dict(
                    defaults={
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
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
                        'blah_blah_blah': None,  # (*void* value)
                        'component_type': 'a default TO BE OVERRIDDEN...',
                        'system': EXAMPLE_SYSTEM,
                        'zero': 0,
                    },
                    auto_makers={
                        'component': (
                            ConstantValueAutoMaker(EXAMPLE_COMPONENT).importable_dotted_name
                        ),
                        'component_type': ConstantValueAutoMaker(EXAMPLE_COMPONENT_TYPE),
                        'foo': ConstantValueAutoMaker(None),
                        'system': (
                            # (A *void* value does *not* mask the default...)
                            ConstantValueAutoMaker(None).importable_dotted_name
                        ),
                        'xyz': ConstantValueAutoMaker(dt.date(2026, 4, 27)),
                    },
                    serializer=example_serializer.importable_dotted_name,
                ),
            ),
            (
                ExampleSubclassOfStructuredLogsFormatter,
                dict(),
            )
        ],
    )
    @pytest.mark.parametrize(
        (
            # (Overriding these fixtures)
            'formatter_init_kwargs_passing_variant',
            'prepare_formatter_init_kwargs_mapping',
        ),
        [
            (FormatterInitKwargsPassingVariant.DIRECT, sentinel.UNUSED),
            (FormatterInitKwargsPassingVariant.MAPPING, dict),
            (FormatterInitKwargsPassingVariant.MAPPING, ExampleNonDictMutableMapping),
            (FormatterInitKwargsPassingVariant.MAPPING, types.MappingProxyType),
            (FormatterInitKwargsPassingVariant.STRING, sentinel.UNUSED),
        ],
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
                        'zero': 0,
                        **(
                            {
                                # Under PyPy, the order of keys in a log record's
                                # `__dict__` may be different from insertion order
                                # (see: https://github.com/pypy/pypy/issues/5436).
                                # In some cases, this affects the order in which
                                # *output data* keys are inserted and deduplicated
                                # with `_` suffixes...
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
                    },
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='DEBUG'),
                        'func': '<lambda>',
                        # No 'message_base'/'message' [!]
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                            blah_blah_blah='ut-re-mi-fa-sol-la-si',
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
                        'xyz': '2026-04-27',
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
                        'blah_blah_blah': 'ut-re-mi-fa-sol-la-si',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'something_else': [{'42': 42}],
                        'system': EXAMPLE_SYSTEM,  # (*not* masked by a *void* value)
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'system': EXAMPLE_SYSTEM,  # (*not* masked by a *void* value)
                        'xyz': '2026-04-27',
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
                            'test_log_various_cases_including_some_complex_or_contrived_ones'
                        ),
                        'message': "Example message - Foo, 'spam', 0042, %",
                        'message_base': 'Example message - %s, %r, %04d, %%',
                        'component': EXAMPLE_COMPONENT,
                        'component_type': EXAMPLE_COMPONENT_TYPE,
                        'system': EXAMPLE_SYSTEM,
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='ERROR'),
                        'func': (
                            'test_log_various_cases_including_some_complex_or_contrived_ones'
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
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                    {
                        **get_output_base(level='CRITICAL'),
                        'func': (
                            'test_log_various_cases_including_some_complex_or_contrived_ones'
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
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
                        'xyz': '2026-04-27',
                        'zero': 0,
                    },
                ],
                id='with_stacklevel_specified',
            ),
        ],
    )
    def test_log_various_cases_including_some_complex_or_contrived_ones(
        self,
        logger,
        logger_method_calls,
        log_handler,
        expected_output_list,
    ):
        for log_call in logger_method_calls:
            log_call(logger)

        assert log_handler.output_list == expected_output_list


    @pytest.mark.skip('...test not implemented yet...')
    def test_unregister_auto_makers(
        self,
    ):
        TODO   # type: ignore[name-defined]


@pytest.mark.skip('...tests not implemented yet...')
class TestExtendedMessage:
    def xm_is_alias_of_ExtendedMessage(self):  # noqa
        TODO   # type: ignore[name-defined]
    def test_TODO(self):
        TODO   # type: ignore[name-defined]


@pytest.mark.skip('...tests not implemented yet...')
class TestAutoMakersRegistryFunctions:
    def test_TODO(self):
        TODO   # type: ignore[name-defined]


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
                ```           # <- 3 backticks denoting beginning of snippet

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
                ```           # <- 3 backticks denoting end of snippet
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
            no_substring: str | None = None,
            syntax_label: str = 'python',
            mark_as_covered: bool = True,
        ) -> str:

            def matches(snippet) -> bool:
                return (
                    snippet.syntax_label == syntax_label
                    and substring in snippet.dedented_content
                    and (
                        no_substring is None
                        or no_substring not in snippet.dedented_content
                    )
                )

            matching_snippets = [
                snippet
                for snippet in self._all_snippets_sorted_by_start_lineno
                if matches(snippet)
            ]
            if not matching_snippets:
                raise AssertionError(
                    f'no matching snippet found in {self._source_descr} '
                    f'({syntax_label=}, {substring=}, {no_substring=})'
                )
            try:
                [the_snippet] = matching_snippets
            except ValueError as exc:
                listing = '\n'.join(map(str, matching_snippets))
                raise AssertionError(
                    f'{len(matching_snippets)} matching snippets '
                    f'(more than one) found in {self._source_descr} '
                    f'({syntax_label=}, {substring=}, {no_substring=}):'
                    f'\n\n{listing}'
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
            # `dt.date.today()`'s results presented in our snippets...)
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


    classmethod_if_supported: Callable[[Any], Any] = (
        # TODO: get rid of it after dropping unofficial support for Py3.9
        (lambda func: func) if pytest.version_tuple[0] < 9   # type: ignore[operator]
        else classmethod
    )

    @pytest.fixture(scope='class')
    @classmethod_if_supported
    def snippet_finder(cls) -> Generator[_SnippetFinder]:
        snippet_finder = cls._SnippetFinder(certlib.log)
        yield snippet_finder
        snippet_finder.assert_all_snippets_covered()

    @pytest.fixture(scope='class', autouse=True)
    @classmethod_if_supported
    def mark_uninteresting_snippets_as_covered(cls, snippet_finder):
        # Testing these code snippets would
        # be hard and/or not very beneficial:
        snippet_finder.lookup(substring='install', syntax_label='bash')
        snippet_finder.lookup(substring='client_ip_context_var =')
        snippet_finder.lookup(substring='# WRONG (!!!):')
        snippet_finder.lookup(substring='# All WRONG (!!!):')
        snippet_finder.lookup(substring='__call__() -> Value')
        snippet_finder.lookup(substring='__call__(output_data')
        snippet_finder.lookup(substring='__call__(conf: ConfDict')

    @pytest.fixture(scope='class')
    @classmethod_if_supported
    def client_ip_context_var(cls) -> contextvars.ContextVar[ipaddress.IPv4Address]:
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

    # (This fixture is overridden for some tests...)
    @pytest.fixture
    def customized_formatter_cls_module_and_name(self) -> tuple[str, str] | None:
        return None

    @pytest.fixture(params=[
        'imperative',
        'dictConfig',
        'fileConfig',
    ])
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

        # TODO: restore `match` after dropping unofficial support for Py3.9
        if config_snippet_label == 'imperative':
        # match config_snippet_label:
        #     case 'imperative':
                config_snippet = '\n'.join([
                    snippet_finder.lookup(
                        substring='structured_logs_formatter = StructuredLogsFormatter(',
                        no_substring='conf_corrector',
                        mark_as_covered=mark_as_covered,
                    ),
                    snippet_finder.lookup(
                        substring='# (continuing with our main example)',
                        mark_as_covered=mark_as_covered,
                    ),
                ])
        elif config_snippet_label == 'dictConfig':
            # case 'dictConfig':
                config_snippet = snippet_finder.lookup(
                    substring='logging.config.dictConfig(logging_configuration_dict)',
                    mark_as_covered=mark_as_covered,
                )
        elif config_snippet_label == 'fileConfig':
            # case 'fileConfig':
                config_snippet = snippet_finder.lookup(
                    substring='class = certlib.log.StructuredLogsFormatter',
                    syntax_label='ini',
                    mark_as_covered=mark_as_covered,
                )
        else:
            raise AssertionError(f'unrecognized_label={config_snippet_label!r}')
            # case unrecognized_label:
            #     raise AssertionError(f'{unrecognized_label=}')

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
            # ^ Both refer to a serializer using the *dotted path*:
            #   'some_package.faster_replacement_for_json_dumps'.
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

    # (This fixture is overridden for some tests...)
    @pytest.fixture
    def expected_utc_formatted_timestamp(self, request) -> str:
        return '2026-02-20 23:14:47.019574Z'

    @pytest.fixture
    def expected_posix_timestamp(self, expected_utc_formatted_timestamp):
        without_tz = expected_utc_formatted_timestamp.removesuffix('Z')
        return dt.datetime.fromisoformat(f'{without_tz}+00:00').timestamp()

    @pytest.fixture
    def expected_posix_timestamp_ns(self, expected_posix_timestamp):
        return 10**3 * int(10**6 * expected_posix_timestamp)

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
            'timestamp': expected_utc_formatted_timestamp,
        }
        if 'TLDR' not in config_snippet_label:
            items |= {
                'client_ip': '192.168.0.123',
                'component': 'Portal',
                'component_type': 'web',
                'nano_time': AnyOfType(int),
                'system': 'MyOwn',
                'the_answer': 42,
            }
        if config_snippet_label == 'imperative':
            # Not included in `dictConfig`/`fileConfig` config snippets:
            items['just_local_counter'] = AnyOfType(int)
        return items

    @pytest.fixture
    def extract_and_adjust_json_snippet_items(
        self,
        snippet_finder,
        config_snippet_label,
    ) -> Callable[..., dict[str, Any]]:

        def extract_and_adjust_json_snippet_items_impl(substring):
            snippet = snippet_finder.lookup(substring, syntax_label='json')
            items = json.loads(snippet)
            items['pid'] = os.getpid()
            if config_snippet_label != 'imperative':
                # Not included in `dictConfig`/`fileConfig` config snippets:
                del items['just_local_counter']
            return items

        return extract_and_adjust_json_snippet_items_impl

    # Overrides the module-wide fixture of the same name
    @pytest.fixture(autouse=True)
    def monkeypatch_relevant_time_functions(
        self,
        monkeypatch,
        expected_posix_timestamp_ns,
        expected_posix_timestamp,
    ):
        monkeypatch.setattr(
            logging, 'time', TimeModuleFakingProxy(expected_posix_timestamp_ns),
        )
        monkeypatch.setattr(
            dt, 'date', self._DateClassFakingProxy(expected_posix_timestamp),
        )


    def test_user_guide_tldr_imperative_conf_snippet(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        config_snippet = snippet_finder.lookup(
            substring='some_handler = logging.StreamHandler()',
        )
        pytest.skip('...test not implemented yet...')


    def test_user_guide_tldr_dict_conf_snippet(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        config_snippet = snippet_finder.lookup(
            substring='{"fmt": {"()": "certlib.log.StructuredLogsFormatter"}}',
        )
        pytest.skip('...test not implemented yet...')


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


    def test_user_guide_formatter_simple_subclass_snippet(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        config_snippet = snippet_finder.lookup(
            substring='class MyDreamFormatter(',
        )
        pytest.skip('...test not implemented yet...')


    def test_user_guide_conf_corrector_snippets(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        for substring, no_substring in [
            ('def my_conf_corrector', 'extra_required_keys ='),
            ('conf_corrector=my', '"platform.architecture"'),
            ('"conf_corrector": "my', '"platform.architecture"'),
            ('"platform.architecture"', '"conf_corrector_params":'),
            ('"platform.architecture"', 'conf_corrector_params='),
            ('extra_required_keys =', None),
        ]:
            snippet_finder.lookup(substring, no_substring=no_substring)
        pytest.skip('...test not implemented yet...')


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
        # (Overriding fixture)
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
            snippet_finder.lookup(
                substring=substring,
                no_substring=no_substring,
            )
            for substring, no_substring in [
                ('(in {:%Y-%m})"', None),
                ('(in {2:%Y-%m})"', None),
                ('(in {today:%Y-%m})"', 'something_more=(1,'),
                ('something_more=(1,', None),
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
                    'pattern': 'Note: {} is {.attr[item]!r} (in {:%Y-%m})',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {0} is {1.attr[item]!r} (in {2:%Y-%m})',
                },
            },
            {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {} is {obj.attr[item]!r} (in {today:%Y-%m})',
                },
                'obj': '<our object>',
                'today': '2026-02-21',
            },
            last_expected_output := {
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'myown.portal.another_example_module',
                'message': f"Note: foo is 'Bar' (in 2026-02)",
                'message_base': {
                    'pattern': 'Note: {} is {obj.attr[item]!r} (in {today:%Y-%m})',
                },
                'obj': '<our object>',
                'today': '2026-02-21',
                'something': 123456789,
                'something_more': [1, 2, 3, 4, True, None, {'5': [6789, 10]}],
            },
        ]
        assert last_expected_output == extract_and_adjust_json_snippet_items(
            substring='"logger": "myown.portal.another_example_module"',
        )


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'customized_formatter_cls_module_and_name',
        [
            (
                'myown.portal.example_module',
                'EstTimezoneOrientedStructuredLogsFormatter',
            )
        ],
    )
    def test_reference_formatter_format_timestamp_snippet(
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
                'func': 'test_reference_formatter_format_timestamp_snippet',
                'timestamp': '2026-02-20 18:14:47.019574 EST',
            },
        ]


    @pytest.mark.parametrize(
        # (Overriding fixture)
        'customized_formatter_cls_module_and_name',
        [
            (
                'myown.portal.another_example_module',
                'MyEnhancedStructuredLogsFormatter',
            )
        ],
    )
    def test_reference_formatter_prepare_value_snippet(
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
        # TODO: remove this after dropping unofficial support for Py3.9:
        if sys.version_info[:2] == (3, 9):
            snippet = snippet.replace('@staticmethod', '')
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
                'func': 'test_reference_formatter_prepare_value_snippet',
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


    def test_reference_xm_constructor_snippets(
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
                **get_output_base(level='INFO'),
                **commonly_expected_output_items,
                'logger': 'root',
                'message': f'Python {sys.version_info[0]}.{sys.version_info[1]}',
                'message_base': {
                    'pattern': 'Python {sys.version_info[0]}.{sys.version_info[1]}',
                },
                'sys': repr(sys),
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
                    'func': 'test_reference_xm_constructor_snippets',  # [sic!]
                    'logger': EXAMPLE_LOGGER_NAME,
                    'message': 'Foo',
                    'message_base': {
                        'pattern': 'Foo',
                    },
                },
                {
                    **get_output_base(level='INFO'),
                    **commonly_expected_output_items,
                    'func': 'test_reference_xm_constructor_snippets',  # [sic!]
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


    def test_reference_typed_dict_snippets(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
    ):
        for substring in [
            '"ConfDict", {',
            '"CorrectedConfDict", {',
        ]:
            snippet_finder.lookup(substring)
        pytest.skip('...test not implemented yet...')


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
        # Prepare necessary modules:
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
                snippet_finder.lookup(substring='example_with_text_message_formatting'),
                myexample.lib.__dict__,
            )
            exec(
                snippet_finder.lookup(substring='example_with_no_text'),
                myexample.lib.__dict__,
            )
            # Let's call the functions defined in some snippets...
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
                'message': 'Today is day #052 of year 2026',
                'message_base': {
                    'pattern': '{what[a].b[c]} is day #{today:%j} of year {today:%Y}',
                },
                'what': {'a': {'b': {'c': 'Today'}}},
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
                'message': 'Today is day #052 of year 2026',
                'message_base': {
                    'pattern': '{what[a].b[c]} is day #{today:%j} of year {today:%Y}',
                },
                'what': {'a': {'b': {'c': 'Today'}}},
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

        # Let's separately test the *minimal setup* snippet
        # (the one placed in README as the first one):
        sub = 'some_handler = logging.StreamHandler()'
        sub_upd = f'{sub}; some_handler.name = "stderr"'  # <- Just to ease cleanup
        simple_snippet = snippet_finder.lookup(substring=sub).replace(sub, sub_upd)
        with self._finally_undoing_our_tweaks_to_root_logger():
            exec(simple_snippet, {})
            logging.getLogger('some').warning('Here!')
        assert get_actual_output_list() == [
            {
                **get_output_base(level='WARNING'),
                'func': 'test_readme_snippets',
                'logger': 'some',
                'message': 'Here!',
                'message_base': 'Here!',
                'timestamp': expected_utc_formatted_timestamp,
            },
        ]

        # Also, let's separately test (superficially) the
        # *example log entry* snippet:
        json_snippet = snippet_finder.lookup(
            substring="Request from '10.20.30.40'",
            syntax_label='json',
        )
        assert isinstance(json.loads(json_snippet), dict)

        snippet_finder.assert_all_snippets_covered()


    #
    # Tests related to snippets in unofficial extra stuff docstrings


    def test_extra_non_public_opinionated_conf_corrector_snippets(
        self,
        monkeypatch,
        snippet_finder,
        get_actual_output_list,
        expected_utc_formatted_timestamp,
        expected_posix_timestamp_ns,
    ):
        config_snippet = snippet_finder.lookup(
            substring='"keyword": "flask_app",',
        )
        ext_setup_completion_snippet = snippet_finder.lookup(
            substring='_complete_ext_setup(flask_app=app)'
        )

        # * Prepare necessary fakes:

        class FakeFlaskApp:
            def __init__(self, name):
                assert name == 'my_flask_based_app'
                assert 'on_start' not in vars(fake_request_lifecycle)
            def before_request(self, callback, /):
                fake_request_lifecycle.on_start = callback
            def after_request(self, callback, /):
                fake_request_lifecycle.on_finish = callback
            def teardown_request(self, callback, /):
                fake_request_lifecycle.on_cleanup = callback

        class FakeRequestLifecycle:
            def __init__(self):
                self._handling = False
            def is_being_handled(self):
                return self._handling
            def start(self):
                self._handling = True
                self.on_start()
            def finish(self):
                resp = self.on_finish(fake_response)
                self._handling = False
                assert resp is fake_response
            def cleanup(self):
                self.on_cleanup(None)
            on_start: Callable[[], None]
            on_finish: Callable[[Any], Any]
            on_cleanup: Callable[[Any], None]

        fake_request_lifecycle = FakeRequestLifecycle()
        fake_request = SimpleNamespace(
            headers=Mock(
                getlist=Mock(return_value=['1.2.3.4']),
                get=Mock(return_value='some-request-id'),
            ),
            remote_addr='10.11.12.13',
            host='camelot.example.org',
            method='GET',
            path='/sir/Lancelot',
            query_string=b'question=What\xaais\xbbyour\xccquest',
            user_agent=ExampleSomethingWithCustomStrAndRepr(),
        )
        fake_response = SimpleNamespace(
            status_code=404,
        )
        custom_auto_makers_source = SimpleNamespace(get_auto_makers=lambda: {
            'Camelot!': lambda: "It's only a model.",
            'time_ns': 'logging.time.time_ns',
        })

        # * Prepare necessary modules and environment:

        flask = Module('flask')
        flask.Flask = FakeFlaskApp
        flask.request = fake_request
        flask.has_request_context = fake_request_lifecycle.is_being_handled

        my_flask_based_app = Module('my_flask_based_app')
        my_flask_based_app.custom_auto_makers_source = custom_auto_makers_source

        monkeypatch.setitem(sys.modules, 'flask', flask)
        monkeypatch.setitem(sys.modules, 'my_flask_based_app', my_flask_based_app)
        monkeypatch.setenv('CERT_LOG_TRUSTED_PROXIES', '10.9.8.7 10.11.12.13 10.3.2.1')

        # * Prepare expected output elements:

        expected_request_specific_output_items = {
            'remote_ip': '1.2.3.4',
            'remote_direct_ip': '10.11.12.13',
            'remote_x_forwarded_for': '1.2.3.4',
            'request_id': 'some-request-id',
            'request_host': 'camelot.example.org',
            'request_method': 'GET',
            'request_path': '/sir/Lancelot',
            'query_string': 'question=What\ufffdis\ufffdyour\ufffdquest',
            'user_agent': '-> STR <-',
        }
        def get_expected_output_base(**kw):
            output_base = get_output_base(**kw)
            output_base |= {
                'timestamp': expected_utc_formatted_timestamp,
                # From `defaults` in config snippet:
                'system': 'MyOwn',
                'component': 'Portal',
                'component_type': 'web',
                # From `_DefaultExtension`:
                'py_ver': '.'.join(map(str, sys.version_info[:3])),
                'tid': AnyOfType(int),
                # From `custom_auto_makers_source` (see above...) resolved by
                # `_ExtraAutoMakerSourcesExtension` (config-snipped-specified):
                'Camelot!': "It's only a model.",
                'time_ns': expected_posix_timestamp_ns,
            }
            # From `_DefaultExtension`:
            del output_base['thread_id']
            # From `base_record_attr_to_output_key_overrides` in config snippet:
            del output_base['thread_name']
            output_base['process_name_according_to_python_stdlib'] = (
                output_base.pop('process_name')
            )
            return output_base

        # * Actual test:

        with self._finally_undoing_our_tweaks_to_root_logger():
            exec(config_snippet, {})
            exec(ext_setup_completion_snippet, my_flask_based_app.__dict__)

            logger = logging.getLogger('my_flask_based_app.views')
            logger.warning('Outside request handler')

            fake_request_lifecycle.start()
            logger.warning('Inside request handler')
            fake_request_lifecycle.finish()

            logger.warning('Before after-request cleanup')
            fake_request_lifecycle.cleanup()
            logger.warning('Outside request handler again')

        assert get_actual_output_list() == [
            {
                **get_expected_output_base(level='WARNING'),
                'func': 'test_extra_non_public_opinionated_conf_corrector_snippets',
                'logger': 'my_flask_based_app.views',
                'message': 'Outside request handler',
            },
            {
                **get_expected_output_base(level='WARNING'),
                **expected_request_specific_output_items,    # <- Notice this.
                'func': 'test_extra_non_public_opinionated_conf_corrector_snippets',
                'logger': 'my_flask_based_app.views',
                'message': 'Inside request handler',
            },
            {
                # *** Automatically emitted *access log* entry ***
                **get_expected_output_base(level='INFO'),
                **expected_request_specific_output_items,    # <- Notice this.
                'func': 'on_request_finish',
                'logger': 'certlib.log.WEB_ACCESS',
                'response_status': 404,                      # <- Notice this.
                'request_duration_ms': AnyOfType(float),     # <- Notice this.
            },
            {
                **get_expected_output_base(level='WARNING'),
                **expected_request_specific_output_items,    # <- Notice this.
                'func': 'test_extra_non_public_opinionated_conf_corrector_snippets',
                'logger': 'my_flask_based_app.views',
                'message': 'Before after-request cleanup',
            },
            {
                **get_expected_output_base(level='WARNING'),
                'func': 'test_extra_non_public_opinionated_conf_corrector_snippets',
                'logger': 'my_flask_based_app.views',
                'message': 'Outside request handler again',
            },
        ]
        assert fake_request.headers.mock_calls == [
            call.getlist('X-Forwarded-For'),
            call.get('X-CERT-Request-ID'),
        ]


#
# Tests related to unofficial extra stuff


class TestContextBoundProperty:

    @pytest.fixture
    def doc(self):
        return 'some docstring'

    @pytest.fixture
    def prop_owner_cls(self, doc):
        class PropOwner:
            some = certlib.log._ContextBoundProperty(doc)      # type: ignore[var-annotated]
            another = certlib.log._ContextBoundProperty(doc)   # type: ignore[var-annotated]
        return PropOwner

    @pytest.fixture
    def prop_owner_subclass(self, prop_owner_cls):
        class PropOwnerSub(prop_owner_cls):   # type: ignore[valid-type,misc]
            pass
        return PropOwnerSub

    @pytest.fixture(params=[True, False])
    def target_cls(self, request, prop_owner_cls, prop_owner_subclass):
        return (
            prop_owner_subclass if request.param
            else prop_owner_cls
        )

    @pytest.fixture(params=[True, False])
    def second_target_cls(self, request, prop_owner_cls, prop_owner_subclass):
        return (
            prop_owner_subclass if request.param
            else prop_owner_cls
        )

    @pytest.fixture(params=[
        sentinel.VALUE,
        [123],
        None,
        float('nan'),
    ])
    def value(self, request):
        return request.param


    @pytest.mark.parametrize('doc', ['some docstring', None])
    def test_basics(self, target_cls, prop_owner_cls, doc):
        assert isinstance(target_cls.some, certlib.log._ContextBoundProperty)
        assert target_cls.some is vars(prop_owner_cls)['some']
        assert target_cls.some.__doc__ == doc
        assert target_cls.some.__name__ == 'some'
        assert target_cls.some.__module__ == __name__
        assert target_cls.some.__qualname__ == f'{prop_owner_cls.__qualname__}.some'
        assert repr(target_cls.some) == f'{__name__}.{prop_owner_cls.__qualname__}.some'


    @pytest.mark.parametrize('doc', ['some docstring', None])
    def test_basics_before_set_name(self, doc):
        # No call to `__set_name__()` has been made.
        some = certlib.log._ContextBoundProperty(doc)   # type: ignore[var-annotated]
        assert isinstance(some, certlib.log._ContextBoundProperty)
        assert some.__doc__ == doc
        assert repr(some) == object.__repr__(some)


    def test_attr_operations__same_target_instance__same_context__same_ctx_property(
        self, target_cls, value,
    ):
        # => operating on same value slot

        target = target_cls()
        assert not hasattr(target, 'some')

        target.some = value
        assert target.some is value

        del target.some
        assert not hasattr(target, 'some')


    def test_attr_operations__different_target_instances__same_context__same_ctx_property(
        self, target_cls, second_target_cls, value,
    ):
        # => operating on separate value slots independently

        target = target_cls()
        second_target = second_target_cls()

        target.some = value
        assert target.some is value
        assert not hasattr(second_target, 'some')

        second_target.some = 42
        assert target.some is value
        assert second_target.some == 42
        assert value != 42, "test's internal assumption"

        del target.some
        assert not hasattr(target, 'some')
        assert second_target.some == 42

        target.some = 42
        assert target.some == second_target.some == 42

        second_target.some += 1000
        assert target.some == 42
        assert second_target.some == 1042

        del second_target.some
        assert target.some == 42
        assert not hasattr(second_target, 'some')

        del target.some
        assert not hasattr(target, 'some')
        assert not hasattr(second_target, 'some')


    def test_attr_operations__same_target_instance__different_contexts__same_ctx_property(
        self, target_cls, value,
    ):
        # => operating on separate value slots independently

        target = target_cls()

        alt_context = contextvars.Context()
        def hasattr_within_alt_context():
            return alt_context.run(lambda: hasattr(target, 'some'))
        def getattr_within_alt_context():
            return alt_context.run(lambda: target.some)
        def setattr_within_alt_context(val):
            @alt_context.run
            def _(): target.some = val
        def delattr_within_alt_context():
            @alt_context.run
            def _(): del target.some

        target.some = value
        assert target.some is value
        assert not hasattr_within_alt_context()

        setattr_within_alt_context(42)
        assert target.some is value
        assert getattr_within_alt_context() == 42
        assert value != 42, "test's internal assumption"

        del target.some
        assert not hasattr(target, 'some')
        assert getattr_within_alt_context() == 42

        target.some = 42
        assert target.some == getattr_within_alt_context() == 42

        setattr_within_alt_context(getattr_within_alt_context() + 1000)
        assert target.some == 42
        assert getattr_within_alt_context() == 1042

        delattr_within_alt_context()
        assert target.some == 42
        assert not hasattr_within_alt_context()

        del target.some
        assert not hasattr(target, 'some')
        assert not hasattr_within_alt_context()


    def test_attr_operations__same_target_instance__same_context__different_ctx_properties(
        self, target_cls, value,
    ):
        # => operating on separate value slots independently

        target = target_cls()

        target.some = value
        assert target.some is value
        assert not hasattr(target, 'another')

        target.another = 42
        assert target.some is value
        assert target.another == 42
        assert value != 42, "test's internal assumption"

        del target.some
        assert not hasattr(target, 'some')
        assert target.another == 42

        target.some = 42
        assert target.some == target.another == 42

        target.another += 1000
        assert target.some == 42
        assert target.another == 1042

        del target.another
        assert target.some == 42
        assert not hasattr(target, 'another')

        del target.some
        assert not hasattr(target, 'some')
        assert not hasattr(target, 'another')


    def test_get_raises_attribute_error_if_value_is_missing(
        self, target_cls, value,
    ):
        target = target_cls()
        with pytest.raises(AttributeError):
            target.some  # noqa

        target.some = value
        assert target.some is value

        del target.some
        with pytest.raises(AttributeError):
            target.some  # noqa


    def test_delete_never_raises_attribute_error(
        self, target_cls, value,
    ):
        target = target_cls()
        assert not hasattr(target, 'some')
        for _ in range(3):
            del target.some
            assert not hasattr(target, 'some')

        target.some = value
        assert target.some is value

        for _ in range(3):
            del target.some
            assert not hasattr(target, 'some')


class TestCtxCachedDecorator:

    class PropOwnerSuper:
        pass

    class PropOwner(PropOwnerSuper):
        ctx_namespace = certlib.log._ContextBoundProperty()   # type: ignore[var-annotated]

    class PropOwnerSub(PropOwner):
        pass

    @pytest.fixture(params=[
        SimpleNamespace,
        dict,
        ExampleNonDictMutableMapping,
    ])
    def namespace_type(self, request):
        return request.param

    @pytest.fixture
    def provide_prop_owner_with_ctx_namespace_init_and_drop_methods(
        self,
        monkeypatch,
        namespace_type,
    ):
        def init_namespace(self):
            self.ctx_namespace = namespace_type(n=0)

        def remove_namespace(self, alt_context: contextvars.Context | None = None):
            del self.ctx_namespace

        monkeypatch.setattr(
            self.PropOwner, 'init_namespace', init_namespace, raising=False,
        )
        monkeypatch.setattr(
            self.PropOwner, 'remove_namespace', remove_namespace, raising=False,
        )

    @pytest.fixture
    def add_decorated_method(
        self,
        monkeypatch,
        namespace_type,
        provide_prop_owner_with_ctx_namespace_init_and_drop_methods,
    ):

        def add_decorated_method_impl(cls, method_name):
            if issubclass(namespace_type, SimpleNamespace):

                def method(self):  # noqa
                    """Net effect: increment `n` and return its value."""
                    assert isinstance(self.ctx_namespace, namespace_type)
                    n = self.ctx_namespace.n                     # get n
                    del self.ctx_namespace.n                     # delete n
                    assert not hasattr(self.ctx_namespace, 'n')  # get n
                    self.ctx_namespace.n = n + 1                 # set n
                    return self.ctx_namespace.n                  # get n

            elif issubclass(namespace_type, MutableMapping):

                def method(self):  # noqa
                    """Net effect: increment `n` and return its value."""
                    assert isinstance(self.ctx_namespace, namespace_type)
                    n = self.ctx_namespace['n']                  # get n
                    del self.ctx_namespace['n']                  # delete n
                    assert 'n' not in self.ctx_namespace         # contains n
                    self.ctx_namespace['n'] = n + 1              # set n
                    return self.ctx_namespace['n']               # get n

            else:
                raise AssertionError(f'unsupported type of {namespace_type=!r}')

            method.__module__ = cls.__module__
            method.__qualname__ = f'{cls.__qualname__}.{method_name}'
            method.__name__ = method_name

            decorator = certlib.log._ctx_cached(
                'ctx_namespace',
                fallback_result=sentinel.FALLBACK,
            )
            decorated_method = decorator(method)

            assert isinstance(decorated_method, Function)
            assert decorated_method.__module__ == cls.__module__
            assert decorated_method.__qualname__ == f'{cls.__qualname__}.{method_name}'
            assert decorated_method.__name__ == method_name
            assert decorated_method.__doc__ == method.__doc__

            monkeypatch.setattr(cls, method_name, decorated_method, raising=False)

        return add_decorated_method_impl

    @pytest.fixture(params=[
        # (<`method_1` owner>, <`method_2` owner>, <call target>)
        (PropOwnerSuper, PropOwnerSuper, PropOwner),
        (PropOwnerSuper, PropOwnerSuper, PropOwnerSub),
        (PropOwnerSuper, PropOwner, PropOwner),
        (PropOwnerSuper, PropOwner, PropOwnerSub),
        (PropOwnerSuper, PropOwnerSub, PropOwnerSub),
        (PropOwner, PropOwnerSuper, PropOwner),
        (PropOwner, PropOwnerSuper, PropOwnerSub),
        (PropOwner, PropOwner, PropOwner),
        (PropOwner, PropOwner, PropOwnerSub),
        (PropOwner, PropOwnerSub, PropOwnerSub),
        (PropOwnerSub, PropOwnerSuper, PropOwnerSub),
        (PropOwnerSub, PropOwner, PropOwnerSub),
        (PropOwnerSub, PropOwnerSub, PropOwnerSub),
    ])
    def call_target_cls(self, request, add_decorated_method):
        method_1_owner_cls, method_2_owner_cls, call_target_cls = request.param
        add_decorated_method(method_1_owner_cls, 'method_1')
        add_decorated_method(method_2_owner_cls, 'method_2')
        return call_target_cls


    def test__same_target_instance__same_context(
        self,
        call_target_cls,
    ):
        # => modifying same namespace

        target = call_target_cls()
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK

        target.init_namespace()
        assert target.method_1() == 1
        assert target.method_1() == 1  # (same namespace, same cache key)
        assert target.method_2() == 2  # (same namespace, separate cache key)
        assert target.method_2() == 2
        assert target.method_1() == 1
        assert target.method_2() == 2

        target.remove_namespace()
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK

        target.init_namespace()
        assert target.method_1() == 1
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert target.method_2() == 2
        assert target.method_1() == 1
        assert target.method_2() == 2


    def test__different_target_instances__same_context(
        self,
        call_target_cls,
    ):
        # => modifying separate namespaces independently

        target_a = call_target_cls()
        target_b = call_target_cls()
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_a.method_2() is sentinel.FALLBACK
        assert target_a.method_2() is sentinel.FALLBACK
        assert target_b.method_2() is sentinel.FALLBACK
        assert target_b.method_2() is sentinel.FALLBACK
        assert target_b.method_1() is sentinel.FALLBACK
        assert target_b.method_1() is sentinel.FALLBACK
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_b.method_2() is sentinel.FALLBACK

        target_a.init_namespace()
        assert target_a.method_1() == 1
        assert target_a.method_1() == 1  # (same namespace, same cache key)
        assert target_a.method_2() == 2  # (same namespace, separate cache key)
        assert target_a.method_2() == 2
        assert target_b.method_2() is sentinel.FALLBACK  # (separate namespace)
        assert target_b.method_2() is sentinel.FALLBACK
        assert target_b.method_1() is sentinel.FALLBACK
        assert target_b.method_1() is sentinel.FALLBACK
        assert target_a.method_1() == 1
        assert target_b.method_2() is sentinel.FALLBACK

        target_b.init_namespace()
        assert target_a.method_1() == 1
        assert target_a.method_1() == 1
        assert target_a.method_2() == 2
        assert target_a.method_2() == 2
        assert target_b.method_2() == 1
        assert target_b.method_2() == 1
        assert target_b.method_1() == 2
        assert target_b.method_1() == 2
        assert target_a.method_1() == 1
        assert target_b.method_2() == 1

        target_a.remove_namespace()
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_a.method_2() is sentinel.FALLBACK
        assert target_a.method_2() is sentinel.FALLBACK
        assert target_b.method_2() == 1
        assert target_b.method_2() == 1
        assert target_b.method_1() == 2
        assert target_b.method_1() == 2
        assert target_a.method_1() is sentinel.FALLBACK
        assert target_b.method_2() == 1


    def test__same_target_instance__different_contexts(
        self,
        call_target_cls,
    ):
        # => modifying separate namespaces independently

        target = call_target_cls()
        alt_context = contextvars.Context()

        target.init_namespace()
        alt_context.run(target.init_namespace)
        assert target.method_1() == 1
        assert target.method_1() == 1  # (same namespace, same cache key)
        assert alt_context.run(target.method_2) == 1  # (separate namespace)
        assert alt_context.run(target.method_1) == 2  # (separate cache key)
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_1) == 2
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert target.method_2() == 2

        target.remove_namespace()
        alt_context.run(target.remove_namespace)
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_1) is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_1) is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK

        target.init_namespace()
        assert target.method_1() == 1
        assert target.method_1() == 1
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_1) is sentinel.FALLBACK
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_2) is sentinel.FALLBACK
        assert alt_context.run(target.method_1) is sentinel.FALLBACK
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert target.method_2() == 2

        alt_context.run(target.init_namespace)
        assert target.method_1() == 1
        assert target.method_1() == 1
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_1) == 2
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_1) == 2
        assert target.method_1() == 1
        assert target.method_2() == 2
        assert target.method_2() == 2

        target.remove_namespace()
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_1() is sentinel.FALLBACK
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_1) == 2
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_2) == 1
        assert alt_context.run(target.method_1) == 2
        assert target.method_1() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK
        assert target.method_2() is sentinel.FALLBACK

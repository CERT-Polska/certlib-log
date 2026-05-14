# API Reference

!!! exclusion "Interface exclusion"

    In general, the following elements are _**not**_ part of the public
    API (so, in particular, they may change in *minor* or *patch* versions
    of the `certlib.log` library):

    * any elements *not* documented in this *API reference*;

    * specific *runtime types* of any objects bound to a documented
      element of the API (variable, attribute, parameter or call
      result) -- *provided that* they remain correct with respect to
      the element's type annotation, according to the [static typing
      rules](https://typing.python.org/en/latest/spec/index.html);

    * specific behaviors in cases where -- according to the
      documentation -- *undefined behavior* is expected;

    * any elements that appear in this document *only* in source code
      excerpts (available via `<> Source code...` drop-down widgets),
      e.g., specific exception messages.

!!! warning "Important"

    Whenever this document refers to *undefined behavior*, this should
    be understood to mean: *the API makes no guarantees about what will
    happen -- an exception or a malfunction is likely.*

***

::: certlib.log.StructuredLogsFormatter
    handler: python
    options:
      heading_level: 2
      filters:
        - "!^_"
      show_attribute_values: false

***

::: certlib.log.xm
    handler: python
    options:
      heading_level: 2
      separate_signature: false

::: certlib.log.ExtendedMessage
    handler: python
    options:
      heading_level: 2
      filters:
        - "!^_"
        - "^__str__$"
        - "^__repr__$"
        - "^_ensure_callable_args_and_data_items_resolved$"
      show_attribute_values: false

***

::: certlib.log.make_constant_value_provider
    handler: python
    options:
      heading_level: 2

***

::: certlib.log.register_log_record_attr_auto_maker
    handler: python
    options:
      heading_level: 2

***

::: certlib.log.unregister_log_record_attr_auto_maker
    handler: python
    options:
      heading_level: 2

***

::: certlib.log.COMMONLY_EXPECTED_NON_STANDARD_OUTPUT_KEYS
    handler: python
    options:
      heading_level: 2

***

::: certlib.log.STANDARD_RECORD_ATTR_TO_OUTPUT_KEY
    handler: python
    options:
      heading_level: 2

***

## Static Typing Helpers

!!! note

    In your day-to-day work with the `certlib.log` library, you do not
    need to delve into this stuff.

!!! exclusion "Interface exclusion"

    The flavor of any *type aliases* -- i.e., whether they are
    [`TypeAlias`][typing.TypeAlias]-annotated ones or [*type
    statement*](https://docs.python.org/3/reference/simple_stmts.html#type)-made
    ones -- is _**not**_ part of the public API.

::: certlib.log.ValueProvider
    handler: python
    options:
      heading: 'ValueProvider'
      heading_level: 3
      members: false

::: certlib.log.OutputSerializer
    handler: python
    options:
      heading: 'OutputSerializer'
      heading_level: 3
      members: false

::: certlib.log.OutputValue
    handler: python
    options:
      heading: 'OutputValue'
      heading_level: 3
      show_signature_annotations: false

::: certlib.log.DottedPath
    handler: python
    options:
      heading: 'DottedPath'
      heading_level: 3
      show_signature_annotations: false

::: certlib.log.KwargsMappingAsLiteralEvaluableString
    handler: python
    options:
      heading: 'KwargsMappingAsLiteralEvaluableString'
      heading_level: 3
      show_signature_annotations: false

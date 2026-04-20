# API Reference

!!! info

    Whenever this document refers to *undefined behavior*, this should
    be understood to mean: *the API makes no guarantees about what will
    happen -- an exception or a malfunction is likely.*


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

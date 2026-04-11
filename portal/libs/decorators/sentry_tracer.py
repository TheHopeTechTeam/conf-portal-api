"""
telemetry tracer
"""
import inspect
from functools import wraps
from typing import Callable, Optional

import sentry_sdk
from sentry_sdk.consts import SPANDATA
from sentry_sdk.tracing import Span, TransactionSource


def start_transaction(
    *,
    op: Optional[str] = None,
    name: Optional[str] = None,
    source: Optional[TransactionSource] = None
) -> Callable:
    """
    A decorator to instrument a class or function with an open telemetry tracing transaction.
    Usage Example::
        class Foo:

            @start_transaction()
            def sync_func(self, *args, **kwargs):
                ...

            @start_transaction()
            async def async_func(self, *args, **kwargs):
                ...

    :param op:
    :param name:
    :param source:
    :return:
    """

    def decorator(func):
        """

        :param func:
        :return:
        """
        transaction_name = name or func.__name__.replace("_", " ").title()
        operation = op or func.__qualname__
        description = func.__name__.replace("_", " ").title()

        # Asynchronous case
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                """

                :param args:
                :param kwargs:
                :return:
                """
                with sentry_sdk.start_transaction(
                    name=transaction_name,
                    op=operation,
                    source=source,
                    description=description
                ) as transaction:
                    try:
                        result = await func(*args, **kwargs)
                        transaction.set_status("ok")
                    except Exception as exc:
                        transaction.set_data("error", str(exc))
                        transaction.set_status("error")
                        raise exc
                return result
        # Synchronous case
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                """

                :param args:
                :param kwargs:
                :return:
                """
                with sentry_sdk.start_transaction(
                    name=transaction_name,
                    op=operation,
                    source=source,
                    description=description
                ) as transaction:
                    try:
                        result = func(*args, **kwargs)
                        transaction.set_status("ok")
                    except Exception as exc:
                        transaction.set_data("Exception", str(exc))
                        transaction.set_status("error")
                        raise exc
                return result

        return wrapper

    return decorator


def distributed_trace(
    *,
    op: str = None,
    description: str = None,
    inject_span: bool = False
) -> Callable:
    """
    A decorator to instrument a class or function with an open telemetry tracing span.
    Usage Example::
        class Foo:

            @distributed_trace()
            def sync_func(self, *args, **kwargs):
                ...

            @distributed_trace()
            async def async_func(self, *args, **kwargs):
                ...

            @distributed_trace(inject_span=True)
            def func_with_inject_span(self, xxx, *, _span: Span = None):
                # _span.set_data()
                ...

    :param op:
    :param description:
    :param inject_span:
    :return:
    """

    def decorator(func):
        """

        :param func:
        :return:
        """
        operation = op or func.__qualname__
        name = description or func.__name__.replace("_", " ").title()

        def _set_semantic_attributes(span: Span, raw_func: Callable):
            """

            :param span:
            :param raw_func:
            :return:
            """
            span.set_data(SPANDATA.CODE_FILEPATH, str(raw_func.__code__.co_filename))  # noqa
            span.set_data(SPANDATA.CODE_LINENO, str(raw_func.__code__.co_firstlineno))  # noqa
            span.set_data(SPANDATA.CODE_FUNCTION, str(raw_func.__qualname__))  # noqa
            span.set_data(SPANDATA.CODE_NAMESPACE, str(raw_func.__module__))  # noqa

        def _check_func_args_has_span(raw_func: Callable):
            """

            :param raw_func:
            :return:
            """
            return "_span" in inspect.signature(raw_func).parameters

        # Asynchronous case
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                """

                :param args:
                :param kwargs:
                :return:
                """
                with sentry_sdk.start_span(
                    op=operation,
                    description=name
                ) as span:  # type: Span
                    _set_semantic_attributes(span=span, raw_func=func)
                    try:
                        if inject_span and _check_func_args_has_span(func):
                            result = await func(*args, **kwargs, _span=span)
                        else:
                            result = await func(*args, **kwargs)
                    except Exception as exc:
                        span.set_data("Exception", str(exc))
                        raise exc
                return result
        # Synchronous case
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                """

                :param args:
                :param kwargs:
                :return:
                """
                with sentry_sdk.start_span(
                    op=operation,
                    description=name
                ) as span:  # type: Span
                    _set_semantic_attributes(span=span, raw_func=func)
                    try:
                        if inject_span and _check_func_args_has_span(func):
                            result = func(*args, **kwargs, _span=span)
                        else:
                            result = func(*args, **kwargs)
                    except Exception as exc:
                        span.set_data("Exception", str(exc))
                        raise exc
                return result

        return wrapper

    return decorator

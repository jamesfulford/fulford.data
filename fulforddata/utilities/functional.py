from inspect import getargspec
import functools

from fulforddata import constants as c


def prepare_argument(fn, contexts):
    """
    Implements dependency injection.

    (Passes only the arguments fn expects from contexts dicitonary)
    """
    args, varargs, varkwargs, defaults = getargspec(fn)
    arguments = map(lambda a: contexts.get(a, None), args)
    return arguments


class ReadableFunction(object):
    """
    Decorator for deferred-evaluation-generating functions
        so you can print how a given function was obtained.
    
    Behaves well if deferred evaluator has been decorated with
        functools.wraps.

    >>> @ReadableFunction
    ... def sample(a, b, c=42):
    ...     def inner_func():
    ...         return a + b + c
    ...     return inner_func
    >>> str(sample(1, 42, c=73))
    'sample(1, 42, c=73)'

    >>> sample(1, 42, c=73)()  # calls inner_func
    116
    """
    def __init__(self, fn, name=None):
        self.fn = fn
        # functools.update_wrapper(self, fn)
        self.name = name if isinstance(name, c.STRINGS) else fn.__name__
        self.__name__ = self.name
        self.__doc__ = fn.__doc__  # if hasattr(fn, "__doc__") else self.__doc__

    def __str__(self):
        return self.name

    __repr__ = __str__

    def _resolve_to_py_function(self):
        """
        So the inspect module can work, call this to get the
            actually defined python function
        """
        if isinstance(self.fn, ReadableFunction):
            return self.fn._resolve_to_py_function()
        else:
            return self.fn

    def __call__(self, *args, **kwargs):
        result = self.fn(*args, **kwargs)

        # if a function is returned,
        # make it a validator
        # with the name describing how it was made.
        if hasattr(result, "__call__"):
            name = self.name + "("
            if args or kwargs:
                arguments = []
                if args:
                    typetype = type(type(1))
                    args = map(lambda x: x.__name__ if isinstance(x, typetype)
                               else repr(x), args)
                    arguments.extend(args)
                if kwargs:
                    arguments.extend(map(lambda kv: str(kv[0]) + "=" +
                                         repr(kv[1]), kwargs.items()))
                name += ", ".join(arguments)
            name += ")"
            # print name
            return ReadableFunction(result, name=name)
        return result


def compose(*fns):
    """
    Returns a function that evaluates each function in order, starting with
        function 0's output being fed into function 1's input.

    The first function can accept anything, but output beyond that is passed
        as a single value.
    """
    @functools.wraps(compose)
    def comp(*args, **kwargs):
        v = fns[0](*args, **kwargs)
        for fn in fns[1:]:
            v = fn(v)
        return v
    return comp


def pass_through(value, mapping, warn=False, **kwargs):
    """Tries to map value through mapping. If fails, returns input.
    Mapping can be a function or a dictionary.

    If function, key words are passed down to the function.
        Exceptions are caught and printed, returns value

    If dictionary, tries to get new value by inputting the value.
        If value is not hashable (list, set, etc.), prints and returns value

    >>> pass_through(2, lambda x: x ** 2)
    4

    >>> pass_through("color", {"color": "BLUE"})
    "BLUE"

    >>> pass_through("color", {"id": 42})
    "color"

    >>> pass_through(["unhashable"], {"id": 42})
    ["unhashable"]  # also prints error to stdout

    >>> pass_through(0, lambda x: 1/x)
    0  # prints error to stdout

    """

    # Lists cannot pass_through. Instead, we pass through all items.
    # If a staggered, unflattened list of lists,
    #   will pass all entries and lower entries through
    if isinstance(value, c.ITERABLES):
        return map(lambda v: pass_through(v, mapping, warn=False, **kwargs),
                   value)

    if isinstance(mapping, c.DICTIONARIES):
        try:
            return mapping.get(value, value)
        except TypeError:
            msg = "pass_through: TypeError (unhashable type?)" \
                ": cannot get {} from {}".format(value, mapping)
            print msg
            # will return value later
        except KeyError:
            # this is expected behavior
            pass  # will return value later
    else:
        try:
            return mapping(value, **kwargs)
        except Exception as e:  # calling the function failed
            msg = "pass_through: {}({}) failed\n".format(
                mapping, value) + str(e)
            print msg

    # Mapping failed - return input
    return value


if __name__ == "__main__":
    print pass_through(1, {1: 9})

    @ReadableFunction
    def sample(a, b, c=42):
        """
        sample docstring
        """
        # @functools.wraps(sample)
        def inner_func():
            """
            inner_func docstring
            """
            return a + b + c
        return inner_func

    print str(sample(1, 42, c=73))
    print sample(1, 42, c=73)()
    print sample.__doc__
    print sample(1, 42, c=73).__doc__
    # 'sample(1, 42, c=73)'

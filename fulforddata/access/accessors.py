import functools

from fulforddata import constants as c
from fulforddata.utilities.tools import flatten_list

from fulforddata.utilities.functional import pass_through
from fulforddata.utilities.functional import ReadableFunction as accessor


def resolve_keypath(keypath, split="/"):
    """
    Converts keypath into a list of keys to pass through.
    If keypath is a string, makes list by splitting on split

    >>> resolve_keypath(["a", "b"])
    ["a", "b"]

    >>> resolve_keypath("a/b")
    ["a", "b"]

    >>> resolve_keypath("a_b", split="_")
    ["a", "b"]

    """
    if isinstance(keypath, c.STRINGS):
        if split:
            keypath = keypath.split(split)
        else:
            keypath = [keypath]
    return keypath


@accessor
def access(key, default=None, flatten=None,
           mapping=None, get_attr=None,
           warn=False, split="/", **kwargs):
    """Returns a function which obtains the value of *key* in
    later-passed-in data. If key is a string and split is specified, will split
    key on split value and use that list as the key path. Default: /

    If default is not None, returned function will return *default*
    if key not found in data.

    If flatten, passes flatten to flatten_list for each entry.
    The results structure is always list_flattened.

    If mapping is not falsey, will return the result of the mapping
    or the original value if fails. Accepts dictionary or function.
    (Warn is passed to pass_through)

    If get_attr is set, will access on this attribute on each entry.
    (ex: custom dict wrapping objects, stored dict in .data)

    If faulty key, will raise KeyError.
    """

    key = resolve_keypath(key, split=split)

    # Warning: recursion.
    def get_deeper(k, data, leaf=False):
        """
        Returns data at key k.

        If data is a list, gets k from each item in the list.
        If default is set, returns default value on fail
        """
        if isinstance(data, c.ITERABLES):
            get_deeper.non_data_lists += 1  # set before calling
            return map(lambda dp: get_deeper(k, dp, leaf=leaf), data)
        elif isinstance(data, c.DICTIONARIES):
            try:
                return data[k]
            except Exception:
                if default is not None and leaf:
                    return default
                else:
                    raise  # TypeError or KeyError
    
    # @functools.wraps
    def get_deep_key_from_dictionary(data, *args):
        """
        Gets deep key from data. Ignores resource.
        """
        # handling objects
        if get_attr:
            data = getattr(data, get_attr)

        # this handles depth
        get_deeper.non_data_lists = 0  # incremented in get_deeper
        for i in range(len(key)):
            k = key[i]
            data = get_deeper(k, data, leaf=(i == len(key) - 1))

        # now getting ready to return data
        if isinstance(data, c.ITERABLES):
            data = flatten_list(data, depth=get_deeper.non_data_lists - 2)
            if flatten:
                data = map(lambda d: flatten_list(d, depth=flatten), data)

        if mapping:
            data = pass_through(data, mapping, warn=warn, **kwargs)

        return data

    return get_deep_key_from_dictionary


@accessor
def try_deeper_key(key, deep_key, default=None, **kwargs):
    """
    Returns getter which tries to access from parent dictionary.
    If no success, tries to grab from deep_key dictionary instead.
    If that fails, uses access's default option.
    """
    def try_access(data, key=key, deep_key=deep_key, *args):
        try:
            return access(key, **kwargs)(data, *args)
        except KeyError:
            # Build new path starting from deep_key
            key = resolve_keypath(key)
            deep_key = resolve_keypath(deep_key)
            key = deep_key + key
            # Try accessing new key path
            return access(key, default=default, **kwargs)(data, *args)

    return try_access


@accessor
def always(value):
    """Always returns the same *value* irregardless of inputs"""
    def always_return(data, *args):
        return value
    return always_return


blank = always("")
blank.__doc__ = "Always returns the empty string (\"\")."


if __name__ == "__main__":
    print access("x")({"x": 2})
    print access.__name__
    print access.__doc__
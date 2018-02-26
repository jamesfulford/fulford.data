
from fulforddata import constants as c
from fulforddata.access.accessors import access


def retrieve(data, form, *args):
    """
    Using accessors specified in form,
    retrieves all values from dictionary 'data'.
    form = {
        "value": accessor_function,
    }

    If accessor is a dict, recurses.
    If accessor is a str/unicode, splits on "/"

    Returns dictionary if succeeded. If accessor raises Exception,
    will return None (should be filtered out)
    and prints and logs a message about that entry.
    """
    entry = {}
    for tupl in form.items():
        key, accessor = tuple(tupl)  # just in case it's a list

        #
        # if accessor is a dict, recurse
        #
        if isinstance(accessor, c.DICTIONARIES):
            entry[key] = retrieve(data, accessor, *args)
            if entry[key] is None:  # retrieve failed
                return None  # filter it out
        #
        # else, access the value
        #
        else:
            #
            # if value is a string, use standard accessor with / as lister
            #
            if isinstance(accessor, c.STRINGS):
                accessor = access(accessor.split("/"))

            #
            # try to access the value from the data
            #
            try:
                entry[key] = accessor(data, *args)
            except Exception as e:
                #
                # accessing failed. Log message
                # and return None so it gets filtered out.
                #
                msg = "({}, {}): {}\nSkipping {}.".format(
                    *(key, accessor.__name__, str(e), data)
                )
                # logger.debug(msg)
                print msg
                return None
    return entry

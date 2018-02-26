# tools.py

from fulforddata import constants as c


def partition(fn, ls):
    """
    Calls fn on each item in ls
        returns dictionary keyed on outputs of fn
        values being lists of items with that output

    >>> partition(lambda x: x ** 2, [1, 2, 3, -2])
    {1: [1], 4: [2, -2], 9: [3]}

    >>> partition(bool, [1, 0, [], "Hello"])
    {True: [1, "Hello"], False: [0, []]}
    """
    parting = {}
    for item in ls:
        r = fn(item)
        try:
            parting[r].append(item)
        except KeyError:
            parting[r] = [item]
    return parting


def flatten_list(list_of_lists, depth=True):
    """Given a list of lists, unpacks all the items
    and puts it in one list.

    depth specifies how many layers deep we should flatten.
        by default flattens all layers

    >>> flatten_list([[1, [2], [3, 4]], [[5, [6, 7], [8]]]])
    [1, 2, 3, 4, 5, 6, 7, 8]

    >>> flatten_list([[1, [2], [3, 4]], [[5, [6, 7], [8]]]], depth=2)
    [1, 2, 3, 4, 5, [6, 7], [8]]
    """
    result = []
    for item in list_of_lists:
        if isinstance(item, c.ITERABLES):
            if type(depth) is int and depth - 1 >= 0:
                # flatten this level
                result.extend(flatten_list(item, depth=depth - 1))
            elif depth:
                # flatten all the way down
                result.extend(flatten_list(item))
            else:
                # preserve
                result.append(item)
        else:
            result.append(item)
    return result

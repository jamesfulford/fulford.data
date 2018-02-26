# validators.py
# by James Fulford

#
# Probably the most moral Python I've ever written
# -James Fulford
#


from fulforddata import constants as c
from fulforddata.access.accessors import access
from fulforddata.utilities.functional import ReadableFunction as validator

#
# CONTEXT DEFINITIONS
#
# 'record' context: validating against other fields in entry
#       (useful for one field less than another)
#
# 'entries' context: validating against other entries in list
#       (useful for graph references and uniqueness)
#
# 'collection' context: validating against entries in named lists (dictionary)
#       (useful for foreign references)
#


@validator
def should(*args):
    """
    Aggregates multiple tests in an 'AND' fashion (all must pass)

    If a test is a list, at least 1 must pass (OR)
        If a subtest is a list, all must pass (AND)
            If a subsubtest is a list, at least 1 must pass (OR)
    (Continues to alternate.)

    Stops list execution if
        'AND' lists: one fails
        'OR' lists: one succeeds

    >>> should(
        # ALL
        be_a(dict),  # YEP
        [   # EITHER
            [   # ALL
                have("death"),  # YEP
                lambda d: d["death"] is True  # NOPE - "AND" FAILS
            ],
            have("liberty", be_an(int)),  # YEP - OR SUCCEEDS
        ]  # YEP - AND SUCCEEDS
    )({"liberty": 22, "death": False})
    True
    """
    return _parse_tests(args, top_is_and=True)


@validator
def at_least(*args):
    """
    Aggregates multiple tests in an 'OR' fashion (1 must pass)

    If a test is a list, all must pass (AND)
        If a subtest is a list, at least 1 must pass (OR)
            If a subsubtest is a list, all must pass (AND)
    (Continues to alternate.)

    Stops list execution if
        'AND' lists: one fails
        'OR' lists: one succeeds

    >>> case(
        # EITHER
        be_a(dict),  # YEP - STOPS EXECUTION
        [   # ALL
            [   # EITHER
                have("death"),
                lambda d: d["death"] is True
            ],
            have("liberty", be_an(int)),
        ]
    )({"liberty": 22, "death": False})
    True
    """
    return _parse_tests(args, top_is_and=False)


@validator
def case(*args):
    pass


def _parse_tests(args, top_is_and=True):

    def check_that(data, **context):

        def check_and(arg, depth=0):
            if isinstance(arg, c.ITERABLES):
                # print ("    " * depth) + "AND({})".format(arg)
                for a in arg:
                    #
                    # If one test fails,
                    # prematurely return False
                    #
                    if not check_or(a, depth=depth + 1):
                        # lower level alternation
                        return False
                return True
            else:
                return arg(data, **context)

        def check_or(arg, depth=0):
            if isinstance(arg, c.ITERABLES):
                # print ("    " * depth) + "OR({})".format(arg)
                for a in arg:
                    #
                    # If one test succeeds,
                    # prematurely return True
                    #
                    if check_and(a, depth=depth + 1):
                        # lower level alternation
                        return True
                return False
            else:
                return arg(data)

        if top_is_and:
            return check_and(args, depth=0)
        else:
            return check_or(args, depth=0)

    return check_that


#
# No context validators
#


@validator
def be(*goods):
    def is_good(data):
        return data in goods
    return is_good


@validator
def be_in(good_list):
    return be(*good_list)


@validator
def be_a(*good_types):
    def good_type_or_not(data):
        return isinstance(data, tuple(good_types))
    return good_type_or_not


be_an = be_a  # makes my english feel better


@validator
def be_truthful(data):
    return bool(data)


@validator
def be_good(good_test):
    def is_test_good(data):
        return good_test(data)
    return is_test_good


@validator
def have(key, *tests):
    """
    Returns if key successfully accessed from data.
    Will call should with args, passing in accessed value.

    >>> have("liberty")({"liberty": 32})
    True

    >>> have("liberty", be_an(int))({"liberty": 32})
    True
    """
    tests = should(*tests)

    def try_access(data, **context):
        try:
            result = access(key)(data)
        except Exception:
            return False
        else:  # make sure validation errors not caught
            return tests(result, **context)

    return try_access


#
# 'entries' Contextual Validators
#

@validator
def _reference(key, min_finds, max_finds=None, flatten=True):
    """
    Returns refer, which accesses key from each item
        in second context's list

    If data is found less than min_finds times
        or more than max_finds times (if specified)
        returns False.
    Otherwise, returns True.

    If accessed value is a list, looks for datavalue in list
        (List is flattened by default)
    """
    def refer(data, entries):
        finds = 0
        for item in entries:
            acc = access(key, flatten=flatten)(item)
            if isinstance(acc, c.ITERABLES):
                result = data in acc
            else:
                result = data == acc
            if result:
                finds += 1
                if max_finds and finds > max_finds:
                    return False
        return finds >= min_finds
    return refer


@validator
def be_unique(key):
    """
    Returns True if value shows up only once in the list
        after accessing key from each item in first context list.

    Returns False for ALL entries with conflicts.
    """
    return _reference(key, 1, 1)


@validator
def point_to(key):
    """
    Returns True if value shows up at least once in the list
        after accessing key from each item in first context list.

    Else, False.
    """
    return _reference(key, 1)


#
# Third Context Validators
#

@validator
def foreign(nexi_name, key, *tests):
    """
    Returns function which checks uniqueness on third context
    """
    # test = should(*tests) if tests else be_unique
    # ^ may have to prepare_argument
    def foreign_reference(data, me, ls, nexi):
        return be_unique(key)(data, nexi[nexi_name])
    return foreign_reference


if __name__ == "__main__":
    print should(
        # ALL
        be_a(dict),
        [   # EITHER
            [   # ALL
                have("death"),
                lambda d: d["death"] is True
            ],
            have("liberty", be_an(int)),
        ]
    )({"liberty": 22, "death": False})

    @validator
    def beans(beans, **kwargs):
        def be_a_bean(data, *context):
            return data in beans
        return be_a_bean

    print should(be_a(str),
                 should(be_in(["Bean"]))
                 )

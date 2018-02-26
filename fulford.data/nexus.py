import logging
from accessors import *
from validators import *
from tools import flatten_list, check, partition

from tools import ITERABLES
from tools import DICTIONARIES
from tools import STRINGS

logger = logging.getLogger(__name__)


def _retrieve(data, form, *args):
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
        if isinstance(accessor, DICTIONARIES):
            entry[key] = _retrieve(data, accessor, *args)
            if entry[key] is None:  # retrieve failed
                return None  # filter it out
        #
        # else, access the value
        #
        else:
            #
            # if value is a string, use standard accessor with / as lister
            #
            if isinstance(accessor, STRINGS):
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
                logger.debug(msg)
                print msg
                return None
    return entry


class Nexus(object):
    def __init__(self, template):
        self.template = template  # what a valid entry looks like
        self.entries = []  # valid entries
        self.rejects = []  # all entries that fail validation
        self.packed = []  # all entries that failed unpacking

    def add(self, entries, unpackers, *args):
        """
        Adds valid entries in given format to self.entries
        Invalid entries added to self.rejects
        Un-unpackable entries added to self.packed

        Passes extra args to each getter.
        """

        def transform(entry):
            return _retrieve(entry, unpackers, *args)

        results = map(transform, entries)  # unpack

        #
        # Validate
        #
        parting = partition(lambda e: check(e, self.template) if e else e,
                            results)

        # Store results
        self.entries.extend(  # successful mappings and valid
            parting.get(True, [])
        )
        self.rejects.extend(  # successful mappings and invalid
            parting.get(False, [])
        )
        self.packed.extend(  # unsuccessful mappings
            parting.get(None, [])
        )

    def get_rows(self, columns, fill="", *args):
        """
        Returns data as rows according to given columns

        Examples given use columns:
        [
            (0, access("x", default=0, mapping=IDENTITY)),
            (2, access("y", mapping=abs))
        ]

        (Columns can also be a dictionary)
        """

        def transform(entry):
            """
            >>> transform({"x": 2.33, "y": -3.14})
            {0: 2.33, 2: 3.14}
            Returns None if an accessor raised Exception.
            """
            return _retrieve(entry, columns, *args)

        def make_row(ent, fill=fill):
            """
            Keys will be index values,
            Values will be values.
            If key not in ent, will use fill as value.

            >>> make_row({0: 2.33, 2: 3.14})
            [2.33, "", 3.14]
            """
            return map(lambda i: ent.get(i, fill),  # get ith value from ent
                       range(max(ent.keys() + 1)))  # 0 to largest col

        # Filter out formations that failed
        formed_dicts = filter(lambda a: a, map(transform, self.entries))

        # Return as rows
        return map(make_row, formed_dicts)

    def get_dictionaries(self, form, *args):
        """
        Given dictionary (form), runs accessor values on each
        of the entries stored.

        Example form is {
            "time": access("x"),
            "measures": {
                "pirates": access("y1", default=0),
                "CO 2": access("y2", mapping=lambda n: round(n, 3))
            }
        }
        """
        def transform(entry):
            return _retrieve(entry, form, *args)

        return filter(lambda r: r, map(transform, self.entries))

    def get_writeable_rows(self, columns, fill="", delimiter=",",
                           subdelimiter="|", headers=True, *args):
        """
        Returns list of delimited strings from self.get_rows()

        Lists of lists will be flattened.
        (unable to represent lists of lists in strings)
        """
        def stringify_cell(self, value):
            if isinstance(value, ITERABLES):
                value = flatten_list(value)
                value = map(self._stringify_cell, value)
                value.sort(key=lambda s: int(s) if s.isdigit() else s)
                return subdelimiter.join(value)
            else:
                return str(value).strip()

        output = self.get_rows(columns, fill=fill, *args)

        if headers:
            output = [map(lambda s: str(s[0]).strip(), self.columns)] + output

        return map(lambda r: delimiter.join(
            map(lambda v: stringify_cell(v).replace(delimiter, "|"), r)
        ), output)

    def validate(self, template, **contexts):
        """
        Using each template, which has a similar structure to each entry,
        will apply each leaf function on each entry in self.entries.
        """

        parting = partition(lambda e: check(e, template, **contexts),
                            self.entries)

        #
        # Replace entries with valid entries
        # Add invalid entries to rejects
        #
        self.entries = parting.get(True, [])
        self.rejects.extend(parting.get(False, []))


if __name__ == "__main__":
    entries = [
        {
            "x": 1,
            "y": 2,
            "james": {
                "id": 10
            },
        },
        {
            "y": 4,
            "james": {
                "id": 20
            },
            "extra_data": {
                "x": 2
            }
        },
        {
            "x": 3,
            "james": {
                "id": 30
            },
            "extra_data": {
                "x": 2
            }
        },
    ]

    unpackers = {
        "id": access(["james", "id"]),
        "x_coord": try_deeper_key("x", "extra_data", default=0),
        "y_coord": access(["y"], 0)
    }

    declaration = {
        "id": be_an(int),
        "x_coord": be_an(int),
        "y_coord": be_an(int)
    }

    print unpackers
    n = Nexus(declaration)

    n.add(entries, unpackers)
    n.validate({"id": be_unique("id")}, entries=n.entries)
    print "Entries", len(n.entries)
    print "Rejects", len(n.rejects)
    print "Packed ", len(n.packed)

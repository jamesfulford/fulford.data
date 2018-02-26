# wrapper.py
# by James Fulford

from accessors import access
from tools import ITERABLES, DICTIONARIES


class Wrapper(object):
    def __init__(self, data, splitter="__"):
        self.__data = data
        self.__splitter = splitter

    def __getattr__(self, name):
        """
        .get_{} will return a function that when called will access from self
            and pass kwargs to access

        .{} will work as normal.

        """

        if name in self.__dict__:
            return self.__dict__[name]

        if name.startswith("get_"):

            def get_ter(**kwargs):
                keypath = name[4:].split(self.__splitter)
                try:
                    return access(keypath, **kwargs)(self.__data)
                except KeyError:
                    raise AttributeError("Cannot access {}".format(keypath))

            return get_ter

        # if name.startswith("valid_"):
        #     return valid(name[6:])

        try:
            return self.__data[name]
        except KeyError:
            raise AttributeError("Cannot access {}".format(name))

    def __getitem__(self, name):
        result = access(name)(self.__data)
        if (isinstance(result, ITERABLES) or
                isinstance(result, DICTIONARIES)):
            return Wrapper(result)
        return result

    def __str__(self):
        return str(self.__data)

    def __repr__(self):
        return "{}({!r}, splitter={!r})".format(
            self.__class__.__name__, self.__data, self.__splitter
        )


if __name__ == "__main__":
    james = Wrapper({"help": {"text": "Eat something tasty"}})
    print james.get_help__text()

# wrapper.py
# by James Fulford

from fulforddata import constants as c

from fulforddata.access.accessors import access


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
        result = access(name, split=self.__splitter)(self.__data)
        if (isinstance(result, c.ITERABLES) or
                isinstance(result, c.DICTIONARIES)):
            return Wrapper(result, splitter=self.__splitter)
        return result

    def __str__(self):
        return str(self.__data)

    def __repr__(self):
        return "{}({!r}, splitter={!r})".format(
            self.__class__.__name__, self.__data, self.__splitter
        )


if __name__ == "__main__":
    james = Wrapper(
        {"help": {"text": "Eat something tasty"}},
        splitter="_0_"
    )
    print james.get_help_0_text()
    print james[["help", "text"]]
    print james["help_0_text"]
    print james["help"].get_text()

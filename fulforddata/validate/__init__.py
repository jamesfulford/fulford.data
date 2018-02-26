
from fulforddata import constants as c
from fulforddata.utilities.functional import ReadableFunction, prepare_argument


def check(data, template, **context):
    """
    Checks data complies with tests specified in template.
    If test fails, prints value returned and returns False
        continues to evaluate tests
    Is part of validation.
    """

    if isinstance(template, c.DICTIONARIES):
        # delegate to all key-value pairs
        results = []
        for key, value in template.items():
            result = check(data[key], value, **context)
            results.append(result)
            if not result:
                break
        return reduce(lambda p, q: bool(p) and bool(q), results)
    elif isinstance(template, c.ITERABLES):
        # delegate to all items
        results = []
        for item in data:  # data should be a list
            result = check(item, template[0], **context)
            results.append(result)
            if not result:
                break
        return reduce(lambda p, q: bool(p) and bool(q), results)
    else:
        # Leaf of template
        contexts = {"data": data}
        contexts.update(context)

        test = template
        if isinstance(test, ReadableFunction):
            test = test._resolve_to_py_function()
        try:
            # Call the validator on this piece of data
            arguments = prepare_argument(test, contexts)
            output = test(*arguments)
        except Exception as e:
            output = str(e)
            raise

        if output is not True:
            print "{}({}) failed (output: {})" \
                .format(template.__name__, data, output)
            return False
        return True

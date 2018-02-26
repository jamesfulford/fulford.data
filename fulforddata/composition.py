

def compose(*fns):
    """
    Returns a function that evaluates it all
    """
    def comp(*args, **kwargs):
        v = fns[0](*args, **kwargs)
        for fn in fns[1:]:
            v = fn(v)
        return v
    return comp


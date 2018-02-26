
import threading
from copy import deepcopy
from time import sleep


def mutate(key, mapper):
    def mutator(d):
        sleep(d[key])
        d[key] = mapper(d[key])
    return mutator


def fork(fns):

    def forker(item):
        tapestry = [threading.Thread(**{
            "target": f,
            "args": (item,)
        }) for f in fns]  # prepare worker threads
        [t.start() for t in tapestry]  # start worker threads
        [t.join() for t in tapestry]  # wait for all threads to finish
        return item

    return forker


if __name__ == "__main__":
    print fork([
        mutate("a", lambda x: x * 2),
        mutate("b", lambda x: x * 3)
    ])({"a": 2, "b": 4})

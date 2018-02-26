# stream.py

import time
import threading
from copy import deepcopy

import workers


class Trickle(object):

    def __init__(self, work):
        self.work = work
        self.i = 0
        self.nomore = False

    def __iter__(self):
        return self

    def __getitem__(self, i):
        return self.work[i]

    def __repr__(self):
        return "Tricker({})".format(self.work)

    __str__ = __repr__

    def append(self, item):
        self.work.append(item)

    def extend(self, items):
        self.work.extend(items)

    def next(self):
        try:
            ret = self.work[deepcopy(self.i)]
            self.i += 1
            return ret if ret is not None else self.next()
        except KeyError:
            # print "{} out of work. Nomore: {}".format(self.i, self.nomore)
            if self.nomore:
                raise StopIteration()
            time.sleep(0.05)
            return self.next()  # TODO: make iterative; limit depth
        except IndexError:
            # print "{} out of work. Nomore: {}".format(self.i, self.nomore)
            if self.nomore:
                raise StopIteration()
            time.sleep(0.05)
            return self.next()  # TODO: make iterative; limit depth


class Stream(object):
    """
    Represents a task that can be streamlined. Useful for doing work while
        waiting for IO.

    NOTE: May not preserve order, depending on which workers are used.
        Use .preserves_order attr to find if your Stream should preserve order.

    >>> mystream = Stream().then(
        lambda x: x ** 2,
        name="Square"
    ).then(  # [0, 1, 4, 9]
        lambda x: [i for i in range(x)],
        unpack=True,
        name=
    )

    >>> mystream(range(4))
    [0, 1, 0, 1, 2, 3, 0, 1, 2, 3, 4, 5, 6, 7, 8]

    >>> mystream.errors
    {}

    >>> mystream.preserves_order
    True

    >>> mystream.then(
        lambda x: 1.0 / x,
        name="Reciprocal"
    )
    mystream

    >>> mystream(range(4))
    [1, 1, 2, 3, 1, 2, 3, 4, 5, 6, 7, 8]

    >>> mystream.errors
    {
        "Reciprocal <Worker>": [
            {"item": 0, "exception": DivideByZeroException},  # 0th index
            {"item": 0, "exception": DivideByZeroException},  # 2nd index
            {"item": 0, "exception": DivideByZeroException},  # 6th index
        ]
    }
    """
    def __init__(self, default_worker=workers.Worker, **worker_args):
        self._workers = []
        self.errors = {}
        self.default_worker = default_worker
        self.defaults = worker_args

    @property
    def preserves_order(self):
        return all(w.PRESERVES_ORDER for w in self._workers)

    def then(self, worker, **worker_overrides):
        """
        Appends this worker (or these workers) at the end of the stream.

        If worker variable is not already a worker, wraps with this stream's
            default worker (as specified during __init__)

        Returns this stream.
        """
        if hasattr(worker, "__iter__"):
            map(self.then, worker)
        else:
            if not isinstance(worker, workers.Worker):
                worker_args = deepcopy(self.defaults)
                worker_args.update(worker_overrides)
                worker = self.default_worker(worker, **worker_args)
            worker.error_key = len(self._workers)
            self._workers.append(worker)
        return self

    def __call__(self, work):
        work = deepcopy(work)  # in case initial input is important

        work_queues = [work] + [[] for w in self._workers]
        work_queues = map(Trickle, work_queues)
        work_queues[0].nomore = True  # no more input in Tricker 0

        # print "Before: {}".format(work_queues)

        tapestry = [threading.Thread(**{
            "target": self._workers[i],
            "args": (work_queues[i], work_queues[i + 1], self.errors)
        }) for i in range(len(self._workers))]  # prepare worker threads
        [t.start() for t in tapestry]  # start worker threads

        return work_queues[-1]
        # [t.join() for t in tapestry]  # wait for all threads to finish

        # print "After: {}".format(work_queues)

        # return work_queues[-1].work  # todo: yield as results trickle in


if __name__ == "__main__":
    def wait(d):
        val = d["value"]
        if val > 5:
            raise Exception("TOO LONG")
        time.sleep(val)
        return d

    def recip(d):
        d["value"] = 1.0 / d["value"]
        return d

    def tee(d):
        print d
        return d

    #
    # Example
    #

    mystream = Stream(quiet=False).then([
        lambda x: {"value": x},
        workers.IOWorker(wait),
        tee,
    ])

    results = mystream([2, 3, 0, 1, 7])
    results.extend(mystream([4, 4, 9]))
    for i in results:
        print "Done:", i

    print
    print "Errors"
    for e in sorted(mystream.errors.items()):
        print e

    print "This stream does {}preserve order.".format(
        "" if mystream.preserves_order else "NOT "
    )

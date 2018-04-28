# stream.py

import time
import threading
import logging
from copy import deepcopy

import workers


default_logger = logging.getLogger(__name__)
default_logger.addHandler(logging.NullHandler())

class Trickle(object):
    """
    A iterable object which acts as a buffer between processing stations
        in a Stream. Can only be iterated over once.

    Difference between Trickle and a Queue is that Trickle.nomore is a flag to
        set which indicates that nothing else is coming, allowing the iterating
        code to distinguish between a build-up of work earlier in the process
        and between having no work at all left.
    """

    def __init__(self, work):
        self.work = work
        self.i = 0  # note: can only iterate over once
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

    def get_next_if_any(self):
        """
        Returns the next item in the queue, if there is one queued.
            If nothing is waiting in queue, return None
        """
        try:
            ret = self.work[deepcopy(self.i)]
            self.i += 1
            # print "Trickling item", self.i
            return ret
        except Exception:
            return None

    def next(self):
        """
        Called when iterating over this object.

        Waits for an item to be added to work list.

        If told no new items will be added and the work list has been
            exhausted, then will stop waiting for new items and will raise
            a StopIteration.
        """
        while True:  # waiting
            item = self.get_next_if_any()
            if item is not None:  # feature: value None is filtered out
                return item

            if self.nomore:  # if nothing else is coming
                break  # stop waiting

            time.sleep(0.1)  # wait before checking again

        raise StopIteration()  # tell next worker nothing else is coming


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
        "0: Reciprocal <Worker>": [
            {"item": 0, "exception": DivideByZeroException},  # 0th index
            {"item": 0, "exception": DivideByZeroException},  # 2nd index
            {"item": 0, "exception": DivideByZeroException},  # 6th index
        ]
    }
    """
    def __init__(self, default_worker=workers.Worker, logger=None, **worker_args):
        self._workers = []
        self.errors = {}
        self.default_worker = default_worker
        self.defaults = worker_args
        self.logger=logger if logger is not None else default_logger

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
                worker = self.default_worker(worker, 
                    logger=self.logger, 
                    **worker_args
                )
            worker.error_key = "{}: {}".format(
                len(self._workers),
                worker.error_key
            )
            self._workers.append(worker)
        return self

    def __call__(self, work):
        work = deepcopy(work)  # in case initial input is important

        # represents where each piece of work is in the process
        # first list being not done yet, last list being finished
        work_queues = [work] + [[] for w in self._workers]
        work_queues = map(Trickle, work_queues)
        work_queues[0].nomore = True  # no more input in Tricker 0

        # print "Before: {}".format(work_queues)

        # prepares all workers in stream by putting on separate threads
        tapestry = [threading.Thread(**{
            "target": self._workers[i],
            "args": (work_queues[i], work_queues[i + 1], self.errors)
        }) for i in range(len(self._workers))]  # prepare worker threads

        # start worker threads
        [t.start() for t in tapestry]  # start worker threads

        # return a reference to a Trickler of finished items
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
        return 1.0 / d

    def tee(d):
        time.sleep(d)
        return d

    #
    # Example
    #
    import logging
    lg = logging.getLogger(__name__)
    lg.addHandler(logging.StreamHandler())

    mystream = Stream(logger=lg).then([
        recip,
        lambda x: x ** 2
    ])

    for w in mystream._workers:
        print w.__name__

    results = mystream([1, 2])
    results.extend(mystream([1, 0]))
    for i in results:
        print "Done:", i

    print
    print "Errors"
    for e in sorted(mystream.errors.items()):
        print e

    print "This stream does {}preserve order.".format(
        "" if mystream.preserves_order else "NOT "
    )

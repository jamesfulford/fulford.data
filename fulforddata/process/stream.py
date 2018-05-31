"""
Stream
"""


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
        """
        Python list storing all items in queue.
        """

        self.i = 0
        """
        Indicates how far in the list the iteration has gone, by index.
        """
        
        self.nomore = False
        """
        When true, once the current queue of items is exhausted, iteration must end.
        """

    def __iter__(self):
        return self

    def __getitem__(self, i):
        return self.work[i]

    def __repr__(self):
        return "Tricker({})".format(self.work)

    __str__ = __repr__

    def append(self, item):
        """
        Add an item to the end of the line.
        """
        self.work.append(item)

    def extend(self, items):
        """
        Add a list of items to the end of the line.
        """
        self.work.extend(items)

    def get_next_if_any(self):
        """
        Returns the next item in the queue, if there is one queued.
        If nothing is waiting in queue, return None.
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
        Returns next item in the work list. Skips items of value 'None'.
        If no items remain and the nomore flag is True, raises StopIteration.
        Otherwise, waits and tries again.

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
    Represents a workflow made of multiple streamlined, order-dependent tasks.
    Useful for parallel processing and avoiding IO bottlenecks.

    To leverage parallization, be sure to wrap process functions in workers from
    fulforddata.process.workers.

    First, we should add 2 to each number, then we should square each number.

    >>> addThenSquare = Stream().then(lambda x: x + 2).then(lambda x: x ** 2)
    >>> list(addThenSquare([-2, -1, 0, 1, 2]))
    [0, 1, 4, 9, 16]

    (The output is wrapped with `list` because a Stream returns a sort of iterator
    which allows access to items as they finish processing. Wrapping in `list`
    forces the Stream to finish processing all items before returning.)

    Any keyword arguments are passed to the default worker upon initialization.
    To specify a worker type, wrap the function in that worker type
    and pass any keyword arguments there. Pre-initialized workers will not respect
    any keyword arguments supplied.

    For instance, the unpack argument accepted by workers allows for functions
    which return lists to have each item in the list considered as individual work
    items to the next worker.
    >>> no_unpack = Stream().then(lambda x: [i for i in range(1, x)])
    >>> list(no_unpack([3, 4, 5]))
    [[1, 2], [1, 2, 3], [1, 2, 3, 4]]

    >>> unpacks = Stream().then(lambda x: [i for i in range(1, x)], unpack=True)
    >>> list(unpacks([3, 4, 5]))
    [1, 2, 1, 2, 3, 1, 2, 3, 4]

    Here's how we can improve a workflow
    >>> from time import sleep
    >>> def wait(t):
    ...     sleep(t)
    ...     print("Ending " + str(t))
    ...     return t
    ...
    >>> thinker = Stream().then(wait)

    By default, each worker is single-threaded. So, the only worker in this Stream
    will have to finish processing the first item before it can start on the next item,
    even if most of the processing consists of idle activity.
    >>> list(thinker([3, 1, 4]))
    ... # doctest: +SKIP
    Ending 3
    Ending 1
    Ending 4
    [3, 1, 4]

    After about 8 seconds of twiddling thumbs, thinker is completely finished processing.

    Instead of waiting to complete one task to start the next, perhaps we can do these
    in parallel by using a different worker. By default, Stream assigns each task to be a
    single-threaded Worker (the default can be changed with the __init__ argument `default_worker`)

    >>> from fulforddata.process.workers import IOWorker
    >>> iothinker = Stream().then(IOWorker(wait))
    >>> list(iothinker([3, 1, 4]))
    ... # doctest: +SKIP
    Ending 1
    Ending 3
    Ending 4
    [1, 3, 4]

    After 4 seconds of computation, iothinker is completely done processing.
    However, the output is not in the same order as the input! This is because
    of how IOWorker operates: it returns work as soon as it is finished back
    into the stream.

    For convenience, the property .preserves_order indicates whether all workers
    respect order or if one worker does not respect order.
    >>> iothinker.preserves_order
    ... # doctest: +SKIP
    False

    >>> from fulforddata.process.workers import ThreadWorker
    >>> threadthinker = Stream().then(ThreadWorker(wait))
    >>> threadthinker.preserves_order
    True
    >>> list(threadthinker([3, 1, 4]))
    ... # doctest: +SKIP
    Ending 1
    Ending 3
    Ending 4
    [3, 1, 4]

    This time, after only 4 seconds of computation, the process fully completes.
    The difference is that a ThreadWorker will start work on the next items,
    however it will not return the product back into the stream until all prior
    items have finished processing. 
    
    Preserving the order comes at a cost, however: if a work item takes a long time to process, 
    it prevents all following items from re-entering the stream until it finishes processing, 
    causing a build-up of work for future workers to suddenly have to process after waiting for work to arrive.

    Errors:

    If any worker in the process raises an exception, the exception is logged
    to the logger (from the builtin logging module) provided to the Stream at
    initialization with the keyword `logger`.

    Exceptions are also put into the .errors dictionary, where keys are strings
    which include the name of the function. You can set some of these strings
    using the .error_key attribute of the worker provided. The values of this dictionary
    are lists of objects with the exception raised and the item it raised on.

    The item is removed from the Stream, and the worker moves on as usual.

    >>> def twelve_reciprocal(x):
    ...     return 12.0 / x
    ...
    >>> breakstream = Stream().then(twelve_reciprocal).then(round).then(int)
    >>> list(breakstream([2, 4, 0, 6, 12, 1]))
    [6, 3, 2, 1, 12]
    >>> for error_key, value in sorted(breakstream.errors.items()):
    ...     print error_key
    0: twelve_reciprocal <Worker>
    1: round <Worker>
    2: int <Worker>

    TODO: allow user to turn off automatic numbering of errors    
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
    # def wait(d):
    #     val = d["value"]
    #     if val > 5:
    #         raise Exception("TOO LONG")
    #     time.sleep(val)
    #     return d

    # def recip(d):
    #     return 1.0 / d

    # def tee(d):
    #     time.sleep(d)
    #     return d

    #
    # Example
    #
    # import logging
    # lg = logging.getLogger(__name__)
    # lg.addHandler(logging.StreamHandler())

    # mystream = Stream(logger=lg).then([
    #     recip,
    #     lambda x: x ** 2
    # ])

    # for w in mystream._workers:
    #     print w.__name__

    # results = mystream([1, 2])
    # results.extend(mystream([1, 0]))
    # for i in results:
    #     print "Done:", i

    # print
    # print "Errors"
    # for e in sorted(mystream.errors.items()):
    #     print e

    # print "This stream does {}preserve order.".format(
    #     "" if mystream.preserves_order else "NOT "
    # )

    from doctest import testmod
    testmod()

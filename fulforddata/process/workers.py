# workers.py

import requests
import logging
import functools

from multiprocessing import Pool as ProcessPool
from multiprocessing.pool import ThreadPool

default_logger = logging.getLogger(__name__)
default_logger.addHandler(logging.NullHandler())

MSG = "\n\t{1.__class__.__name__}: {1.message} raised by {0.__name__} on {2}\n"


class Worker(object):
    """
    Wraps function which does work. When called, uses wrapped function on each
        input and outputs into buffer given.

    If wrapped function raises an exception, that item is excluded from output
        and the item is collected in error_buffer under self.error_key
        and the exception is collected under self.error_key + "_exception".
        It is also logged to given logger as an exception.

    When done ALL work, sets output_list.nomore to True.

    >>> recip = Worker(lambda x: 1.0 / x)
    >>> work, output, error = [2, 1, 0], [], {}
    >>> recip(work, output, error)
    >>> output
    [.5, 1.0]
    # NOTE: work item #3, which was 0, raised an error
    """
    PRESERVES_ORDER = True
    UNPACK = False
    INSTANCES = 1

    def __init__(self, fn, unpack=None, instances=None, error_key=None, logger=None):     
        self.fn = fn
        functools.update_wrapper(self, fn)

        self.error_key = "{1.__name__} <{0.__class__.__name__}>".format(
            self, fn
        ) if error_key is None else error_key
        self.unpack = self.__class__.UNPACK if unpack is None else unpack
        self.instances = self.__class__.INSTANCES if instances is None else instances
        self.logger = logger if logger is not None else default_logger

    def push_to(self, output_list):
        def do(task):
            try:
                res = self.fn(task)
            except Exception as e:
                self.log(task, e)
                return None
            else:
                self.done(res, output_list)
        return do

    def process(self, work_list, output_list):
        """
        Default: single-threaded execution of work.
        Override this function for different workers.
        """
        map(self.push_to(output_list), work_list)

    def done(self, finished_product, output_list):
        if hasattr(finished_product, "__iter__") and self.unpack:
            output_list.extend(list(finished_product))
        else:
            output_list.append(finished_product)

    def log(self, item, exception):
        err = {
            "item": item,
            "exception": exception
        }
        self.error_buffer[self.error_key].append(err)
        self.logger.exception(exception, err)

    def __call__(self, work_list, output_list, error_buffer={}):
        # Prepare for errors
        self.error_buffer = error_buffer  # for self.log function
        error_buffer[self.error_key] = error_buffer.get(self.error_key, [])

        # Delegate
        self.process(work_list, output_list)

        # Tell the next Trickler that no more is coming
        if hasattr(output_list, "nomore"):
            output_list.nomore = True


class ThreadWorker(Worker):
    """
    Preserves order. If one request takes too long, the worker will start on
        later work but will hold up the stream until the slow request finishes.
    """
    PRESERVES_ORDER = True
    INSTANCES = 6

    def process(self, work_list, output_list):

        def do(task):
            try:
                return self.fn(task)
            except Exception as e:
                self.log(task, e)
                return e
        # do = self.push_to(output_list)  # magically doesn't work

        pool = ThreadPool(self.instances)
        for result in pool.imap(do, work_list):
            if not isinstance(result, Exception):
                self.done(result, output_list)
        pool.close()
        pool.join()


class IOWorker(Worker):
    """
    Does not preserve order, in exchange for less bottlenecking downstream.
    """
    PRESERVES_ORDER = False
    INSTANCES = 12

    def process(self, work_list, output_list):
        pool = ThreadPool(self.instances)
        pool.map(self.push_to(output_list), work_list)
        pool.close()
        pool.join()


class ProcessWorker(Worker):
    PRESERVES_ORDER = False
    INSTANCES = 4

    def process(self, work_list, output_list):
        """
        NOTE: This is not preserving order right now.
        NOTE: This also may not work.
        """
        def do(task):
            try:
                return self.fn(task)
            except Exception as e:
                self.log(task, e)
                return e

        pool = ProcessPool(self.instances)
        for result in pool.imap(do, work_list):
            if not isinstance(result, Exception):
                self.done(result, output_list)
        pool.close()
        pool.join()


def query(engine, sql, **defaults):
    def run_query(**kwargs):
        defaults.update(kwargs)
        sql = sql.format(**defaults)
        with engine.connection() as c:
            return c.execute(sql)
    return run_query


class API(object):
    def __init__(self, url):
        self.url = url

    @IOWorker
    def post(self, data):
        return requests.post(self.url, data=data)

    @IOWorker
    def get(self, params):
        return requests.get(self.url, params=params)

if __name__ == "__main__":
    print "Hello World"

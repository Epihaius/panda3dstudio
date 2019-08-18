from ..base import *


class UVManager:

    # structure to store callables through which data can be retrieved by id
    _data_retrievers = {}
    # store handlers of tasks by id
    _task_handlers = {}
    _defaults = {
        "data_retriever": lambda *args, **kwargs: None,
        "task_handler": lambda *args, **kwargs: None
    }
    _verbose = False

    @classmethod
    def init(cls, verbose=False):

        cls._verbose = verbose

    @classmethod
    def accept(cls, task_id, task_handler):
        """
        Make the manager accept a task by providing its id and handler (a callable).

        """

        cls._task_handlers[task_id] = task_handler

    @classmethod
    def do(cls, task_id, *args, **kwargs):
        """
        Make the manager do the task with the given id.
        The arguments provided will be passed to the handler associated with this id.

        """

        if task_id not in cls._task_handlers:

            logging.warning(f'CORE: task "{task_id}" is not defined.')

            if cls._verbose:
                print(f'CORE warning: task "{task_id}" is not defined.')

        task_handler = cls._task_handlers.get(task_id, cls._defaults["task_handler"])

        return task_handler(*args, **kwargs)

    @classmethod
    def expose(cls, data_id, retriever):
        """ Make data publicly available by id through a callable """

        cls._data_retrievers[data_id] = retriever

    @classmethod
    def get(cls, data_id, *args, **kwargs):
        """
        Obtain data by id. The arguments provided will be passed to the callable
        that returns the data.

        """

        if data_id not in cls._data_retrievers:

            logging.warning(f'CORE: data "{data_id}" is not defined.')

            if cls._verbose:
                print(f'CORE warning: data "{data_id}" is not defined.')

        retriever = cls._data_retrievers.get(data_id, cls._defaults["data_retriever"])

        return retriever(*args, **kwargs)


UVMgr = UVManager

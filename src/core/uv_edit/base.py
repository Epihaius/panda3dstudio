from ..base import *


class BaseObject(object):

    uv_space = None
    cam = None
    cam_node = None
    cam_lens = None
    geom_root = None
    mouse_watcher = None

    @classmethod
    def init(cls, uv_space, cam, cam_node, cam_lens, geom_root):

        cls.uv_space = uv_space
        cls.cam = cam
        cls.cam_node = cam_node
        cls.cam_lens = cam_lens
        cls.geom_root = geom_root

    @classmethod
    def set_mouse_watcher(cls, mouse_watcher):

        cls.mouse_watcher = mouse_watcher

    def setup(self, *args, **kwargs):
        """
        Should be called to set up things that cannot be handled during __init__(),
        e.g. because they depend on objects that were not created yet.
        Should return True if successful.

        Override in derived class.

        """

        return True


class UVManager(object):

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

            logging.warning('CORE: task "{}" is not defined.'.format(task_id))

            if cls._verbose:
                print('CORE warning: task "{}" is not defined.'.format(task_id))

        task_handler = cls._task_handlers.get(task_id, cls._defaults["task_handler"])

        return task_handler(*args, **kwargs)

    @classmethod
    def expose(cls, data_id, retriever):
        """ Make data publicly available by id through a callable """

        cls._data_retrievers[data_id] = retriever

    @classmethod
    def __get(cls, data_id, *args, **kwargs):
        """
        Obtain data by id. The arguments provided will be passed to the callable
        that returns the data.

        """

        if data_id not in cls._data_retrievers:

            logging.warning('CORE: data "{}" is not defined.'.format(data_id))

            if cls._verbose:
                print('CORE warning: data "{}" is not defined.')

        retriever = cls._data_retrievers.get(data_id, cls._defaults["data_retriever"])

        return retriever(*args, **kwargs)

    @classmethod
    def get(cls, data_id, *args, **kwargs):
        """
        Obtain data by id. This id can either be the id of the data, or it can be a
        sequence consisting of the id of the "owner" object and the id of the data
        itself.

        """

        if isinstance(data_id, (list, tuple)):

            obj_id, obj_data_id = data_id
            obj = cls.__get(obj_id)

            return obj.get(obj_data_id, *args, **kwargs)

        else:

            return cls.__get(data_id, *args, **kwargs)


UVMgr = UVManager

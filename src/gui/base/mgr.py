from .base import *


class GUIManager(object):

    # store handlers of tasks by id
    _task_handlers = {}
    # structure to store callables through which data can be retrieved by id
    _data_retrievers = {}
    _default_task_handler = lambda *args, **kwargs: None
    _default_data_retriever = lambda *args, **kwargs: None
    _task_mgr = None
    _msgr = None
    _app_mgr = None
    _verbose = False

    @classmethod
    def init(cls, app_mgr, verbose=False):

        cls._app_mgr = app_mgr
        cls._verbose = verbose
        base = app_mgr.get_base()
        cls._task_mgr = base.task_mgr
        cls._msgr = base.messenger
        cls.expose("base", lambda: cls._app_mgr.get_base())
        cls.expose("mouse_pointer", lambda i: cls._app_mgr.get_base().win.get_pointer(i))

    @classmethod
    def accept(cls, task_id, task_handler):
        """
        Let the manager accept a task by providing its id and handler.

        """

        cls._task_handlers[task_id] = task_handler

    @classmethod
    def do(cls, task_id, *args, **kwargs):
        """
        Let the manager do the task with the given id.
        The arguments provided will be passed to the handler associated with this id.

        """

        if task_id not in cls._task_handlers:

            logging.warning('GUI: task "{}" is not defined.'.format(task_id))

            if cls._verbose:
                print('GUI warning: task "{}" is not defined.'.format(task_id))

        task_handler = cls._task_handlers.get(task_id, cls._default_task_handler)

        return task_handler(*args, **kwargs)

    @classmethod
    def expose(cls, data_id, retriever):
        """ Make data publicly available by id through a callable """

        cls._data_retrievers[data_id] = retriever

    @classmethod
    def __get(cls, data_id, *args, **kwargs):
        """
        Obtain data by id.
        The arguments provided will be passed to the callable that returns the data.

        """

        if data_id not in cls._data_retrievers:

            logging.warning('GUI: data "{}" is not defined.'.format(data_id))

            if cls._verbose:
                print('GUI warning: data "{}" is not defined.'.format(data_id))

        retriever = cls._data_retrievers.get(data_id, cls._default_data_retriever)

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

    @classmethod
    def add_interface(cls, interface_id, key_handlers):

        cls._app_mgr.add_state_manager(interface_id, "GUI")
        cls._app_mgr.add_key_handlers(interface_id, key_handlers)

    @classmethod
    def add_state(cls, state_id, persistence, on_enter=None, on_exit=None, interface_id="main"):

        cls._app_mgr.add_state(interface_id, "GUI", state_id, persistence, on_enter, on_exit)

    @classmethod
    def set_initial_state(cls, state_id, interface_id="main"):

        cls._app_mgr.set_initial_state(interface_id, state_id)

    @classmethod
    def enter_state(cls, state_id, interface_id="main"):

        cls._app_mgr.enter_state(interface_id, state_id)

    @classmethod
    def exit_state(cls, state_id, interface_id="main"):

        cls._app_mgr.exit_state(interface_id, state_id)

    @classmethod
    def get_state_id(cls, interface_id="main"):

        return cls._app_mgr.get_state_id(interface_id, "GUI")

    @classmethod
    def get_state_persistence(cls, state_id, interface_id="main"):

        return cls._app_mgr.get_state_persistence(interface_id, "GUI", state_id)

    @classmethod
    def add_app_updater(cls, update_id, updater, kwargs=None, interface_id="main"):

        cls._app_mgr.add_updater("GUI", update_id, updater, kwargs, interface_id)

    @classmethod
    def update_app(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("GUI", True, True, update_id, *args, **kwargs)

    @classmethod
    def update_locally(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("GUI", True, False, update_id, *args, **kwargs)

    @classmethod
    def update_remotely(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("GUI", False, True, update_id, *args, **kwargs)

    @classmethod
    def update_interface(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "GUI", True, True,
                                             update_id, *args, **kwargs)

    @classmethod
    def update_interface_locally(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "GUI", True, False,
                                             update_id, *args, **kwargs)

    @classmethod
    def update_interface_remotely(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "GUI", False, True,
                                             update_id, *args, **kwargs)

    @classmethod
    def send(cls, *args):
        """ Convenience wrapper around ShowBase.messenger.send() """

        cls._msgr.send(*args)

    @classmethod
    def add_task(cls, *args, **kwargs):
        """
        Convenience wrapper around ShowBase.task_mgr.do_method_later() and
        ShowBase.task_mgr.add().

        """

        if isinstance(args[0], (int, float)) or "delayTime" in kwargs:
            cls._task_mgr.do_method_later(*args, **kwargs)
        else:
            cls._task_mgr.add(*args, **kwargs)

    @classmethod
    def do_next_frame(cls, *args, **kwargs):
        """ Convenience wrapper around ShowBase.task_mgr.do_method_later(0., ...) """

        cls._task_mgr.do_method_later(0., *args, **kwargs)

    @classmethod
    def remove_task(cls, task_name):
        """ Convenience wrapper around ShowBase.task_mgr.remove() """

        cls._task_mgr.remove(task_name)

    @classmethod
    def get_tasks_matching(cls, name_pattern):
        """ Convenience wrapper around ShowBase.task_mgr.get_tasks_matching() """

        return cls._task_mgr.getTasksMatching(name_pattern)

    @classmethod
    def add_cursor_region(cls, interface_id, mouse_region):

        cls._app_mgr.add_cursor_region(interface_id, mouse_region)

    @classmethod
    def remove_cursor_regions(cls, interface_id):

        cls._app_mgr.remove_cursor_regions(interface_id)

    @classmethod
    def set_cursor_regions_active(cls, interface_id, active=True):

        cls._app_mgr.set_cursor_regions_active(interface_id, active)

    @classmethod
    def set_cursor(cls, cursor_id, region_id=None):
        """ Set a cursor image loaded from file """

        if cursor_id == "main":
            cursor_filename = Filename()
        else:
            cursor_filename = Skin["cursors"][cursor_id]

        if region_id is None:
            cls._app_mgr.set_cursor("gui", cursor_filename)
        else:
            cls._app_mgr.set_cursor(region_id, cursor_filename)

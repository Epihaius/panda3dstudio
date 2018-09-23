from .base import *


class CoreManager(object):

    # structure to store handlers for received notifications
    _notification_handlers = {}
    # structure to store callables through which data can be retrieved by id
    _data_retrievers = {}
    # store handlers of tasks by id
    _task_handlers = {}
    _defaults = {
        "data_retriever": lambda *args, **kwargs: None,
        "task_handler": lambda *args, **kwargs: None
    }
    _core = None
    _cursors = {}
    _cursor = "main"
    _task_mgr = None
    _msgr = None
    _app_mgr = None
    _verbose = False

    @classmethod
    def init(cls, core, app_mgr, gizmo_root, picking_col_mgr, verbose=False):

        cls._core = core
        cls.expose("core", lambda: cls._core)
        cls._app_mgr = app_mgr
        base = app_mgr.get_base()
        cls.expose("base", lambda: cls._app_mgr.get_base())
        cls._verbose = verbose

        BaseObject.init(base.render, base.aspect2d, base.pixel2d, base.mouseWatcherNode, verbose)

        cls._cursors = {
            "create": Filename.binary_filename(GFX_PATH + "create.cur"),
            "select": Filename.binary_filename(GFX_PATH + "select.cur"),
            "translate": Filename.binary_filename(GFX_PATH + "translate.cur"),
            "rotate": Filename.binary_filename(GFX_PATH + "rotate.cur"),
            "scale": Filename.binary_filename(GFX_PATH + "scale.cur"),
            "link": Filename.binary_filename(GFX_PATH + "link.cur"),
            "no_link": Filename.binary_filename(GFX_PATH + "no_link.cur")
        }

        cls.expose("cursors", lambda: cls._cursors)

        cls._task_mgr = base.task_mgr
        cls._msgr = base.messenger
        cls.expose("gizmo_root", lambda: gizmo_root)

        def get_window_size():

            win_props = cls._app_mgr.get_base().win.get_properties()

            return win_props.get_x_size(), win_props.get_y_size()

        cls.expose("window_size", get_window_size)

        base.disable_mouse()
        mouse_watcher = base.mouseWatcherNode
        mouse_watcher.set_enter_pattern("region_enter")
        mouse_watcher.set_leave_pattern("region_leave")
        mouse_watcher.set_within_pattern("region_within")
        mouse_watcher.set_without_pattern("region_without")
        cls.expose("mouse_pointer", lambda i: cls._app_mgr.get_base().win.get_pointer(i))

        light_node = DirectionalLight("default_light")
        light_node.set_color((1., 1., 1., 1.))
        cls._default_light = NodePath(light_node)
        cls._default_light.set_hpr(20., -20., 0.)
        cls.expose("default_light", lambda: cls._default_light)

        MainObjects.init()
        MainObjects.setup()

        picking_col_mgr.init()

        cls.get("object_root").set_shader_input("light", cls._default_light)
        cls.get("object_root").set_shader_auto()

    @classmethod
    def add_notification_handler(cls, notification, obj_id, handler, once=False):

        cls._notification_handlers.setdefault(notification, {})[obj_id] = (handler, once)

    @classmethod
    def remove_notification_handler(cls, notification, obj_id):

        handlers = cls._notification_handlers.get(notification, {})

        if obj_id in handlers:
            del handlers[obj_id]

    @classmethod
    def notify(cls, notification, info=""):

        handlers = cls._notification_handlers.get(notification, {})

        for obj_id, handler_data in list(handlers.items()):

            handler, once = handler_data
            handler(info)

            if once:
                del handlers[obj_id]

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
    def do_gradually(cls, process, process_id="", descr="", cancellable=False):
        """
        Spread a time-consuming process over multiple frames.

        """

        return cls._core.do_gradually(process, process_id, descr, cancellable)

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
                print('CORE warning: data "{}" is not defined.'.format(data_id))

        retriever = cls._data_retrievers.get(data_id, cls._defaults["data_retriever"])

        return retriever(*args, **kwargs)

    @classmethod
    def get(cls, data_id, *args, **kwargs):
        """
        Obtain data by id. This id can either be the id of the data, or it can be a
        sequence consisting of the id of the "owner" object and the id of the data
        itself.
        Example of the latter:
            CoreManager.get( ("grid", "point_at_screen_pos") )

        """

        if isinstance(data_id, (list, tuple)):
            obj_id, obj_data_id = data_id
            obj = cls.__get(obj_id)
            return obj.get(obj_data_id, *args, **kwargs)
        else:
            return cls.__get(data_id, *args, **kwargs)

    @classmethod
    def add_interface(cls, interface_id, key_prefix="", mouse_watcher=None):

        listener = cls._core.add_listener(interface_id, key_prefix, mouse_watcher)
        cls._app_mgr.add_state_manager(interface_id, "CORE", listener)

    @classmethod
    def remove_interface(cls, interface_id):

        cls._core.remove_listener(interface_id)
        cls._app_mgr.remove_interface(interface_id)

    @classmethod
    def add_state(cls, state_id, persistence, on_enter=None, on_exit=None, interface_id="main"):

        cls._app_mgr.add_state(interface_id, "CORE", state_id, persistence, on_enter, on_exit)

    @classmethod
    def set_default_state(cls, state_id, interface_id="main"):

        cls._app_mgr.set_default_state(interface_id, state_id)

    @classmethod
    def enter_state(cls, state_id, interface_id="main"):

        cls._app_mgr.enter_state(interface_id, state_id)

    @classmethod
    def exit_state(cls, state_id, interface_id="main"):

        cls._app_mgr.exit_state(interface_id, state_id)

    @classmethod
    def exit_states(cls, min_persistence=None, interface_id="main"):

        cls._app_mgr.exit_states(interface_id, min_persistence)

    @classmethod
    def get_state_id(cls, interface_id="main"):

        return cls._app_mgr.get_state_id(interface_id, "CORE")

    @classmethod
    def get_state_persistence(cls, state_id, interface_id="main"):

        return cls._app_mgr.get_state_persistence(interface_id, "CORE", state_id)

    @classmethod
    def bind_state(cls, state_id, binding_id, event_props, event_handler, interface_id="main"):

        cls._app_mgr.bind_state(interface_id, state_id, binding_id, event_props,
                                event_handler)

    @classmethod
    def activate_bindings(cls, binding_ids, exclusive=False, interface_id="main"):

        cls._app_mgr.activate_bindings(interface_id, binding_ids, exclusive)

    @classmethod
    def add_app_updater(cls, update_id, updater, kwargs=None, interface_id="main"):

        cls._app_mgr.add_updater("CORE", update_id, updater, kwargs, interface_id)

    @classmethod
    def update_app(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("CORE", True, True, update_id, *args, **kwargs)

    @classmethod
    def update_locally(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("CORE", True, False, update_id, *args, **kwargs)

    @classmethod
    def update_remotely(cls, update_id, *args, **kwargs):

        return cls._app_mgr.update("CORE", False, True, update_id, *args, **kwargs)

    @classmethod
    def update_interface(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "CORE", True, True,
                                             update_id, *args, **kwargs)

    @classmethod
    def update_interface_locally(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "CORE", True, False,
                                             update_id, *args, **kwargs)

    @classmethod
    def update_interface_remotely(cls, interface_id, update_id, *args, **kwargs):

        return cls._app_mgr.update_interface(interface_id, "CORE", False, True,
                                             update_id, *args, **kwargs)

    @classmethod
    def handle_key_down_remotely(cls, key, interface_id="main"):

        return cls._app_mgr.handle_key_down(interface_id, key)

    @classmethod
    def handle_key_up_remotely(cls, key, interface_id="main"):

        return cls._app_mgr.handle_key_up(interface_id, key)

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
##        return cls._task_mgr.get_tasks_matching(name_pattern)

    @classmethod
    def load_model(cls, *args, **kwargs):
        """ Convenience wrapper around ShowBase.loader.load_model() """

        return cls._app_mgr.get_base().loader.load_model(*args, **kwargs)

    @classmethod
    def load_tex(cls, *args, **kwargs):
        """ Convenience wrapper around ShowBase.loader.load_texture() """

        return cls._app_mgr.get_base().loader.load_texture(*args, **kwargs)

    @classmethod
    def render_frame(cls):
        """ Convenience wrapper around ShowBase.graphicsEngine.render_frame() """

        cls._app_mgr.get_base().graphicsEngine.render_frame()

    @classmethod
    def add_cursor_region(cls, interface_id, mouse_region):

        cls._app_mgr.add_cursor_region(interface_id, mouse_region)

    @classmethod
    def set_cursor(cls, cursor_id, region_id=None):
        """ Set a cursor image loaded from file """

        if cursor_id == "main":
            cursor_filename = Filename()
        else:
            cursor_filename = cls._cursors[cursor_id]

        if region_id is None:
            cls._app_mgr.set_cursor("viewport", cursor_filename)
        else:
            cls._app_mgr.set_cursor(region_id, cursor_filename)

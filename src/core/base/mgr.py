from .base import *


class CoreManager(object):

    # structure to store callables through which data can be retrieved by id
    _data_retrievers = {}
    # store handlers of tasks by id
    _task_handlers = {}
    _defaults = {
        "data_retriever": lambda *args, **kwargs: None,
        "task_handler": lambda *args, **kwargs: None
    }
    _core = None
    _task_mgr = None
    _msgr = None
    _app_mgr = None
    _verbose = False

    @classmethod
    def init(cls, core, app_mgr, gizmo_root, picking_col_mgr, verbose=False):

        cls._verbose = verbose

        BaseObject.init(core.render, core.aspect2d, core.camera, core.camNode,
                        core.camLens, core.mouseWatcherNode, verbose)

        cls._cursors = {
            "create": Filename.binary_filename(GFX_PATH + "create.cur"),
            "select": Filename.binary_filename(GFX_PATH + "select.cur"),
            "translate": Filename.binary_filename(GFX_PATH + "translate.cur"),
            "rotate": Filename.binary_filename(GFX_PATH + "rotate.cur"),
            "scale": Filename.binary_filename(GFX_PATH + "scale.cur")
        }

        cls.expose("cursors", lambda: cls._cursors)

        cls._core = core
        cls.expose("core", lambda: cls._core)
        cls._task_mgr = core.task_mgr
        cls._msgr = core.messenger
        cls._app_mgr = app_mgr
        cls.expose("gizmo_root", lambda: gizmo_root)

        cls.expose("window_width", lambda: cls._core.win.get_x_size())
        cls.expose("window_height", lambda: cls._core.win.get_y_size())

        cls._core.disable_mouse()
        cls.expose("mouse_pointer", lambda i: cls._core.win.get_pointer(i))

        cls.expose("mod_shift", lambda: cls._app_mgr.get_mod_key_code("shift"))
        cls.expose("mod_ctrl", lambda: cls._app_mgr.get_mod_key_code("ctrl"))
        cls.expose("mod_alt", lambda: cls._app_mgr.get_mod_key_code("alt"))

        picking_col_mgr.init()
        MainObjects.init()

        cls._default_light = None
        cls.expose("default_light", lambda: cls._default_light)

        p_light = PointLight("point_light")
        p_light.set_color(VBase4(1., 1., 1., 1.))
        cls._default_light = cls._core.render.attach_new_node(p_light)
        cls._default_light.set_pos(500., -1000., 700.)

        MainObjects.setup()

        cls.get("object_root").set_shader_input("light", cls._default_light)
        cls.get("object_root").set_shader_auto()

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

        if cls._verbose and task_id not in cls._task_handlers:
            print 'Core warning: task "%s" is not defined.' % task_id

        task_handler = cls._task_handlers.get(
            task_id, cls._defaults["task_handler"])

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

        if cls._verbose and data_id not in cls._data_retrievers:
            print 'Core warning: data "%s" is not defined.' % data_id

        retriever = cls._data_retrievers.get(
            data_id, cls._defaults["data_retriever"])

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

        listener = cls._core.add_listener(
            interface_id, key_prefix, mouse_watcher)
        cls._app_mgr.add_state_manager(interface_id, "CORE", listener)
        cls._app_mgr.add_key_handlers(
            interface_id, "CORE", listener.get_key_handlers())

    @classmethod
    def remove_interface(cls, interface_id):

        cls._core.remove_listener(interface_id)
        cls._app_mgr.remove_interface(interface_id)

    @classmethod
    def add_state(cls, state_id, persistence, on_enter=None, on_exit=None, interface_id=""):

        cls._app_mgr.add_state(interface_id, "CORE",
                               state_id, persistence, on_enter, on_exit)

    @classmethod
    def set_initial_state(cls, state_id, interface_id=""):

        cls._app_mgr.set_initial_state(interface_id, state_id)

    @classmethod
    def enter_state(cls, state_id, interface_id=""):

        cls._app_mgr.enter_state(interface_id, state_id)

    @classmethod
    def exit_state(cls, state_id, interface_id=""):

        cls._app_mgr.exit_state(interface_id, state_id)

    @classmethod
    def get_state_id(cls, interface_id=""):

        return cls._app_mgr.get_state_id(interface_id, "CORE")

    @classmethod
    def get_state_persistence(cls, state_id, interface_id=""):

        return cls._app_mgr.get_state_persistence(interface_id, "CORE", state_id)

    @classmethod
    def bind_state(cls, state_id, binding_id, event_props, event_handler,
                   interface_id=""):

        cls._app_mgr.bind_state(interface_id, state_id, binding_id, event_props,
                                event_handler)

    @classmethod
    def activate_bindings(cls, binding_ids, exclusive=False, interface_id=""):

        cls._app_mgr.activate_bindings(interface_id, binding_ids, exclusive)

    @classmethod
    def add_app_updater(cls, update_id, updater, kwargs=None):

        cls._app_mgr.add_updater("CORE", update_id, updater, kwargs)

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
    def add_interface_updater(cls, interface_id, update_id, updater, kwargs=None):

        cls._app_mgr.add_interface_updater(
            interface_id, "CORE", update_id, updater, kwargs)

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
    def convert_from_remote_format(cls, format_type, data):

        return cls._app_mgr.convert_from_format("CORE", format_type, data)

    @classmethod
    def convert_to_remote_format(cls, format_type, data):

        return cls._app_mgr.convert_to_format("CORE", format_type, data)

    @classmethod
    def remotely_handle_key_down(cls, key, interface_id=""):

        return cls._app_mgr.remotely_handle_key_down(interface_id, "CORE", key)

    @classmethod
    def remotely_handle_key_up(cls, key, interface_id=""):

        return cls._app_mgr.remotely_handle_key_up(interface_id, "CORE", key)

    @classmethod
    def set_global(cls, global_id, value):
        """
        Set a certain global value.
        This can be done from *any* object, while a value obtained through
        CoreManager.get() can only be set through the object that initially exposed
        it.

        """

        cls._app_mgr.set_global(global_id, value)

    @classmethod
    def get_global(cls, global_id):
        """
        Get the current value of a certain global.
        Also see set_global().

        """

        return cls._app_mgr.get_global(global_id)

    @classmethod
    def reset_globals(cls):
        """ Reset all globals to their initial values """

        cls._app_mgr.reset_globals()

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

        return cls._task_mgr.get_tasks_matching(name_pattern)

    @classmethod
    def load_model(cls, *args, **kwargs):
        """ Convenience wrapper around ShowBase.loader.load_model() """

        return cls._core.loader.load_model(*args, **kwargs)

    @classmethod
    def load_tex(cls, *args, **kwargs):
        """ Convenience wrapper around ShowBase.loader.load_texture() """

        return cls._core.loader.load_texture(*args, **kwargs)

    @classmethod
    def render_frame(cls):
        """ Convenience wrapper around ShowBase.graphicsEngine.render_frame() """

        cls._core.graphicsEngine.render_frame()

    @classmethod
    def set_cursor(cls, cursor_name):
        """ Set a cursor image loaded from file """

        win_props = WindowProperties()

        if cursor_name == "main":
            win_props.set_cursor_filename(Filename())
        else:
            win_props.set_cursor_filename(cls._cursors[cursor_name])

        cls._core.win.request_properties(win_props)

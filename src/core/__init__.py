from .base import *
from .base.base import _PendingTask
from . import (cam, nav, view, history, scene, import_, export, create, select, transform,
               transf_center, coord_sys, geom, hierarchy, helpers, texmap, material, snap, align)


class Core:

    def __init__(self, app_mgr, verbose=False):

        self._app_mgr = app_mgr
        self._verbose = verbose
        KeyEventListener.init_event_ids()
        self._listeners = {"main": KeyEventListener()}
        self._gizmo_root = NodePath("gizmo_root")
        self._long_process_id = ""

        def handle_pending_tasks(task):

            PendingTasks.handle(["object", "ui"], True)
            Mgr.update_remotely("pending_tasks")

            return task.cont

        GD.showbase.task_mgr.add(handle_pending_tasks, "handle_pending_tasks", sort=48)

    def setup(self):

        self._listeners["main"].set_mouse_watcher(GD.mouse_watcher)

        Mgr.init(self, self._app_mgr, self._gizmo_root, PickingColorIDManager, self._verbose)
        _PendingTask.init(self.do_gradually)

        GD.set_default("active_interface", "main")
        GD.set_default("open_file", "")
        GD.set_default("shift_down", False)
        GD.set_default("ctrl_down", False)
        GD.set_default("alt_down", False)
        GD.set_default("long_process_running", False)
        GD.set_default("progress_steps", 0)

        def enter_suppressed_state(*args):

            Mgr.do("enable_view_gizmo", False)
            self.__suppress_events()
            Mgr.notify("suppressed_state_enter")

        def exit_suppressed_state(*args):

            def task(t):

                if not Mgr.get_state_id() == "suppressed":
                    Mgr.do("enable_view_gizmo")
                    self.__suppress_events(False)
                    Mgr.notify("suppressed_state_exit")

            Mgr.do_next_frame(task, "exit_suppressed_state")

        Mgr.add_state("suppressed", -1000, enter_suppressed_state, exit_suppressed_state)
        Mgr.add_state("inactive", -1000)

        Mgr.add_notification_handler("long_process_cancelled", "core", self.__cancel_long_process)
        notifier = lambda: Mgr.notify("long_process_cancelled", self._long_process_id)
        Mgr.add_app_updater("long_process_cancellation", notifier)
        Mgr.add_app_updater("screenshot_removal", self.__schedule_screenshot_removal)
        Mgr.add_app_updater("uv_edit_init", self.__init_uv_editing)

    def __init_uv_editing(self):

        from . import uv_edit

        MainObjects.init("uv")
        MainObjects.setup("uv")

    def __schedule_screenshot_removal(self):

        task = lambda: Mgr.update_remotely("screenshot", "remove")
        task_id = "remove_screenshot"
        PendingTasks.add(task, task_id, "ui", sort=100)

    def do_gradually(self, process, process_id="", descr="", cancellable=False):

        # The given process is expected to be a Python generator object;
        # it will be handled over multiple frames while a progressbar gives an indication
        # of when it will finish.

        if GD["long_process_running"]:
            return False

        PendingTasks.suspend()
        GD["long_process_running"] = True
        self._long_process_id = process_id
        task_mgr = GD.showbase.task_mgr
        Mgr.update_remotely("progress", "start", descr, cancellable)

        def progress(task):

            progress_steps = GD["progress_steps"]

            if progress_steps:
                Mgr.update_remotely("progress", "set_rate", 1. / progress_steps)
                Notifiers.mgr.debug(f'Long-running process to be handled over {progress_steps} frames.')
                GD["progress_steps"] = 0

            if next(process):
                Mgr.update_remotely("progress", "advance")
                return task.cont

            self.__end_long_process()
            Notifiers.mgr.debug(f'****** Long-running process finished: {process_id}.')

        task_mgr.add(progress, "progress")
        Notifiers.mgr.debug(f'****** Long-running process started: {process_id}.')

        return True

    def __end_long_process(self):

        Mgr.update_remotely("progress", "end")
        GD["long_process_running"] = False
        self._long_process_id = ""
        PendingTasks.suspend(False)

    def __cancel_long_process(self, info=""):

        Mgr.update_remotely("screenshot", "remove")
        GD["long_process_running"] = False
        self._long_process_id = ""
        PendingTasks.suspend(False)
        PendingTasks.clear()
        Mgr.remove_task("progress")
        Notifiers.mgr.debug('****** Long-running process cancelled.')

    def suppress_mouse_events(self, suppress=True, interface_id=None):

        if interface_id is None:
            for listener in self._listeners.values():
                listener.suppress_mouse_events(suppress)
        else:
            self._listeners[interface_id].suppress_mouse_events(suppress)

    def suppress_key_events(self, suppress=True, keys=None, interface_id=None):

        if interface_id is None:
            for listener in self._listeners.values():
                listener.suppress_key_events(suppress, keys)
        else:
            self._listeners[interface_id].suppress_key_events(suppress, keys)

    def __suppress_events(self, suppress=True):

        for listener in self._listeners.values():
            listener.suppress_mouse_events(suppress)

        for listener in self._listeners.values():
            listener.suppress_key_events(suppress)

    def add_listener(self, interface_id, key_prefix="", mouse_watcher=None):

        listener = KeyEventListener(interface_id, key_prefix, mouse_watcher)
        self._listeners[interface_id] = listener

        return listener

    def remove_listener(self, interface_id):

        if interface_id in self._listeners:
            listener = self._listeners[interface_id]
            listener.destroy()
            del self._listeners[interface_id]

    def get_listener(self, interface_id="main"):

        return self._listeners[interface_id]


class KeyEventListener:

    _event_ids = [
        "escape", "print_screen", "scroll_lock", "num_lock", "caps_lock", "backspace", "delete",
        "enter", "tab", "insert", "space", "arrow_left", "arrow_right", "arrow_up", "arrow_down",
        "home", "end", "page_up", "page_down", "shift", "control", "alt"
    ]

    @classmethod
    def init_event_ids(cls):

        for key_code in range(0x41, 0x5b):
            char = chr(key_code)
            cls._event_ids.append(char.lower())

        for key_code in list(range(0x21, 0x41)) + list(range(0x5b, 0x61)) + list(range(0x7b, 0x80)):
            cls._event_ids.append(chr(key_code))

        for i in range(12):
            cls._event_ids.append(f"f{i + 1}")

    def __init__(self, interface_id="main", prefix="", mouse_watcher=None):

        self._interface_id = interface_id
        self._prefix = prefix
        self._mouse_watcher = mouse_watcher

        self._listener = listener = DirectObject()
        self._evt_handlers = {}
        self._mouse_evt_handlers = {}

        mouse_btns = ("mouse1", "mouse2", "mouse3", "wheel_up", "wheel_down")

        for key in self._event_ids:
            listener.accept(prefix + key, self.__get_key_down_handler(key))
            listener.accept(prefix + key + "-up", self.__get_key_up_handler(key))

        for key in mouse_btns:
            handler = self.__get_key_down_handler(key, is_mouse_btn=True)
            listener.accept(prefix + key, handler)
            self._mouse_evt_handlers[prefix + key] = handler

        for key in mouse_btns[:3]:
            handler = self.__get_key_up_handler(key)
            listener.accept(prefix + key + "-up", handler)
            self._mouse_evt_handlers[prefix + key + "-up"] = handler

        handler = lambda: self.__handle_focus_loss()
        listener.accept("focus_loss", handler)

    def __get_key_down_handler(self, key, is_mouse_btn=False):

        def handle_key_down():

            if is_mouse_btn:

                index = 1 if GD["viewport"][1] == self._interface_id else 2

                if GD["viewport"]["active"] != index:
                    Mgr.update_app("active_viewport", index)

            else:

                index = GD["viewport"]["active"]

                if GD["viewport"][index] != self._interface_id:
                    return

            mod_key_down = self._mouse_watcher.is_button_down

            if mod_key_down("shift"):
                GD["shift_down"] = True

            if mod_key_down("control"):
                GD["ctrl_down"] = True

            if mod_key_down("alt"):
                GD["alt_down"] = True

            if not self.__handle_event(self._prefix + key):
                Mgr.handle_key_down_remotely(key, self._interface_id)

        return handle_key_down

    def __get_key_up_handler(self, key):

        def handle_key_up():

            index = GD["viewport"]["active"]

            if key == "shift":
                GD["shift_down"] = False
            elif key == "control":
                GD["ctrl_down"] = False
            elif key == "alt":
                GD["alt_down"] = False

            if GD["viewport"][index] != self._interface_id:
                return

            if not self.__handle_event(self._prefix + key + "-up"):
                Mgr.handle_key_up_remotely(key, self._interface_id)

        return handle_key_up

    def set_mouse_watcher(self, mouse_watcher):

        self._mouse_watcher = mouse_watcher

    def __handle_event(self, event_id, *args):

        if event_id[-3:] == "-up":
            mod_code = 0
        elif event_id.replace(self._prefix, "") in ("shift", "control", "alt"):
            mod_code = 0
        else:
            mod_key_codes = GD["mod_key_codes"]
            mod_shift = mod_key_codes["shift"]
            mod_ctrl = mod_key_codes["ctrl"]
            mod_alt = mod_key_codes["alt"]
            mod_code = mod_shift if GD["shift_down"] else 0
            mod_code |= mod_ctrl if GD["ctrl_down"] else 0
            mod_code |= mod_alt if GD["alt_down"] else 0

        if event_id in self._evt_handlers and mod_code in self._evt_handlers[event_id]:

            event_handler, handler_args, once = self._evt_handlers[event_id][mod_code]
            event_handler(*(handler_args + args))

            if once:

                del self._evt_handlers[event_id][mod_code]

                if not self._evt_handlers[event_id]:
                    del self._evt_handlers[event_id]

            return True

        return False

    def __handle_focus_loss(self, *args):

        event_id = self._prefix + "focus_loss"
        mod_code = 0

        if event_id in self._evt_handlers and mod_code in self._evt_handlers[event_id]:

            event_handler, handler_args, once = self._evt_handlers[event_id][mod_code]
            event_handler(*(handler_args + args))

            if once:

                del self._evt_handlers[event_id][mod_code]

                if not self._evt_handlers[event_id]:
                    del self._evt_handlers[event_id]

            return True

        return False

    def __accept(self, event_props, event_handler, handler_args, once=False):

        if handler_args:
            args = tuple(handler_args)
        else:
            args = ()

        mod_code_str, event_id = event_props.rpartition("|")[::2]
        event_id = self._prefix + event_id
        mod_code = int(mod_code_str) if mod_code_str else 0

        self._evt_handlers.setdefault(event_id, {})[mod_code] = (event_handler, args, once)

    def accept(self, event_props, event_handler, handler_args=None):

        self.__accept(event_props, event_handler, handler_args)

    def accept_once(self, event_props, event_handler, handler_args=None):

        self.__accept(event_props, event_handler, handler_args, once=True)

    def ignore(self, event_props):

        mod_code_str, event_id = event_props.rpartition("|")[::2]
        mod_code = int(mod_code_str) if mod_code_str else 0

        if event_id in self._evt_handlers and mod_code in self._evt_handlers[event_id]:

            del self._evt_handlers[event_id][mod_code]

            if not self._evt_handlers[event_id]:
                del self._evt_handlers[event_id]

    def ignore_all(self):

        self._evt_handlers.clear()

    def suppress_mouse_events(self, suppress=True):

        mouse_btns = ("mouse1", "mouse2", "mouse3", "wheel_up", "wheel_down")
        prefix = self._prefix
        listener = self._listener

        if suppress:

            for btn in mouse_btns:
                listener.ignore(prefix + btn)

            for btn in mouse_btns[:3]:
                listener.ignore(prefix + btn + "-up")

        else:

            for btn in mouse_btns:
                handler = self._mouse_evt_handlers[prefix + btn]
                listener.accept(prefix + btn, handler)

            for btn in mouse_btns[:3]:
                handler = self._mouse_evt_handlers[prefix + btn + "-up"]
                listener.accept(prefix + btn + "-up", handler)

    def suppress_key_events(self, suppress=True, keys=None):

        prefix = self._prefix
        listener = self._listener

        if keys is None:
            keys = self._event_ids

        if suppress:
            for key in keys:
                listener.ignore(prefix + key)
        else:
            for key in keys:
                listener.accept(prefix + key, self.__get_key_down_handler(key))

    def destroy(self):

        self._mouse_watcher = None
        self._listener.ignore_all()
        self._listener = None
        self._evt_handlers = {}
        self._mouse_evt_handlers = {}

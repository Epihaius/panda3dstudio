from .base import *
from .base.base import _PendingTask
from . import (cam, nav, view, history, scene, import_, export, create, select, transform,
               transf_center, coord_sys, geom, hierarchy, helpers, texmap, material)
from direct.showbase.ShowBase import ShowBase, DirectObject

loadPrcFileData("", """
                    sync-video #f
                    model-cache-dir
                    geom-cache-size 0
                    window-type none
                    depth-bits 24
                    notify-output p3ds.log
##                    show-buffers 1
##                    gl-debug true
##                    notify-level-glgsg debug

                    """
                )


class Core(ShowBase):

    def __init__(self, viewport_data, eventloop_handler, app_mgr, verbose=False):

        ShowBase.__init__(self)

        self._app_mgr = app_mgr
        self._verbose = verbose
        KeyEventListener.init_event_ids()
        self._listeners = {"": KeyEventListener()}
        self._gizmo_root = NodePath("gizmo_root")
        self._screenshot = None
        self._hidden_widgets = None
        self._progress_bar = None
        self._long_process_id = ""

        size, handle, callback = viewport_data
        self.__create_window(size, handle)

        def handle_pending_tasks(task):

            PendingTasks.handle(["object", "ui"], True)
            Mgr.update_remotely("pending_tasks")

            return task.cont

        def handle_event_loop(task):

            eventloop_handler()

            return task.cont

        self.task_mgr.add(handle_pending_tasks, "handle_pending_tasks", sort=48)
        self.task_mgr.add(handle_event_loop, "process_event_loop", sort=55)

        def handle_window_event(*args):

            window = args[0]
            has_focus = window.get_properties().get_foreground()
            viewport_name = window.get_name()
            callback(viewport_name, has_focus)

        self.accept("window-event", handle_window_event)

    def setup(self):

        self._listeners[""].set_mouse_watcher(self.mouseWatcherNode)

        Mgr.init(self, self._app_mgr, self._gizmo_root,
                 PickingColorIDManager, self._verbose)
        _PendingTask.init(self.do_gradually)

        GlobalData.set_default("open_file", "")
        GlobalData.set_default("active_viewport", "")
        GlobalData.set_default("shift_down", False)
        GlobalData.set_default("ctrl_down", False)
        GlobalData.set_default("alt_down", False)
        GlobalData.set_default("long_process_running", False)
        GlobalData.set_default("progress_steps", 0)

        enter_processing_mode = lambda *args: Mgr.update_app("status", "processing")
        Mgr.add_state("processing", -200, enter_processing_mode)
        enter_processing_no_cancel_mode = lambda *args: Mgr.update_app("status", "processing_no_cancel")
        Mgr.add_state("processing_no_cancel", -200, enter_processing_no_cancel_mode)

        def cancel_long_process(info=""):

            self.__end_long_process(cancellable=True)
            self.remove_screenshot()
            PendingTasks.clear()
            self.task_mgr.remove("progress")
            logging.debug('****** Long-running process cancelled.')

        Mgr.add_notification_handler("long_process_cancelled", "core", cancel_long_process)
        Mgr.bind_state("processing", "cancel process", "escape",
                       lambda: Mgr.notify("long_process_cancelled", self._long_process_id))

        status_data = GlobalData["status_data"]
        mode_text = "Processing..."
        info_text = "<Escape> to cancel"
        status_data["processing"] = {"mode": mode_text, "info": info_text}
        info_text = "Please wait..."
        status_data["processing_no_cancel"] = {"mode": mode_text, "info": info_text}

        Mgr.add_app_updater("uv_edit_init", self.__init_uv_editing)

    def __init_uv_editing(self):

        from . import uv_edit

        MainObjects.init("uv_window")
        MainObjects.setup("uv_window")

    def show_screenshot(self):

        # A screenshot is generated and rendered to replace the rendering of the scene.
        # This can be used to hide temporary changes in object geometry during long processes.

        if self._screenshot:
            return

        region = self._fps_meter.get_display_region()
        region.set_active(False)
        self.graphicsEngine.render_frame()
        tex = self.win.get_screenshot()
        region.set_active(True)
        cm = CardMaker("fullscreen_quad")
        cm.set_frame_fullscreen_quad()
        self._screenshot = self.render2d.attach_new_node(cm.generate())
        self._screenshot.set_texture(tex)
        widgets = self.aspect2d.get_children()

        for widget in NodePathCollection(widgets):
            if widget.is_hidden() or (self._progress_bar and widget == self._progress_bar.get_root()):
                widgets.remove_path(widget)

        widgets.hide()
        self._hidden_widgets = widgets

        self.schedule_screenshot_removal()

    def schedule_screenshot_removal(self):

        task = self.remove_screenshot
        task_id = "remove_screenshot"
        PendingTasks.add(task, task_id, "ui", sort=100)

    def remove_screenshot(self):

        if not self._screenshot:
            return

        self._screenshot.remove_node()
        self._screenshot = None
        self._hidden_widgets.show()
        self._hidden_widgets = None

    def do_gradually(self, process, process_id="", descr="", cancellable=False):

        # The given process is expected to be a Python generator object;
        # it will be handled over multiple frames while a progressbar gives an indication
        # of when it will finish.

        if GlobalData["long_process_running"]:
            return False

        PendingTasks.suspend()
        GlobalData["long_process_running"] = True
        self._long_process_id = process_id
        self._progress_bar = ProgressBar(self.task_mgr, Point3(0., 0., -.95), (1.5, .06), descr)

        def progress(task):

            progress_steps = GlobalData["progress_steps"]

            if progress_steps:
                self._progress_bar.set_rate(1. / progress_steps)
                logging.debug('Long-running process to be handled over %d frames.', progress_steps)
                GlobalData["progress_steps"] = 0

            if process.next():
                self._progress_bar.advance()
                return task.cont

            self.__end_long_process(cancellable)
            logging.debug('****** Long-running process finished: %s.', process_id)

        self.task_mgr.add(progress, "progress")
        Mgr.enter_state("processing" if cancellable else "processing_no_cancel")
        Mgr.do("enable_view_gizmo", False)
        Mgr.do("enable_view_tiles", False)
        logging.debug('****** Long-running process started: %s.', process_id)

        return True

    def __end_long_process(self, cancellable):

        self._progress_bar.destroy()
        self._progress_bar = None
        GlobalData["long_process_running"] = False
        self._long_process_id = ""
        Mgr.exit_state("processing" if cancellable else "processing_no_cancel")
        PendingTasks.suspend(False)
        Mgr.do("enable_view_gizmo")
        Mgr.do("enable_view_tiles")

    def suppress_mouse_events(self, suppress=True):

        self._listeners[""].suppress_mouse_events(suppress)

    def suppress_key_events(self, suppress=True, keys=None):

        self._listeners[""].suppress_key_events(suppress, keys)

    def add_listener(self, interface_id, key_prefix="", mouse_watcher=None):

        listener = KeyEventListener(interface_id, key_prefix, mouse_watcher)
        self._listeners[interface_id] = listener

        return listener

    def remove_listener(self, interface_id):

        if interface_id in self._listeners:
            listener = self._listeners[interface_id]
            listener.destroy()
            del self._listeners[interface_id]

    def get_listener(self, interface_id=""):

        return self._listeners[interface_id]

    def get_key_event_ids(self, interface_id=""):

        return self._listeners[interface_id].get_key_event_ids()

    def get_key_handlers(self, interface_id=""):

        return self._listeners[interface_id].get_key_handlers()

    @staticmethod
    def get_max_color_value():

        return 1.

    def __create_window(self, size, parent_handle):

        wp = WindowProperties.get_default()
        wp.set_foreground(False)
        wp.set_undecorated(True)
        wp.set_origin(0, 0)
        wp.set_size(*size)

        try:
            wp.set_parent_window(parent_handle)
        except OverflowError:
            wp.set_parent_window(parent_handle & 0xffffffff)

        self.windowType = "onscreen"
        self.open_default_window(props=wp, name="")

        self.mouseWatcherNode.set_modifier_buttons(ModifierButtons())
        self.buttonThrowers[0].node().set_modifier_buttons(ModifierButtons())

        # create a custom frame rate meter, so it can be placed at the bottom
        # of the viewport
        self._fps_meter = meter = FrameRateMeter("fps_meter")
        meter.setup_window(self.win)
        meter_np = NodePath(meter)
        meter_np.set_pos(0., 0., -1.95)


class KeyEventListener(object):

    _event_ids = {
                  "Esc": "escape",
                  "PrtScr": "print_screen",
                  "ScrlLk": "scroll_lock",
                  "NumLk": "num_lock",
                  "CapsLk": "caps_lock",
                  "BkSpace": "backspace",
                  "Del": "delete",
                  "Enter": "enter",
                  "Tab": "tab",
                  "Ins": "insert",
                  "Home": "home",
                  "End": "end",
                  "PgUp": "page_up",
                  "PgDn": "page_down",
                  "Left": "arrow_left",
                  "Right": "arrow_right",
                  "Up": "arrow_up",
                  "Down": "arrow_down",
                  "Shift": "shift",
                  "Ctrl": "control",
                  "Alt": "alt",
                  " ": "space",
    }

    @classmethod
    def init_event_ids(cls):

        for key_code in range(0x41, 0x5b):
            char = chr(key_code)
            cls._event_ids[char] = char.lower()

        for key_code in range(0x21, 0x41) + range(0x5b, 0x61) + range(0x7b, 0x80):
            cls._event_ids["%d" % key_code] = chr(key_code)

        for i in range(12):
            cls._event_ids["F%d" % (i + 1)] = "f%d" % (i + 1)

    def __init__(self, interface_id="", prefix="", mouse_watcher=None):

        self._interface_id = interface_id
        self._prefix = prefix
        self._mouse_watcher = mouse_watcher

        self._listener = listener = DirectObject.DirectObject()
        self._evt_handlers = {}
        self._mouse_evt_handlers = {}

        mouse_btns = ("mouse1", "mouse2", "mouse3", "wheel_up", "wheel_down")

        for key in self._event_ids.itervalues():
            listener.accept(prefix + key, self.__get_key_down_handler(key))
            listener.accept(prefix + key + "-up", self.__get_key_up_handler(key))

        for key in mouse_btns:
            handler = self.__get_key_down_handler(key)
            listener.accept(prefix + key, handler)
            self._mouse_evt_handlers[prefix + key] = handler

        for key in mouse_btns[:3]:
            handler = self.__get_key_up_handler(key)
            listener.accept(prefix + key + "-up", handler)
            self._mouse_evt_handlers[prefix + key + "-up"] = handler

    def __get_key_down_handler(self, key):

        def handle_key_down():

            mod_key_down = self._mouse_watcher.is_button_down

            if mod_key_down(KeyboardButton.shift()):
                GlobalData["shift_down"] = True

            if mod_key_down(KeyboardButton.control()):
                GlobalData["ctrl_down"] = True

            if mod_key_down(KeyboardButton.alt()):
                GlobalData["alt_down"] = True

            if not self.__handle_event(self._prefix + key):
                Mgr.remotely_handle_key_down(key, self._interface_id)

        return handle_key_down

    def __get_key_up_handler(self, key):

        def handle_key_up():

            if GlobalData["active_viewport"] != self._interface_id:
                return

            if key == "shift":
                GlobalData["shift_down"] = False
            elif key == "control":
                GlobalData["ctrl_down"] = False
            elif key == "alt":
                GlobalData["alt_down"] = False

            if not self.__handle_event(self._prefix + key + "-up"):
                Mgr.remotely_handle_key_up(key, self._interface_id)

        return handle_key_up

    def set_mouse_watcher(self, mouse_watcher):

        self._mouse_watcher = mouse_watcher

    def get_key_event_ids(self):

        return self._event_ids

    def get_key_handlers(self):

        prefix = self._prefix
        key_handlers = {
            "down": lambda event_id: self.__handle_event(prefix + event_id),
            "up": lambda event_id: self.__handle_event(prefix + event_id + "-up")
        }

        return key_handlers

    def __handle_event(self, event_id, *args):

        if event_id[-3:] == "-up":
            mod_code = 0
        elif event_id in ("shift", "control", "alt"):
            mod_code = 0
        else:
            mod_shift = Mgr.get("mod_shift")
            mod_ctrl = Mgr.get("mod_ctrl")
            mod_alt = Mgr.get("mod_alt")
            mod_code = mod_shift if GlobalData["shift_down"] else 0
            mod_code |= mod_ctrl if GlobalData["ctrl_down"] else 0
            mod_code |= mod_alt if GlobalData["alt_down"] else 0

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
            keys = self._event_ids.itervalues()

        if suppress:
            for key in keys:
                listener.ignore(prefix + key)
                if key not in ("shift", "control", "alt"):
                    listener.ignore(prefix + key + "-up")
        else:
            for key in keys:
                listener.accept(prefix + key, self.__get_key_down_handler(key))
                listener.accept(prefix + key + "-up", self.__get_key_up_handler(key))

    def destroy(self):

        self._listener.ignoreAll()  # ignore_all()
        del self._listener

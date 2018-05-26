from .base import *
from .components import Components
import sys


class GUI(object):

    def __init__(self, app_mgr, verbose=False):

        Mgr.init(app_mgr, verbose)
        load_skin(GlobalData["config"]["skin"])

        self._hotkey_prev = None

        self._title_main = "Panda3D Studio - "
        Mgr.accept("set_scene_label", self.__set_scene_label)
        Mgr.add_app_updater("pending_tasks", PendingTasks.handle)

        gui_cam_root = NodePath("gui_cam_root")
        self._gui_root = gui_root = gui_cam_root.attach_new_node("gui_root")
        CullBinManager.get_global_ptr().add_bin("gui", CullBinManager.BT_fixed, 41)
        gui_root.set_bin("gui", 1)
        gui_root.set_depth_test(False)
        gui_root.set_depth_write(False)
        Mgr.expose("gui_root", lambda: gui_root)
        gui_mouse_watcher_node = MouseWatcher("gui")
        cursor_watcher_node = MouseWatcher("cursor")
        GlobalData["mouse_watchers"] = [gui_mouse_watcher_node]
        Mgr.expose("mouse_watcher", lambda: gui_mouse_watcher_node)
        app_mgr.init_cursor_manager(cursor_watcher_node)

        self._components = Components()
        self._exit_handler = self._components.exit_handler
        w, h = size = Mgr.get("window_size")
        gui_mouse_watcher_node.set_frame(0., w, -h, 0.)

        wp = WindowProperties.get_default()
        wp.set_size(*size)
        wp.set_icon_filename(Filename.binary_filename(os.path.join("res", "p3ds.ico")))
        base = Mgr.get("base")
        base.open_default_window(props=wp, name="")
        base.windowEvent = lambda *args, **kwargs: None
        GlobalData["mouse_watchers"].append(base.mouseWatcherNode)
        base.mouseWatcherNode.set_modifier_buttons(ModifierButtons())
        base.buttonThrowers[0].node().set_modifier_buttons(ModifierButtons())

        viewport_display_regions = base.win.get_display_regions()[1:]
        GlobalData["viewport"]["display_regions"] = list(viewport_display_regions)

        # create a custom frame rate meter, so it can be placed at the bottom
        # of the viewport
        self._fps_meter = meter = FrameRateMeter("fps_meter")
        meter.setup_window(base.win)
        meter_np = NodePath(meter)
        meter_np.set_pos(0., 0., -1.95)
        GlobalData["fps_meter_display_region"] = meter.get_display_region()

        r, g, b, a = base.win.get_clear_color()
        background_color = (r, g, b, a)

        region = base.win.get_display_region(1)
        region.set_clear_color(background_color)
        region.set_clear_color_active(True)
        base.mouseWatcherNode.set_display_region(region)
        fov_v = base.camLens.get_vfov()
        fov_h = math.degrees(math.atan(math.tan(math.radians(fov_v * .5)) * 4. / 3.) * 2.)
        base.camLens.set_fov(fov_h, fov_v)

        gui_root.set_pos(-1., 0., 1.)
        gui_cam = gui_cam_root.attach_new_node(Camera("gui_cam"))
        lens = OrthographicLens()
        lens.set_near(-10.)
        lens.set_film_size(2., 2.)
        gui_cam.node().set_lens(lens)
        gui_cam.node().set_cull_bounds(OmniBoundingVolume())

        region = base.win.make_display_region(0., 1., 0., 1.)
        region.set_sort(10000)
        region.set_clear_depth(1000.)
        region.set_clear_depth_active(True)
        region.set_camera(gui_cam)
        gui_mouse_watcher_node.set_display_region(region)
        input_ctrl = base.mouseWatcher.get_parent()
        mw = input_ctrl.attach_new_node(gui_mouse_watcher_node)
        gui_mouse_watcher_node.set_enter_pattern("gui_region_enter")
        gui_mouse_watcher_node.set_leave_pattern("gui_region_leave")
        self._mouse_watcher = gui_mouse_watcher_node
        btn_thrower_node = ButtonThrower("btn_thrower_gui")
        btn_thrower_node.set_prefix("gui_")
        btn_thrower_node.set_modifier_buttons(ModifierButtons())
        btn_thrower_node.set_keystroke_event("keystroke")
        mw.attach_new_node(btn_thrower_node)
        cursor_watcher = input_ctrl.attach_new_node(cursor_watcher_node)
        gui_cursor_region = MouseWatcherRegion("gui", -1., 1., -1., 1.)
        gui_cursor_region.set_frame(-1., 1., -1., 1.)
        viewport_cursor_region = MouseWatcherRegion("viewport", 0., 0., 0., 0.)
        Mgr.expose("viewport_cursor_region", lambda: viewport_cursor_region)
        app_mgr.add_cursor_region("", gui_cursor_region)
        app_mgr.add_cursor_region("", viewport_cursor_region)

        base.accept("gui_region_enter", self.__on_region_enter)
        base.accept("gui_region_leave", self.__on_region_leave)
        base.accept("gui_mouse1", self.__on_left_down)
        base.accept("gui_mouse1-up", self.__on_left_up)
        base.accept("gui_mouse3", self.__on_right_down)
        base.accept("gui_mouse3-up", self.__on_right_up)

        base.win.set_close_request_event("close_request_event")
        base.accept("close_request_event", self.__on_close_request)

    def __on_region_enter(self, *args):

        name = args[0].get_name()

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_enter()
        elif name.startswith("toolbar_grip_"):
            Mgr.set_cursor("move")

    def __on_region_leave(self, *args):

        name = args[0].get_name()

        if name.startswith("widget_"):

            widget_id = int(name.replace("widget_", ""))

            # the widget could already be destroyed and thus unregistered
            if widget_id in Widget.registry:
                Widget.registry[widget_id].on_leave()

        elif name.startswith("toolbar_grip_") and not self._components.dragging_toolbar():

            Mgr.set_cursor("main")

    def __on_left_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name == "inputfield_mask":
            Mgr.do("accept_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_down()

    def __on_left_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_up()

    def __on_right_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name == "inputfield_mask":
            Mgr.do("reject_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_down()

    def __on_right_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_up()

    def setup(self):

        self._components.setup()
        self.__set_scene_label("New")

    def get_key_handlers(self):

        return {
            "down": self.__on_key_down,
            "up": self.__on_key_up
        }

    def __on_close_request(self):

        if self._exit_handler():
            Mgr.get("base").userExit()

    def __on_key_down(self, key=None):

        if not self._components.is_enabled():
            return

        mod_code = 0
        mod_key_codes = GlobalData["mod_key_codes"]

        if GlobalData["alt_down"]:
            mod_code |= mod_key_codes["alt"]

        if GlobalData["ctrl_down"]:
            mod_code |= mod_key_codes["ctrl"]

        if GlobalData["shift_down"]:
            mod_code |= mod_key_codes["shift"]

        hotkey = (key, mod_code)

        if self._hotkey_prev == hotkey:
            hotkey_repeat = True
        else:
            hotkey_repeat = False
            self._hotkey_prev = hotkey

        self._components.handle_hotkey(hotkey, hotkey_repeat)

    def __on_key_up(self, key=None):

        self._hotkey_prev = None

    def __set_scene_label(self, scene_label):

        props = WindowProperties()
        props.set_title(self._title_main + scene_label)
        Mgr.get("base").win.request_properties(props)

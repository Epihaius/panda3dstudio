from ..base import *
from ..tooltip import ToolTip
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField
from ..colorctrl import ColorPickerCtrl
from ..checkbox import CheckBox
from ..radiobtn import RadioButtonGroup
from ..panel import Panel, PanelStack
from .viewport import Viewport
from .transform import TransformToolbar
from .material import MaterialPanel, MaterialToolbar
from .hierarchy import HierarchyPanel
from .props import PropertyPanel
from .history import HistoryToolbar
from .grid import GridToolbar
from .status import StatusBar
from .menu import MenuBar
from .file import FileManager
from .create import CreationManager
from .edit import EditManager
from .view import ViewManager
from .render import RenderModeToolbar
from .obj_props import ObjectPropertiesMenu


class Components(BaseObject):

    def __init__(self, frame):

        border_bitmap_paths = {"toolbar": {}, "panel": {}}

        for part in ("left", "center", "right"):
            path = os.path.join(GFX_PATH, "toolbar_border_small_%s.png" % part)
            border_bitmap_paths["toolbar"][part] = path

        for part in ("left", "right", "top", "bottom", "topleft", "topright",
                     "bottomright", "bottomleft"):
            path = os.path.join(GFX_PATH, "panel_border_sunken_%s.png" % part)
            border_bitmap_paths["panel"][part] = path

        fore_color = wx.Colour(127, 178, 229)
        back_color = wx.Colour(51, 38, 76)

        ToolTip.init(frame)
        InputField.init(border_bitmap_paths, fore_color, back_color)
        ColorPickerCtrl.init(border_bitmap_paths)
        ComboBox.init((45, 10))
        Panel.init()
        CheckBox.init(border_bitmap_paths, fore_color.Get(), back_color)
        RadioButtonGroup.init(fore_color, back_color)

        def create_bitmap_paths(prefix, states, dupe_states=None):

            bitmap_paths = {}

            for part in ("left", "center", "right"):

                bitmap_paths[part] = {}

                for state in states:
                    path = os.path.join(GFX_PATH, "%s_%s_%s.png" % (prefix, part, state))
                    bitmap_paths[part][state] = path

                if dupe_states:
                    for dupe_state, orig_state in dupe_states:
                        bitmap_paths[part][dupe_state] = bitmap_paths[part][orig_state]

            return bitmap_paths

        states = ("hilited", "pressed", "active")
        paths = create_bitmap_paths("btn", states)
        Button.add_bitmap_paths("toolbar_button", paths)

        states = ("normal", "hilited", "pressed", "active")
        dupe_states = (("disabled", "normal"), )
        paths = create_bitmap_paths("btn_small", states, dupe_states)
        Button.add_bitmap_paths("panel_button", paths)

        states = ("flat", "hilited", "pressed")
        dupe_states = (("active", "pressed"), )
        paths = create_bitmap_paths("combobox", states, dupe_states)
        ComboBox.add_bitmap_paths("toolbar_button", paths)

        states = ("normal", "hilited", "pressed")
        dupe_states = (("flat", "normal"), ("active", "pressed"), ("disabled", "normal"))
        paths = create_bitmap_paths("combobox_small", states, dupe_states)
        ComboBox.add_bitmap_paths("panel_button", paths)

        w, h = size = frame.GetClientSize()

        self._disablers = {}

        Mgr.accept("enable_components", self.__enable)
        Mgr.accept("disable_components", self.__disable)
        Mgr.accept("add_component_disabler", self.__add_disabler)
        Mgr.accept("remove_component_disabler", self.__remove_disabler)

        self._components = components = {}

        self._viewport = Viewport(border_width=3,
                                  parent=frame,
                                  pos=wx.Point(0, 50 + 24),
                                  size=wx.Size(800, 600),
                                  name="p3d_viewport")
        self._obj_props_menu = ObjectPropertiesMenu(self._viewport)
        rot_toolbars = RotatingToolbars(frame, wx.Point(826, 0 + 24))
        toolbar = TransformToolbar(frame, wx.Point(0, 0 + 24), 826)
        rot_toolbars.add_toolbar("transform", toolbar)
        toolbar = MaterialToolbar(frame, wx.Point(0, 0 + 24), 826)
        rot_toolbars.add_toolbar("material", toolbar)
        components["main_toolbar"] = rot_toolbars
        x = 826 + rot_toolbars.get_spinner_width()
        toolbar = HistoryToolbar(frame, wx.Point(x, 0 + 24), w - x)
        components["history_toolbar"] = toolbar
        panel_stack = PanelStack(frame, wx.Point(806, 100 + 24), wx.Size(200, 506))
        components["panel_stack"] = panel_stack
        components["hierarchy_panel"] = HierarchyPanel(panel_stack)
        components["prop_panel"] = PropertyPanel(panel_stack)
        components["material_panel"] = MaterialPanel(panel_stack)
        statusbar = StatusBar(frame, wx.Point(0, h - 24), w)
        components["statusbar"] = statusbar
        toolbar = RenderModeToolbar(frame, wx.Point(806, 50 + 24), 200)
        components["render_mode_toolbar"] = toolbar
        toolbar = GridToolbar(frame, wx.Point(806, 606 + 24), 200)
        components["grid_toolbar"] = toolbar
        menubar = MenuBar(frame, wx.Point(0, 0), 1006)
        components["menubar"] = menubar

        self._uv_editing_initialized = False

        def uv_edit_command():

            if not self._uv_editing_initialized:
                Mgr.update_app("uv_edit_init")
                self._uv_editing_initialized = True

            Mgr.enter_state("uv_edit_mode")

        self._file_mgr = FileManager(menubar)
        self.exit_handler = self._file_mgr.on_exit
        self._edit_mgr = EditManager(menubar, uv_edit_command)
        self._view_mgr = ViewManager(menubar, self._viewport)
        self._creation_mgr = CreationManager(menubar)

        self._component_ids = ("menubar", "main_toolbar", "history_toolbar",
                               "panel_stack", "render_mode_toolbar", "grid_toolbar")

        def update_object_name_tag(is_shown, name="", pos=None, is_selected=False):

            if not is_shown:
                ToolTip.hide()
                return

            color = (255, 255, 0, 255) if is_selected else (255, 255, 255, 255)
            bitmap = ToolTip.create_bitmap(name, wx.Colour(*color))
            viewport_pos = self._viewport.GetScreenPosition()
            mouse_pos = wx.Point(*pos) + viewport_pos
            ToolTip.show(bitmap, mouse_pos, use_timer=False)

        Mgr.add_app_updater("object_name_tag", update_object_name_tag)
        Mgr.add_app_updater("uv_edit_init", self.__init_uv_editing)

    def setup(self):

        self._components["main_toolbar"].setup()
        self._edit_mgr.setup()
        self._creation_mgr.setup()
        self._view_mgr.setup()
        self._components["hierarchy_panel"].setup()
        self._components["prop_panel"].setup()
        self._components["material_panel"].setup()

        def enter_selection_mode(prev_state_id, is_active):

            Mgr.do("reset_viewport_border_color")
            self.__enable()

        def enter_navigation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 255, 255))

        nav_states = ("panning", "orbiting", "zooming", "dollying_forward",
                      "dollying_backward")

        add_state = Mgr.add_state
        add_state("selection_mode", 0, enter_selection_mode)
        add_state("navigation_mode", -100, enter_navigation_mode)

        for state in nav_states:
            add_state(state, -110, lambda prev_state_id, is_active: self.__disable(show=False),
                      lambda next_state_id, is_active: self.__enable())

    def __init_uv_editing(self):

        from .uv_edit import UVEditGUI

        self._components["uv_edit_gui"] = uv_gui = UVEditGUI()
        uv_gui.setup()

    def handle_key_down(self, key, mod_code, hotkey, hotkey_repeat):

        if Button.handle_hotkey(hotkey, hotkey_repeat):
            return

        menubar = self._components["menubar"]

        if menubar.is_enabled():
            menubar.handle_hotkey(hotkey)

    def handle_key_up(self, key):
        pass

    def get_viewport_data(self):

        size = self._viewport.get_size()
        handle = self._viewport.GetHandle()
        callback = self._viewport.get_callback()

        return size, handle, callback

    def __add_disabler(self, disabler_id, disabler, ids=None):

        comp_ids = self._component_ids if ids is None else ids
        self._disablers[disabler_id] = (disabler, comp_ids)

    def __remove_disabler(self, disabler_id):

        if disabler_id in self._disablers:
            del self._disablers[disabler_id]

    def __enable_component(self, comp_id, disablers):

        for disabler in disablers:
            if disabler():
                return

        self._components[comp_id].enable()

    def __enable(self):

        disablers = {}

        for disabler, comp_ids in self._disablers.itervalues():
            for comp_id in comp_ids:
                disablers.setdefault(comp_id, []).append(disabler)

        for comp_id in self._component_ids:
            self.__enable_component(comp_id, disablers.get(comp_id, []))

    def __disable(self, show=True, ids=None):

        if ids:
            for comp_id in ids:
                self._components[comp_id].disable(show)
        else:
            for comp_id in self._component_ids:
                self._components[comp_id].disable(show)

    def deactivate(self):

        self._components["main_toolbar"].deactivate()

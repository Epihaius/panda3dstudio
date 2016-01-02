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
from .props import PropertyPanel
from .history import HistoryToolbar
from .grid import GridToolbar
from .status import StatusBar
from .create import CreationButtons
from .file import FileButtons
from .render import RenderModeToolbar
from deepshelf import DeepShelf as DeepShelfBase


class DeepShelfActivator(BasicToolbar):

    def __init__(self, deepshelf_base, parent, pos, width):

        image = Cache.load("image", os.path.join(GFX_PATH, "toolbar_bg.png"))
        bitmap = image.Scale(width, 24).ConvertToBitmap()

        BasicToolbar.__init__(self, parent, pos, bitmap)

        icon = wx.Bitmap(os.path.join(GFX_PATH, "arrow_normal.png"))
        w_b, h_b = bitmap.GetSize()
        w_i, h_i = icon.GetSize()
        offset_x = (w_b - w_i) // 2
        offset_y = (h_b - h_i) // 2
        self._arrow_rect = wx.Rect(offset_x, offset_y, w_i, h_i)
        self._bitmap_normal = bitmap
        self._bitmap_hilited = bitmap.GetSubBitmap(wx.Rect(0, 0, w_b, h_b))
        mem_dc = wx.MemoryDC(self._bitmap_normal)
        mem_dc.DrawBitmap(icon, offset_x, offset_y)
        icon = wx.Bitmap(os.path.join(GFX_PATH, "arrow_hilited.png"))
        mem_dc.SelectObject(self._bitmap_hilited)
        mem_dc.DrawBitmap(icon, offset_x, offset_y)
        mem_dc.SelectObject(wx.NullBitmap)

        def on_enter_window(event):

            self._bitmap = self._bitmap_hilited
            self.RefreshRect(self._arrow_rect)
            deepshelf_base.on_enter()

        def on_leave_window(event):

            self._bitmap = self._bitmap_normal
            self.RefreshRect(self._arrow_rect)
            deepshelf_base.on_leave()

        wx.EVT_ENTER_WINDOW(self, on_enter_window)
        wx.EVT_LEAVE_WINDOW(self, on_leave_window)


class DeepShelf(object):

    def __init__(self, parent, gfx_path, pos, width, remote_task_handler,
                 components_to_replace):

        self._components_to_replace = components_to_replace

        def btn_down_handler():

            Mgr.do("reject_field_input")
            Mgr.get("default_focus_receiver").SetFocus()

        self._base = DeepShelfBase(parent, gfx_path, width, remote_task_handler,
                                   self.__on_show, self.__on_hide)
        self._base.set_tool_btn_down_handler(btn_down_handler)

        self._activator = DeepShelfActivator(self._base, parent, pos, width)

        self._base.hide()

        def add_tool_button(btn_id, btn_props, task_handler):

            self._base.add_tool_button(btn_id, btn_props)
            Mgr.accept("deepshelf_task %s" % btn_id, task_handler)

        Mgr.accept("add_deepshelf_btn", add_tool_button)
        Mgr.accept("toggle_deepshelf_btn", self._base.toggle_tool_button)

    def __on_show(self):

        self._activator.Hide()

        for component in self._components_to_replace:
            component.hide()

    def __on_hide(self):

        self._activator.Show()

        for component in self._components_to_replace:
            component.show()

    def set_tool_btn_down_handler(self, handler):

        self._base.set_tool_btn_down_handler(handler)

    def set_tool_btn_up_handler(self, handler):

        self._base.set_tool_btn_up_handler(handler)

    def show(self):

        self._base.show()

    def hide(self):

        self._base.hide()

    def enable(self):

        self._activator.Enable()

    def disable(self, show=False):

        if not self._activator.IsShown():

            self._base.hide()
            self._activator.Show()

            for component in self._components_to_replace:
                component.show()

        self._activator.Disable()

    def is_enabled(self):

        return self._activator.IsEnabled()

    def on_enter(self):

        self._base.on_enter()

    def on_leave(self):

        self._base.on_leave()

    def add_tool_button(self, btn_id, btn_props):

        self._base.add_tool_button(btn_id, btn_props)

    def toggle_tool_button(self, btn_id):

        self._base.toggle_tool_button(btn_id)

    def handle_key_down(self, key, mod_code=0):

        return self._base.handle_key_down(key, mod_code)

    def handle_key_up(self, key):

        return self._base.handle_key_up(key)


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
                    path = os.path.join(GFX_PATH, "%s_%s_%s.png" %
                                        (prefix, part, state))
                    bitmap_paths[part][state] = path

                if dupe_states:
                    for dupe_state, orig_state in dupe_states:
                        bitmap_paths[part][dupe_state] = bitmap_paths[
                            part][orig_state]

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
        dupe_states = (("flat", "normal"), ("active", "pressed"),
                       ("disabled", "normal"))
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
        rot_toolbars = RotatingToolbars(frame, wx.Point(826, 0 + 24))
        toolbar = TransformToolbar(frame, wx.Point(0, 0 + 24), 826)
        rot_toolbars.add_toolbar("transform", toolbar)
        toolbar = MaterialToolbar(frame, wx.Point(0, 0 + 24), 826)
        rot_toolbars.add_toolbar("material", toolbar)
        components["main_toolbar"] = rot_toolbars
        x = 826 + rot_toolbars.get_spinner_width()
        toolbar = HistoryToolbar(frame, wx.Point(x, 0 + 24), w - x)
        components["history_toolbar"] = toolbar
        panel_stack = PanelStack(frame, wx.Point(
            806, 100 + 24), wx.Size(200, 506))
        components["panel_stack"] = panel_stack
        components["prop_panel"] = PropertyPanel(panel_stack)
        components["material_panel"] = MaterialPanel(panel_stack)
        statusbar = StatusBar(frame, wx.Point(0, h - 24), w)
        components["statusbar"] = statusbar
        toolbar = RenderModeToolbar(frame, wx.Point(806, 50 + 24), 200)
        components["render_mode_toolbar"] = toolbar
        toolbar = GridToolbar(frame, wx.Point(806, 606 + 24), 200)
        components["grid_toolbar"] = toolbar

        gfx_path = os.path.join(GFX_PATH, "DeepShelf")
        comp_ids = ("main_toolbar", "history_toolbar")
        components_to_replace = [self._components[comp_id]
                                 for comp_id in comp_ids]
        deepshelf = DeepShelf(frame, gfx_path, wx.Point(0, 0), w, Mgr.do,
                              components_to_replace)
        components["deepshelf"] = deepshelf

        components["creation_btns"] = CreationButtons()
        components["file_btns"] = FileButtons()

        self._component_ids = ("deepshelf", "main_toolbar", "history_toolbar",
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

        self._uv_editing_initialized = False
        btn_id = "edit_uvs"
        label = "Edit UVs"
        icon_path = os.path.join(GFX_PATH, "icon_uv.png")
        btn_props = (label, icon_path)

        def command():

            if not self._uv_editing_initialized:
                Mgr.update_app("uv_edit_init")
                self._uv_editing_initialized = True

            Mgr.enter_state("uv_edit_mode")

        Mgr.do("add_deepshelf_btn", btn_id, btn_props, command)

        Mgr.add_app_updater("uv_edit_init", self.__init_uv_editing)

    def setup(self):

        self._components["main_toolbar"].setup()
        self._components["creation_btns"].setup()
        self._components["prop_panel"].setup()

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

        deepshelf = self._components["deepshelf"]

        if deepshelf.is_enabled():
            deepshelf.handle_key_down(key, mod_code)

    def handle_key_up(self, key):

        deepshelf = self._components["deepshelf"]

        if deepshelf.is_enabled():
            deepshelf.handle_key_up(key)

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

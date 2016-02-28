from ..base import *
from ..button import Button, ButtonGroup
from ..toggle import ToggleButtonGroup
from ..combobox import ComboBox
from ..field import InputField
from ..checkbox import CheckBox
from ..colorctrl import ColorPickerCtrl
from ..panel import *


class HierarchyPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Hierarchy", focus_receiver)

        self._parent = parent
        self._width = parent.get_width()

        self._comboboxes = {}
        self._checkboxes = {}
        self._color_pickers = {}
        self._fields = {}
        self._btns = {}
        self._radio_btns = {}
        self._toggle_btns = PanelToggleButtonGroup()
        toggle = (self.__set_xform_target_type, lambda: None)
        self._toggle_btns.set_default_toggle("all", toggle)

        panel_sizer = self.GetSizer()
        panel_sizer.Add(wx.Size(self._width, 0))
        parent.GetSizer().Add(self)

        bitmap_paths = Button.get_bitmap_paths("panel_button")

        # ********************** Object linking section ************************

        link_section = section = self.add_section("linking", "Object linking")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer)
        sizer_args = (0, wx.ALL, 2)

        label = "Link"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label, "Link objects",
                          self.__toggle_linking_mode, sizer_args, focus_receiver=focus_receiver)
        self._btns["link"] = btn

        btn_sizer.Add(wx.Size(5, 0))

        label = "Unlink"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label, "Unlink selected objects",
                          self.__unlink_objects, sizer_args, focus_receiver=focus_receiver)
        self._btns["unlink"] = btn

        btn_sizer.Add(wx.Size(5, 0))

        label = "Show"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label, "Show links between objects",
                          self.__toggle_link_visibility, sizer_args, focus_receiver=focus_receiver)
        self._btns["show_links"] = btn

        # ************************ Transforms section **************************

        transf_section = section = self.add_section("transforms", "Transforms")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Geom only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("geom"), lambda: None)
        self._toggle_btns.add_button(self, section, btn_sizer, "geom", toggle, bitmaps,
                                     "Transform geometry only", label, sizer_args=sizer_args)

        label = "Reset geom"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Reset geometry to original transform",
                          lambda: Mgr.update_app("geom_reset"), sizer_args,
                          focus_receiver=focus_receiver)
        self._btns["reset_geom"] = btn

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Pivot only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("pivot"), lambda: None)
        self._toggle_btns.add_button(self, section, btn_sizer, "pivot", toggle, bitmaps,
                                     "Transform pivot only", label, sizer_args=sizer_args)

        label = "Reset pivot"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Reset pivot to original transform",
                          lambda: Mgr.update_app("pivot_reset"), sizer_args,
                          focus_receiver=focus_receiver)
        self._btns["reset_pivot"] = btn

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Links only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("links"), lambda: None)
        self._toggle_btns.add_button(self, section, btn_sizer, "links", toggle, bitmaps,
                                     "Transform hierarchy links only", label, sizer_args=sizer_args)

        label = "No children"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("no_children"), lambda: None)
        self._toggle_btns.add_button(self, section, btn_sizer, "no_children", toggle, bitmaps,
                                     "Don't transform child objects", label, sizer_args=sizer_args)

        # **********************************************************************

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize():

            transf_section.expand(False)
            self.expand(False)
            self.update_parent()

        wx.CallAfter(finalize)

        Mgr.add_app_updater("object_link_viz", self.__update_link_visibility)
        Mgr.add_app_updater("transform_target_type", self.__update_xform_target_type)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def setup(self):

        def enter_linking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 255))
            self._btns["link"].set_active()

        def exit_linking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["link"].set_active(False)

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, enter_linking_mode, exit_linking_mode)

    def __toggle_linking_mode(self):

        if self._btns["link"].is_active():
            Mgr.exit_state("object_linking_mode")
        else:
            Mgr.enter_state("object_linking_mode")

    def __unlink_objects(self):

        Mgr.update_remotely("object_unlinking")

    def __toggle_link_visibility(self):

        show_links = Mgr.get_global("object_links_shown")
        Mgr.update_app("object_link_viz", not show_links)

    def __update_link_visibility(self, show):

        self._btns["show_links"].set_active(show)

    def __set_xform_target_type(self, target_type="all"):

        Mgr.set_global("transform_target_type", target_type)
        Mgr.update_app("transform_target_type")

    def __update_xform_target_type(self):

        target_type = Mgr.get_global("transform_target_type")

        if target_type == "all":
            self._toggle_btns.deactivate()
        else:
            self._toggle_btns.set_active_button(target_type)

        self.GetSizer().Layout()
        self.update_parent()

    def get_width(self):

        return self._width

    def get_client_width(self):

        return self._width - self.get_client_offset() * 2

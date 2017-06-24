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

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        checkbox = PanelCheckBox(self, section, subsizer, self.__toggle_link_visibility,
                                 sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["show_links"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Show links", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 2))
        group = section.add_group("Link")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        label = "Selection"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Link selected objects to target object",
                          lambda: self.__toggle_linking_mode("sel_linking_mode"))
        self._btns["sel_linking_mode"] = btn

        subsizer.Add(wx.Size(15, 0))
        label = "Pick..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Link single object to target object",
                          lambda: self.__toggle_linking_mode("obj_linking_mode"))
        self._btns["obj_linking_mode"] = btn

        sizer.Add(wx.Size(0, 2))
        group = section.add_group("Unlink")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        label = "Selection"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Unlink selected objects",
                          self.__unlink_selection)

        subsizer.Add(wx.Size(15, 0))
        label = "Pick..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, group, subsizer, bitmaps, label,
                          "Unlink single object",
                          lambda: self.__toggle_linking_mode("obj_unlinking_mode"))
        self._btns["obj_unlinking_mode"] = btn

        sizer.Add(wx.Size(0, 5))

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        checkbox = PanelCheckBox(self, section, subsizer,
                                 self.__toggle_group_member_linking,
                                 sizer_args=sizer_args)
        checkbox.check()
        self._checkboxes["group_member_linking_allowed"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Affect group membership:", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)

        subsizer.Add(wx.Size(20, 0))
        checkbox = PanelCheckBox(self, section, subsizer,
                                 self.__toggle_open_group_member_linking,
                                 sizer_args=sizer_args)
        checkbox.check()
        self._checkboxes["group_member_linking_open_groups_only"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("affect open groups only", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer)

        subsizer.Add(wx.Size(20, 0))
        checkbox = PanelCheckBox(self, section, subsizer,
                                 self.__toggle_group_member_unlink_only,
                                 sizer_args=sizer_args)
        checkbox.check()
        self._checkboxes["group_member_linking_unlink_only"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("unlink only", subsizer, sizer_args)

        # ************************ Transforms section **************************

        disabler = lambda: GlobalData["active_obj_level"] != "top"

        transf_section = section = self.add_section("transforms", "Transforms")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Geom only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("geom"), lambda: None)
        btn = self._toggle_btns.add_button(self, section, btn_sizer, "geom", toggle, bitmaps,
                                           "Transform geometry only", label, sizer_args=sizer_args)
        btn.add_disabler("subobj_lvl", disabler)

        label = "Reset geom"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Reset geometry to original transform",
                          lambda: Mgr.update_app("geom_reset"), sizer_args,
                          focus_receiver=focus_receiver)
        btn.add_disabler("subobj_lvl", disabler)
        self._btns["reset_geom"] = btn

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Pivot only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("pivot"), lambda: None)
        btn = self._toggle_btns.add_button(self, section, btn_sizer, "pivot", toggle, bitmaps,
                                           "Transform pivot only", label, sizer_args=sizer_args)
        btn.add_disabler("subobj_lvl", disabler)

        label = "Reset pivot"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label,
                          "Reset pivot to original transform",
                          lambda: Mgr.update_app("pivot_reset"), sizer_args,
                          focus_receiver=focus_receiver)
        btn.add_disabler("subobj_lvl", disabler)
        self._btns["reset_pivot"] = btn

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        sizer_args = (0, wx.ALL, 2)

        label = "Links only"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("links"), lambda: None)
        btn = self._toggle_btns.add_button(self, section, btn_sizer, "links", toggle, bitmaps,
                                           "Transform hierarchy links only", label, sizer_args=sizer_args)
        btn.add_disabler("subobj_lvl", disabler)

        label = "No children"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_xform_target_type("no_children"), lambda: None)
        btn = self._toggle_btns.add_button(self, section, btn_sizer, "no_children", toggle, bitmaps,
                                           "Don't transform child objects", label, sizer_args=sizer_args)
        btn.add_disabler("subobj_lvl", disabler)

        # **********************************************************************

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize():

            transf_section.expand(False)
            self.expand(False)
            self.update_parent()

        wx.CallAfter(finalize)

        def disable_xform_targets():

            self._toggle_btns.disable(show=False)
            self._btns["reset_geom"].disable(show=False)
            self._btns["reset_pivot"].disable(show=False)

        def enable_xform_targets():

            self._toggle_btns.enable()
            self._btns["reset_geom"].enable()
            self._btns["reset_pivot"].enable()

        Mgr.accept("disable_transform_targets", disable_xform_targets)
        Mgr.accept("enable_transform_targets", enable_xform_targets)
        Mgr.add_app_updater("object_link_viz", self.__update_link_visibility)
        Mgr.add_app_updater("group_options", self.__update_group_member_linking)
        Mgr.add_app_updater("transform_target_type", self.__update_xform_target_type)

    def __update_group_member_linking(self):

        for option, value in GlobalData["group_options"]["member_linking"].iteritems():
            self._checkboxes["group_member_linking_%s" % option].check(value)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def setup(self):

        def enter_linking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 255))
            self._btns[GlobalData["object_linking_mode"]].set_active()

        def exit_linking_mode(next_state_id, is_active):

            if not is_active:
                self._btns[GlobalData["object_linking_mode"]].set_active(False)

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, enter_linking_mode, exit_linking_mode)

    def __toggle_linking_mode(self, linking_mode):

        current_linking_mode = GlobalData["object_linking_mode"]

        if current_linking_mode and current_linking_mode != linking_mode:
            Mgr.exit_state("object_linking_mode")

        if self._btns[linking_mode].is_active():
            Mgr.exit_state("object_linking_mode")
            GlobalData["object_linking_mode"] = ""
        else:
            GlobalData["object_linking_mode"] = linking_mode
            Mgr.enter_state("object_linking_mode")

    def __unlink_selection(self):

        Mgr.update_remotely("selection_unlinking")

    def __toggle_link_visibility(self, links_shown):

        GlobalData["object_links_shown"] = links_shown
        Mgr.update_remotely("object_link_viz")

    def __update_link_visibility(self):

        links_shown = GlobalData["object_links_shown"]
        self._checkboxes["show_links"].check(links_shown)

    def __toggle_group_member_linking(self, allowed):

        GlobalData["group_options"]["member_linking"]["allowed"] = allowed

    def __toggle_open_group_member_linking(self, open_groups_only):

        GlobalData["group_options"]["member_linking"]["open_groups_only"] = open_groups_only

    def __toggle_group_member_unlink_only(self, unlink_only):

        GlobalData["group_options"]["member_linking"]["unlink_only"] = unlink_only

    def __set_xform_target_type(self, target_type="all"):

        GlobalData["transform_target_type"] = target_type
        Mgr.update_app("transform_target_type")

    def __update_xform_target_type(self):

        target_type = GlobalData["transform_target_type"]

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

from ....base import *
from ....panel import *


class SubobjectPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Subobjects", focus_receiver, "uv_window")

        self._parent = parent
        self._width = parent.get_width()

        panel_sizer = self.GetSizer()
        panel_sizer.Add(wx.Size(self._width, 0))
        parent.GetSizer().Add(self)

        self._btns = {}
        self._comboboxes = {}
        self._checkboxes = {}
        self._color_pickers = {}
        self._fields = {}
        self._radio_btns = {}
        self._uv_lvl_btns = uv_lvl_btns = PanelToggleButtonGroup()
        self._prev_obj_lvl = "poly"
        self._subobj_state_ids = {"vert": [], "edge": [], "poly": []}

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        sizer = self.get_top_ctrl_sizer()

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        sizer_args = (0, wx.RIGHT, 10)
        args = (sizer_args, sizer_args, None)
        subobj_types = ("vert", "edge", "poly")
        tooltip_prefixes = ("Vertex", "Edge", "Polygon")
        hotkeys = ((ord("V"), 0), (ord("E"), 0), (ord("P"), 0))

        for s_args, subobj_type, tooltip_prefix, hotkey in zip(args, subobj_types, tooltip_prefixes, hotkeys):
            label = subobj_type.title()
            bitmaps = PanelButton.create_button_bitmaps(
                "*%s" % label, bitmap_paths)
            get_command = lambda subobj_type: lambda: self.__set_subobj_level(
                subobj_type)
            toggle = (get_command(subobj_type), lambda: None)
            btn = uv_lvl_btns.add_button(self, self, btn_sizer, subobj_type, toggle, bitmaps,
                                         "%s level" % tooltip_prefix, label, sizer_args=s_args,
                                         focus_receiver=focus_receiver)
            btn.set_hotkey(hotkey, "uv_window")

        uv_lvl_btns.set_active_button("poly")

        # ************************* Vertex section ****************************

        vert_section = section = self.add_section("vert_props", "Vertices")
        sizer = section.get_client_sizer()

        label = "Break"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, sizer, bitmaps, label, "Break selected vertices",
                          self.__break_vertices, sizer_args, focus_receiver=focus_receiver)
        self._btns["break_vert"] = btn

        # ************************* Edge section ******************************

        edge_section = section = self.add_section("edge_props", "Edges")
        sizer = section.get_client_sizer()

        label = "Split"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, sizer, bitmaps, label, "Split selected edges",
                          self.__split_edges, sizer_args, focus_receiver=focus_receiver)
        self._btns["split_edge"] = btn

        # ************************* Polygon section ***************************

        poly_section = section = self.add_section("poly_props", "Polygons")
        sizer = section.get_client_sizer()

        label = "Detach"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, sizer, bitmaps, label, "Detach selected polygons",
                          self.__detach_polygons, sizer_args, focus_receiver=focus_receiver)
        self._btns["detach_poly"] = btn

        # **************************************************************************

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize_sections():

            for subobj_lvl in ("vert", "edge"):
                self.show_section("%s_props" % subobj_lvl, False, update=False)

            self.GetSizer().Layout()
            self.update_parent()

        wx.CallAfter(finalize_sections)

        Mgr.add_interface_updater("uv_window", "uv_level", self.__set_uv_level)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def __set_uv_level(self, uv_level):

        for subobj_lvl in ("vert", "edge", "poly"):
            self.show_section("%s_props" % subobj_lvl, False, update=False)

        self._uv_lvl_btns.set_active_button(uv_level)
        self.show_section("%s_props" % uv_level, update=False)

        for state_id in self._subobj_state_ids[self._prev_obj_lvl]:
            Mgr.exit_state(state_id)

        self._prev_obj_lvl = uv_level

        self.GetSizer().Layout()
        self.update_parent()

    def __set_subobj_level(self, uv_level):

        Mgr.update_interface("uv_window", "uv_level", uv_level)

    def __break_vertices(self):

        Mgr.update_interface_remotely("uv_window", "vert_break")

    def __split_edges(self):

        Mgr.update_interface_remotely("uv_window", "edge_split")

    def __detach_polygons(self):

        Mgr.update_interface_remotely("uv_window", "poly_detach")

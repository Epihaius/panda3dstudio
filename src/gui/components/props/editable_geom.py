from .base import *


class EditableGeomProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._btns = {}
        self._checkboxes = {}
        self._subobj_btns = PanelToggleButtonGroup()
        toggle = (self.__set_topobj_level, lambda: None)
        self._subobj_btns.set_default_toggle("top", toggle)

        # ************************* Subobject level section *******************

        main_section = section = panel.add_section("subobj_lvl", "Subobject level")
        sizer = section.get_client_sizer()

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Vert"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("vert"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "vert", toggle, bitmaps,
                                     "Vertex level", label, sizer_args=sizer_args)

        label = "Edge"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("edge"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "edge", toggle, bitmaps,
                                     "Edge level", label, sizer_args=sizer_args)

        label = "Poly"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("poly"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "poly", toggle, bitmaps,
                                     "Polygon level", label)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)

        # ************************* Vertex section ****************************

        vert_section = section = panel.add_section("vert_props", "Vertices")
        sizer = section.get_client_sizer()

        label = "Break"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, sizer, bitmaps, label, "Break selected vertices",
                          self.__break_vertices, sizer_args)
        self._btns["break_vert"] = btn

        # ************************* Edge section ******************************

        edge_section = section = panel.add_section("edge_props", "Edges")
        sizer = section.get_client_sizer()

        label = "Split"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, sizer, bitmaps, label, "Split selected edges",
                          self.__split_edges, sizer_args)
        self._btns["split_edge"] = btn

        # ************************* Polygon section ***************************

        poly_section = section = panel.add_section("poly_props", "Polygons")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)

        label = "Create"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Create single polygon",
                          self.__toggle_poly_creation, sizer_args)
        self._btns["create_poly"] = btn

        label = "Detach"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Detach selected polygons",
                          self.__detach_polygons, sizer_args)
        self._btns["detach_poly"] = btn

        sizer.Add(wx.Size(0, 4))

        group = section.add_group("Polygon smoothing")
        grp_sizer = group.get_client_sizer()

        btn_sizer = wx.BoxSizer()
        grp_sizer.Add(btn_sizer, 0)

        label = "Smooth"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label, "Smooth selected polygons",
                          self.__smooth_polygons, sizer_args)
        self._btns["smooth_polys"] = btn

        label = "Unsmooth"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label, "Flatten selected polygons",
                          lambda: self.__smooth_polygons(False))
        self._btns["unsmooth_polys"] = btn

        grp_sizer.Add(wx.Size(0, 4))

        label = "Smooth with other..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, grp_sizer, bitmaps, label,
                          "Smooth selected polygons with another",
                          self.__pick_poly_to_smooth_with, sizer_args)
        self._btns["smooth_with"] = btn

        grp_sizer.Add(wx.Size(0, 4))

        label = "Unsmooth with other..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, grp_sizer, bitmaps, label,
                          "Unsmooth selected polygons with another",
                          lambda: self.__pick_poly_to_smooth_with(False), sizer_args)
        self._btns["unsmooth_with"] = btn

        grp_sizer.Add(wx.Size(0, 4))

        btn_sizer = wx.BoxSizer()
        grp_sizer.Add(btn_sizer)

        label = "Smooth all"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label, "Smooth all polygons",
                          self.__smooth_all, sizer_args)
        self._btns["smooth_all"] = btn

        label = "Unsm. all"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label, "Flatten all polygons",
                          lambda: self.__smooth_all(False))
        self._btns["unsmooth_all"] = btn

        grp_sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)

        def handler(val):

            GlobalData["sel_polys_by_smoothing"] = val

        checkbox = PanelCheckBox(panel, group, subsizer, handler)
        checkbox.check(False)
        self._checkboxes["sel_by_smoothing"] = checkbox
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        group.add_text("Select by smoothing", subsizer, sizer_args)

        group = section.add_group("Polygon normals")
        grp_sizer = group.get_client_sizer()

        btn_sizer = wx.BoxSizer()
        grp_sizer.Add(btn_sizer)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Flip"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label,
                          "Reverse selected polygon normals",
                          self.__flip_poly_normals, sizer_args)
        self._btns["flip_normals"] = btn

        label = "Flip all"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label,
                          "Reverse all polygon normals",
                          lambda: self.__flip_poly_normals(False))
        self._btns["flip_all_normals"] = btn

        sizer.Add(wx.Size(0, 4))

        label = "Turn diagonals..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, sizer, bitmaps, label,
                          "Turn any diagonals of a selected polygon",
                          self.__turn_diagonals)
        self._btns["turn_diagonals"] = btn

        # **************************************************************************

    def setup(self):

        def enter_creation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (220, 220, 100))
            Mgr.do("enable_components")
            self._btns["create_poly"].set_active()

        def exit_creation_mode(next_state_id, is_active):

            if not is_active:
                self._btns["create_poly"].set_active(False)

        def enter_smoothing_poly_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            self._btns["smooth_with"].set_active()

        def exit_smoothing_poly_picking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["smooth_with"].set_active(False)

        def enter_unsmoothing_poly_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            self._btns["unsmooth_with"].set_active()

        def exit_unsmoothing_poly_picking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["unsmooth_with"].set_active(False)

        def enter_diagonal_turning_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            self._btns["turn_diagonals"].set_active()

        def exit_diagonal_turning_mode(next_state_id, is_active):

            if not is_active:
                self._btns["turn_diagonals"].set_active(False)

        add_state = Mgr.add_state
        add_state("poly_creation_mode", -10,
                  enter_creation_mode, exit_creation_mode)
        add_state("poly_creation", -11, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))
        add_state("smoothing_poly_picking_mode", -10, enter_smoothing_poly_picking_mode,
                  exit_smoothing_poly_picking_mode)
        add_state("unsmoothing_poly_picking_mode", -10, enter_unsmoothing_poly_picking_mode,
                  exit_unsmoothing_poly_picking_mode)
        add_state("diagonal_turning_mode", -10, enter_diagonal_turning_mode,
                  exit_diagonal_turning_mode)

        for subobj_lvl in ("vert", "edge", "poly"):
            self._panel.show_section("%s_props" % subobj_lvl, False, update=False)

        self._panel.GetSizer().Layout()
        self._panel.update_parent()

    def __update_object_level(self):

        if self._panel.get_active_object_type() != "editable_geom":
            return

        obj_lvl = GlobalData["active_obj_level"]

        for subobj_lvl in ("vert", "edge", "poly"):
            self._panel.show_section("%s_props" % subobj_lvl, False, update=False)

        if obj_lvl == "top":
            self._subobj_btns.deactivate()
            Mgr.do("enable_transform_targets")
            # exit any subobject modes
            Mgr.enter_state("selection_mode")
        else:
            Mgr.do("disable_transform_targets")
            self._subobj_btns.set_active_button(obj_lvl)
            self._panel.show_section("%s_props" % obj_lvl, update=False)

        self._panel.GetSizer().Layout()
        self._panel.update_parent()

    def __set_topobj_level(self):

        state_id = Mgr.get_state_id()
        GlobalData["active_obj_level"] = "top"
        Mgr.update_app("active_obj_level")

        if state_id == "navigation_mode":
            Mgr.enter_state("navigation_mode")

    def __set_subobj_level(self, subobj_lvl):

        if Mgr.get_state_id() != "navigation_mode":
            Mgr.enter_state("selection_mode")

        if GlobalData["transform_target_type"] != "all":
            GlobalData["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        GlobalData["active_obj_level"] = subobj_lvl
        Mgr.update_app("active_obj_level")

    def __toggle_poly_creation(self):

        if self._btns["create_poly"].is_active():
            Mgr.exit_state("poly_creation_mode")
        else:
            Mgr.enter_state("poly_creation_mode")

    def __break_vertices(self):

        Mgr.update_remotely("vert_break")

    def __split_edges(self):

        Mgr.update_remotely("edge_split")

    def __detach_polygons(self):

        Mgr.update_remotely("poly_detach")

    def __smooth_polygons(self, smooth=True):

        Mgr.update_remotely("poly_smoothing", smooth)

    def __smooth_all(self, smooth=True):

        Mgr.update_remotely("model_smoothing", smooth)

    def __pick_poly_to_smooth_with(self, smooth=True):

        pick_btn = self._btns[("" if smooth else "un") + "smooth_with"]
        state_id = ("" if smooth else "un") + "smoothing_poly_picking_mode"

        if pick_btn.is_active():
            Mgr.exit_state(state_id)
        else:
            Mgr.enter_state(state_id)

    def __flip_poly_normals(self, selected_only=True):

        Mgr.update_remotely("poly_flip", selected_only)

    def __turn_diagonals(self):

        pick_btn = self._btns["turn_diagonals"]

        if pick_btn.is_active():
            Mgr.exit_state("diagonal_turning_mode")
        else:
            Mgr.update_remotely("diagonal_turn")

    def get_base_type(self):

        return "editable_geom"

    def get_section_ids(self):

        return ["subobj_lvl"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        field = self._fields[prop_id]
        field.show_text()
        field.set_value(prop_id, value)
        field.set_text_color(wx.Colour(255, 255, 0))

    def set_object_property(self, prop_id, value):

        if prop_id not in self._fields:
            return

        field = self._fields[prop_id]
        field.set_value(prop_id, value)
        field.set_text_color()

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


PropertyPanel.add_properties("editable_geom", EditableGeomProperties)

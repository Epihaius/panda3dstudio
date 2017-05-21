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
        sizer_args = (0, wx.RIGHT, 10)

        label = "Vertex"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("vert"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "vert", toggle, bitmaps,
                                     "Vertex level", label, sizer_args=sizer_args)

        label = "Normal"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("normal"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "normal", toggle, bitmaps,
                                     "Normal level", label)

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

        label = "Edge"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("edge"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "edge", toggle, bitmaps,
                                     "Edge level", label, sizer_args=sizer_args)

        label = "Polygon"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        toggle = (lambda: self.__set_subobj_level("poly"), lambda: None)
        self._subobj_btns.add_button(panel, section, btn_sizer, "poly", toggle, bitmaps,
                                     "Polygon level", label)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)

        # ************************* Vertex section ****************************

        vert_section = section = panel.add_section("vert_props", "Vertices")
        sizer = section.get_client_sizer()

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 2)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_selection_via_poly)
        checkbox.check(False)
        self._checkboxes["sel_vert_via_poly"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Select using polygon", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 4)

        label = "Break"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label, "Break selected vertices",
                          self.__break_vertices, sizer_args)
        self._btns["break_verts"] = btn

        subsizer.Add(wx.Size(5, 0))
        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["vert_normal_preserve"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Lock normals", subsizer, sizer_args)

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Smooth"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Smooth selected vertices",
                          self.__smooth_vertices, sizer_args)
        self._btns["smooth_verts"] = btn

        label = "Sharpen"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Sharpen selected vertices",
                          lambda: self.__smooth_vertices(False), sizer_args)
        self._btns["sharpen_verts"] = btn

        # ************************* Normal section ****************************

        normal_section = section = panel.add_section("normal_props", "Vertex normals")
        sizer = section.get_client_sizer()

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 2)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_selection_via_poly)
        checkbox.check(False)
        self._checkboxes["sel_normal_via_poly"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Select using polygon", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        section.add_text("Length:", subsizer, sizer_args)
        field = PanelInputField(panel, section, subsizer, 80, sizer_args=sizer_args)
        prop_id = "normal_length"
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        field.set_input_parser(prop_id, self.__parse_length)
        self._fields[prop_id] = field

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Unify"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Average selected normals",
                          self.__unify_normals, sizer_args)
        self._btns["unify_normals"] = btn

        label = "Separate"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Separate selected normals",
                          lambda: self.__unify_normals(False), sizer_args)
        self._btns["separate_normals"] = btn

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)

        label = "Lock"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Lock selected normals",
                          self.__lock_normals, sizer_args)
        self._btns["lock_normals"] = btn

        label = "Unlock"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Unlock selected normals",
                          lambda: self.__lock_normals(False), sizer_args)
        self._btns["unlock_normals"] = btn

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)

        label = "Copy direction..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label,
                          "Copy selected normals' direction from picked normal",
                          self.__copy_normal_direction, sizer_args)
        self._btns["copy_normal_dir"] = btn

        # ************************* Edge section ******************************

        edge_section = section = panel.add_section("edge_props", "Edges")
        sizer = section.get_client_sizer()

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 2)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_selection_via_poly)
        checkbox.check(False)
        self._checkboxes["sel_edge_via_poly"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Select using polygon", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 2)

        def handler(by_border):

            GlobalData["subobj_edit_options"]["sel_edges_by_border"] = by_border

        checkbox = PanelCheckBox(panel, section, subsizer, handler)
        checkbox.check(False)
        self._checkboxes["sel_edges_by_border"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Select by border", subsizer, sizer_args)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 4)

        label = "Split"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label, "Split selected edges",
                          self.__split_edges, sizer_args)
        self._btns["split_edges"] = btn

        subsizer.Add(wx.Size(5, 0))
        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["edge_normal_preserve"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Lock normals", subsizer, sizer_args)

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Merge..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Merge picked edge (selection) with target",
                          self.__merge_edges, sizer_args)
        self._btns["merge_edges"] = btn

        label = "Bridge..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Create poly(s) between picked edge (selection) and target",
                          self.__bridge_edges)
        self._btns["bridge_edges"] = btn

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        def handler(value_id, segments):

            GlobalData["subobj_edit_options"]["edge_bridge_segments"] = segments

        section.add_text("Bridge segments:", subsizer, sizer_args)
        prop_id = "edge_bridge_segments"
        field = PanelInputField(panel, section, subsizer, 40, sizer_args=sizer_args)
        field.add_value(prop_id, "int", handler=handler)
        field.show_value(prop_id)
        field.set_input_parser(prop_id, self.__parse_edge_bridge_segments)
        field.set_value(prop_id, 1)
        self._fields[prop_id] = field

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Smooth"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Smooth selected edges",
                          self.__smooth_edges, sizer_args)
        self._btns["smooth_edges"] = btn

        label = "Sharpen"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Sharpen selected edges",
                          lambda: self.__smooth_edges(False))
        self._btns["sharpen_edges"] = btn

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

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        label = "Detach"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label, "Detach selected polygons",
                          self.__detach_polygons, sizer_args)
        self._btns["detach_poly"] = btn

        subsizer.Add(wx.Size(5, 0))
        checkbox = PanelCheckBox(panel, section, subsizer, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["poly_normal_preserve"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        section.add_text("Lock normals", subsizer, sizer_args)

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALL, 4)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Turn diagonals..."
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label,
                          "Turn any diagonals of a selected polygon",
                          self.__turn_diagonals, sizer_args)
        self._btns["turn_diagonals"] = btn

        sizer.Add(wx.Size(0, 4))

        group = section.add_group("Polygon regions")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        def handler(by_region):

            GlobalData["subobj_edit_options"]["sel_polys_by_region"] = by_region

        checkbox = PanelCheckBox(panel, group, subsizer, handler)
        checkbox.check(False)
        self._checkboxes["sel_polys_by_region"] = checkbox
        subsizer.Add(wx.Size(5, 0))
        group.add_text("Select by region", subsizer, sizer_args)

        grp_sizer.Add(wx.Size(0, 6))

        btn_sizer = wx.BoxSizer()
        grp_sizer.Add(btn_sizer)
        sizer_args = (0, wx.RIGHT, 5)

        label = "Flip (inside out)"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, btn_sizer, bitmaps, label,
                          "Flip regions containing selected polygons",
                          self.__flip_poly_regions, sizer_args)
        self._btns["flip_regions"] = btn

        sizer.Add(wx.Size(0, 2))

        group = section.add_group("Polygon smoothing")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        def handler(by_smoothing):

            GlobalData["subobj_edit_options"]["sel_polys_by_smoothing"] = by_smoothing

        checkbox = PanelCheckBox(panel, group, subsizer, handler)
        checkbox.check(False)
        self._checkboxes["sel_polys_by_smoothing"] = checkbox
        group.add_text("Select by smoothing", subsizer, sizer_args)

        grp_sizer.Add(wx.Size(0, 6))

        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)

        label = "Update"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, group, grp_sizer, bitmaps, label, "Update polygon smoothing",
                          self.__update_polygon_smoothing, sizer_args)
        self._btns["upd_poly_smoothing"] = btn

        grp_sizer.Add(wx.Size(0, 8))

        sizer_args = (0, wx.RIGHT, 5)

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

        # **************************************************************************

        Mgr.add_app_updater("subobj_edit_options", self.__update_subobj_edit_options)
        Mgr.add_app_updater("selection_via_poly", self.__update_selection_via_poly)
        Mgr.add_app_updater("normal_preserve", self.__update_normal_preserve)

    def __update_subobj_edit_options(self):

        for option, value in GlobalData["subobj_edit_options"].iteritems():
            if option in self._checkboxes:
                self._checkboxes[option].check(value)
            elif option in self._fields:
                self._fields[option].set_value(option, value)

    def __update_selection_via_poly(self):

        via_poly = GlobalData["selection_via_poly"]

        for subobj_type in ("vert", "edge", "normal"):
            self._checkboxes["sel_%s_via_poly" % subobj_type].check(via_poly)

    def __handle_selection_via_poly(self, via_poly):

        if Mgr.get_state_id() not in ("selection_mode", "navigation_mode"):
            for subobj_type in ("vert", "edge", "normal"):
                self._checkboxes["sel_%s_via_poly" % subobj_type].check(not via_poly)
            return

        Mgr.update_remotely("selection_via_poly", via_poly)

        for subobj_type in ("vert", "edge", "normal"):
            self._checkboxes["sel_%s_via_poly" % subobj_type].check(via_poly)

    def __update_normal_preserve(self):

        preserve = GlobalData["normal_preserve"]

        for subobj_type in ("vert", "edge", "poly"):
            self._checkboxes["%s_normal_preserve" % subobj_type].check(preserve)

    def __handle_normal_preserve(self, preserve):

        GlobalData["normal_preserve"] = preserve

        for subobj_type in ("vert", "edge", "poly"):
            self._checkboxes["%s_normal_preserve" % subobj_type].check(preserve)

    def setup(self):

        def enter_normal_dir_copy_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            Mgr.do("enable_components")
            self._btns["copy_normal_dir"].set_active()

        def exit_normal_dir_copy_mode(next_state_id, is_active):

            if not is_active:
                self._btns["copy_normal_dir"].set_active(False)

        def enter_edge_merge_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            Mgr.do("enable_components")
            self._btns["merge_edges"].set_active()

        def exit_edge_merge_mode(next_state_id, is_active):

            if not is_active:
                self._btns["merge_edges"].set_active(False)

        def enter_edge_bridge_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 50))
            Mgr.do("enable_components")
            self._btns["bridge_edges"].set_active()

        def exit_edge_bridge_mode(next_state_id, is_active):

            if not is_active:
                self._btns["bridge_edges"].set_active(False)

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
        add_state("normal_dir_copy_mode", -10,
                  enter_normal_dir_copy_mode, exit_normal_dir_copy_mode)
        add_state("edge_merge_mode", -10,
                  enter_edge_merge_mode, exit_edge_merge_mode)
        add_state("edge_merge", -11, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))
        add_state("edge_bridge_mode", -10,
                  enter_edge_bridge_mode, exit_edge_bridge_mode)
        add_state("edge_bridge", -11, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))
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

        for subobj_lvl in ("vert", "edge", "poly", "normal"):
            self._panel.show_section("%s_props" % subobj_lvl, False, update=False)

        self._panel.GetSizer().Layout()
        self._panel.update_parent()

    def __update_object_level(self):

        if self._panel.get_active_object_type() != "editable_geom":
            return

        obj_lvl = GlobalData["active_obj_level"]

        # exit any subobject modes
        Mgr.enter_state("selection_mode")

        def task():

            for subobj_lvl in ("vert", "edge", "poly", "normal"):
                if subobj_lvl != obj_lvl:
                    self._panel.show_section("%s_props" % subobj_lvl, False, update=False)

            if obj_lvl == "top":
                self._subobj_btns.deactivate()
                Mgr.do("enable_transform_targets")
            else:
                Mgr.do("disable_transform_targets")
                self._subobj_btns.set_active_button(obj_lvl)
                self._panel.show_section("%s_props" % obj_lvl, update=False)

        task_id = "update_subobj_layout"
        PendingTasks.add(task, task_id, sort=0)

        self._panel.update_layout()

    def __set_topobj_level(self):

        state_id = Mgr.get_state_id()
        GlobalData["active_obj_level"] = "top"
        Mgr.update_app("active_obj_level")

        if state_id == "navigation_mode":
            Mgr.enter_state("navigation_mode")

    def __set_subobj_level(self, subobj_lvl):

        state_id = Mgr.get_state_id()

        if state_id != "navigation_mode":
            Mgr.enter_state("selection_mode")

        if GlobalData["transform_target_type"] != "all":
            GlobalData["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        GlobalData["active_obj_level"] = subobj_lvl
        Mgr.update_app("active_obj_level")

        if state_id == "navigation_mode":
            Mgr.enter_state("navigation_mode")

    def __handle_value(self, value_id, value):

        Mgr.update_remotely(value_id, value)

    def __parse_length(self, length):

        try:
            return max(.001, abs(float(eval(length))))
        except:
            return None

    def __parse_edge_bridge_segments(self, segments):

        try:
            return max(1, abs(int(eval(segments))))
        except:
            return None

    def __toggle_poly_creation(self):

        if self._btns["create_poly"].is_active():
            Mgr.exit_state("poly_creation_mode")
        else:
            Mgr.enter_state("poly_creation_mode")

    def __break_vertices(self):

        Mgr.update_remotely("vert_break")

    def __smooth_vertices(self, smooth=True):

        Mgr.update_remotely("vert_smoothing", smooth)

    def __unify_normals(self, unify=True):

        Mgr.update_remotely("normal_unification", unify)

    def __lock_normals(self, lock=True):

        Mgr.update_remotely("normal_lock", lock)

    def __copy_normal_direction(self):

        btn = self._btns["copy_normal_dir"]

        if btn.is_active():
            Mgr.exit_state("normal_dir_copy_mode")
        else:
            Mgr.enter_state("normal_dir_copy_mode")

    def __split_edges(self):

        Mgr.update_remotely("edge_split")

    def __merge_edges(self):

        btn = self._btns["merge_edges"]

        if btn.is_active():
            Mgr.exit_state("edge_merge_mode")
        else:
            Mgr.enter_state("edge_merge_mode")

    def __bridge_edges(self):

        btn = self._btns["bridge_edges"]

        if btn.is_active():
            Mgr.exit_state("edge_bridge_mode")
        else:
            Mgr.enter_state("edge_bridge_mode")

    def __smooth_edges(self, smooth=True):

        Mgr.update_remotely("edge_smoothing", smooth)

    def __detach_polygons(self):

        Mgr.update_remotely("poly_detach")

    def __update_polygon_smoothing(self):

        Mgr.update_remotely("poly_smoothing_update")

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

    def __flip_poly_regions(self):

        Mgr.update_remotely("poly_region_flip")

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
        val, sel_count = value

        if sel_count == 1:
            field.set_value(prop_id, val)
            field.set_text_color()
            field.show_text()
        else:
            field.set_text_color(wx.Colour(127, 127, 127))
            field.show_text(False)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for prop_id, field in self._fields.iteritems():
            if prop_id not in ("normal_length", "edge_bridge_segments"):
                field.set_text_color(color)
                field.show_text(not multi_sel)


PropertyPanel.add_properties("editable_geom", EditableGeomProperties)

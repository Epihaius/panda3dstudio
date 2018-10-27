from .base import *


class EditableGeomProperties(object):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._btns = {}
        self._checkboxes = {}
        self._subobj_btns = ToggleButtonGroup()
        toggle = (self.__set_topobj_level, lambda: None)
        self._subobj_btns.set_default_toggle("top", toggle)

        # **************************** Geometry section ************************

        section = panel.add_section("geometry", "Geometry", hidden=True)

        text = "Merge object..."
        tooltip_text = "Not implemented"
        btn = PanelButton(section, text, "", tooltip_text, lambda: None)
        self._btns["merge_obj"] = btn
        borders = (0, 0, 10, 10)
        section.add(btn, alignment="center_h", borders=borders)

        # ************************* Subobject level section *******************

        section = panel.add_section("subobj_lvl", "Subobject level", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        section.add(sizer, expand=True)

        subobj_types = ("vert", "normal", "edge", "poly")
        subobj_names = ("Vertex", "Normal", "Edge", "Polygon")
        get_level_setter = lambda subobj_type: lambda: self.__set_subobj_level(subobj_type)

        for subobj_type, subobj_name in zip(subobj_types, subobj_names):
            tooltip_text = "{} level".format(subobj_name)
            btn = PanelButton(section, subobj_name, "", tooltip_text)
            sizer.add(btn, proportion_h=1.)
            toggle = (get_level_setter(subobj_type), lambda: None)
            self._subobj_btns.add_button(btn, subobj_type, toggle)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)

        # ************************* Vertex section ****************************

        section = panel.add_section("vert_props", "Vertices", hidden=True)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        borders = (0, 5, 0, 0)

        checkbox = PanelCheckBox(section, self.__handle_picking_via_poly)
        checkbox.check(False)
        self._checkboxes["pick_vert_via_poly"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Pick via polygon"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_picking_by_aiming)
        checkbox.check(False)
        self._checkboxes["pick_vert_by_aiming"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "aim"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Break"
        tooltip_text = "Break selected vertices"
        btn = PanelButton(section, text, "", tooltip_text, self.__break_vertices)
        self._btns["break_verts"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["vert_normal_preserve"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Lock normals"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Smooth"
        tooltip_text = "Smooth selected vertices"
        btn = PanelButton(section, text, "", tooltip_text, self.__smooth_vertices)
        self._btns["smooth_verts"] = btn
        btn_sizer.add(btn, proportion=1., borders=borders)

        text = "Sharpen"
        tooltip_text = "Sharpen selected vertices"
        btn = PanelButton(section, text, "", tooltip_text, lambda: self.__smooth_vertices(False))
        self._btns["sharpen_verts"] = btn
        btn_sizer.add(btn, proportion=1.)

        # ************************* Normal section ****************************

        section = panel.add_section("normal_props", "Vertex normals", hidden=True)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        checkbox = PanelCheckBox(section, self.__handle_picking_via_poly)
        checkbox.check(False)
        self._checkboxes["pick_normal_via_poly"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Pick via polygon"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_picking_by_aiming)
        checkbox.check(False)
        self._checkboxes["pick_normal_by_aiming"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "aim"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer)

        text = "Length:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        field = PanelInputField(section, 80)
        prop_id = "normal_length"
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        field.set_input_parser(prop_id, self.__parse_length)
        self._fields[prop_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Unify"
        tooltip_text = "Average selected normals"
        btn = PanelButton(section, text, "", tooltip_text, self.__unify_normals)
        self._btns["unify_normals"] = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        text = "Separate"
        tooltip_text = "Separate selected normals"
        btn = PanelButton(section, text, "", tooltip_text, lambda: self.__unify_normals(False))
        self._btns["separate_normals"] = btn
        btn_sizer.add(btn, proportion=1.)

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Lock"
        tooltip_text = "Lock selected normals"
        btn = PanelButton(section, text, "", tooltip_text, self.__lock_normals)
        self._btns["lock_normals"] = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        text = "Unlock"
        tooltip_text = "Unlock selected normals"
        btn = PanelButton(section, text, "", tooltip_text, lambda: self.__lock_normals(False))
        self._btns["unlock_normals"] = btn
        btn_sizer.add(btn, proportion=1.)

        section.add((0, 5))

        text = "Copy direction..."
        tooltip_text = "Copy selected normals' direction from picked normal"
        btn = PanelButton(section, text, "", tooltip_text, self.__copy_normal_direction)
        self._btns["copy_normal_dir"] = btn
        section.add(btn, alignment="center_h")

        # ************************* Edge section ******************************

        section = panel.add_section("edge_props", "Edges", hidden=True)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        checkbox = PanelCheckBox(section, self.__handle_picking_via_poly)
        checkbox.check(False)
        self._checkboxes["pick_edge_via_poly"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Pick via polygon"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_picking_by_aiming)
        checkbox.check(False)
        self._checkboxes["pick_edge_by_aiming"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "aim"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        def handler(by_border):

            GlobalData["subobj_edit_options"]["sel_edges_by_border"] = by_border

        checkbox = PanelCheckBox(section, handler)
        checkbox.check(False)
        self._checkboxes["sel_edges_by_border"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Select by border"
        sizer.add(PanelText(section, text), alignment="center_v")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Split"
        tooltip_text = "Split selected edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__split_edges)
        self._btns["split_edges"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["edge_normal_preserve"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Lock normals"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Merge..."
        tooltip_text = "Merge picked edge (selection) with target"
        btn = PanelButton(section, text, "", tooltip_text, self.__merge_edges)
        self._btns["merge_edges"] = btn
        btn_sizer.add(btn, proportion=1., borders=borders)

        text = "Bridge..."
        tooltip_text = "Create poly(s) between picked edge (selection) and target"
        btn = PanelButton(section, text, "", tooltip_text, self.__bridge_edges)
        self._btns["bridge_edges"] = btn
        btn_sizer.add(btn, proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer)

        def handler(value_id, segments):

            GlobalData["subobj_edit_options"]["edge_bridge_segments"] = segments

        text = "Bridge segments:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        prop_id = "edge_bridge_segments"
        field = PanelInputField(section, 40)
        field.add_value(prop_id, "int", handler=handler)
        field.show_value(prop_id)
        field.set_input_parser(prop_id, self.__parse_edge_bridge_segments)
        field.set_value(prop_id, 1, handle_value=False)
        self._fields[prop_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Smooth"
        tooltip_text = "Smooth selected edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__smooth_edges)
        self._btns["smooth_edges"] = btn
        btn_sizer.add(btn, proportion=1., borders=borders)

        text = "Sharpen"
        tooltip_text = "Sharpen selected edges"
        btn = PanelButton(section, text, "", tooltip_text, lambda: self.__smooth_edges(False))
        self._btns["sharpen_edges"] = btn
        btn_sizer.add(btn, proportion=1.)

        # ************************* Polygon section ***************************

        section = panel.add_section("poly_props", "Polygons", hidden=True)

        text = "Create"
        tooltip_text = "Create single polygon"
        btn = PanelButton(section, text, "", tooltip_text, self.__toggle_poly_creation)
        self._btns["create_poly"] = btn
        section.add(btn)

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Detach"
        tooltip_text = "Detach selected polygons"
        btn = PanelButton(section, text, "", tooltip_text, self.__detach_polygons)
        self._btns["detach_poly"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        checkbox = PanelCheckBox(section, self.__handle_normal_preserve)
        checkbox.check(False)
        self._checkboxes["poly_normal_preserve"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Lock normals"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        section.add((0, 5))

        text = "Turn diagonals..."
        tooltip_text = "Turn any diagonals of a selected polygon"
        btn = PanelButton(section, text, "", tooltip_text, self.__turn_diagonals)
        self._btns["turn_diagonals"] = btn
        section.add(btn)

        group = section.add_group("Contiguous surfaces")

        sizer = Sizer("horizontal")
        group.add(sizer)

        def handler(by_surface):

            GlobalData["subobj_edit_options"]["sel_polys_by_surface"] = by_surface

        checkbox = PanelCheckBox(group, handler)
        checkbox.check(False)
        self._checkboxes["sel_polys_by_surface"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Select by surface"
        sizer.add(PanelText(group, text), alignment="center_v")

        group.add((0, 6))

        text = "Invert surfaces"
        tooltip_text = "Invert surfaces containing selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__invert_poly_surfaces)
        self._btns["invert_surfaces"] = btn
        group.add(btn)

        group = section.add_group("Polygon smoothing")

        sizer = Sizer("horizontal")
        group.add(sizer)

        def handler(by_smoothing):

            GlobalData["subobj_edit_options"]["sel_polys_by_smoothing"] = by_smoothing

        checkbox = PanelCheckBox(group, handler)
        checkbox.check(False)
        self._checkboxes["sel_polys_by_smoothing"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Select by smoothing"
        sizer.add(PanelText(group, text), alignment="center_v")

        group.add((0, 6))

        text = "Update"
        tooltip_text = "Update polygon smoothing"
        btn = PanelButton(group, text, "", tooltip_text, self.__update_polygon_smoothing)
        self._btns["upd_poly_smoothing"] = btn
        group.add(btn, alignment="center_h")

        group.add((0, 10))

        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)
        subsizer1 = Sizer("vertical")
        btn_sizer.add(subsizer1, proportion=1., borders=borders)
        subsizer2 = Sizer("vertical")
        btn_sizer.add(subsizer2, proportion=1.)

        text = "Smooth"
        tooltip_text = "Smooth selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__smooth_polygons)
        self._btns["smooth_polys"] = btn
        subsizer1.add(btn, expand=True)

        text = "Unsmooth"
        tooltip_text = "Flatten selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, lambda: self.__smooth_polygons(False))
        self._btns["unsmooth_polys"] = btn
        subsizer2.add(btn, expand=True)

        borders = (0, 0, 0, 5)

        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)

        text = "Smooth all"
        tooltip_text = "Smooth all polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__smooth_all)
        self._btns["smooth_all"] = btn
        subsizer1.add(btn, expand=True, borders=borders)

        text = "Unsm. all"
        tooltip_text = "Flatten all polygons"
        btn = PanelButton(group, text, "", tooltip_text, lambda: self.__smooth_all(False))
        self._btns["unsmooth_all"] = btn
        subsizer2.add(btn, expand=True, borders=borders)

        group.add((0, 5))

        borders = (0, 5, 0, 0)

        text = "Smooth with other..."
        tooltip_text = "Smooth selected polygons with another"
        btn = PanelButton(group, text, "", tooltip_text, self.__pick_poly_to_smooth_with)
        self._btns["smooth_with"] = btn
        group.add(btn, expand=True)

        group.add((0, 5))

        text = "Unsmooth with other..."
        tooltip_text = "Unsmooth selected polygons with another"
        btn = PanelButton(group, text, "", tooltip_text, lambda: self.__pick_poly_to_smooth_with(False))
        self._btns["unsmooth_with"] = btn
        group.add(btn, expand=True)

        # **************************************************************************

        Mgr.add_app_updater("subobj_edit_options", self.__update_subobj_edit_options)

    def __update_subobj_edit_options(self):

        for option, value in GlobalData["subobj_edit_options"].items():
            if option == "pick_via_poly":
                for subobj_type in ("vert", "edge", "normal"):
                    self._checkboxes["pick_{}_via_poly".format(subobj_type)].check(value)
            elif option == "pick_by_aiming":
                for subobj_type in ("vert", "edge", "normal"):
                    self._checkboxes["pick_{}_by_aiming".format(subobj_type)].check(value)
            elif option == "normal_preserve":
                for subobj_type in ("vert", "edge", "poly"):
                    self._checkboxes["{}_normal_preserve".format(subobj_type)].check(value)
            elif option in self._checkboxes:
                self._checkboxes[option].check(value)
            elif option in self._fields:
                self._fields[option].set_value(option, value, handle_value=False)

    def __handle_picking_via_poly(self, via_poly):

        Mgr.update_remotely("picking_via_poly", via_poly)

        for subobj_type in ("vert", "edge", "normal"):
            self._checkboxes["pick_{}_via_poly".format(subobj_type)].check(via_poly)

    def __handle_picking_by_aiming(self, by_aiming):

        GlobalData["subobj_edit_options"]["pick_by_aiming"] = by_aiming

        for subobj_type in ("vert", "edge", "normal"):
            self._checkboxes["pick_{}_by_aiming".format(subobj_type)].check(by_aiming)

    def __handle_normal_preserve(self, preserve):

        GlobalData["subobj_edit_options"]["normal_preserve"] = preserve

        for subobj_type in ("vert", "edge", "poly"):
            self._checkboxes["{}_normal_preserve".format(subobj_type)].check(preserve)

    def setup(self):

        def enter_normal_dir_copy_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["copy_normal_dir"].set_active()

        def exit_normal_dir_copy_mode(next_state_id, is_active):

            if not is_active:
                self._btns["copy_normal_dir"].set_active(False)

        def enter_edge_merge_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["merge_edges"].set_active()

        def exit_edge_merge_mode(next_state_id, is_active):

            if not is_active:
                self._btns["merge_edges"].set_active(False)

        def enter_edge_bridge_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["bridge_edges"].set_active()

        def exit_edge_bridge_mode(next_state_id, is_active):

            if not is_active:
                self._btns["bridge_edges"].set_active(False)

        def enter_creation_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            Mgr.do("enable_gui")
            self._btns["create_poly"].set_active()

        def exit_creation_mode(next_state_id, is_active):

            if not is_active:
                self._btns["create_poly"].set_active(False)

        def enter_smoothing_poly_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._btns["smooth_with"].set_active()

        def exit_smoothing_poly_picking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["smooth_with"].set_active(False)

        def enter_unsmoothing_poly_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._btns["unsmooth_with"].set_active()

        def exit_unsmoothing_poly_picking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["unsmooth_with"].set_active(False)

        def enter_diagonal_turning_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
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
                  Mgr.do("enable_gui", False))
        add_state("edge_bridge_mode", -10,
                  enter_edge_bridge_mode, exit_edge_bridge_mode)
        add_state("edge_bridge", -11, lambda prev_state_id, is_active:
                  Mgr.do("enable_gui", False))
        add_state("poly_creation_mode", -10,
                  enter_creation_mode, exit_creation_mode)
        add_state("poly_creation", -11, lambda prev_state_id, is_active:
                  Mgr.do("enable_gui", False))
        add_state("smoothing_poly_picking_mode", -10, enter_smoothing_poly_picking_mode,
                  exit_smoothing_poly_picking_mode)
        add_state("unsmoothing_poly_picking_mode", -10, enter_unsmoothing_poly_picking_mode,
                  exit_unsmoothing_poly_picking_mode)
        add_state("diagonal_turning_mode", -10, enter_diagonal_turning_mode,
                  exit_diagonal_turning_mode)

        self._panel.get_section("geometry").expand(False)

    def __update_object_level(self):

        if self._panel.get_active_object_type() != "editable_geom":
            return

        obj_lvl = GlobalData["active_obj_level"]

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)

        def task():

            if obj_lvl == "top":
                self._subobj_btns.deactivate()
                Mgr.do("enable_transform_targets")
                Mgr.do("enable_selection_dialog")
            else:
                Mgr.do("disable_selection_dialog")
                Mgr.do("disable_transform_targets")
                self._subobj_btns.set_active_button(obj_lvl)
                self._panel.get_section("{}_props".format(obj_lvl)).show()

            for subobj_lvl in ("vert", "edge", "poly", "normal"):
                if subobj_lvl != obj_lvl:
                    self._panel.get_section("{}_props".format(subobj_lvl)).hide()

        task_id = "update_obj_level"
        PendingTasks.add(task, task_id, sort=0)

    def __set_topobj_level(self):

        GlobalData["active_obj_level"] = "top"
        Mgr.update_app("active_obj_level")

    def __set_subobj_level(self, subobj_lvl):

        if GlobalData["transform_target_type"] != "all":
            GlobalData["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        GlobalData["active_obj_level"] = subobj_lvl
        Mgr.update_app("active_obj_level")

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

    def __invert_poly_surfaces(self):

        Mgr.update_remotely("poly_surface_inversion")

    def __turn_diagonals(self):

        pick_btn = self._btns["turn_diagonals"]

        if pick_btn.is_active():
            Mgr.exit_state("diagonal_turning_mode")
        else:
            Mgr.update_remotely("diagonal_turn")

    def get_base_type(self):

        return "editable_geom"

    def get_section_ids(self):

        return ["geometry", "subobj_lvl"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        field = self._fields[prop_id]
        field.show_text()
        field.set_value(prop_id, value, handle_value=False)
        field.set_text_color((1., 1., 0., 1.))

    def set_object_property(self, prop_id, value):

        if prop_id not in self._fields:
            return

        field = self._fields[prop_id]
        val, sel_count = value

        if sel_count == 1:
            field.set_value(prop_id, val, handle_value=False)
            field.set_text_color()
            field.show_text()
        else:
            field.set_text_color((.5, .5, .5, 1.))
            field.show_text(False)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        for prop_id, field in self._fields.items():
            if prop_id not in ("normal_length", "edge_bridge_segments"):
                field.set_text_color(color)
                field.show_text(not multi_sel)


PropertyPanel.add_properties("editable_geom", EditableGeomProperties)

from .base import *


class UnlockedGeomProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._btns = {}
        self._checkbuttons = {}
        self._radio_btns = {}
        self._subobj_btns = ToggleButtonGroup()
        toggle = (self.__set_topobj_level, lambda: None)
        self._subobj_btns.set_default_toggle("top", toggle)

        # ************************* Subobject level section *******************

        subobj_types = ("vert", "normal", "edge", "poly")
        get_level_setter = lambda subobj_type: lambda: self.__set_subobj_level(subobj_type)

        for subobj_type in subobj_types:
            btn = widgets["buttons"][f"unlocked_geom_{subobj_type}"]
            toggle = (get_level_setter(subobj_type), lambda: None)
            self._subobj_btns.add_button(btn, subobj_type, toggle)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)

        # ******************* Selection conversion section ********************

        radio_btns = widgets["radiobutton_groups"]["sel_conversion_type"]
        radio_btns.set_selected_button("touching")
        self._radio_btns["sel_conversion_type"] = radio_btns

        btn = widgets["buttons"]["sel_conversion"]
        btn.command = self.__toggle_auto_selection_conversion
        self._btns["sel_conversion"] = btn

        # ************************* Vertex section ****************************

        checkbtn = widgets["checkbuttons"]["pick_vert_via_poly"]
        checkbtn.command = self.__handle_picking_via_poly
        self._checkbuttons["pick_vert_via_poly"] = checkbtn

        checkbtn = widgets["checkbuttons"]["pick_vert_by_aiming"]
        checkbtn.command = self.__handle_picking_by_aiming
        self._checkbuttons["pick_vert_by_aiming"] = checkbtn

        btn = widgets["buttons"]["break_verts"]
        btn.command = self.__break_vertices
        self._btns["break_verts"] = btn

        checkbtn = widgets["checkbuttons"]["vert_normal_preserve"]
        checkbtn.command = self.__handle_normal_preserve
        self._checkbuttons["vert_normal_preserve"] = checkbtn

        btn = widgets["buttons"]["smooth_verts"]
        btn.command = self.__smooth_vertices
        self._btns["smooth_verts"] = btn

        btn = widgets["buttons"]["sharpen_verts"]
        btn.command = lambda: self.__smooth_vertices(False)
        self._btns["sharpen_verts"] = btn

        # ************************* Normal section ****************************

        checkbtn = widgets["checkbuttons"]["pick_normal_via_poly"]
        checkbtn.command = self.__handle_picking_via_poly
        self._checkbuttons["pick_normal_via_poly"] = checkbtn

        checkbtn = widgets["checkbuttons"]["pick_normal_by_aiming"]
        checkbtn.command = self.__handle_picking_by_aiming
        self._checkbuttons["pick_normal_by_aiming"] = checkbtn

        prop_id = "normal_length"
        field = widgets["fields"]["unlocked_geom_normal_length"]
        field.value_id = prop_id
        field.set_input_parser(self.__parse_length_input)
        field.set_value_handler(self.__handle_value)
        field.set_value_range((.001, None), False, "float")
        field.set_step(.001)
        self._fields[prop_id] = field

        btn = widgets["buttons"]["unify_normals"]
        btn.command = self.__unify_normals
        self._btns["unify_normals"] = btn

        btn = widgets["buttons"]["separate_normals"]
        btn.command = lambda: self.__unify_normals(False)
        self._btns["separate_normals"] = btn

        btn = widgets["buttons"]["lock_normals"]
        btn.command = self.__lock_normals
        self._btns["lock_normals"] = btn

        btn = widgets["buttons"]["unlock_normals"]
        btn.command = lambda: self.__lock_normals(False)
        self._btns["unlock_normals"] = btn

        btn = widgets["buttons"]["flip_normals"]
        btn.command = self.__flip_normals
        self._btns["flip_normals"] = btn

        btn = widgets["buttons"]["copy_normal_dir"]
        btn.command = self.__copy_normal_direction
        self._btns["copy_normal_dir"] = btn

        # ************************* Edge section ******************************

        checkbtn = widgets["checkbuttons"]["pick_edge_via_poly"]
        checkbtn.command = self.__handle_picking_via_poly
        self._checkbuttons["pick_edge_via_poly"] = checkbtn

        checkbtn = widgets["checkbuttons"]["pick_edge_by_aiming"]
        checkbtn.command = self.__handle_picking_by_aiming
        self._checkbuttons["pick_edge_by_aiming"] = checkbtn

        def handler(by_border):

            GD["subobj_edit_options"]["sel_edges_by_border"] = by_border

        checkbtn = widgets["checkbuttons"]["sel_edges_by_border"]
        checkbtn.command = handler
        self._checkbuttons["sel_edges_by_border"] = checkbtn

        btn = widgets["buttons"]["split_edges"]
        btn.command = self.__split_edges
        self._btns["split_edges"] = btn

        checkbtn = widgets["checkbuttons"]["edge_normal_preserve"]
        checkbtn.command = self.__handle_normal_preserve
        self._checkbuttons["edge_normal_preserve"] = checkbtn

        btn = widgets["buttons"]["merge_edges"]
        btn.command = self.__merge_edges
        self._btns["merge_edges"] = btn

        btn = widgets["buttons"]["bridge_edges"]
        btn.command = self.__bridge_edges
        self._btns["bridge_edges"] = btn

        def handler(value_id, segments, state="done"):

            GD["subobj_edit_options"]["edge_bridge_segments"] = segments

        prop_id = "edge_bridge_segments"
        field = widgets["fields"][prop_id]
        field.value_id = prop_id
        field.value_type = "int"
        field.set_input_parser(self.__parse_edge_bridge_segs_input)
        field.set_value_handler(handler)
        field.set_value(1)
        self._fields[prop_id] = field

        btn = widgets["buttons"]["smooth_edges"]
        btn.command = self.__smooth_edges
        self._btns["smooth_edges"] = btn

        btn = widgets["buttons"]["sharpen_edges"]
        btn.command = lambda: self.__smooth_edges(False)
        self._btns["sharpen_edges"] = btn

        # ************************* Polygon section ***************************

        checkbtn = widgets["checkbuttons"]["poly_normal_preserve"]
        checkbtn.command = self.__handle_normal_preserve
        self._checkbuttons["poly_normal_preserve"] = checkbtn

        btn = widgets["buttons"]["create_poly"]
        btn.command = self.__toggle_poly_creation
        self._btns["create_poly"] = btn

        btn = widgets["buttons"]["detach_poly"]
        btn.command = self.__detach_polygons
        self._btns["detach_poly"] = btn

        btn = widgets["buttons"]["turn_diagonals"]
        btn.command = self.__turn_diagonals
        self._btns["turn_diagonals"] = btn

        def handler(by_surface):

            GD["subobj_edit_options"]["sel_polys_by_surface"] = by_surface

        checkbtn = widgets["checkbuttons"]["sel_polys_by_surface"]
        checkbtn.command = handler
        self._checkbuttons["sel_polys_by_surface"] = checkbtn

        btn = widgets["buttons"]["invert_surfaces"]
        btn.command = self.__invert_poly_surfaces
        self._btns["invert_surfaces"] = btn

        btn = widgets["buttons"]["doubleside_surfaces"]
        btn.command = self.__doubleside_poly_surfaces
        self._btns["doubleside_surfaces"] = btn

        btn = widgets["buttons"]["make_model"]
        btn.command = self.__init_surf_to_model
        self._btns["make_model"] = btn

        combobox = widgets["comboboxes"]["extrusion_vector_type"]

        vec_types = ("avg_poly_normal1", "avg_poly_normal2", "vert_normal")
        vec_type_descr = (
            "per-vertex averaged poly normal",
            "per-region averaged poly normal",
            "vertex normal"
        )

        def set_vec_type(vec_type_id, vec_type):

            combobox.select_item(vec_type)
            Mgr.update_remotely("poly_extr_inset", "extr_vec_type", vec_type_id)

        for i, (vec_type, descr) in enumerate(zip(vec_types, vec_type_descr)):
            command = lambda vt_id=i, vt=vec_type: set_vec_type(vt_id, vt)
            combobox.add_item(vec_type, descr, command)

        combobox.update_popup_menu()

        prop_id = "poly_extrusion"
        handler = lambda *args: Mgr.update_remotely("poly_extr_inset", "extrusion", args[1])
        field = widgets["fields"][prop_id]
        field.value_id = prop_id
        field.set_value_handler(handler)
        field.set_value_range(None, False, "float")
        field.set_step(.1)
        field.set_value(0.)
        self._fields[prop_id] = field

        prop_id = "poly_inset"
        handler = lambda *args: Mgr.update_remotely("poly_extr_inset", "inset", args[1])
        field = widgets["fields"][prop_id]
        field.value_id = prop_id
        field.set_value_handler(handler)
        field.set_value_range(None, False, "float")
        field.set_step(.01)
        field.set_value(0.)
        self._fields[prop_id] = field

        checkbtn = widgets["checkbuttons"]["inset_individual"]
        checkbtn.command = lambda arg: Mgr.update_remotely("poly_extr_inset", "individual", arg)
        self._checkbuttons["inset_individual"] = checkbtn

        btn = widgets["buttons"]["preview_inset"]
        btn.command = self.__preview_poly_extr_inset
        self._btns["preview_inset"] = btn

        btn = widgets["buttons"]["apply_inset"]
        btn.command = lambda: Mgr.update_remotely("poly_extr_inset", "apply")
        self._btns["apply_inset"] = btn

        def handler(by_smoothing):

            GD["subobj_edit_options"]["sel_polys_by_smoothing"] = by_smoothing

        checkbtn = widgets["checkbuttons"]["sel_polys_by_smoothing"]
        checkbtn.command = handler
        self._checkbuttons["sel_polys_by_smoothing"] = checkbtn

        btn = widgets["buttons"]["upd_poly_smoothing"]
        btn.command = self.__update_polygon_smoothing
        self._btns["upd_poly_smoothing"] = btn

        btn = widgets["buttons"]["smooth_polys"]
        btn.command = self.__smooth_polygons
        self._btns["smooth_polys"] = btn

        btn = widgets["buttons"]["unsmooth_polys"]
        btn.command = lambda: self.__smooth_polygons(False)
        self._btns["unsmooth_polys"] = btn

        btn = widgets["buttons"]["smooth_all"]
        btn.command = self.__smooth_all
        self._btns["smooth_all"] = btn

        btn = widgets["buttons"]["unsmooth_all"]
        btn.command = lambda: self.__smooth_all(False)
        self._btns["unsmooth_all"] = btn

        btn = widgets["buttons"]["smooth_with"]
        btn.command = self.__pick_poly_to_smooth_with
        self._btns["smooth_with"] = btn

        btn = widgets["buttons"]["unsmooth_with"]
        btn.command = lambda: self.__pick_poly_to_smooth_with(False)
        self._btns["unsmooth_with"] = btn

        # **************************** Geometry section ************************

        btn = widgets["buttons"]["add_geometry"]
        btn.command = self.__toggle_geometry_from_model
        self._btns["add_geometry"] = btn

        def handler(multiple):

            Mgr.update_remotely("geometry_from_model", "multiple", multiple)
            src_descr = "chosen models" if multiple else "picked model"
            tooltip_text = f"Add geometry from {src_descr} to selected models"
            self._btns["add_geometry"].tooltip_text = tooltip_text

        checkbtn = widgets["checkbuttons"]["multiple_src_models"]
        checkbtn.command = handler
        self._checkbuttons["multiple_src_models"] = checkbtn

        prop_id = "solidification_thickness"
        handler = lambda *args: Mgr.update_remotely("solidification", "thickness", args[1])
        field = widgets["fields"][prop_id]
        field.value_id = prop_id
        field.set_input_parser(self.__parse_solidification_thickness)
        field.set_value_handler(handler)
        field.set_value_range((0., None), False, "float")
        field.set_step(.1)
        field.set_value(0.)
        self._fields[prop_id] = field

        prop_id = "solidification_offset"
        handler = lambda *args: Mgr.update_remotely("solidification", "offset", args[1])
        field = widgets["fields"][prop_id]
        field.value_id = prop_id
        field.set_value_handler(handler)
        field.set_value_range(None, False, "float")
        field.set_step(.01)
        field.set_value(0.)
        self._fields[prop_id] = field

        btn = widgets["buttons"]["preview_solidification"]
        btn.command = self.__preview_solidification
        self._btns["preview_solidification"] = btn

        btn = widgets["buttons"]["apply_solidification"]
        btn.command = lambda: Mgr.update_remotely("solidification", "apply")
        self._btns["apply_solidification"] = btn

        btn = widgets["buttons"]["lock_geometry"]
        btn.command = lambda: Mgr.update_remotely("geometry_access", False)
        self._btns["lock_geometry"] = btn

        # **************************************************************************

        Mgr.add_app_updater("subobj_edit_options", self.__update_subobj_edit_options)
        Mgr.add_app_updater("poly_surface_to_model", self.__show_surf_to_model_dialog)
        Mgr.add_app_updater("geometry_from_model", self.__update_geom_from_model)

    def __update_subobj_edit_options(self):

        for option, value in GD["subobj_edit_options"].items():
            if option == "pick_via_poly":
                for subobj_type in ("vert", "edge", "normal"):
                    self._checkbuttons[f"pick_{subobj_type}_via_poly"].check(value)
            elif option == "pick_by_aiming":
                for subobj_type in ("vert", "edge", "normal"):
                    self._checkbuttons[f"pick_{subobj_type}_by_aiming"].check(value)
            elif option == "normal_preserve":
                for subobj_type in ("vert", "edge", "poly"):
                    self._checkbuttons[f"{subobj_type}_normal_preserve"].check(value)
            elif option in self._checkbuttons:
                self._checkbuttons[option].check(value)
            elif option in self._fields:
                self._fields[option].set_value(value)

    def __handle_picking_via_poly(self, via_poly):

        Mgr.update_remotely("picking_via_poly", via_poly)

        for subobj_type in ("vert", "edge", "normal"):
            self._checkbuttons[f"pick_{subobj_type}_via_poly"].check(via_poly)

    def __handle_picking_by_aiming(self, by_aiming):

        GD["subobj_edit_options"]["pick_by_aiming"] = by_aiming

        for subobj_type in ("vert", "edge", "normal"):
            self._checkbuttons[f"pick_{subobj_type}_by_aiming"].check(by_aiming)

    def __handle_normal_preserve(self, preserve):

        GD["subobj_edit_options"]["normal_preserve"] = preserve

        for subobj_type in ("vert", "edge", "poly"):
            self._checkbuttons[f"{subobj_type}_normal_preserve"].check(preserve)

    def setup(self):

        def enter_normal_dir_copy_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["copy_normal_dir"].active = True

        def exit_normal_dir_copy_mode(next_state_id, active):

            if not active:
                self._btns["copy_normal_dir"].active = False

        def enter_edge_merge_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["merge_edges"].active = True

        def exit_edge_merge_mode(next_state_id, active):

            if not active:
                self._btns["merge_edges"].active = False

        def enter_edge_bridge_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")
            self._btns["bridge_edges"].active = True

        def exit_edge_bridge_mode(next_state_id, active):

            if not active:
                self._btns["bridge_edges"].active = False

        def enter_creation_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            Mgr.do("enable_gui")
            self._btns["create_poly"].active = True

        def exit_creation_mode(next_state_id, active):

            if not active:
                self._btns["create_poly"].active = False

        def enter_diagonal_turning_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._btns["turn_diagonals"].active = True

        def exit_diagonal_turning_mode(next_state_id, active):

            if not active:
                self._btns["turn_diagonals"].active = False

        def enter_extr_inset_preview_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            self._btns["preview_inset"].active = True

        def exit_extr_inset_preview_mode(next_state_id, active):

            if not active:
                self._btns["preview_inset"].active = False

        def enter_smoothing_poly_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._btns["smooth_with"].active = True

        def exit_smoothing_poly_picking_mode(next_state_id, active):

            if not active:
                self._btns["smooth_with"].active = False

        def enter_unsmoothing_poly_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._btns["unsmooth_with"].active = True

        def exit_unsmoothing_poly_picking_mode(next_state_id, active):

            if not active:
                self._btns["unsmooth_with"].active = False

        def enter_model_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

            if not active:
                self._btns["add_geometry"].active = True
                self._checkbuttons["multiple_src_models"].enable(False)

        def exit_model_picking_mode(next_state_id, active):

            if not active:
                self._btns["add_geometry"].active = False
                self._checkbuttons["multiple_src_models"].enable()

        def enter_solidification_preview_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_create_objects")
            self._btns["preview_solidification"].active = True

        def exit_solidification_preview_mode(next_state_id, active):

            if not active:
                self._btns["preview_solidification"].active = False

        add_state = Mgr.add_state
        add_state("normal_dir_copy_mode", -10,
                  enter_normal_dir_copy_mode, exit_normal_dir_copy_mode)
        add_state("edge_merge_mode", -10,
                  enter_edge_merge_mode, exit_edge_merge_mode)
        add_state("edge_merge", -11, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))
        add_state("edge_bridge_mode", -10,
                  enter_edge_bridge_mode, exit_edge_bridge_mode)
        add_state("edge_bridge", -11, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))
        add_state("poly_creation_mode", -10,
                  enter_creation_mode, exit_creation_mode)
        add_state("poly_creation", -11, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))
        add_state("diagonal_turning_mode", -10, enter_diagonal_turning_mode,
                  exit_diagonal_turning_mode)
        add_state("poly_extr_inset_preview_mode", -10, enter_extr_inset_preview_mode,
                  exit_extr_inset_preview_mode)
        add_state("smoothing_poly_picking_mode", -10, enter_smoothing_poly_picking_mode,
                  exit_smoothing_poly_picking_mode)
        add_state("unsmoothing_poly_picking_mode", -10, enter_unsmoothing_poly_picking_mode,
                  exit_unsmoothing_poly_picking_mode)
        add_state("model_picking_mode", -10, enter_model_picking_mode,
                  exit_model_picking_mode)
        add_state("solidification_preview_mode", -10, enter_solidification_preview_mode,
                  exit_solidification_preview_mode)

        self._panel.get_section("sel_conversion").expand(False)

    def __update_object_level(self):

        if self._panel.get_active_object_type() != "unlocked_geom":
            return

        obj_lvl = GD["active_obj_level"]

        # exit any subobject modes
        Mgr.exit_states(min_persistence=-99)
        Mgr.do("update_offset_btn")

        def task():

            if obj_lvl == "top":
                self._subobj_btns.deactivate()
                Mgr.do("enable_transform_targets")
                Mgr.do("enable_selection_dialog")
                self._btns["sel_conversion"].active = False
                self._panel.get_section("sel_conversion").hide()
                if not self._panel.get_section("subobj_lvl").is_hidden():
                    self._panel.get_section("geometry").show()
            else:
                Mgr.do("disable_selection_dialog")
                Mgr.do("disable_transform_targets")
                self._subobj_btns.set_active_button(obj_lvl)
                self._panel.get_section("geometry").hide()
                self._panel.get_section(f"{obj_lvl}_props").show()
                self._panel.get_section("sel_conversion").show()

            for subobj_lvl in ("vert", "edge", "poly", "normal"):
                if subobj_lvl != obj_lvl:
                    self._panel.get_section(f"{subobj_lvl}_props").hide()

        task_id = "update_obj_level"
        PendingTasks.add(task, task_id, sort=0)

    def __set_topobj_level(self):

        GD["active_obj_level"] = "top"
        Mgr.update_app("active_obj_level")

    def __set_subobj_level(self, subobj_lvl):

        # exit any object modes
        Mgr.exit_states(min_persistence=-99)

        if GD["transform_target_type"] != "all":
            GD["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        self.__convert_selection(subobj_lvl)
        GD["active_obj_level"] = subobj_lvl
        Mgr.update_app("active_obj_level")

    def __handle_value(self, value_id, value, state="done"):

        Mgr.update_remotely(value_id, value, state)

    def __toggle_auto_selection_conversion(self):

        if self._btns["sel_conversion"].active:
            self._btns["sel_conversion"].active = False
        else:
            self._btns["sel_conversion"].active = True

    def __convert_selection(self, next_subobj_lvl):

        if self._btns["sel_conversion"].active:
            conversion_type = self._radio_btns["sel_conversion_type"].get_selected_button()
            Mgr.update_remotely("subobj_sel_conversion", next_subobj_lvl, conversion_type)
            self._btns["sel_conversion"].active = False

    def __parse_length_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __break_vertices(self):

        Mgr.update_remotely("vert_break")

    def __smooth_vertices(self, smooth=True):

        Mgr.update_remotely("vert_smoothing", smooth)

    def __unify_normals(self, unify=True):

        Mgr.update_remotely("normal_unification", unify)

    def __lock_normals(self, lock=True):

        Mgr.update_remotely("normal_lock", lock)

    def __flip_normals(self):

        Mgr.update_remotely("normal_flip")

    def __copy_normal_direction(self):

        btn = self._btns["copy_normal_dir"]

        if btn.active:
            Mgr.exit_state("normal_dir_copy_mode")
        else:
            Mgr.enter_state("normal_dir_copy_mode")

    def __split_edges(self):

        Mgr.update_remotely("edge_split")

    def __merge_edges(self):

        btn = self._btns["merge_edges"]

        if btn.active:
            Mgr.exit_state("edge_merge_mode")
        else:
            Mgr.enter_state("edge_merge_mode")

    def __parse_edge_bridge_segs_input(self, input_text):

        try:
            return max(1, abs(int(eval(input_text))))
        except:
            return None

    def __bridge_edges(self):

        btn = self._btns["bridge_edges"]

        if btn.active:
            Mgr.exit_state("edge_bridge_mode")
        else:
            Mgr.enter_state("edge_bridge_mode")

    def __smooth_edges(self, smooth=True):

        Mgr.update_remotely("edge_smoothing", smooth)

    def __toggle_poly_creation(self):

        if self._btns["create_poly"].active:
            Mgr.exit_state("poly_creation_mode")
        else:
            Mgr.enter_state("poly_creation_mode")

    def __detach_polygons(self):

        Mgr.update_remotely("poly_detach")

    def __turn_diagonals(self):

        pick_btn = self._btns["turn_diagonals"]

        if pick_btn.active:
            Mgr.exit_state("diagonal_turning_mode")
        else:
            Mgr.update_remotely("diagonal_turn")

    def __invert_poly_surfaces(self):

        Mgr.update_remotely("poly_surface_inversion")

    def __doubleside_poly_surfaces(self):

        Mgr.update_remotely("poly_surface_doublesiding")

    def __init_surf_to_model(self):

        Mgr.update_remotely("poly_surface_to_model", "init")

    def __show_surf_to_model_dialog(self):

        SurfaceToModelDialog()

    def __preview_poly_extr_inset(self):

        preview_btn = self._btns["preview_inset"]

        if preview_btn.active:
            Mgr.exit_state("poly_extr_inset_preview_mode")
        else:
            Mgr.update_remotely("poly_extr_inset", "preview")

    def __update_polygon_smoothing(self):

        Mgr.update_remotely("poly_smoothing_update")

    def __smooth_polygons(self, smooth=True):

        Mgr.update_remotely("poly_smoothing", smooth)

    def __smooth_all(self, smooth=True):

        Mgr.update_remotely("model_smoothing", smooth)

    def __pick_poly_to_smooth_with(self, smooth=True):

        pick_btn = self._btns[("" if smooth else "un") + "smooth_with"]
        state_id = ("" if smooth else "un") + "smoothing_poly_picking_mode"

        if pick_btn.active:
            Mgr.exit_state(state_id)
        else:
            Mgr.enter_state(state_id)

    def __toggle_geometry_from_model(self):

        btn = self._btns["add_geometry"]

        if btn.active:
            Mgr.exit_state("model_picking_mode")
        else:
            Mgr.update_remotely("geometry_from_model", "init")

    def __update_geom_from_model(self, update_type, *args):

        if update_type == "options":
            GeometryFromModelDialog(*args)
        elif update_type == "invalid_src":
            MessageDialog(title="Invalid geometry source",
                          message="No suitable models chosen to add geometry from.\n\n"
                                  "Source models must contain unlocked geometry.\n"
                                  "Also, at least one model in the current selection may not\n"
                                  "be chosen as source model.",
                          choices="ok",
                          icon_id="icon_exclamation")

    def __preview_solidification(self):

        preview_btn = self._btns["preview_solidification"]

        if preview_btn.active:
            Mgr.exit_state("solidification_preview_mode")
        else:
            Mgr.update_remotely("solidification", "preview")

    def __parse_solidification_thickness(self, input_text):

        try:
            return max(0., float(eval(input_text)))
        except:
            return None

    def get_base_type(self):

        return "unlocked_geom"

    def get_section_ids(self):

        return ["geometry", "subobj_lvl"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        field = self._fields[prop_id]
        field.show_text()
        field.set_value(value)
        field.set_text_color(Skin.colors["default_value"])

    def set_object_property(self, prop_id, value):

        if prop_id not in self._fields or type(value) is not tuple:
            return

        field = self._fields[prop_id]
        val, sel_count = value

        if sel_count == 1:
            field.set_value(val)
            field.set_text_color()
            field.show_text()
        else:
            field.set_text_color(Skin.text["input_disabled"]["color"])
            field.show_text(False)

    def check_selection_count(self):

        return  # there's currently no property handling affected by selection size

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = Skin.text["input_disabled"]["color"] if multi_sel else None

        for prop_id, field in self._fields.items():
            if prop_id not in ("normal_length", "edge_bridge_segments",
                    "poly_extrusion", "poly_inset", "solidification_thickness",
                    "solidification_offset"):
                field.set_text_color(color)
                field.show_text(not multi_sel)


PropertyPanel.add_properties("unlocked_geom", UnlockedGeomProperties)

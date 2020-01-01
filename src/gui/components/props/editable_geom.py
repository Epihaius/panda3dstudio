from .base import *


class SurfaceToModelDialog(Dialog):

    def __init__(self):

        title = "Create models from surfaces"

        Dialog.__init__(self, title, choices="okcancel", on_yes=self.__on_yes)

        self._model_basename = ""
        self._creation_method = "per_src"
        self._copy_surfaces = False

        client_sizer = self.get_client_sizer()

        subsizer = Sizer("horizontal")
        borders = (50, 50, 0, 20)
        client_sizer.add(subsizer, expand=True, borders=borders)

        text = DialogText(self, "Model basename:")
        borders = (0, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)
        field = DialogInputField(self, "name", "string", self.__handle_name, 200)
        field.set_input_parser(self.__parse_input)
        subsizer.add(field, proportion=1., alignment="center_v")

        text = DialogText(self, "Leave field empty to base name(s) on source model name(s).")
        borders = (50, 50, 0, 5)
        client_sizer.add(text, borders=borders)

        group = DialogWidgetGroup(self, "Creation method")
        borders = (50, 50, 0, 20)
        client_sizer.add(group, expand=True, borders=borders)

        radio_btns = DialogRadioButtonGroup(group, columns=1, gap_v=5)

        def get_command(method_id):

            def command():

                self._creation_method = method_id

            return command

        method_ids = ("per_src", "per_surface", "single")
        method_names = ("One model per source model", "One model per surface", "Single model")

        for method_id, method_name in zip(method_ids, method_names):
            radio_btns.add_button(method_id, method_name)
            radio_btns.set_button_command(method_id, get_command(method_id))

        radio_btns.set_selected_button("per_src")
        group.add(radio_btns.sizer)

        text = "Copy surfaces"
        checkbtn = DialogCheckButton(self, self.__copy_surfaces, text)
        borders = (50, 50, 20, 15)
        client_sizer.add(checkbtn, borders=borders)

        self.finalize()

    def __parse_input(self, input_text):

        self._input = input_text.strip()

        return self._input

    def __handle_name(self, value_id, name, state):

        self._model_basename = name

    def __copy_surfaces(self, copy_surfaces):

        self._copy_surfaces = copy_surfaces

    def __on_yes(self):

        Mgr.update_remotely("poly_surface_to_model", "create", self._model_basename,
                            self._creation_method, self._copy_surfaces)


class GeometryFromModelDialog(Dialog):

    def __init__(self, model_name=None):

        if model_name is None:
            title = 'Add geometry from other models'
        else:
            title = f'Add geometry from "{model_name}"'

        Dialog.__init__(self, title, choices="okcancel", on_yes=self.__on_yes)

        self._delete_src_geometry = True
        self._keep_src_models = False

        client_sizer = self.get_client_sizer()

        text = "Delete source geometry"
        checkbtn = DialogCheckButton(self, self.__delete_src_geometry, text)
        checkbtn.check()
        borders = (50, 50, 0, 20)
        client_sizer.add(checkbtn, borders=borders)

        text = "Keep empty source model"

        if model_name is None:
            text += "s"

        checkbtn = DialogCheckButton(self, self.__keep_src_models, text)
        borders = (70, 50, 20, 0)
        client_sizer.add(checkbtn, borders=borders)

        self.finalize()

    def __delete_src_geometry(self, delete_src_geometry):

        self._delete_src_geometry = delete_src_geometry

    def __keep_src_models(self, keep_src_models):

        self._keep_src_models = keep_src_models

    def __on_yes(self):

        Mgr.update_remotely("geometry_from_model", "add",
            self._delete_src_geometry, self._keep_src_models)


class EditableGeomProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._btns = {}
        self._checkbuttons = {}
        self._radio_btns = {}
        self._subobj_btns = ToggleButtonGroup()
        toggle = (self.__set_topobj_level, lambda: None)
        self._subobj_btns.set_default_toggle("top", toggle)

        # ************************* Subobject level section *******************

        section = panel.add_section("subobj_lvl", "Subobject level", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        section.add(sizer, expand=True)

        subobj_types = ("vert", "normal", "edge", "poly")
        subobj_names = ("Vertex", "Normal", "Edge", "Polygon")
        get_level_setter = lambda subobj_type: lambda: self.__set_subobj_level(subobj_type)

        for subobj_type, subobj_name in zip(subobj_types, subobj_names):
            tooltip_text = f"{subobj_name} level"
            btn = PanelButton(section, subobj_name, "", tooltip_text)
            sizer.add(btn, proportion_h=1.)
            toggle = (get_level_setter(subobj_type), lambda: None)
            self._subobj_btns.add_button(btn, subobj_type, toggle)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)

        # ******************* Selection conversion section ********************

        section = panel.add_section("sel_conversion", "Selection conversion", hidden=True)

        group = section.add_group("Conversion type:")

        radio_btns = PanelRadioButtonGroup(group, columns=2, gap_h=10, gap_v=5)
        btn_ids = texts = ("touching", "containing", "bordering")

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)

        radio_btns.set_selected_button("touching")
        self._radio_btns["sel_conversion_type"] = radio_btns
        group.add(radio_btns.sizer)

        section.add((0, 10))

        text = "Auto-convert selection"
        tooltip_text = "Convert sel. when switching to other subobj. level"
        btn = PanelButton(section, text, "", tooltip_text)
        btn.command = self.__toggle_auto_selection_conversion
        self._btns["sel_conversion"] = btn
        section.add(btn, alignment="center_h")

        # ************************* Vertex section ****************************

        section = panel.add_section("vert_props", "Vertices", hidden=True)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Pick via polygon"
        checkbtn = PanelCheckButton(section, self.__handle_picking_via_poly, text)
        self._checkbuttons["pick_vert_via_poly"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((5, 0), proportion=1.)
        text = "aim"
        checkbtn = PanelCheckButton(section, self.__handle_picking_by_aiming, text)
        self._checkbuttons["pick_vert_by_aiming"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Break"
        tooltip_text = "Break selected vertices"
        btn = PanelButton(section, text, "", tooltip_text, self.__break_vertices)
        self._btns["break_verts"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        text = "Lock normals"
        checkbtn = PanelCheckButton(section, self.__handle_normal_preserve, text)
        self._checkbuttons["vert_normal_preserve"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        section.add((0, 5))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        borders = (0, 5, 0, 0)

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

        text = "Pick via polygon"
        checkbtn = PanelCheckButton(section, self.__handle_picking_via_poly, text)
        self._checkbuttons["pick_normal_via_poly"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((5, 0), proportion=1.)
        text = "aim"
        checkbtn = PanelCheckButton(section, self.__handle_picking_by_aiming, text)
        self._checkbuttons["pick_normal_by_aiming"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        section.add(sizer)

        text = "Length:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        prop_id = "normal_length"
        field = PanelSpinnerField(section, prop_id, "float", (.001, None), .001,
                                  self.__handle_value, 80)
        field.set_input_parser(self.__parse_length_input)
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

        text = "Pick via polygon"
        checkbtn = PanelCheckButton(section, self.__handle_picking_via_poly, text)
        self._checkbuttons["pick_edge_via_poly"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((5, 0), proportion=1.)
        text = "aim"
        checkbtn = PanelCheckButton(section, self.__handle_picking_by_aiming, text)
        self._checkbuttons["pick_edge_by_aiming"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        def handler(by_border):

            GD["subobj_edit_options"]["sel_edges_by_border"] = by_border

        text = "Select by border"
        checkbtn = PanelCheckButton(section, handler, text)
        self._checkbuttons["sel_edges_by_border"] = checkbtn
        section.add(checkbtn)

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Split"
        tooltip_text = "Split selected edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__split_edges)
        self._btns["split_edges"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        text = "Lock normals"
        checkbtn = PanelCheckButton(section, self.__handle_normal_preserve, text)
        self._checkbuttons["edge_normal_preserve"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
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

        def handler(value_id, segments, state="done"):

            GD["subobj_edit_options"]["edge_bridge_segments"] = segments

        text = "Bridge segments:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        prop_id = "edge_bridge_segments"
        field = PanelInputField(section, prop_id, "int", handler, 40)
        field.set_input_parser(self.__parse_edge_bridge_segs_input)
        field.set_value(1)
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

        text = "Auto-lock border normals"
        checkbtn = PanelCheckButton(section, self.__handle_normal_preserve, text)
        self._checkbuttons["poly_normal_preserve"] = checkbtn
        section.add(checkbtn)

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Create..."
        tooltip_text = "Create single polygon"
        btn = PanelButton(section, text, "", tooltip_text, self.__toggle_poly_creation)
        self._btns["create_poly"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        text = "Detach"
        tooltip_text = "Detach selected polygons"
        btn = PanelButton(section, text, "", tooltip_text, self.__detach_polygons)
        self._btns["detach_poly"] = btn
        sizer.add(btn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        section.add((0, 5))

        text = "Turn diagonals..."
        tooltip_text = "Turn any diagonals of a selected polygon"
        btn = PanelButton(section, text, "", tooltip_text, self.__turn_diagonals)
        self._btns["turn_diagonals"] = btn
        section.add(btn)

        group = section.add_group("Contiguous surfaces")

        def handler(by_surface):

            GD["subobj_edit_options"]["sel_polys_by_surface"] = by_surface

        text = "Select by surface"
        checkbtn = PanelCheckButton(group, handler, text)
        self._checkbuttons["sel_polys_by_surface"] = checkbtn
        group.add(checkbtn)

        group.add((0, 6))

        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "Invert"
        tooltip_text = "Invert surfaces containing selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__invert_poly_surfaces)
        self._btns["invert_surfaces"] = btn
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        text = "Doubleside"
        tooltip_text = "Doubleside surfaces containing selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__doubleside_poly_surfaces)
        self._btns["invert_surfaces"] = btn
        sizer.add(btn)

        sizer.add((0, 0), proportion=1.)

        group.add((0, 5))

        text = "To new model(s)..."
        tooltip_text = "Create new model(s) out of surfaces containing selected polygons"
        btn = PanelButton(group, text, "", tooltip_text, self.__init_surf_to_model)
        self._btns["make_model"] = btn
        group.add(btn)

        group = section.add_group("Extrusion/inset")

        text = "Extrusion vector type:"
        borders = (0, 0, 5, 0)
        group.add(PanelText(group, text), borders=borders)

        combobox = PanelComboBox(group, 100, tooltip_text="Extrusion vector type")
        group.add(combobox, expand=True, borders=borders)

        vec_types = ("avg_poly_normal1", "avg_poly_normal2", "vert_normal")
        vec_type_descr = (
            "per-vertex averaged poly normal",
            "per-region averaged poly normal",
            "vertex normal"
        )

        def get_command(vec_type_id, vec_type):

            def set_vec_type():

                combobox.select_item(vec_type)
                Mgr.update_remotely("poly_extr_inset", "extr_vec_type", vec_type_id)

            return set_vec_type

        for i, (vec_type, descr) in enumerate(zip(vec_types, vec_type_descr)):
            combobox.add_item(vec_type, descr, get_command(i, vec_type))

        combobox.update_popup_menu()

        subsizer = GridSizer(columns=2, gap_h=5)
        subsizer.set_column_proportion(1, 1.)
        group.add(subsizer, expand=True)

        borders = (0, 5, 0, 0)

        prop_id = "poly_extrusion"
        text = "Extrusion:"
        subsizer.add(PanelText(group, text), alignment_v="center_v", borders=borders)
        handler = lambda *args: Mgr.update_remotely("poly_extr_inset", "extrusion", args[1])
        field = PanelSpinnerField(group, prop_id, "float", None, .1, handler, 80)
        field.set_value(0.)
        self._fields[prop_id] = field
        subsizer.add(field, expand_h=True, alignment_v="center_v")

        prop_id = "poly_inset"
        text = "Inset:"
        subsizer.add(PanelText(group, text), alignment_v="center_v", borders=borders)
        handler = lambda *args: Mgr.update_remotely("poly_extr_inset", "inset", args[1])
        field = PanelSpinnerField(group, prop_id, "float", None, .01, handler, 80)
        field.set_value(0.)
        self._fields[prop_id] = field
        subsizer.add(field, expand_h=True, alignment_v="center_v")

        borders = (0, 0, 0, 5)

        text = "Individual polygons"
        command = lambda arg: Mgr.update_remotely("poly_extr_inset", "individual", arg)
        checkbtn = PanelCheckButton(group, command, text)
        self._checkbuttons["inset_individual"] = checkbtn
        group.add(checkbtn, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True, borders=borders)

        tooltip_text = "Preview extrusion and inset"
        btn = PanelButton(group, "Preview", "", tooltip_text)
        btn.command = self.__preview_poly_extr_inset
        self._btns["preview_inset"] = btn
        subsizer.add(btn, proportion=1.)

        subsizer.add((10, 0))

        tooltip_text = "Extrude/inset selected polygons"
        btn = PanelButton(group, "Apply", "", tooltip_text)
        btn.command = lambda: Mgr.update_remotely("poly_extr_inset", "apply")
        self._btns["apply_inset"] = btn
        subsizer.add(btn, proportion=1.)

        group = section.add_group("Polygon smoothing")

        def handler(by_smoothing):

            GD["subobj_edit_options"]["sel_polys_by_smoothing"] = by_smoothing

        text = "Select by smoothing"
        checkbtn = PanelCheckButton(group, handler, text)
        self._checkbuttons["sel_polys_by_smoothing"] = checkbtn
        group.add(checkbtn)

        group.add((0, 6))

        text = "Update"
        tooltip_text = "Update polygon smoothing"
        btn = PanelButton(group, text, "", tooltip_text, self.__update_polygon_smoothing)
        self._btns["upd_poly_smoothing"] = btn
        group.add(btn, alignment="center_h")

        group.add((0, 10))

        borders = (0, 5, 0, 0)

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

        # **************************** Geometry section ************************

        section = panel.add_section("geometry", "Geometry", hidden=True)

        subsizer = Sizer("horizontal")
        section.add(subsizer, expand=True)

        text = "Add from..."
        tooltip_text = "Add geometry from picked model to selected models"
        btn = PanelButton(section, text, "", tooltip_text)
        btn.command = self.__toggle_geometry_from_model
        self._btns["add_geometry"] = btn
        subsizer.add(btn, alignment="center_v")

        borders = (5, 0, 0, 0)

        def handler(multiple):

            Mgr.update_remotely("geometry_from_model", "multiple", multiple)
            src_descr = "chosen models" if multiple else "picked model"
            tooltip_text = f"Add geometry from {src_descr} to selected models"
            self._btns["add_geometry"].set_tooltip_text(tooltip_text)

        text = "multiple"
        checkbtn = PanelCheckButton(section, handler, text)
        self._checkbuttons["multiple_src_models"] = checkbtn
        subsizer.add(checkbtn, alignment="center_v", borders=borders)

        group = section.add_group("Solidification")

        subsizer = GridSizer(columns=2, gap_h=5)
        subsizer.set_column_proportion(1, 1.)
        group.add(subsizer, expand=True)

        prop_id = "solidification_thickness"
        text = "Thickness:"
        subsizer.add(PanelText(group, text), alignment_v="center_v", borders=borders)
        handler = lambda *args: Mgr.update_remotely("solidification", "thickness", args[1])
        field = PanelSpinnerField(group, prop_id, "float", (0., None), .1, handler, 80)
        field.set_input_parser(self.__parse_solidification_thickness)
        field.set_value(0.)
        self._fields[prop_id] = field
        subsizer.add(field, expand_h=True, alignment_v="center_v")

        prop_id = "solidification_offset"
        text = "Offset:"
        subsizer.add(PanelText(group, text), alignment_v="center_v", borders=borders)
        handler = lambda *args: Mgr.update_remotely("solidification", "offset", args[1])
        field = PanelSpinnerField(group, prop_id, "float", None, .01, handler, 80)
        field.set_value(0.)
        self._fields[prop_id] = field
        subsizer.add(field, expand_h=True, alignment_v="center_v")

        borders = (0, 0, 0, 5)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True, borders=borders)

        tooltip_text = "Preview solidification of model surface"
        btn = PanelButton(group, "Preview", "", tooltip_text)
        btn.command = self.__preview_solidification
        self._btns["preview_solidification"] = btn
        subsizer.add(btn, proportion=1.)

        subsizer.add((10, 0))

        tooltip_text = "Solidify model surface"
        btn = PanelButton(group, "Apply", "", tooltip_text)
        btn.command = lambda: Mgr.update_remotely("solidification", "apply")
        self._btns["apply_solidification"] = btn
        subsizer.add(btn, proportion=1.)

        tooltip_text = "Disable geometry editing"
        btn = PanelButton(section, "Lock", "", tooltip_text)
        btn.command = lambda: Mgr.update_remotely("geometry_access", False)
        self._btns["lock_geometry"] = btn
        borders = (0, 0, 0, 10)
        section.add(btn, alignment="center_h", borders=borders)

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

        if self._panel.get_active_object_type() != "editable_geom":
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

        return "editable_geom"

    def get_section_ids(self):

        return ["geometry", "subobj_lvl"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        field = self._fields[prop_id]
        field.show_text()
        field.set_value(value)
        field.set_text_color((1., 1., 0., 1.))

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
            field.set_text_color((.5, .5, .5, 1.))
            field.show_text(False)

    def check_selection_count(self):

        return  # there's currently no property handling affected by selection size

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        for prop_id, field in self._fields.items():
            if prop_id not in ("normal_length", "edge_bridge_segments",
                    "poly_extrusion", "poly_inset", "solidification_thickness",
                    "solidification_offset"):
                field.set_text_color(color)
                field.show_text(not multi_sel)


PropertyPanel.add_properties("editable_geom", EditableGeomProperties)

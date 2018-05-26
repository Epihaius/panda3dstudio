from ...base import *
from ...button import *
from ...panel import *


class SubobjectPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "subobj", "Subobject level")

        self._btns = {}
        self._comboboxes = {}
        self._checkboxes = {}
        self._colorboxes = {}
        self._fields = {}
        self._radio_btns = {}
        self._uv_lvl_btns = uv_lvl_btns = ToggleButtonGroup()
        self._prev_obj_lvl = "poly"
        self._subobj_state_ids = {"vert": [], "edge": [], "poly": []}

        top_container = self.get_top_container()

        btn_sizer = Sizer("horizontal")
        borders = (5, 5, 10, 5)
        top_container.add(btn_sizer, expand=True, borders=borders)

        get_command = lambda subobj_type: lambda: self.__set_subobj_level(subobj_type)
        subobj_types = ("vert", "edge", "poly")
        subobj_text = ("Vertex", "Edge", "Polygon")
        btns = []

        for subobj_type, text in zip(subobj_types, subobj_text):
            tooltip_text = "{} level".format(text)
            btn = PanelButton(top_container, text, "", tooltip_text)
            toggle = (get_command(subobj_type), lambda: None)
            uv_lvl_btns.add_button(btn, subobj_type, toggle)
            btns.append(btn)

        btn_sizer.add(btns[0], proportion=1.)
        btn_sizer.add((5, 0))
        btn_sizer.add(btns[1], proportion=1.)
        btn_sizer.add((5, 0))
        btn_sizer.add(btns[2], proportion=1.)

        uv_lvl_btns.set_active_button("poly")

        # ************************* Vertex section ****************************

        section = self.add_section("uv_vert_props", "Vertices")

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

        section.add((0, 10))

        text = "Break"
        tooltip_text = "Break selected vertices"
        btn = PanelButton(section, text, "", tooltip_text, self.__break_vertices)
        self._btns["break_verts"] = btn
        section.add(btn)

        # ************************* Edge section ******************************

        section = self.add_section("uv_edge_props", "Edges")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        checkbox = PanelCheckBox(section, self.__handle_picking_via_poly)
        checkbox.check(False)
        self._checkboxes["pick_edge_via_poly"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Pick via polygon"
        sizer.add(PanelText(section, text), alignment="center_v")
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

        def handler(by_seam):

            GlobalData["uv_edit_options"]["sel_edges_by_seam"] = by_seam

        checkbox = PanelCheckBox(section, handler)
        checkbox.check(False)
        self._checkboxes["sel_edges_by_seam"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Select by seam"
        sizer.add(PanelText(section, text), alignment="center_v")

        section.add((0, 10))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Split"
        tooltip_text = "Split selected edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__split_edges)
        self._btns["split_edges"] = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        text = "Stitch"
        tooltip_text = "Stitch selected seam edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__stitch_edges)
        self._btns["stitch_edges"] = btn
        btn_sizer.add(btn, proportion=1.)

        # ************************* Polygon section ***************************

        section = self.add_section("uv_poly_props", "Polygons")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        def handler(by_cluster):

            GlobalData["uv_edit_options"]["sel_polys_by_cluster"] = by_cluster

        checkbox = PanelCheckBox(section, handler)
        checkbox.check(False)
        self._checkboxes["sel_polys_by_cluster"] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Select by cluster"
        sizer.add(PanelText(section, text), alignment="center_v")

        section.add((0, 10))

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Detach"
        tooltip_text = "Detach selected polygons"
        btn = PanelButton(section, text, "", tooltip_text, self.__detach_polygons)
        self._btns["detach_polys"] = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        text = "Stitch"
        tooltip_text = "Stitch selected polygon seam edges"
        btn = PanelButton(section, text, "", tooltip_text, self.__stitch_polygons)
        self._btns["stitch_polys"] = btn
        btn_sizer.add(btn, proportion=1.)

        section.add((0, 5))

        group = section.add_group("Color")

        text = "Unselected"
        group.add(PanelText(group, text))

        group.add((0, 6))

        sizer = Sizer("horizontal")
        group.add(sizer)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        dialog_title = "Pick unselected polygon color"
        command = lambda col: self.__handle_poly_rgb("unselected", col)
        colorbox = PanelColorBox(group, command, dialog_title=dialog_title)
        self._colorboxes["unselected_poly_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")
        sizer.add((5, 0))
        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        field = PanelInputField(group, 50)
        val_id = "unselected_poly_alpha"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_alpha)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        group.add((0, 10))

        text = "Selected"
        group.add(PanelText(group, text))

        group.add((0, 6))

        sizer = Sizer("horizontal")
        group.add(sizer)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        dialog_title = "Pick selected polygon color"
        command = lambda col: self.__handle_poly_rgb("selected", col)
        colorbox = PanelColorBox(group, command, dialog_title=dialog_title)
        self._colorboxes["selected_poly_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")
        sizer.add((5, 0))
        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        field = PanelInputField(group, 50)
        val_id = "selected_poly_alpha"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_alpha)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

    def setup(self):

        self._uv_lvl_btns.set_active_button("poly")
        self.get_section("uv_poly_props").show()
        self.get_section("uv_vert_props").hide()
        self.get_section("uv_edge_props").hide()

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_level", self.__set_uv_level, interface_id="uv")
        Mgr.add_app_updater("poly_color", self.__set_poly_color, interface_id="uv")
        Mgr.add_app_updater("uv_edit_options", self.__update_uv_edit_options, interface_id="uv")

    def __update_uv_edit_options(self):

        for option, value in GlobalData["uv_edit_options"].iteritems():
            if option == "pick_via_poly":
                for subobj_type in ("vert", "edge"):
                    self._checkboxes["pick_{}_via_poly".format(subobj_type)].check(value)
            elif option == "pick_by_aiming":
                for subobj_type in ("vert", "edge"):
                    self._checkboxes["pick_{}_by_aiming".format(subobj_type)].check(value)
            elif option in self._checkboxes:
                self._checkboxes[option].check(value)
            elif option in self._fields:
                self._fields[option].set_value(option, value, handle_value=False)

    def __set_uv_level(self, uv_level):

        self._uv_lvl_btns.set_active_button(uv_level)
        self.get_section("uv_{}_props".format(uv_level)).show()

        for subobj_lvl in ("vert", "edge", "poly"):
            if subobj_lvl != uv_level:
                self.get_section("uv_{}_props".format(subobj_lvl)).hide()

        for state_id in self._subobj_state_ids[self._prev_obj_lvl]:
            Mgr.exit_state(state_id)

        self._prev_obj_lvl = uv_level

    def __set_subobj_level(self, uv_level):

        Mgr.update_interface("uv", "uv_level", uv_level)

    def __handle_picking_via_poly(self, via_poly):

        Mgr.update_interface_remotely("uv", "picking_via_poly", via_poly)

        for subobj_type in ("vert", "edge"):
            self._checkboxes["pick_{}_via_poly".format(subobj_type)].check(via_poly)

    def __handle_picking_by_aiming(self, by_aiming):

        GlobalData["uv_edit_options"]["pick_by_aiming"] = by_aiming
        GlobalData["subobj_edit_options"]["pick_by_aiming"] = by_aiming

        for subobj_type in ("vert", "edge"):
            self._checkboxes["pick_{}_by_aiming".format(subobj_type)].check(by_aiming)

    def __break_vertices(self):

        Mgr.update_interface_remotely("uv", "vert_break")

    def __split_edges(self):

        Mgr.update_interface_remotely("uv", "edge_split")

    def __stitch_edges(self):

        Mgr.update_interface_remotely("uv", "edge_stitch")

    def __detach_polygons(self):

        Mgr.update_interface_remotely("uv", "poly_detach")

    def __stitch_polygons(self):

        Mgr.update_interface_remotely("uv", "poly_stitch")

    def __handle_poly_rgb(self, sel_state, color):

        r, g, b = color
        Mgr.update_interface_remotely("uv", "poly_color", sel_state, "rgb", (r, g, b, 1.))

    def __parse_alpha(self, alpha):

        try:
            return min(1., max(0., float(eval(alpha))))
        except:
            return None

    def __handle_value(self, value_id, value):

        sel_state = value_id.replace("_poly_alpha", "")
        Mgr.update_interface_remotely("uv", "poly_color", sel_state, "alpha", value)

    def __set_poly_color(self, sel_state, channels, value):

        if channels == "rgb":
            self._colorboxes["{}_poly_rgb".format(sel_state)].set_color(value[:3])
        elif channels == "alpha":
            prop_id = "{}_poly_alpha".format(sel_state)
            self._fields[prop_id].set_value(prop_id, value, handle_value=False)

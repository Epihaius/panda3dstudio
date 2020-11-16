from ...base import *
from ...button import *
from ...panel import *


class SubobjectPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "subobj")

        widgets = Skin.layout.create(self, "subobj")
        self._btns = btns = widgets["buttons"]
        self._checkbuttons = checkbuttons = widgets["checkbuttons"]
        self._colorboxes = colorboxes = widgets["colorboxes"]
        self._fields = fields = widgets["fields"]
        self._uv_lvl_btns = uv_lvl_btns = ToggleButtonGroup()

        self._prev_obj_lvl = ""
        self._subobj_state_ids = {"vert": [], "edge": [], "poly": [], "part": []}

        subobj_types = ("vert", "edge", "poly", "part")

        for subobj_type in subobj_types:
            btn = btns[subobj_type]
            command = lambda s=subobj_type: self.__set_subobj_level(s)
            toggle = (command, lambda: None)
            uv_lvl_btns.add_button(btn, subobj_type, toggle)

        # ************************* Vertex section ****************************

        checkbtn = checkbuttons["pick_vert_via_poly"]
        checkbtn.command = self.__handle_picking_via_poly

        checkbtn = checkbuttons["pick_vert_by_aiming"]
        checkbtn.command = self.__handle_picking_by_aiming

        btn = btns["break_verts"]
        btn.command = self.__break_vertices

        # ************************* Edge section ******************************

        checkbtn = checkbuttons["pick_edge_via_poly"]
        checkbtn.command = self.__handle_picking_via_poly

        checkbtn = checkbuttons["pick_edge_by_aiming"]
        checkbtn.command = self.__handle_picking_by_aiming

        def handler(by_seam):

            GD["uv_edit_options"]["sel_edges_by_seam"] = by_seam

        checkbtn = checkbuttons["sel_edges_by_seam"]
        checkbtn.command = handler

        btn = btns["split_edges"]
        btn.command = self.__split_edges

        btn = btns["stitch_edges"]
        btn.command = self.__stitch_edges

        # ************************* Polygon section ***************************

        def handler(by_cluster):

            GD["uv_edit_options"]["sel_polys_by_cluster"] = by_cluster

        checkbtn = checkbuttons["sel_polys_by_cluster"]
        checkbtn.command = handler

        btn = btns["detach_polys"]
        btn.command = self.__detach_polygons

        btn = btns["stitch_polys"]
        btn.command = self.__stitch_polygons

        colorbox = colorboxes["unselected_poly_rgb"]
        colorbox.command = lambda col: self.__handle_poly_rgb("unselected", col)
        colorbox.dialog_title = "Pick unselected polygon color"

        val_id = "unselected_poly_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_poly_value)
        field.set_value_range((0., 1.), False, "float")

        colorbox = colorboxes["selected_poly_rgb"]
        colorbox.command = lambda col: self.__handle_poly_rgb("selected", col)
        colorbox.dialog_title = "Pick selected polygon color"

        val_id = "selected_poly_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_poly_value)
        field.set_value_range((0., 1.), False, "float")

        # ********************* Primitive part section ***********************

        btn = btns["reset_part_uvs"]
        btn.command = self.__reset_default_part_uvs

        colorbox = colorboxes["unselected_part_rgb"]
        colorbox.command = lambda col: self.__handle_part_rgb("unselected", col)
        colorbox.dialog_title = "Pick unselected primitive part color"

        val_id = "unselected_part_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_part_value)
        field.set_value_range((0., 1.), False, "float")

        colorbox = colorboxes["selected_part_rgb"]
        colorbox.command = lambda col: self.__handle_part_rgb("selected", col)
        colorbox.dialog_title = "Pick selected primitive part color"

        val_id = "selected_part_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_part_value)
        field.set_value_range((0., 1.), False, "float")

    def setup(self):

        for subobj_lvl in ("vert", "edge", "poly", "part"):
            self.get_section(f"uv_{subobj_lvl}_props").hide()

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_level", self.__set_uv_level, interface_id="uv")
        Mgr.add_app_updater("poly_color", self.__set_poly_color, interface_id="uv")
        Mgr.add_app_updater("part_color", self.__set_part_color, interface_id="uv")
        Mgr.add_app_updater("uv_edit_options", self.__update_uv_edit_options, interface_id="uv")

    def __update_uv_edit_options(self):

        for option, value in GD["uv_edit_options"].items():
            if option == "pick_via_poly":
                for subobj_type in ("vert", "edge"):
                    self._checkbuttons[f"pick_{subobj_type}_via_poly"].check(value)
            elif option == "pick_by_aiming":
                for subobj_type in ("vert", "edge"):
                    self._checkbuttons[f"pick_{subobj_type}_by_aiming"].check(value)
            elif option in self._checkbuttons:
                self._checkbuttons[option].check(value)
            elif option in self._fields:
                self._fields[option].set_value(value)

    def __set_uv_level(self, uv_level):

        self._uv_lvl_btns.set_active_button(uv_level)
        self.get_section(f"uv_{uv_level}_props").show()

        for subobj_lvl in ("vert", "edge", "poly", "part"):
            if subobj_lvl != uv_level:
                self.get_section(f"uv_{subobj_lvl}_props").hide()

        for state_id in self._subobj_state_ids.get(self._prev_obj_lvl, []):
            Mgr.exit_state(state_id)

        self._prev_obj_lvl = uv_level

    def __set_subobj_level(self, uv_level):

        Mgr.update_interface("uv", "uv_level", uv_level)

    def __handle_picking_via_poly(self, via_poly):

        Mgr.update_interface_remotely("uv", "picking_via_poly", via_poly)

        for subobj_type in ("vert", "edge"):
            self._checkbuttons[f"pick_{subobj_type}_via_poly"].check(via_poly)

    def __handle_picking_by_aiming(self, by_aiming):

        GD["uv_edit_options"]["pick_by_aiming"] = by_aiming
        GD["subobj_edit_options"]["pick_by_aiming"] = by_aiming

        for subobj_type in ("vert", "edge"):
            self._checkbuttons[f"pick_{subobj_type}_by_aiming"].check(by_aiming)

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

    def __reset_default_part_uvs(self):

        Mgr.update_interface_remotely("uv", "part_uv_defaults_reset")

    def __handle_poly_rgb(self, sel_state, color):

        r, g, b = color
        Mgr.update_interface_remotely("uv", "poly_color", sel_state, "rgb", (r, g, b, 1.))

    def __handle_poly_value(self, value_id, value, state="done"):

        sel_state = value_id.replace("_poly_alpha", "")
        Mgr.update_interface_remotely("uv", "poly_color", sel_state, "alpha", value)

    def __set_poly_color(self, sel_state, channels, value):

        if channels == "rgb":
            self._colorboxes[f"{sel_state}_poly_rgb"].color = value[:3]
        elif channels == "alpha":
            prop_id = f"{sel_state}_poly_alpha"
            self._fields[prop_id].set_value(value)

    def __handle_part_rgb(self, sel_state, color):

        r, g, b = color
        Mgr.update_interface_remotely("uv", "part_color", sel_state, "rgb", (r, g, b, 1.))

    def __handle_part_value(self, value_id, value, state="done"):

        sel_state = value_id.replace("_part_alpha", "")
        Mgr.update_interface_remotely("uv", "part_color", sel_state, "alpha", value)

    def __set_part_color(self, sel_state, channels, value):

        if channels == "rgb":
            self._colorboxes[f"{sel_state}_part_rgb"].color = value[:3]
        elif channels == "alpha":
            prop_id = f"{sel_state}_part_alpha"
            self._fields[prop_id].set_value(value)

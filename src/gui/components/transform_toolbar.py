from ..base import *
from ..button import *
from ..toolbar import *
from ..dialogs import *


class TransformButtons(ToggleButtonGroup):

    def __init__(self, buttons):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", ["select", ""])

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        hotkeys = {
            "translate": [("w", 0), "W"],
            "rotate": [("e", 0), "E"],
            "scale": [("r", 0), "R"]
        }

        def add_toggle(transf_type):

            def toggle_on():

                Mgr.enter_state("selection_mode")
                GD["active_transform_type"] = transf_type
                Mgr.update_app("active_transform_type", transf_type)

                if GD["snap"]["on"][transf_type]:
                    Mgr.update_app("status", ["select", transf_type, "snap_idle"])
                else:
                    Mgr.update_app("status", ["select", transf_type, "idle"])

            toggle = (toggle_on, lambda: None)
            btn = buttons[transf_type]
            btn.set_hotkey(*hotkeys[transf_type])
            self.add_button(btn, transf_type, toggle)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)


class AxisButtons(ButtonGroup):

    def __init__(self, buttons):

        ButtonGroup.__init__(self)

        for axis_id in "xyz":
            btn = buttons[axis_id]
            btn.command = lambda a=axis_id: self.__set_axis_constraint(a)
            btn.set_hotkey((axis_id, 0), axis_id.upper())
            self.add_button(btn, axis_id)

        self._axes = {"": ""}

    def update_axis_constraints(self, transf_type, axes):

        for axis_id in "xyz":
            self.get_button(axis_id).active = False

        if not transf_type:
            return

        if axes in ("view", "trackball"):
            return

        self._axes[transf_type] = axes

        for axis_id in axes:
            self.get_button(axis_id).active = True

    def __set_axis_constraint(self, axis_id):

        tt = GD["active_transform_type"]

        if not tt:
            return

        old_axes = self._axes[tt]

        if tt == "translate":

            if len(self._axes[tt]) == 1:
                if axis_id == self._axes[tt]:
                    self._axes[tt] = "xyz".replace(axis_id, "")
                else:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis_id))
            else:
                if axis_id in self._axes[tt]:
                    self._axes[tt] = self._axes[tt].replace(axis_id, "")
                else:
                    self._axes[tt] = axis_id

        elif tt == "rotate":

            if axis_id != self._axes[tt]:
                self._axes[tt] = axis_id

        elif tt == "scale":

            if len(self._axes[tt]) == 1:
                if axis_id != self._axes[tt]:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis_id))
            else:
                if axis_id in self._axes[tt]:
                    self._axes[tt] = self._axes[tt].replace(axis_id, "")
                else:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis_id))

        Mgr.update_app("axis_constraints", tt, self._axes[tt])


class TransformToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "transform")

        widgets = Skin.layout.create(self, "transform")
        self._transform_btns = TransformButtons(widgets["buttons"])
        self._axis_btns = AxisButtons(widgets["buttons"])
        self._offsets_btn = offsets_btn = widgets["buttons"]["offsets"]
        self._fields = fields = widgets["fields"]
        self._comboboxes = widgets["comboboxes"]

        self.__setup_coord_sys_combobox()
        self.__setup_transf_center_combobox()
        Mgr.expose("coord_sys_combobox", lambda: self._comboboxes["coord_sys"])

        def set_active_transform_off():

            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", ["select", ""])

        self.add_hotkey(("q", 0), set_active_transform_off)

        font = Skin.text["input2"]["font"]
        is_relative_value = True
        btn_disabler = lambda: not GD["active_transform_type"]
        self._axis_btns.add_disabler("no_transf", btn_disabler)
        offsets_btn.command = self.__toggle_relative_values
        offsets_btn.add_disabler("no_transf", btn_disabler)
        field_disabler = lambda: not (GD["active_transform_type"] and GD["selection_count"])

        for axis_id in "xyz":

            field = fields[axis_id]
            field.add_disabler("no_transf_or_sel", field_disabler)
            handler = lambda value_id, value, state="done", a=axis_id: \
                self.__handle_value(a, value_id, value, state)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value((transf_type, not is_relative_value), "float", handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, "float", handler, font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

        self._axis_btns.enable(False)
        self.__enable_fields(False)
        self.__show_field_text(False)
        offsets_btn.active = False
        offsets_btn.enable(False)

        tools_menu = Mgr.get("tool_options_menu")
        item = tools_menu.add("transforms", "Transforms", self.__show_options_dialog)
        self._tool_options_menu_item = item

        def update_axis_constraints(transf_type, axes):

            if transf_type:
                self._axis_btns.update_axis_constraints(transf_type, axes)

        def set_transform_type(transf_type):

            if transf_type:

                self._transform_btns.set_active_button(transf_type)
                self._axis_btns.enable()
                axes = GD["axis_constraints"][transf_type]
                self._axis_btns.update_axis_constraints(transf_type, axes)
                obj_lvl = GD["active_obj_level"]
                is_rel_value = GD["rel_transform_values"][obj_lvl][transf_type]
                value_id = (transf_type, is_rel_value)

                for field in self._fields.values():
                    field.show_value(value_id)

                self._offsets_btn.enable(True)
                self._offsets_btn.active = is_rel_value
                self.__check_selection_count(transf_type)
                GD["snap"]["type"] = transf_type
                Mgr.update_locally("object_snap", "enable", True, False)

            else:

                self._transform_btns.deactivate()
                self._axis_btns.enable(False)
                self.__enable_fields(False)
                self.__show_field_text(False)
                self._offsets_btn.active = False
                self._offsets_btn.enable(False)

                if Mgr.get_state_id() not in ("transf_center_snap_mode",
                        "coord_origin_snap_mode"):
                    Mgr.update_locally("object_snap", "enable", False, False)

        Mgr.add_app_updater("active_transform_type", set_transform_type)
        Mgr.add_app_updater("axis_constraints", update_axis_constraints)
        Mgr.add_app_updater("transform_values", self.__set_field_values)
        Mgr.add_app_updater("selection_count", self.__check_selection_count)
        Mgr.add_app_updater("active_obj_level", self.__show_values)
        Mgr.add_app_updater("componentwise_xform", TransformDialog)
        Mgr.add_app_updater("coord_sys", self.__update_coord_sys)
        Mgr.add_app_updater("transf_center", self.__update_transf_center)

        Mgr.accept("update_offset_btn", self.__update_offset_btn)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))

        def add_picking_mode(picking_type):

            state_id = f"{picking_type}_picking_mode"

            def enter_picking_mode(prev_state_id, active):

                tint = Skin.colors["combobox_field_tint_pick"]
                self._comboboxes[picking_type].set_field_tint(tint)
                Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

            def exit_picking_mode(next_state_id, active):

                if not active:
                    self._comboboxes[picking_type].set_field_tint(None)

            add_state(state_id, -80, enter_picking_mode, exit_picking_mode)

        for picking_type in ("coord_sys", "transf_center"):
            add_picking_mode(picking_type)

        def add_snap_mode(snap_type):

            state_id = f"{snap_type}_snap_mode"

            def enter_snap_mode(prev_state_id, active):

                tint = Skin.colors["combobox_field_tint_pick"]
                combobox_id = "coord_sys" if snap_type == "coord_origin" else snap_type
                self._comboboxes[combobox_id].set_field_tint(tint)
                Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

                if not active:
                    GD["snap"]["prev_type"] = GD["snap"]["type"]
                    GD["snap"]["type"] = snap_type

            def exit_snap_mode(next_state_id, active):

                if not active:
                    combobox_id = "coord_sys" if snap_type == "coord_origin" else snap_type
                    self._comboboxes[combobox_id].set_field_tint(None)
                    Mgr.update_locally("object_snap", "enable", False, True)
                    GD["snap"]["type"] = GD["snap"]["prev_type"]

            add_state(state_id, -80, enter_snap_mode, exit_snap_mode)

        for snap_type in ("coord_origin", "transf_center"):
            add_snap_mode(snap_type)

    def __setup_coord_sys_combobox(self):

        combobox = self._comboboxes["coord_sys"]
        self._has_tmp_coord_sys_text = False

        def add_coord_sys_entry(cs_type, text):

            def set_coord_sys():

                self._has_tmp_coord_sys_text = False
                Mgr.update_remotely("grid_alignment", "cancel")
                Mgr.update_app("coord_sys", cs_type)

            combobox.add_item(cs_type, text, set_coord_sys)

        for cs in (("world", "World"), ("view", "View"), ("local", "Local")):
            add_coord_sys_entry(*cs)

        def start_coord_sys_picking():

            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            Mgr.enter_state("coord_sys_picking_mode")
            combobox = self._comboboxes["coord_sys"]
            combobox.select_none()
            combobox.select_item("object")
            self._has_tmp_coord_sys_text = True

        combobox.add_item("object", "Pick object...", start_coord_sys_picking, persistent=True)

        def enter_snap_mode():

            Mgr.enter_state("coord_origin_snap_mode")
            combobox = self._comboboxes["coord_sys"]
            combobox.select_none()
            combobox.select_item("snap_pt")
            self._has_tmp_coord_sys_text = True
            Mgr.update_locally("object_snap", "enable", True, True)

        combobox.add_item("snap_pt", "Snap to point...", enter_snap_mode, persistent=True)

        def set_custom_xform():

            Mgr.exit_state("coord_sys_picking_mode")
            Mgr.exit_state("coord_origin_snap_mode")
            combobox = self._comboboxes["coord_sys"]
            combobox.select_none()
            combobox.select_item("custom")
            self._has_tmp_coord_sys_text = True
            tint = Skin.colors["combobox_field_tint_pick"]
            combobox.set_field_tint(tint)
            CoordSysDialog(combobox)

        combobox.add_item("custom", "Custom transform...", set_custom_xform, persistent=True)

        menu = combobox.get_popup_menu()
        item = menu.add("align", "Align to", item_type="submenu")
        submenu = item.get_submenu()

        def add_align_target_type_entry(target_type, target_descr):

            def set_target_type():

                Mgr.update_remotely("grid_alignment", "pick_target", target_type)
                combobox = self._comboboxes["coord_sys"]
                combobox.select_none()
                combobox.select_item("custom")
                combobox.set_text("Align...")
                self._has_tmp_coord_sys_text = True
                tint = Skin.colors["combobox_field_tint_pick"]
                combobox.set_field_tint(tint)

            submenu.add(target_type, target_descr, set_target_type)

        target_types = ("view", "object", "obj_point", "surface")
        target_descr = ("view", "object", "object (aim at point)", "surface")

        for target_type, descr in zip(target_types, target_descr):
            add_align_target_type_entry(target_type, descr)

        menu.add("sep0", item_type="separator")
        combobox.add_item("store", "Store...", lambda: self.__show_coord_sys_dialog("store"))
        combobox.add_item("restore", "Restore...", lambda: self.__show_coord_sys_dialog("restore"))

        combobox.update_popup_menu()

    def __show_coord_sys_dialog(self, command_id):

        StoredTransformDialog(command_id, "coordinate system", "coord_sys")

    def __update_coord_sys_obj_name(self, name):

        if not self._has_tmp_coord_sys_text:
            self._comboboxes["coord_sys"].set_text(name)

    def __update_coord_sys(self, coord_sys_type, obj_name=None):

        combobox = self._comboboxes["coord_sys"]

        if Mgr.is_state_active("coord_sys_picking_mode"):
            Mgr.exit_state("coord_sys_picking_mode")
        elif Mgr.is_state_active("coord_origin_snap_mode"):
            Mgr.exit_state("coord_origin_snap_mode")
        elif Mgr.is_state_active("alignment_target_picking_mode"):
            Mgr.exit_state("alignment_target_picking_mode")

        combobox.select_item(coord_sys_type)

        if coord_sys_type == "object":
            combobox.set_text(obj_name.get_value())
            obj_name.add_updater("coord_sys", self.__update_coord_sys_obj_name)
        elif coord_sys_type == "custom":
            combobox.set_text("Custom")
            self._has_tmp_coord_sys_text = False

        self._has_tmp_coord_sys_text = False
        combobox.set_field_tint(None)

    def __setup_transf_center_combobox(self):

        combobox = self._comboboxes["transf_center"]
        self._has_tmp_transf_center_text = False

        def add_transf_center_type(tc_type, text):

            def set_transf_center():

                self._has_tmp_transf_center_text = False
                Mgr.update_app("transf_center", tc_type)

            combobox.add_item(tc_type, text, set_transf_center)

        for tc in (
            ("adaptive", "Adaptive"), ("sel_center", "Selection center"),
            ("pivot", "Pivot"), ("cs_origin", "Ref. coord. origin")
        ):
            add_transf_center_type(*tc)

        def start_transf_center_picking():

            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            Mgr.enter_state("transf_center_picking_mode")
            combobox = self._comboboxes["transf_center"]
            combobox.select_none()
            combobox.select_item("object")
            self._has_tmp_transf_center_text = True

        combobox.add_item("object", "Pick object...", start_transf_center_picking, persistent=True)

        def enter_snap_mode():

            Mgr.enter_state("transf_center_snap_mode")
            combobox = self._comboboxes["transf_center"]
            combobox.select_none()
            combobox.select_item("snap_pt")
            self._has_tmp_transf_center_text = True
            Mgr.update_locally("object_snap", "enable", True, True)

        combobox.add_item("snap_pt", "Snap to point...", enter_snap_mode, persistent=True)

        def set_custom_coords():

            Mgr.exit_state("transf_center_picking_mode")
            Mgr.exit_state("transf_center_snap_mode")
            combobox = self._comboboxes["transf_center"]
            combobox.select_none()
            combobox.select_item("custom")
            self._has_tmp_transf_center_text = True
            tint = Skin.colors["combobox_field_tint_pick"]
            combobox.set_field_tint(tint)
            TransfCenterDialog(combobox)

        combobox.add_item("custom", "Custom coords...", set_custom_coords, persistent=True)

        menu = combobox.get_popup_menu()
        menu.add("sep0", item_type="separator")
        combobox.add_item("store", "Store...", lambda: self.__show_transf_center_dialog("store"))
        combobox.add_item("restore", "Restore...", lambda: self.__show_transf_center_dialog("restore"))

        combobox.update_popup_menu()

    def __show_transf_center_dialog(self, command_id):

        StoredTransformDialog(command_id, "transform center", "transf_center")

    def __update_transf_center_obj_name(self, name):

        if not self._has_tmp_transf_center_text:
            self._comboboxes["transf_center"].set_text(name)

    def __update_transf_center(self, transf_center_type, obj_name=None):

        combobox = self._comboboxes["transf_center"]

        if Mgr.is_state_active("transf_center_picking_mode"):
            Mgr.exit_state("transf_center_picking_mode")
        elif Mgr.is_state_active("transf_center_snap_mode"):
            Mgr.exit_state("transf_center_snap_mode")

        combobox.select_item(transf_center_type)

        if transf_center_type == "object":
            combobox.set_text(obj_name.get_value())
            obj_name.add_updater("transf_center", self.__update_transf_center_obj_name)
        elif transf_center_type == "custom":
            combobox.set_text("Custom")
            self._has_tmp_transf_center_text = False

        self._has_tmp_transf_center_text = False
        combobox.set_field_tint(None)

    def __show_options_dialog(self):

        TransformOptionsDialog()

    def __update_offset_btn(self):

        transf_type = self._transform_btns.get_active_button_id()

        if transf_type:
            obj_lvl = GD["active_obj_level"]
            is_rel_value = GD["rel_transform_values"][obj_lvl][transf_type]
            self._offsets_btn.active = is_rel_value

    def __toggle_relative_values(self):

        transf_type = self._transform_btns.get_active_button_id()
        obj_lvl = GD["active_obj_level"]

        if obj_lvl in ("vert", "edge", "poly", "normal"):
            if not ((obj_lvl == "vert" and transf_type == "translate")
                    or (obj_lvl == "normal" and transf_type == "rotate")):
                return

        rel_values = GD["rel_transform_values"][obj_lvl]
        use_rel_values = not rel_values[transf_type]
        rel_values[transf_type] = use_rel_values
        value_id = (transf_type, use_rel_values)
        self._offsets_btn.active = use_rel_values

        for field in self._fields.values():

            field.show_value(value_id)

            if use_rel_values:
                field.show_text()
                val = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, val)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis_id, value_id, value, state="done"):

        transf_type, is_rel_value = value_id
        Mgr.update_remotely("transf_component", transf_type, axis_id, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis_id].set_value(value_id, val)

    def __set_field_values(self, transform_data=None):

        transf_type = GD["active_transform_type"]

        if not transform_data:

            obj_lvl = GD["active_obj_level"]

            if not (transf_type and GD["rel_transform_values"][obj_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.items():

            value_id = (transform_type, False)

            for axis_id, value in zip("xyz", values):
                self._fields[axis_id].set_value(value_id, value)

        if transf_type:
            self.__show_field_text()

    def __show_field_text(self, show=True):

        for field in self._fields.values():
            field.show_text(show)

    def __enable_fields(self, enable=True):

        if enable and not (GD["active_transform_type"]
                           and GD["selection_count"]):
            return

        for field in self._fields.values():
            field.enable(enable)

    def __check_selection_count(self, transf_type=None):

        tr_type = GD["active_transform_type"] if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = GD["selection_count"]
        self.__enable_fields(sel_count > 0)

        if sel_count > 1:

            color = Skin.text["input_disabled"]["color"]

            for field in self._fields.values():
                field.set_text_color(color)

        else:

            for field in self._fields.values():
                field.set_text_color()

        obj_lvl = GD["active_obj_level"]
        use_rel_values = GD["rel_transform_values"][obj_lvl][tr_type]
        show = (use_rel_values and sel_count) or sel_count == 1
        self.__show_field_text(show)

    def __show_values(self):

        transf_type = GD["active_transform_type"]

        if not transf_type:
            return

        obj_lvl = GD["active_obj_level"]
        use_rel_values = GD["rel_transform_values"][obj_lvl][transf_type]
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():
            field.show_value(value_id)

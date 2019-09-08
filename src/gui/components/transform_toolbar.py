from ..base import *
from ..button import *
from ..toolbar import *
from ..dialog import *
from .transform_dialogs import (TransformOptionsDialog, TransformDialog, CoordSysDialog,
                                TransfCenterDialog, StoredTransformDialog)


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", ["select", ""])

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        btn_data = {
            "translate": ("icon_translate", "Select and translate", [("w", 0), "W"]),
            "rotate": ("icon_rotate", "Select and rotate", [("e", 0), "E"]),
            "scale": ("icon_scale", "Select and scale", [("r", 0), "R"])
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
            icon_id, tooltip_text, hotkey = btn_data[transf_type]
            btn = ToolbarButton(toolbar, icon_id=icon_id, tooltip_text=tooltip_text)
            btn.set_hotkey(*hotkey)
            self.add_button(btn, transf_type, toggle)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)


class AxisButtons(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._axes = {"": ""}

    def update_axis_constraints(self, transf_type, axes):

        for axis in "xyz":
            self.get_button(axis).active = False

        if not transf_type:
            return

        if axes in ("view", "trackball"):
            return

        self._axes[transf_type] = axes

        for axis in axes:
            self.get_button(axis).active = True

    def __set_axis_constraint(self, axis):

        tt = GD["active_transform_type"]

        if not tt:
            return

        old_axes = self._axes[tt]

        if tt == "translate":

            if len(self._axes[tt]) == 1:
                if axis == self._axes[tt]:
                    self._axes[tt] = "xyz".replace(axis, "")
                else:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis))
            else:
                if axis in self._axes[tt]:
                    self._axes[tt] = self._axes[tt].replace(axis, "")
                else:
                    self._axes[tt] = axis

        elif tt == "rotate":

            if axis != self._axes[tt]:
                self._axes[tt] = axis

        elif tt == "scale":

            if len(self._axes[tt]) == 1:
                if axis != self._axes[tt]:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis))
            else:
                if axis in self._axes[tt]:
                    self._axes[tt] = self._axes[tt].replace(axis, "")
                else:
                    self._axes[tt] = "".join(sorted(self._axes[tt] + axis))

        Mgr.update_app("axis_constraints", tt, self._axes[tt])

    def create_button(self, toolbar, axis):

        icon_id = f"icon_{axis}"
        tooltip_text = f"Transform about {axis.upper()}-axis"
        command = lambda: self.__set_axis_constraint(axis)
        btn = ToolbarButton(toolbar, "", icon_id, tooltip_text, command)
        btn.set_hotkey((axis, 0), axis.upper())
        self.add_button(btn, axis)

        return btn


class CoordSysComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        icon_id = "icon_coord_sys"
        tooltip_text = "Reference coordinate system"

        ToolbarComboBox.__init__(self, toolbar, 100, icon_id=icon_id, tooltip_text=tooltip_text)

        self._has_tmp_text = False

        def add_coord_sys_entry(cs_type, text):

            def set_coord_sys():

                self._has_tmp_text = False
                Mgr.update_remotely("grid_alignment", "cancel")
                Mgr.update_app("coord_sys", cs_type)

            self.add_item(cs_type, text, set_coord_sys)

        for cs in (("world", "World"), ("view", "View"), ("local", "Local")):
            add_coord_sys_entry(*cs)

        def start_coord_sys_picking():

            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            Mgr.enter_state("coord_sys_picking_mode")
            self.select_none()
            self.select_item("object")
            self._has_tmp_text = True

        self.add_item("object", "Pick object...", start_coord_sys_picking, persistent=True)

        def enter_snap_mode():

            Mgr.enter_state("coord_origin_snap_mode")
            self.select_none()
            self.select_item("snap_pt")
            self._has_tmp_text = True
            Mgr.update_locally("object_snap", "enable", True, True)

        self.add_item("snap_pt", "Snap to point...", enter_snap_mode, persistent=True)

        def set_custom_xform():

            Mgr.exit_state("coord_sys_picking_mode")
            Mgr.exit_state("coord_origin_snap_mode")
            self.select_none()
            self.select_item("custom")
            self._has_tmp_text = True
            tint = Skin["colors"]["combobox_field_tint_pick"]
            self.set_field_tint(tint)
            CoordSysDialog(self)

        self.add_item("custom", "Custom transform...", set_custom_xform, persistent=True)

        menu = self.get_popup_menu()
        item = menu.add("align", "Align to", item_type="submenu")
        submenu = item.get_submenu()

        def add_align_target_type_entry(target_type, target_descr):

            def set_target_type():

                Mgr.update_remotely("grid_alignment", "pick_target", target_type)
                self.select_none()
                self.select_item("custom")
                self.set_text("Align...")
                self._has_tmp_text = True
                tint = Skin["colors"]["combobox_field_tint_pick"]
                self.set_field_tint(tint)

            submenu.add(target_type, target_descr, set_target_type)

        target_types = ("view", "object", "obj_point", "surface")
        target_descr = ("view", "object", "object (aim at point)", "surface")

        for target_type, descr in zip(target_types, target_descr):
            add_align_target_type_entry(target_type, descr)

        menu.add("sep0", item_type="separator")
        self.add_item("store", "Store...", lambda: self.__show_dialog("store"))
        self.add_item("restore", "Restore...", lambda: self.__show_dialog("restore"))

        self.update_popup_menu()

        Mgr.add_app_updater("coord_sys", self.__update)

    def __show_dialog(self, command_id):

        StoredTransformDialog(command_id, "coordinate system", "coord_sys")

    def __update_obj_name(self, name):

        if not self._has_tmp_text:
            self.set_text(name)

    def __update(self, coord_sys_type, obj_name=None):

        if Mgr.is_state_active("coord_sys_picking_mode"):
            Mgr.exit_state("coord_sys_picking_mode")
        elif Mgr.is_state_active("coord_origin_snap_mode"):
            Mgr.exit_state("coord_origin_snap_mode")
        elif Mgr.is_state_active("alignment_target_picking_mode"):
            Mgr.exit_state("alignment_target_picking_mode")

        self.select_item(coord_sys_type)

        if coord_sys_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("coord_sys", self.__update_obj_name)
        elif coord_sys_type == "custom":
            self.set_text("Custom")
            self._has_tmp_text = False

        self._has_tmp_text = False
        self.set_field_tint(None)


class TransfCenterComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        icon_id = "icon_transf_center"
        tooltip_text = "Transform center"

        ToolbarComboBox.__init__(self, toolbar, 100, icon_id=icon_id, tooltip_text=tooltip_text)

        self._has_tmp_text = False

        def add_transf_center_type(tc_type, text):

            def set_transf_center():

                self._has_tmp_text = False
                Mgr.update_app("transf_center", tc_type)

            self.add_item(tc_type, text, set_transf_center)

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
            self.select_none()
            self.select_item("object")
            self._has_tmp_text = True

        self.add_item("object", "Pick object...", start_transf_center_picking, persistent=True)

        def enter_snap_mode():

            Mgr.enter_state("transf_center_snap_mode")
            self.select_none()
            self.select_item("snap_pt")
            self._has_tmp_text = True
            Mgr.update_locally("object_snap", "enable", True, True)

        self.add_item("snap_pt", "Snap to point...", enter_snap_mode, persistent=True)

        def set_custom_coords():

            Mgr.exit_state("transf_center_picking_mode")
            Mgr.exit_state("transf_center_snap_mode")
            self.select_none()
            self.select_item("custom")
            self._has_tmp_text = True
            tint = Skin["colors"]["combobox_field_tint_pick"]
            self.set_field_tint(tint)
            TransfCenterDialog(self)

        self.add_item("custom", "Custom coords...", set_custom_coords, persistent=True)

        menu = self.get_popup_menu()
        menu.add("sep0", item_type="separator")
        self.add_item("store", "Store...", lambda: self.__show_dialog("store"))
        self.add_item("restore", "Restore...", lambda: self.__show_dialog("restore"))

        self.update_popup_menu()

        Mgr.add_app_updater("transf_center", self.__update)

    def __show_dialog(self, command_id):

        StoredTransformDialog(command_id, "transform center", "transf_center")

    def __update_obj_name(self, name):

        if not self._has_tmp_text:
            self.set_text(name)

    def __update(self, transf_center_type, obj_name=None):

        if Mgr.is_state_active("transf_center_picking_mode"):
            Mgr.exit_state("transf_center_picking_mode")
        elif Mgr.is_state_active("transf_center_snap_mode"):
            Mgr.exit_state("transf_center_snap_mode")

        self.select_item(transf_center_type)

        if transf_center_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("transf_center", self.__update_obj_name)
        elif transf_center_type == "custom":
            self.set_text("Custom")
            self._has_tmp_text = False

        self._has_tmp_text = False
        self.set_field_tint(None)


class TransformToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "transform", "Transform")

        self._transform_btns = btns = TransformButtons(self)

        def set_active_transform_off():

            GD["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", ["select", ""])

        self.add_hotkey(("q", 0), set_active_transform_off)

        borders = (0, 5, 0, 0)

        for transf_type in ("translate", "rotate", "scale"):
            btn = btns.get_button(transf_type)
            self.add(btn, borders=borders, alignment="center_v")

        self.add(ToolbarSeparator(self), borders=borders)

        self._axis_btns = AxisButtons()
        self._fields = {}

        get_value_handler = lambda axis: lambda value_id, value, state="done": \
            self.__handle_value(axis, value_id, value, state)

        font = Skin["text"]["input2"]["font"]
        is_relative_value = True
        btn_disabler = lambda: not GD["active_transform_type"]
        self._axis_btns.add_disabler("no_transf", btn_disabler)
        field_disabler = lambda: not (GD["active_transform_type"] and GD["selection_count"])

        for axis in "xyz":

            axis_btn = self._axis_btns.create_button(self, axis)
            self.add(axis_btn, borders=borders, alignment="center_v")

            field = ToolbarMultiValField(self, 80)
            field.add_disabler("no_transf_or_sel", field_disabler)
            self._fields[axis] = field
            self.add(field, borders=borders, alignment="center_v")
            handler = get_value_handler(axis)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value((transf_type, not is_relative_value), "float", handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, "float", handler, font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

        icon_id = "icon_offsets"
        tooltip_text = "Input relative values (offsets)"
        btn = ToolbarButton(self, "", icon_id, tooltip_text, self.__toggle_relative_values)
        btn.add_disabler("no_transf", btn_disabler)
        self._offsets_btn = btn
        self.add(btn, borders=borders, alignment="center_v")

        self.add(ToolbarSeparator(self), borders=borders)

        self._comboboxes = {}
        combobox = CoordSysComboBox(self)
        self._comboboxes["coord_sys"] = combobox
        Mgr.expose("coord_sys_combobox", lambda: self._comboboxes["coord_sys"])
        self.add(combobox, borders=borders, alignment="center_v")
        combobox = TransfCenterComboBox(self)
        self._comboboxes["transf_center"] = combobox
        self.add(combobox, alignment="center_v")

        self._axis_btns.enable(False)
        self.__enable_fields(False)
        self.__show_field_text(False)
        self._offsets_btn.active = False
        self._offsets_btn.enable(False)

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

        Mgr.accept("update_offset_btn", self.__update_offset_btn)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False))

        def add_picking_mode(picking_type):

            state_id = f"{picking_type}_picking_mode"

            def enter_picking_mode(prev_state_id, active):

                tint = Skin["colors"]["combobox_field_tint_pick"]
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

                tint = Skin["colors"]["combobox_field_tint_pick"]
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

    def __handle_value(self, axis, value_id, value, state="done"):

        transf_type, is_rel_value = value_id
        Mgr.update_remotely("transf_component", transf_type, axis, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis].set_value(value_id, val)

    def __set_field_values(self, transform_data=None):

        transf_type = GD["active_transform_type"]

        if not transform_data:

            obj_lvl = GD["active_obj_level"]

            if not (transf_type and GD["rel_transform_values"][obj_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.items():

            value_id = (transform_type, False)

            for axis, value in zip("xyz", values):
                self._fields[axis].set_value(value_id, value)

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

            color = (.5, .5, .5, 1.)

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

from ..base import *
from ..button import *
from ..toolbar import *


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", ["select", ""])

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        btn_data = {
            "translate": ("icon_translate", "Select and translate", ("w", 0)),
            "rotate": ("icon_rotate", "Select and rotate", ("e", 0)),
            "scale": ("icon_scale", "Select and scale", ("r", 0))
        }

        def add_toggle(transf_type):

            def toggle_on():

                Mgr.enter_state("selection_mode")
                GlobalData["active_transform_type"] = transf_type
                Mgr.update_app("active_transform_type", transf_type)
                Mgr.update_app("status", ["select", transf_type, "idle"])

            toggle = (toggle_on, lambda: None)
            icon_id, tooltip_text, hotkey = btn_data[transf_type]
            btn = ToolbarButton(toolbar, icon_id=icon_id, tooltip_text=tooltip_text)
            btn.set_hotkey(hotkey)
            self.add_button(btn, transf_type, toggle)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)


class AxisButtons(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._axes = {"": ""}

    def update_axis_constraints(self, transf_type, axes):

        for axis in "xyz":
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        if axes in ("screen", "trackball"):
            return

        self._axes[transf_type] = axes

        for axis in axes:
            self.get_button(axis).set_active()

    def __set_axis_constraint(self, axis):

        tt = GlobalData["active_transform_type"]

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

        icon_id = "icon_{}".format(axis)
        tooltip_text = "Transform about {}".format(axis.upper())
        command = lambda: self.__set_axis_constraint(axis)
        btn = ToolbarButton(toolbar, "", icon_id, tooltip_text, command)
        btn.set_hotkey((axis, 0))
        self.add_button(btn, axis)

        return btn


class CoordSysComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        icon_id = "icon_coord_sys"
        tooltip_text = "Coordinate system"

        ToolbarComboBox.__init__(self, toolbar, 100, icon_id=icon_id, tooltip_text=tooltip_text)

        def add_coord_sys_entry(cs_type, text):

            if cs_type == "object":

                def start_coord_sys_picking():

                    self.select_item(cs_type)
                    Mgr.enter_state("coord_sys_picking_mode")

                self.add_item(cs_type, text, start_coord_sys_picking, persistent=True)

            else:

                def set_coord_sys():

                    Mgr.exit_state("coord_sys_picking_mode")
                    Mgr.update_app("coord_sys", cs_type)

                self.add_item(cs_type, text, set_coord_sys)

        for cs in (
            ("world", "World"), ("screen", "Screen"), ("local", "Local"),
            ("object", "Pick object...")
        ):
            add_coord_sys_entry(*cs)

        self.update_popup_menu()

        Mgr.add_app_updater("coord_sys", self.__update)

    def __update(self, coord_sys_type, obj_name=None):

        self.select_item(coord_sys_type)

        if coord_sys_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("coord_sys", self.set_text)


class TransfCenterComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        icon_id = "icon_transf_center"
        tooltip_text = "Transform center"

        ToolbarComboBox.__init__(self, toolbar, 100, icon_id=icon_id, tooltip_text=tooltip_text)

        def add_transf_center_type(tc_type, text):

            if tc_type == "object":

                def start_transf_center_picking():

                    self.select_item(tc_type)
                    Mgr.enter_state("transf_center_picking_mode")

                self.add_item(tc_type, text, start_transf_center_picking, persistent=True)

            else:

                def set_transf_center():

                    Mgr.exit_state("transf_center_picking_mode")
                    Mgr.update_app("transf_center", tc_type)

                self.add_item(tc_type, text, set_transf_center)

        for tc in (
            ("adaptive", "Adaptive"), ("sel_center", "Selection Center"),
            ("pivot", "Pivot"), ("cs_origin", "Coord Sys Origin"),
            ("object", "Pick object...")
        ):
            add_transf_center_type(*tc)

        self.update_popup_menu()

        Mgr.add_app_updater("transf_center", self.__update)

    def __update(self, transf_center_type, obj_name=None):

        self.select_item(transf_center_type)

        if transf_center_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("transf_center", self.set_text)


class TransformToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "transform", "Transform")

        self._transform_btns = btns = TransformButtons(self)

        def set_active_transform_off():

            GlobalData["active_transform_type"] = ""
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

        get_rel_val_toggler = lambda field: lambda: self.__toggle_relative_values(field)
        get_popup_handler = lambda field: lambda: self.__on_popup(field)
        get_value_handler = lambda axis: lambda value_id, value: self.__handle_value(axis, value_id, value)

        font = Skin["text"]["input2"]["font"]
        is_relative_value = True
        axis_btn_disabler = lambda: not GlobalData["active_transform_type"]
        self._axis_btns.add_disabler("no_transf", axis_btn_disabler)
        field_disabler = lambda: not (GlobalData["active_transform_type"] and GlobalData["selection_count"])

        for axis in "xyz":

            axis_btn = self._axis_btns.create_button(self, axis)
            self.add(axis_btn, borders=borders, alignment="center_v")

            field = ToolbarInputField(self, 80)
            field.add_disabler("no_transf_or_sel", field_disabler)
            self._fields[axis] = field
            self.add(field, borders=borders, alignment="center_v")
            field.set_popup_handler(get_popup_handler(field))
            menu = field.get_popup_menu()
            menu.add("use_rel_values", "Use relative values", get_rel_val_toggler(field),
                     item_type="check", update=True)
            handler = get_value_handler(axis)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value((transf_type, not is_relative_value), handler=handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, handler=handler, font=font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0., handle_value=False)

        self.add(ToolbarSeparator(self), borders=borders)

        self._comboboxes = {}
        combobox = CoordSysComboBox(self)
        self._comboboxes["coord_sys"] = combobox
        self.add(combobox, borders=borders, alignment="center_v")
        combobox = TransfCenterComboBox(self)
        self._comboboxes["transf_center"] = combobox
        self.add(combobox, alignment="center_v")

        self._axis_btns.enable(False)
        self.__enable_fields(False)
        self.__show_field_text(False)

        def update_axis_constraints(transf_type, axes):

            if transf_type:
                self._axis_btns.update_axis_constraints(transf_type, axes)

        def set_transform_type(transf_type):

            if transf_type:

                self._transform_btns.set_active_button(transf_type)
                self._axis_btns.enable()
                axes = GlobalData["axis_constraints"][transf_type]
                self._axis_btns.update_axis_constraints(transf_type, axes)
                obj_lvl = GlobalData["active_obj_level"]
                is_rel_value = GlobalData["rel_transform_values"][obj_lvl][transf_type]
                value_id = (transf_type, is_rel_value)

                for field in self._fields.values():
                    field.show_value(value_id)

                self.__check_selection_count(transf_type)

            else:

                self._transform_btns.deactivate()
                self._axis_btns.enable(False)
                self.__enable_fields(False)
                self.__show_field_text(False)

        Mgr.add_app_updater("active_transform_type", set_transform_type)
        Mgr.add_app_updater("axis_constraints", update_axis_constraints)
        Mgr.add_app_updater("transform_values", self.__set_field_values)
        Mgr.add_app_updater("selection_count", self.__check_selection_count)
        Mgr.add_app_updater("active_obj_level", self.__show_values)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("enable_gui", False))

        def add_picking_mode(picking_type):

            state_id = "{}_picking_mode".format(picking_type)

            def enter_picking_mode(prev_state_id, is_active):

                tint = Skin["colors"]["combobox_field_tint_pick"]
                self._comboboxes[picking_type].set_field_tint(tint)
                Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

            def exit_picking_mode(next_state_id, is_active):

                if not is_active:
                    self._comboboxes[picking_type].set_field_tint(None)

            add_state(state_id, -80, enter_picking_mode, exit_picking_mode)

        for picking_type in ("coord_sys", "transf_center"):
            add_picking_mode(picking_type)

    def __on_popup(self, field):

        transf_type, is_rel_value = field.get_value_id()
        field.get_popup_menu().check_item("use_rel_values", is_rel_value)

    def __toggle_relative_values(self, current_field):

        transf_type = self._transform_btns.get_active_button_id()
        obj_lvl = GlobalData["active_obj_level"]

        if obj_lvl in ("vert", "edge", "poly", "normal"):
            if not ((obj_lvl == "vert" and transf_type == "translate")
                    or (obj_lvl == "normal" and transf_type == "rotate")):
                return

        rel_values = GlobalData["rel_transform_values"][obj_lvl]
        use_rel_values = not rel_values[transf_type]
        rel_values[transf_type] = use_rel_values
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():

            field.show_value(value_id)

            if use_rel_values:
                field.show_text()
                val = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, val, handle_value=False)

            if field is not current_field:
                field.get_popup_menu().check_item("use_rel_values", use_rel_values)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis, value_id, value):

        transf_type, is_rel_value = value_id
        Mgr.update_remotely("transf_component", transf_type, axis, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis].set_value(value_id, val, handle_value=False)

    def __set_field_values(self, transform_data=None):

        transf_type = GlobalData["active_transform_type"]

        if not transform_data:

            obj_lvl = GlobalData["active_obj_level"]

            if not (transf_type and GlobalData["rel_transform_values"][obj_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.items():

            value_id = (transform_type, False)

            for axis, value in zip("xyz", values):
                self._fields[axis].set_value(value_id, value, handle_value=False)

        if transf_type:
            self.__show_field_text()

    def __show_field_text(self, show=True):

        for field in self._fields.values():
            field.show_text(show)

    def __enable_fields(self, enable=True):

        if enable and not (GlobalData["active_transform_type"]
                           and GlobalData["selection_count"]):
            return

        for field in self._fields.values():
            field.enable(enable)

    def __check_selection_count(self, transf_type=None):

        tr_type = GlobalData["active_transform_type"] if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = GlobalData["selection_count"]
        self.__enable_fields(sel_count > 0)

        if sel_count > 1:

            color = (.5, .5, .5, 1.)

            for field in self._fields.values():
                field.set_text_color(color)

        else:

            for field in self._fields.values():
                field.set_text_color()

        obj_lvl = GlobalData["active_obj_level"]
        use_rel_values = GlobalData["rel_transform_values"][obj_lvl][tr_type]
        show = (use_rel_values and sel_count) or sel_count == 1
        self.__show_field_text(show)

    def __show_values(self):

        transf_type = GlobalData["active_transform_type"]

        if not transf_type:
            return

        obj_lvl = GlobalData["active_obj_level"]
        use_rel_values = GlobalData["rel_transform_values"][obj_lvl][transf_type]
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():
            field.show_value(value_id)

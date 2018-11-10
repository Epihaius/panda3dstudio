from ...base import *
from ...button import *
from ...toolbar import *


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GlobalData["active_uv_transform_type"] = ""
            Mgr.update_interface("uv", "active_transform_type", "")
            Mgr.update_app("status", ["select_uvs", ""], "uv")

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        btn_data = {
            "translate": ("icon_translate", "Select and translate", [("w", 0), "W"]),
            "rotate": ("icon_rotate", "Select and rotate", [("e", 0), "E"]),
            "scale": ("icon_scale", "Select and scale", [("r", 0), "R"])
        }

        def add_toggle(transf_type):

            def toggle_on():

                GlobalData["active_uv_transform_type"] = transf_type
                Mgr.update_interface("uv", "active_transform_type", transf_type)
                Mgr.update_app("status", ["select_uvs", transf_type, "idle"], "uv")

            toggle = (toggle_on, lambda: None)
            icon_id, tooltip_text, hotkey = btn_data[transf_type]
            btn = ToolbarButton(toolbar, icon_id=icon_id, tooltip_text=tooltip_text)
            btn.set_hotkey(*hotkey, "uv")
            btn.enable_hotkey(False)
            self.add_button(btn, transf_type, toggle)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)


class AxisButtons(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._axes = {"": ""}

    def update_axis_constraints(self, transf_type, axes):

        for axis in "uvw":
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        self._axes[transf_type] = axes

        for axis in axes:
            self.get_button(axis).set_active()

    def __set_axis_constraint(self, axis):

        tt = GlobalData["active_uv_transform_type"]

        if not tt:
            return

        if tt == "rotate":
            self.get_button(axis).set_active()
            return

        old_axes = self._axes[tt]

        if len(self._axes[tt]) == 1:
            if axis == self._axes[tt]:
                self._axes[tt] = "uv".replace(axis, "")
            else:
                self._axes[tt] = "".join(sorted(self._axes[tt] + axis))
        else:
            if axis in self._axes[tt]:
                self._axes[tt] = self._axes[tt].replace(axis, "")
            else:
                self._axes[tt] = axis

        Mgr.update_interface("uv", "axis_constraints", tt, self._axes[tt])

    def create_button(self, toolbar, axis):

        icon_id = "icon_{}".format(axis)
        tooltip_text = "Transform about {}-axis".format(axis.upper())
        command = lambda: self.__set_axis_constraint(axis)
        btn = ToolbarButton(toolbar, "", icon_id, tooltip_text, command)
        self.add_button(btn, axis)

        if axis != "w":
            btn.set_hotkey((axis, 0), axis.upper(), "uv")
            btn.enable_hotkey(False)

        return btn


class TransformToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "uv_transform", "UV Transform")

        self._uv_lvl = "poly"

        self._checkboxes = {}
        self._transform_btns = btns = TransformButtons(self)

        def set_active_transform_off():

            GlobalData["active_uv_transform_type"] = ""
            Mgr.update_interface("uv", "active_transform_type", "")
            Mgr.update_app("status", ["select_uvs", ""], "uv")

        self.add_hotkey(("q", 0), set_active_transform_off, "uv")

        borders = (0, 5, 0, 0)
        get_handles_toggler = lambda transf_type: lambda shown: self.__toggle_transform_handles(transf_type, shown)

        for transf_type in ("translate", "rotate", "scale"):
            checkbox = ToolbarCheckBox(self, get_handles_toggler(transf_type))
            checkbox.check()
            self._checkboxes[transf_type] = checkbox
            self.add(checkbox, borders=borders, alignment="center_v")
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

        for axis in "uvw":

            axis_btn = self._axis_btns.create_button(self, axis)
            self.add(axis_btn, borders=borders, alignment="center_v")

            field = ToolbarInputField(self, 80)
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
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("enable_gui", False), interface_id="uv")

        self._axis_btns.enable(False)
        self.__enable_fields(False)
        self.__show_field_text(False)

    def add_interface_updaters(self):

        Mgr.add_app_updater("active_transform_type", self.__set_transform_type, interface_id="uv")
        Mgr.add_app_updater("axis_constraints", self.__update_axis_constraints, interface_id="uv")
        Mgr.add_app_updater("transform_handles", self.__show_transform_handles, interface_id="uv")
        Mgr.add_app_updater("transform_values", self.__set_field_values, interface_id="uv")
        Mgr.add_app_updater("selection_count", self.__check_selection_count, interface_id="uv")
        Mgr.add_app_updater("uv_level", self.__set_uv_level, interface_id="uv")

    def __set_transform_type(self, transf_type):

        axis_btns = self._axis_btns

        if transf_type:

            self._transform_btns.set_active_button(transf_type)
            axis_btns.enable()

            if transf_type == "rotate":
                axis_btns.get_button("u").enable(False)
                axis_btns.get_button("v").enable(False)
                axis_btns.get_button("w").set_active()
            else:
                axis_btns.get_button("w").enable(False)
                axes = GlobalData["uv_axis_constraints_{}".format(transf_type)]
                axis_btns.update_axis_constraints(transf_type, axes)

            rel_values = GlobalData["rel_uv_transform_values"]
            is_rel_value = rel_values[self._uv_lvl][transf_type]
            value_id = (transf_type, is_rel_value)

            for field in self._fields.values():
                field.show_value(value_id)

            self.__check_selection_count(transf_type)

        else:

            self._transform_btns.deactivate()
            axis_btns.enable(False)
            self.__enable_fields(False)
            self.__show_field_text(False)

    def __update_axis_constraints(self, transf_type, axes):

        if transf_type:
            self._axis_btns.update_axis_constraints(transf_type, axes)

    def __toggle_transform_handles(self, transf_type, shown):

        Mgr.update_interface_remotely("uv", "transform_handles", transf_type, shown)

    def __show_transform_handles(self, transf_type, shown):

        self._checkboxes[transf_type].check(shown)

    def __on_popup(self, field):

        transf_type, is_rel_value = field.get_value_id()
        field.get_popup_menu().check_item("use_rel_values", is_rel_value)

    def __toggle_relative_values(self, current_field):

        transf_type = self._transform_btns.get_active_button_id()
        uv_lvl = self._uv_lvl

        if uv_lvl in ("vert", "edge", "poly"):
            if not (uv_lvl == "vert" and transf_type == "translate"):
                return

        rel_values = GlobalData["rel_uv_transform_values"][uv_lvl]
        use_rel_values = not rel_values[transf_type]
        rel_values[transf_type] = use_rel_values
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():

            field.show_value(value_id)

            if use_rel_values:
                value = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, value)

            if field is not current_field:
                field.get_popup_menu().check_item("use_rel_values", use_rel_values)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis, value_id, value):

        transf_type, is_rel_value = value_id
        Mgr.update_interface_remotely("uv", "transf_component", transf_type,
                                      axis, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis].set_value(value_id, val)

    def __set_field_values(self, transform_data=None):

        transf_type = GlobalData["active_uv_transform_type"]

        if not transform_data:

            if not (transf_type and GlobalData["rel_uv_transform_values"][self._uv_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.items():

            value_id = (transform_type, False)

            for axis, value in zip("uv", values):
                self._fields[axis].set_value(value_id, value)

        if transf_type:
            self.__show_field_text()

    def __show_field_text(self, show=True):

        transf_type = GlobalData["active_uv_transform_type"]
        fields = self._fields

        for field in fields.values():
            field.show_text(show)

        if show:
            if transf_type == "rotate":
                fields["u"].show_text(False)
                fields["v"].show_text(False)
            else:
                fields["w"].show_text(False)

    def __enable_fields(self, enable=True):

        transf_type = GlobalData["active_uv_transform_type"]

        if enable and not (transf_type and GlobalData["uv_selection_count"]):
            return

        fields = self._fields

        for field in fields.values():
            field.enable(enable)

        if enable:
            if transf_type == "rotate":
                fields["u"].enable(False)
                fields["v"].enable(False)
            else:
                fields["w"].enable(False)

    def __check_selection_count(self, transf_type=None):

        tr_type = GlobalData["active_uv_transform_type"] if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = GlobalData["uv_selection_count"]
        self.__enable_fields(sel_count > 0)

        if sel_count > 1:

            color = (.5, .5, .5, 1.)

            for field in self._fields.values():
                field.set_text_color(color)

        else:

            for field in self._fields.values():
                field.set_text_color()

        use_rel_values = GlobalData["rel_uv_transform_values"][self._uv_lvl][tr_type]
        show = (use_rel_values and sel_count) or sel_count == 1
        self.__show_field_text(show)

    def __set_uv_level(self, uv_level):

        self._uv_lvl = uv_level

        transf_type = GlobalData["active_uv_transform_type"]

        if not transf_type:
            return

        use_rel_values = GlobalData["rel_uv_transform_values"][uv_level][transf_type]
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():
            field.show_value(value_id)

        self.__check_selection_count(transf_type)

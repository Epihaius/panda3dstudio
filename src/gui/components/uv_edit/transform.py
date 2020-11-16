from ...base import *
from ...button import *
from ...toolbar import *


class TransformButtons(ToggleButtonGroup):

    def __init__(self, buttons):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GD["active_uv_transform_type"] = ""
            Mgr.update_interface("uv", "active_transform_type", "")
            Mgr.update_app("status", ["select_uvs", ""], "uv")

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        hotkeys = {
            "translate": [("w", 0), "W"],
            "rotate": [("e", 0), "E"],
            "scale": [("r", 0), "R"]
        }

        def add_toggle(transf_type):

            def toggle_on():

                GD["active_uv_transform_type"] = transf_type
                Mgr.update_interface("uv", "active_transform_type", transf_type)
                Mgr.update_app("status", ["select_uvs", transf_type, "idle"], "uv")

            toggle = (toggle_on, lambda: None)
            btn = buttons[transf_type]
            btn.set_hotkey(*hotkeys[transf_type], "uv")
            btn.enable_hotkey(False)
            self.add_button(btn, transf_type, toggle)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)


class AxisButtons(ButtonGroup):

    def __init__(self, buttons):

        ButtonGroup.__init__(self)

        for axis_id in "uvw":

            btn = buttons[axis_id]
            btn.command = lambda a=axis_id: self.__set_axis_constraint(a)
            self.add_button(btn, axis_id)

            if axis_id != "w":
                btn.set_hotkey((axis_id, 0), axis_id.upper(), "uv")
                btn.enable_hotkey(False)

        self._axes = {"": ""}

    def update_axis_constraints(self, transf_type, axes):

        for axis_id in "uvw":
            self.get_button(axis_id).active = False

        if not transf_type:
            return

        self._axes[transf_type] = axes

        for axis_id in axes:
            self.get_button(axis_id).active = True

    def __set_axis_constraint(self, axis_id):

        tt = GD["active_uv_transform_type"]

        if not tt:
            return

        if tt == "rotate":
            self.get_button(axis_id).active = True
            return

        old_axes = self._axes[tt]

        if len(self._axes[tt]) == 1:
            if axis_id == self._axes[tt]:
                self._axes[tt] = "uv".replace(axis_id, "")
            else:
                self._axes[tt] = "".join(sorted(self._axes[tt] + axis_id))
        else:
            if axis_id in self._axes[tt]:
                self._axes[tt] = self._axes[tt].replace(axis_id, "")
            else:
                self._axes[tt] = axis_id

        Mgr.update_interface("uv", "axis_constraints", tt, self._axes[tt])


class TransformToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "uv_transform")

        widgets = Skin.layout.create(self, "uv_transform")
        self._transform_btns = TransformButtons(widgets["buttons"])
        self._axis_btns = AxisButtons(widgets["buttons"])
        self._offsets_btn = offsets_btn = widgets["buttons"]["offsets"]
        self._checkbuttons = checkbuttons = widgets["checkbuttons"]
        self._fields = fields = widgets["fields"]

        self._uv_lvl = "poly"

        def set_active_transform_off():

            GD["active_uv_transform_type"] = ""
            Mgr.update_interface("uv", "active_transform_type", "")
            Mgr.update_app("status", ["select_uvs", ""], "uv")

        self.add_hotkey(("q", 0), set_active_transform_off, "uv")

        get_handles_toggler = lambda transf_type: lambda shown: \
            self.__toggle_transform_handles(transf_type, shown)

        for transf_type in ("translate", "rotate", "scale"):
            checkbtn = checkbuttons[transf_type]
            checkbtn.command = get_handles_toggler(transf_type)
            checkbtn.check()

        font = Skin.text["input2"]["font"]
        is_relative_value = True

        for axis_id in "uvw":

            field = fields[axis_id]
            handler = lambda value_id, value, state="done", a=axis_id: \
                self.__handle_value(a, value_id, value, state)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value((transf_type, not is_relative_value), "float", handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, "float", handler, font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

        offsets_btn.command = self.__toggle_relative_values
        btn_disabler = lambda: not GD["active_uv_transform_type"]
        offsets_btn.add_disabler("no_transf", btn_disabler)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, active:
                  Mgr.do("enable_gui", False), interface_id="uv")

        self._axis_btns.enable(False)
        self.__enable_fields(False)
        self.__show_field_text(False)
        self._offsets_btn.active = False
        self._offsets_btn.enable(False)

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
                axis_btns.get_button("w").active = True
            else:
                axis_btns.get_button("w").enable(False)
                axes = GD[f"uv_axis_constraints_{transf_type}"]
                axis_btns.update_axis_constraints(transf_type, axes)

            rel_values = GD["rel_uv_transform_values"]
            is_rel_value = rel_values[self._uv_lvl][transf_type]
            value_id = (transf_type, is_rel_value)

            for field in self._fields.values():
                field.show_value(value_id)

            self._offsets_btn.enable(True)
            self._offsets_btn.active = is_rel_value
            self.__check_selection_count(transf_type)

        else:

            self._transform_btns.deactivate()
            axis_btns.enable(False)
            self.__enable_fields(False)
            self.__show_field_text(False)
            self._offsets_btn.active = False
            self._offsets_btn.enable(False)

    def __update_axis_constraints(self, transf_type, axes):

        if transf_type:
            self._axis_btns.update_axis_constraints(transf_type, axes)

    def __toggle_transform_handles(self, transf_type, shown):

        Mgr.update_interface_remotely("uv", "transform_handles", transf_type, shown)

        if GD["ctrl_down"]:

            other_transf_types = ["translate", "rotate", "scale"]
            other_transf_types.remove(transf_type)
            btns = self._checkbuttons

            for other_type in other_transf_types:
                if btns[other_type].is_checked() != shown:
                    Mgr.update_interface_remotely("uv", "transform_handles", other_type, shown)
                    btns[other_type].check(shown)

    def __show_transform_handles(self, transf_type, shown):

        self._checkbuttons[transf_type].check(shown)

    def __toggle_relative_values(self):

        transf_type = self._transform_btns.get_active_button_id()
        uv_lvl = self._uv_lvl

        if uv_lvl in ("vert", "edge", "poly"):
            if not (uv_lvl == "vert" and transf_type == "translate"):
                return

        rel_values = GD["rel_uv_transform_values"][uv_lvl]
        use_rel_values = not rel_values[transf_type]
        rel_values[transf_type] = use_rel_values
        value_id = (transf_type, use_rel_values)
        self._offsets_btn.active = use_rel_values

        for field in self._fields.values():

            field.show_value(value_id)

            if use_rel_values:
                value = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, value)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis_id, value_id, value, state="done"):

        transf_type, is_rel_value = value_id
        Mgr.update_interface_remotely("uv", "transf_component", transf_type,
                                      axis_id, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis_id].set_value(value_id, val)

    def __set_field_values(self, transform_data=None):

        transf_type = GD["active_uv_transform_type"]

        if not transform_data:

            if not (transf_type and GD["rel_uv_transform_values"][self._uv_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.items():

            value_id = (transform_type, False)

            if transform_type == "rotate":
                self._fields["w"].set_value(value_id, values[0])
            else:
                for axis_id, value in zip("uv", values):
                    self._fields[axis_id].set_value(value_id, value)

        if transf_type:
            self.__show_field_text()

    def __show_field_text(self, show=True):

        transf_type = GD["active_uv_transform_type"]
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

        transf_type = GD["active_uv_transform_type"]

        if enable and not (transf_type and GD["uv_selection_count"]):
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

        tr_type = GD["active_uv_transform_type"] if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = GD["uv_selection_count"]
        self.__enable_fields(sel_count > 0)

        if sel_count > 1:

            color = Skin.text["input_disabled"]["color"]

            for field in self._fields.values():
                field.set_text_color(color)

        else:

            for field in self._fields.values():
                field.set_text_color()

        use_rel_values = GD["rel_uv_transform_values"][self._uv_lvl][tr_type]
        show = (use_rel_values and sel_count) or sel_count == 1
        self.__show_field_text(show)

    def __set_uv_level(self, uv_level):

        self._uv_lvl = uv_level

        transf_type = GD["active_uv_transform_type"]

        if not transf_type:
            return

        use_rel_values = GD["rel_uv_transform_values"][uv_level][transf_type]
        value_id = (transf_type, use_rel_values)

        for field in self._fields.values():
            field.show_value(value_id)

        self.__check_selection_count(transf_type)
        self._offsets_btn.active = use_rel_values

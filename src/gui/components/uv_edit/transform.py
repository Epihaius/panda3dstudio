from ...base import *
from ...button import Button, ButtonGroup
from ...toggle import ToggleButtonGroup
from ...field import InputField
from ...combobox import ComboBox
from ...checkbox import CheckBox


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar, focus_receiver):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GlobalData["active_uv_transform_type"] = ""
            Mgr.update_interface("uv_window", "active_transform_type", "")

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        btn_data = {
            "translate": ("icon_translate", "Select and translate"),
            "rotate": ("icon_rotate", "Select and rotate"),
            "scale": ("icon_scale", "Select and scale")
        }

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        def add_toggle(transf_type):

            def toggle_on():

                GlobalData["active_uv_transform_type"] = transf_type
                Mgr.update_interface("uv_window", "active_transform_type", transf_type)

            toggle = (toggle_on, lambda: None)
            icon_name, btn_tooltip = btn_data[transf_type]
            icon_path = os.path.join(GFX_PATH, icon_name + ".png")

            bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
            self.add_button(toolbar, transf_type, toggle, bitmaps, btn_tooltip,
                            focus_receiver=focus_receiver)

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

        Mgr.update_interface("uv_window", "axis_constraints", tt, self._axes[tt])

    def create_button(self, toolbar, axis, focus_receiver=None):

        icon_name = "icon_%s" % axis.lower()
        icon_path = os.path.join(GFX_PATH, icon_name + ".png")
        bitmap_paths = Button.get_bitmap_paths("toolbar_button")
        bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
        tooltip_label = "Transform about %s" % axis.upper()
        btn = Button(toolbar, bitmaps, "", tooltip_label, lambda: self.__set_axis_constraint(axis),
                     focus_receiver=focus_receiver)
        self.add_button(btn, axis)

        return btn


class TransformToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width, focus_receiver=parent)

        self._uv_lvl = "poly"

        sizer = self.GetSizer()

        self._checkboxes = {}
        self._transform_btns = TransformButtons(self, parent)
        get_handles_toggler = lambda transf_type: lambda shown: self.__toggle_transform_handles(transf_type, shown)

        for transf_type in ("translate", "rotate", "scale"):
            checkbox = CheckBox(self, get_handles_toggler(transf_type), focus_receiver=parent)
            checkbox.check()
            self._checkboxes[transf_type] = checkbox
            sizer.Add(checkbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            btn = self._transform_btns.get_button(transf_type)
            sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        sizer.AddSpacer(10)
        self._axis_btns = AxisButtons()
        self._fields = {}

        get_rel_val_toggler = lambda field: lambda: self.__toggle_relative_values(field)
        get_popup_handler = lambda field: lambda: self.__on_popup(field)
        get_value_handler = lambda axis: lambda *args: self.__handle_value(axis, *args)

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        is_relative_value = True

        for axis in "uvw":

            axis_btn = self._axis_btns.create_button(self, axis, parent)
            sizer.Add(axis_btn, 0, wx.ALIGN_CENTER_VERTICAL)

            field = InputField(self, 80, focus_receiver=parent)
            self._fields[axis] = field
            sizer.Add(field, 0, wx.ALIGN_CENTER_VERTICAL)
            field.set_popup_handler(get_popup_handler(field))
            field.add_popup_menu_item("use_rel_values", "Use relative values",
                                      get_rel_val_toggler(field), checkable=True)
            handler = get_value_handler(axis)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value((transf_type, not is_relative_value), handler=handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, handler=handler, font=font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

        sizer.Layout()

        self._axis_btns.disable()
        self.__enable_fields(False)
        self.__show_field_text(False)

        def update_axis_constraints(transf_type, axes):

            if transf_type:
                self._axis_btns.update_axis_constraints(transf_type, axes)

        def set_transform_type(transf_type):

            axis_btns = self._axis_btns

            if transf_type:

                self._transform_btns.set_active_button(transf_type)
                axis_btns.enable()

                if transf_type == "rotate":
                    axis_btns.disable_button("u")
                    axis_btns.disable_button("v")
                    axis_btns.get_button("w").set_active()
                else:
                    axis_btns.disable_button("w")
                    axes = GlobalData["uv_axis_constraints_%s" % transf_type]
                    axis_btns.update_axis_constraints(transf_type, axes)

                rel_values = GlobalData["rel_uv_transform_values"]
                is_rel_value = rel_values[self._uv_lvl][transf_type]
                value_id = (transf_type, is_rel_value)

                for field in self._fields.itervalues():
                    field.show_value(value_id)

                self.__check_selection_count(transf_type)

            else:

                self._transform_btns.deactivate()
                axis_btns.disable()
                self.__enable_fields(False)
                self.__show_field_text(False)

        Mgr.add_interface_updater("uv_window", "active_transform_type", set_transform_type)
        Mgr.add_interface_updater("uv_window", "axis_constraints", update_axis_constraints)
        Mgr.add_interface_updater("uv_window", "transform_values", self.__set_field_values)
        Mgr.add_interface_updater("uv_window", "selection_count", self.__check_selection_count)
        Mgr.add_interface_updater("uv_window", "uv_level", self.__set_uv_level)

    def setup(self):

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False), interface_id="uv_window")

    def __toggle_transform_handles(self, transf_type, shown):

        Mgr.update_interface_remotely("uv_window", "transform_handles",
                                      transf_type, shown)

    def __on_popup(self, field):

        transf_type, is_rel_value = field.get_value_id()
        field.check_popup_menu_item("use_rel_values", is_rel_value)

    def __toggle_relative_values(self, current_field):

        transf_type = self._transform_btns.get_active_button_id()
        uv_lvl = self._uv_lvl

        if uv_lvl in ("vert", "edge", "poly"):
            if not (uv_lvl == "vert" and transf_type == "translate"):
                return

        rel_values = GlobalData["rel_uv_transform_values"][uv_lvl]
        use_rel_values = not rel_values[transf_type]
        rel_values[transf_type] = use_rel_values

        for field in self._fields.itervalues():

            value_id = (transf_type, use_rel_values)
            field.show_value(value_id)

            if use_rel_values:
                value = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, value)

            if field is not current_field:
                field.check_popup_menu_item("use_rel_values", use_rel_values)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis, value_id, value):

        transf_type, is_rel_value = value_id
        Mgr.update_interface_remotely("uv_window", "transf_component", transf_type,
                                      axis, value, is_rel_value)

        if is_rel_value:
            self._fields[axis].set_value(value_id, 1. if transf_type == "scale" else 0.)

    def __set_field_values(self, transform_data=None):

        transf_type = GlobalData["active_uv_transform_type"]

        if not transform_data:

            if not (transf_type and GlobalData["rel_uv_transform_values"][self._uv_lvl][transf_type]):
                self.__show_field_text(False)

            return

        for transform_type, values in transform_data.iteritems():

            value_id = (transform_type, False)

            for axis, value in zip("uv", values):
                self._fields[axis].set_value(value_id, value)

        if transf_type:
            self.__show_field_text()

    def __set_field_text_color(self, color):

        for field in self._fields.itervalues():
            field.set_text_color(color)

    def __show_field_text(self, show=True):

        transf_type = GlobalData["active_uv_transform_type"]
        fields = self._fields

        for field in fields.itervalues():
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

        for field in fields.itervalues():
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

            color = wx.Colour(127, 127, 127)

            for field in self._fields.itervalues():
                field.set_text_color(color)

        else:

            for field in self._fields.itervalues():
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

        for field in self._fields.itervalues():
            field.show_value(value_id)

        self.__check_selection_count(transf_type)

    def enable(self):

        for combobox in self._comboboxes.itervalues():
            combobox.enable()

        self._transform_btns.enable()
        self._axis_btns.enable()
        self.__enable_fields()

    def disable(self, show=True):

        for combobox in self._comboboxes.itervalues():
            combobox.disable(show)

        self._transform_btns.disable(show)
        self._axis_btns.disable(show)
        self.__enable_fields(False)

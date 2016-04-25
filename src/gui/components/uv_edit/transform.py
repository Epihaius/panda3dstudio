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

            Mgr.set_global("active_uv_transform_type", "")
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

                Mgr.set_global("active_uv_transform_type", transf_type)
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

    def setup(self):
        pass

    def update_axis_constraints(self, transf_type, axes):

        for axis in "uvw":
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        self._axes[transf_type] = axes

        for axis in axes:
            self.get_button(axis).set_active()

    def __set_axis_constraint(self, axis):

        tt = Mgr.get_global("active_uv_transform_type")

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

        get_value_handler = lambda axis: lambda *args: self.__handle_value(axis, *args)

        for axis in "uvw":

            axis_btn = self._axis_btns.create_button(self, axis, parent)
            sizer.Add(axis_btn, 0, wx.ALIGN_CENTER_VERTICAL)

            field = InputField(self, 80, focus_receiver=parent)
            self._fields[axis] = field
            sizer.Add(field, 0, wx.ALIGN_CENTER_VERTICAL)
            handler = get_value_handler(axis)

            for transf_type in ("translate", "rotate", "scale"):
                field.add_value(transf_type, handler=handler)
                field.set_value(transf_type, 1. if transf_type == "scale" else 0.)

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
                    axes = Mgr.get_global("uv_axis_constraints_%s" % transf_type)
                    axis_btns.update_axis_constraints(transf_type, axes)

                for field in self._fields.itervalues():
                    field.show_value(transf_type)

                self.__check_selection_count(transf_type)

            else:

                self._transform_btns.deactivate()
                axis_btns.disable()
                self.__enable_fields(False)
                self.__show_field_text(False)

        Mgr.add_interface_updater("uv_window", "active_transform_type", set_transform_type)
        Mgr.add_interface_updater("uv_window", "axis_constraints", update_axis_constraints)
        Mgr.add_interface_updater("uv_window", "selection_count", self.__check_selection_count)

    def setup(self):

        self._axis_btns.setup()

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False), interface_id="uv_window")

    def __toggle_transform_handles(self, transf_type, shown):

        Mgr.update_interface_remotely("uv_window", "transform_handles",
                                      transf_type, shown)

    def __handle_value(self, axis, transf_type, value):

        Mgr.update_interface_remotely("uv_window", "transf_component", transf_type,
                                      axis, value)

        self._fields[axis].set_value(transf_type, 1. if transf_type == "scale" else 0.)

    def __set_field_text_color(self, color):

        for field in self._fields.itervalues():
            field.set_text_color(color)

    def __show_field_text(self, show=True):

        transf_type = Mgr.get_global("active_uv_transform_type")
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

        transf_type = Mgr.get_global("active_uv_transform_type")

        if enable and not (transf_type and Mgr.get_global("uv_selection_count")):
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

        tr_type = Mgr.get_global("active_uv_transform_type") if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = Mgr.get_global("uv_selection_count")
        self.__enable_fields(sel_count > 0)
        self.__show_field_text(sel_count > 0)

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

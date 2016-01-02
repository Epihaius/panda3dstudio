from ...base import *
from ...button import Button, ButtonGroup
from ...toggle import ToggleButtonGroup
from ...field import InputField
from ...combobox import ComboBox


class TransformButtons(ButtonGroup):

    def __init__(self, toolbar, focus_receiver=None):

        ButtonGroup.__init__(self)

        self._active_transforms = []

        btn_data = {
            "translate": ("icon_translate", "Select and translate"),
            "rotate": ("icon_rotate", "Select and rotate"),
            "scale": ("icon_scale", "Select and scale")
        }

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        def add_toggle(transf_type):

            icon_name, btn_tooltip = btn_data[transf_type]
            icon_path = os.path.join(GFX_PATH, icon_name + ".png")

            bitmaps = Button.create_button_bitmaps(
                icon_path, bitmap_paths, flat=True)
            command = lambda: self.__toggle_transform_type(transf_type)
            btn = Button(toolbar, bitmaps, "", btn_tooltip, command,
                         focus_receiver=focus_receiver)
            self.add_button(btn, transf_type)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)

        self.get_button("translate").set_hotkey((ord("W"), 0), "uv_window")
        self.get_button("rotate").set_hotkey((ord("E"), 0), "uv_window")
        self.get_button("scale").set_hotkey((ord("R"), 0), "uv_window")

        Mgr.add_interface_updater(
            "uv_window", "uv_transform_type", self.__update_transform_type)

    def __update_transform_type(self, transf_type=None, activate=True):

        if activate:

            if transf_type is None:

                self._active_transforms = transf_ids = [
                    "translate", "rotate", "scale"]

                for transf_id in transf_ids:
                    self.get_button(transf_id).set_active(activate)

            elif transf_type not in self._active_transforms:

                self.get_button(transf_type).set_active(activate)
                self._active_transforms.append(transf_type)

        else:

            if transf_type is None:

                for transf_id in self._active_transforms:
                    self.get_button(transf_id).set_active(activate)

                self._active_transforms = []

            elif transf_type in self._active_transforms:

                self.get_button(transf_type).set_active(activate)
                self._active_transforms.remove(transf_type)

    def __toggle_transform_type(self, transf_type):

        if transf_type in self._active_transforms:
            Mgr.update_interface(
                "uv_window", "uv_transform_type", transf_type, False)
        else:
            Mgr.update_interface(
                "uv_window", "uv_transform_type", transf_type, True)


class ExtraTransformButtons(ButtonGroup):

    def __init__(self, toolbar, focus_receiver=None):

        ButtonGroup.__init__(self)

        sizer = toolbar.GetSizer()

        for label in ("None", "All"):

            bitmap_paths = Button.get_bitmap_paths("toolbar_button")
            bitmaps = Button.create_button_bitmaps(
                "*%s" % label, bitmap_paths, flat=True)
            tooltip_label = "Select " + \
                ("only" if label == "None" else "and transform")
            get_command = lambda label: lambda: self.__toggle_transform_type(
                label)
            btn = Button(toolbar, bitmaps, label, tooltip_label, get_command(label),
                         focus_receiver=focus_receiver)
            self.add_button(btn, label.lower())
            sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

    def __toggle_transform_type(self, transf_type):

        if transf_type == "None":
            Mgr.update_interface("uv_window", "uv_transform_type", None, False)
        else:
            Mgr.update_interface("uv_window", "uv_transform_type", None, True)


class AxisButtons(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._axes = {"": ""}

    def setup(self):
        pass

    def update_axis_constraints(self, transf_type, axes):

        for axis in "UVW":
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        self._axes[transf_type] = axes

        for axis in axes:
            self.get_button(axis).set_active()

    def __set_axis_constraint(self, axis):

        tt = Mgr.get_global("active_transform_type")

        old_axes = self._axes[tt]

        if tt == "translate":

            if len(self._axes[tt]) == 1:
                if axis == self._axes[tt]:
                    self._axes[tt] = "XYZ".replace(axis, "")
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

    def create_button(self, toolbar, axis, focus_receiver=None):

        icon_name = "icon_%s" % axis.lower()
        icon_path = os.path.join(GFX_PATH, icon_name + ".png")
        bitmap_paths = Button.get_bitmap_paths("toolbar_button")
        bitmaps = Button.create_button_bitmaps(
            icon_path, bitmap_paths, flat=True)
        tooltip_label = "Transform about %s" % axis
        btn = Button(toolbar, bitmaps, "", tooltip_label, lambda: self.__set_axis_constraint(axis),
                     focus_receiver=focus_receiver)
        btn.set_hotkey((ord(axis), 0), "uv_window")
        self.add_button(btn, axis)

        return btn


class TransformToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width, focus_receiver=parent)

        sizer = self.GetSizer()

        self._extra_transform_btns = ExtraTransformButtons(self, parent)
        self._transform_btns = TransformButtons(self, parent)

        for transf_type in ("translate", "rotate", "scale"):
            btn = self._transform_btns.get_button(transf_type)
            sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        sizer.AddSpacer(10)
        self._axis_btns = AxisButtons()
        self._fields = {}

        get_rel_val_toggler = lambda field: lambda: self.__toggle_relative_values(
            field)
        get_popup_handler = lambda field: lambda: self.__on_popup(field)
        get_value_handler = lambda axis: lambda value_id, value: self.__handle_value(
            axis, value_id, value)

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        is_relative_value = True

        for axis in "UVW":

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
                field.add_value(
                    (transf_type, not is_relative_value), handler=handler)
                value_id = (transf_type, is_relative_value)
                field.add_value(value_id, handler=handler, font=font)
                field.set_value(value_id, 1. if transf_type == "scale" else 0.)

        sizer.Layout()

        self._axis_btns.disable()
        self.__enable_fields(False)
        self.__show_field_text(False)

        def disable_transforms(show=True):

            self._transform_btns.deactivate()
            self.disable(show)

        def update_axis_constraints(transf_type, axes):

            if transf_type:
                self._axis_btns.update_axis_constraints(transf_type, axes)

        def set_transform_type(transf_type):

            if transf_type:

                self._transform_btns.set_active_button(transf_type)
                self._axis_btns.enable()
                axes = Mgr.get_global("axis_constraints_%s" % transf_type)
                self._axis_btns.update_axis_constraints(transf_type, axes)
                is_rel_value = Mgr.get_global(
                    "using_rel_%s_values" % transf_type)

                for field in self._fields.itervalues():
                    field.show_value((transf_type, is_rel_value))

                self.__check_selection_count(transf_type)

                if Mgr.get_global("selection_count") == 1:
                    self.__show_field_text()

            else:

                self._transform_btns.deactivate()
                self._axis_btns.disable()
                self.__enable_fields(False)
                self.__show_field_text(False)

    def setup(self):

        self._axis_btns.setup()

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False),
                  interface_id="uv_window")

    def __on_popup(self, field):

        transf_type, is_rel_value = field.get_value_id()
        field.check_popup_menu_item("use_rel_values", is_rel_value)

    def __toggle_relative_values(self, current_field):

        transf_type = self._transform_btns.get_active_button_id()

        use_rel_value = not Mgr.get_global("using_rel_%s_values" % transf_type)
        Mgr.set_global("using_rel_%s_values" % transf_type, use_rel_value)

        for field in self._fields.itervalues():

            field.show_value((transf_type, use_rel_value))

            if field is not current_field:
                field.check_popup_menu_item("use_rel_values", use_rel_value)

    def __handle_value(self, axis, value_id, value):

        transf_type, is_rel_value = value_id
        Mgr.update_remotely("transf_component", transf_type,
                            axis, value, is_rel_value)

        if is_rel_value:
            self._fields[axis].set_value(
                value_id, 1. if transf_type == "scale" else 0.)

    def __set_field_values(self, transform_data=None):

        if not transform_data:

            self.__show_field_text(False)

            return

        for transform_type, values in transform_data.iteritems():
            for axis, value in zip("XYZ", values):
                self._fields[axis].set_value((transform_type, False), value)

        if Mgr.get_global("active_transform_type"):
            self.__show_field_text()

    def __set_field_text_color(self, color):

        for field in self._fields.itervalues():
            field.set_text_color(color)

    def __show_field_text(self, show=True):

        for field in self._fields.itervalues():
            field.show_text(show)

    def __enable_fields(self, enable=True):

        if enable and not (Mgr.get_global("active_transform_type")
                           and Mgr.get_global("selection_count")):
            return

        for field in self._fields.itervalues():
            field.enable(enable)

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

    def deactivate(self):

        self._transform_btns.deactivate()

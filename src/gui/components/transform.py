from ..base import *
from ..button import Button, ButtonGroup
from ..toggle import ToggleButtonGroup
from ..field import InputField
from ..combobox import ComboBox


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            Mgr.set_global("active_transform_type", "")
            Mgr.update_app("active_transform_type", "")
            Mgr.update_app("status", "select", "")

        self.set_default_toggle("", (toggle_on_default, lambda: None))

        btn_data = {
            "translate": ("icon_translate", "Select and translate"),
            "rotate": ("icon_rotate", "Select and rotate"),
            "scale": ("icon_scale", "Select and scale")
        }

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        def add_toggle(transf_type):

            def toggle_on():

                Mgr.enter_state("selection_mode")
                Mgr.set_global("active_transform_type", transf_type)
                Mgr.update_app("active_transform_type", transf_type)
                Mgr.update_app("status", "select", transf_type, "idle")

            toggle = (toggle_on, lambda: None)
            icon_name, btn_tooltip = btn_data[transf_type]
            icon_path = os.path.join(GFX_PATH, icon_name + ".png")

            bitmaps = Button.create_button_bitmaps(
                icon_path, bitmap_paths, flat=True)
            btn = self.add_button(toolbar, transf_type,
                                  toggle, bitmaps, btn_tooltip)

        for transf_type in ("translate", "rotate", "scale"):
            add_toggle(transf_type)

        self.get_button("translate").set_hotkey((ord("W"), 0))
        self.get_button("rotate").set_hotkey((ord("E"), 0))
        self.get_button("scale").set_hotkey((ord("R"), 0))


class AxisButtons(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._axes = {"": ""}

        Mgr.accept("enable_axis_constraints", self.enable)
        Mgr.accept("disable_axis_constraints", self.disable)

    def setup(self):

        for transf_type in ("translate", "rotate", "scale"):
            self._axes[transf_type] = Mgr.get_global(
                "axis_constraints_%s" % transf_type)

    def update_axis_constraints(self, transf_type, axes):

        for axis in "XYZ":
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        if axes in ("screen", "trackball"):
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

    def create_button(self, toolbar, axis):

        icon_name = "icon_%s" % axis.lower()
        icon_path = os.path.join(GFX_PATH, icon_name + ".png")
        bitmap_paths = Button.get_bitmap_paths("toolbar_button")
        bitmaps = Button.create_button_bitmaps(
            icon_path, bitmap_paths, flat=True)
        tooltip_label = "Transform about %s" % axis
        btn = Button(toolbar, bitmaps, "", tooltip_label,
                     lambda: self.__set_axis_constraint(axis))
        btn.set_hotkey((ord(axis), 0))
        self.add_button(btn, axis)

        return btn


class CoordSysComboBox(ComboBox):

    def __init__(self, toolbar):

        icon_path = os.path.join(GFX_PATH, "icon_coordsys.png")
        bitmap_paths = ComboBox.get_bitmap_paths("toolbar_button")
        bitmaps = ComboBox.create_button_bitmaps(
            icon_path, bitmap_paths, 148, flat=True)
        btn_data = (toolbar, bitmaps, "", "Coordinate system")

        ComboBox.__init__(self, btn_data, active_tint=(.8, 1.8, 1.8))

        def add_coord_sys_entry(cs_type, label):

            if cs_type == "object":

                def start_coord_sys_picking():

                    self.select_item(cs_type)
                    Mgr.enter_state("coord_sys_picking_mode")

                self.add_item(cs_type, label,
                              start_coord_sys_picking, persistent=True)

            else:

                def set_coord_sys():

                    Mgr.exit_state("coord_sys_picking_mode")
                    Mgr.update_app("coord_sys", cs_type)

                self.add_item(cs_type, label, set_coord_sys)

        for cs in (
            ("world", "World"), ("screen", "Screen"), ("local", "Local"),
            ("object", "Pick object...")
        ):
            add_coord_sys_entry(*cs)

        Mgr.accept("enable_coord_sys_control", self.enable)
        Mgr.accept("disable_coord_sys_control", self.disable)

        Mgr.add_app_updater("coord_sys", self.__update)

    def __update(self, coord_sys_type, obj_name=""):

        self.select_item(coord_sys_type)

        if coord_sys_type == "object":
            self.set_label(obj_name)


class TransfCenterComboBox(ComboBox):

    def __init__(self, toolbar):

        icon_path = os.path.join(GFX_PATH, "icon_transf_center.png")
        bitmap_paths = ComboBox.get_bitmap_paths("toolbar_button")
        bitmaps = ComboBox.create_button_bitmaps(
            icon_path, bitmap_paths, 148, flat=True)
        btn_data = (toolbar, bitmaps, "", "Transform center")

        ComboBox.__init__(self, btn_data, active_tint=(.8, 1.8, 1.8))

        def add_transf_center_type(tc_type, label):

            if tc_type == "object":

                def start_transf_center_picking():

                    self.select_item(tc_type)
                    Mgr.enter_state("transf_center_picking_mode")

                self.add_item(tc_type, label,
                              start_transf_center_picking, persistent=True)

            else:

                def set_transf_center():

                    Mgr.exit_state("transf_center_picking_mode")
                    Mgr.update_app("transf_center", tc_type)

                self.add_item(tc_type, label, set_transf_center)

        for tc in (
            ("sel_center", "Selection Center"), ("local_origin", "Local Origin"),
            ("cs_origin", "Coord Sys Origin"), ("object", "Pick object...")
        ):
            add_transf_center_type(*tc)

        Mgr.add_app_updater("transf_center", self.__update)

    def __update(self, transf_center_type, obj_name=""):

        self.select_item(transf_center_type)

        if transf_center_type == "object":
            self.set_label(obj_name)


class TransformToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width)

        sizer = self.GetSizer()

        self._transform_btns = TransformButtons(self)

        for transf_type in ("translate", "rotate", "scale"):
            btn = self._transform_btns.get_button(transf_type)
            sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        sizer.AddSpacer(10)
        self._axis_btns = AxisButtons()
        self._axis_btns.add_disabler(
            "no_transf", lambda: not Mgr.get_global("active_transform_type"))
        self._fields = {}

        get_rel_val_toggler = lambda field: lambda: self.__toggle_relative_values(
            field)
        get_popup_handler = lambda field: lambda: self.__on_popup(field)
        get_value_handler = lambda axis: lambda value_id, value: self.__handle_value(
            axis, value_id, value)

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)
        is_relative_value = True

        for axis in "XYZ":

            axis_btn = self._axis_btns.create_button(self, axis)
            sizer.Add(axis_btn, 0, wx.ALIGN_CENTER_VERTICAL)

            field = InputField(self, 80)
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

        self._comboboxes = {}

        sizer.AddSpacer(10)
        combobox = CoordSysComboBox(self)
        self._comboboxes["coord_sys"] = combobox
        sizer.Add(combobox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        combobox = TransfCenterComboBox(self)
        self._comboboxes["transf_center"] = combobox
        sizer.Add(combobox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
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

        Mgr.accept("enable_transforms", self.enable)
        Mgr.accept("disable_transforms", disable_transforms)

        Mgr.add_app_updater("active_transform_type", set_transform_type)
        Mgr.add_app_updater("axis_constraints", update_axis_constraints)
        Mgr.add_app_updater("transform_values", self.__set_field_values)
        Mgr.add_app_updater("selection_count", self.__check_selection_count)

    def setup(self):

        self._axis_btns.setup()

        add_state = Mgr.add_state
        add_state("transforming", -1, lambda prev_state_id, is_active:
                  Mgr.do("disable_components", show=False))

        def add_picking_mode(picking_type):

            state_id = "%s_picking_mode" % picking_type

            def enter_picking_mode(prev_state_id, is_active):

                self._comboboxes[picking_type].set_field_active()
                Mgr.do("set_viewport_border_color", (0, 255, 255))

            def exit_picking_mode(next_state_id, is_active):

                if not is_active:
                    self._comboboxes[picking_type].set_field_active(False)

            add_state(state_id, -80, enter_picking_mode, exit_picking_mode)

        for picking_type in ("coord_sys", "transf_center"):
            add_picking_mode(picking_type)

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

    def __check_selection_count(self, transf_type=None):

        tr_type = Mgr.get_global(
            "active_transform_type") if transf_type is None else transf_type

        if not tr_type:
            return

        sel_count = Mgr.get_global("selection_count")
        self.__enable_fields(sel_count > 0)

        if sel_count > 1:

            color = wx.Colour(127, 127, 127)

            for field in self._fields.itervalues():
                field.set_text_color(color)

        else:

            for field in self._fields.itervalues():
                field.set_text_color()

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

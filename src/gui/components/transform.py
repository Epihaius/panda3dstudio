from ..base import *
from ..button import *
from ..toolbar import *
from ..dialog import *


class TransformButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        def toggle_on_default():

            GlobalData["active_transform_type"] = ""
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
                GlobalData["active_transform_type"] = transf_type
                Mgr.update_app("active_transform_type", transf_type)

                if GlobalData["snap"]["on"][transf_type]:
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
            self.get_button(axis).set_active(False)

        if not transf_type:
            return

        if axes in ("view", "trackball"):
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
        tooltip_text = "Transform about {}-axis".format(axis.upper())
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

        def add_coord_sys_entry(cs_type, text):

            if cs_type == "object":

                def start_coord_sys_picking():

                    if GlobalData["active_obj_level"] != "top":
                        GlobalData["active_obj_level"] = "top"
                        Mgr.update_app("active_obj_level")

                    Mgr.enter_state("coord_sys_picking_mode")
                    self.select_none()
                    self.select_item(cs_type)

                self.add_item(cs_type, text, start_coord_sys_picking, persistent=True)

            elif cs_type == "snap_pt":

                def enter_snap_mode():

                    Mgr.enter_state("coord_origin_snap_mode")
                    self.select_none()
                    self.select_item(cs_type)
                    Mgr.update_locally("object_snap", "enable", True, True)

                self.add_item(cs_type, text, enter_snap_mode, persistent=True)

            else:

                def set_coord_sys():

                    Mgr.exit_state("coord_sys_picking_mode")
                    Mgr.exit_state("coord_origin_snap_mode")
                    Mgr.update_app("coord_sys", cs_type)

                self.add_item(cs_type, text, set_coord_sys)

        for cs in (
            ("world", "World"), ("view", "View"), ("local", "Local"),
            ("object", "Pick object..."), ("snap_pt", "Snap to point...")
        ):
            add_coord_sys_entry(*cs)

        self.update_popup_menu()

        Mgr.add_app_updater("coord_sys", self.__update)

    def __update(self, coord_sys_type, obj_name=None):

        self.select_item(coord_sys_type)

        if coord_sys_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("coord_sys", self.set_text)
        elif coord_sys_type == "snap_pt":
            self.set_text("Custom")


class TransfCenterComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        icon_id = "icon_transf_center"
        tooltip_text = "Transform center"

        ToolbarComboBox.__init__(self, toolbar, 100, icon_id=icon_id, tooltip_text=tooltip_text)

        def add_transf_center_type(tc_type, text):

            if tc_type == "object":

                def start_transf_center_picking():

                    if GlobalData["active_obj_level"] != "top":
                        GlobalData["active_obj_level"] = "top"
                        Mgr.update_app("active_obj_level")

                    Mgr.enter_state("transf_center_picking_mode")
                    self.select_none()
                    self.select_item(tc_type)

                self.add_item(tc_type, text, start_transf_center_picking, persistent=True)

            elif tc_type == "snap_pt":

                def enter_snap_mode():

                    Mgr.enter_state("transf_center_snap_mode")
                    self.select_none()
                    self.select_item(tc_type)
                    Mgr.update_locally("object_snap", "enable", True, True)

                self.add_item(tc_type, text, enter_snap_mode, persistent=True)

            else:

                def set_transf_center():

                    Mgr.exit_state("transf_center_picking_mode")
                    Mgr.exit_state("transf_center_snap_mode")
                    Mgr.update_app("transf_center", tc_type)

                self.add_item(tc_type, text, set_transf_center)

        for tc in (
            ("adaptive", "Adaptive"), ("sel_center", "Selection center"),
            ("pivot", "Pivot"), ("cs_origin", "Ref. coord. origin"),
            ("object", "Pick object..."), ("snap_pt", "Snap to point...")
        ):
            add_transf_center_type(*tc)

        self.update_popup_menu()

        Mgr.add_app_updater("transf_center", self.__update)

    def __update(self, transf_center_type, obj_name=None):

        self.select_item(transf_center_type)

        if transf_center_type == "object":
            self.set_text(obj_name.get_value())
            obj_name.add_updater("transf_center", self.set_text)
        elif transf_center_type == "snap_pt":
            self.set_text("Custom point")


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

        get_value_handler = lambda axis: lambda value_id, value, state: \
            self.__handle_value(axis, value_id, value, state)

        font = Skin["text"]["input2"]["font"]
        is_relative_value = True
        btn_disabler = lambda: not GlobalData["active_transform_type"]
        self._axis_btns.add_disabler("no_transf", btn_disabler)
        field_disabler = lambda: not (GlobalData["active_transform_type"] and GlobalData["selection_count"])

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
        tooltip_text = "Use relative values (offsets)"
        btn = ToolbarButton(self, "", icon_id, tooltip_text, self.__toggle_relative_values)
        btn.add_disabler("no_transf", btn_disabler)
        self._offsets_btn = btn
        self.add(btn, borders=borders, alignment="center_v")

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
        self._offsets_btn.set_active(False)
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
                axes = GlobalData["axis_constraints"][transf_type]
                self._axis_btns.update_axis_constraints(transf_type, axes)
                obj_lvl = GlobalData["active_obj_level"]
                is_rel_value = GlobalData["rel_transform_values"][obj_lvl][transf_type]
                value_id = (transf_type, is_rel_value)

                for field in self._fields.values():
                    field.show_value(value_id)

                self._offsets_btn.enable(True)
                self._offsets_btn.set_active(is_rel_value)
                self.__check_selection_count(transf_type)
                GlobalData["snap"]["type"] = transf_type
                Mgr.update_locally("object_snap", "enable", True, False)

            else:

                self._transform_btns.deactivate()
                self._axis_btns.enable(False)
                self.__enable_fields(False)
                self.__show_field_text(False)
                self._offsets_btn.set_active(False)
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

        def add_snap_mode(snap_type):

            state_id = "{}_snap_mode".format(snap_type)

            def enter_snap_mode(prev_state_id, is_active):

                tint = Skin["colors"]["combobox_field_tint_pick"]
                combobox_id = "coord_sys" if snap_type == "coord_origin" else snap_type
                self._comboboxes[combobox_id].set_field_tint(tint)
                Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

                if not is_active:
                    GlobalData["snap"]["prev_type"] = GlobalData["snap"]["type"]
                    GlobalData["snap"]["type"] = snap_type

            def exit_snap_mode(next_state_id, is_active):

                if not is_active:
                    combobox_id = "coord_sys" if snap_type == "coord_origin" else snap_type
                    self._comboboxes[combobox_id].set_field_tint(None)
                    Mgr.update_locally("object_snap", "enable", False, True)
                    GlobalData["snap"]["type"] = GlobalData["snap"]["prev_type"]

            add_state(state_id, -80, enter_snap_mode, exit_snap_mode)

        for snap_type in ("coord_origin", "transf_center"):
            add_snap_mode(snap_type)

    def __show_options_dialog(self):

        TransformOptionsDialog()

    def __update_offset_btn(self):

        transf_type = self._transform_btns.get_active_button_id()

        if transf_type:
            obj_lvl = GlobalData["active_obj_level"]
            is_rel_value = GlobalData["rel_transform_values"][obj_lvl][transf_type]
            self._offsets_btn.set_active(is_rel_value)

    def __toggle_relative_values(self):

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
        self._offsets_btn.set_active(use_rel_values)

        for field in self._fields.values():

            field.show_value(value_id)

            if use_rel_values:
                field.show_text()
                val = 1. if transf_type == "scale" else 0.
                field.set_value(value_id, val)

        self.__check_selection_count(transf_type)

    def __handle_value(self, axis, value_id, value, state):

        transf_type, is_rel_value = value_id
        Mgr.update_remotely("transf_component", transf_type, axis, value, is_rel_value)

        if is_rel_value:
            val = 1. if transf_type == "scale" else 0.
            self._fields[axis].set_value(value_id, val)

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
                self._fields[axis].set_value(value_id, value)

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


class ValueInputField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, value_id, value_type, handler, width):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, value_id, value_type, handler, width,
                                  INSET1_BORDER_GFX_DATA, self._img_offset)

    def get_outer_borders(self):

        return self._field_borders


class AngleField(DialogSliderField):

    def __init__(self, parent, value_id, value_range, handler, parser, width):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        self._field_borders = (l, r, b, t)
        img_offset = (-l, -t)

        DialogSliderField.__init__(self, parent, value_id, "float", value_range, handler,
                                   width, INSET1_BORDER_GFX_DATA, img_offset)

        self._parser = parser
        self.set_input_parser(self.__parse_angle_input)
        self.set_value(0.)

    def get_outer_borders(self):

        return self._field_borders

    def __parse_angle_input(self, input_text):

        try:
            return self._parser(input_text)
        except:
            return None


class TransformDialog(Dialog):

    def __init__(self):

        transf_type = GlobalData["active_transform_type"]
        title = '{} selection'.format(transf_type.title())
        on_cancel = lambda: Mgr.update_remotely("componentwise_xform", "cancel")
        extra_button_data = (("Apply", "", self.__on_apply, None, 1.),)

        Dialog.__init__(self, title, "okcancel", transf_type.title(), self.__on_yes,
                        on_cancel=on_cancel, extra_button_data=extra_button_data)

        value = 1. if transf_type == "scale" else 0.
        rot_axis = GlobalData["axis_constraints"]["rotate"]
        self._rot_axis = "z" if rot_axis == "view" else rot_axis
        self._values = values = {axis_id: value for axis_id in "xyz"}
        self._link_values = True if transf_type == "scale" else False
        self._linked_axes = "xyz"
        self._preview = True
        self._fields = fields = {}

        client_sizer = self.get_client_sizer()

        if transf_type == "rotate":

            subsizer = Sizer("horizontal")
            borders = (20, 20, 0, 20)
            client_sizer.add(subsizer, expand=True, borders=borders)

            self._toggle_btns = btns = ToggleButtonGroup()
            borders = (0, 5, 0, 0)

            def add_toggle(axis_id):

                def toggle_on():

                    self._toggle_btns.set_active_button(axis_id)
                    value = values[self._rot_axis]
                    self._rot_axis = axis_id
                    values[self._rot_axis] = value

                    for other_axis_id in "xyz".replace(self._rot_axis, ""):
                        values[other_axis_id] = 0.

                    if self._preview:
                        Mgr.update_remotely("componentwise_xform", "", values)

                toggle = (toggle_on, lambda: None)
                axis_text = axis_id.upper()
                tooltip_text = "Rotate about {}-axis".format(axis_text)
                btn = DialogButton(self, axis_text, tooltip_text=tooltip_text)
                btns.add_button(btn, axis_id, toggle)
                subsizer.add(btn, alignment="center_v", borders=borders)

            for axis_id in "xyz":
                add_toggle(axis_id)

            btns.set_active_button(self._rot_axis)

            borders = (5, 0, 0, 0)
            text = DialogText(self, "Offset angle:")
            subsizer.add(text, alignment="center_v", borders=borders)
            parser = lambda input_text: (float(eval(input_text)) + 180.) % 360. - 180.
            field = AngleField(self, "rot_axis", (-180., 180.), self.__handle_value, parser, 100)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        else:

            main_sizer = Sizer("horizontal")
            borders = (20, 20, 0, 0)
            client_sizer.add(main_sizer, expand=True, borders=borders)

            subsizer = Sizer("vertical")
            borders = (0, 10, 0, 0)
            main_sizer.add(subsizer, expand=True, borders=borders)

            subsizer.add((0, 0), proportion=1.)

            self._toggle_btns = btns = ToggleButtonGroup()

            def unlink_values():

                self._toggle_btns.deactivate()
                self._link_values = False

            btns.set_default_toggle("", (unlink_values, lambda: None))
            borders = (0, 0, 5, 0)

            def add_toggle(axes):

                def toggle_on():

                    self._toggle_btns.set_active_button(axes)
                    self._link_values = True
                    self._linked_axes = axes

                    val_to_copy = values[axes[0]]
                    change = False

                    for axis_id in axes[1:]:
                        if values[axis_id] != val_to_copy:
                            values[axis_id] = val_to_copy
                            fields[axis_id].set_value(val_to_copy)
                            change = True

                    if change and self._preview:
                        Mgr.update_remotely("componentwise_xform", "", values)

                toggle = (toggle_on, lambda: None)
                text = "=".join(axes.upper())
                axes_descr = "all" if axes == "xyz" else " and ".join(axes.upper())
                tooltip_text = "Make {} values equal".format(axes_descr)
                btn = DialogButton(self, text, tooltip_text=tooltip_text)
                btns.add_button(btn, axes, toggle)
                subsizer.add(btn, expand=True, borders=borders)

            for axes in ("xyz", "xy", "yz", "xz"):
                add_toggle(axes)

            if transf_type == "scale":
                btns.set_active_button("xyz")

            subsizer.add((0, 0), proportion=1.)

            group_title = "Offset {}".format("factors" if transf_type == "scale" else "distances")
            group = DialogWidgetGroup(self, group_title)
            borders = (0, 0, 10, 10)
            main_sizer.add(group, proportion=1., borders=borders)
            value = 1. if transf_type == "scale" else 0.

            for axis_id in "xyz":

                subsizer = Sizer("horizontal")
                borders = (0, 0, 5, 0)
                group.add(subsizer, expand=True, borders=borders)

                text = DialogText(group, "{}:".format(axis_id.upper()))
                subsizer.add(text, alignment="center_v")
                field = ValueInputField(group, axis_id, "float", self.__handle_value, 100)
                field.set_value(value)
                borders = (5, 0, 0, 0)
                subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
                fields[axis_id] = field

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("componentwise_xform", "", values, "done", preview, not preview)

        text = "Preview"
        checkbtn = DialogCheckButton(self, enable_preview, text)
        checkbtn.check()
        borders = (20, 20, 15, 20)
        client_sizer.add(checkbtn, borders=borders)

        self.finalize()

    def close(self, answer=""):

        self._fields = None
        self._toggle_btns = None

        Dialog.close(self, answer)

    def __handle_value(self, axis_id, value, state):

        if axis_id == "rot_axis":

            self._values[self._rot_axis] = value

            for other_axis_id in "xyz".replace(self._rot_axis, ""):
                self._values[other_axis_id] = 0.

        else:

            self._values[axis_id] = value

            if self._link_values and axis_id in self._linked_axes:
                for other_axis_id in self._linked_axes.replace(axis_id, ""):
                    self._values[other_axis_id] = value
                    self._fields[other_axis_id].set_value(value)

        if self._preview:
            Mgr.update_remotely("componentwise_xform", "", self._values, state)

    def __on_yes(self):

        Mgr.update_remotely("componentwise_xform", "", self._values, "done", False)

    def __on_apply(self):

        Mgr.update_remotely("componentwise_xform", "", self._values, "done", False)

        if self._preview:
            Mgr.update_remotely("componentwise_xform", "", self._values)


class TransformOptionsDialog(Dialog):

    def __init__(self):

        old_options = GlobalData["transform_options"]
        old_rot_options = old_options["rotation"]
        self._options = new_options = {}
        new_options["rotation"] = new_rot_options = {}

        for option_id in ("drag_method", "alt_method", "method_switch_threshold",
                "show_circle", "circle_center", "circle_radius", "scale_circle_to_cursor",
                "show_line", "line_thru_gizmo_center", "full_roll_dist"):
            new_rot_options[option_id] = old_rot_options[option_id]

        Dialog.__init__(self, "Transform options", "okcancel", on_yes=self.__on_yes)

        client_sizer = self.get_client_sizer()

        group = DialogWidgetGroup(self, "Rotation")
        borders = (20, 20, 20, 10)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        borders = (5, 5, 10, 0)
        group.add(subsizer, expand=True, borders=borders)

        text = DialogText(group, "Interactive dragging method:")
        borders = (0, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        combobox = DialogComboBox(group, 150, tooltip_text="Drag method")
        subsizer.add(combobox, alignment="center_v", proportion=1.)

        def get_command(method_id):

            def command():

                combobox.select_item(method_id)
                new_rot_options["drag_method"] = method_id

            return command

        method_ids = ("circular_in_rot_plane", "circular_in_view_plane", "linear")
        method_names = ("circular in rotation plane", "circular in view plane", "linear")

        for method_id, method_name in zip(method_ids, method_names):
            combobox.add_item(method_id, method_name, get_command(method_id))

        combobox.update_popup_menu()
        combobox.select_item(old_rot_options["drag_method"])

        subsizer = Sizer("horizontal")
        borders = (5, 5, 5, 0)
        group.add(subsizer, expand=True, borders=borders)

        text = DialogText(group, "View-aligned circle center:")
        borders = (0, 10, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        radio_btns = DialogRadioButtonGroup(group, rows=1, gap_h=10, stretch=True)

        def get_command(center_id):

            def command():

                new_rot_options["circle_center"] = center_id

            return command

        center_ids = ("start_click_pos", "gizmo_center")
        center_names = ("start click pos.", "transf. gizmo center")

        for center_id, center_name in zip(center_ids, center_names):
            radio_btns.add_button(center_id, center_name)
            radio_btns.set_button_command(center_id, get_command(center_id))

        radio_btns.set_selected_button(old_rot_options["circle_center"])
        subsizer.add(radio_btns.get_sizer(), proportion=1.)

        subgroup = DialogWidgetGroup(group, "Display")
        borders = (5, 5, 0, 10)
        group.add(subgroup, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        borders = (5, 5, 5, 0)
        subgroup.add(subsizer, expand=True, borders=borders)

        def show_viz(show):

            new_rot_options["show_circle"] = show

        text = "View-aligned circle"
        checkbtn = DialogCheckButton(subgroup, show_viz, text)
        checkbtn.check(old_rot_options["show_circle"])
        subsizer.add(checkbtn, alignment="center_v")

        text = DialogText(subgroup, "Radius:")
        borders = (20, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        field = ValueInputField(subgroup, "radius", "int", self.__handle_value, 50)
        field.set_input_parser(self.__parse_input)
        field.set_value(old_rot_options["circle_radius"])
        subsizer.add(field, alignment="center_v")

        def scale_to_cursor(to_cursor):

            new_rot_options["scale_circle_to_cursor"] = to_cursor

        text = "Scale to cursor"
        checkbtn = DialogCheckButton(subgroup, scale_to_cursor, text)
        checkbtn.check(old_rot_options["scale_circle_to_cursor"])
        borders = (20, 0, 0, 0)
        subsizer.add(checkbtn, alignment="center_v", borders=borders)

        subsizer = Sizer("horizontal")
        borders = (5, 5, 5, 0)
        subgroup.add(subsizer, expand=True, borders=borders)

        def show_viz(show):

            new_rot_options["show_line"] = show

        text = "Line"
        checkbtn = DialogCheckButton(subgroup, show_viz, text)
        checkbtn.check(old_rot_options["show_line"])
        subsizer.add(checkbtn, alignment="center_v")

        def thru_gizmo_center(thru_gizmo):

            new_rot_options["line_thru_gizmo_center"] = thru_gizmo

        text = "Through gizmo center"
        checkbtn = DialogCheckButton(subgroup, thru_gizmo_center, text)
        checkbtn.check(old_rot_options["line_thru_gizmo_center"])
        borders = (20, 0, 0, 0)
        subsizer.add(checkbtn, alignment="center_v", borders=borders)

        text = DialogText(subgroup, "Full rotation:")
        borders = (20, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        option_id = "full_roll_dist"
        field = ValueInputField(subgroup, option_id, "int", self.__handle_value, 50)
        field.set_input_parser(self.__parse_input)
        field.set_value(old_rot_options[option_id])
        subsizer.add(field, alignment="center_v")

        text = DialogText(subgroup, "pixels")
        borders = (5, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        subgroup = DialogWidgetGroup(group, "Auto-switch method")
        borders = (5, 5, 5, 10)
        group.add(subgroup, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        borders = (5, 5, 0, 0)
        subgroup.add(subsizer, expand=True, borders=borders)

        text = DialogText(subgroup, "Alternative method:")
        borders = (0, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        radio_btns = DialogRadioButtonGroup(subgroup, rows=1, gap_h=10, stretch=True)

        def get_command(method_id):

            def command():

                new_rot_options["alt_method"] = method_id

            return command

        for method_id, method_name in zip(method_ids[1:], method_names[1:]):
            radio_btns.add_button(method_id, method_name)
            radio_btns.set_button_command(method_id, get_command(method_id))

        radio_btns.set_selected_button(old_rot_options["alt_method"])
        subsizer.add(radio_btns.get_sizer(), proportion=1.)

        subsizer = Sizer("horizontal")
        borders = (5, 5, 5, 10)
        subgroup.add(subsizer, expand=True, borders=borders)

        text = DialogText(subgroup, "Threshold angle:")
        borders = (0, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        parser = lambda input_text: max(0., min(91., float(eval(input_text))))
        field = AngleField(subgroup, "threshold", (0., 91.), self.__handle_value, parser, 100)
        field.set_value(old_rot_options["method_switch_threshold"])
        subsizer.add(field, proportion=1., alignment="center_v")

        text = DialogText(subgroup, "degrees")
        borders = (5, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        self.finalize()

    def __parse_input(self, input_text):

        try:
            return max(1, abs(int(eval(input_text))))
        except:
            return None

    def __handle_value(self, value_id, value, state):

        if value_id == "radius":
            self._options["rotation"]["circle_radius"] = value
        elif value_id == "full_roll_dist":
            self._options["rotation"]["full_roll_dist"] = value
        elif value_id == "threshold":
            self._options["rotation"]["method_switch_threshold"] = value

    def __on_yes(self):

        old_options = GlobalData["transform_options"]
        old_rot_options = old_options["rotation"]
        new_options = self._options
        new_rot_options = new_options["rotation"]

        for option_id in ("drag_method", "alt_method", "method_switch_threshold",
                "show_circle", "circle_center", "circle_radius", "scale_circle_to_cursor",
                "show_line", "line_thru_gizmo_center", "full_roll_dist"):
            old_rot_options[option_id] = new_rot_options[option_id]

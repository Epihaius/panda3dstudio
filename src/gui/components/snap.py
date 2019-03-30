from ..base import *
from ..button import *
from ..toolbar import *
from ..dialog import *


class SnapButton(ToolbarButton):

    def __init__(self, toolbar):

        tooltip_text = "Enable snapping"
        command = lambda: Mgr.update_locally("object_snap", "snap")

        ToolbarButton.__init__(self, toolbar, "", "icon_snap", tooltip_text, command)

        hotkey = ("s", 0)
        self.set_hotkey(hotkey, "S")


class OptionsButton(ToolbarButton):

    def __init__(self, toolbar):

        tooltip_text = "Set snap options"
        ToolbarButton.__init__(self, toolbar, "", "icon_snap_options",
                               tooltip_text, lambda: SnapDialog())


class SnapToolbar(Toolbar):

    def __init__(self, parent, toolbar_id, name):

        Toolbar.__init__(self, parent, toolbar_id, name)

        self._btns = btns = {}
        borders = (0, 5, 0, 0)
        btn = SnapButton(self)
        btn.enable(False)
        self.add(btn, borders=borders, alignment="center_v")
        btns["snap"] = btn
        btn = OptionsButton(self)
        btn.enable(False)
        self.add(btn, borders=borders, alignment="center_v")
        btns["snap_options"] = btn
        tools_menu = Mgr.get("main_gui_components")["main_context_tools_menu"]
        item = tools_menu.add("snap", "Snap", self._btns["snap"].press, item_type="check")
        item.enable(False)
        self._tools_menu_item = item
        tools_menu = Mgr.get("tool_options_menu")
        item = tools_menu.add("snap", "Snap", lambda: self.__update_snapping("show_options"))
        item.enable(False)
        self._tool_options_menu_item = item

        Mgr.add_app_updater("object_snap", self.__update_snapping)

    def setup(self):

        def enter_transf_start_snap_mode(prev_state_id, is_active):

            Mgr.do("enable_gui", False)

        def exit_transf_start_snap_mode(next_state_id, is_active):

            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("transf_start_snap_mode", -1, enter_transf_start_snap_mode,
                  exit_transf_start_snap_mode)

    def __update_snapping(self, update_type, *args):

        if update_type == "reset":

            self._btns["snap"].set_active(False)
            self._btns["snap"].enable(False)
            self._btns["snap_options"].enable(False)
            self._tools_menu_item.enable(False)
            self._tool_options_menu_item.enable(False)

        elif update_type == "enable":

            enable, options_only = args

            if enable or (Mgr.get_state_id() not in ("transf_center_snap_mode",
                    "coord_origin_snap_mode") and not GlobalData["active_transform_type"]):
                self._btns["snap_options"].enable(enable)
                self._tool_options_menu_item.enable(enable)

            if not options_only:

                self._btns["snap"].enable(enable)
                self._tools_menu_item.enable(enable)

                if enable:
                    snap_settings = GlobalData["snap"]
                    snap_type = snap_settings["type"]
                    active = snap_settings["on"].get(snap_type, False)
                    self._btns["snap"].set_active(active)
                    self._tools_menu_item.check(active)
                else:
                    self._tools_menu_item.check(False)

        elif update_type == "show_options":

            SnapDialog()

        elif update_type == "snap":

            snap_settings = GlobalData["snap"]
            snap_type = snap_settings["type"]

            if snap_type in ("transf_center", "coord_origin"):
                return

            snap_on = not snap_settings["on"][snap_type]
            snap_settings["on"][snap_type] = snap_on
            self._btns["snap"].set_active(snap_on)
            self._tools_menu_item.check(snap_on)

            transf_type = GlobalData["active_transform_type"]
            state_id = Mgr.get_state_id()

            if transf_type and state_id == "selection_mode":
                if GlobalData["snap"]["on"][transf_type]:
                    Mgr.update_app("status", ["select", transf_type, "snap_idle"])
                else:
                    Mgr.update_app("status", ["select", transf_type, "idle"])


class SnapInputField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, width):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, INSET1_BORDER_GFX_DATA, width)

        self.set_image_offset(self._img_offset)

    def get_outer_borders(self):

        return self._field_borders


class SnapDialog(Dialog):

    def __init__(self):

        old_options = GlobalData["snap"]
        self._snap_type = snap_type = old_options["type"]

        if snap_type == "transf_center":
            title = 'Snap options (transform center)'
        elif snap_type == "coord_origin":
            title = 'Snap options (ref. coord. origin)'
        elif snap_type == "translate":
            title = 'Snap options (translation)'
        elif snap_type == "rotate":
            title = 'Snap options (rotation)'
        elif snap_type == "scale":
            title = 'Snap options (scaling)'

        Dialog.__init__(self, title, "okcancel", on_yes=self.__on_yes)

        self._options = new_options = {}

        for option_id in ("src_type", "tgt_type", "size", "show_marker", "marker_size"):
            new_options[option_id] = old_options[option_id][snap_type]

        if snap_type not in ("transf_center", "coord_origin"):
            for option_id in ("show_rubber_band", "show_proj_line", "show_proj_marker",
                    "proj_marker_size", "use_axis_constraints", "increment"):
                new_options[option_id] = old_options[option_id][snap_type]

        client_sizer = self.get_client_sizer()

        if snap_type in ("translate", "rotate", "scale"):

            group = DialogWidgetGroup(self, "Snap from:")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            def get_command(target_type):

                def command():

                    self._options["src_type"] = target_type

                return command

            columns = 4 if snap_type == "translate" else 3
            radio_btns = DialogRadioButtonGroup(group, columns=columns, gap_h=10, gap_v=5)

            if snap_type == "translate":
                btn_id = "transf_center"
                radio_btns.add_button(btn_id, "transform center")
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            btn_ids = ("grid_point", "obj_center", "obj_pivot", "vert", "edge", "poly")
            texts = ("grid point", "object center", "object pivot", "vertex",
                     "edge center", "polygon center")

            for btn_id, text in zip(btn_ids, texts):
                radio_btns.add_button(btn_id, text)
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            radio_btns.set_selected_button(old_options["src_type"][snap_type])
            borders = (5, 0, 0, 0)
            group.add(radio_btns.get_sizer(), expand=True, borders=borders)

        if snap_type in ("transf_center", "coord_origin", "translate", "rotate", "scale"):

            group = DialogWidgetGroup(self, "Snap to:")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            columns = 4 if snap_type in ("translate", "rotate", "scale") else 3
            radio_btns = DialogRadioButtonGroup(group, columns=columns, gap_h=10, gap_v=5)

            if snap_type in ("translate", "rotate", "scale"):

                def command():

                    self._options["tgt_type"] = "increment"

                if snap_type == "translate":
                    btn_txt = "offset increment"
                elif snap_type == "rotate":
                    btn_txt = "angle increment"
                elif snap_type == "scale":
                    btn_txt = "scale increment"

                radio_btns.add_button("increment", btn_txt)
                radio_btns.set_button_command("increment", command)

            def get_command(target_type):

                def command():

                    self._options["tgt_type"] = target_type

                return command

            btn_ids = ("grid_point", "obj_center", "obj_pivot", "vert", "edge", "poly")
            texts = ("grid point", "object center", "object pivot", "vertex",
                     "edge center", "polygon center")

            for btn_id, text in zip(btn_ids, texts):
                radio_btns.add_button(btn_id, text)
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            radio_btns.set_selected_button(old_options["tgt_type"][snap_type])
            borders = (5, 20, 0, 0)
            group.add(radio_btns.get_sizer(), expand=True, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 0, 10)
            group.add(subsizer, expand=True, borders=borders)

            if snap_type == "translate":
                incr_type = "Offset"
                incr_unit_descr = ""
                input_parser = self.__parse_value
            elif snap_type == "rotate":
                incr_type = "Angle"
                incr_unit_descr = " (degr.)"
                input_parser = self.__parse_angle_incr
            elif snap_type == "scale":
                incr_type = "Scale"
                incr_unit_descr = " (%)"
                input_parser = self.__parse_value

            if snap_type in ("translate", "rotate", "scale"):
                text = DialogText(group, "{} increment{}:".format(incr_type, incr_unit_descr))
                borders = (5, 0, 0, 0)
                subsizer.add(text, alignment="center_v", borders=borders)
                val_id = "increment"
                field = SnapInputField(group, 100)
                field.add_value(val_id, handler=self.__handle_value)
                field.set_value(val_id, old_options[val_id][snap_type])
                field.show_value(val_id)
                field.set_input_parser(val_id, input_parser)
                subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
                subsizer.add((10, 0), proportion=.2)

            text = DialogText(group, "Target point size:")
            borders = (5, 0, 0, 0)
            subsizer.add(text, alignment="center_v", borders=borders)
            field = SnapInputField(group, 100)
            val_id = "size"
            field.add_value(val_id, handler=self.__handle_value)
            field.set_value(val_id, old_options[val_id][snap_type])
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        def add_marker_display_options(group, text_str):

            def command(show):

                self._options["show_marker"] = show

            widgets = []
            checkbox = DialogCheckBox(group, command)
            checkbox.check(old_options["show_marker"][snap_type])
            widgets.append(checkbox)
            text = DialogText(group, text_str)
            widgets.append(text)
            text = DialogText(group, "Size:")
            widgets.append(text)
            field = SnapInputField(group, 100)
            val_id = "marker_size"
            field.add_value(val_id, handler=self.__handle_value)
            field.set_value(val_id, old_options[val_id][snap_type])
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            widgets.append(field)

            return widgets

        if snap_type in ("transf_center", "coord_origin"):

            group = DialogWidgetGroup(self, "Marker display")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 0, 0)
            group.add(subsizer, expand=True, borders=borders)

            checkbox, text1, text2, field = add_marker_display_options(group, "Show")
            subsizer.add(checkbox, alignment="center_v")
            subsizer.add(text1, alignment="center_v", borders=borders)
            subsizer.add((10, 0), proportion=.1)
            subsizer.add(text2, alignment="center_v", borders=borders)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        else:

            group = DialogWidgetGroup(self, "Display")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = GridSizer(columns=8, gap_h=5, gap_v=2)
            borders = (5, 0, 0, 0)
            group.add(subsizer, expand=True, borders=borders)

            checkbox, text1, text2, field = add_marker_display_options(group, "Target point marker")
            subsizer.add(checkbox, alignment_v="center_v")
            subsizer.add(text1, alignment_v="center_v")
            subsizer.add((10, 0), proportion_h=.5)
            subsizer.add(text2, alignment_v="center_v")
            subsizer.add(field, alignment_v="center_v")

            subsizer.add((10, 0), proportion_h=1.)

            def command(show):

                self._options["show_rubber_band"] = show

            val_id = "show_rubber_band"
            checkbox = DialogCheckBox(group, command)
            checkbox.check(old_options[val_id][snap_type])
            subsizer.add(checkbox, alignment_v="center_v")
            text = DialogText(group, "Rubber band")
            subsizer.add(text, alignment_v="center_v")

            def command(show):

                self._options["show_proj_marker"] = show

            val_id = "show_proj_marker"
            checkbox = DialogCheckBox(group, command)
            checkbox.check(old_options[val_id][snap_type])
            subsizer.add(checkbox, alignment_v="center_v")
            text = DialogText(group, "Projected point marker")
            subsizer.add(text, alignment_v="center_v")

            subsizer.add((10, 0), proportion_h=.5)

            text = DialogText(group, "Size:")
            subsizer.add(text, alignment_v="center_v")
            field = SnapInputField(group, 100)
            val_id = "proj_marker_size"
            field.add_value(val_id, handler=self.__handle_value)
            field.set_value(val_id, old_options[val_id][snap_type])
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            subsizer.add(field, alignment_v="center_v")

            subsizer.add((10, 0), proportion_h=1.)

            def command(show):

                self._options["show_proj_line"] = show

            val_id = "show_proj_line"
            checkbox = DialogCheckBox(group, command)
            checkbox.check(old_options[val_id][snap_type])
            subsizer.add(checkbox, alignment_v="center_v")
            text = DialogText(group, "Projection line")
            subsizer.add(text, alignment_v="center_v")

            subsizer = Sizer("horizontal")
            borders = (25, 20, 0, 10)
            client_sizer.add(subsizer, expand=True, borders=borders)

            def command(use):

                self._options["use_axis_constraints"] = use

            checkbox = DialogCheckBox(self, command)
            checkbox.check(old_options["use_axis_constraints"][snap_type])
            subsizer.add(checkbox, alignment="center_v")
            t = "Use axis constraints (snap to projection of target point onto transform plane/axis)"
            text = DialogText(self, t)
            borders = (5, 0, 0, 0)
            subsizer.add(text, alignment="center_v", borders=borders)

        client_sizer.add((0, 20))

        self.finalize()

    def __handle_value(self, value_id, value):

        self._options[value_id] = value

    def __parse_value(self, value):

        try:
            return max(.001, abs(float(eval(value))))
        except:
            return None

    def __parse_angle_incr(self, angle_incr):

        try:
            return max(.001, min(180., abs(float(eval(angle_incr)))))
        except:
            return None

    def __on_yes(self):

        snap_type = self._snap_type
        state_id = Mgr.get_state_id()

        if ((state_id == "transf_center_snap_mode" and snap_type == "transf_center")
                or (state_id == "coord_origin_snap_mode" and snap_type == "coord_origin")):
            Mgr.enter_state("suppressed")

        old_options = GlobalData["snap"]
        new_options = self._options

        for option_id in ("src_type", "tgt_type", "size", "show_marker", "marker_size"):
            old_options[option_id][snap_type] = new_options[option_id]

        if snap_type not in ("transf_center", "coord_origin"):
            for option_id in ("show_rubber_band", "show_proj_line", "show_proj_marker",
                    "proj_marker_size", "use_axis_constraints", "increment"):
                old_options[option_id][snap_type] = new_options[option_id]

        if ((state_id == "transf_center_snap_mode" and snap_type == "transf_center")
                or (state_id == "coord_origin_snap_mode" and snap_type == "coord_origin")):
            Mgr.exit_state("suppressed")

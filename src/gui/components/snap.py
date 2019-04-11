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

            enable, force_snap_on = args

            if enable:

                self._btns["snap"].enable()
                self._btns["snap_options"].enable()
                self._tools_menu_item.enable()
                self._tool_options_menu_item.enable()

                if force_snap_on:
                    self._btns["snap"].set_active()
                    self._tools_menu_item.check()
                else:
                    snap_settings = GlobalData["snap"]
                    snap_type = snap_settings["type"]
                    active = snap_settings["on"][snap_type]
                    self._btns["snap"].set_active(active)
                    self._tools_menu_item.check(active)

            else:

                if not (Mgr.is_state_active("creation_mode")
                        or GlobalData["active_transform_type"]):
                    self._btns["snap"].enable(False)
                    self._btns["snap_options"].enable(False)
                    self._tools_menu_item.enable(False)
                    self._tools_menu_item.check(False)
                    self._tool_options_menu_item.enable(False)
                else:
                    snap_settings = GlobalData["snap"]
                    snap_type = snap_settings["prev_type"]
                    active = snap_settings["on"][snap_type]
                    self._btns["snap"].set_active(active)
                    self._tools_menu_item.check(active)

        elif update_type == "show_options":

            SnapDialog()

        elif update_type == "snap":

            snap_settings = GlobalData["snap"]
            snap_type = snap_settings["type"]

            if snap_type in ("transf_center", "coord_origin"):
                self._btns["snap"].set_active()
                self._tools_menu_item.check()
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
            elif state_id == "creation_mode":
                creation_type = GlobalData["active_creation_type"]
                if GlobalData["snap"]["on"]["creation"]:
                    Mgr.update_app("status", ["create", creation_type, "snap_idle"])
                else:
                    Mgr.update_app("status", ["create", creation_type, "idle"])

            Mgr.update_remotely("object_snap")


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

        if snap_type == "creation":
            title = 'Snap options (object creation)'
        elif snap_type == "transf_center":
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

        if snap_type == "creation":
            checkboxes = {}
            fields = {}
            toggle_btns = ToggleButtonGroup()
            creation_phase_radio_btns = {}
            new_creation_options = new_options["creation_start"] = {}
            for option_id in ("on", "tgt_type", "size", "show_marker", "marker_size"):
                new_creation_options[option_id] = old_options[option_id]["creation_start"]
            for creation_snap_type in ("creation_phase_1", "creation_phase_2", "creation_phase_3"):
                new_creation_options = new_options[creation_snap_type] = {}
                for option_id in ("on", "tgt_type", "size", "show_marker", "marker_size",
                        "show_proj_line", "show_proj_marker", "proj_marker_size", "increment"):
                    new_creation_options[option_id] = old_options[option_id][creation_snap_type]
        else:
            for option_id in ("src_type", "tgt_type", "size", "show_marker", "marker_size"):
                new_options[option_id] = old_options[option_id][snap_type]

        if snap_type not in ("transf_center", "coord_origin", "creation"):
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

        def add_target_options(parent, parent_sizer, borders, for_creation_phase=False):

            group = DialogWidgetGroup(parent, "Snap to:")
            parent_sizer.add(group, expand=True, borders=borders)
            add_incr_option = ((snap_type == "creation" and for_creation_phase)
                               or snap_type in ("translate", "rotate", "scale"))

            columns = 4 if add_incr_option else 3
            radio_btns = DialogRadioButtonGroup(group, columns=columns, gap_h=10, gap_v=5)

            if add_incr_option:

                def command():

                    if for_creation_phase:
                        self._options[self._creation_phase_id]["tgt_type"] = "increment"
                    else:
                        self._options["tgt_type"] = "increment"

                if snap_type == "rotate":
                    btn_txt = "angle increment"
                elif snap_type == "scale":
                    btn_txt = "scale increment"
                else:
                    btn_txt = "offset increment"

                radio_btns.add_button("increment", btn_txt)
                radio_btns.set_button_command("increment", command)

            def get_command(target_type):

                def command():

                    if for_creation_phase:
                        self._options[self._creation_phase_id]["tgt_type"] = target_type
                    elif snap_type == "creation":
                        self._options["creation_start"]["tgt_type"] = target_type
                    else:
                        self._options["tgt_type"] = target_type

                return command

            btn_ids = ("grid_point", "obj_center", "obj_pivot", "vert", "edge", "poly")
            texts = ("grid point", "object center", "object pivot", "vertex",
                     "edge center", "polygon center")

            for btn_id, text in zip(btn_ids, texts):
                radio_btns.add_button(btn_id, text)
                radio_btns.set_button_command(btn_id, get_command(btn_id))

            if for_creation_phase:
                tgt_type = old_options["tgt_type"][self._creation_phase_id]
                creation_phase_radio_btns["tgt_type"] = radio_btns
            elif snap_type == "creation":
                tgt_type = old_options["tgt_type"]["creation_start"]
            else:
                tgt_type = old_options["tgt_type"][snap_type]

            radio_btns.set_selected_button(tgt_type)

            if snap_type == "creation" and not for_creation_phase:
                h_subsizer = Sizer("horizontal")
                borders = (5, 0, 0, 0)
                group.add(h_subsizer, expand=True, proportion=1., borders=borders)
                h_subsizer.add(radio_btns.get_sizer(), proportion=1., borders=borders)
                subsizer = Sizer("vertical")
                borders = (50, 0, 0, 0)
                h_subsizer.add(subsizer, expand=True, proportion=1., borders=borders)
                parent_sizer.add((0, 5))
            else:
                borders = (5, 20, 0, 0)
                group.add(radio_btns.get_sizer(), expand=True, borders=borders)
                subsizer = Sizer("horizontal")
                borders = (5, 0, 0, 10)
                group.add(subsizer, expand=True, borders=borders)

            if add_incr_option:

                if snap_type == "rotate":
                    incr_type = "Angle"
                    incr_unit_descr = " (degr.)"
                    input_parser = self.__parse_angle_incr
                elif snap_type == "scale":
                    incr_type = "Scale"
                    incr_unit_descr = " (%)"
                    input_parser = self.__parse_value
                else:
                    incr_type = "Offset"
                    incr_unit_descr = ""
                    input_parser = self.__parse_value

                text = DialogText(group, "{} increment{}:".format(incr_type, incr_unit_descr))
                borders = (5, 0, 0, 0)
                subsizer.add(text, alignment="center_v", borders=borders)
                val_id = "increment"
                field = SnapInputField(group, 100)

                if for_creation_phase:
                    handler = self.__get_value_handler()
                    incr = old_options[val_id][self._creation_phase_id]
                    fields[val_id] = field
                else:
                    handler = self.__handle_value
                    incr = old_options[val_id][snap_type]

                field.add_value(val_id, handler=handler)
                field.set_value(val_id, incr)
                field.show_value(val_id)
                field.set_input_parser(val_id, input_parser)
                subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
                subsizer.add((10, 0), proportion=.2)

            text = DialogText(group, "Target point size:")
            borders = (5, 0, 0, 0)
            subsizer.add(text, alignment="center_v", borders=borders)
            field = SnapInputField(group, 100)
            val_id = "size"

            if for_creation_phase:
                handler = self.__get_value_handler()
                size = old_options[val_id][self._creation_phase_id]
                fields[val_id] = field
            elif snap_type == "creation":
                handler = self.__get_value_handler("creation_start")
                size = old_options[val_id]["creation_start"]
            else:
                handler = self.__handle_value
                size = old_options[val_id][snap_type]

            field.add_value(val_id, handler=handler)
            field.set_value(val_id, size)
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            subsizer.add(field, expand=True, proportion=1., alignment="center_v", borders=borders)

        def add_marker_display_options(group, text_str, for_creation_phase=False):

            def command(show):

                if for_creation_phase:
                    self._options[self._creation_phase_id]["show_marker"] = show
                elif snap_type == "creation":
                    self._options["creation_start"]["show_marker"] = show
                else:
                    self._options["show_marker"] = show

            widgets = []
            checkbox = DialogCheckBox(group, command)
            val_id = "show_marker"

            if for_creation_phase:
                show = old_options[val_id][self._creation_phase_id]
            elif snap_type == "creation":
                show = old_options[val_id]["creation_start"]
            else:
                show = old_options[val_id][snap_type]

            checkbox.check(show)
            widgets.append(checkbox)
            text = DialogText(group, text_str)
            widgets.append(text)
            text = DialogText(group, "Size:")
            widgets.append(text)
            field = SnapInputField(group, 100)
            val_id = "marker_size"

            if for_creation_phase:
                handler = self.__get_value_handler()
                size = old_options[val_id][self._creation_phase_id]
            elif snap_type == "creation":
                handler = self.__get_value_handler("creation_start")
                size = old_options[val_id]["creation_start"]
            else:
                handler = self.__handle_value
                size = old_options[val_id][snap_type]

            field.add_value(val_id, handler=handler)
            field.set_value(val_id, size)
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            widgets.append(field)

            return widgets

        def add_marker_display_group(parent, parent_sizer, borders, proportion=0.):

            group = DialogWidgetGroup(parent, "Marker display")
            parent_sizer.add(group, expand=True, proportion=proportion, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 0, 0)
            group.add(subsizer, expand=True, borders=borders)

            checkbox, text1, text2, field = add_marker_display_options(group, "Show")
            subsizer.add(checkbox, alignment="center_v")
            subsizer.add(text1, alignment="center_v", borders=borders)
            subsizer.add((10, 0), proportion=.1)
            subsizer.add(text2, alignment="center_v", borders=borders)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        if snap_type == "creation":

            self._creation_phase_id = "creation_phase_1"

            group = DialogWidgetGroup(self, "Creation start")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 0, 0)
            group.add(subsizer, expand=True, borders=borders)

            def enable_snapping(enable):

                self._options["creation_start"]["on"] = enable

            checkbox = DialogCheckBox(group, enable_snapping)
            checkbox.check(old_options["on"]["creation_start"])
            subsizer.add(checkbox, alignment="center_v")
            text = DialogText(group, "Enable snapping")
            borders = (5, 0, 0, 0)
            subsizer.add(text, alignment="center_v", borders=borders)
            borders = (20, 5, 0, 0)
            add_marker_display_group(group, subsizer, borders, proportion=1.)

            borders = (5, 5, 0, 10)
            add_target_options(group, group.get_client_sizer(), borders)

            group = DialogWidgetGroup(self, "Creation phases")
            borders = (20, 20, 0, 10)
            client_sizer.add(group, expand=True, borders=borders)

            subsizer = Sizer("horizontal")
            borders = (5, 0, 0, 0)
            group.add(subsizer, expand=True, borders=borders)

            def get_checkbox_command(phase_id):

                def enable_snapping(enable):

                    self._options["creation_{}".format(phase_id)]["on"] = enable

                return enable_snapping

            def get_btn_command(phase_id):

                def command():

                    toggle_btns.set_active_button(phase_id)
                    options = self._options["creation_{}".format(phase_id)]
                    creation_phase_radio_btns["tgt_type"].set_selected_button(options["tgt_type"])

                    for option_id in ("show_marker", "show_proj_marker", "show_proj_line"):
                        checkboxes[option_id].check(options[option_id])

                    for option_id in ("increment", "size", "marker_size", "proj_marker_size"):
                        fields[option_id].set_value(option_id, options[option_id])

                    self._creation_phase_id = "creation_{}".format(phase_id)

                return command

            for index in range(3):
                phase_id = "phase_{:d}".format(index + 1)
                checkbox = DialogCheckBox(group, get_checkbox_command(phase_id))
                checkbox.check(old_options["on"]["creation_{}".format(phase_id)])
                subsizer.add(checkbox, alignment="center_v")
                text = "Phase {:d}".format(index + 1)
                tooltip_text = "Creation phase {:d} settings".format(index + 1)
                btn = DialogButton(group, text, "", tooltip_text)
                toggle = (get_btn_command(phase_id), lambda: None)
                toggle_btns.add_button(btn, phase_id, toggle)
                subsizer.add(btn, alignment="center_v", borders=borders)
                subsizer.add((10, 0), proportion=1.)

            toggle_btns.set_active_button("phase_1")

            borders = (5, 5, 0, 10)
            add_target_options(group, group.get_client_sizer(), borders, True)

            subgroup = DialogWidgetGroup(group, "Display")
            borders = (5, 5, 5, 10)
            group.add(subgroup, expand=True, borders=borders)

            subsizer = GridSizer(columns=8, gap_h=5, gap_v=2)
            borders = (5, 0, 0, 0)
            subgroup.add(subsizer, expand=True, borders=borders)

            checkbox, text1, text2, field = add_marker_display_options(subgroup,
                "Target point marker", for_creation_phase=True)
            checkboxes["show_marker"] = checkbox
            fields["marker_size"] = field
            subsizer.add(checkbox, alignment_v="center_v")
            subsizer.add(text1, alignment_v="center_v")
            subsizer.add((10, 0), proportion_h=.5)
            subsizer.add(text2, alignment_v="center_v")
            subsizer.add(field, alignment_v="center_v")
            subsizer.add((10, 0), proportion_h=1.)
            subsizer.add((0, 0))
            subsizer.add((0, 0))

            def command(show):

                self._options[self._creation_phase_id]["show_proj_marker"] = show

            val_id = "show_proj_marker"
            checkbox = DialogCheckBox(subgroup, command)
            checkbox.check(old_options[val_id][self._creation_phase_id])
            checkboxes["show_proj_marker"] = checkbox
            subsizer.add(checkbox, alignment_v="center_v")
            text = DialogText(subgroup, "Projected point marker")
            subsizer.add(text, alignment_v="center_v")

            subsizer.add((10, 0), proportion_h=.5)

            text = DialogText(subgroup, "Size:")
            subsizer.add(text, alignment_v="center_v")
            field = SnapInputField(subgroup, 100)
            fields["proj_marker_size"] = field
            val_id = "proj_marker_size"
            field.add_value(val_id, handler=self.__get_value_handler())
            field.set_value(val_id, old_options[val_id][self._creation_phase_id])
            field.show_value(val_id)
            field.set_input_parser(val_id, self.__parse_value)
            subsizer.add(field, alignment_v="center_v")

            subsizer.add((10, 0), proportion_h=1.)

            def command(show):

                self._options[self._creation_phase_id]["show_proj_line"] = show

            val_id = "show_proj_line"
            checkbox = DialogCheckBox(subgroup, command)
            checkbox.check(old_options[val_id][self._creation_phase_id])
            checkboxes["show_proj_line"] = checkbox
            subsizer.add(checkbox, alignment_v="center_v")
            text = DialogText(subgroup, "Projection line")
            subsizer.add(text, alignment_v="center_v")

        else:

            borders = (20, 20, 0, 10)
            add_target_options(self, client_sizer, borders)

            if snap_type in ("transf_center", "coord_origin"):

                add_marker_display_group(self, client_sizer, borders)

            else:

                group = DialogWidgetGroup(self, "Display")
                client_sizer.add(group, expand=True, borders=borders)

                subsizer = GridSizer(columns=8, gap_h=5, gap_v=2)
                borders = (5, 0, 0, 0)
                group.add(subsizer, expand=True, borders=borders)

                checkbox, text1, text2, field = add_marker_display_options(group,
                    "Target point marker")
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
                t = "Use axis constraints (snap to projection of target " \
                    "point onto transform plane/axis)"
                text = DialogText(self, t)
                borders = (5, 0, 0, 0)
                subsizer.add(text, alignment="center_v", borders=borders)

        client_sizer.add((0, 20))

        self.finalize()

    def __get_value_handler(self, snap_type="creation_phase"):

        def handle_value(value_id, value):

            if snap_type == "creation_phase":
                self._options[self._creation_phase_id][value_id] = value
            else:
                self._options[snap_type][value_id] = value

        return handle_value

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
                or (state_id == "coord_origin_snap_mode" and snap_type == "coord_origin")
                or state_id == "creation_mode"):
            Mgr.enter_state("suppressed")

        old_options = GlobalData["snap"]
        new_options = self._options

        if snap_type == "creation":
            new_creation_options = new_options["creation_start"]
            for option_id in ("on", "tgt_type", "size", "show_marker", "marker_size"):
                old_options[option_id]["creation_start"] = new_creation_options[option_id]
            for creation_snap_type in ("creation_phase_1", "creation_phase_2", "creation_phase_3"):
                new_creation_options = new_options[creation_snap_type]
                for option_id in ("on", "tgt_type", "size", "show_marker", "marker_size",
                        "show_proj_line", "show_proj_marker", "proj_marker_size", "increment"):
                    old_options[option_id][creation_snap_type] = new_creation_options[option_id]
        else:
            for option_id in ("src_type", "tgt_type", "size", "show_marker", "marker_size"):
                old_options[option_id][snap_type] = new_options[option_id]

        if snap_type not in ("transf_center", "coord_origin", "creation"):
            for option_id in ("show_rubber_band", "show_proj_line", "show_proj_marker",
                    "proj_marker_size", "use_axis_constraints", "increment"):
                old_options[option_id][snap_type] = new_options[option_id]

        if ((state_id == "transf_center_snap_mode" and snap_type == "transf_center")
                or (state_id == "coord_origin_snap_mode" and snap_type == "coord_origin")
                or state_id == "creation_mode"):
            Mgr.exit_state("suppressed")

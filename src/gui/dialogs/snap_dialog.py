from ..base import *
from ..button import *
from ..dialog import *


class SnapDialog(Dialog):

    def __init__(self):

        Dialog.__init__(self, "", "okcancel", on_yes=self.__on_yes)

        old_options = GD["snap"]
        self._snap_type = snap_type = old_options["type"]
        incr_type = incr_descr = ""

        if snap_type == "creation":
            snap_descr = "object creation"
        elif snap_type == "transf_center":
            snap_descr = "transform center"
        elif snap_type == "coord_origin":
            snap_descr = "ref. coord. origin"
        elif snap_type == "translate":
            snap_descr = "translation"
            incr_type = "offset"
            incr_descr = "Offset increment"
        elif snap_type == "rotate":
            snap_descr = "rotation"
            incr_type = "angle"
            incr_descr = "Angle increment (degr.)"
        elif snap_type == "scale":
            snap_descr = "scaling"
            incr_type = "scale"
            incr_descr = "Scale increment (%)"

        text_vars = {
            "snap_descr": snap_descr,
            "incr_type": incr_type,
            "incr_descr": incr_descr
        }

        if snap_type == "translate":
            component_ids = ["transform", "translate", "target options",
                "increment", "display (transform)"]
        elif snap_type in ("rotate", "scale"):
            component_ids = ["transform", "target options", "increment",
                "display (transform)"]
        elif snap_type == "creation":
            component_ids = ["creation"]
        else:
            component_ids = ["target options", "marker display"]

        widgets = Skin.layout.create(self, "snap", text_vars, component_ids)
        loaded_checkbtns = widgets["checkbuttons"]
        radio_btn_groups = widgets["radiobutton_groups"]
        btns = widgets["buttons"]
        loaded_fields = widgets["fields"]

        self._options = new_options = {}

        if snap_type == "creation":
            checkbtns = {}
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

        if snap_type in ("translate", "rotate", "scale"):

            def set_src_type(src_type):

                self._options["src_type"] = src_type

            radio_btns = radio_btn_groups["src_type"]

            if snap_type == "translate":
                btn_id = "transf_center"
                command = lambda: set_src_type("transf_center")
                radio_btns.set_button_command(btn_id, command)

            btn_ids = ("grid_point", "obj_center", "obj_pivot", "vert", "edge", "poly")

            for btn_id in btn_ids:
                command = lambda src_type=btn_id: set_src_type(src_type)
                radio_btns.set_button_command(btn_id, command)

            radio_btns.set_selected_button(old_options["src_type"][snap_type])

        def set_target_options(for_creation_phase=False):

            add_incr_option = ((snap_type == "creation" and for_creation_phase)
                               or snap_type in ("translate", "rotate", "scale"))

            if for_creation_phase:
                radio_btns = radio_btn_groups["tgt_type_creation_phase"]
            else:
                radio_btns = radio_btn_groups["tgt_type"]

            if add_incr_option:

                def command():

                    if for_creation_phase:
                        self._options[self._creation_phase_id]["tgt_type"] = "increment"
                    else:
                        self._options["tgt_type"] = "increment"

                radio_btns.set_button_command("increment", command)

            def set_target_type(target_type):

                if for_creation_phase:
                    self._options[self._creation_phase_id]["tgt_type"] = target_type
                elif snap_type == "creation":
                    self._options["creation_start"]["tgt_type"] = target_type
                else:
                    self._options["tgt_type"] = target_type

            btn_ids = ("grid_point", "obj_center", "obj_pivot", "vert", "edge", "poly")

            for btn_id in btn_ids:
                command = lambda target_type=btn_id: set_target_type(target_type)
                radio_btns.set_button_command(btn_id, command)

            if for_creation_phase:
                tgt_type = old_options["tgt_type"][self._creation_phase_id]
                creation_phase_radio_btns["tgt_type"] = radio_btns
            elif snap_type == "creation":
                tgt_type = old_options["tgt_type"]["creation_start"]
            else:
                tgt_type = old_options["tgt_type"][snap_type]

            radio_btns.set_selected_button(tgt_type)

            if add_incr_option:

                if snap_type == "rotate":
                    input_parser = self.__parse_angle_incr_input
                    val_rng = (.001, 180.)
                elif snap_type == "scale":
                    input_parser = self.__parse_input
                    val_rng = (.001, None)
                else:
                    input_parser = self.__parse_input
                    val_rng = (.001, None)

                val_id = "increment"

                if for_creation_phase:
                    handler = self.__handle_snap_value
                    incr = old_options[val_id][self._creation_phase_id]
                else:
                    handler = self.__handle_value
                    incr = old_options[val_id][snap_type]

                field = loaded_fields[val_id]
                field.value_id = val_id
                field.set_value_handler(handler)
                field.set_value_range(val_rng, False, "float")
                field.set_step(.001)
                field.set_input_parser(input_parser)
                field.set_value(incr)

                if for_creation_phase:
                    fields[val_id] = field

            val_id = "size"

            if for_creation_phase:
                handler = self.__handle_snap_value
                size = old_options[val_id][self._creation_phase_id]
            elif snap_type == "creation":
                handler = lambda i, v, s="done": self.__handle_snap_value(i, v, s,
                    snap_type="creation_start")
                size = old_options[val_id]["creation_start"]
            else:
                handler = self.__handle_value
                size = old_options[val_id][snap_type]

            if for_creation_phase:
                field = loaded_fields["size_creation_start"]
                fields[val_id] = field
            else:
                field = loaded_fields["size"]

            field.value_id = val_id
            field.set_value_handler(handler)
            field.set_value_range((.001, None), False, "float")
            field.set_step(.001)
            field.set_input_parser(self.__parse_input)
            field.set_value(size)

        def set_marker_display_options(for_creation_phase=False):

            def command(show):

                if for_creation_phase:
                    self._options[self._creation_phase_id]["show_marker"] = show
                elif snap_type == "creation":
                    self._options["creation_start"]["show_marker"] = show
                else:
                    self._options["show_marker"] = show

            val_id = "show_marker"

            if for_creation_phase:
                checkbtn = loaded_checkbtns[val_id + "_creation_phase"]
                field = loaded_fields["marker_size_creation_phase"]
            else:
                checkbtn = loaded_checkbtns[val_id]
                field = loaded_fields["marker_size"]

            checkbtn.command = command

            if for_creation_phase:
                show = old_options[val_id][self._creation_phase_id]
            elif snap_type == "creation":
                show = old_options[val_id]["creation_start"]
            else:
                show = old_options[val_id][snap_type]

            checkbtn.check(show)
            val_id = "marker_size"

            if for_creation_phase:
                handler = self.__handle_snap_value
                size = old_options[val_id][self._creation_phase_id]
            elif snap_type == "creation":
                handler = lambda i, v, s="done": self.__handle_snap_value(i, v, s,
                    snap_type="creation_start")
                size = old_options[val_id]["creation_start"]
            else:
                handler = self.__handle_value
                size = old_options[val_id][snap_type]

            field.value_id = val_id
            field.set_value_handler(handler)
            field.set_value_range((.001, None), False, "float")
            field.set_step(.001)
            field.set_input_parser(self.__parse_input)
            field.set_value(size)

            if snap_type == "creation":
                checkbtns["show_marker"] = checkbtn
                fields["marker_size"] = field

        if snap_type == "creation":

            self._creation_phase_id = "creation_phase_1"

            def enable_snapping(enable):

                self._options["creation_start"]["on"] = enable

            checkbtn = loaded_checkbtns["enable_snapping"]
            checkbtn.command = enable_snapping
            checkbtn.check(old_options["on"]["creation_start"])

            set_marker_display_options()
            set_target_options()

            def enable_snapping(phase_id, enable):

                self._options[f"creation_{phase_id}"]["on"] = enable

            def show_phase_options(phase_id):

                toggle_btns.set_active_button(phase_id)
                options = self._options[f"creation_{phase_id}"]
                creation_phase_radio_btns["tgt_type"].set_selected_button(options["tgt_type"])

                for option_id in ("show_marker", "show_proj_marker", "show_proj_line"):
                    checkbtns[option_id].check(options[option_id])

                for option_id in ("increment", "size", "marker_size", "proj_marker_size"):
                    fields[option_id].set_value(options[option_id])

                self._creation_phase_id = f"creation_{phase_id}"

            for index in range(3):
                phase_id = f"phase_{index + 1}"
                checkbtn = loaded_checkbtns[phase_id]
                checkbtn.command = lambda enable, i=phase_id: enable_snapping(i, enable)
                checkbtn.check(old_options["on"][f"creation_{phase_id}"])
                btn = btns[phase_id]
                command = lambda i=phase_id: show_phase_options(i)
                toggle = (command, lambda: None)
                toggle_btns.add_button(btn, phase_id, toggle)

            toggle_btns.set_active_button("phase_1")

            set_target_options(True)
            set_marker_display_options(for_creation_phase=True)

            def command(show):

                self._options[self._creation_phase_id]["show_proj_marker"] = show

            val_id = "show_proj_marker"
            checkbtn = loaded_checkbtns[val_id]
            checkbtn.command = command
            checkbtn.check(old_options[val_id][self._creation_phase_id])
            checkbtns[val_id] = checkbtn

            val_id = "proj_marker_size"
            field = loaded_fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_snap_value)
            field.set_value_range((.001, None), False, "float")
            field.set_step(.001)
            field.set_input_parser(self.__parse_input)
            field.set_value(old_options[val_id][self._creation_phase_id])
            fields[val_id] = field

            def command(show):

                self._options[self._creation_phase_id]["show_proj_line"] = show

            val_id = "show_proj_line"
            checkbtn = loaded_checkbtns[val_id]
            checkbtn.command = command
            checkbtn.check(old_options[val_id][self._creation_phase_id])
            checkbtns[val_id] = checkbtn

        else:

            set_target_options()
            set_marker_display_options()

            if snap_type not in ("transf_center", "coord_origin"):

                def command(show):

                    self._options["show_rubber_band"] = show

                val_id = "show_rubber_band"
                checkbtn = loaded_checkbtns[val_id]
                checkbtn.command = command
                checkbtn.check(old_options[val_id][snap_type])

                def command(show):

                    self._options["show_proj_marker"] = show

                val_id = "show_proj_marker"
                checkbtn = loaded_checkbtns[val_id]
                checkbtn.command = command
                checkbtn.check(old_options[val_id][snap_type])

                val_id = "proj_marker_size"
                field = loaded_fields[val_id]
                field.value_id = val_id
                field.set_value_handler(self.__handle_value)
                field.set_value_range((.001, None), False, "float")
                field.set_step(.001)
                field.set_input_parser(self.__parse_input)
                field.set_value(old_options[val_id][snap_type])

                def command(show):

                    self._options["show_proj_line"] = show

                val_id = "show_proj_line"
                checkbtn = loaded_checkbtns[val_id]
                checkbtn.command = command
                checkbtn.check(old_options[val_id][snap_type])

                def command(use):

                    self._options["use_axis_constraints"] = use

                checkbtn = loaded_checkbtns["use_axis_constraints"]
                checkbtn.command = command
                checkbtn.check(old_options["use_axis_constraints"][snap_type])

        self.finalize()

    def __handle_snap_value(self, value_id, value, state="done", snap_type="creation_phase"):

        if snap_type == "creation_phase":
            self._options[self._creation_phase_id][value_id] = value
        else:
            self._options[snap_type][value_id] = value

    def __handle_value(self, value_id, value, state="done"):

        self._options[value_id] = value

    def __parse_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __parse_angle_incr_input(self, input_text):

        try:
            return max(.001, min(180., abs(float(eval(input_text)))))
        except:
            return None

    def __on_yes(self):

        snap_type = self._snap_type
        state_id = Mgr.get_state_id()

        if ((state_id == "transf_center_snap_mode" and snap_type == "transf_center")
                or (state_id == "coord_origin_snap_mode" and snap_type == "coord_origin")
                or state_id == "creation_mode"):
            Mgr.enter_state("suppressed")

        old_options = GD["snap"]
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

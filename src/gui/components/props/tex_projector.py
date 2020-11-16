from .base import *


class TexProjectorProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        self._targets = {}

        checkbtn = widgets["checkbuttons"]["tex_proj_on"]
        checkbtn.command = lambda on: self.__handle_value("on", on)
        self._checkbuttons["on"] = checkbtn

        val_id = "size"
        field = widgets["fields"]["tex_proj_size"]
        field.value_id = val_id
        field.value_type = "float"
        field.set_value_handler(self.__handle_value)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field

        radio_btns = widgets["radiobutton_groups"]["tex_proj_type"]

        for projection_type in ("orthographic", "perspective"):
            command = lambda p=projection_type: self.__set_projection_type(p)
            radio_btns.set_button_command(projection_type, command)

        radio_btns.set_selected_button("orthographic")
        self._radio_btns = radio_btns

        for val_id in ("film_w", "film_h", "film_x", "film_y"):
            field = widgets["fields"][val_id]
            field.value_id = val_id
            field.value_type = "float"
            field.set_value_handler(self.__handle_value)
            field.set_input_parser(self.__parse_size_input)
            self._fields[val_id] = field

        self._target_combobox = widgets["comboboxes"]["tex_proj_target"]

        btn = widgets["buttons"]["tex_proj_pick_target"]
        btn.command = self.__pick_object
        self._pick_btn = btn

        btn = widgets["buttons"]["tex_proj_remove_target"]
        btn.command = self.__remove_target

        btn = widgets["buttons"]["tex_proj_clear_target"]
        btn.command = self.__clear_targets

        checkbtn = widgets["checkbuttons"]["use_poly_sel"]
        checkbtn.command = lambda val: self.__handle_value("use_poly_sel", val)
        checkbtn.enable(False)
        checkbtn.add_disabler("no_targets", lambda: not self._targets)
        self._checkbuttons["use_poly_sel"] = checkbtn

        checkbtn = widgets["checkbuttons"]["show_poly_sel"]
        checkbtn.command = lambda val: self.__handle_value("show_poly_sel", val)
        checkbtn.enable(False)
        checkbtn.add_disabler("no_targets", lambda: not self._targets)
        self._checkbuttons["show_poly_sel"] = checkbtn

        val_id = "uv_set_ids"
        field = widgets["fields"]["tex_proj_uv_set_ids"]
        field.value_id = val_id
        field.value_type = "custom"
        field.set_input_parser(self.__parse_uv_set_id_input)
        field.set_value_parser(self.__parse_uv_set_ids)
        field.set_value_handler(self.__handle_value)
        field.set_value(())
        field.enable(False)
        field.add_disabler("no_targets", lambda: not self._targets)
        self._fields[val_id] = field

        btn = widgets["buttons"]["tex_proj_apply_uvs"]
        btn.command = self.__apply_uvs

    def setup(self):

        def enter_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._pick_btn.active = True

        def exit_picking_mode(next_state_id, active):

            if not active:
                self._pick_btn.active = False

        add_state = Mgr.add_state
        add_state("texprojtarget_picking_mode", -10, enter_picking_mode, exit_picking_mode)

    def __set_projection_type(self, projection_type):

        if GD["active_creation_type"]:
            Mgr.update_app("tex_projector_prop_default", "projection_type", projection_type)
            return

        Mgr.update_remotely("texproj_prop", "projection_type", projection_type)

    def __handle_value(self, value_id, value, state="done"):

        if GD["active_creation_type"]:
            Mgr.update_app("tex_projector_prop_default", value_id, value)
            return

        if value_id == "use_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["toplvl"] = not value
            value = {k: v.copy() for k, v in self._targets.items()}
            target_prop = "use_poly_sel"
        elif value_id == "show_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["show_poly_sel"] = value
            value = {k: v.copy() for k, v in self._targets.items()}
            target_prop = "show_poly_sel"
        elif value_id == "uv_set_ids":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["uv_set_ids"] = value
            value = {k: v.copy() for k, v in self._targets.items()}
            target_prop = "uv_set_ids"
        else:
            target_id = None
            target_prop = ""

        Mgr.update_remotely("texproj_prop", value_id, value, target_id=target_id,
                            target_prop=target_prop)

    def __select_target(self, target_id):

        self._target_combobox.select_item(target_id)
        target_data = self._targets[target_id]
        uv_set_ids = target_data["uv_set_ids"]
        use_poly_sel = not target_data["toplvl"]
        show_poly_sel = target_data["show_poly_sel"]
        field = self._fields["uv_set_ids"]
        field.set_value(uv_set_ids)
        self._checkbuttons["use_poly_sel"].check(use_poly_sel)
        self._checkbuttons["show_poly_sel"].check(show_poly_sel)

    def __remove_target(self):

        if not self._targets:
            return

        target_id = self._target_combobox.get_selected_item()
        value = {k: v.copy() for k, v in self._targets.items()}
        del value[target_id]

        Mgr.update_remotely("texproj_prop", "targets", value, target_id=target_id,
                            target_prop="remove")

    def __clear_targets(self):

        if not self._targets:
            return

        value = {}

        Mgr.update_remotely("texproj_prop", "targets", value, target_prop="clear")

    def __parse_size_input(self, input_text):

        try:
            size = float(input_text)
        except:
            try:
                size = eval(input_text)
            except:
                return None

        return max(.001, size)

    def __parse_uv_set_id_input(self, input_text):
        # TODO: use ranges

        try:
            uv_set_ids = tuple(set(sorted(min(7, max(0, int(s)))
                for s in input_text.replace(" ", "").split(","))))
        except:
            return None

        return uv_set_ids

    def __parse_uv_set_ids(self, uv_set_ids):
        # TODO: turn into ranges

        try:
            uv_set_id_str = str(uv_set_ids).strip("(),")
        except:
            return None

        return uv_set_id_str

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["tex_projector_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return ["tex_projector_targets"]

    def set_object_property_default(self, prop_id, value):

        color = Skin.colors["default_value"]

        if prop_id == "on":
            self._checkbuttons["on"].check(value)
            self._checkbuttons["on"].set_checkmark_color(color)
        elif prop_id == "projection_type":
            self._radio_btns.set_selected_button(value)
            self._radio_btns.set_bullet_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "on":

            self._checkbuttons["on"].check(value)

        elif prop_id == "projection_type":

            self._radio_btns.set_selected_button(value)

        elif prop_id == "targets":

            old_targets = self._targets
            new_targets, target_names = value

            if new_targets == old_targets:
                return

            self._targets = new_targets

            field = self._fields["uv_set_ids"]
            checkbtns = self._checkbuttons
            combobox = self._target_combobox
            cur_target_id = combobox.get_selected_item()

            if not old_targets:
                field.enable()
                checkbtns["use_poly_sel"].enable()
                checkbtns["show_poly_sel"].enable()

            if cur_target_id in new_targets:

                old_target_data = old_targets[cur_target_id]
                new_target_data = new_targets[cur_target_id]

                if new_target_data != old_target_data:
                    uv_set_ids = new_target_data["uv_set_ids"]
                    use_poly_sel = not new_target_data["toplvl"]
                    show_poly_sel = new_target_data["show_poly_sel"]
                    field.set_value(uv_set_ids)
                    checkbtns["use_poly_sel"].check(use_poly_sel)
                    checkbtns["show_poly_sel"].check(show_poly_sel)

            old_target_ids = set(old_targets.keys())
            new_target_ids = set(new_targets.keys())

            if new_target_ids == old_target_ids:
                return

            for target_id in new_target_ids - old_target_ids:
                target_name = target_names[target_id]
                command = lambda t=target_id: self.__select_target(t)
                combobox.add_item(target_id, target_name, command)
                combobox.select_item(target_id)

            for target_id in old_target_ids - new_target_ids:
                combobox.remove_item(target_id)

            new_target_id = combobox.get_selected_item()

            if new_target_id != cur_target_id:
                if new_target_id:
                    target_data = new_targets[new_target_id]
                    uv_set_ids = target_data["uv_set_ids"]
                    use_poly_sel = not target_data["toplvl"]
                    show_poly_sel = target_data["show_poly_sel"]
                    field.set_value(uv_set_ids)
                    checkbtns["use_poly_sel"].check(use_poly_sel)
                    checkbtns["show_poly_sel"].check(show_poly_sel)
                else:
                    field.set_value(())
                    field.enable(False)
                    checkbtns["use_poly_sel"].check(False)
                    checkbtns["use_poly_sel"].enable(False)
                    checkbtns["show_poly_sel"].check(False)
                    checkbtns["show_poly_sel"].enable(False)

        elif prop_id in self._fields:

            field = self._fields[prop_id]
            field.set_value(value)

    def check_selection_count(self):

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = Skin.text["input_disabled"]["color"] if multi_sel else None

        if multi_sel:
            self._checkbuttons["on"].check(False)
            self._radio_btns.set_selected_button()

        fields = self._fields

        for val_id in ("size", "film_w", "film_h", "film_x", "film_y"):
            field = fields[val_id]
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkbuttons["on"].set_checkmark_color(color)
        self._radio_btns.set_bullet_color(color, update=True)

    def __pick_object(self):

        if self._pick_btn.active:
            Mgr.exit_state("texprojtarget_picking_mode")
        else:
            Mgr.enter_state("texprojtarget_picking_mode")

    def __apply_uvs(self):

        Mgr.update_app("uv_projection")


ObjectTypes.add_type("tex_projector", "Texture Projector")
PropertyPanel.add_properties("tex_projector", TexProjectorProperties)

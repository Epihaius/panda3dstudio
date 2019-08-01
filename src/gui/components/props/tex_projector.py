from .base import *


class TexProjectorProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        self._targets = {}

        section = panel.add_section("tex_projector_props", "Tex. projector properties", hidden=True)

        text = "On"
        checkbtn = PanelCheckButton(section, lambda on:
            self.__handle_value("on", on), text)
        self._checkbuttons["on"] = checkbtn
        section.add(checkbtn)

        borders = (0, 5, 0, 0)

        sizer = Sizer("horizontal")
        section.add(sizer)
        text = "Size:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        val_id = "size"
        field = PanelInputField(section, val_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        group = section.add_group("Projection type")
        radio_btns = PanelRadioButtonGroup(group, columns=1)
        group.add(radio_btns.get_sizer())

        get_command = lambda projection_type: lambda: self.__set_projection_type(projection_type)

        for projection_type in ("orthographic", "perspective"):
            radio_btns.add_button(projection_type, projection_type.title())
            radio_btns.set_button_command(projection_type, get_command(projection_type))

        radio_btns.set_selected_button("orthographic")
        self._radio_btns = radio_btns

        group = section.add_group("Lens/Film")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)
        text = "Width:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        val_id = "film_w"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Height:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        val_id = "film_h"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "X offset:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        val_id = "film_x"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Y offset:"
        sizer.add(PanelText(group, text), alignment_v="center_v")
        val_id = "film_y"
        field = PanelInputField(group, val_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        section = panel.add_section("tex_projector_targets", "Projector targets", hidden=True)

        self._target_combobox = PanelComboBox(section, 10, tooltip_text="Selected target")
        borders = (5, 5, 5, 0)
        section.add(self._target_combobox, expand=True, borders=borders)

        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True, borders=borders)

        borders = (0, 5, 0, 0)

        text = "Pick"
        btn = PanelButton(section, text, "", "Add target model", self.__pick_object)
        self._pick_btn = btn
        btn_sizer.add(btn, proportion=1., borders=borders)

        text = "Remove"
        btn = PanelButton(section, text, "", "Remove selected target", self.__remove_target)
        btn_sizer.add(btn, proportion=1., borders=borders)

        text = "Clear"
        btn = PanelButton(section, text, "", "Remove all targets", self.__clear_targets)
        btn_sizer.add(btn, proportion=1.)

        group = section.add_group("Target poly selection")
        sizer = Sizer("horizontal")
        borders = (0, 0, 5, 0)
        group.add(sizer, expand=True, borders=borders)

        borders = (0, 5, 0, 0)

        text = "Use"
        checkbtn = PanelCheckButton(group, lambda val:
            self.__handle_value("use_poly_sel", val), text)
        checkbtn.enable(False)
        checkbtn.add_disabler("no_targets", lambda: not self._targets)
        self._checkbuttons["use_poly_sel"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((5, 0), proportion=1.)
        text = "Show"
        checkbtn = PanelCheckButton(group, lambda val:
            self.__handle_value("show_poly_sel", val), text)
        checkbtn.enable(False)
        checkbtn.add_disabler("no_targets", lambda: not self._targets)
        self._checkbuttons["show_poly_sel"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        text = "Affected UV sets:"
        borders = (5, 5, 5, 10)
        section.add(PanelText(group, text), alignment="center_h", borders=borders)
        val_id = "uv_set_ids"
        field = PanelInputField(section, val_id, "custom", self.__handle_value, 10)
        field.set_input_parser(self.__parse_uv_set_id_input)
        field.set_value_parser(self.__parse_uv_set_ids)
        field.set_value(())
        field.enable(False)
        field.add_disabler("no_targets", lambda: not self._targets)
        self._fields[val_id] = field
        borders = (5, 5, 5, 0)
        section.add(field, expand=True, borders=borders)

        text = "Apply UVs"
        btn = PanelButton(section, text, "", "Bake UVs into target vertices", self.__apply_uvs)
        section.add(btn, alignment="center_h")#, borders=borders)

    def setup(self):

        def enter_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            self._pick_btn.set_active()

        def exit_picking_mode(next_state_id, is_active):

            if not is_active:
                self._pick_btn.set_active(False)

        add_state = Mgr.add_state
        add_state("texprojtarget_picking_mode", -10, enter_picking_mode, exit_picking_mode)

    def __set_projection_type(self, projection_type):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("tex_projector_prop_default", "projection_type", projection_type)
            return

        Mgr.update_remotely("texproj_prop", "projection_type", projection_type)

    def __handle_value(self, value_id, value, state):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("tex_projector_prop_default", value_id, value)
            return

        if value_id == "use_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["toplvl"] = not value
            value = dict((k, v.copy()) for k, v in self._targets.items())
            target_prop = "use_poly_sel"
        elif value_id == "show_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["show_poly_sel"] = value
            value = dict((k, v.copy()) for k, v in self._targets.items())
            target_prop = "show_poly_sel"
        elif value_id == "uv_set_ids":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["uv_set_ids"] = value
            value = dict((k, v.copy()) for k, v in self._targets.items())
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
        value = dict((k, v.copy()) for k, v in self._targets.items())
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

        color = (1., 1., 0., 1.)

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
                get_command = lambda target_id: lambda: self.__select_target(target_id)
                combobox.add_item(target_id, target_name, get_command(target_id))
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

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

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

        if self._pick_btn.is_active():
            Mgr.exit_state("texprojtarget_picking_mode")
        else:
            Mgr.enter_state("texprojtarget_picking_mode")

    def __apply_uvs(self):

        Mgr.update_app("uv_projection")


ObjectTypes.add_type("tex_projector", "Texture Projector")
PropertyPanel.add_properties("tex_projector", TexProjectorProperties)

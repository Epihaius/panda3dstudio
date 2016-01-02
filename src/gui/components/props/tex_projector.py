from .base import *


class TargetComboBox(PanelComboBox):

    def __init__(self, panel, container, sizer):

        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)

        PanelComboBox.__init__(self, panel, container, sizer, "Selected target",
                               140, (1.75, 1.75, .9), sizer_args)


class TexProjectorProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}

        self._targets = {}

        section = panel.add_section(
            "tex_projector_props", "Tex. projector properties")
        sizer = section.get_client_sizer()
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        checkbox = PanelCheckBox(panel, section, subsizer,
                                 lambda on: self.__handle_value("on", on))
        self._checkboxes["on"] = checkbox
        section.add_text("On", subsizer, sizer_args)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        section.add_text("Size:", subsizer, sizer_args)
        field = PanelInputField(panel, section, subsizer, 80)
        val_id = "size"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_size)
        self._fields[val_id] = field

        yellow = wx.Colour(255, 255, 0)
        radio_btns = PanelRadioButtonGroup(
            panel, section, "Projection type", dot_color=yellow)

        get_command = lambda projection_type: lambda: self.__set_projection_type(
            projection_type)

        for projection_type in ("orthographic", "perspective"):
            radio_btns.add_button(projection_type, projection_type.title())
            radio_btns.set_button_command(
                projection_type, get_command(projection_type))

        radio_btns.set_selected_button("orthographic")
        self._radio_btns = radio_btns

        group = section.add_group("Lens/Film")
        sizer = group.get_client_sizer()
        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        group.add_text("Width:", subsizer, sizer_args)
        field = PanelInputField(panel, group, subsizer, 80)
        val_id = "film_w"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_size)
        self._fields[val_id] = field
        group.add_text("Height:", subsizer, sizer_args)
        field = PanelInputField(panel, group, subsizer, 80)
        val_id = "film_h"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_size)
        self._fields[val_id] = field
        group.add_text("X offset:", subsizer, sizer_args)
        field = PanelInputField(panel, group, subsizer, 80)
        val_id = "film_x"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_size)
        self._fields[val_id] = field
        group.add_text("Y offset:", subsizer, sizer_args)
        field = PanelInputField(panel, group, subsizer, 80)
        val_id = "film_y"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_size)
        self._fields[val_id] = field

        section = panel.add_section(
            "tex_projector_targets", "Projector targets")
        sizer = section.get_client_sizer()

        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)

        self._target_combobox = PanelComboBox(panel, section, sizer, "Selected target",
                                              164, sizer_args=sizer_args)

        sizer.Add(wx.Size(0, 4))

        btn_sizer = wx.BoxSizer()
        sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        sizer_args = (0, wx.RIGHT, 5)

        label = "Pick"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Add target model",
                          self.__pick_object, sizer_args)
        self._pick_btn = btn

        label = "Remove"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Remove selected target",
                          self.__remove_target, sizer_args)

        label = "Clear"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, btn_sizer, bitmaps, label, "Remove all targets",
                          self.__clear_targets)

        sizer.Add(wx.Size(0, 4))
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        group = section.add_group("Target poly selection")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.FlexGridSizer(rows=0, cols=4, hgap=5)
        grp_sizer.Add(subsizer)
        checkbox = PanelCheckBox(panel, group, subsizer,
                                 lambda val: self.__handle_value("use_poly_sel", val))
        checkbox.check(False)
        checkbox.disable()
        checkbox.add_disabler("no_targets", lambda: not self._targets)
        self._checkboxes["use_poly_sel"] = checkbox
        group.add_text("Use    ", subsizer, sizer_args)
        checkbox = PanelCheckBox(panel, group, subsizer,
                                 lambda val: self.__handle_value("show_poly_sel", val))
        checkbox.check(False)
        checkbox.disable()
        checkbox.add_disabler("no_targets", lambda: not self._targets)
        self._checkboxes["show_poly_sel"] = checkbox
        group.add_text("Show", subsizer, sizer_args)

        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)

        sizer.Add(wx.Size(0, 4))
        section.add_text("Affected UV sets:", sizer, sizer_args)
        field = PanelInputField(panel, section, sizer,
                                164, sizer_args=sizer_args)
        val_id = "uv_set_ids"
        field.add_value(val_id, "custom", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_uv_set_id_string)
        field.set_value_parser(val_id, self.__parse_uv_set_ids)
        field.set_value(val_id, ())
        field.disable()
        field.add_disabler("no_targets", lambda: not self._targets)
        self._fields[val_id] = field

        label = "Apply UVs"
        bitmaps = PanelButton.create_button_bitmaps(
            "*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, sizer, bitmaps, label, "Bake UVs into target vertices",
                          self.__apply_uvs, sizer_args)

    def setup(self):

        def enter_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (100, 255, 100))
            self._pick_btn.set_active()

        def exit_picking_mode(next_state_id, is_active):

            if not is_active:
                self._pick_btn.set_active(False)

        add_state = Mgr.add_state
        add_state("texprojtarget_picking_mode", -10,
                  enter_picking_mode, exit_picking_mode)

    def __set_projection_type(self, projection_type):

        if Mgr.get_global("active_creation_type"):
            Mgr.update_app("tex_projector_prop_default",
                           "projection_type", projection_type)
            return

        Mgr.update_remotely("texproj_prop", "projection_type", projection_type)

    def __handle_value(self, value_id, value):

        if Mgr.get_global("active_creation_type"):
            Mgr.update_app("tex_projector_prop_default", value_id, value)
            return

        if value_id == "use_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["toplvl"] = not value
            value = dict((k, v.copy()) for k, v in self._targets.iteritems())
            target_prop = "use_poly_sel"
        elif value_id == "show_poly_sel":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["show_poly_sel"] = value
            value = dict((k, v.copy()) for k, v in self._targets.iteritems())
            target_prop = "show_poly_sel"
        elif value_id == "uv_set_ids":
            value_id = "targets"
            target_id = self._target_combobox.get_selected_item()
            self._targets[target_id]["uv_set_ids"] = value
            value = dict((k, v.copy()) for k, v in self._targets.iteritems())
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
        field.set_value("uv_set_ids", uv_set_ids)
        self._checkboxes["use_poly_sel"].check(use_poly_sel)
        self._checkboxes["show_poly_sel"].check(show_poly_sel)

    def __remove_target(self):

        if not self._targets:
            return

        target_id = self._target_combobox.get_selected_item()
        value = dict((k, v.copy()) for k, v in self._targets.iteritems())
        del value[target_id]

        Mgr.update_remotely("texproj_prop", "targets", value, target_id=target_id,
                            target_prop="remove")

    def __clear_targets(self):

        if not self._targets:
            return

        value = {}

        Mgr.update_remotely("texproj_prop", "targets",
                            value, target_prop="clear")

    def __parse_size(self, size_str):

        try:
            size = float(size_str)
        except:
            try:
                size = eval(size_str)
            except:
                return None

        return max(.001, size)

    def __parse_uv_set_id_string(self, uv_set_id_str):
        # TODO: use ranges

        try:
            uv_set_ids = tuple(set(sorted(min(7, max(0, int(s)))
                                          for s in uv_set_id_str.replace(" ", "").split(","))))
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

        color = wx.Colour(255, 255, 0)

        if prop_id == "on":
            self._checkboxes["on"].check(value)
            self._checkboxes["on"].set_checkmark_color(color)
        elif prop_id == "projection_type":
            self._radio_btns.set_selected_button(value)
            self._radio_btns.set_dot_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "on":

            self._checkboxes["on"].check(value)

        elif prop_id == "projection_type":

            self._radio_btns.set_selected_button(value)

        elif prop_id == "targets":

            old_targets = self._targets
            new_targets, target_names = value

            if new_targets == old_targets:
                return

            self._targets = new_targets

            field = self._fields["uv_set_ids"]
            checkboxes = self._checkboxes
            combobox = self._target_combobox
            cur_target_id = combobox.get_selected_item()

            if not old_targets:
                field.enable()
                checkboxes["use_poly_sel"].enable()
                checkboxes["show_poly_sel"].enable()

            if cur_target_id in new_targets:

                old_target_data = old_targets[cur_target_id]
                new_target_data = new_targets[cur_target_id]

                if new_target_data != old_target_data:
                    uv_set_ids = new_target_data["uv_set_ids"]
                    use_poly_sel = not new_target_data["toplvl"]
                    show_poly_sel = new_target_data["show_poly_sel"]
                    field.set_value("uv_set_ids", uv_set_ids)
                    checkboxes["use_poly_sel"].check(use_poly_sel)
                    checkboxes["show_poly_sel"].check(show_poly_sel)

            old_target_ids = set(old_targets.keys())
            new_target_ids = set(new_targets.keys())

            if new_target_ids == old_target_ids:
                return

            for target_id in new_target_ids - old_target_ids:
                target_name = target_names[target_id]
                get_command = lambda target_id: lambda: self.__select_target(
                    target_id)
                combobox.add_item(target_id, target_name,
                                  get_command(target_id))
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
                    field.set_value("uv_set_ids", uv_set_ids)
                    checkboxes["use_poly_sel"].check(use_poly_sel)
                    checkboxes["show_poly_sel"].check(show_poly_sel)
                else:
                    field.set_value("uv_set_ids", ())
                    field.disable()
                    checkboxes["use_poly_sel"].check(False)
                    checkboxes["use_poly_sel"].disable()
                    checkboxes["show_poly_sel"].check(False)
                    checkboxes["show_poly_sel"].disable()

        elif prop_id in self._fields:

            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = Mgr.get_global("selection_count")
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        if multi_sel:
            self._checkboxes["on"].check(False)
            self._radio_btns.set_selected_button()

        fields = self._fields

        for val_id in ("size", "film_w", "film_h", "film_x", "film_y"):
            field = fields[val_id]
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkboxes["on"].set_checkmark_color(color)
        self._radio_btns.set_dot_color(color)

    def __pick_object(self):

        if self._pick_btn.is_active():
            Mgr.exit_state("texprojtarget_picking_mode")
        else:
            Mgr.enter_state("texprojtarget_picking_mode")

    def __apply_uvs(self):

        Mgr.update_app("uv_projection")


ObjectTypes.add_type("tex_projector", "Texture Projector")
PropertyPanel.add_properties("tex_projector", TexProjectorProperties)

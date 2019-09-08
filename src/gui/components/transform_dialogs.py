from ..base import *
from ..button import *
from ..toolbar import *
from ..dialog import *


class ValueInputField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, value_id, value_type, handler, width,
                 on_key_enter=None, on_key_escape=None):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, value_id, value_type, handler, width,
                                  INSET1_BORDER_GFX_DATA, self._img_offset,
                                  on_key_enter=on_key_enter, on_key_escape=on_key_escape)

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

        transf_type = GD["active_transform_type"]
        title = f'{transf_type.title()} selection'
        on_cancel = lambda: Mgr.update_remotely("componentwise_xform", "cancel")
        extra_button_data = (("Apply", "", self.__on_apply, None, 1.),)

        Dialog.__init__(self, title, "okcancel", transf_type.title(), self.__on_yes,
                        on_cancel=on_cancel, extra_button_data=extra_button_data)

        value = 1. if transf_type == "scale" else 0.
        rot_axis = GD["axis_constraints"]["rotate"]
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
                tooltip_text = f"Rotate about {axis_text}-axis"
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
                tooltip_text = f"Make {axes_descr} values equal"
                btn = DialogButton(self, text, tooltip_text=tooltip_text)
                btns.add_button(btn, axes, toggle)
                subsizer.add(btn, expand=True, borders=borders)

            for axes in ("xyz", "xy", "yz", "xz"):
                add_toggle(axes)

            if transf_type == "scale":
                btns.set_active_button("xyz")

            subsizer.add((0, 0), proportion=1.)

            group_title = f'Offset {"factors" if transf_type == "scale" else "distances"}'
            group = DialogWidgetGroup(self, group_title)
            borders = (0, 0, 10, 10)
            main_sizer.add(group, proportion=1., borders=borders)
            value = 1. if transf_type == "scale" else 0.

            for axis_id in "xyz":

                subsizer = Sizer("horizontal")
                borders = (0, 0, 5, 0)
                group.add(subsizer, expand=True, borders=borders)

                text = DialogText(group, f"{axis_id.upper()}:")
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

    def __handle_value(self, axis_id, value, state="done"):

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


class CoordSysDialog(Dialog):

    def __init__(self, combobox):

        title = "Reference coordinate system position and orientation"

        def on_yes():

            x = self._fields["x"].get_value()
            y = self._fields["y"].get_value()
            z = self._fields["z"].get_value()
            h = self._fields["h"].get_value()
            p = self._fields["p"].get_value()
            r = self._fields["r"].get_value()
            Mgr.update_remotely("custom_coord_sys_transform", "set", (x, y, z, h, p, r))
            combobox.set_field_tint(None)

        def on_cancel():

            Mgr.update_remotely("custom_coord_sys_transform", "cancel")
            combobox.set_field_tint(None)

        Dialog.__init__(self, title, "okcancel", on_yes=on_yes, on_cancel=on_cancel)

        self._fields = fields = {}

        client_sizer = self.get_client_sizer()

        group = DialogWidgetGroup(self, "World-space coordinates")
        borders = (20, 20, 20, 20)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True)

        handler = lambda *args: None
        pos_hpr = {}
        Mgr.update_remotely("custom_coord_sys_transform", "init", pos_hpr)

        for axis_id in "xyz":
            borders = (0, 5, 0, 0)
            text = DialogText(group, f"{axis_id.upper()}:")
            subsizer.add(text, alignment="center_v", borders=borders)
            field = ValueInputField(group, axis_id, "float", handler, 100)
            field.set_value(pos_hpr[axis_id])
            borders = (0, 10, 0, 0)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
            fields[axis_id] = field

        group = DialogWidgetGroup(self, "World-space angles")
        borders = (20, 20, 20, 0)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True)

        parser = lambda input_text: (float(eval(input_text)) + 180.) % 360. - 180.

        for axis_id, angle_id in zip("xyz", "prh"):
            borders = (0, 5, 0, 0)
            text = DialogText(group, f"{axis_id.upper()}:")
            subsizer.add(text, alignment="center_v", borders=borders)
            field = AngleField(group, angle_id, (-180., 180.), handler, parser, 100)
            field.set_value(pos_hpr[angle_id])
            borders = (0, 10, 0, 0)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
            fields[angle_id] = field

        self.finalize()

    def close(self, answer=""):

        Dialog.close(self, answer)

        self._fields = None


class TransfCenterDialog(Dialog):

    def __init__(self, combobox):

        title = "Transform center position"

        def on_yes():

            x = self._fields["x"].get_value()
            y = self._fields["y"].get_value()
            z = self._fields["z"].get_value()
            Mgr.update_remotely("custom_transf_center_transform", "set", (x, y, z))
            combobox.set_field_tint(None)

        def on_cancel():

            Mgr.update_remotely("custom_transf_center_transform", "cancel")
            combobox.set_field_tint(None)

        Dialog.__init__(self, title, "okcancel", on_yes=on_yes, on_cancel=on_cancel)

        self._fields = fields = {}

        client_sizer = self.get_client_sizer()

        group = DialogWidgetGroup(self, "Grid-space coordinates")
        borders = (20, 20, 20, 20)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True)

        handler = lambda *args: None
        pos = {}
        Mgr.update_remotely("custom_transf_center_transform", "init", pos)

        for axis_id in "xyz":
            borders = (0, 5, 0, 0)
            text = DialogText(group, f"{axis_id.upper()}:")
            subsizer.add(text, alignment="center_v", borders=borders)
            field = ValueInputField(group, axis_id, "float", handler, 100)
            field.set_value(pos[axis_id])
            borders = (0, 10, 0, 0)
            subsizer.add(field, proportion=1., alignment="center_v", borders=borders)
            fields[axis_id] = field

        self.finalize()

    def close(self, answer=""):

        Dialog.close(self, answer)

        self._fields = None


class TransformEntry(ListEntry):

    def __init__(self, parent, name):

        ListEntry.__init__(self, parent)

        data = (("name", name, "left", 0),)
        self.set_data(data)


class TransformPane(ListPane):

    def __init__(self, dialog, names):

        column_data = (("name", 1.),)

        ListPane.__init__(self, dialog, column_data, frame_client_size=(300, 200), multi_select=False)

        for name in names:
            entry = TransformEntry(self, name)
            self.entry_list.append(entry)

    def search_entries(self, text_id, substring, in_selection, match_case, part, find_next=False):

        entries = ListPane.search_entries(self, text_id, substring, in_selection,
                                          match_case, part, find_next)

        if not find_next:
            self.get_ancestor("dialog").set_name(entries[0].get_text("name") if entries else "")

        return entries

    def find_next(self):

        entry = ListPane.find_next(self)
        self.get_ancestor("dialog").set_name(entry.get_text("name") if entry else "")

    def set_selected_entry(self, entry):

        ListPane.set_selected_entry(self, entry)

        self.get_ancestor("dialog").set_name(entry.get_text("name"))


class StoredTransformDialog(ListDialog):

    _entry_listener = DirectObject()

    def __init__(self, command_id, transf_target_name, transf_target):

        transf_descr = "transform" if transf_target == "coord_sys" else "position"
        ok_alias = command_id.title()
        title = f"{ok_alias} {transf_target_name} {transf_descr}"
        updater_id = f"custom_{transf_target}_transform"
        update_type = command_id
        on_yes = lambda: Mgr.update_remotely(updater_id, update_type, self._selected_name)

        ListDialog.__init__(self, title, "okcancel", ok_alias, on_yes, multi_select=False)

        self.accept_extra_dialog_events()

        self._store = store = command_id == "store"
        self._transf_target = transf_target
        self._selected_name = ""
        self._search_options = {"match_case": True, "part": "start"}

        client_sizer = self.get_client_sizer()

        group = self.create_find_group(self.__search_entries,
            self.__set_search_option, True, "start")
        borders = (20, 20, 10, 20)
        client_sizer.add(group, expand=True, borders=borders)

        self._names = []
        Mgr.update_remotely(f"custom_{transf_target}_transform", "get_stored_names", self._names)
        self._names.sort(key=str.casefold)
        self.pane = pane = TransformPane(self, self._names)
        frame = pane.frame
        borders = (20, 20, 10, 0)
        client_sizer.add(frame, proportion=1., expand=True, borders=borders)

        btn_sizer = Sizer("horizontal")
        borders = (20, 20, 10 if store else 20, 0)
        client_sizer.add(btn_sizer, expand=True, borders=borders)

        tooltip_text = f"Rename selected {transf_descr}"
        btn = DialogButton(self, "Rename", "", tooltip_text,
                           command=self.__rename_selected_entry_text)
        btn.set_hotkey(None, "F2")
        borders = (0, 5, 0, 0)
        btn_sizer.add(btn, proportion=1., borders=borders)
        tooltip_text = f"Delete selected {transf_descr}"
        btn = DialogButton(self, "Delete", "", tooltip_text, command=self.__delete_selected_entry)
        btn.set_hotkey(None, "Del")
        btn_sizer.add(btn, proportion=1., borders=borders)
        tooltip_text = f"Delete all {transf_descr}s"
        btn = DialogButton(self, "Clear", "", tooltip_text, command=self.__clear_entries)
        btn_sizer.add(btn, proportion=1.)

        if store:
            on_key_enter = lambda: self.close(answer="yes")
            field = ValueInputField(self, "name", "string", self.__handle_value, 100,
                                    on_key_enter=on_key_enter, on_key_escape=self.close)
            field.set_input_parser(self.__parse_name)
            borders = (20, 20, 20, 0)
            client_sizer.add(field, expand=True, borders=borders)
            self._name_field = field

        # the following code is necessary to update the width of the list entries
        client_sizer.update_min_size()
        client_sizer.set_size(client_sizer.get_size())
        self.pane.finalize()
        self.finalize()

        if store:
            field.on_left_down()
            field._on_left_up()

    def close(self, answer=""):

        def command():

            self.ignore_extra_dialog_events()
            self.pane = None

            if self._store:
                self._name_field = None

            ListDialog.close(self, answer)

        if answer == "yes":
            if not self._selected_name:
                msg = f"Please {'enter a valid' if self._store else 'select a'} name."
                MessageDialog(title="Invalid name",
                              message=msg,
                              choices="ok",
                              icon_id="icon_exclamation")
                return
            elif self._store and self._selected_name in self._names:
                msg = "Transform already exists!\n\nOverwrite?"
                MessageDialog(title="Confirm overwrite transform",
                              message=msg,
                              choices="yesno", on_yes=command,
                              icon_id="icon_exclamation")
                return

        command()

    def accept_extra_dialog_events(self):

        self._entry_listener.accept("gui_f2", self.__rename_selected_entry_text)
        self._entry_listener.accept("gui_delete", self.__delete_selected_entry)

    def ignore_extra_dialog_events(self):

        self._entry_listener.ignore_all()

    def __rename_selected_entry_text(self):

        selected_entry = self.pane.get_selected_entry()

        if selected_entry:

            old_name = selected_entry.get_text("name")

            def validate(new_name):

                if new_name in self._names:
                    msg = "This name is already used.\nPlease enter a new name."
                    MessageDialog(title="Duplicate name",
                                  message=msg,
                                  choices="ok",
                                  icon_id="icon_exclamation")
                    return False

                return True

            def command(new_name):

                self._names.remove(old_name)
                self._names.append(new_name)
                self.update_layout()

                if not self._store:
                    self._selected_name = new_name

                Mgr.update_remotely(f"custom_{self._transf_target}_transform", "rename_stored",
                                    old_name, new_name)

            transf_descr = "transform" if self._transf_target == "coord_sys" else "position"
            title = f"Rename {transf_descr}"
            msg = f"Enter a new name for this {transf_descr}:"
            self.pane.edit_selected_entry_text("name", title, msg, "Rename", validate, command)

    def __delete_selected_entry(self):

        selected_entry = self.pane.get_selected_entry()

        if selected_entry:

            def command():

                name = selected_entry.get_text("name")
                self._names.remove(name)
                self.pane.remove_selected_entry()
                self.update_layout()

                if not self._store:
                    self._selected_name = ""

                Mgr.update_remotely(f"custom_{self._transf_target}_transform",
                                    "delete_stored", name)

            transf_descr = "transform" if self._transf_target == "coord_sys" else "position"
            msg = f"Deleting a {transf_descr} cannot be undone!\n\nContinue?"
            MessageDialog(title=f"Confirm delete {transf_descr}",
                          message=msg,
                          choices="yesno", on_yes=command,
                          icon_id="icon_exclamation")

    def __clear_entries(self):

        if not self._names:
            return

        def command():

            self.pane.clear_entries(destroy_entries=True)
            self.update_layout()
            self._names = []

            if not self._store:
                self._selected_name = ""

            Mgr.update_remotely(f"custom_{self._transf_target}_transform", "clear_stored")

        transf_descr = "transform" if self._transf_target == "coord_sys" else "position"
        msg = f"All {transf_descr}s will be deleted!\n\nContinue?"
        MessageDialog(title=f"Confirm clear {transf_descr}s",
                      message=msg,
                      choices="yesno", on_yes=command,
                      icon_id="icon_exclamation")

    def __set_search_option(self, option, value):

        self._search_options[option] = value

    def __search_entries(self, name):

        match_case = self._search_options["match_case"]
        part = self._search_options["part"]
        self.pane.search_entries("name", name, False, match_case, part)

    def __parse_name(self, input_text):

        name = input_text.strip()

        return name if name else None

    def __handle_value(self, value_id, value, state="done"):

        self._selected_name = value

    def set_name(self, name):

        self._selected_name = name

        if self._store:
            self._name_field.set_value(name)


class TransformOptionsDialog(Dialog):

    def __init__(self):

        old_options = GD["transform_options"]
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

    def __handle_value(self, value_id, value, state="done"):

        if value_id == "radius":
            self._options["rotation"]["circle_radius"] = value
        elif value_id == "full_roll_dist":
            self._options["rotation"]["full_roll_dist"] = value
        elif value_id == "threshold":
            self._options["rotation"]["method_switch_threshold"] = value

    def __on_yes(self):

        old_options = GD["transform_options"]
        old_rot_options = old_options["rotation"]
        new_options = self._options
        new_rot_options = new_options["rotation"]

        for option_id in ("drag_method", "alt_method", "method_switch_threshold",
                "show_circle", "circle_center", "circle_radius", "scale_circle_to_cursor",
                "show_line", "line_thru_gizmo_center", "full_roll_dist"):
            old_rot_options[option_id] = new_rot_options[option_id]

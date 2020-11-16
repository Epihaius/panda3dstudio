from ..base import *
from ..button import *
from ..dialog import *
from .list_dialog import ListEntry, ListPane, ListDialog
from .message_dialog import MessageDialog


class TransformDialog(Dialog):

    def __init__(self):

        transf_type = GD["active_transform_type"]
        on_cancel = lambda: Mgr.update_remotely("componentwise_xform", "cancel")
        extra_button_data = (("Apply", "", self.__on_apply, None, 1.),)

        Dialog.__init__(self, "", "okcancel", transf_type.title(), self.__on_yes,
                        on_cancel=on_cancel, extra_button_data=extra_button_data)

        value_type = "factors" if transf_type == "scale" else "distances"
        text_vars = {"transf_type": transf_type.title(), "value_type": value_type}
        component_ids = ["rotate" if transf_type == "rotate" else "transform"]
        widgets = Skin.layout.create(self, "transform", text_vars, component_ids)
        self._fields = fields = widgets["fields"]
        btns = widgets["buttons"]
        checkbtn = widgets["checkbuttons"]["preview"]

        value = 1. if transf_type == "scale" else 0.
        rot_axis = GD["axis_constraints"]["rotate"]
        self._rot_axis = "z" if rot_axis == "view" else rot_axis
        self._values = values = {axis_id: value for axis_id in "xyz"}
        self._link_values = True if transf_type == "scale" else False
        self._linked_axes = "xyz"
        self._preview = True

        if transf_type == "rotate":

            self._toggle_btns = toggle_btns = ToggleButtonGroup()

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
                btn = btns[axis_id]
                toggle_btns.add_button(btn, axis_id, toggle)

            for axis_id in "xyz":
                add_toggle(axis_id)

            toggle_btns.set_active_button(self._rot_axis)

            def parse_angle_input(input_text):

                try:
                    return (float(eval(input_text)) + 180.) % 360. - 180.
                except:
                    return None

            field = fields["rot_axis"]
            field.value_id = "rot_axis"
            field.set_value_handler(self.__handle_value)
            field.set_value_range((-180., 180.), False, "float")
            field.set_input_parser(parse_angle_input)
            field.set_value(0.)

        else:

            self._toggle_btns = toggle_btns = ToggleButtonGroup()

            def unlink_values():

                self._toggle_btns.deactivate()
                self._link_values = False

            toggle_btns.set_default_toggle("", (unlink_values, lambda: None))

            def add_toggle(axes):

                def toggle_on():

                    self._toggle_btns.set_active_button(axes)
                    self._link_values = True
                    self._linked_axes = axes
                    fields = self._fields

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
                btn = btns[axes]
                toggle_btns.add_button(btn, axes, toggle)

            for axes in ("xyz", "xy", "yz", "xz"):
                add_toggle(axes)

            if transf_type == "scale":
                toggle_btns.set_active_button("xyz")

            value = 1. if transf_type == "scale" else 0.

            for axis_id in "xyz":
                field = fields[axis_id]
                field.value_id = axis_id
                field.set_value_handler(self.__handle_value)
                field.set_value_range(None, False, "float")
                field.set_step(.01)
                field.set_value(value)

        def enable_preview(preview):

            self._preview = preview
            Mgr.update_remotely("componentwise_xform", "", values, "done", preview, not preview)

        checkbtn.command = enable_preview
        checkbtn.check()

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

        Dialog.__init__(self, "", "okcancel", on_yes=on_yes, on_cancel=on_cancel)

        widgets = Skin.layout.create(self, "coord_sys")
        self._fields = fields = widgets["fields"]

        handler = lambda *args: None
        pos_hpr = {}
        Mgr.update_remotely("custom_coord_sys_transform", "init", pos_hpr)

        for axis_id in "xyz":
            field = fields[axis_id]
            field.value_id = axis_id
            field.set_value_handler(handler)
            field.set_value_range(None, False, "float")
            field.set_step(.01)
            field.set_value(pos_hpr[axis_id])

        def parse_angle_input(input_text):

            try:
                return (float(eval(input_text)) + 180.) % 360. - 180.
            except:
                return None

        for angle_id in "prh":
            field = fields[angle_id]
            field.value_id = angle_id
            field.set_value_handler(handler)
            field.set_value_range((-180., 180.), False, "float")
            field.set_input_parser(parse_angle_input)
            field.set_value(pos_hpr[angle_id])

        self.finalize()

    def close(self, answer=""):

        Dialog.close(self, answer)

        self._fields = None


class TransfCenterDialog(Dialog):

    def __init__(self, combobox):

        def on_yes():

            x = self._fields["x"].get_value()
            y = self._fields["y"].get_value()
            z = self._fields["z"].get_value()
            Mgr.update_remotely("custom_transf_center_transform", "set", (x, y, z))
            combobox.set_field_tint(None)

        def on_cancel():

            Mgr.update_remotely("custom_transf_center_transform", "cancel")
            combobox.set_field_tint(None)

        Dialog.__init__(self, "", "okcancel", on_yes=on_yes, on_cancel=on_cancel)

        widgets = Skin.layout.create(self, "transf_center")
        self._fields = fields = widgets["fields"]

        handler = lambda *args: None
        pos = {}
        Mgr.update_remotely("custom_transf_center_transform", "init", pos)

        for axis_id in "xyz":
            field = fields[axis_id]
            field.value_id = axis_id
            field.set_value_handler(handler)
            field.set_value_range(None, False, "float")
            field.set_step(.01)
            field.set_value(pos[axis_id])

        self.finalize()

    def close(self, answer=""):

        Dialog.close(self, answer)

        self._fields = None


class TransformEntry(ListEntry):

    def __init__(self, parent, name):

        ListEntry.__init__(self, parent)

        data = (("name", name, "min", 0, 0.),)
        self.set_data(data, Skin.layout.borders["xform_dialog_entry_data"])


class TransformPane(ListPane):

    def __init__(self, parent, names):

        column_data = (("name", 1.),)
        borders = Skin.layout.borders["xform_dialog_entry_column"]
        frame_client_size = (
            Skin.options["xform_dialog_scrollpane_width"],
            Skin.options["xform_dialog_scrollpane_height"]
        )

        ListPane.__init__(self, parent, column_data, borders, frame_client_size,
            multi_select=False)

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

    def __init__(self, op_type, transf_target_name, transf_target):

        transf_descr = "transform" if transf_target == "coord_sys" else "position"
        ok_alias = op_type.title()
        updater_id = f"custom_{transf_target}_transform"
        update_type = op_type
        on_yes = lambda: Mgr.update_remotely(updater_id, update_type, self._selected_name)

        ListDialog.__init__(self, "", "okcancel", ok_alias, on_yes, multi_select=False)

        self._store = store = op_type == "store"
        self._transf_target = transf_target
        self._selected_name = ""
        self._search_options = {"match_case": True, "part": "start"}

        text_vars = {"op_type": ok_alias, "target_name": transf_target_name, "descr": transf_descr}
        component_ids = ["name field"] if store else None
        widgets = Skin.layout.create(self, "stored_transforms", text_vars, component_ids)
        pane_cell = widgets["placeholders"]["pane"]
        fields = widgets["fields"]
        btns = widgets["buttons"]

        self.accept_extra_dialog_events()

        self.setup_search_interface(widgets, self.__search_entries,
            self.__set_search_option, True, "start")

        self._names = []
        Mgr.update_remotely(f"custom_{transf_target}_transform", "get_stored_names", self._names)
        self._names.sort(key=str.casefold)
        parent = pane_cell.sizer.owner_widget
        self.pane = pane = TransformPane(parent, self._names)
        pane_cell.object = pane.frame

        btn = btns["rename"]
        btn.command = self.__rename_selected_entry_text
        btn.set_hotkey(None, "F2")

        btn = btns["delete"]
        btn.command = self.__delete_selected_entry
        btn.set_hotkey(None, "Del")

        btn = btns["clear"]
        btn.command = self.__clear_entries

        if store:
            self._name_field = field = fields["name"]
            field.value_id = "name"
            field.value_type = "string"
            field.set_value_handler(self.__handle_value)
            field.set_on_key_enter(lambda: self.close(answer="yes"))
            field.set_on_key_escape(self.close)
            field.set_input_parser(self.__parse_name)

        # the following code is necessary to update the width of the list entries
        client_sizer = self.client_sizer
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

        Dialog.__init__(self, "", "okcancel", on_yes=self.__on_yes)

        widgets = Skin.layout.create(self, "transform_options")
        self._combobox = combobox = widgets["comboboxes"]["drag_method"]
        radio_btn_grps = widgets["radiobutton_groups"]
        checkbtns = widgets["checkbuttons"]
        fields = widgets["fields"]

        def set_drag_method(method_id):

            self._combobox.select_item(method_id)
            new_rot_options["drag_method"] = method_id

        method_ids = ("circular_in_rot_plane", "circular_in_view_plane", "linear")
        method_names = ("circular in rotation plane", "circular in view plane", "linear")

        for method_id, method_name in zip(method_ids, method_names):
            command = lambda m=method_id: set_drag_method(m)
            combobox.add_item(method_id, method_name, command)

        combobox.update_popup_menu()
        combobox.select_item(old_rot_options["drag_method"])

        radio_btns = radio_btn_grps["circle_center"]

        def set_circle_center(center_id):

            new_rot_options["circle_center"] = center_id

        for center_id in ("start_click_pos", "gizmo_center"):
            command = lambda c=center_id: set_circle_center(c)
            radio_btns.set_button_command(center_id, command)

        radio_btns.set_selected_button(old_rot_options["circle_center"])

        def show_viz(show):

            new_rot_options["show_circle"] = show

        checkbtn = checkbtns["show_circle"]
        checkbtn.command = show_viz
        checkbtn.check(old_rot_options["show_circle"])

        field = fields["radius"]
        field.value_id = "radius"
        field.set_value_handler(self.__handle_value)
        field.set_value_range((1, None), False, "int")
        field.set_step(1)
        field.set_input_parser(self.__parse_input)
        field.set_value(old_rot_options["circle_radius"])

        def scale_to_cursor(to_cursor):

            new_rot_options["scale_circle_to_cursor"] = to_cursor

        checkbtn = checkbtns["scale_to_cursor"]
        checkbtn.command = scale_to_cursor
        checkbtn.check(old_rot_options["scale_circle_to_cursor"])

        def show_viz(show):

            new_rot_options["show_line"] = show

        checkbtn = checkbtns["show_line"]
        checkbtn.command = show_viz
        checkbtn.check(old_rot_options["show_line"])

        def thru_gizmo_center(thru_gizmo):

            new_rot_options["line_thru_gizmo_center"] = thru_gizmo

        checkbtn = checkbtns["thru_gizmo_center"]
        checkbtn.command = thru_gizmo_center
        checkbtn.check(old_rot_options["line_thru_gizmo_center"])

        option_id = "full_roll_dist"
        field = fields[option_id]
        field.value_id = option_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((1, None), False, "int")
        field.set_step(1)
        field.set_input_parser(self.__parse_input)
        field.set_value(old_rot_options[option_id])

        radio_btns = radio_btn_grps["alt_method"]

        def set_alt_method(method_id):

            new_rot_options["alt_method"] = method_id

        for method_id in method_ids[1:]:
            command = lambda m=method_id: set_alt_method(m)
            radio_btns.set_button_command(method_id, command)

        radio_btns.set_selected_button(old_rot_options["alt_method"])

        field = fields["threshold"]
        field.value_id = "threshold"
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 91.), False, "float")
        field.set_step(1.)
        field.set_value(old_rot_options["method_switch_threshold"])

        self.finalize()

    def close(self, answer=""):

        Dialog.close(self, answer)

        self._combobox = None

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

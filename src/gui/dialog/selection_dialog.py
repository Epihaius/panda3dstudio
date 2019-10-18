from .dialog import *
from .list_dialog import ListEntry, ListPane, ListDialog


class SelectionEntry(ListEntry):

    def __init__(self, parent, obj_data):

        ListEntry.__init__(self, parent)

        obj_id, obj_sel_state, obj_name, obj_type = obj_data
        self._obj_id = obj_id

        data = (
            ("", "*", "center", 20) if obj_sel_state else ("", "", "left", 20),
            ("name", obj_name, "left", 0),
            ("type", obj_type.title(), "right", 0)
        )
        self.set_data(data)

    def get_object_id(self):

        return self._obj_id

    def get_object_name(self):

        return self.get_text("name")

    def get_object_type(self):

        return self.get_text("type").lower()


class SelectionPane(ListPane):

    def __init__(self, dialog, object_types, obj_data, multi_select):

        column_data = (("sel_state", 0.), ("name", 1.), ("type", 0.))

        ListPane.__init__(self, dialog, column_data, multi_select=multi_select)

        sel_dialog_config = GD["config"]["sel_dialog"]
        obj_types = object_types if object_types else sel_dialog_config["obj_types"]
        self._entries_by_name = entries_by_name = {}
        self._entries_by_type = entries_by_type = {}
        self._entries_sorted_by_name = by_name = []
        self._entries_sorted_by_type = by_type = []
        self.entry_list = by_name if sel_dialog_config["sort"] == "name" else by_type

        shown_entries = []
        shown_by_type = {}

        for obj_type, value in obj_data.items():
            for obj_id, obj_sel_state, obj_name in value:
                data_ext = (obj_id, obj_sel_state, obj_name, obj_type)
                entry = SelectionEntry(self, data_ext)
                if obj_type in obj_types:
                    shown_entries.append(entry)
                entries_by_type.setdefault(obj_type, []).append(entry)
                entries_by_name[obj_name] = entry

        for entry in shown_entries:
            by_name.append(entry.get_object_name())
            shown_by_type.setdefault(entry.get_object_type(), []).append(entry.get_object_name())

        sort_case = GD["config"]["sel_dialog"]["sort_case"]

        by_name.sort() if sort_case else by_name.sort(key=str.casefold)
        by_name[:] = [entries_by_name[name] for name in by_name]

        for obj_type in obj_types:
            names = shown_by_type.get(obj_type, [])
            sorted_names = sorted(names) if sort_case else sorted(names, key=str.casefold)
            by_type.extend([entries_by_name[name] for name in sorted_names])

    def destroy(self):

        ListPane.destroy(self)

        self._entries_by_name = {}
        self._entries_by_type = {}
        self._entries_sorted_by_name = []
        self._entries_sorted_by_type = []

    def show_object_types(self, obj_types):

        entries_by_name = self._entries_by_name
        entries_by_type = self._entries_by_type
        by_name = self._entries_sorted_by_name
        by_type = self._entries_sorted_by_type
        entry_list = self.entry_list
        old_entries = set(entry_list)
        self.clear_entries()
        del by_name[:]
        del by_type[:]

        shown_entries = []
        shown_by_type = {}

        for obj_type in obj_types:
            for entry in entries_by_type.get(obj_type, []):
                shown_entries.append(entry)

        for entry in shown_entries:
            by_name.append(entry.get_object_name())
            shown_by_type.setdefault(entry.get_object_type(), []).append(entry.get_object_name())

        sort_case = GD["config"]["sel_dialog"]["sort_case"]

        by_name.sort() if sort_case else by_name.sort(key=str.casefold)
        by_name[:] = [entries_by_name[name] for name in by_name]

        for obj_type in obj_types:
            names = shown_by_type.get(obj_type, [])
            sorted_names = sorted(names) if sort_case else sorted(names, key=str.casefold)
            by_type.extend([entries_by_name[name] for name in sorted_names])

        self.add_entries()

        for entry in entry_list:
            entry.show()

        for entry in old_entries.difference(entry_list):
            entry.hide()
            entry.set_selected(False)

        self.get_ancestor("dialog").update_layout()
        self.check_selection_start_entry()

        if self.multi_select:
            self.get_ancestor("dialog").hide_set_name()

    def sort_entries(self, sort_by):

        self.entry_list = self._entries_sorted_by_name \
            if sort_by == "name" else self._entries_sorted_by_type

        self.clear_entries()
        self.add_entries()

        self.get_ancestor("dialog").update_layout()

    def set_selected_entry(self, entry):

        ListPane.set_selected_entry(self, entry)

        if self.multi_select:
            self.get_ancestor("dialog").hide_set_name()

    def toggle_selected_entry(self, entry):

        if ListPane.toggle_selected_entry(self, entry):
            self.get_ancestor("dialog").hide_set_name()

    def set_selected_entry_range(self, end_entry):

        if ListPane.set_selected_entry_range(self, end_entry):
            self.get_ancestor("dialog").hide_set_name()

    def modify_selection(self, mod):

        if ListPane.modify_selection(self, mod):
            self.get_ancestor("dialog").hide_set_name()

    def select_from_set(self, selection_set):

        if not self.multi_select:
            return

        entries = [e for e in self.entry_list if e.get_object_id() in selection_set]
        self.select(entries)

    def get_selection(self):

        return [e.get_object_id() for e in self.entry_list if e.is_selected()]


class SelectionDialog(ListDialog):

    def __init__(self, title="Select objects", object_types=None, multi_select=True,
                 ok_alias="Select", handler=None):

        if handler is None:
            on_yes = self.__set_selection
        else:
            on_yes = lambda: handler(self._selection_ids)

        ListDialog.__init__(self, title, "okcancel", ok_alias, on_yes, multi_select)

        self._selection_ids = []
        self._checkbuttons = {}
        self._search_in_selection = False
        self._obj_types = ["model", "helper", "group", "light", "camera"]
        client_sizer = self.get_client_sizer()
        subsizer = Sizer("horizontal")
        client_sizer.add(subsizer)
        column1_sizer = Sizer("vertical")
        borders = (20, 20, 0, 20)
        subsizer.add(column1_sizer, proportion=1., expand=True, borders=borders)

        sel_dialog_config = GD["config"]["sel_dialog"]
        match_case = sel_dialog_config["search"]["match_case"]
        part = sel_dialog_config["search"]["part"]

        group = self.create_find_group(self.__search_entries,
            self.__set_search_option, match_case, part)
        borders = (0, 0, 10, 0)
        column1_sizer.add(group, expand=True, borders=borders)

        obj_data = {}
        sel_set_data = {}
        Mgr.update_remotely("object_selection", "get_data", obj_data, sel_set_data)
        self.pane = pane = SelectionPane(self, object_types, obj_data, multi_select)
        frame = pane.frame
        borders = (0, 0, 5, 0)
        column1_sizer.add(frame, proportion=1., expand=True, borders=borders)

        if multi_select:
            btn_sizer = self.create_selection_buttons()
            column1_sizer.add(btn_sizer, expand=True)

        column2_sizer = Sizer("vertical")
        borders = (0, 20, 0, 20)
        subsizer.add(column2_sizer, proportion=1., expand=True, borders=borders)

        group = DialogWidgetGroup(self, "Sort by")
        borders = (0, 0, 10, 0)
        column2_sizer.add(group, expand=True, borders=borders)

        grp_subsizer = Sizer("horizontal")
        group.add(grp_subsizer)

        radio_btns = DialogRadioButtonGroup(group, columns=1)
        btn_ids = ("name", "type")
        texts = ("Name", "Type")
        get_command = lambda sort_by: lambda: self.__sort_entries(sort_by)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            radio_btns.set_button_command(btn_id, get_command(btn_id))

        radio_btns.set_selected_button(sel_dialog_config["sort"])
        grp_subsizer.add(radio_btns.sizer)

        text = "Case-sensitive"
        checkbtn = DialogCheckButton(group, lambda on:
            self.__set_case_sort(on, object_types), text)
        checkbtn.check(sel_dialog_config["sort_case"])
        borders = (20, 0, 0, 0)
        grp_subsizer.add(checkbtn, borders=borders, alignment="center_v")

        group = DialogWidgetGroup(self, "Object types")
        borders = (0, 0, 10, 0)
        column2_sizer.add(group, expand=True, proportion=1., borders=borders)

        borders = (0, 20, 2, 0)
        type_names = ("Models", "Helpers", "Groups", "Lights", "Cameras")
        obj_types = object_types if object_types else sel_dialog_config["obj_types"]
        checkbox_handler = lambda *args: self.__show_object_types(object_types)

        for obj_type, type_name in zip(self._obj_types, type_names):

            checkbtn = DialogCheckButton(group, checkbox_handler, type_name)
            checkbtn.check(obj_type in obj_types)
            group.add(checkbtn, borders=borders)
            self._checkbuttons[obj_type] = checkbtn

            if object_types and obj_type not in obj_types:
                checkbtn.enable(False)

        group.add((0, 10), proportion=1.)

        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)
        btns = []
        btn = DialogButton(group, "All", command=lambda: self.__modify_types("all"))
        btns.append(btn)
        borders = (0, 5, 0, 0)
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(group, "None", command=lambda: self.__modify_types("none"))
        btns.append(btn)
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(group, "Invert", command=lambda: self.__modify_types("invert"))
        btns.append(btn)
        btn_sizer.add(btn, proportion=1.)

        if object_types:
            for btn in btns:
                btn.enable(False)

        if multi_select:

            group = DialogWidgetGroup(self, "Selection set")
            column2_sizer.add(group, expand=True)

            combobox = DialogComboBox(group, 150, tooltip_text="Selection set")
            self._set_combobox = combobox
            group.add(combobox, expand=True)
            sets = sel_set_data["sets"]
            get_command = lambda set_id: lambda: self.__select_from_set(sets, set_id)

            for set_id, set_name in sel_set_data["names"].items():
                combobox.add_item(set_id, set_name, get_command(set_id), select_initial=False)

            combobox.update_popup_menu()

        info = ""

        if multi_select:
            info += "Shift-click to select range; Ctrl-click to toggle selection state.\n"

        info += "Names of currently selected objects are preceded by an asterisk (*)."
        text = DialogText(self, info)
        borders = (20, 20, 20, 20)
        client_sizer.add(text, expand=True, borders=borders)

        # the following code is necessary to update the width of the list entries
        client_sizer.update_min_size()
        client_sizer.set_size(client_sizer.get_size())
        self.pane.finalize()
        self.finalize()

    def close(self, answer=""):

        self._checkbuttons = None

        if answer == "yes":
            self._selection_ids = self.pane.get_selection()

        self.pane = None

        ListDialog.close(self, answer)

        self._selection_ids = []

    def __show_object_types(self, object_types):

        checkbtns = self._checkbuttons
        obj_types = [o_type for o_type in self._obj_types if checkbtns[o_type].is_checked()]

        if not object_types:

            config_data = GD["config"]
            config_data["sel_dialog"]["obj_types"] = obj_types

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

        self.pane.show_object_types(obj_types)

    def __modify_types(self, mod):

        checkbtns = self._checkbuttons

        if mod == "all":
            obj_types = self._obj_types[:]
        elif mod == "none":
            obj_types = []
        elif mod == "invert":
            obj_types = [o_type for o_type in self._obj_types
                         if not checkbtns[o_type].is_checked()]

        for obj_type in self._obj_types:
            checkbtns[obj_type].check(obj_type in obj_types)

        config_data = GD["config"]
        config_data["sel_dialog"]["obj_types"] = obj_types

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self.pane.show_object_types(obj_types)

    def __set_case_sort(self, on, object_types):

        config_data = GD["config"]
        config_data["sel_dialog"]["sort_case"] = on

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self.__show_object_types(object_types)

    def __sort_entries(self, sort_by):

        config_data = GD["config"]
        config_data["sel_dialog"]["sort"] = sort_by

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self.pane.sort_entries(sort_by)

    def __set_search_option(self, option, value):

        if option == "in_sel":
            self._search_in_selection = value
            return

        config_data = GD["config"]
        config_data["sel_dialog"]["search"][option] = value

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __search_entries(self, name):

        in_selection = self._search_in_selection
        search_config = GD["config"]["sel_dialog"]["search"]
        match_case = search_config["match_case"]
        part = search_config["part"]
        self.pane.search_entries("name", name, in_selection, match_case, part)

        if self.multi_select:
            self.hide_set_name()

    def __select_from_set(self, sets, set_id):

        selection_set = sets[set_id]
        self._set_combobox.select_item(set_id)
        self.pane.select_from_set(selection_set)

    def __set_selection(self):

        Mgr.update_remotely("object_selection", "replace", *self._selection_ids)

    def hide_set_name(self):

        self._set_combobox.select_none()

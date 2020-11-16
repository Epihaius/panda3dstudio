from ...base import *
from ...button import *
from ...panel import *


class UVSetPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "uv_set")

        widgets = Skin.layout.create(self, "uv_set")
        self._btns = btns = widgets["buttons"]
        self._comboboxes = widgets["comboboxes"]
        self._fields = widgets["fields"]

        # *********************** Active UV set section ************************

        self._uv_set_btns = uv_set_btns = ToggleButtonGroup()

        def set_active_uv_set(uv_set_id):

            self._uv_set_btns.set_active_button(str(uv_set_id))
            Mgr.update_interface_remotely("uv", "active_uv_set", uv_set_id)

        for i in range(8):
            btn = btns[str(i)]
            command = lambda set_id=i: set_active_uv_set(set_id)
            toggle = (command, lambda: None)
            uv_set_btns.add_button(btn, str(i), toggle)

        uv_set_btns.set_active_button("0")

        btn = btns["copy"]
        btn.command = lambda: Mgr.update_interface_remotely("uv", "uv_set_copy")

        btn = btns["paste"]
        btn.command = lambda: Mgr.update_interface_remotely("uv", "uv_set_paste")

        # ************************ UV set name section *************************

        val_id = "uv_name"
        field = self._fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_input_parser(self.__parse_uv_name)
        field.set_value_handler(self.__handle_value)

    def setup(self):

        self.get_section("uv_set_name").expand(False)

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_name_targets", self.__set_uv_name_targets, interface_id="uv")
        Mgr.add_app_updater("uv_name", self.__set_uv_name, interface_id="uv")
        Mgr.add_app_updater("target_uv_name", self.__set_target_uv_name, interface_id="uv")

    def __select_uv_name_target(self, obj_id):

        self._comboboxes["uv_name_target"].select_item(obj_id)
        Mgr.update_interface_remotely("uv", "uv_name_target_select", obj_id)

    def __set_uv_name_targets(self, names):

        self._uv_set_btns.set_active_button("0")
        combobox = self._comboboxes["uv_name_target"]
        combobox.clear()
        name_field = self._fields["uv_name"]

        if names:
            combobox.enable()
            name_field.enable()
        else:
            combobox.enable(False)
            name_field.enable(False)
            return

        for obj_id, name in names.items():
            command = lambda o=obj_id: self.__select_uv_name_target(o)
            combobox.add_item(obj_id, name, command)

        combobox.update_popup_menu()
        obj_id = list(names.keys())[0]
        self.__select_uv_name_target(obj_id)

    def __handle_value(self, value_id, value, state="done"):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()
        Mgr.update_interface_remotely("uv", value_id, obj_id, value)

    def __parse_uv_name(self, input_text):

        return input_text.strip().replace(".", "")

    def __set_uv_name(self, uv_set_name):

        self._fields["uv_name"].set_value(uv_set_name)

    def __set_target_uv_name(self, uv_set_names):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()

        if obj_id:
            uv_set_name = uv_set_names[obj_id]
            self._fields["uv_name"].set_value(uv_set_name)

from ...base import *
from ...button import *
from ...panel import *


class UVSetPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "uv_set", "UV sets")

        self._btns = {}
        self._comboboxes = {}
        self._fields = {}

        # *********************** Active UV set section ************************

        section = self.add_section("active_uv_set", "Active UV set")

        self._uv_set_btns = uv_set_btns = ToggleButtonGroup()

        def set_active_uv_set(uv_set_id):

            self._uv_set_btns.set_active_button(str(uv_set_id))
            Mgr.update_interface_remotely("uv", "active_uv_set", uv_set_id)

        get_command = lambda i: lambda: set_active_uv_set(i)

        sizer = GridSizer(rows=0, columns=4, gap_h=5, gap_v=5)
        borders = (5, 5, 5, 5)
        section.add(sizer, expand=True, borders=borders)

        for i in range(8):
            text = str(i)
            tooltip_text = "UV set {:d}".format(i)
            btn = PanelButton(section, text, "", tooltip_text)
            toggle = (get_command(i), lambda: None)
            uv_set_btns.add_button(btn, str(i), toggle)
            sizer.add(btn, proportion_h=1.)

        uv_set_btns.set_active_button("0")

        btn_sizer = Sizer("horizontal")
        borders = (10, 10, 0, 10)
        section.add(btn_sizer, expand=True, borders=borders)

        text = "Copy"
        tooltip_text = "Copy active UV set"
        command = lambda: Mgr.update_interface_remotely("uv", "uv_set_copy")
        btn = PanelButton(section, text, "", tooltip_text, command)
        btn_sizer.add(btn, proportion=1.)
        btn_sizer.add((20, 0))

        text = "Paste"
        tooltip_text = "Replace active UV set with copied one"
        command = lambda: Mgr.update_interface_remotely("uv", "uv_set_paste")
        btn = PanelButton(section, text, "", tooltip_text, command)
        btn_sizer.add(btn, proportion=1.)

        # ************************ UV set name section *************************

        section = self.add_section("uv_set_name", "Active UV set name")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "For"
        borders = (0, 5, 0, 0)
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        combobox = PanelComboBox(section, 60, tooltip_text="Object")
        self._comboboxes["uv_name_target"] = combobox
        sizer.add(combobox, proportion=1., alignment="center_v")

        field = PanelInputField(section, 50)
        val_id = "uv_name"
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_input_parser(val_id, self.__parse_uv_name)
        self._fields[val_id] = field
        borders = (0, 0, 0, 10)
        section.add(field, expand=True, borders=borders)

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

        combobox = self._comboboxes["uv_name_target"]
        # TODO: clear combobox popup menu
        name_field = self._fields["uv_name"]

        if not names:
            combobox.enable(False)
            self._fields["uv_name"].enable(False)
            return

        get_command = lambda obj_id: lambda: self.__select_uv_name_target(obj_id)

        for obj_id, name in names.items():
            combobox.add_item(obj_id, name, get_command(obj_id))

        combobox.update_popup_menu()
        obj_id = list(names.keys())[0]
        self.__select_uv_name_target(obj_id)

    def __handle_value(self, value_id, value):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()
        Mgr.update_interface_remotely("uv", value_id, obj_id, value)

    def __parse_uv_name(self, name):

        parsed_name = name.strip().replace(".", "")

        return parsed_name

    def __set_uv_name(self, uv_set_name):

        self._fields["uv_name"].set_value("uv_name", uv_set_name, handle_value=False)

    def __set_target_uv_name(self, uv_set_names):

        obj_id = self._comboboxes["uv_name_target"].get_selected_item()
        uv_set_name = uv_set_names[obj_id]
        self._fields["uv_name"].set_value("uv_name", uv_set_name, handle_value=False)

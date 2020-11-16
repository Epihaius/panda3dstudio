from .base import *


class GroupProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._btns = {}
        self._checkbuttons = {}
        self._comboboxes = {}

        btn = widgets["buttons"]["group_open"]
        btn.command = lambda: Mgr.update_remotely("group", "open", True)

        checkbtn = widgets["checkbuttons"]["recursive_open"]
        checkbtn.command = self.__toggle_recursive_open
        self._checkbuttons["recursive_open"] = checkbtn

        btn = widgets["buttons"]["group_close"]
        btn.command = lambda: Mgr.update_remotely("group", "open", False)

        btn = widgets["buttons"]["group_dissolve"]
        btn.command = lambda: Mgr.update_remotely("group", "dissolve")

        checkbtn = widgets["checkbuttons"]["recursive_dissolve"]
        checkbtn.command = self.__toggle_recursive_dissolve
        self._checkbuttons["recursive_dissolve"] = checkbtn

        member_types = ["any", "model", "dummy", "point", "tex_projector", "collision",
                        "helper", "model+helper", "model+collision"]
        type_descr = ["Any", "Model", "Dummy helper", "Point helper", "Tex. projector",
                      "Collision geometry", "Any helper", "Model + any helper",
                      "Model + coll. geom."]

        combobox = widgets["comboboxes"]["member_types"]

        for member_type, descr in zip(member_types, type_descr):
            command = lambda m=member_type: Mgr.update_remotely("group", "set_member_types", m)
            combobox.add_item(member_type, descr, command)

        combobox.update_popup_menu()
        self._comboboxes["member_types"] = combobox

        checkbtn = widgets["checkbuttons"]["recursive_member_selection"]
        checkbtn.command = self.__toggle_recursive_member_selection
        self._checkbuttons["recursive_member_selection"] = checkbtn

        checkbtn = widgets["checkbuttons"]["subgroup_selection"]
        checkbtn.command = self.__toggle_subgroup_selection
        self._checkbuttons["subgroup_selection"] = checkbtn

        btn = widgets["buttons"]["select_members"]
        btn.command = lambda: Mgr.update_remotely("group", "select_members")

        Mgr.add_app_updater("group_options", self.__update_group_options)

    def setup(self): pass

    def __update_group_options(self):

        for option, value in GD["group_options"]["main"].items():
            self._checkbuttons[option].check(value)

    def __toggle_recursive_open(self, recursive):

        GD["group_options"]["main"]["recursive_open"] = recursive

    def __toggle_recursive_dissolve(self, recursive):

        GD["group_options"]["main"]["recursive_dissolve"] = recursive

    def __toggle_recursive_member_selection(self, recursive):

        GD["group_options"]["main"]["recursive_member_selection"] = recursive

    def __toggle_subgroup_selection(self, select):

        GD["group_options"]["main"]["subgroup_selection"] = select

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["group_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value): pass

    def set_object_property(self, prop_id, value):

        if prop_id == "member_types":
            self._comboboxes["member_types"].select_item(value)
            self.check_selection_count()

    def check_selection_count(self):

        sel_count = GD["selection_count"]

        if sel_count > 1:
            self._comboboxes["member_types"].select_none()


PropertyPanel.add_properties("group", GroupProperties)

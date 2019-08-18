from .base import *


class GroupProperties:

    def __init__(self, panel):

        self._panel = panel
        self._btns = {}
        self._checkbuttons = {}
        self._comboboxes = {}

        section = panel.add_section("group_props", "Group properties", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=5)
        section.add(sizer, expand=True)

        text = "Open"
        tooltip_text = "Make members accessible"
        command = lambda: Mgr.update_remotely("group", "open", True)
        btn = PanelButton(section, text, "", tooltip_text, command)
        sizer.add(btn, proportion_h=1., alignment_v="center_v")
        text = "recursively"
        checkbtn = PanelCheckButton(section, self.__toggle_recursive_open, text)
        self._checkbuttons["recursive_open"] = checkbtn
        sizer.add(checkbtn, alignment_v="center_v")

        text = "Close"
        tooltip_text = "Make members inaccessible"
        command = lambda: Mgr.update_remotely("group", "open", False)
        btn = PanelButton(section, text, "", tooltip_text, command)
        sizer.add(btn, stretch_h=True)

        sizer.add((0, 0))

        text = "Dissolve"
        tooltip_text = "Ungroup members and delete"
        command = lambda: Mgr.update_remotely("group", "dissolve")
        btn = PanelButton(section, text, "", tooltip_text, command)
        sizer.add(btn, proportion_h=1., alignment_v="center_v")
        text = "recursively"
        checkbtn = PanelCheckButton(section, self.__toggle_recursive_dissolve, text)
        self._checkbuttons["recursive_dissolve"] = checkbtn
        sizer.add(checkbtn, alignment_v="center_v")

        group = section.add_group("Member types")

        def get_command(member_types):

            def set_member_types():

                Mgr.update_remotely("group", "set_member_types", member_types)

            return set_member_types

        member_types = ["any", "model", "dummy", "point", "tex_projector", "collision",
                        "helper", "model+helper", "model+collision"]
        type_descr = ["Any", "Model", "Dummy helper", "Point helper", "Tex. projector",
                      "Collision geometry", "Any helper", "Model + any helper",
                      "Model + coll. geom."]

        combobox = PanelComboBox(group, 145, tooltip_text="Member types")
        group.add(combobox, expand=True)

        for member_type, descr in zip(member_types, type_descr):
            combobox.add_item(member_type, descr, get_command(member_type))

        combobox.update_popup_menu()
        self._comboboxes["member_types"] = combobox

        section.add((0, 5))

        group = section.add_group("Member selection")
        borders = (0, 0, 3, 0)

        text = "Recursively"
        checkbtn = PanelCheckButton(group, self.__toggle_recursive_member_selection, text)
        self._checkbuttons["recursive_member_selection"] = checkbtn
        group.add(checkbtn, borders=borders)

        text = "Select subgroups"
        checkbtn = PanelCheckButton(group, self.__toggle_subgroup_selection, text)
        self._checkbuttons["subgroup_selection"] = checkbtn
        group.add(checkbtn, borders=borders)

        text = "Select"
        tooltip_text = "Open group and select members"
        command = lambda: Mgr.update_remotely("group", "select_members")
        btn = PanelButton(group, text, "", tooltip_text, command)
        group.add(btn, alignment="center_h")

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

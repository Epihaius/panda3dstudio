from .base import *


class GroupProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._btns = {}
        self._checkboxes = {}
        self._comboboxes = {}

        section = panel.add_section("group_props", "Group properties")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=5, vgap=2)
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        label = "Close"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label,
                          "Make members inaccessible",
                          lambda: Mgr.update_remotely("group", "open", False),
                          sizer_args)
        subsizer.Add(wx.Size(0, 0))
        subsizer.Add(wx.Size(0, 0))

        label = "Open"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label,
                          "Make members accessible",
                          lambda: Mgr.update_remotely("group", "open", True),
                          sizer_args)
        checkbox = PanelCheckBox(panel, section, subsizer, self.__toggle_recursive_open,
                                 sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["recursive_open"] = checkbox
        section.add_text("recursively", subsizer, sizer_args)

        label = "Dissolve"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, subsizer, bitmaps, label,
                          "Ungroup members and delete",
                          lambda: Mgr.update_remotely("group", "dissolve"),
                          sizer_args)
        checkbox = PanelCheckBox(panel, section, subsizer, self.__toggle_recursive_dissolve,
                                 sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["recursive_dissolve"] = checkbox
        section.add_text("recursively", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 6))

        group = section.add_group("Member types")
        grp_sizer = group.get_client_sizer()

        def get_command(member_types):

            def set_member_types():

                Mgr.update_remotely("group", "set_member_types", member_types)

            return set_member_types

        member_types = ["any", "model", "dummy", "point", "tex_projector", "collision",
                        "helper", "model+helper", "model+collision"]
        type_descr = ["Any", "Model", "Dummy helper", "Point helper", "Tex. projector",
                      "Collision geometry", "Any helper", "Model + any helper",
                      "Model + coll. geom."]

        combobox = PanelComboBox(panel, group, grp_sizer, "Member types",
                                 145, sizer_args=sizer_args)

        for member_type, descr in zip(member_types, type_descr):
            combobox.add_item(member_type, descr, get_command(member_type))

        self._comboboxes["member_types"] = combobox

        sizer.Add(wx.Size(0, 6))

        sizer_args = (0, wx.ALIGN_CENTER)

        label = "Select members"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(panel, section, sizer, bitmaps, label,
                          "Open group and select members",
                          lambda: Mgr.update_remotely("group", "select_members"),
                          sizer_args)

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER)
        checkbox = PanelCheckBox(panel, section, subsizer, self.__toggle_recursive_member_selection,
                                 sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["recursive_member_selection"] = checkbox
        section.add_text("recursively", subsizer, sizer_args)

        checkbox = PanelCheckBox(panel, section, subsizer, self.__toggle_subgroup_selection,
                                 sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["subgroup_selection"] = checkbox
        section.add_text("select groups", subsizer, sizer_args)

        Mgr.add_app_updater("group_options", self.__update_group_options)

    def __update_group_options(self):

        for option, value in GlobalData["group_options"]["main"].iteritems():
            self._checkboxes[option].check(value)

    def __toggle_recursive_open(self, recursive):

        GlobalData["group_options"]["main"]["recursive_open"] = recursive

    def __toggle_recursive_dissolve(self, recursive):

        GlobalData["group_options"]["main"]["recursive_dissolve"] = recursive

    def __toggle_recursive_member_selection(self, recursive):

        GlobalData["group_options"]["main"]["recursive_member_selection"] = recursive

    def __toggle_subgroup_selection(self, select):

        GlobalData["group_options"]["main"]["subgroup_selection"] = select

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["group_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):
        pass

    def set_object_property(self, prop_id, value):

        if prop_id == "member_types":
            self._comboboxes["member_types"].select_item(value)
            self.check_selection_count()

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]

        if sel_count > 1:
            self._comboboxes["member_types"].select_none()


PropertyPanel.add_properties("group", GroupProperties)

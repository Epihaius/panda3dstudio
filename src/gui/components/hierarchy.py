from ..base import *
from ..button import *
from ..panel import *


class HierarchyPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "hierarchy")

        widgets = Skin.layout.create(self, "hierarchy")
        self._btns = widgets["buttons"]
        self._checkbuttons = widgets["checkbuttons"]

        self._toggle_btns = ToggleButtonGroup()
        toggle = (self.__set_xform_target_type, lambda: None)
        self._toggle_btns.set_default_toggle("all", toggle)

        # ********************** Object linking section ************************

        checkbtn = self._checkbuttons["show_links"]
        checkbtn.command = self.__toggle_link_visibility

        command = lambda: self.__toggle_linking_mode("sel_linking_mode")
        btn = self._btns["sel_linking_mode"]
        btn.command = command

        command = lambda: self.__toggle_linking_mode("obj_linking_mode")
        btn = self._btns["obj_linking_mode"]
        btn.command = command

        btn = self._btns["unlink"]
        btn.command = self.__unlink_selection

        command = lambda: self.__toggle_linking_mode("obj_unlinking_mode")
        btn = self._btns["obj_unlinking_mode"]
        btn.command = command

        checkbtn = self._checkbuttons["group_member_linking_allowed"]
        checkbtn.command = self.__toggle_group_member_linking
        checkbtn.check()

        checkbtn = self._checkbuttons["group_member_linking_open_groups_only"]
        checkbtn.command = self.__toggle_open_group_member_linking
        checkbtn.check()

        checkbtn = self._checkbuttons["group_member_linking_unlink_only"]
        checkbtn.command = self.__toggle_group_member_unlink_only
        checkbtn.check()

        # ************************ Transforms section **************************

        disabler = lambda: GD["active_obj_level"] != "top"

        btn = self._btns["geom"]
        btn.add_disabler("subobj_lvl", disabler)
        toggle = (lambda: self.__set_xform_target_type("geom"), lambda: None)
        self._toggle_btns.add_button(btn, "geom", toggle)

        command = lambda: Mgr.update_app("geom_reset")
        btn = self._btns["reset_geom"]
        btn.command = command
        btn.add_disabler("subobj_lvl", disabler)

        btn = self._btns["pivot"]
        btn.add_disabler("subobj_lvl", disabler)
        toggle = (lambda: self.__set_xform_target_type("pivot"), lambda: None)
        self._toggle_btns.add_button(btn, "pivot", toggle)

        command = lambda: Mgr.update_app("pivot_reset")
        btn = self._btns["reset_pivot"]
        btn.command = command
        btn.add_disabler("subobj_lvl", disabler)

        btn = self._btns["links"]
        btn.add_disabler("subobj_lvl", disabler)
        toggle = (lambda: self.__set_xform_target_type("links"), lambda: None)
        self._toggle_btns.add_button(btn, "links", toggle)

        btn = self._btns["no_children"]
        btn.add_disabler("subobj_lvl", disabler)
        toggle = (lambda: self.__set_xform_target_type("no_children"), lambda: None)
        self._toggle_btns.add_button(btn, "no_children", toggle)

        # **********************************************************************

        def disable_xform_targets():

            self._toggle_btns.enable(False)
            self._btns["reset_geom"].enable(False)
            self._btns["reset_pivot"].enable(False)

        def enable_xform_targets():

            self._toggle_btns.enable()
            self._btns["reset_geom"].enable()
            self._btns["reset_pivot"].enable()

        Mgr.accept("disable_transform_targets", disable_xform_targets)
        Mgr.accept("enable_transform_targets", enable_xform_targets)
        Mgr.add_app_updater("object_link_viz", self.__update_link_visibility)
        Mgr.add_app_updater("group_options", self.__update_group_member_linking)
        Mgr.add_app_updater("transform_target_type", self.__update_xform_target_type)

    def __update_group_member_linking(self):

        for option, value in GD["group_options"]["member_linking"].items():
            self._checkbuttons[f"group_member_linking_{option}"].check(value)

    def setup(self):

        def enter_linking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_link_objects")
            self._btns[GD["object_linking_mode"]].active = True

        def exit_linking_mode(next_state_id, active):

            if not active:
                self._btns[GD["object_linking_mode"]].active = False

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, enter_linking_mode, exit_linking_mode)

        self.get_section("transforms").expand(False)
        self.expand(False)

    def __toggle_linking_mode(self, linking_mode):

        if GD["active_obj_level"] != "top":
            GD["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        current_linking_mode = GD["object_linking_mode"]

        if current_linking_mode and current_linking_mode != linking_mode:
            Mgr.exit_state("object_linking_mode")

        if self._btns[linking_mode].active:
            Mgr.exit_state("object_linking_mode")
            GD["object_linking_mode"] = ""
        else:
            GD["object_linking_mode"] = linking_mode
            Mgr.enter_state("object_linking_mode")

    def __unlink_selection(self):

        Mgr.update_remotely("selection_unlinking")

    def __toggle_link_visibility(self, links_shown):

        GD["object_links_shown"] = links_shown
        Mgr.update_remotely("object_link_viz")

    def __update_link_visibility(self):

        links_shown = GD["object_links_shown"]
        self._checkbuttons["show_links"].check(links_shown)

    def __toggle_group_member_linking(self, allowed):

        GD["group_options"]["member_linking"]["allowed"] = allowed

    def __toggle_open_group_member_linking(self, open_groups_only):

        GD["group_options"]["member_linking"]["open_groups_only"] = open_groups_only

    def __toggle_group_member_unlink_only(self, unlink_only):

        GD["group_options"]["member_linking"]["unlink_only"] = unlink_only

    def __set_xform_target_type(self, target_type="all"):

        GD["transform_target_type"] = target_type
        Mgr.update_app("transform_target_type")

    def __update_xform_target_type(self):

        target_type = GD["transform_target_type"]

        if target_type == "all":
            self._toggle_btns.deactivate()
        else:
            self._toggle_btns.set_active_button(target_type)

from ..base import *
from ..button import *
from ..toolbar import *
from ..dialogs import *
from .snap import SnapToolbar


class SnapAlignToolbar(SnapToolbar):

    def __init__(self, parent):

        SnapToolbar.__init__(self, parent, "snap_align")

        self._comboboxes = {}

        widgets = self.widgets
        self._comboboxes["align_type"] = widgets["comboboxes"]["align_type"]
        del self.widgets

        self.__setup_align_type_combobox()

        Mgr.add_app_updater("object_alignment", self.__show_object_alignment_dialog)
        Mgr.add_app_updater("grid_alignment", self.__show_grid_alignment_dialog)

    def __setup_align_type_combobox(self):

        combobox = self._comboboxes["align_type"]

        def add_target_type_entry(target_type, target_descr):

            def set_target_type():

                Mgr.update_remotely("object_alignment", "pick_target", target_type)

            combobox.add_item(target_type, target_descr, set_target_type, select_initial=False)

        target_types = ("view", "object", "obj_point", "surface")
        target_descr = ("view", "object", "object (aim at point)", "surface")

        for target_type, descr in zip(target_types, target_descr):
            add_target_type_entry(target_type, descr)

        combobox.update_popup_menu()
        combobox.allow_field_text_in_tooltip(False)
        combobox.set_text("Align to...")

    def setup(self):

        SnapToolbar.setup(self)

        def enter_picking_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")

            if not active and GD["active_obj_level"] != "top":
                Mgr.do("enable_selection_dialog")

        def exit_picking_mode(next_state_id, active):

            if not active and GD["active_obj_level"] != "top":
                Mgr.do("disable_selection_dialog")

        def enter_align_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui", False)

        def exit_align_mode(next_state_id, active):

            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("alignment_target_picking_mode", -80, enter_picking_mode, exit_picking_mode)
        add_state("alignment_target_picking_end", -80)
        add_state("surface_alignment_mode", -80, enter_align_mode, exit_align_mode)

    def __show_object_alignment_dialog(self, dialog_type, *args):

        if dialog_type == "align":
            AlignmentDialog(*args)
        elif dialog_type == "msg":
            msg_type = args[0]
            if msg_type == "invalid_sel":
                MessageDialog(title="Invalid selection",
                              message="No suitable selection for alignment.\n"
                                      "(Open groups must be closed before they can be aligned.)",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "no_subobj_sel":
                MessageDialog(title="No selection",
                              message="No subobjects are selected for alignment.",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "links":
                MessageDialog(title="Cannot align",
                              message="Object hierarchy links cannot be aligned.",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "invalid_target":
                MessageDialog(title="Invalid alignment target",
                              message="No suitable object picked to align to.\n"
                                      "(An open group must be closed before it can"
                                      " be used as target.)",
                              choices="ok",
                              icon_id="icon_exclamation")
            elif msg_type == "invalid_surface":
                MessageDialog(title="Invalid surface",
                              message="No surface picked to align to.",
                              choices="ok",
                              icon_id="icon_exclamation")

    def __show_grid_alignment_dialog(self, dialog_type, *args):

        GridAlignmentDialog(*args)

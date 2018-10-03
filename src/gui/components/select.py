from ..base import *
from ..button import *
from ..toolbar import *


class RegionTypeComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        tooltip_text = "Region type"

        ToolbarComboBox.__init__(self, toolbar, 150, tooltip_text=tooltip_text)

        def add_region_type_entry(region_type, text):

            def set_region_type():

                GlobalData["region_select"]["type"] = region_type
                self.select_item(region_type)

            self.add_item(region_type, text, set_region_type)

        for entry_data in (
            ("rect", "Rectangle (from corner)"), ("rect_centered", "Rectangle (from center)"),
            ("square", "Square (from corner)"), ("square_centered", "Square (from center)"),
            ("ellipse", "Ellipse (from corner)"), ("ellipse_centered", "Ellipse (from center)"),
            ("circle", "Circle (from corner)"), ("circle_centered", "Circle (from center)"),
            ("fence", "Fence (point-to-point)"), ("lasso", "Lasso (freehand)"),
            ("paint", "Paint (using circle)")
        ):
            add_region_type_entry(*entry_data)

        self.update_popup_menu()


class SelectionToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "selection", "Selection")

        self._btns = btns = {}
        btn = ToolbarButton(self, icon_id="icon_region_sel",
                            tooltip_text="Region-select objects by default",
                            command=self.__toggle_region_select)
        mod_code = GlobalData["mod_key_codes"]["alt"]
        hotkey = ("s", mod_code)
        btn.set_hotkey(hotkey, "Alt+S")
        btns["region_select"] = btn
        borders = (0, 5, 0, 0)
        self.add(btn, borders=borders, alignment="center_v")

        self._comboboxes = {}
        combobox = RegionTypeComboBox(self)
        self._comboboxes["region_type"] = combobox
        self.add(combobox, borders=borders, alignment="center_v")

        btn = ToolbarButton(self, icon_id="icon_region_sel_enclose",
                            tooltip_text="Only select fully enclosed objects",
                            command=self.__toggle_enclose)
        btns["enclose"] = btn
        borders = (0, 5, 0, 0)
        self.add(btn, borders=borders, alignment="center_v")

    def __toggle_region_select(self):

        is_default = not GlobalData["region_select"]["is_default"]
        GlobalData["region_select"]["is_default"] = is_default
        self._btns["region_select"].set_active(is_default)

    def __toggle_enclose(self):

        enclose = not GlobalData["region_select"]["enclose"]
        GlobalData["region_select"]["enclose"] = enclose
        colors = Skin["colors"]
        shape_color = colors["selection_region_shape_{}".format("enclose" if enclose else "default")]
        fill_color = colors["selection_region_fill_{}".format("enclose" if enclose else "default")]
        GlobalData["region_select"]["shape_color"] = shape_color
        GlobalData["region_select"]["fill_color"] = fill_color
        Mgr.update_remotely("object_selection", "region_color")
        self._btns["enclose"].set_active(enclose)


class SelectionManager(object):

    def __init__(self, menubar):

        menu = menubar.add_menu("select", "Select")
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        handler = lambda: Mgr.update_remotely("object_selection", "all")
        menu.add("select_all", "Select all", handler)
        hotkey = ("a", mod_ctrl)
        menu.set_item_hotkey("select_all", hotkey, "Ctrl+A")
        handler = lambda: Mgr.update_remotely("object_selection", "invert")
        menu.add("invert_sel", "Invert selection", handler)
        hotkey = ("i", mod_ctrl)
        menu.set_item_hotkey("invert_sel", hotkey, "Ctrl+I")
        handler = lambda: Mgr.update_remotely("object_selection", "clear")
        menu.add("clear_sel", "Select none", handler)
        hotkey = ("backspace", mod_ctrl)
        menu.set_item_hotkey("clear_sel", hotkey, "Ctrl+Backspace")

        region_select = {"is_default": False, "type": "rect", "enclose": False}
        region_select["shape_color"] = Skin["colors"]["selection_region_shape_default"]
        region_select["fill_color"] = Skin["colors"]["selection_region_fill_default"]
        GlobalData.set_default("region_select", region_select)

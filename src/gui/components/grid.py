from ..base import *
from ..button import *
from ..toolbar import *


class GridPlaneButtons(ToggleButtonGroup):

    def __init__(self, buttons):

        ToggleButtonGroup.__init__(self)

        def add_toggle(grid_plane):

            def toggle_on():

                Mgr.update_app("active_grid_plane", grid_plane)

            toggle = (toggle_on, lambda: None)

            if grid_plane == "xy":
                self.set_default_toggle(grid_plane, toggle)
            else:
                btn = buttons[grid_plane]
                self.add_button(btn, grid_plane, toggle)

        for grid_plane in ("xy", "xz", "yz"):
            add_toggle(grid_plane)

        Mgr.add_app_updater("active_grid_plane", self.__set_active_grid_plane)

    def __set_active_grid_plane(self, plane):

        if plane == "xy":
            self.deactivate()
        else:
            self.set_active_button(plane)


class GridToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "grid")

        widgets = Skin.layout.create(self, "grid")
        self._plane_btns = GridPlaneButtons(widgets["buttons"])

        # TODO: add "Hide/Show Grid" button

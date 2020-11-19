from ..base import *
from ..button import *
from ..toolbar import *


class RenderModeButtons(ToggleButtonGroup):

    def __init__(self, buttons):

        ToggleButtonGroup.__init__(self)

        render_modes = ("shaded", "wire", "shaded+wire")
        hotkeys = {"wire": [("f3", 0), "F3"], "shaded+wire": [("f4", 0), "F4"]}

        def add_toggle(render_mode):

            def toggle_on():

                Mgr.update_app("render_mode", render_mode)

            toggle = (toggle_on, lambda: None)

            if render_mode == "shaded":
                self.set_default_toggle(render_mode, toggle)
            else:
                btn = buttons[render_mode]
                self.add_button(btn, render_mode, toggle)
                btn.set_hotkey(*hotkeys[render_mode])

        for render_mode in render_modes:
            add_toggle(render_mode)

        Mgr.add_app_updater("render_mode", self.__update_render_mode)

    def __update_render_mode(self, render_mode):

        if render_mode == "shaded":
            self.deactivate()
        else:
            self.set_active_button(render_mode)


class RenderModeToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "render_mode")

        widgets = Skin.layout.create(self, "render_mode")
        self._btns = RenderModeButtons(widgets["buttons"])

        self._btn_two_sided = btn = widgets["buttons"]["two_sided"]
        btn.command = lambda: Mgr.update_remotely("two_sided")
        hotkey = ("f5", 0)
        btn.set_hotkey(hotkey, "F5")

        Mgr.add_app_updater("two_sided", self.__toggle_two_sided)

    def __toggle_two_sided(self):

        if GD["two_sided"]:
            self._btn_two_sided.active = True
        else:
            self._btn_two_sided.active = False

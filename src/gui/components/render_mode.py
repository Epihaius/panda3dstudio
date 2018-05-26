from ..base import *
from ..button import *
from ..toolbar import *


class RenderModeButtons(ToggleButtonGroup):

    def __init__(self, toolbar):

        ToggleButtonGroup.__init__(self)

        render_modes = ("shaded", "wire", "shaded+wire")
        hotkeys = {"wire": ("f3", 0), "shaded+wire": ("f4", 0)}

        btn_data = dict((mode, ("icon_render_mode_" + mode, mode.title()))
                        for mode in render_modes[1:])

        def add_toggle(render_mode):

            def toggle_on():

                GlobalData["render_mode"] = render_mode
                Mgr.update_app("render_mode")

            toggle = (toggle_on, lambda: None)

            if render_mode == "shaded":
                self.set_default_toggle(render_mode, toggle)
            else:
                icon_id, tooltip_text = btn_data[render_mode]
                btn = ToolbarButton(toolbar, "", icon_id, tooltip_text)
                self.add_button(btn, render_mode, toggle)
                btn.set_hotkey(hotkeys[render_mode])
                borders = (0, 5, 0, 0)
                toolbar.add(btn, borders=borders, alignment="center_v")

        for render_mode in render_modes:
            add_toggle(render_mode)

        def update_render_mode():

            render_mode = GlobalData["render_mode"]

            if render_mode == "shaded":
                self.deactivate()
            else:
                self.set_active_button(render_mode)

        Mgr.add_app_updater("render_mode", update_render_mode)


class RenderModeToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "render_mode", "Render mode")

        self._btns = RenderModeButtons(self)

        borders = (0, 5, 0, 0)
        self.add(ToolbarSeparator(self), borders=borders)

        icon_id = "icon_two_sided"
        tooltip_text = "Toggle two-sided"
        command = lambda: Mgr.update_remotely("two_sided")
        hotkey = ("f5", 0)
        btn = ToolbarButton(self, "", icon_id, tooltip_text, command)
        btn.set_hotkey(hotkey)
        self._btn_two_sided = btn
        self.add(btn, alignment="center_v")

        def toggle_two_sided():

            if GlobalData["two_sided"]:
                self._btn_two_sided.set_active()
            else:
                self._btn_two_sided.set_active(False)

        Mgr.add_app_updater("two_sided", toggle_two_sided)

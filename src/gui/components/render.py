from ..base import *
from ..button import Button
from ..toggle import ToggleButtonGroup


class RenderModeToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width)

        self._btns = RenderModeButtons(self)

        sizer = self.GetSizer()
        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        sizer.AddSpacer(5)

        icon_name = "icon_two_sided"
        tooltip_text = "Toggle two-sided"
        icon_path = os.path.join(GFX_PATH, icon_name + ".png")
        bitmap_paths = Button.get_bitmap_paths("toolbar_button")
        command = lambda: Mgr.update_remotely("two_sided")
        hotkey = (wx.WXK_F5, 0)
        bitmaps = Button.create_button_bitmaps(
            icon_path, bitmap_paths, flat=True)
        btn = Button(self, bitmaps, "", tooltip_text, command)
        btn.set_hotkey(hotkey)
        self._btn_two_sided = btn
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        def toggle_two_sided():

            if Mgr.get_global("two_sided"):
                self._btn_two_sided.set_active()
            else:
                self._btn_two_sided.set_active(False)

        Mgr.add_app_updater("two_sided", toggle_two_sided)

        sizer.AddSpacer(5)
        self.add_separator(separator_bitmap_path)
        sizer.Layout()

    def enable(self):

        self._btns.enable()

    def disable(self, show=True):

        self._btns.disable(show)


class RenderModeButtons(ToggleButtonGroup):

    def __init__(self, btn_parent):

        ToggleButtonGroup.__init__(self)

        render_modes = ("shaded", "wire", "shaded+wire")
        hotkeys = {"wire": (wx.WXK_F3, 0), "shaded+wire": (wx.WXK_F4, 0)}

        btn_data = dict((mode, ("icon_render_mode_" + mode, mode.title()))
                        for mode in render_modes[1:])

        sizer = btn_parent.GetSizer()
        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        btn_parent.add_separator(separator_bitmap_path)
        btn_parent.add_separator(separator_bitmap_path)
        sizer.AddSpacer(5)

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        def add_toggle(render_mode):

            def toggle_on():

                Mgr.set_global("render_mode", render_mode)
                Mgr.update_app("render_mode")

            toggle = (toggle_on, lambda: None)

            if render_mode == "shaded":
                self.set_default_toggle(render_mode, toggle)
            else:
                icon_name, tooltip_text = btn_data[render_mode]
                icon_path = os.path.join(GFX_PATH, icon_name + ".png")
                bitmaps = Button.create_button_bitmaps(
                    icon_path, bitmap_paths, flat=True)
                btn = self.add_button(
                    btn_parent, render_mode, toggle, bitmaps, tooltip_text)
                btn.set_hotkey(hotkeys[render_mode])
                sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        for render_mode in render_modes:
            add_toggle(render_mode)

        def update_render_mode():

            render_mode = Mgr.get_global("render_mode")

            if render_mode == "shaded":
                self.deactivate()
            else:
                self.set_active_button(render_mode)

        Mgr.add_app_updater("render_mode", update_render_mode)

        sizer.AddStretchSpacer()
        btn_parent.add_separator(separator_bitmap_path)
        sizer.Layout()

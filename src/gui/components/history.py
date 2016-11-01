from ..base import *
from ..button import Button, ButtonGroup
from .hist_dlg import HistoryWindow


class HistoryToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width)

        self._btns = ButtonGroup()

        btn_data = {
            "undo": ("icon_undo", "Undo"),
            "redo": ("icon_redo", "Redo"),
            "edit": ("icon_hist", "History")
        }

        sizer = self.GetSizer()
        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        self.add_separator(separator_bitmap_path)
        self.add_separator(separator_bitmap_path)
        sizer.Add(wx.Size(10, 0))

        get_updater = lambda btn_id: lambda: Mgr.update_app("history", btn_id)

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        for btn_id in ("undo", "redo", "edit"):
            icon_name, tooltip_text = btn_data[btn_id]
            icon_path = os.path.join(GFX_PATH, icon_name + ".png")
            bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
            btn = Button(self, bitmaps, "", tooltip_text, get_updater(btn_id))
            self._btns.add_button(btn, btn_id)
            btn.disable()
            sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        sizer.Layout()

        self._btns.get_button("undo").set_hotkey((ord("Z"), wx.MOD_CONTROL))
        self._btns.get_button("redo").set_hotkey((ord("Z"), wx.MOD_CONTROL | wx.MOD_SHIFT))

        def update_history(update_type, *args, **kwargs):

            if update_type == "show":
                HistoryWindow(self.GetParent(), *args, **kwargs)
            elif update_type == "archive":
                for btn in self._btns.get_buttons():
                    btn.disable()
            elif update_type == "check":
                self.__check_undo_redo()
            elif update_type == "set_descriptions":
                self.__set_undo_redo_descriptions(*args)

        Mgr.add_app_updater("history", update_history)

    def __check_undo_redo(self):

        to_undo = GlobalData["history_to_undo"]
        to_redo = GlobalData["history_to_redo"]
        undo_btn = self._btns.get_button("undo")
        redo_btn = self._btns.get_button("redo")
        edit_btn = self._btns.get_button("edit")

        undo_btn.enable() if to_undo else undo_btn.disable()
        redo_btn.enable() if to_redo else redo_btn.disable()
        edit_btn.enable() if to_undo or to_redo else edit_btn.disable()

    def __set_undo_redo_descriptions(self, undo_descr, redo_descr):

        if undo_descr:
            self._btns.get_button("undo").set_tooltip("Undo: " + undo_descr)

        if redo_descr:
            self._btns.get_button("redo").set_tooltip("Redo: " + redo_descr)

    def enable(self):

        self._btns.enable()
        self.__check_undo_redo()

    def disable(self, show=True):

        self._btns.disable(show)

from ..base import *
from ..button import *
from ..toolbar import *
from ..dialogs import HistoryDialog


class HistoryToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "history")

        widgets = Skin.layout.create(self, "history")
        self._btns = btns = widgets["buttons"]

        get_updater = lambda btn_id: lambda: Mgr.update_app("history", btn_id)

        for btn_id in ("undo", "redo", "edit"):
            btn = btns[btn_id]
            btn.command = get_updater(btn_id)
            btn.enable(False)

        Mgr.add_app_updater("history", self.__update_history)

    def __update_history(self, update_type, *args, **kwargs):

        if update_type == "show":
            HistoryDialog(*args, **kwargs)
        elif update_type == "archive":
            for btn in self._btns.values():
                btn.enable(False)
        elif update_type == "check":
            self.__check_undo_redo()
        elif update_type == "set_descriptions":
            self.__set_undo_redo_descriptions(*args)

    def __check_undo_redo(self):

        to_undo = GD["history_to_undo"]
        to_redo = GD["history_to_redo"]
        undo_btn = self._btns["undo"]
        redo_btn = self._btns["redo"]
        edit_btn = self._btns["edit"]

        undo_btn.enable(to_undo)
        redo_btn.enable(to_redo)
        edit_btn.enable(to_undo or to_redo)

    def __set_undo_redo_descriptions(self, undo_descr, redo_descr):

        if undo_descr:
            self._btns["undo"].tooltip_text = "Undo: " + undo_descr

        if redo_descr:
            self._btns["redo"].tooltip_text = "Redo: " + redo_descr

    def enable(self, enable=True, update_bundle=True):

        Toolbar.enable(self, enable, update_bundle)

        self.__check_undo_redo()

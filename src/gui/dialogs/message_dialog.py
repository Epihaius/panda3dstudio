from ..icon import Icon
from ..dialog import *


class MessageDialog(Dialog):

    def __init__(self, title="", message="", choices="okcancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None, icon_id=""):

        Dialog.__init__(self, title, choices, ok_alias, on_yes, on_no, on_cancel)

        component_ids = ["icon"] if icon_id else None
        widgets = Skin.layout.create(self, "message", component_ids=component_ids)

        if icon_id:
            icon_cell = widgets["placeholders"]["icon"]
            icon_cell.object = Icon(self, icon_id)

        text_cell = widgets["placeholders"]["text"]
        text_cell.object = DialogText(self, message, text_type="dialog_message")

        self.finalize()

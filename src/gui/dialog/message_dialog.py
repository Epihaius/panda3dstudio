from ..icon import Icon
from .dialog import *


class MessageDialog(Dialog):

    def __init__(self, parent=None, title="", message="", choices="okcancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None, icon_id=""):

        Dialog.__init__(self, parent, title, choices, ok_alias, on_yes, on_no, on_cancel)

        client_sizer = self.get_client_sizer()

        if message or icon_id:
            subsizer = Sizer("horizontal")
            subsizer.add((0, 0), proportion=1.)
            subsizer.add((0, 0), proportion=1.)
            borders = (50, 50, 30, 30)
            client_sizer.add(subsizer, borders=borders, expand=True)

        if message:
            text = DialogMessageText(self, message)
            borders = (20, 0, 0, 0) if icon_id else None
            subsizer.add(text, borders=borders, alignment="center_v", index=1)

        if icon_id:
            icon = Icon(self, icon_id)
            subsizer.add(icon, alignment="center_v", index=1)

        self.finalize()

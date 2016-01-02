from .base import *
from .panel import DeepShelfPanel


class DeepShelf(DeepShelfObject):

    def __init__(self, parent, gfx_path, width, remote_task_handler,
                 on_show=None, on_hide=None):

        DeepShelfObject._mgr = DeepShelfManager()
        self._mgr.set_remote_task_handler(remote_task_handler)
        self._panel = DeepShelfPanel(parent, gfx_path, width, on_show, on_hide)

        no_access_cursor_path = os.path.join(gfx_path, "no_access.cur")
        move_cursor_path = os.path.join(gfx_path, "move.cur")
        CURSORS["no_access"] = wx.Cursor(
            no_access_cursor_path, wx.BITMAP_TYPE_CUR)
        CURSORS["move"] = wx.Cursor(move_cursor_path, wx.BITMAP_TYPE_CUR)

    def hide(self):

        self._panel.Hide()

    def show(self):

        self._panel.Show()

    def on_enter(self):

        self._panel.on_enter_window()

    def on_leave(self):

        self._panel.on_leave_window()

    def add_tool_button(self, btn_id, btn_props):

        self._mgr.do("add_tool_button_props", btn_id, btn_props)

    def toggle_tool_button(self, btn_id):

        self._mgr.do("toggle_tool_button", btn_id)

    def handle_key_down(self, key, mod_code=0):

        return self._mgr.handle_key_down(self._panel, key, mod_code)

    def handle_key_up(self, key):

        return self._mgr.handle_key_up(self._panel, key)

    def set_tool_btn_down_handler(self, handler=None):

        self._mgr.do("set_btn_down_handler", handler)

    def set_tool_btn_up_handler(self, handler=None):

        self._mgr.do("set_btn_up_handler", handler)

from ...base import *
from ...button import Button
from .components import Components


class UVEditGUI(BaseObject):

    def __init__(self):

        self._window = None

    def setup(self):

        def enter_editing_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (100, 255, 100))

            if not is_active:
                ids = ["menubar", "main_toolbar", "history_toolbar", "panel_stack"]
                Mgr.do("add_component_disabler", "uv_edit", lambda: True, ids)
                Mgr.do("disable_components", show=False, ids=ids)
                self._window = win = UVEditWindow(Mgr.get("main_window"))
                win.create_viewport()
                win.set_bindings()

        def exit_editing_mode(next_state_id, is_active):

            if not is_active:
                self._window = None
                Mgr.do("remove_component_disabler", "uv_edit")
                # the following allows the name & color user controls to be re-enabled
                GlobalData["active_obj_level"] = "top"
                Mgr.do("enable_components")

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, enter_editing_mode, exit_editing_mode)


class UVEditWindow(wx.Frame):

    def __init__(self, parent=None):

        style = wx.CAPTION | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, -1, "Edit UVs", style=style)

        self._hotkey_prev = None
        key_handlers = {
            "down": lambda key: self.__on_key_down(remote_key=key),
            "up": lambda key: self.__on_key_up(remote_key=key)
        }
        Mgr.add_interface("uv_window", key_handlers)

        add_state = Mgr.add_state
        add_state("uv_edit_mode", 0, interface_id="uv_window")

        w = 800
        h = 650
        self.SetClientSize((w, h))
        self._panel = wx.Panel(self, -1, size=(w, h))
        self.Show()

        Mgr.expose("uv_focus_receiver", lambda: self._panel)

        self._components = Components(self._panel)
        self._viewport = None

    def create_viewport(self):

        self._viewport = UVEditViewport(self._panel, (0, 50), (600, 600))

    def set_bindings(self):

        self.Bind(wx.EVT_CLOSE, self.__on_close)
        self._panel.Bind(wx.EVT_KEY_DOWN, self.__on_key_down)
        self._panel.Bind(wx.EVT_KEY_UP, self.__on_key_up)
        self.Bind(wx.EVT_MOUSEWHEEL, lambda evt:
                  EventDispatcher.dispatch_event("uv_window", "mouse_wheel", evt))

    def __on_close(self, wx_event=None):

        Mgr.expose("uv_focus_receiver", lambda: None)
        Button.remove_interface("uv_window")
        EventDispatcher.remove_interface("uv_window")
        Mgr.update_remotely("uv_viewport", False)
        self._components.destroy()

        if wx_event:
            wx_event.Skip()

    def __on_key_down(self, event=None, remote_key=None):

        mod_code = 0
        alt_key_event_ids = Mgr.get("alt_key_event_ids")

        if event:

            key = event.GetKeyCode()

            if key in alt_key_event_ids:
                key = alt_key_event_ids[key]

            if event.AltDown():
                mod_code |= wx.MOD_ALT
                GlobalData["alt_down"] = True

            if event.CmdDown():
                mod_code |= wx.MOD_CONTROL
                GlobalData["ctrl_down"] = True

            if event.ShiftDown():
                mod_code |= wx.MOD_SHIFT
                GlobalData["shift_down"] = True

            if Mgr.remotely_handle_key_down(key, "uv_window"):
                return

        else:

            key = remote_key

            if GlobalData["alt_down"]:
                mod_code |= wx.MOD_ALT

            if GlobalData["ctrl_down"]:
                mod_code |= wx.MOD_CONTROL

            if GlobalData["shift_down"]:
                mod_code |= wx.MOD_SHIFT

        hotkey = (key, mod_code)

        if self._hotkey_prev == hotkey:
            hotkey_repeat = True
        else:
            hotkey_repeat = False
            self._hotkey_prev = hotkey

        self._components.handle_key_down(hotkey, hotkey_repeat)

    def __on_key_up(self, event=None, remote_key=None):

        self._hotkey_prev = None
        alt_key_event_ids = Mgr.get("alt_key_event_ids")

        if event:

            key = event.GetKeyCode()

            if key in alt_key_event_ids:
                key = alt_key_event_ids[key]

            if key == wx.WXK_ALT:
                GlobalData["alt_down"] = False
            elif key == wx.WXK_CONTROL:
                GlobalData["ctrl_down"] = False
            elif key == wx.WXK_SHIFT:
                GlobalData["shift_down"] = False

            if Mgr.remotely_handle_key_up(key, "uv_window"):
                return


class UVEditViewport(wx.Window, FocusResetter):

    def __init__(self, parent, pos, size, name="uv_edit_viewport"):

        wx.Window.__init__(self, parent=parent, pos=pos, size=size, name=name)
        FocusResetter.__init__(self, parent)

        self.refuse_focus(reject_field_input=True)

        handle = self.GetHandle()
        Mgr.update_remotely("uv_viewport", True, size, handle)

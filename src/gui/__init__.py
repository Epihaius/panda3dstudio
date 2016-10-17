from .base import *
from .components import Components
import sys


class GUI(wx.App):

    def __init__(self, app_mgr, verbose=False):

        wx.App.__init__(self, redirect=False)

        cursors = {}
        cursor_path = os.path.join(GFX_PATH, "dropper.cur")
        cursors["dropper"] = wx.Cursor(cursor_path, wx.BITMAP_TYPE_CUR)
        cursor_path = os.path.join(GFX_PATH, "drag.cur")
        cursors["drag"] = wx.Cursor(cursor_path, wx.BITMAP_TYPE_CUR)

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        fonts = {"default": font}

        Cursors.init(cursors)
        Fonts.init(fonts)
        BaseObject.init(verbose)
        Mgr.init(app_mgr, verbose)

        self._alt_key_event_ids = {
            wx.WXK_NUMPAD_DELETE: wx.WXK_DELETE,
            wx.WXK_NUMPAD_ENTER: wx.WXK_RETURN,
            wx.WXK_NUMPAD_TAB: wx.WXK_TAB,
            wx.WXK_NUMPAD_INSERT: wx.WXK_INSERT,
            wx.WXK_NUMPAD_HOME: wx.WXK_HOME,
            wx.WXK_NUMPAD_END: wx.WXK_END,
            wx.WXK_NUMPAD_PAGEUP: wx.WXK_PAGEUP,
            wx.WXK_NUMPAD_PAGEDOWN: wx.WXK_PAGEDOWN,
            wx.WXK_NUMPAD_LEFT: wx.WXK_LEFT,
            wx.WXK_NUMPAD_RIGHT: wx.WXK_RIGHT,
            wx.WXK_NUMPAD_UP: wx.WXK_UP,
            wx.WXK_NUMPAD_DOWN: wx.WXK_DOWN,
            wx.WXK_NUMPAD_SPACE: wx.WXK_SPACE,
            wx.WXK_NUMPAD_F1: wx.WXK_F1,
            wx.WXK_NUMPAD_F2: wx.WXK_F2,
            wx.WXK_NUMPAD_F3: wx.WXK_F3,
            wx.WXK_NUMPAD_F4: wx.WXK_F4,
            wx.WXK_ADD: 0x2b,
            wx.WXK_SUBTRACT: 0x2d,
            wx.WXK_MULTIPLY: 0x2a,
            wx.WXK_DIVIDE: 0x2f,
            wx.WXK_DECIMAL: 0x2e,
            wx.WXK_NUMPAD_ADD: 0x2b,
            wx.WXK_NUMPAD_SUBTRACT: 0x2d,
            wx.WXK_NUMPAD_MULTIPLY: 0x2a,
            wx.WXK_NUMPAD_DIVIDE: 0x2f,
            wx.WXK_NUMPAD_DECIMAL: 0x2e,
            wx.WXK_NUMPAD_EQUAL: 0x3d,
        }

        for wx_code, key_code in zip(range(wx.WXK_NUMPAD0, wx.WXK_NUMPAD9 + 1), range(0x30, 0x3a)):
            self._alt_key_event_ids[wx_code] = key_code

        Mgr.expose("alt_key_event_ids", lambda: self._alt_key_event_ids)
        self._hotkey_prev = None

        # Create a new event loop (to override default wx.EventLoop)
        self._evt_loop = wx.EventLoop()
        self._old_loop = wx.EventLoop.GetActive()
        wx.EventLoop.SetActive(self._evt_loop)

        size = (1006, 656 + 48)
        style = wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.CAPTION
        self._title_main = "Panda3D Studio - "
        main_frame = wx.Frame(None, -1, self._title_main + "New", style=style)
        self.SetTopWindow(main_frame)

        if PLATFORM_ID == "Windows":
            main_frame.SetPosition(wx.Point(-10000, -10000))

        main_frame.SetClientSize(size)
        main_frame.Show()
        self._main_frame = main_frame
        panel = wx.Panel(main_frame, -1, size=size)
        default_focus_receiver = panel
        self._default_focus_receiver = default_focus_receiver
        default_focus_receiver.Bind(wx.EVT_KEY_DOWN, self.__on_key_down)
        default_focus_receiver.Bind(wx.EVT_KEY_UP, self.__on_key_up)
        main_frame.Bind(wx.EVT_CLOSE, self.__on_close)
        main_frame.Bind(wx.EVT_MOUSEWHEEL, lambda evt:
                        EventDispatcher.dispatch_event("", "mouse_wheel", evt))
        Mgr.expose("main_window", lambda: self._main_frame)
        Mgr.expose("default_focus_receiver", lambda: default_focus_receiver)
        Mgr.accept("set_scene_label", self.__set_scene_label)
        Mgr.accept("handle_key_down", self.__on_key_down)
        Mgr.accept("handle_key_up", self.__on_key_up)
        Mgr.add_app_updater("pending_tasks", PendingTasks.handle)

        self._components = Components(default_focus_receiver)
        self._exit_handler = self._components.exit_handler

    # wxWindows calls this method to initialize the application
    def OnInit(self):

        self.SetAppName("Panda3D Studio")
        self.SetClassName("MyAppClass")

        return True

    def setup(self):

        self._components.setup()
        wx.CallAfter(self._main_frame.Center)

    def get_viewport_data(self):

        return self._components.get_viewport_data()

    def get_event_loop_handler(self):

        return self.__process_event_loop

    @staticmethod
    def get_key_event_ids():

        key_event_ids = {
            "Esc": wx.WXK_ESCAPE,
            "PrtScr": wx.WXK_PRINT,
            "ScrlLk": wx.WXK_SCROLL,
            "NumLk": wx.WXK_NUMLOCK,
            "CapsLk": wx.WXK_CAPITAL,
            "BkSpace": wx.WXK_BACK,
            "Del": wx.WXK_DELETE,
            "Enter": wx.WXK_RETURN,
            "Tab": wx.WXK_TAB,
            "Ins": wx.WXK_INSERT,
            "Home": wx.WXK_HOME,
            "End": wx.WXK_END,
            "PgUp": wx.WXK_PAGEUP,
            "PgDn": wx.WXK_PAGEDOWN,
            "Left": wx.WXK_LEFT,
            "Right": wx.WXK_RIGHT,
            "Up": wx.WXK_UP,
            "Down": wx.WXK_DOWN,
            "Shift": wx.WXK_SHIFT,
            "Ctrl": wx.WXK_CONTROL,
            "Alt": wx.WXK_ALT,
            " ": wx.WXK_SPACE,
        }

        for key_code in range(0x41, 0x5b):
            char = chr(key_code)
            key_event_ids[char] = key_code

        for key_code in range(0x21, 0x41) + range(0x5b, 0x61) + range(0x7b, 0x80):
            key_event_ids["%d" % key_code] = key_code

        for i, key_code in enumerate(range(wx.WXK_F1, wx.WXK_F12 + 1)):
            key_event_ids["F%d" % (i + 1)] = key_code

        return key_event_ids

    @staticmethod
    def get_mod_key_codes():

        return {"shift": wx.MOD_SHIFT, "ctrl": wx.MOD_CONTROL, "alt": wx.MOD_ALT}

    @staticmethod
    def get_max_color_value():

        return 255

    def get_key_handlers(self):

        return {
            "down": lambda key: self.__on_key_down(remote_key=key),
            "up": lambda key: self.__on_key_up(remote_key=key)
        }

    def __process_event_loop(self):

        while self._evt_loop.Pending():
            self._evt_loop.Dispatch()

        self.ProcessIdle()

    def __on_close(self, event):

        def cleanup():

            for window in wx.GetTopLevelWindows():
                window.Hide()

            for window in wx.GetTopLevelWindows():
                if window is not self._main_frame:
                    window.Close()

            wx.EventLoop.SetActive(self._old_loop)
            self._main_frame.Destroy()

            sys.exit()

        if event.CanVeto() and not self._exit_handler():
            event.Veto()
        else:
            cleanup()

    def __on_key_down(self, event=None, remote_key=None):

        mod_code = 0

        if event:

            key = event.GetKeyCode()

            if key in self._alt_key_event_ids:
                key = self._alt_key_event_ids[key]

            if event.AltDown():
                mod_code |= wx.MOD_ALT
                GlobalData["alt_down"] = True

            if event.CmdDown():
                mod_code |= wx.MOD_CONTROL
                GlobalData["ctrl_down"] = True

            if event.ShiftDown():
                mod_code |= wx.MOD_SHIFT
                GlobalData["shift_down"] = True

            if Mgr.remotely_handle_key_down(key):
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

        self._components.handle_key_down(key, mod_code, hotkey, hotkey_repeat)

    def __on_key_up(self, event=None, remote_key=None):

        self._hotkey_prev = None

        if event:

            key = event.GetKeyCode()

            if key in self._alt_key_event_ids:
                key = self._alt_key_event_ids[key]

            if key == wx.WXK_ALT:
                GlobalData["alt_down"] = False
            elif key == wx.WXK_CONTROL:
                GlobalData["ctrl_down"] = False
            elif key == wx.WXK_SHIFT:
                GlobalData["shift_down"] = False

            if Mgr.remotely_handle_key_up(key):
                return

        else:

            key = remote_key

        self._components.handle_key_up(key)

    def __set_scene_label(self, scene_label):

        self._main_frame.SetTitle(self._title_main + scene_label)

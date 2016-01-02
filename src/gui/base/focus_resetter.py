from .base import *
from .mgr import GUIManager as Mgr


class FocusResetter(object):

    def __init__(self, focus_receiver=None):

        if focus_receiver:
            self._focus_receiver = focus_receiver
        else:
            self._focus_receiver = Mgr.get("default_focus_receiver")

    def refuse_focus(self, refuse_focus=True, reject_field_input=False, on_click=None):

        if refuse_focus:

            def reset_focus(event):

                Mgr.do("%s_field_input" %
                       ("reject" if reject_field_input else "accept"))
                self._focus_receiver.SetFocusIgnoringChildren()

            self.Bind(wx.EVT_SET_FOCUS, reset_focus)

            if on_click:

                def on_left_down(event):

                    on_click(event)
                    Mgr.do("%s_field_input" %
                           ("reject" if reject_field_input else "accept"))
                    self._focus_receiver.SetFocusIgnoringChildren()

                self.Bind(wx.EVT_LEFT_DOWN, on_left_down)

            else:

                self.Bind(wx.EVT_LEFT_DOWN, reset_focus)

        else:

            self.Unbind(wx.EVT_SET_FOCUS)
            self.Unbind(wx.EVT_LEFT_DOWN)

    def set_focus_receiver(self, focus_receiver=None):

        if focus_receiver:
            self._focus_receiver = focus_receiver
        else:
            self._focus_receiver = Mgr.get("default_focus_receiver")

    def get_focus_receiver(self):

        return self._focus_receiver

    def reset_focus(self):

        return self._focus_receiver.SetFocusIgnoringChildren()

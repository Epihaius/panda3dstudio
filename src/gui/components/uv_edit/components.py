from ...base import *
from ...button import Button
from ...panel import PanelStack
from .panel import UVSetPanel, SubobjectPanel, BackgroundPanel, ExportPanel
from .transform import TransformToolbar


class Components(BaseObject):

    def __init__(self, frame):

        w, h = size = frame.GetClientSize()

        self._disablers = {}
        self._components = components = {}

        toolbar = TransformToolbar(frame, wx.Point(0, 0), w)
        components["transf_toolbar"] = toolbar

        panel_stack = PanelStack(frame, wx.Point(w - 200, 50), wx.Size(200, h - 50),
                                 frame, interface_id="uv_window")
        components["panel_stack"] = panel_stack
        components["uv_set_panel"] = UVSetPanel(panel_stack, frame)
        components["subobj_panel"] = SubobjectPanel(panel_stack, frame)
        components["backgr_panel"] = BackgroundPanel(panel_stack, frame)
        components["export_panel"] = ExportPanel(panel_stack, frame)

        self._component_ids = (
            "uv_set_panel", "subobj_panel", "backgr_panel", "export_panel")

    def destroy(self):

        self._components["panel_stack"].destroy()

    def handle_key_down(self, hotkey, hotkey_repeat):

        Button.handle_hotkey(hotkey, hotkey_repeat, "uv_window")

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        if disabler_id in self._disablers:
            del self._disablers[disabler_id]

    def enable(self):

        for disabler in self._disablers.itervalues():
            if disabler():
                return

        for comp_id in self._component_ids:
            self._components[comp_id].enable()

    def disable(self, show=True, ids=None):

        if ids:
            for comp_id in ids:
                self._components[comp_id].disable(show)
        else:
            for comp_id in self._component_ids:
                self._components[comp_id].disable(show)

    def deactivate(self):

        self._components["main_toolbar"].deactivate()

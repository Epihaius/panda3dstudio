from ..base import *
from ..button import Button, ButtonGroup
from ..toggle import ToggleButtonGroup
from ..combobox import ComboBox
from ..field import InputField
from ..checkbox import CheckBox
from ..colorctrl import ColorPickerCtrl
from ..panel import *


class HierarchyPanel(Panel):

    def __init__(self, parent, focus_receiver=None):

        Panel.__init__(self, parent, "Hierarchy", focus_receiver)

        self._parent = parent
        self._width = parent.get_width()

        self._comboboxes = {}
        self._checkboxes = {}
        self._color_pickers = {}
        self._fields = {}
        self._btns = {}
        self._radio_btns = {}

        panel_sizer = self.GetSizer()
        panel_sizer.Add(wx.Size(self._width, 0))
        parent.GetSizer().Add(self)

        bitmap_paths = Button.get_bitmap_paths("panel_button")

        # ********************** Object linking section ************************

        link_section = section = self.add_section("linking", "Object linking")
        sizer = section.get_client_sizer()

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(btn_sizer)
        sizer_args = (0, wx.ALL, 2)

        label = "Link"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label, "Link objects",
                          self.__toggle_linking_mode, sizer_args, focus_receiver=focus_receiver)
        self._btns["link"] = btn

        btn_sizer.Add(wx.Size(10, 0))

        label = "Unlink"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        btn = PanelButton(self, section, btn_sizer, bitmaps, label, "Unlink selected objects",
                          self.__unlink_objects, sizer_args, focus_receiver=focus_receiver)
        self._btns["unlink"] = btn

        # **********************************************************************

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize():

            self.expand(False)
            self.update_parent()

        wx.CallAfter(finalize)

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def setup(self):

        def enter_linking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 255))
            self._btns["link"].set_active()

        def exit_linking_mode(next_state_id, is_active):

            if not is_active:
                self._btns["link"].set_active(False)

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, enter_linking_mode, exit_linking_mode)

    def __toggle_linking_mode(self):

        if self._btns["link"].is_active():
            Mgr.exit_state("object_linking_mode")
        else:
            Mgr.enter_state("object_linking_mode")

    def __unlink_objects(self):

        Mgr.update_remotely("object_unlinking")

    def get_width(self):

        return self._width

    def get_client_width(self):

        return self._width - self.get_client_offset() * 2

# DeepShelf module.

# Implements the main panel.

from __future__ import division, with_statement
from .base import *
from .shelf import Shelf
from .root_shelves import HomeShelf, FavoritesShelf, HistoryShelf
from .shelf_path import ShelfPath
from .shelf_dlg import ShelfContentsCreationDialog, ShelfCreationDialog
from .tool_btn import ToolButton
from .tool_btn_dlg import ToolButtonEditingDialog, ToolButtonCreationDialog
from .access_btn import AccessButton


class DeepShelfPanel(DeepShelfObject, wx.Panel):

    def __init__(self, parent, gfx_path, width, on_show=None, on_hide=None):

        self._parent = parent

        self._on_show = on_show if on_show else lambda: None
        self._on_hide = on_hide if on_hide else lambda: None

        bitmap_names = {
            "background": os.path.join(gfx_path, "background"),
            "border": os.path.join(gfx_path, "border"),
            "path_btn": os.path.join(gfx_path, "path_btn_"),
            "parent_btn": os.path.join(gfx_path, "parent_btn_"),
            "fav_btn": os.path.join(gfx_path, "fav_btn_"),
            "fav_icon": os.path.join(gfx_path, "fav_icon"),
            "hist_btn": os.path.join(gfx_path, "hist_btn_"),
            "hist_icon": os.path.join(gfx_path, "hist_icon"),
            "home_btn": os.path.join(gfx_path, "home_btn_"),
            "home_icon": os.path.join(gfx_path, "home_icon"),
            "scroll_left_btn": os.path.join(gfx_path, "scroll_left_btn_"),
            "scroll_right_btn": os.path.join(gfx_path, "scroll_right_btn_"),
            "tool_button": os.path.join(gfx_path, "tool_btn_"),
            "shelf_button": os.path.join(gfx_path, "shelf_btn_")
        }

        border_bitmap = wx.Bitmap(bitmap_names["border"] + ".png")
        w_b, h = border_bitmap.GetSize()
        w_bg = width - 2 * w_b
        bg_image = wx.Image(bitmap_names["background"] + ".png")
        bg_image = bg_image.Scale(w_bg, h)

        self._background = wx.EmptyBitmap(width, h)
        mem_dc = wx.MemoryDC(self._background)
        mem_dc.DrawBitmap(border_bitmap, 0, 0)
        mem_dc.DrawBitmap(bg_image.ConvertToBitmap(), w_b, 0)
        mem_dc.DrawBitmap(border_bitmap, w_b + w_bg, 0)
        mem_dc.SelectObject(wx.NullBitmap)

        self._font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                             wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        gc = wx.GraphicsContext.Create(mem_dc)
        gc.SetFont(self._font)
        text_width, text_height = gc.GetTextExtent("kg")

        self._size = (width, h)
        ShelfPath.init(self, bitmap_names, w_b, width, h, self._font)
        btn_w, btn_h = ShelfPath.getButtonSize()
        btn_space = btn_w + 7
        self._preview_rect = wx.Rect(
            w_b + btn_space, 0, width - 2 * (w_b + btn_space), h - btn_h - 3)
        Shelf.init(self, wx.Rect(w_b + btn_space, 0,
                                 w_bg - 2 * btn_space, h), bitmap_names)
        AccessButton.init(self, width, h, bitmap_names["shelf_button"])
        self._shelf_icon_y = 2 + (btn_h - text_height) // 2

        self._home_shelf_obj = HomeShelf(bitmap_names["home_icon"])
        self._home_shelf = self._home_shelf_obj.getProxy()
        self._fav_shelf_obj = FavoritesShelf(bitmap_names["fav_icon"])
        self._fav_shelf = self._fav_shelf_obj.getProxy()
        self._hist_shelf_obj = HistoryShelf(bitmap_names["hist_icon"])
        self._hist_shelf = self._hist_shelf_obj.getProxy()
        self._current_shelf = self._home_shelf
        self._candidate_shelf = None

        ShelfPath.setRootShelves({"fav": self._fav_shelf, "hist": self._hist_shelf,
                                  "home": self._home_shelf})

        wx.Panel.__init__(self, parent, size=self._size)

        ToolTip.init(self)
        InsertionMarker.init(self, gfx_path)
        DraggedContents.init(self)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        wx.EVT_PAINT(self, self.__draw)

        self._rect = wx.Rect(0, 0, width, h)

        self._main_menu = wx.Menu()
        self._btn_menu = wx.Menu()
        self._menu_items = {}
        self._menu_items["shelf_contents"] = {}
        self._menu_items["button"] = {}

        self._contents_menu = wx.Menu()
        item = self._main_menu.AppendMenu(-1,
                                          "Shelf contents", self._contents_menu)
        self._menu_items["shelf_contents"]["menu"] = item
        item = self._contents_menu.Append(-1, "New")
        self._menu_items["shelf_contents"]["new"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__createShelfContents(), item)
        self._contents_menu.AppendSeparator()
        item = self._contents_menu.Append(-1, "Move to new shelf")
        self._menu_items["shelf_contents"]["move"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.relocateShelfContents(
            show_message=False), item)
        self._contents_menu.AppendSeparator()
        item = self._contents_menu.Append(-1, "Select none\tCTRL+BACKSPACE")
        self.Bind(wx.EVT_MENU, lambda evt: self.__selectShelfContents("none"), item)
        item = self._contents_menu.Append(-1, "Select all\tCTRL+A")
        self.Bind(wx.EVT_MENU, lambda evt: self.__selectShelfContents("all"), item)
        item = self._contents_menu.Append(-1, "Invert selection\tCTRL+I")
        self.Bind(
            wx.EVT_MENU, lambda evt: self.__selectShelfContents("invert"), item)
        self._contents_menu.AppendSeparator()
        item = self._contents_menu.Append(-1, "Delete selection\tDEL")
        self._menu_items["shelf_contents"]["remove_selection"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__removeShelfContents(), item)
        item = self._contents_menu.Append(-1, "Cut selection\tCTRL+X")
        self._menu_items["shelf_contents"]["cut_selection"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__cutShelfContents(), item)
        item = self._contents_menu.Append(-1, "Paste\tCTRL+V")
        self._menu_items["shelf_contents"]["paste"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__pasteShelfContents(), item)
        self._contents_menu.AppendSeparator()
        item = self._contents_menu.Append(-1, "Hide\tCTRL+H")
        self._menu_items["shelf_contents"]["access"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__hideShelfContents(), item)

        self._main_menu.AppendSeparator()
        self._layout_menu = wx.Menu()
        item = self._main_menu.AppendMenu(-1, "Layout", self._layout_menu)
        item = self._layout_menu.Append(-1, "Save")
        self.Bind(wx.EVT_MENU, lambda evt: self.__save(), item)
        item = self._layout_menu.Append(-1, "Load")
        self.Bind(wx.EVT_MENU, lambda evt: self.__load(), item)
        self._layout_menu.AppendSeparator()
        item = self._layout_menu.Append(-1, "Clear")
        self.Bind(wx.EVT_MENU, lambda evt: self.__clear(), item)

        self._main_menu.AppendSeparator()
        item = self._main_menu.Append(-1, "Exit")
        self.Bind(wx.EVT_MENU, lambda evt: self._parent.Close(), item)

        item = self._btn_menu.Append(-1, "Edit properties")
        self._menu_items["button"]["edit"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__editToolButton(), item)
        self._btn_menu.AppendSeparator()
        item = self._btn_menu.Append(-1, "Rename")
        self._menu_items["button"]["rename"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__renameShelfContents(), item)
        item = self._btn_menu.Append(-1, "Delete")
        self._menu_items["button"]["remove"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__removeShelfContents(False), item)
        item = self._btn_menu.Append(-1, "Cut")
        self._menu_items["button"]["cut"] = item
        self.Bind(wx.EVT_MENU, lambda evt: self.__cutShelfContents(False), item)
        self._btn_menu.AppendSeparator()
        item = self._btn_menu.Append(-1, "(De)select\tCTRL")
        self._menu_items["button"]["select"] = item
        self.Bind(
            wx.EVT_MENU, lambda evt: self.__toggleShelfContentsSelection(), item)

        self._menu_open = False
        self._menu_x = 0
        self._dialog_open = False

        def notifyMenuClosed(event):
            # print "notifyMenuClosed() called."

            self._menu_open = False
            self.Refresh()
            mouse_pos = self.ScreenToClient(wx.GetMousePosition())
            self._has_mouse = self._rect.Contains(mouse_pos)
            self._timer.Start(500, oneShot=True)
            self._delay_timer.Start(200, oneShot=True)
            self.__checkMouse()

        self._menu_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, notifyMenuClosed, self._menu_timer)

        self._delay_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.__onDelayTimer, self._delay_timer)

        self._has_mouse = False
        self._left_down = False

        def toggleVisibility(event):
            # print "pullFrame(event) called *********"

            if self._has_mouse:
                self._on_show()
                self.Show()
            elif not self._dialog_open:
                self.Hide()
                self._on_hide()

            if not self._menu_open:
                self._dialog_open = False

        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, toggleVisibility, self._timer)

        def onMotion(event=None):
            # print "Mouse moved."

            if DraggedContents.get_candidate():
                DraggedContents.on_drag()

            self._delay_timer.Start(200, oneShot=True)
            self.__checkMouse()

        wx.EVT_MOTION(self, onMotion)

        wx.EVT_ENTER_WINDOW(self, self.on_enter_window)
        wx.EVT_LEAVE_WINDOW(self, self.on_leave_window)

        def finalizeDrag(event):
            # print "Finalizing drag (panel)"

            DraggedContents.clear()

            mouse_pos = self.ScreenToClient(wx.GetMousePosition())
            self.on_enter_window() if self._rect.Contains(
                mouse_pos) else self.on_leave_window()

        wx.EVT_MOUSE_CAPTURE_CHANGED(self, finalizeDrag)
##    self._is_dragging = False

        def on_left_down(event):

            if self._menu_open or DraggedContents.get_items():
                return

            self._left_down = True

            if self._current_shelf.has_mouse():
                self._current_shelf.notify_left_down()
            elif ShelfPath.has_mouse():
                ShelfPath.notify_left_down()

        wx.EVT_LEFT_DOWN(self, on_left_down)

        def onLeftUp(event):

            if not self._left_down:
                return

            self._left_down = False

            if self._menu_open:
                return

            self._current_shelf.notify_left_up()

            if ShelfPath.notify_left_up():
                self.__checkMouse()

            if self.HasCapture():
                # print "Releasing mouse on left-up."
                self.ReleaseMouse()

        wx.EVT_LEFT_UP(self, onLeftUp)

        def onRightUp(event):

            self._left_down = False

            if DraggedContents.get_items():

                if self.HasCapture():
                    # print "Releasing mouse on right-up."
                    self.ReleaseMouse()

                return

            self._menu_x = event.GetX()
            self.__showMenu()

        wx.EVT_RIGHT_UP(self, onRightUp)
##
##    self._ctrl_pressed = False

        self._cut_btns = {}  # {"buttons":[], "type":"shelf"|"tool", "shelf":Shelf}

        self._shelves = {}

        def onGainFocus(event):

            # print "DeepShelfPanel gained focus."
            self._parent.SetFocus()
# self._mgr.sendRequest("handle_deepshelf_gains_focus")

        wx.EVT_SET_FOCUS(self, onGainFocus)

        if os.path.isfile("deepshelf_data"):
            self.__loadShelfData()
        else:
            self._shelf_data = {
                "label": "", "children": [], "tools": [], "favorite": [],
                "contents_hidden": False, "password": ""
            }
            self._shelves[self._home_shelf.get_id()] = self._shelf_data

    def on_enter_window(self, event=None):

        self._current_shelf.check_dragged_contents()
        self.Refresh()

        if DraggedContents.get_candidate():
            return

        self._has_mouse = True
        self._timer.Start(500, oneShot=True)

    def on_leave_window(self, event=None):
        # print "on_leave_window(event=None)"

        if DraggedContents.get_candidate():
            # print "DraggedContents.get_candidate()"
            return

        if self._menu_open:
            # print "self._menu_open"
            return

# if not self._is_dragging and not self._frame.isPressed():
        self._has_mouse = False
        self._current_shelf.notify_mouse_leave()
        ShelfPath.notify_mouse_leave()
        ToolTip.hide()
        self.set_candidate_shelf(None)
        self.Refresh()
        self._timer.Start(500, oneShot=True)

    def get_size(self):

        return self._size

    def get_favorites_shelf(self):

        return self._fav_shelf

    def get_history_shelf(self):

        return self._hist_shelf

    def getHomeShelf(self):

        return self._home_shelf

    def setCurrentShelf(self, shelf):

        if shelf:
            self._current_shelf.notify_mouse_leave()
            self._current_shelf = shelf
            self._current_shelf.check_dragged_contents()
            self.Refresh()

    def get_current_shelf(self):

        return self._current_shelf

    def set_candidate_shelf(self, shelf):

        if self._candidate_shelf:
            self._candidate_shelf.set_as_candidate(False)

        self._candidate_shelf = shelf

        if self._candidate_shelf:
            self._candidate_shelf.set_as_candidate()

        self.Refresh()

    def getCandidateShelf(self):

        return self._candidate_shelf

    def setShelfDataValue(self, shelf_id, data_type, value):

        self._shelves[shelf_id][data_type] = value

    def getShelfDataValue(self, shelf_id, data_type):

        return self._shelves[shelf_id][data_type]

    def insertShelfData(self, shelf_id, parent_id, index):

        self._shelves[parent_id]["children"].insert(
            index, self._shelves[shelf_id])

    def removeShelfData(self, shelf_id, parent_id):

        self._shelves[parent_id]["children"].remove(self._shelves[shelf_id])

    def is_shelf_path_ready(self):

        return ShelfPath.isReady()
##
##
# def notify_ctrl_down(self):
##
# if self._menu_open or DraggedContents.get_items():
# return
##
# if not self._ctrl_pressed:
##
##      self._ctrl_pressed = True
##
# if self._current_shelf.has_mouse():
# self._current_shelf.notify_ctrl_down()
##
##
# def notifyCtrlUp(self):
##
##    self._ctrl_pressed = False

    def edit_subobjects(self, char):

        if ShelfPath.isReady() or self._current_shelf is self._hist_shelf:
            return

        if char == "BACKSPACE":
            self.__selectShelfContents("none")
        elif char == "A":
            self.__selectShelfContents("all")
        elif char == "I":
            self.__selectShelfContents("invert")
        elif char == "DEL":
            self.__removeShelfContents()
        elif char == "X":
            self.__cutShelfContents()
        elif char == "V":
            self._menu_x = 100000
            self.__pasteShelfContents()
        elif char == "H":
            self.__hideShelfContents()

    def __checkMouse(self):

        mouse_pos = self.ScreenToClient(wx.GetMousePosition())

        has_mouse = ShelfPath.check_has_mouse(mouse_pos)

        if not has_mouse and not ShelfPath.isReady():

            has_mouse = self._current_shelf.check_has_mouse(mouse_pos)

        if not has_mouse:

            rect = wx.Rect(*self._preview_rect).Inflate(0, 1)

            if self._candidate_shelf and rect.Contains(mouse_pos) and not DraggedContents.is_in_favs():
                self.setCurrentShelf(self._candidate_shelf)
                self.set_candidate_shelf(None)
                ShelfPath.reset()

    def __onDelayTimer(self, event):

        if self._menu_open:
            return

        ShelfPath.notify_mouse_hover()

        if not ShelfPath.isReady():
            self._current_shelf.notify_mouse_hover()

    def has_mouse(self):

        return self._has_mouse

    def mouseInPreviewArea(self, mouse_pos):

        rect = wx.Rect(*self._preview_rect).Inflate(0, 1)

        return rect.Contains(mouse_pos)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self._background, 0, 0)

        if self._candidate_shelf:

            dc.SetPen(wx.Pen(wx.Colour(196, 192, 222)))
            dc.SetBrush(wx.Brush(wx.Colour(131, 125, 172)))

            dc.DrawRectangleRect(self._preview_rect)
            y = 2 if self._candidate_shelf.get_button_type() == "tool" else 8
            self._candidate_shelf.draw(dc, y, flat=True)

            if not ShelfPath.isReady():
                self._current_shelf.draw(dc, self._size[1] - 30)

        elif not (ShelfPath.isReady() or ShelfPath.isParentShown()):

            y = self._size[
                1] - (42 if self._current_shelf.get_button_type() == "tool" else 30)
            self._current_shelf.draw(dc, y)

        ShelfPath.draw(dc)

    def __showMenu(self):

        self.set_candidate_shelf(None)
        button_type = self._current_shelf.get_button_type()
        is_fav_shelf = self._current_shelf is self._fav_shelf
        is_hist_shelf = self._current_shelf is self._hist_shelf

        self._menu_open = True
        btn_with_mouse = self._current_shelf.get_button_with_mouse()

        if btn_with_mouse:

            if is_hist_shelf:
                self._menu_open = False
                return

            self._menu_items["button"]["edit"].Enable(button_type == "tool")
            self._menu_items["button"]["cut"].Enable(not is_fav_shelf)
            self._menu_items["button"]["rename"].Enable(
                btn_with_mouse.get_shelf() is not None)

            self.PopupMenu(self._btn_menu)

        else:

            if self._current_shelf.is_accessible() and not ShelfPath.isReady() and not is_hist_shelf:

                self._menu_items["shelf_contents"]["menu"].Enable(True)

                btn_count = len(self._current_shelf.get_buttons())

                if btn_count and not is_fav_shelf:
                    self._menu_items["shelf_contents"]["move"].Enable(True)
                else:
                    self._menu_items["shelf_contents"]["move"].Enable(False)

                if (button_type == "" or btn_count < Shelf.get_max_button_count(button_type)) \
                        and not is_fav_shelf:
                    self._menu_items["shelf_contents"]["new"].Enable(True)
                else:
                    self._menu_items["shelf_contents"]["new"].Enable(False)

                btns_selected = len(
                    self._current_shelf.get_selected_buttons()) > 0
                self._menu_items["shelf_contents"][
                    "remove_selection"].Enable(btns_selected)
                cut_allowed = btns_selected and not is_fav_shelf
                self._menu_items["shelf_contents"][
                    "cut_selection"].Enable(cut_allowed)

                if self._cut_btns and button_type in ("", self._cut_btns["type"]):
                    self._menu_items["shelf_contents"]["paste"].Enable(True)
                else:
                    self._menu_items["shelf_contents"]["paste"].Enable(False)

                self._menu_items["shelf_contents"][
                    "access"].Enable(not is_fav_shelf)

            else:

                self._menu_items["shelf_contents"]["menu"].Enable(False)

            self.PopupMenu(self._main_menu)

        self._menu_timer.Start(1, oneShot=True)

    def __createChildShelves(self, parent_shelf, labels):

        parent_id = parent_shelf.get_id()
        child_data = self._shelves[parent_id]["children"]

        if len(labels) == 1 and not labels[0]:
            return

        for shelf in parent_shelf.createChildren([(label, None) for label in labels]):
            shelf_id = shelf.get_id()
            shelf_data = {
                "label": encode_string(shelf.get_label()), "children": [], "tools": [],
                "favorite": [], "contents_hidden": False, "password": ""
            }
            child_data.append(shelf_data)
            self._shelves[shelf_id] = shelf_data
            shelf.get_button().setShelfData(shelf_data)

    def notifyDialogOpen(self):

        self._dialog_open = True

    def __createShelfContents(self):

        button_type = self._current_shelf.get_button_type()

        if button_type == "shelf":

            self.__createShelves()

        elif button_type == "tool":

            self.__createToolButton()

        else:

            self._dialog_open = True
            dlg = ShelfContentsCreationDialog()
            answer = dlg.ShowModal()
            contents_type = dlg.getContentsType()
            dlg.Destroy()

            if answer == wx.ID_OK:
                if contents_type == 0:
                    self.__createShelves()
                else:
                    self.__createToolButton()
##
# self.SetFocus()

    def __createShelves(self):

        self.Refresh()

        self._dialog_open = True
        dlg = ShelfCreationDialog(self._current_shelf)
        answer = dlg.ShowModal()

        if answer == wx.ID_OK:
            self.__createChildShelves(self._current_shelf, dlg.getLabels())
            self.save_shelf_data()
            self.Refresh()

        dlg.Destroy()

    def relocateShelfContents(self, buttons=None, btn_type="", show_message=True):

        self.Refresh()

        if show_message:

            self._dialog_open = True
            answer = wx.MessageBox(
                "There is not enough room for all of the buttons!\n"
                + "They have to be relocated to multiple new shelves,\n"
                + "which you can create next.",
                "Additional shelves required",
                wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
            )

            if answer != wx.OK:
                return False

        if not btn_type:

            btn_type = self._current_shelf.get_button_type()

            if not btn_type:
                return False

            buttons = (self._current_shelf.get_buttons()[:], [])

        btn_count = sum([len(btns) for btns in buttons])
        max_btn_count = Shelf.get_max_button_count(btn_type)
        self._dialog_open = True
        dlg = ShelfCreationDialog(self._current_shelf, btn_count, max_btn_count,
                                  ignore_existing=True)
        answer = dlg.ShowModal()
        labels = dlg.getLabels()
        dlg.Destroy()
##
# self.SetFocus()

        if len(labels) == 1 and not labels[0]:
            return False

        if answer == wx.ID_OK:

            if btn_type == "tool":

                for btn in buttons[0] + buttons[1]:
                    self._current_shelf.removeToolButton(btn, destroy=False)

            elif btn_type == "shelf":

                shelves = self._current_shelf.get_children()[:]
                shelf_refs = [shelf.get_object()
                              for shelf in shelves]  # keep shelves alive
                self._current_shelf.removeChildren(shelves)
                parent_id = self._current_shelf.get_id()

                for shelf in shelves:
                    shelf_id = shelf.get_id()
                    self._shelves[parent_id]["children"].remove(
                        self._shelves[shelf_id])

            self.__createChildShelves(self._current_shelf, labels)
            self._current_shelf.fillChildren(buttons, btn_type)

            self.save_shelf_data()

            self.Refresh()

            return True

        else:

            return False

    def __removeShelfContents(self, selected=True):

        if selected and not self._current_shelf.get_selected_buttons():
            return

        if self._current_shelf.get_button_type() == "tool":
            self.__removeToolButtons(selected)
        else:
            if self._current_shelf is self._fav_shelf:
                self.__removeFavorites(selected)
            else:
                self.__removeShelves(selected)
##
# self.SetFocus()

    def __removeFavorites(self, selected=True):

        self.Refresh()

        msg = "You have chosen to delete "

        if selected:
            buttons = self._fav_shelf.get_selected_buttons()
        else:
            buttons = [self._fav_shelf.get_button_with_mouse()]

        if len(buttons) == 1:
            label = buttons[0].get_label()
            msg += "the following shelf from Favorites:\n\n" + label
        else:
            msg += "the selected shelves from Favorites."

        self._dialog_open = True
        answer = wx.MessageBox(
            msg, "Confirm favorites removal",
            wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
        )

        if answer == wx.OK:

            self.set_candidate_shelf(None)
            ToolTip.hide()

            for btn in buttons:
                shelf_id = btn.get_shelf().get_id()
                self._shelves[shelf_id]["favorite"] = []

            self._fav_shelf.removeShelfButtons(buttons)

            if not self._fav_shelf.get_button_type():
                self._fav_shelf.set_button_type("shelf")

            self.Refresh()

            self.save_shelf_data()

    def __removeShelves(self, selected=True):

        self.Refresh()

        msg = "You have chosen to delete "

        if selected:
            shelves = [btn.get_shelf()
                       for btn in self._current_shelf.get_selected_buttons()]
        else:
            shelves = [self._current_shelf.get_button_with_mouse().get_shelf()]

        if len(shelves) == 1:
            label = shelves[0].get_label()
            msg += "the following shelf:\n\n" + label + "\n\nAll of its "
        else:
            msg += "the selected shelves.\n\nAll of their "

        self._dialog_open = True
        answer = wx.MessageBox(
            msg + "contents will be lost!",
            "Confirm shelf removal",
            wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
        )

        if answer == wx.OK:

            self.set_candidate_shelf(None)
            ToolTip.hide()

            fav_btns = self._fav_shelf.get_buttons()
            fav_shelves = [btn.get_shelf() for btn in fav_btns]
            fav_btns_to_remove = []
            hist_btns = self._hist_shelf.get_buttons()
            hist_shelves = [btn.get_shelf() for btn in hist_btns]
            hist_btns_to_remove = []

            def activateHotkeys(shelf_data):

                for child_data in shelf_data["children"]:
                    activateHotkeys(child_data)

                for btn_props in shelf_data["tools"]:
                    hotkey_string = decode_string(btn_props["hotkey"])
                    hotkey = ToolButton.getHotkeyFromString(hotkey_string)
                    ToolButton.activateHotkey(hotkey)

            for shelf in shelves:
                activateHotkeys(self._shelves[shelf.get_id()])

            def deleteShelfData(shelf):

                for child_shelf in shelf.get_children():
                    deleteShelfData(child_shelf)

                for btn in shelf.get_cut_buttons():
                    self.releaseCutButton(btn)

                if shelf.get_button_type() == "tool":
                    for btn in shelf.get_buttons():
                        ToolButton.set_hotkey(hotkey_old=btn.getHotkey())
                        Shelf.removeToggleButton(btn)

                if shelf in fav_shelves:
                    fav_btns_to_remove.append(
                        fav_btns[fav_shelves.index(shelf)])

                if shelf in hist_shelves:
                    hist_btns_to_remove.append(
                        hist_btns[hist_shelves.index(shelf)])

                del self._shelves[shelf.get_id()]

            parent_id = self._current_shelf.get_id()

            for shelf in shelves:
                shelf_id = shelf.get_id()
                self._shelves[parent_id]["children"].remove(
                    self._shelves[shelf_id])
                deleteShelfData(shelf)

            if fav_btns_to_remove:

                self._fav_shelf.removeShelfButtons(fav_btns_to_remove)

                if not self._fav_shelf.get_button_type():
                    self._fav_shelf.set_button_type("shelf")

            if hist_btns_to_remove:
                self._hist_shelf.removeShelfButtons(hist_btns_to_remove)

            self._current_shelf.removeChildren(shelves)

            self.Refresh()

            self.save_shelf_data()

    def __renameShelfContents(self):

        if self._current_shelf.get_button_type() == "tool":
            self.__renameToolButton()
        else:
            self.__renameChildShelf()
##
# self.SetFocus()

    def __renameChildShelf(self):

        self.Refresh()

        button = self._current_shelf.get_button_with_mouse()
        label = button.get_label()
        self._dialog_open = True
        label = wx.GetTextFromUser(
            "Please enter a new name for this shelf:",
            "Rename shelf", label, None
        )

        if label:

            self._current_shelf.setShelfButtonLabel(button, label, False)
            shelf = button.get_shelf()
            shelf_id = shelf.get_id()

            if self._current_shelf is self._fav_shelf:
                self._shelves[shelf_id]["favorite"][0] = encode_string(label)
            else:
                self._shelves[shelf_id]["label"] = encode_string(label)

            hist_btns = self._hist_shelf.get_buttons()
            hist_shelves = [btn.get_shelf() for btn in hist_btns]

            if shelf in hist_shelves:
                self._hist_shelf.setShelfButtonLabel(
                    hist_btns[hist_shelves.index(shelf)], label, False)

            self.Refresh()

            self.save_shelf_data()

    def restoreShelfContents(self, shelf):

        btn_data = self._shelves[shelf.get_id()]["tools"]

        fav_btns = self._fav_shelf.get_buttons()
        fav_btn_label_data = []

        if btn_data:

            for btn_props in btn_data:
                hotkey_string = decode_string(btn_props["hotkey"])
                hotkey = ToolButton.getHotkeyFromString(hotkey_string)
                ToolButton.activateHotkey(hotkey)

            shelf.insertToolButtons(btn_data)

        else:

            shelf_data = self._shelves[shelf.get_id()]["children"]
            favs = {}

            self.__createShelvesFromData(shelf, shelf_data, favs)

            for fav_index in sorted(favs.iterkeys()):

                fav_label, fav_shelf, data = favs[fav_index]

                if fav_shelf:
                    btn = fav_btns[fav_index]
                    btn.setShelf(fav_shelf)
                    col = None if fav_shelf.is_accessible() else (128, 128, 128)
                    fav_btn_label_data.append(
                        (btn, decode_string(data["favorite"][0]), col))

        fav_shelves = [btn.get_shelf() for btn in fav_btns]

        if shelf in fav_shelves:
            btn = fav_btns[fav_shelves.index(shelf)]
            fav_btn_label_data.append((btn, btn.get_label(), None))

        if fav_btn_label_data:
            self._fav_shelf.setShelfButtonLabels(fav_btn_label_data)

        hist_btns = self._hist_shelf.get_buttons()
        hist_shelves = [btn.get_shelf() for btn in hist_btns]

        if shelf in hist_shelves:
            btn = hist_btns[hist_shelves.index(shelf)]
            self._hist_shelf.setShelfButtonLabel(btn, btn.get_label(), None)

        if shelf is not self._home_shelf:
            btn = shelf.get_button()
            shelf.get_parent().setShelfButtonLabel(btn, btn.get_label())

        self.Refresh()

    def __hideShelfContents(self):

        if not self._current_shelf.is_accessible() or self._current_shelf is self._fav_shelf:
            return

        hist_btns = self._hist_shelf.get_buttons()
        hist_shelves = [btn.get_shelf() for btn in hist_btns]
        hist_btns_to_remove = []

        fav_btns = self._fav_shelf.get_buttons()
        fav_shelves = [btn.get_shelf() for btn in fav_btns]
        fav_btn_label_data = []

        def updateHistAndFavs(shelf):

            for child in shelf.get_children():

                if child in hist_shelves:
                    hist_btns_to_remove.append(
                        hist_btns[hist_shelves.index(child)])

                if child in fav_shelves:
                    btn = fav_btns[fav_shelves.index(child)]
                    btn.setShelf(None)
                    fav_btn_label_data.append(
                        (btn, "<hidden>", (128, 128, 128)))

                if child.is_accessible():
                    updateHistAndFavs(child)

            for btn in shelf.get_cut_buttons():
                self.releaseCutButton(btn)

        updateHistAndFavs(self._current_shelf)

        def deactivateHotkeys(shelf):

            for child_shelf in shelf.get_children():
                deactivateHotkeys(child_shelf)

            if shelf.get_button_type() == "tool":
                for btn in shelf.get_buttons():
                    hotkey = btn.getHotkey()
                    ToolButton.deactivateHotkey(hotkey)
                    ToolButton.set_hotkey(hotkey_old=hotkey)
                    Shelf.removeToggleButton(btn)

        deactivateHotkeys(self._current_shelf)

        if hist_btns_to_remove:
            self._hist_shelf.removeShelfButtons(hist_btns_to_remove)

        if self._current_shelf in hist_shelves:
            btn = hist_btns[hist_shelves.index(self._current_shelf)]
            self._hist_shelf.setShelfButtonLabel(
                btn, btn.get_label(), (128, 128, 128))

        if self._current_shelf in fav_shelves:
            btn = fav_btns[fav_shelves.index(self._current_shelf)]
            fav_btn_label_data.append((btn, btn.get_label(), (128, 128, 128)))

        if fav_btn_label_data:
            self._fav_shelf.setShelfButtonLabels(fav_btn_label_data)

        shelf = self._current_shelf

        if shelf is not self._home_shelf:
            btn = shelf.get_button()
            shelf.get_parent().setShelfButtonLabel(btn, btn.get_label(), (128, 128, 128))

        self._current_shelf.set_access(False)

        self.Refresh()
##
# self.SetFocus()

    def __createToolButton(self):

        self.Refresh()

        self._dialog_open = True
        btn_dlg = ToolButtonCreationDialog(self._current_shelf, self._menu_x)
        answer = btn_dlg.ShowModal()

        if answer == wx.ID_OK:

            button = btn_dlg.create_button()
            btns = self._current_shelf.get_buttons()

            if button in btns:
                index = btns.index(button)
                btn_data = self.getShelfDataValue(
                    self._current_shelf.get_id(), "tools")
                btn_data.insert(index, button.getProps())

            self.Refresh()
            self.save_shelf_data()

        btn_dlg.Destroy()

    def __editToolButton(self):

        self.Refresh()

        button = self._current_shelf.get_button_with_mouse()
        self._dialog_open = True
        btn_dlg = ToolButtonEditingDialog(button)
        answer = btn_dlg.ShowModal()

        if answer == wx.ID_OK:
            btn_dlg.saveChanges()
            self.Refresh()
            self.save_shelf_data()

        btn_dlg.Destroy()
##
# self.SetFocus()

    def __renameToolButton(self):

        self.Refresh()

        button = self._current_shelf.get_button_with_mouse()
        label = button.get_label()
        self._dialog_open = True
        label = wx.GetTextFromUser(
            "Please enter a new name for this button:",
            "Rename button", label, None
        )

        if label:
            button.set_label(label)
            self.save_shelf_data()

    def __removeToolButtons(self, selected=True):

        self.Refresh()

        msg = "You have chosen to delete "

        if selected:

            btns = self._current_shelf.get_selected_buttons()

            if not btns:
                return

            if len(btns) == 1:
                label = btns[0].get_label()
                msg += "the following button:\n\n" + label
            else:
                msg += "all the selected buttons!"

        else:

            button = self._current_shelf.get_button_with_mouse()
            btns = [button]
            label = button.get_label()
            msg += "the following button:\n\n" + label

        self._dialog_open = True
        answer = wx.MessageBox(
            msg, "Confirm button removal",
            wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
        )

        if answer == wx.OK:
            # print "Removing button:", label

            for btn in btns:
                self._current_shelf.removeToolButton(btn)
                ToolButton.set_hotkey(hotkey_old=btn.getHotkey())

            self.Refresh()

            self.save_shelf_data()

    def __toggleShelfContentsSelection(self):

        self._current_shelf.toggle_button_selection()

        self.Refresh()

    def __selectShelfContents(self, mode):

        self._current_shelf.select_buttons(mode)

        self.Refresh()

    def __cutShelfContents(self, selected=True):

        if selected and not self._current_shelf.get_selected_buttons():
            return

        if self._current_shelf is self._fav_shelf:
            return

        if self._cut_btns:

            for btn in self._cut_btns["buttons"]:
                btn.set_cut(False)

            self._cut_btns["shelf"]._update_cut_btn_ids()

        btns = self._current_shelf.cut_buttons(selected)
        btn_type = self._current_shelf.get_button_type()
        self._cut_btns = {"buttons": btns,
                          "type": btn_type, "shelf": self._current_shelf}

        self.Refresh()

    def releaseCutButton(self, button):

        if self._cut_btns and button in self._cut_btns["buttons"]:

            self._cut_btns["buttons"].remove(button)

            if not self._cut_btns["buttons"]:
                self._cut_btns = {}

    def __pasteShelfContents(self):

        if not self._cut_btns:
            return

        btn_type = self._cut_btns["type"]
        shelf = self._current_shelf

        if not shelf.is_accessible() or shelf.get_button_type() not in ("", btn_type):
            return

        paste_ok = True
        buttons = self._cut_btns["buttons"][:]

        if btn_type == "shelf":

            ancestors = shelf.get_ancestors() + [shelf]
            ancestor = None
            ancestor_btn = None

            for btn in buttons:
                if btn.get_shelf() in ancestors:
                    ancestor_btn = btn
                    ancestor = btn.get_shelf()
                    break

            if ancestor:

                buttons.remove(ancestor_btn)

                if buttons:

                    self._dialog_open = True
                    answer = wx.MessageBox(
                        "A shelf cannot be moved into itself!\n\n"
                        + "The following shelf cannot be dropped here:\n\n"
                        + ancestor.get_label()
                        + "\n\nOnly the remaining shelves will be moved.",
                        "Invalid relocation",
                        wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
                    )

                    if answer != wx.OK:
                        paste_ok = False

                else:

                    self._dialog_open = True
                    wx.MessageBox(
                        "A shelf cannot be moved into itself!\n\n"
                        + "The following shelf cannot be dropped here:\n\n"
                        + ancestor.get_label(),
                        "Invalid relocation",
                        wx.OK | wx.ICON_EXCLAMATION, self
                    )

                    paste_ok = False
##
# self.SetFocus()

            if paste_ok:
                paste_ok = shelf.drop_children(100000, buttons)

        else:

            paste_ok = shelf.drop_tool_buttons(100000, buttons)

        if paste_ok:
            self.save_shelf_data()
            self.Refresh()

    def __reset(self):

        self._current_shelf = self._home_shelf
        self._home_shelf.clear()
        self._fav_shelf.clear()
        self._fav_shelf.set_button_type("shelf")
        self._hist_shelf.clear()
        ShelfPath.reset()
        self._cut_btns = {}
        ToolButton.clearHotkeys()
        Shelf.clearToggleButtons()
        Icons.clear()

    def __clear(self):

        self.Refresh()

        self._dialog_open = True
        answer = wx.MessageBox(
            "You have chosen to clear the current layout;\n"
            + "all contents will be lost!\n"
            + "Save current layout first?",
            "Save current DeepShelf layout",
            wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION, self
        )

        if answer == wx.YES:
            self.__save()
        elif answer == wx.CANCEL:
            return

        self.__reset()
        self._shelf_data = {
            "label": "", "children": [], "tools": [], "favorite": [],
            "contents_hidden": False, "password": ""
        }
        self._shelves = {self._home_shelf.get_id(): self._shelf_data}
        self.save_shelf_data()
        self.Refresh()
##
# self.SetFocus()

    def __save(self):

        self.Refresh()

        self._dialog_open = True
        filename = wx.FileSelector(
            "Save DeepShelf layout as",
            "", "", "dsl", "*.dsl",
            wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
            self
        )

        if filename:

            with open(filename, "wb") as shelf_data_file:
                cPickle.dump(self._shelf_data, shelf_data_file, -1)
##
# self.SetFocus()

    def __load(self):

        self.Refresh()

        if self._home_shelf.get_buttons():

            self._dialog_open = True
            answer = wx.MessageBox(
                "The current layout will be lost when loading"
                + " another one!\nSave current layout first?",
                "Save current DeepShelf layout",
                wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION, self
            )

            if answer == wx.YES:
                self.__save()
            elif answer == wx.CANCEL:
                return

        self._dialog_open = True
        filename = wx.FileSelector(
            "Load DeepShelf layout",
            "", "", "dsl", "*.dsl",
            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            self
        )

        if filename:

            with open(filename, "rb") as shelf_data_file:
                shelf_data = cPickle.load(shelf_data_file)

            with open("deepshelf_data", "wb") as shelf_data_file:
                cPickle.dump(shelf_data, shelf_data_file, -1)

            self.__reset()

            self.__loadShelfData()
            self.Refresh()
##
# self.SetFocus()

    def save_shelf_data(self):

        with open("deepshelf_data", "wb") as shelf_data_file:
            cPickle.dump(self._shelf_data, shelf_data_file, -1)

    def __loadShelfData(self):

        if not os.path.isfile("deepshelf_data"):
            return

        self._shelves = {}

        with open("deepshelf_data", "rb") as shelf_data_file:
            self._shelf_data = cPickle.load(shelf_data_file)

        self._shelves[self._home_shelf.get_id()] = self._shelf_data
        root_contents_hidden = self._shelf_data["contents_hidden"]

        if root_contents_hidden:
            self._home_shelf.set_access(
                False, True, self._shelf_data["password"])

        if self._shelf_data["tools"]:

            if not root_contents_hidden:
                self._home_shelf.insertToolButtons(self._shelf_data["tools"])

            return

        favs = {}

        self.__createShelvesFromData(self._home_shelf, self._shelf_data["children"],
                                     favs, root_contents_hidden)

        fav_label_data = []
        fav_shelves = []
        fav_shelf_data = []

        for fav_index in sorted(favs.iterkeys()):

            fav_label, shelf, data = favs[fav_index]

            fav_label_col = None if (
                shelf and shelf.is_accessible()) else (128, 128, 128)
            fav_label_data.append((fav_label, fav_label_col))
            fav_shelves.append(shelf)
            fav_shelf_data.append(data)

        if fav_label_data:

            fav_btns = self._fav_shelf.insertShelfButtons(
                0, label_data=fav_label_data)

            for btn, shelf, data in zip(fav_btns, fav_shelves, fav_shelf_data):
                btn.setShelf(shelf, data)

    def __createShelvesFromData(self, root_shelf, data, favs, root_contents_hidden=False):

        def loadShelf(parent_shelf, shelf_data, parent_contents_hidden):

            if parent_contents_hidden:
                shelves = [None] * len(shelf_data)
            else:
                label_data = [(decode_string(shelf_props["label"]),
                               (128, 128, 128) if shelf_props["contents_hidden"] else None)
                              for shelf_props in shelf_data]
                shelves = parent_shelf.createChildren(label_data=label_data)

            for shelf, shelf_props in zip(shelves, shelf_data):

                child_data = shelf_props["children"]
                fav_data = shelf_props["favorite"]
                contents_hidden = shelf_props["contents_hidden"]
                btn_data = shelf_props["tools"]

                if not parent_contents_hidden:
                    shelf_id = shelf.get_id()
                    self._shelves[shelf_id] = shelf_props
                    shelf.get_button().setShelfData(shelf_props)

                if fav_data:
                    fav_label, fav_index = fav_data
                    favs[fav_index] = ("<hidden>" if parent_contents_hidden
                                       else decode_string(fav_label), shelf, shelf_props)

                activateHotkey = ToolButton.deactivateHotkey if (parent_contents_hidden
                                                                 or contents_hidden) else ToolButton.activateHotkey

                for btn_props in btn_data:
                    hotkey_string = decode_string(btn_props["hotkey"])
                    hotkey = ToolButton.getHotkeyFromString(hotkey_string)
                    activateHotkey(hotkey)

                if btn_data and not (parent_contents_hidden or contents_hidden):
                    shelf.insertToolButtons(btn_data)

                loadShelf(shelf, child_data,
                          parent_contents_hidden or contents_hidden)

                if contents_hidden and not parent_contents_hidden:
                    shelf.set_access(False, True, shelf_props["password"])

        loadShelf(root_shelf, data, root_contents_hidden)

    def addShelfToHistory(self, shelf):

        self._hist_shelf.addShelf(shelf)

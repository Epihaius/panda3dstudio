# DeepShelf module.

# Implements the Path, Favorites, History, Home and Parent buttons.

from .base import *


class Button(object):

    def __init__(self, bitmap_name, x, y):

        self._bitmaps = {"normal": {}, "hilited": {}, "down": {}, "flat": {}}

        for state in self._bitmaps:
            self._bitmaps[state] = wx.Bitmap(bitmap_name + state + ".png")

        self._shelf = None
        self._rect = wx.Rect(x, y, *self._bitmaps["normal"].GetSize())
        self._has_mouse = False
        self._is_ready = False
        self._is_down = False
        self._is_hidden = True

    def setShelf(self, shelf):

        self._shelf = shelf

    def get_size(self):

        return self._rect.GetSize()

    def getRect(self):

        return self._rect

    def has_mouse(self):

        return self._has_mouse

    def isReady(self):

        return self._is_ready

    def is_hidden(self):

        return self._is_hidden

    def draw(self, dc, flat=False):

        if self._is_hidden:
            return

        draw_rect = self._shelf.is_candidate() if self._shelf else self._is_ready

        if draw_rect:
            dc.SetPen(wx.Pen(wx.Colour(196, 192, 222)))
            dc.SetBrush(wx.Brush(wx.Colour(131, 125, 172)))
            rect = wx.Rect(*self._rect).Inflate(2, 2)
            dc.DrawRectangleRect(rect)
            x_, y_, w, h = rect
            dc.SetPen(wx.Pen(wx.Colour(131, 125, 172)))
            dc.DrawLine(x_ + 1, y_, x_ + w - 1, y_)

        state = "flat" if flat else "down" if self._is_down else "hilited" if self._has_mouse else "normal"
        dc.DrawBitmap(self._bitmaps[state], *self._rect.GetPosition())

    def check_has_mouse(self, mouse_pos):

        if self._is_hidden:
            return False

        self._has_mouse = self._rect.Contains(mouse_pos)

        if not self._has_mouse:
            self._is_ready = False
            self._is_down = False

        return self._has_mouse

    def press(self):

        self._is_down = True

    def release(self):

        if self._is_down:
            self._is_down = False
            return True

        return False

    def show(self, x=None):

        self._is_hidden = False

        if x is not None:
            self._rect.SetX(x)

    def hide(self):

        self._is_hidden = True
        self._has_mouse = False
        self._is_ready = False
        self._is_down = False

    def notify_mouse_hover(self):

        if self._is_ready:
            return False

        if self._has_mouse:
            self._is_ready = True

        return self._is_ready

    def notify_mouse_leave(self):

        self._has_mouse = False
        self._is_ready = False
        self._is_down = False


class PathButton(Button):

    def __init__(self, bitmap_name, x, y):

        self._bitmaps = {"normal": {}, "hilited": {}, "down": {}, "active": {}}

        for state in self._bitmaps:
            self._bitmaps[state] = wx.Bitmap(bitmap_name + state + ".png")

        self._rect = wx.Rect(x, y, *self._bitmaps["normal"].GetSize())
        self._has_mouse = False
        self._is_ready = False
        self._is_down = False

    def draw(self, dc, path_ready):

        active = path_ready and not self._is_ready
        state = "active" if active else "down" if self._is_down else "hilited" if self._has_mouse else "normal"
        dc.DrawBitmap(self._bitmaps[state], *self._rect.GetPosition())

    def check_has_mouse(self, mouse_pos):

        self._has_mouse = self._rect.Contains(mouse_pos)

        if not self._has_mouse:
            self._is_ready = False

        return self._has_mouse


class ParentButton(Button):

    def __init__(self, bitmap_name, x, y):

        self._bitmaps = {"normal": {}, "hilited": {}, "down": {}}

        for state in self._bitmaps:
            self._bitmaps[state] = wx.Bitmap(bitmap_name + state + ".png")

        self._rect = wx.Rect(x, y, *self._bitmaps["normal"].GetSize())
        self._has_mouse = False
        self._is_ready = False
        self._is_down = False
        self._is_hidden = False

    def draw(self, dc):

        if self._is_hidden:
            return

        state = "down" if self._is_down else "hilited" if self._has_mouse else "normal"
        dc.DrawBitmap(self._bitmaps[state], *self._rect.GetPosition())


class ScrollButton(Button):

    def __init__(self, bitmap_name, x, y, direction):

        Button.__init__(self, bitmap_name, x, y)

        self._bitmaps["disabled"] = wx.Bitmap(bitmap_name + "disabled.png")
        self._items = []
        self._direction = direction

    def hasItems(self):

        return True if self._items else False

    def clearItems(self):

        self._items = []

    def addItems(self, items):

        if self._direction == "left":
            self._items += items
        else:
            self._items[:0] = items

    def getItem(self):

        return self._items.pop(-1 if self._direction == "left" else 0) if self._items else None

    def draw(self, dc, flat=False):

        if self._is_hidden:
            return

        state = "flat" if flat else "down" if self._is_down else "hilited" if (self._has_mouse
                                                                               and self._items) else "normal" if self._items else "disabled"
        dc.DrawBitmap(self._bitmaps[state], *self._rect.GetPosition())

    def press(self):

        if self._items:
            self._is_down = True


class ShelfPath(object):

    _panel = None
    _border_width = 0
    _panel_width = 0
    _font = None
    _main_btns = {
        "path": None,
        "parent": None,
        "fav": None,
        "hist": None,
        "home": None,
        "scroll_left": None,
        "scroll_right": None
    }
    _shelf_btns = []
    _hilited_btn = None
    _connector = " > "
    _connector_width = 0
    _connector_offset = 0
    _separator = "|"
    _separator_width = 0
    _ellipsis = "..."
    _ellipsis_width = 0
    _has_mouse = False
    _is_ready = False
    _rect = None
    _parent_shelf_rect = None

    @classmethod
    def init(cls, panel, bitmap_names, border_width, panel_width, panel_height, font):

        cls._panel = panel
        cls._border_width = border_width
        cls._panel_width = panel_width
        cls._font = font

        mem_dc = wx.MemoryDC()
        gc = wx.GraphicsContext.Create(mem_dc)
        gc.SetFont(font)
        cls._connector_width, h = gc.GetTextExtent(cls._connector)
        cls._separator_width, h = gc.GetTextExtent(cls._separator)
        cls._ellipsis_width, h = gc.GetTextExtent(cls._ellipsis)

        x = border_width + 5
        cls._main_btns["path"] = PathButton(bitmap_names["path_btn"], x, 44)
        w, h = cls._main_btns["path"].get_size()
        cls._main_btns["path"].show()
        x += w + 5
        cls._main_btns["fav"] = Button(bitmap_names["fav_btn"], x, 44)
        x += w + cls._separator_width
        cls._main_btns["hist"] = Button(bitmap_names["hist_btn"], x, 44)
        x += w + cls._separator_width
        cls._main_btns["home"] = Button(bitmap_names["home_btn"], x, 44)
        x += w + cls._separator_width
        cls._main_btns["scroll_left"] = ScrollButton(bitmap_names["scroll_left_btn"],
                                                     x, 44, "left")
        x = panel_width - border_width - 5 - w
        cls._main_btns["parent"] = ParentButton(
            bitmap_names["parent_btn"], x, 44)
        cls._main_btns["scroll_right"] = ScrollButton(bitmap_names["scroll_right_btn"],
                                                      x, 44, "right")

        cls._rect = wx.Rect(border_width + 5, 44,
                            panel_width - border_width * 2 - 10, h)
        cls._parent_shelf_rect = wx.Rect(border_width + 10 + w, 44,
                                         panel_width - border_width * 2 - 15 - w, h)

    @classmethod
    def setRootShelves(cls, root_shelves):

        for root_shelf in ("fav", "hist", "home"):
            cls._main_btns[root_shelf].setShelf(root_shelves[root_shelf])

    @classmethod
    def getButtonSize(cls):

        return cls._main_btns["path"].get_size()

    @classmethod
    def has_mouse(cls):

        return cls._has_mouse

    @classmethod
    def isReady(cls):

        return cls._is_ready

    @classmethod
    def isParentShown(cls):

        return cls._main_btns["parent"].isReady()

    @classmethod
    def __setShelfButtons(cls, buttons, from_right=False):

        scroll_left_btn = cls._main_btns["scroll_left"]
        scroll_right_btn = cls._main_btns["scroll_right"]
        x1 = scroll_left_btn.getRect().GetRight() + cls._separator_width
        x2 = scroll_right_btn.getRect().GetLeft() - cls._separator_width
        path_width = 0
        total_btn_width = 0

        if from_right:

            for btn in buttons[::-1]:

                btn_width = btn.get_width()
                w = btn_width + cls._connector_width

                if x1 + path_width + w <= x2:
                    path_width += w
                    total_btn_width += btn_width
                else:
                    index = buttons.index(btn)
                    scroll_left_btn.addItems(buttons[:index + 1])
                    del buttons[:index + 1]
                    scroll_left_btn.show()
                    scroll_right_btn.show()
                    break

        else:

            for btn in buttons:

                btn_width = btn.get_width()
                w = btn_width + cls._connector_width

                if x1 + path_width + w <= x2:
                    path_width += w
                    total_btn_width += btn_width
                else:
                    index = buttons.index(btn)
                    scroll_right_btn.addItems(buttons[index:])
                    del buttons[index:]
                    scroll_left_btn.show()
                    scroll_right_btn.show()
                    break

        cls._shelf_btns = buttons
        scrollable = scroll_left_btn.hasItems() or scroll_right_btn.hasItems()
        con_width = (x2 - x1 - total_btn_width) // max(1, len(buttons) - 1) \
            if scrollable else cls._connector_width
        cls._connector_offset = (con_width - cls._connector_width) // 2
        btn_name = "scroll_left" if scrollable else "home"
        rect = cls._main_btns[btn_name].getRect()
        x = rect.GetRight() + (cls._separator_width if scrollable
                               else cls._connector_width)

        for btn in buttons:
            btn.moveToPath(x)
            x += btn.get_width() + con_width

    @classmethod
    def __clearShelfButtons(cls):

        for btn in cls._shelf_btns:
            btn.moveFromPath()

        cls._shelf_btns = []

        cls._main_btns["scroll_left"].clearItems()
        cls._main_btns["scroll_right"].clearItems()
        cls._main_btns["scroll_left"].hide()
        cls._main_btns["scroll_right"].hide()

    @classmethod
    def __getButtonData(cls):

        data = [
            (cls._main_btns["fav"].getRect().GetRight(), cls._separator),
            (cls._main_btns["hist"].getRect().GetRight(), cls._separator)
        ]

        x = cls._main_btns["home"].getRect().GetRight()

        if cls._shelf_btns:

            if cls._main_btns["scroll_left"].is_hidden():
                data.append((x, cls._connector))

            for btn in cls._shelf_btns[:-1]:
                x = btn.getPathRect().GetRight()
                data.append((x + cls._connector_offset, cls._connector))

        return data

    @classmethod
    def draw(cls, dc):

        path_btn_is_ready = cls._main_btns["path"].isReady()
        parent_btn_is_ready = cls._main_btns["parent"].isReady()
        is_ready = path_btn_is_ready or parent_btn_is_ready

        if path_btn_is_ready or parent_btn_is_ready:
            dc.SetPen(wx.Pen(wx.Colour(196, 192, 222)))
            dc.SetBrush(wx.Brush(wx.Colour(131, 125, 172)))
            rect = wx.Rect(
                *(cls._parent_shelf_rect if parent_btn_is_ready else cls._rect)).Inflate(2, 2)
            dc.DrawRectangleRect(rect)

        cls._main_btns["path"].draw(dc, cls._is_ready)
        cls._main_btns["parent"].draw(dc)

        for btn_name in ("fav", "hist", "home", "scroll_left", "scroll_right"):
            cls._main_btns[btn_name].draw(dc, flat=path_btn_is_ready)

        for btn in cls._shelf_btns:
            btn.draw(dc, 44, flat=is_ready,
                     in_path=False if parent_btn_is_ready else True)

        if not (cls._panel.getCandidateShelf() or cls._is_ready):

            gc = wx.GraphicsContext.Create(dc)
            gc.SetFont(cls._font, wx.NamedColour("white"))
            path_label_data = cls._panel.get_current_shelf().getPathLabelData()

            if cls._main_btns["parent"].isReady():
                path_label_data = path_label_data[:-1]

            path_width = 0
            draw_ellipsis = False

            for data_item in path_label_data[::-1]:

                w = cls._connector_width + data_item[1]

                if path_width + w < cls._panel_width - 100:
                    path_width += w
                else:
                    path_width += cls._connector_width + cls._ellipsis_width
                    index = path_label_data.index(data_item)
                    path_label_data = path_label_data[index + 1:]
                    draw_ellipsis = True
                    break

            w, path_height = gc.GetTextExtent("fg")
            x = (cls._panel_width - path_width) // 2
            y = 2 + (28 - path_height) // 2
            dc.DrawBitmap(cls._panel.get_current_shelf(
            ).getRootIcon(), x - 29 // 2, 2)
            x += 29 // 2

            if draw_ellipsis:
                gc.SetFont(cls._font, wx.NamedColour("cyan"))
                gc.DrawText(cls._connector + cls._ellipsis, x, y)
                x += cls._connector_width + cls._ellipsis_width

            for label, width in path_label_data:
                gc.SetFont(cls._font, wx.NamedColour("cyan"))
                gc.DrawText(cls._connector, x, y)
                x += cls._connector_width
                gc.SetFont(cls._font, wx.NamedColour("white"))
                gc.DrawText(label, x, y)
                x += width

        elif cls._is_ready:

            gc = wx.GraphicsContext.Create(dc)
            gc.SetFont(cls._font, wx.NamedColour("cyan"))
            path_btn_data = cls.__getButtonData()
            w, path_height = gc.GetTextExtent("fg")
            y = 44 + (28 - path_height) // 2

            for x, text in path_btn_data:
                gc.DrawText(text, x, y)

    @classmethod
    def reset(cls):

        cls._is_ready = False
        cls._main_btns["path"].release()
        cls._main_btns["parent"].show()
        cls._main_btns["fav"].hide()
        cls._main_btns["hist"].hide()
        cls._main_btns["home"].hide()
        cls.__clearShelfButtons()
        cls._hilited_btn = None
        cls._parent_shown = False
        cls._panel.set_candidate_shelf(None)
        cls._panel.Refresh()

    @classmethod
    def check_has_mouse(cls, mouse_pos):

        refresh_needed = False

        if cls._main_btns["path"].has_mouse():
            if not cls._main_btns["path"].check_has_mouse(mouse_pos):
                if not cls._rect.Contains(mouse_pos):
                    cls.reset()
                    cls._panel.get_current_shelf().check_dragged_contents()

        if cls._main_btns["parent"].isReady():

            if not cls._main_btns["parent"].check_has_mouse(mouse_pos):

                if cls._parent_shelf_rect.Contains(mouse_pos):

                    parent_shelf = cls._panel.get_current_shelf().get_parent()

                    if parent_shelf:
                        cls._panel.setCurrentShelf(parent_shelf)

                cls._shelf_btns = []

        has_mouse = False
        hilited_btn = None
        hilited_btn_name = ""

        for btn_name, btn in cls._main_btns.iteritems():
            if btn.check_has_mouse(mouse_pos):
                has_mouse = True
                hilited_btn = btn
                hilited_btn_name = btn_name

        if not hilited_btn:
            for btn in cls._shelf_btns:
                if btn.check_has_mouse(mouse_pos):
                    has_mouse = True
                    hilited_btn = btn

        if cls._hilited_btn is not hilited_btn:

            cls._hilited_btn = hilited_btn
            refresh_needed = True

        if cls._has_mouse != has_mouse:

            cls._has_mouse = has_mouse

        if refresh_needed:
            cls._panel.Refresh()

        return has_mouse

    @classmethod
    def __activateButton(cls, button, execute=False):

        if execute and button not in (cls._main_btns["scroll_left"],
                                      cls._main_btns["scroll_right"]):
            button.notify_mouse_leave()

        if button is cls._main_btns["path"]:

            if DraggedContents.get_type():
                cls._panel.SetCursor(CURSORS["no_access"])

            cls._is_ready = True
            button.press()
            cls._main_btns["fav"].show()
            cls._main_btns["hist"].show()
            cls._main_btns["home"].show()
            cls._main_btns["parent"].hide()
            cls.__clearShelfButtons()
            cls.__setShelfButtons(
                cls._panel.get_current_shelf().getPathButtons())
            cls._panel.set_candidate_shelf(None)

            return True

        elif button is cls._main_btns["parent"]:

            parent_shelf = cls._panel.get_current_shelf().get_parent()

            if execute:
                cls._panel.setCurrentShelf(parent_shelf)
                cls.reset()
            else:
                cls._shelf_btns = parent_shelf.get_buttons()[:]
                cls._parent_shown = True
                cls._panel.set_candidate_shelf(None)

            return True

        elif button is cls._main_btns["fav"]:

            if execute:
                cls._panel.setCurrentShelf(cls._panel.get_favorites_shelf())
                cls.reset()
            else:
                cls._panel.set_candidate_shelf(
                    cls._panel.get_favorites_shelf())

            return True

        elif button is cls._main_btns["hist"]:

            if execute:
                cls._panel.setCurrentShelf(cls._panel.get_history_shelf())
                cls.reset()
            else:
                cls._panel.set_candidate_shelf(cls._panel.get_history_shelf())

            return True

        elif button is cls._main_btns["home"]:

            if execute:
                cls._panel.setCurrentShelf(cls._panel.getHomeShelf())
                cls.reset()
            else:
                cls._panel.set_candidate_shelf(cls._panel.getHomeShelf())

            return True

        elif button is cls._main_btns["scroll_left"]:

            shelf_btn = button.getItem()

            if shelf_btn:

                for btn in cls._shelf_btns:
                    btn.moveFromPath()

                cls._shelf_btns.insert(0, shelf_btn)
                cls.__setShelfButtons(cls._shelf_btns)

            return True

        elif button is cls._main_btns["scroll_right"]:

            shelf_btn = button.getItem()

            if shelf_btn:

                for btn in cls._shelf_btns:
                    btn.moveFromPath()

                cls._shelf_btns.append(shelf_btn)
                cls.__setShelfButtons(cls._shelf_btns, from_right=True)

            return True

        return False

    @classmethod
    def notify_mouse_hover(cls):

        if DraggedContents.is_in_favs():
            return

        refresh_needed = False

        main_btns = cls._main_btns.copy()

        if not cls._panel.get_current_shelf().get_parent():
            del main_btns["parent"]

        for btn in main_btns.itervalues():

            if btn.notify_mouse_hover():
                refresh_needed = cls.__activateButton(btn)

        if cls._hilited_btn in cls._shelf_btns:
            cls._hilited_btn.notify_mouse_hover()

        if refresh_needed:
            cls._panel.Refresh()

    @classmethod
    def notify_mouse_leave(cls):

        if cls._main_btns["parent"].isReady():
            cls._shelf_btns = []

        for btn in cls._main_btns.itervalues():
            btn.notify_mouse_leave()

        for btn in cls._shelf_btns:
            btn.notify_mouse_leave()

        if cls._hilited_btn in cls._shelf_btns:
            cls._hilited_btn.notify_mouse_leave()

        cls._hilited_btn = None
        cls._parent_shown = False

    @classmethod
    def notify_left_down(cls):

        if cls._hilited_btn:

            cls._hilited_btn.press()

            if cls._hilited_btn not in cls._shelf_btns:
                cls._panel.Refresh()

    @classmethod
    def notify_left_up(cls):

        if cls._hilited_btn in cls._shelf_btns:
            if cls._hilited_btn.release():
                cls.reset()
                return True
        elif cls._hilited_btn and cls._hilited_btn.release():
            if cls.__activateButton(cls._hilited_btn, execute=True):
                cls._panel.Refresh()
                return True

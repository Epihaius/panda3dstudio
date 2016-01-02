# DeepShelf module.

# Implements the root Home, History and Favorites shelves.

from .base import *
from .shelf_btn_container import ShelfButtonContainer
from .shelf import Shelf


class RootShelf(Shelf):

    def __init__(self, icon_name=""):

        ShelfButtonContainer.__init__(self)

        self._icon = wx.Bitmap(icon_name + ".png") if icon_name else None

        self._children = []
        self._child_proxies = []

        self._is_accessible = True
        self._password = ""

        self._proxy = weakref.proxy(self)

    def setParent(self, parent): pass

    def get_parent(self): return

    def updateAncestors(self): pass

    def get_ancestors(self):

        return []

    def get_label(self):

        return ""

    def getLabelWidth(self):

        return 0

    def getPathLabelData(self):

        return []

    def getPathButtons(self):

        return []

    def getIcon(self):

        return self._icon

    def getRootIcon(self):

        return self._icon

    def updateButton(self, btn_x, btn_width): pass

    def get_button(self): return

    def clear(self):

        del self._child_proxies[:]
        self._children = []
        self._btns = []
        self._update_selected_btn_ids()
        self._update_cut_btn_ids()
        self._btn_positions = [self._rect.GetX() + self._btn_gutter]
        self._button_type = ""

    def check_dragged_contents(self):

        dragged_contents_type = DraggedContents.get_type()

        if dragged_contents_type:
            InsertionMarker.show()
        else:
            return

        if self._proxy is self._panel.get_history_shelf():

            self._panel.SetCursor(CURSORS["no_access"])
            InsertionMarker.hide()

        elif dragged_contents_type == "shelf":

            if not self.is_accessible() or self._button_type == "tool":
                self._panel.SetCursor(CURSORS["no_access"])
                InsertionMarker.hide()
            else:
                self._panel.SetCursor(CURSORS["move"])
                InsertionMarker.set_y(43)

        elif dragged_contents_type == "tool":

            if not self.is_accessible() or self._button_type == "shelf":
                self._panel.SetCursor(CURSORS["no_access"])
                InsertionMarker.hide()
            else:
                self._panel.SetCursor(CURSORS["move"])
                InsertionMarker.set_y(37)


class HomeShelf(RootShelf):
    ##
    # def __del__(self):
    ##
    # print "HomeShelf garbage-collected."
    # pass

    def __init__(self, icon_name):

        RootShelf.__init__(self, icon_name)

        self._id = -1

    def clear(self):

        RootShelf.clear(self)

        Shelf._indices_removed = []
        Shelf._count = 0


class FavoritesShelf(RootShelf):
    ##
    # def __del__(self):
    ##
    # print "FavoritesShelf garbage-collected."
    # pass

    def __init__(self, icon_name):

        RootShelf.__init__(self, icon_name)

        self._id = -2
        self._button_type = "shelf"

    def drop_children(self, x, original_buttons, single_source=True):

        if original_buttons[0] in self._btns:

            buttons = original_buttons

        else:

            buttons = original_buttons[
                :self._max_btn_count["shelf"] - len(self._btns)]
            shelves = [btn.get_shelf() for btn in self._btns]

            for btn in buttons[:]:
                if btn.get_shelf() in shelves:
                    buttons.remove(btn)

            buttons = [btn.copy() for btn in buttons]

        if not buttons:
            return False

        btns_were_dropped = self.dropShelfButtons(x, buttons)

        if btns_were_dropped == "not":
            return False

        for i, btn in enumerate(self._btns):

            shelf_data = btn.getShelfData()

            if shelf_data["favorite"]:
                shelf_data["favorite"][1] = i
            else:
                shelf_data["favorite"] = [shelf_data["label"], i]

        return True


class HistoryShelf(RootShelf):
    ##
    # def __del__(self):
    ##
    # print "HistoryShelf garbage-collected."
    # pass

    def __init__(self, icon_name):

        RootShelf.__init__(self, icon_name)

        self._id = -3

    def addShelf(self, shelf):

        shelves = [btn.get_shelf() for btn in self._btns]

        if shelf in shelves:

            index = shelves.index(shelf)

            if index > 0:
                btn_to_move = self._btns[index]
                self.dropShelfButtons(0, [btn_to_move])

            return

        if len(self._btns) == self._max_btn_count["shelf"]:
            self.removeShelfButtons([self._btns[-1]])

        label = "<Home>" if shelf is self._panel.getHomeShelf() else shelf.get_label()
        btn = self.insertShelfButtons(0, label_data=[(label, None)])[0]
        btn.setShelf(shelf)

    def notify_left_down(self):

        if self._btn_with_mouse:
            self._btn_with_mouse.press()

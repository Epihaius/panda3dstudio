# DeepShelf module.

# Implements the shelves.

from __future__ import division
from .base import *
from .shelf_btn import ShelfButton
from .tool_btn import ToolButton
from .shelf_btn_container import ShelfButtonContainer
from .tool_btn_container import ToolButtonContainer
import hashlib


class Shelf(ShelfButtonContainer, ToolButtonContainer):

    _indices_removed = []
    _count = 0

    @classmethod
    def init(cls, panel, rect, bitmap_names):

        ShelfButtonContainer.init(panel, rect, bitmap_names["shelf_button"], 5)
        ToolButtonContainer.init(bitmap_names["tool_button"])

    def __del__(self):

        self.__class__._indices_removed.append(self._id)
        self.__class__._indices_removed.sort()
##
# for btn in self._btns:
##
# if btn.is_cut():
# self._panel.releaseCutButton(btn)

# print "Shelf", self._id, "(", self.get_label(), ") garbage-collected."

    def __init__(self, button, parent):

        ShelfButtonContainer.__init__(self)

        if self.__class__._indices_removed:
            self._id = self.__class__._indices_removed.pop(0)
        else:
            self.__class__._count += 1
            self._id = self.__class__._count

        self._button = button
        self._parent = parent
        self._ancestors = parent.get_ancestors() + [parent]
        self._children = []
        self._child_proxies = []

        self._is_accessible = True
        self._password = ""

        self._proxy = weakref.proxy(self)

        self._button.setShelf(self._proxy)
# parent.set_button_type("shelf")

    def get_object(self):

        return self

    def getProxy(self):

        return self._proxy

    def setParent(self, parent):

        self._parent = parent
# parent.set_button_type("shelf")
        self._ancestors = parent.get_ancestors() + [parent]

        for child in self._children:
            child.updateAncestors()

    def get_parent(self):

        return self._parent

    def updateAncestors(self):

        self._ancestors = []

        def getAncestor(shelf):

            parent = shelf.get_parent()

            if parent:
                getAncestor(parent)
                self._ancestors.append(parent)

        getAncestor(self._proxy)

    def get_ancestors(self):

        return self._ancestors

    def get_id(self):

        return self._id

    def get_width(self):

        return self._width

    def get_button(self):

        return self._button

    def get_label(self):

        return self._button.get_label()

    def getLabelWidth(self):

        return self._button.getLabelWidth()

    def getLabelData(self):

        return (self.get_label(), self.getLabelWidth())

    def getPathLabelData(self):

        label_data = [shelf.getLabelData() for shelf in self._ancestors[1:]]
        label_data += [self.getLabelData()]

        return label_data

    def getPathButtons(self):

        buttons = [shelf.get_button()
                   for shelf in self._ancestors[1:]] + [self._button]

        return buttons

    def getRootIcon(self):

        return self._ancestors[0].getIcon()

    def updateButton(self, btn_x, btn_width):

        self._button.setWidthScaled(btn_width)
        self._button.set_x(btn_x)

    def get_panel(self):

        return self._panel

    def getScreenPos(self):

        return self._panel.GetScreenPosition()

    def get_children(self):

        return self._child_proxies

    def drop_children(self, x, buttons, single_source=True):

        btns_were_dropped = self.dropShelfButtons(x, buttons)

        if btns_were_dropped == "not":
            return False

        if btns_were_dropped == "deeper":
            return True

        del self._child_proxies[:]
        children = self._children[:]  # keep child shelves alive
        del self._children[:]

        for shelf in children:
            self._panel.removeShelfData(shelf.get_id(), self._id)

        for btn in self._btns[::-1]:
            shelf = btn.get_shelf()
            self._child_proxies.insert(0, shelf)
            self._children.insert(0, shelf.get_object())
            self._panel.insertShelfData(shelf.get_id(), self._id, 0)

        if btns_were_dropped == "from_outside":

            shelves = [btn.get_shelf() for btn in buttons]

            if single_source:

                source_shelf = shelves[0].get_parent()
                source_shelf_id = source_shelf.get_id()
                source_shelf.removeChildren(shelves)

                for shelf in shelves:
                    self._panel.removeShelfData(
                        shelf.get_id(), source_shelf_id)

            for shelf in shelves:
                shelf.setParent(self._proxy)

        return True

    def createChildren(self, label_data):

        if not label_data:
            return []

        proxies = []

        for button in self.insertShelfButtons(len(self._btns), label_data=label_data):
            shelf = Shelf(button, self._proxy)
            proxy = shelf.getProxy()
            proxies.append(proxy)
            self._child_proxies.append(proxy)
            self._children.append(shelf)

        return proxies

    def removeChildren(self, shelves):

        buttons = []

        for shelf in shelves:

            if not shelf in self._child_proxies:
                continue

            buttons.append(shelf.get_button())
            self._child_proxies.remove(shelf)
            self._children.remove(shelf.get_object())

        self.removeShelfButtons(buttons)

    def fillChildren(self, buttons, btn_type):

        if not btn_type:
            return

        child_count = len(self._child_proxies)
        max_btn_count = self._max_btn_count[btn_type]

        if not self._child_proxies:  # something went wrong with child creation!
            return

        btns_to_left, btns_to_right = buttons

        if btn_type == "tool":

            btns_right = btns_to_right[:] if btns_to_right else []
            btn_vacancy = max_btn_count

            i = 0

            if btns_to_left:

                shelf = self._child_proxies[i]
                shelf.drop_tool_buttons(100000, btns_to_left)
                btn_vacancy = max_btn_count - len(btns_to_left)

                if not btn_vacancy:
                    i += 1
                    btn_vacancy = max_btn_count

            while btns_right:

                btns_remaining = btns_right[btn_vacancy:]
                shelf = self._child_proxies[i]
                shelf.drop_tool_buttons(100000, btns_right[:btn_vacancy])
                btns_right = btns_remaining
                i += 1
                btn_vacancy = max_btn_count

        else:

            buttons = btns_to_left + btns_to_right

            if new_btns:
                external_source_shelf = new_btns[0].get_shelf().get_parent()
                external_source_id = external_source_shelf.get_id()
                new_shelves = [btn.get_shelf() for btn in new_btns]

            i = 0

            while buttons:

                btns_remaining = buttons[max_btn_count:]
                shelf = self._child_proxies[i]
                shelf.drop_children(
                    100000, buttons[:max_btn_count], single_source=False)
                buttons = btns_remaining
                i += 1

            if new_btns:

                external_source_shelf.removeChildren(new_shelves)

                for shelf in new_shelves:
                    self._panel.removeShelfData(
                        shelf.get_id(), external_source_id)

    def has_password(self):

        return self._password != ""

    def getPassword(self):

        return self._password

    def set_access(self, accessible=True, from_save=False, password=""):

        self._panel.set_candidate_shelf(None)

        if accessible:

            if self._password:

                self._panel.notifyDialogOpen()
                answer = wx.GetPasswordFromUser("This shelf is password-protected;\n"
                                                + "please provide the correct password to\n"
                                                + "access its contents.",
                                                "Password required")

                if not answer or hashlib.sha224(answer).hexdigest() != self._password:
                    wx.MessageDialog(None,
                                     "The password entered is incorrect!\n",
                                     "Access denied",
                                     style=wx.OK | wx.CENTER | wx.ICON_EXCLAMATION).ShowModal()
                    return False

        elif from_save:

            self._password = password

        else:

            self._panel.notifyDialogOpen()
            password = wx.GetPasswordFromUser("Please enter a password if you"
                                              + " want to\nprotect the contents"
                                              + " of this shelf.",
                                              "Set password")
            self._password = hashlib.sha224(
                password).hexdigest() if password else ""

        self._is_accessible = accessible

        if not from_save:
            self._panel.setShelfDataValue(
                self._id, "contents_hidden", not accessible)
            self._panel.setShelfDataValue(self._id, "password", self._password)
            self._panel.save_shelf_data()

        if accessible:

            self.destroy_access_button()
            self._panel.restoreShelfContents(self._proxy)

        else:

            if self._button_type == "shelf":

                self.removeChildren(self.get_children()[:])

            elif self._button_type == "tool":

                if self._btn_with_mouse:
                    ToolTip.hide()
                    self._btn_with_mouse = None

                self._btns = []
                self._button_type = ""

                self._update_selected_btn_ids()
                self._update_cut_btn_ids()

            self.create_access_button()

        return True

    def is_accessible(self):

        return self._is_accessible

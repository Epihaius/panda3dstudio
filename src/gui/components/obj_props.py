from ..base import *
from ..tooltip import ToolTip
from ..menu import *
from ..dialogs import *


class ObjectPropertiesMenu:

    def __init__(self):

        self._menu = menu = Menu()
        menu.add("edit_tags", "Edit tags", self.__edit_object_tags, update=True)

        Mgr.expose("menu_obj_props", self.__get_menu)
        Mgr.accept("restore_menu_obj_props", self.__restore_menu)
        Mgr.add_app_updater("obj_props", self.__show_menu)
        Mgr.add_app_updater("obj_tags", self.__update_object_tags)

    def __restore_menu(self):

        menu = self._menu
        menu.make_submenu(False)
        menu.set_parent(None)
        menu.set_pos((0, 0))
        menu.update_initial_pos()

    def __get_menu(self):

        return "Object", self._menu

    def __show_menu(self):

        ToolTip.hide()
        self._menu.show_at_mouse_pos()

    def __edit_object_tags(self):

        Mgr.update_remotely("obj_tags")

    def __update_object_tags(self, tags):

        TagDialog(tags)

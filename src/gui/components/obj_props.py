from ..base import *
from ..tooltip import ToolTip
from ..menu import *
from ..dialog import *


class TagField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)
    _ref_node = NodePath("reference_node")

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, width, dialog=None, text_color=None, back_color=None,
                 on_key_enter=None, on_key_escape=None, allow_reject=True):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, INSET1_BORDER_GFX_DATA, width, dialog,
                                  text_color, back_color, on_key_enter=on_key_enter,
                                  on_key_escape=on_key_escape, allow_reject=allow_reject)

        self.set_image_offset(self._img_offset)
        self.get_node().reparent_to(parent.get_widget_root_node())

    def get_outer_borders(self):

        return self._field_borders


class TagPane(DialogScrollPane):

    def __init__(self, dialog, tags):

        DialogScrollPane.__init__(self, dialog, "tag_pane", "vertical", (500, 300), "both")

        self._tags = tags
        self._fields = []
        self._tag_key_fields = []
        self._tag_val_fields = []
        self._active_key_index = 0

        self._menu = menu = Menu()
        command = lambda: self.__remove_tag(self._active_key_index)
        menu.add("remove_tag", "Remove tag", command, update=True)

        for key, value in tags.items():
            self.add_tag(key, value, update=False)

    def _copy_widget_images(self, pane_image): 

        root_node = self.get_widget_root_node()

        for field in self._fields:
            x, y = field.get_pos(ref_node=root_node)
            offset_x, offset_y = field.get_image_offset()
            pane_image.copy_sub_image(field.get_image(), x + offset_x, y + offset_y, 0, 0)

    def destroy(self):

        DialogScrollPane.destroy(self)

        self._fields = []
        self._tag_key_fields = []
        self._tag_val_fields = []
        self._menu.destroy()
        self._menu = None

    def get_tags(self):

        return self._tags

    def __get_tag_key_parser(self, index):

        def on_cancel():

            self._tag_key_fields[index].on_left_down()

        def show_warning(warning_id, command=None):

            task = lambda: Mgr.do("reject_field_input")
            task_id = "reject_field_input"
            PendingTasks.add(task, task_id)

            if warning_id == "empty_key":
                MessageDialog(title="Empty key",
                              message="Empty keys are not allowed." \
                              + "\n\nDo you want to remove the tag?",
                              choices="okcancel", on_yes=command, on_cancel=on_cancel,
                              icon_id="icon_exclamation")
            elif warning_id == "dupe_key":
                MessageDialog(title="Duplicate key",
                              message="The entered key already exists.",
                              choices="ok", on_yes=on_cancel, on_cancel=on_cancel,
                              icon_id="icon_exclamation")

        def parse_key(key):

            if not key:
                command = lambda: self.__remove_tag(index)
                show_warning("empty_key", command)
                return

            field = self._tag_key_fields[index]
            old_key = field.get_text("tag_key")

            if key in self._tags:

                if key != old_key:
                    show_warning("dupe_key")

            else:

                if old_key in self._tags:
                    del self._tags[old_key]

                field.allow_reject()

                return key

        return parse_key

    def __get_tag_key_handler(self, index):

        def set_tag_key(field_value_id, key):

            value = self._tag_val_fields[index].get_text("tag_val")
            self._tags[key] = value

        return set_tag_key

    def __get_tag_value_handler(self, index):

        def set_tag_value(field_value_id, value):

            key = self._tag_key_fields[index].get_text("tag_key")
            self._tags[key] = value

        return set_tag_value

    def add_tag(self, key=None, value=None, update=True):

        index = len(self._tag_key_fields)
        tag_sizer = Sizer("horizontal")
        self.get_sizer().add(tag_sizer, expand=True)
        allow_reject = key is not None
        dialog = self.get_dialog()
        get_popup_handler = lambda index: lambda: self.__on_popup(index)
        field = key_field = TagField(self, 100, dialog, allow_reject=allow_reject)
        field.add_value("tag_key", "string", handler=self.__get_tag_key_handler(index))
        field.set_input_parser("tag_key", self.__get_tag_key_parser(index))
        field.set_popup_menu(self._menu, manage=False)
        field.set_popup_handler(get_popup_handler(index))

        if key is not None:
            field.set_text("tag_key", key)

        field.show_value("tag_key")
        field.set_scissor_effect(self._scissor_effect)
        self._tag_key_fields.append(field)
        self._fields.append(field)
        borders = (10, 5, 0, 5)
        tag_sizer.add(field, proportion=1., borders=borders)
        field = TagField(self, 100, dialog)
        field.add_value("tag_val", "string", handler=self.__get_tag_value_handler(index))

        if value is not None:
            field.set_text("tag_val", value)

        field.show_value("tag_val")
        field.set_scissor_effect(self._scissor_effect)
        self._tag_val_fields.append(field)
        self._fields.append(field)
        borders = (5, 10, 0, 5)
        tag_sizer.add(field, proportion=1., borders=borders)

        if update:
            self.update_layout()
            h_virt = self.get_sizer().get_virtual_size()[1]
            self.get_scrollthumb().set_offset(h_virt)

        if key is None:
            key_field.on_left_down()

    def __remove_tag(self, index):

        key_field = self._tag_key_fields[index]
        val_field = self._tag_val_fields[index]
        self._fields.remove(key_field)
        self._fields.remove(val_field)

        if index == len(self._tag_key_fields) - 1:
            del self._tag_key_fields[index]
            del self._tag_val_fields[index]
        else:
            self._tag_key_fields[index] = None
            self._tag_val_fields[index] = None

        key = key_field.get_text("tag_key")

        if key in self._tags:
            del self._tags[key]

        sizer_item = key_field.get_sizer_item().get_sizer().get_sizer_item()

        def task():

            self.get_sizer().remove_item(sizer_item, destroy=True)
            self.update_layout()

        task_id = "remove_tag"
        PendingTasks.add(task, task_id)

    def clear_tags(self):

        if not self._tags:
            return

        self._tag_key_fields = []
        self._tag_val_fields = []
        self._fields = []
        self._tags = {}
        self.get_sizer().clear()
        self.update_layout()

    def __on_popup(self, index):

        self._active_key_index = index


class TagDialog(Dialog):

    def __init__(self, tags, obj_id):

        title = "Edit object tags"
        width = Skin["options"]["dialog_standard_button_width"]

        def on_yes():

            Mgr.update_remotely("obj_tags", obj_id, self._tag_pane.get_tags())

        Dialog.__init__(self, None, title, choices="okcancel", on_yes=on_yes)

        client_sizer = self.get_client_sizer()
        subsizer = Sizer("horizontal")
        borders = (50, 50, 0, 20)
        client_sizer.add(subsizer, expand=True, borders=borders)
        inset = DialogInset(self)
        subsizer.add(inset, proportion=1.)
        inset_sizer = inset.get_client_sizer()
        text = DialogText(self, "Key")
        borders = (10, 10, 10, 10)
        inset_sizer.add(text, alignment="center_h", borders=borders)
        inset = DialogInset(self)
        subsizer.add(inset, proportion=1.)
        inset_sizer = inset.get_client_sizer()
        text = DialogText(self, "Value")
        inset_sizer.add(text, alignment="center_h", borders=borders)

        self._tag_pane = pane = TagPane(self, tags)
        frame = pane.get_frame()
        borders = (50, 50, 20, 0)
        client_sizer.add(frame, proportion=1., expand=True, borders=borders)
        btn_sizer = Sizer("horizontal")
        borders = (50, 50, 20, 0)
        client_sizer.add(btn_sizer, expand=True, borders=borders)
        text = "Clear"
        tooltip_text = "Remove all tags"
        btn = DialogButton(self, text, "", tooltip_text, pane.clear_tags)
        btn_sizer.add((0, 0), proportion=.5)
        btn_sizer.add(btn, proportion=1.)
        text = "Add"
        tooltip_text = "Add new tag"
        btn = DialogButton(self, text, "", tooltip_text, pane.add_tag)
        btn_sizer.add((0, 0), proportion=.5)
        btn_sizer.add(btn, proportion=1.)
        btn_sizer.add((0, 0), proportion=.5)

        x, y, w, h = TextureAtlas["regions"]["dialog_inset2_border_right"]
        width = frame.get_scrollbar().get_size()[0] - w
        subsizer.add((width, 0))

        text = DialogText(self, "To remove a tag, input an empty string for the key, "
                          "or right-click the key field and choose\n'Remove tag' "
                          "from the context menu.")
        client_sizer.add(text, borders=borders)

        self.finalize()

    def update_widget_positions(self):

        self._tag_pane.update_quad_pos()
        x, y = self._tag_pane.get_pos(from_root=True)
        TagField.set_ref_node_pos((-x, 0, y))


class ObjectPropertiesMenu(object):

    def __init__(self):

        self._menu = menu = Menu()
        menu.add("edit_tags", "Edit tags", self.__edit_object_tags, update=True)
        self._obj_id = None

        Mgr.add_app_updater("obj_props_access", self.__show_menu)
        Mgr.add_app_updater("obj_tags", self.__update_object_tags)

    def __show_menu(self, obj_id):

        self._obj_id = obj_id
        ToolTip.hide()
        self._menu.show_at_mouse_pos()

    def __edit_object_tags(self):

        Mgr.update_remotely("obj_tags", self._obj_id)

    def __update_object_tags(self, tags):

        TagDialog(tags, self._obj_id)

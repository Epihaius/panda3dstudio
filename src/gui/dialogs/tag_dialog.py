from ..base import *
from ..menu import *
from ..dialog import *
from .message_dialog import MessageDialog


class TagField(DialogInputField):

    _ref_node = NodePath("reference_node")

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, width, font=None, text_color=None, back_color=None):

        DialogInputField.__init__(self, parent, width, font, text_color, back_color)

        self.node.reparent_to(parent.widget_root_node)


class TagPane(DialogScrollPane):

    def __init__(self, parent, tags):

        frame_client_size = (
            Skin.options["tag_dialog_scrollpane_width"],
            Skin.options["tag_dialog_scrollpane_height"]
        )

        DialogScrollPane.__init__(self, parent, "tag_pane", "vertical", frame_client_size)

        self._tags = tags.copy()
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

        root_node = self.widget_root_node

        for field in self._fields:
            x, y = field.get_pos(ref_node=root_node)
            offset_x, offset_y = field.image_offset
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

    def __parse_tag_key(self, index, key):

        def on_cancel():

            self._tag_key_fields[index].on_left_down()
            self._tag_key_fields[index]._on_left_up()

        def show_warning(warning_id, command=None):

            task = lambda: Mgr.do("reject_field_input")
            task_id = "reject_field_input"
            PendingTasks.add(task, task_id)

            if warning_id == "empty_key":
                MessageDialog(title="Empty key",
                              message="Empty keys are not allowed."
                                      "\n\nDo you want to remove the tag?",
                              choices="okcancel", on_yes=command, on_cancel=on_cancel,
                              icon_id="icon_exclamation")
            elif warning_id == "dupe_key":
                MessageDialog(title="Duplicate key",
                              message="The entered key already exists.",
                              choices="ok", on_yes=on_cancel, on_cancel=on_cancel,
                              icon_id="icon_exclamation")

        if not key:
            command = lambda: self.__remove_tag(index)
            show_warning("empty_key", command)
            return

        field = self._tag_key_fields[index]
        old_key = field.get_value()

        if key in self._tags:

            if key != old_key:
                show_warning("dupe_key")

        else:

            if old_key in self._tags:
                del self._tags[old_key]

            field.allow_reject()

            return key

    def __set_tag_key(self, index, key):

        value = self._tag_val_fields[index].get_value()
        self._tags[key] = value

    def __set_tag_value(self, index, value):

        key = self._tag_key_fields[index].get_value()
        self._tags[key] = value

    def add_tag(self, key=None, value=None, update=True):

        index = len(self._tag_key_fields)
        tag_sizer = Sizer("horizontal")
        self.sizer.add(tag_sizer, (1., 0.))
        allow_reject = key is not None
        field_width = Skin.options["tag_dialog_field_min_width"]
        field = key_field = TagField(self, field_width)
        field.value_id = "tag_key"
        field.value_type = "string"
        field.set_value_handler(lambda _1, key, _2: self.__set_tag_key(index, key))
        field.set_input_parser(lambda key: self.__parse_tag_key(index, key))
        field.allow_reject(allow_reject)
        field.set_popup_menu(self._menu, manage=False)
        field.set_popup_handler(lambda: self.__on_popup(index))

        if key is not None:
            field.set_value(key)

        field.set_scissor_effect(self.scissor_effect)
        self._tag_key_fields.append(field)
        self._fields.append(field)
        borders = Skin.layout.borders["tag_dialog_key_field"]
        tag_sizer.add(field, proportions=(1., 0.), borders=borders)

        field = TagField(self, field_width)
        field.value_id = "tag_val"
        field.value_type = "string"
        field.set_value_handler(lambda _1, value, _2: self.__set_tag_value(index, value))

        if value is None:
            field.set_value("")
        else:
            field.set_value(value)

        field.set_scissor_effect(self.scissor_effect)
        self._tag_val_fields.append(field)
        self._fields.append(field)
        borders = Skin.layout.borders["tag_dialog_value_field"]
        tag_sizer.add(field, proportions=(1., 0.), borders=borders)

        if update:
            self.update_layout()
            h_virt = self.virtual_size[1]
            self.scrollthumb.set_offset(h_virt)

        if key is None:
            key_field.on_left_down()
            key_field._on_left_up()

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

        key = key_field.get_value()

        if key in self._tags:
            del self._tags[key]

        sizer_cell = key_field.sizer_cell.sizer.sizer_cell

        def task():

            self.sizer.remove_cell(sizer_cell, destroy=True)
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
        self.sizer.clear(destroy_cells=True)
        self.update_layout()

    def __on_popup(self, index):

        self._active_key_index = index


class TagDialog(Dialog):

    def __init__(self, tags):

        def on_yes():

            Mgr.update_remotely("obj_tags", self._tag_pane.get_tags())

        Dialog.__init__(self, "", choices="okcancel", on_yes=on_yes)

        widgets = Skin.layout.create(self, "tag")
        btns = widgets["buttons"]

        inset = DialogInset(self)
        key_cell = widgets["placeholders"]["key"]
        key_cell.object = inset
        inset_sizer = inset.sizer
        text = DialogText(inset, "Key")
        inset_sizer.add(text, alignments=("center", "center"))

        inset = DialogInset(self)
        value_cell = widgets["placeholders"]["value"]
        value_cell.object = inset
        inset_sizer = inset.sizer
        text = DialogText(inset, "Value")
        inset_sizer.add(text, alignments=("center", "center"))

        self._tag_pane = pane = TagPane(self, tags)
        frame = pane.frame
        pane_cell = widgets["placeholders"]["pane"]
        pane_cell.object = frame

        btn = btns["clear"]
        btn.command = pane.clear_tags

        btn = btns["add"]
        btn.command = pane.add_tag

        gfx_id = Skin.atlas.gfx_ids["inset"]["dialog"][1][2]
        w = Skin.atlas.regions[gfx_id][2]
        width = frame.get_scrollbar().get_size()[0] - w
        value_cell.sizer.add((width, 0))

        self.finalize()

    def update_widget_positions(self):

        self._tag_pane.update_quad_pos()
        x, y = self._tag_pane.get_pos(net=True)
        TagField.set_ref_node_pos((-x, 0, y))

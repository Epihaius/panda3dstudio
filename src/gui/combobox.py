from .base import *
from .button import Button
from .field import InputField
from .menu import Menu


class ComboBox(Button):

    _ref_node = NodePath("combobox_ref_node")

    def __init__(self, parent, field_width, gfx_data, text="", icon_id="", tooltip_text="",
                 editable=False):

        Button.__init__(self, parent, gfx_data, tooltip_text=tooltip_text, command=self.__show_menu)

        self.set_widget_type("combobox")
        self._field_text = text
        self._tooltip_text = tooltip_text

        self._items = {}
        self._item_ids = []
        self._item_texts = {}
        self._persistent_items = []
        self._selected_item_id = None
        self._selection_handlers = {}

        self._is_field_active = False
        self._field_back_img = None
        self._field_tint = Skin["colors"]["combobox_field_tint_default"]

        self._input_field = None

        if text:
            skin_text = Skin["text"]["combobox"]
            font = skin_text["font"]
            color = skin_text["color"]
            self._field_label = font.create_image(text, color)
        else:
            self._field_label = None

        if icon_id:
            x, y, w, h = TextureAtlas["regions"][icon_id]
            img = PNMImage(w, h, 4)
            img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
            self._combo_icon = img
            self._combo_icon_disabled = icon_disabled = PNMImage(img)
            icon_disabled.make_grayscale()
            icon_disabled -= LColorf(0., 0., 0., .25)
            icon_disabled.make_rgb()
        else:
            self._combo_icon = self._combo_icon_disabled = None

        self._popup_menu = Menu(on_hide=self.__on_hide)
        l, r, b, t = self.get_inner_borders()
        w, h = self.get_min_size()
        w = field_width + l + r
        size = (w, h)
        self.set_size(size, is_min=True)

        if editable:
            sizer = Sizer("horizontal")
            sizer.set_default_size(size)
            self.set_sizer(sizer)

    def destroy(self):

        Button.destroy(self)

        if self._selected_item_id not in self._persistent_items:
            self._items[self._selected_item_id].destroy()

        self._input_field = None
        self._items.clear()
        self._selection_handlers.clear()
        self._popup_menu.destroy()
        self._popup_menu = None

    def __on_hide(self):

        if self.is_active():
            self.set_active(False)
            self.on_leave(force=True)

    def __show_menu(self):

        if len(self._items) < 2:
            return

        self.set_active()
        x, y = self.get_pos(ref_node=self._ref_node)
        offset_x, offset_y = self.get_menu_offset("bottom")
        pos = (x + offset_x, y + offset_y)
        offset_x, offset_y = self.get_menu_offset("top")
        w, h = self._popup_menu.get_size()
        alt_pos = (x + offset_x, y + offset_y - h)
        self._popup_menu.show(pos, alt_pos)

    def __on_select(self, item_id):

        if self._selected_item_id == item_id:
            return

        update = False

        if self._selected_item_id is not None and self._selected_item_id not in self._persistent_items:
            index = self._item_ids.index(self._selected_item_id)
            selected_item = self._items[self._selected_item_id]
            self._popup_menu.add_item(selected_item, index)
            update = True

        self._selected_item_id = item_id
        self.set_text(self._item_texts[item_id])

        if self._selected_item_id not in self._persistent_items:
            self._popup_menu.remove(self._selected_item_id)
            update = True

        if update:
            self._popup_menu.update()

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = Button.set_size(self, size, includes_borders, is_min)

        if self._input_field:
            l, r, b, t = self.get_inner_borders()
            w = width - l - r
            size = (w, height)
            self._input_field.set_size(size, includes_borders, is_min)

        return width, height

    def has_icon(self):

        return self._combo_icon is not None

    def set_field_back_image(self, image):

        self._field_back_img = image

    def __get_image(self, state=None, draw_field=True):

        width, height = self.get_size()
        image = PNMImage(width, height, 4)

        if draw_field:

            field_back_img = self._field_back_img * self._field_tint

            if self._field_label:
                x, y = self.get_field_label_offset()
                field_back_img.blend_sub_image(self._field_label, x, y, 0, 0)

            x, y = self.get_field_offset()
            image.blend_sub_image(field_back_img, x, y, 0, 0)

        img = Button.get_image(self, state, composed=False)
        image.blend_sub_image(img, 0, 0, 0, 0)

        if self._combo_icon:
            x, y = self.get_icon_offset()
            image.blend_sub_image(self._combo_icon, x, y, 0, 0)

        return image

    def get_image(self, state=None, composed=False):

        field = self._input_field

        if not field or field.is_hidden():
            return self.__get_image(state)

        width, height = self.get_size()
        image = PNMImage(width, height, 4)
        field_img = field.get_image()

        if field_img:
            x, y = self.get_field_offset()
            image.copy_sub_image(field_img, x, y, 0, 0)

        img = self.__get_image(state, draw_field=False)
        image.blend_sub_image(img, 0, 0, 0, 0)

        return image

    def add_item(self, item_id, item_text, item_command=None, index=None,
                 persistent=False, update=False):

        item = self._popup_menu.add(item_id, item_text, item_command, index=index)
        self._items[item_id] = item
        self._selection_handlers[item_id] = lambda: self.__on_select(item_id)
        self._item_ids.append(item_id)
        self._item_texts[item_id] = item_text

        if persistent:
            self._persistent_items.append(item_id)

        if len(self._items) == 1:

            if not persistent:
                self._popup_menu.remove(item_id)

            self._selected_item_id = item_id
            self.set_text(item_text)

        if update:
            self._popup_menu.update()

    def remove_item(self, item_id):

        if item_id not in self._item_ids:
            return

        item = self._items[item_id]
        del self._items[item_id]
        del self._item_texts[item_id]
        del self._selection_handlers[item_id]
        index = self._item_ids.index(item_id)
        size = len(self._item_ids)
        self._item_ids.remove(item_id)

        if item_id in self._persistent_items or self._selected_item_id != item_id:
            self._popup_menu.remove(item_id, update=True, destroy=True)
        else:
            item.destroy()

        if self._selected_item_id == item_id:

            self._selected_item_id = None

            if index == size - 1:
                index -= 1

            if index >= 0:
                self.select_item(self._item_ids[index])
            else:
                self.set_text("")

        if item_id in self._persistent_items:
            self._persistent_items.remove(item_id)

    def update_popup_menu(self):

        self._popup_menu.update()

    def clear(self):

        self._popup_menu.destroy()
        self._popup_menu = Menu(on_hide=self.__on_hide)
        self._items = {}
        self._item_ids = []
        self._item_texts = {}
        self._persistent_items = []
        self._selected_item_id = None
        self._selection_handlers = {}
        self.set_text("")

    def __card_update_task(self):

        if self.is_hidden():
            return

        image = self.get_image(composed=False)

        if not image:
            return

        parent = self.get_parent()

        if not parent:
            return

        x, y = self.get_pos()
        w, h = self.get_size()
        img = PNMImage(w, h, 4)
        parent_img = parent.get_image(composed=False)

        if parent_img:
            img.copy_sub_image(parent_img, 0, 0, x, y, w, h)

        img.blend_sub_image(image, 0, 0, 0, 0)
        self.get_card().copy_sub_image(self, img, w, h)

    def __update_card_image(self):

        task = self.__card_update_task

        if self.is_card_update_delayed():
            task_id = "update_card_image"
            PendingTasks.add(task, task_id, sort=1, id_prefix=self.get_widget_id(),
                             batch_id="widget_card_update")
        else:
            task()

    def set_field_tint(self, tint=None):

        new_tint = tint if tint else Skin["colors"]["combobox_field_tint_default"]

        if self._field_tint == new_tint:
            return False

        self._field_tint = new_tint
        self.__update_card_image()

        return True

    def select_none(self):

        if self._selected_item_id is not None and self._selected_item_id not in self._persistent_items:
            index = self._item_ids.index(self._selected_item_id)
            selected_item = self._items[self._selected_item_id]
            self._popup_menu.add_item(selected_item, index, update=True)

        self._selected_item_id = None
        self.set_text("")

    def select_item(self, item_id):

        if item_id not in self._item_ids:
            return

        self._selection_handlers[item_id]()

    def get_selected_item(self):

        return self._selected_item_id

    def get_item_ids(self):

        return self._item_ids

    def set_text(self, text):

        if self._field_text == text:
            return False

        self._field_text = text
        self.set_tooltip_text(self._tooltip_text + (": " + text if text else ""))

        if text:
            skin_text = Skin["text"]["combobox"]
            font = skin_text["font"]
            color = skin_text["color"]
            self._field_label = font.create_image(text, color)
        else:
            self._field_label = None

        self.__update_card_image()

        return True

    def set_item_text(self, item_id, text):

        if item_id not in self._item_ids:
            return

        self._item_texts[item_id] = text
        self._popup_menu.set_item_text(item_id, text, update=True)
 
        if self._selected_item_id == item_id:
            item = self._items[self._selected_item_id]
            item.set_text(text)
            self.set_text(text)

    def get_item_text(self, item_id):

        if item_id not in self._item_ids:
            return

        return self._item_texts[item_id]

    def set_item_index(self, item_id, index):

        if item_id not in self._item_ids:
            return

        self._item_ids.remove(item_id)
        self._item_ids.insert(index, item_id)
        item = self._items[item_id]
        self._popup_menu.remove(item_id)
        self._popup_menu.add_item(item, index, update=True)

    def set_input_field(self, input_field):

        self._input_field = input_field
        self.get_sizer().add(input_field)

    def get_input_field(self):

        return self._input_field

    def show_input_field(self, show=True):

        field = self._input_field

        if not field or field.is_hidden() != show:
            return False

        r = field.show() if show else field.hide()
        self.__update_card_image()

        return r

    def is_input_field_hidden(self):

        field = self._input_field

        if not field or field.is_hidden():
            return True

        return False

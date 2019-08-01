from .base import *
from .menu import Menu


class TextControl:

    _shown_caret = None
    _clipboard_text = ""

    @classmethod
    def __set_clipboard_text(cls, text):

        cls._clipboard_text = text

    @classmethod
    def __get_clipboard_text(cls):

        return cls._clipboard_text

    @classmethod
    def __blink_caret(cls, task):

        caret = cls._shown_caret

        if not caret:
            return task.again

        if caret.is_hidden():
            caret.show()
        else:
            caret.hide()

        return task.again

    @classmethod
    def init(cls):

        delay = Skin["options"]["inputfield_caret_blink_delay"]
        Mgr.add_task(delay, cls.__blink_caret, "blink_input_caret")

    def __init__(self, field, font, color, cull_bin=("gui", 3)):

        self._field = field
        self._font = font if font else Skin["text"]["input"]["font"]
        self._color = color
        self._text = ""
        self._label = None
        self._label_offset = 0
        self._char_positions = []
        self._char_pos_stale = False
        self._selection_anchor = 0
        cm = CardMaker("text_control")
        cm.set_frame(0, 1., -1., 0)
        w, h = field.get_size()
        self._root = root = Mgr.get("gui_root").attach_new_node("text_control_root")
        self._quad = quad = root.attach_new_node(cm.generate())
        quad.set_scale(w, 1., h)
        bin_name, bin_sort = cull_bin
        quad.set_bin(bin_name, bin_sort)
        self._tex = tex = Texture("text_control")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        quad.set_texture(tex)
        root.hide()
        self._image = PNMImage(w, h, 4)
        cm.set_name("input_caret")
        w_c = Skin["options"]["inputfield_caret_width"]
        h_c = Skin["options"]["inputfield_caret_height"]
        self._caret_offset_node = offset_node = root.attach_new_node("offset_node")
        margin = Skin["options"]["inputfield_margin"]
        y = (h - h_c) // 2
        l = -w_c // 2
        r = l + w_c
        offset_node.set_pos(margin, 0., -y)
        offset_node.set_texture_off()
        cm.set_frame(l, r, -h_c, 0)
        self._caret = caret = offset_node.attach_new_node(cm.generate())
        caret.set_bin(bin_name, bin_sort + 1)
        self._caret_tex = tex = Texture("caret_tex")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        caret.set_texture(tex)
        self._caret_pos = 0
        self.__update_image()
        self.__update_caret()

    def destroy(self):

        self._field = None
        self._root.remove_node()
        self._root = None
        self._quad = None
        self._caret = None
        self._caret_offset_node = None

    def set_size(self, size):

        w, h = size
        self._quad.set_scale(w, 1., h)
        self._field.update_images()
        self.__update_image()

    def __update_caret(self):

        w, h = self._field.get_size()
        margin = Skin["options"]["inputfield_margin"]
        w -= margin
        x = self._font.calc_width(self._text[:self._caret_pos])
        caret = self._caret
        caret.set_x(x)
        w_c = Skin["options"]["inputfield_caret_width"]
        h_c = Skin["options"]["inputfield_caret_height"]
        x, y, z = caret.get_pos(self._root)
        x = int(x) - w_c // 2
        y = int(-z)
        img1 = PNMImage(w_c, h_c)
        img1.fill(1., 1., 1.)
        img2 = PNMImage(img1)
        img2.copy_sub_image(self._image, 0, 0, x, y, w_c, h_c)
        # invert the image colors
        img1 -= img2
        self._caret_tex.load(img1)
        caret.show()

    def set_scissor_effect(self, effect):

        if effect:
            self._root.set_effect(effect)

    def set_pos(self, pos):

        x, y = pos
        self._root.set_pos(x, 0, -y)

    def clear(self):

        self._text = ""
        self._label = None
        self._label_offset = 0
        self._caret_pos = 0
        self._caret_offset_node.set_x(Skin["options"]["inputfield_margin"])
        self._char_positions = []
        self._char_pos_stale = False
        self._selection_anchor = 0
        self.__scroll()
        self.__update_image()
        self.__update_caret()

    def set_color(self, color):

        self._color = color

    def get_color(self):

        return self._color

    def __scroll(self):

        w, h = self._field.get_size()
        margin = Skin["options"]["inputfield_margin"]
        w_ = w - margin * 2
        w_t = self._font.calc_width(self._text[:self._caret_pos])
        label_offset = self._label_offset

        if label_offset <= w_t <= label_offset + w_:
            return False

        if label_offset > w_t:
            label_offset = w_t
        else:
            label_offset = max(0, w_t - w_)

        self._label_offset = label_offset
        self._caret_offset_node.set_x(margin - label_offset)

        return True

    def set_text(self, text):

        self._text = text
        self._selection_anchor = self._caret_pos = len(text)
        self._caret_offset_node.set_x(Skin["options"]["inputfield_margin"])
        self._char_pos_stale = True
        self._label_offset = 0
        self.create_label()
        self.__scroll()
        self.__update_image()
        self.__update_caret()

    def write(self, text):

        start_pos = min(self._caret_pos, self._selection_anchor)
        end_pos = max(self._caret_pos, self._selection_anchor)
        self._caret_pos = start_pos
        self.__scroll()
        start = self._text[:start_pos]
        end = self._text[end_pos:]
        self._text = "".join((start, text, end))
        self._selection_anchor = self._caret_pos = start_pos + len(text)
        self._char_pos_stale = True
        self.create_label()
        self.__scroll()
        self.__update_image()
        self.__update_caret()

    def delete(self):

        caret_pos = start_pos = min(self._caret_pos, self._selection_anchor)
        end_pos = max(start_pos + 1, self._caret_pos, self._selection_anchor)
        start = self._text[:start_pos]
        end = self._text[end_pos:]
        text = "".join((start, end))

        if self._text != text:
            self._text = text
            self._selection_anchor = self._caret_pos = caret_pos
            self._char_pos_stale = True
            self.create_label()
            self.__update_image()
            self.__update_caret()

    def backspace(self):

        update = False

        if self._caret_pos != self._selection_anchor:

            caret_pos = start_pos = min(self._caret_pos, self._selection_anchor)
            end_pos = max(start_pos + 1, self._caret_pos, self._selection_anchor)
            start = self._text[:start_pos]
            end = self._text[end_pos:]
            update = True

        else:

            caret_pos = max(0, self._caret_pos - 1)

            if self._caret_pos != caret_pos:
                start = self._text[:caret_pos]
                end = self._text[self._caret_pos:]
                update = True

        if update:
            self._text = "".join((start, end))
            self._selection_anchor = self._caret_pos = caret_pos
            self._char_pos_stale = True
            self.create_label()
            self.__scroll()
            self.__update_image()
            self.__update_caret()

    def __get_char_positions(self):

        if self._char_pos_stale:

            char_positions = []
            font = self._font
            text = self._text

            for i in range(len(text) + 1):
                char_positions.append(font.calc_width(text[:i]))

            self._char_positions = char_positions
            self._char_pos_stale = False

        return self._char_positions[:]

    def move_caret(self, amount=0, is_offset=True, select=False):

        if not self._text:
            return

        c_pos = self._caret_pos
        sel_anchor = self._selection_anchor

        if is_offset:

            offset = amount

        else:

            char_positions = self.__get_char_positions()
            right_edge = char_positions[-1]
            pixels = amount - self._caret_offset_node.get_x()

            if pixels <= 0:
                pos = 0
            elif pixels >= right_edge:
                pos = len(char_positions) - 1
            else:
                char_positions.append(pixels)
                char_positions.sort()
                index = char_positions.index(pixels)
                pos_left = char_positions[index - 1]
                pos_right = char_positions[index + 1]
                pos = index - 1 if pixels < (pos_left + pos_right) / 2 else index

            offset = pos - c_pos

        if offset:

            caret_pos = min(len(self._text), max(0, c_pos + offset))

            if not select:
                if is_offset and self._selection_anchor != c_pos:
                    if offset < 0:
                        caret_pos = min(self._selection_anchor, c_pos)
                    else:
                        caret_pos = max(self._selection_anchor, c_pos)

        else:

            caret_pos = c_pos

        if not select:
            self._selection_anchor = caret_pos

        caret_moved = c_pos != caret_pos
        sel_range_change = caret_moved or self._selection_anchor != sel_anchor
        sel_still_empty = caret_pos - self._selection_anchor == c_pos - sel_anchor == 0
        selection_change = sel_range_change and not sel_still_empty
        self._caret_pos = caret_pos

        if selection_change:

            self.create_label()

            if not caret_moved:
                self.__update_image()

        if caret_moved:

            if self.__scroll() or selection_change:
                self.__update_image()

            self.__update_caret()

    def move_caret_to_start(self, select=False):

        self.move_caret(-self._caret_pos, select=select)

    def move_caret_to_end(self, select=False):

        self.move_caret(len(self._text) - self._caret_pos, select=select)

    def select_all(self):

        if not self._text:
            return

        caret_pos = len(self._text)

        if self._caret_pos != caret_pos or self._selection_anchor != 0:

            self._caret_pos = caret_pos
            self._selection_anchor = 0

            if self._caret_pos > 0:
                self.create_label()
                self.__scroll()
                self.__update_image()
                self.__update_caret()

    def get_text(self):

        return self._text

    def get_selected_text(self):

        start_pos = min(self._caret_pos, self._selection_anchor)
        end_pos = max(start_pos + 1, self._caret_pos, self._selection_anchor)

        return self._text[start_pos:end_pos]

    def copy_text(self):

        if USING_TK:
            r = Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(self.get_selected_text())
            r.update()
            r.destroy()
        else:
            self.__set_clipboard_text(self.get_selected_text())

    def cut_text(self):

        self.copy_text()
        self.delete()

    def paste_text(self):

        if USING_TK:

            r = Tk()
            r.withdraw()
            r.update()

            try:
                text = r.selection_get(selection="CLIPBOARD")
            except:
                r.destroy()
                return

            r.destroy()

        else:

            text = self.__get_clipboard_text()

        if text and type(text) == str:
            text = text.replace("\n", "")
            self.write(text)

    def __update_image(self):

        w, h = self._field.get_size()
        image = PNMImage(w, h, 4)
        r, g, b, a = Skin["colors"]["inputfield_background"]
        image.fill(r, g, b)
        image.alpha_fill(a)
        label = self._label

        if label:
            w_l, h_l = label.get_x_size(), label.get_y_size()
            x = margin = Skin["options"]["inputfield_margin"]
            y = (h - h_l) // 2
            w_ = w - margin * 2
            image.blend_sub_image(label, x, y, self._label_offset, 0, w_, h_l)

        img_offset_x, img_offset_y = self._field.get_image_offset()
        image.blend_sub_image(self._field.get_border_image(), img_offset_x, img_offset_y, 0, 0)
        self._image = image
        self._tex.load(image)

    def create_label(self, text=None):

        txt = self._text if text is None else text

        if txt:
            label = self._font.create_image(txt, self._color)
        else:
            label = None

        if text is None:

            self._label = label

            if self._caret_pos - self._selection_anchor:
                start_pos = min(self._caret_pos, self._selection_anchor)
                end_pos = max(self._caret_pos, self._selection_anchor)
                x = self._font.calc_width(self._text[:start_pos])
                txt = self._text[start_pos:end_pos]
                color_fg = Skin["text"]["input_selection"]["color"]
                color_bg = Skin["colors"]["input_selection_background"]
                label_sel = self._font.create_image(txt, color_fg, color_bg)
                label.copy_sub_image(label_sel, x, 0, 0, 0)

        return label

    def get_label(self):

        return self._font.create_image(self._text, self._color)

    def hide(self):

        self._root.hide()
        TextControl._shown_caret = None
        self.move_caret_to_start()

    def show(self, pos):

        self.select_all()
        x, y = pos
        self._root.set_pos(x, 0, -y)
        self._root.show()
        TextControl._shown_caret = self._caret


class SliderControl:

    _mark = None
    _font = None
    _default_text_color = None
    _color = None

    @classmethod
    def init(cls):

        x, y, w, h = TextureAtlas["regions"]["slider_mark"]
        cls._mark = img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        cls._font = Skin["text"]["slider"]["font"]
        cls._default_text_color = Skin["text"]["slider"]["color"]
        cls._color = Skin["colors"]["slider"]

    def __init__(self, field, value_range=(0., 1.), value_type="float", cull_bin=("gui", 3)):

        self._field = field
        self._text_color = self._default_text_color
        self._range = value_range
        self._value = value_range[0]
        self._value_type = value_type
        cm = CardMaker("slider")
        cm.set_frame(0, 1., -1., 0)
        w, h = field.get_size()
        self._root = root = Mgr.get("gui_root").attach_new_node("slider_root")
        self._quad = quad = root.attach_new_node(cm.generate())
        quad.set_scale(w, 1., h)
        bin_name, bin_sort = cull_bin
        quad.set_bin(bin_name, bin_sort)
        self._tex = tex = Texture("slider")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        quad.set_texture(tex)
        root.hide()
        self._image = None
        self.__update_image()

    def destroy(self):

        self._field = None
        self._root.remove_node()
        self._root = None
        self._quad = None

    def set_size(self, size):

        w, h = size
        self._quad.set_scale(w, 1., h)
        self.__update_image()

    def set_scissor_effect(self, effect):

        if effect:
            self._root.set_effect(effect)

    def set_pos(self, pos):

        x, y = pos
        self._root.set_pos(x, 0, -y)

    def clear(self):

        self._value = self._range[0]
        self.__update_image()

    def set_text_color(self, color=None):

        self._text_color = self._default_text_color if color is None else color

    def get_text_color(self):

        return self._text_color

    def update_value(self, slide_amount):

        w, _ = self._field.get_size()
        offset = slide_amount / w
        start, end = self._range
        self._value = max(start, min(end, start + offset * (end - start)))

        if self._value_type == "int":
            self._value = int(self._value)

        self.__update_image()

    def set_value(self, value):

        if self._value != value:
            self._value = value
            self.__update_image()

    def get_value(self):

        return self._value

    def __update_image(self):

        w, h = self._field.get_size()
        image = PNMImage(w, h, 4)
        r, g, b, a = Skin["colors"]["inputfield_background"]
        image.fill(r, g, b)
        image.alpha_fill(a)

        val = self._value
        val_str = "{:.5f}" if self._value_type == "float" else "{:d}"
        label = self._font.create_image(val_str.format(val), self._text_color)

        painter = PNMPainter(image)
        fill = PNMBrush.make_pixel(self._color)
        pen = PNMBrush.make_transparent()
        painter.set_fill(fill)
        painter.set_pen(pen)
        w_l, h_l = label.size
        x = (w - w_l) // 2
        y = (h - h_l) // 2
        start, end = self._range
        w -= Skin["options"]["slider_mark_thickness"]
        w = int(w * (val - start) / (end - start))
        painter.draw_rectangle(0, 0, w, h)
        image.blend_sub_image(self._mark * self._color, w, 0, 0, 0)
        image.blend_sub_image(label, x, y, 0, 0)
        self._image = image

        image = PNMImage(image)
        img_offset_x, img_offset_y = self._field.get_image_offset()
        image.blend_sub_image(self._field.get_border_image(), img_offset_x, img_offset_y, 0, 0)
        self._tex.load(image)

    def get_image(self):

        return self._image

    def hide(self):

        self._root.hide()

    def show(self, pos):

        x, y = pos
        self._root.set_pos(x, 0, -y)
        self._root.show()


class InputField(Widget):

    _active_field = None
    _default_input_parsers = {}
    _default_value_parsers = {}
    _default_text_color = (0., 0., 0., 1.)
    _default_back_color = (1., 1., 1., 1.)
    _height = 0
    # create a mouse region "mask" to disable interaction with all widgets (and the
    # viewport) - except input fields - whenever an input field is active
    _mouse_region_mask = None
    _mouse_region_masks = {}
    # make sure each MouseWatcher has a unique name;
    # each time region masks are needed, check for each existing MouseWatcher if its name is in
    # the above dict; if so, retrieve the previously created region mask, otherwise create a
    # region mask for it and add it to the dict;
    # the sort of the region mask for the MouseWatcher named "panel_stack" needs to be 105, the
    # sort of the other region masks must be lower than 100
    _mouse_watchers = None
    _listener = DirectObject()
    _ref_node = NodePath("input_ref_node")
    _edit_menu = None
    _entered_suppressed_state = False

    @classmethod
    def init(cls):

        TextControl.init()
        SliderControl.init()

        d = 100000
        cls._mouse_region_mask = MouseWatcherRegion("inputfield_mask", -d, d, -d, d)
        cls._mouse_region_mask.set_sort(90)

        cls._default_text_color = Skin["text"]["input"]["color"]
        cls._default_back_color = Skin["colors"]["inputfield_background"]
        cls._height = Skin["options"]["inputfield_height"]

        def accept_input():

            if cls._active_field:
                cls._active_field._on_accept_input()

        def reject_input():

            if cls._active_field and cls._active_field.allows_reject():
                cls._active_field._on_reject_input()

        Mgr.expose("active_input_field", lambda: cls._active_field)
        Mgr.accept("accept_field_input", accept_input)
        Mgr.accept("reject_field_input", reject_input)

        def parse_to_string(input_text):

            return input_text

        def parse_to_int(input_text):

            try:
                return int(eval(input_text))
            except:
                return None

        def parse_to_float(input_text):

            try:
                return float(eval(input_text))
            except:
                return None

        cls._default_input_parsers["string"] = parse_to_string
        cls._default_input_parsers["int"] = parse_to_int
        cls._default_input_parsers["float"] = parse_to_float

        def parse_from_string(value):

            return value

        def parse_from_int(value):

            return str(value)

        def parse_from_float(value):

            return "{:.5f}".format(value)

        cls._default_value_parsers["string"] = parse_from_string
        cls._default_value_parsers["int"] = parse_from_int
        cls._default_value_parsers["float"] = parse_from_float

        def edit_text(edit_op):

            if cls._active_field:

                txt_ctrl = cls._active_field.get_text_control()

                if edit_op == "cut":
                    txt_ctrl.cut_text()
                elif edit_op == "copy":
                    txt_ctrl.copy_text()
                elif edit_op == "paste":
                    txt_ctrl.paste_text()
                elif edit_op == "select_all":
                    txt_ctrl.select_all()

        cls._edit_menu = menu = Menu()
        menu.add("cut", "Cut", lambda: edit_text("cut"))
        menu.set_item_hotkey("cut", None, "Ctrl+X")
        menu.add("copy", "Copy", lambda: edit_text("copy"))
        menu.set_item_hotkey("copy", None, "Ctrl+C")
        menu.add("paste", "Paste", lambda: edit_text("paste"))
        menu.set_item_hotkey("paste", None, "Ctrl+V")
        menu.add("select_all", "Select All", lambda: edit_text("select_all"))
        menu.set_item_hotkey("select_all", None, "Ctrl+A")
        menu.update()

        Mgr.accept("accept_field_events", cls.__accept_events)
        Mgr.accept("ignore_field_events", cls.__ignore_events)

    @classmethod
    def __accept_events(cls):

        if cls._active_field:
            cls._active_field.accept_events()

    @classmethod
    def __ignore_events(cls):

        if cls._active_field:
            cls._active_field.ignore_events()

    @staticmethod
    def __enter_suppressed_state():

        cls = InputField

        if not cls._entered_suppressed_state:
            Mgr.enter_state("suppressed")
            cls._entered_suppressed_state = True

    @staticmethod
    def __exit_suppressed_state():

        cls = InputField

        if cls._entered_suppressed_state:
            Mgr.exit_state("suppressed")
            cls._entered_suppressed_state = False

    @classmethod
    def _get_mouse_watchers(cls):

        if cls._mouse_watchers is None:
            return GlobalData["mouse_watchers"] 

        return cls._mouse_watchers

    @classmethod
    def _on_accept_input(cls):

        active_field = cls._active_field
        cls.set_active_input_field(None)

        cls.__exit_suppressed_state()
        cls._listener.ignore_all()

        for watcher in cls._get_mouse_watchers():
            region_mask = cls._get_mouse_region_mask(watcher.get_name())
            region_mask.set_active(False)
            watcher.remove_region(region_mask)

        active_field.accept_input()

    @classmethod
    def _on_reject_input(cls):

        active_field = cls._active_field
        cls.set_active_input_field(None)

        cls.__exit_suppressed_state()
        cls._listener.ignore_all()

        for watcher in cls._get_mouse_watchers():
            region_mask = cls._get_mouse_region_mask(watcher.get_name())
            region_mask.set_active(False)
            watcher.remove_region(region_mask)

        active_field.reject_input()

    @classmethod
    def _get_mouse_region_mask(cls, mouse_watcher_name):

        if mouse_watcher_name in cls._mouse_region_masks:
            return cls._mouse_region_masks[mouse_watcher_name]

        if mouse_watcher_name == "panel_stack":
            mouse_region_mask = MouseWatcherRegion(cls._mouse_region_mask)
            mouse_region_mask.set_sort(105)
        else:
            mouse_region_mask = cls._mouse_region_mask

        cls._mouse_region_masks[mouse_watcher_name] = mouse_region_mask

        return mouse_region_mask

    @staticmethod
    def set_active_input_field(input_field):

        InputField._active_field = input_field

    @staticmethod
    def update_active_text_pos():

        if InputField._active_field:
            InputField._active_field.update_text_pos()

    @staticmethod
    def set_default_value_parser(value_type, parser):

        InputField._default_value_parsers[value_type] = parser

    @staticmethod
    def set_default_input_parser(value_type, parser):

        InputField._default_input_parsers[value_type] = parser

    def __init__(self, parent, value_id, value_type, handler, width, border_gfx_data, image_offset,
                 font=None, text_color=None, back_color=None, sort=110, cull_bin=("gui", 3),
                 on_accept=None, on_reject=None, on_key_enter=None, on_key_escape=None,
                 allow_reject=True):

        Widget.__init__(self, "input_field", parent, gfx_data={}, stretch_dir="horizontal")

        self.set_image_offset(image_offset)
        self.get_mouse_region().set_sort(sort)

        self._text_color = text_color if text_color else self._default_text_color
        self._back_color = back_color if back_color else self._default_back_color

        self._width = int(width * Skin["options"]["inputfield_width_scale"])
        self._text_ctrl = None
        size = (self._width, self._height)
        self.set_size(size, is_min=True)
        self._border_gfx_data = border_gfx_data
        self._border_image = self.__create_border_image()
        self._text_ctrl = TextControl(self, font, self._text_color, cull_bin)
        self._delay_card_update = False
        self._scissor_effect = None

        self._cull_bin = cull_bin
        self._on_accept = on_accept
        self._on_reject = on_reject
        self._on_key_enter = on_key_enter if on_key_enter else lambda: None
        self._on_key_escape = on_key_escape if on_key_escape else lambda: None
        self._allows_reject = allow_reject
        self._is_text_shown = True
        self._is_clicked = False
        self._selecting_text = False
        self._text = ""
        self._value = None
        self._value_id = value_id
        self._value_type = value_type
        self._input_init = lambda: None
        self._input_parser = None
        self._value_parser = None

        if handler:
            self._value_handler = handler
        else:
            self._value_handler = lambda value_id, value, state: None

        self._popup_menu = None
        self._manage_popup_menu = True
        self._popup_handler = lambda: None

    def destroy(self):

        Widget.destroy(self)

        if self._text_ctrl:
            self._text_ctrl.destroy()

        self._text_ctrl = None
        self._value_handler = None
        self._value_parser = None
        self._input_parser = None
        self._input_init = None
        self._on_accept = lambda: None
        self._on_reject = lambda: None
        self._on_key_enter = lambda: None
        self._on_key_escape = lambda: None
        self._popup_handler = lambda: None

        if self._popup_menu and self._manage_popup_menu:
            self._popup_menu.destroy()

        self._popup_menu = None
        self._listener.ignore_all()

    def __create_border_image(self):

        w, h = self.get_size()
        l, r, b, t = self.get_outer_borders()
        borders_h = l + r
        borders_v = b + t
        width = w + borders_h
        height = h + borders_v
        gfx_data = {"": self._border_gfx_data}
        tmp_widget = Widget("tmp", self.get_parent(), gfx_data, stretch_dir="both", has_mouse_region=False)
        tmp_widget.set_size((width, height), is_min=True)
        tmp_widget.update_images()
        image = tmp_widget.get_image()
        tmp_widget.destroy()

        return image

    def set_on_key_enter(self, on_key_enter=None):

        self._on_key_enter = on_key_enter if on_key_enter else lambda: None

    def set_on_key_escape(self, on_key_escape=None):

        self._on_key_escape = on_key_escape if on_key_escape else lambda: None

    def set_on_accept(self, on_accept=None):

        self._on_accept = on_accept

    def set_on_reject(self, on_reject=None):

        self._on_reject = on_reject

    def allow_reject(self, allow_reject=True):

        self._allows_reject = allow_reject

    def allows_reject(self):

        return self._allows_reject

    def get_text_control(self):

        return self._text_ctrl

    def set_scissor_effect(self, effect):

        self._scissor_effect = effect

        if self._text_ctrl:
            self._text_ctrl.set_scissor_effect(effect)

    def set_size(self, size, includes_borders=True, is_min=False):

        w, h = Widget.set_size(self, size, includes_borders, is_min)
        size = (w, self._height)

        if self._text_ctrl:
            self._text_ctrl.set_size(size)

        return size

    def delay_card_update(self, delay=True):

        self._delay_card_update = delay

    def is_card_update_delayed(self):

        return self._delay_card_update

    def __card_update_task(self):

        if self.is_hidden():
            return

        image = self.get_image(composed=False, draw_border=True, crop=True)

        if image:
            w, h = image.get_x_size(), image.get_y_size()
            self.get_card().copy_sub_image(self, image, w, h)

    def __update_card_image(self):

        task = self.__card_update_task

        if self._delay_card_update:
            task_id = "update_card_image"
            PendingTasks.add(task, task_id, sort=1, id_prefix=self.get_widget_id(),
                             batch_id="widget_card_update")
        else:
            task()

    def update_images(self, recurse=True, size=None):

        w, h = self.get_size()

        if "" in self._images:

            img = self._images[""]

            if img.get_x_size() == w and img.get_y_size() == h:
                return

        Widget.update_images(self, recurse, size)

        self._border_image = self.__create_border_image()
        image = PNMImage(w, h, 4)
        r, g, b, a = self._back_color
        image.fill(r, g, b)
        image.alpha_fill(a)
        self._images = {"": image}

        return self._images

    def get_border_image(self):

        return self._border_image

    def _draw_control_image(self, image):

        if self._text and self._text_ctrl and self._is_text_shown:

            if self is self._active_field:
                text = self._text
                label = self._text_ctrl.create_label(text)
            else:
                label = self._text_ctrl.get_label()

            if label:
                w, h = self.get_size()
                w_l, h_l = label.size
                x = margin = Skin["options"]["inputfield_margin"]
                y = (h - h_l) // 2
                w -= margin * 2
                image.blend_sub_image(label, x, y, 0, 0, w, h_l)

    def get_image(self, state=None, composed=True, draw_border=True, crop=False):

        image = Widget.get_image(self, state, composed)

        if not image:
            return

        self._draw_control_image(image)

        if draw_border:

            border_img = self._border_image
            img_offset_x, img_offset_y = self.get_image_offset()

            if crop:
                image.blend_sub_image(border_img, img_offset_x, img_offset_y, 0, 0)
                img = image
            else:
                w, h = border_img.size
                img = PNMImage(w, h, 4)
                img.copy_sub_image(image, -img_offset_x, -img_offset_y, 0, 0)
                img.blend_sub_image(border_img, 0, 0, 0, 0)

        else:

            img = image

        return img

    def update_text_pos(self):

        pos = self.get_pos(ref_node=self._ref_node)
        self._text_ctrl.set_pos(pos)

    def __set_caret_to_mouse_pos(self, select=False):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        x, y = self.get_pos(ref_node=self._ref_node)
        self._text_ctrl.move_caret(mouse_x - x, is_offset=False, select=select)

    def __select_text(self, task):

        self.__set_caret_to_mouse_pos(select=True)

        return task.again

    def accept_events(self):

        txt_ctrl = self._text_ctrl

        def write_keystroke(char):

            val = ord(char)

            if val == 1:
                txt_ctrl.select_all()
            elif val == 3:
                txt_ctrl.copy_text()
            elif val == 24:
                txt_ctrl.cut_text()
            elif val == 22 and not USING_TK:
                txt_ctrl.paste_text()
            elif val in range(32, 255):
                txt_ctrl.write(char)

        def on_key_enter():

            Mgr.do("accept_field_input")
            self._on_key_enter()

        def on_key_escape():

            Mgr.do("reject_field_input")
            self._on_key_escape()

        def is_shift_down():

            return Mgr.get("mouse_watcher").is_button_down("shift")

        listener = self._listener
        listener.accept("gui_arrow_left", lambda: txt_ctrl.move_caret(-1, select=is_shift_down()))
        listener.accept("gui_arrow_right", lambda: txt_ctrl.move_caret(1, select=is_shift_down()))
        listener.accept("gui_arrow_left-repeat", lambda: txt_ctrl.move_caret(-1, select=is_shift_down()))
        listener.accept("gui_arrow_right-repeat", lambda: txt_ctrl.move_caret(1, select=is_shift_down()))
        listener.accept("gui_home", lambda: txt_ctrl.move_caret_to_start(select=is_shift_down()))
        listener.accept("gui_end", lambda: txt_ctrl.move_caret_to_end(select=is_shift_down()))
        listener.accept("gui_delete", txt_ctrl.delete)
        listener.accept("gui_backspace", txt_ctrl.backspace)
        listener.accept("gui_delete-repeat", txt_ctrl.delete)
        listener.accept("gui_backspace-repeat", txt_ctrl.backspace)
        listener.accept("keystroke", write_keystroke)
        listener.accept("gui_enter", on_key_enter)
        listener.accept("gui_escape", on_key_escape)

    def ignore_events(self):

        listener = self._listener
        for event_id in ("gui_arrow_left", "gui_arrow_right", "gui_arrow_left-repeat",
                         "gui_arrow_right-repeat", "gui_home", "gui_end", "gui_delete",
                         "gui_backspace", "gui_delete-repeat", "gui_backspace-repeat",
                         "keystroke", "gui_enter", "gui_escape"):
            listener.ignore(event_id)

    def has_slider_control(self):

        return False

    def is_checking_mouse_offset(self):

        return False

    def init_mouse_checking(self):
        """ Override in derived class """

        pass

    def cancel_mouse_checking(self, event_id):
        """ Override in derived class """

        pass

    def is_sliding(self):

        return False

    def finalize_sliding(self):
        """ Override in derived class """

        pass

    def cancel_sliding(self, event_id):
        """ Override in derived class """

        pass

    def on_left_down(self):

        if self._active_field is self:
            shift_down = Mgr.get("mouse_watcher").is_button_down("shift")
            self.__set_caret_to_mouse_pos(select=shift_down)
            Mgr.add_task(.05, self.__select_text, "select_text")
            self._selecting_text = True
            return

        if self._active_field:
            self._active_field._on_accept_input()

        self._listener.accept("gui_mouse1-up", self._on_left_up)

        if self.has_slider_control():
            self.init_mouse_checking()
        else:
            self._is_clicked = True

    def _on_left_up(self):

        if self.is_checking_mouse_offset():
            self.cancel_mouse_checking("on_left_up")

        if self.is_sliding():

            self.finalize_sliding()

        elif self._selecting_text:

            Mgr.remove_task("select_text")

            if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
                Mgr.set_cursor("input_commit")

            self._selecting_text = False

        elif self._is_clicked:

            if Mgr.get_state_id() != "suppressed":
                self.__enter_suppressed_state()

            self.set_active_input_field(self)

            for watcher in self._get_mouse_watchers():
                region_mask = self._get_mouse_region_mask(watcher.get_name())
                region_mask.set_active(True)
                watcher.add_region(region_mask)

            txt_ctrl = self._text_ctrl
            txt_ctrl.set_text(self._text)
            pos = self.get_pos(ref_node=self._ref_node)
            txt_ctrl.show(pos)
            self._input_init()

            listener = self._listener
            listener.accept("focus_loss", lambda: Mgr.do("reject_field_input"))
            self.accept_events()

            if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
                Mgr.set_cursor("input_commit")
            elif self.has_slider_control():
                Mgr.set_cursor("caret")

            return True

        return False

    def on_right_down(self):

        if self.is_checking_mouse_offset():
            self.cancel_mouse_checking("on_right_down")
            return

        if self.is_sliding():
            self.cancel_sliding("on_right_down")
            return

        if self._selecting_text:
            return

        if self._active_field is self:
            self._edit_menu.show_at_mouse_pos()
            return

        Mgr.do("reject_field_input")
        self._popup_handler()

    def _on_right_up(self):

        self._listener.ignore("gui_mouse3-up")

        if self.is_checking_mouse_offset():
            self.cancel_mouse_checking("on_right_up")
        elif self.is_sliding():
            self.cancel_sliding("on_right_up")

    def on_enter(self):

        if self.has_slider_control() and self._active_field is not self:
            cursor_id = "slider_caret"
        else:
            cursor_id = "caret"

        Mgr.set_cursor(cursor_id)

    def on_leave(self):

        if not (self._selecting_text or self.is_checking_mouse_offset() or self.is_sliding()):
            if self._active_field and not Menu.is_menu_shown():
                Mgr.set_cursor("input_commit")
            else:
                Mgr.set_cursor("main")
                self._is_clicked = False
            if not self._active_field:
                self._listener.ignore("gui_mouse1-up")

    def set_input_init(self, input_init):

        self._input_init = input_init

    def set_input_parser(self, parser):

        self._input_parser = parser

    def __parse_input(self, input_text):

        default_parser = self._default_input_parsers.get(self._value_type)
        parser = self._input_parser if self._input_parser else default_parser

        return parser(input_text) if parser else None

    def set_value_parser(self, parser):

        self._value_parser = parser

    def __parse_value(self, value):

        default_parser = self._default_value_parsers.get(self._value_type)
        parser = self._value_parser if self._value_parser else default_parser

        return parser(value) if parser else None

    def get_value_id(self):

        return self._value_id

    def __reset_cursor(self):

        over_field = False

        for watcher in GlobalData["mouse_watchers"]:

            region = watcher.get_over_region()

            if region:

                name = region.get_name()

                if name.startswith("widget_"):

                    widget_id = int(name.replace("widget_", ""))
                    widget = Widget.registry.get(widget_id)

                    if widget and "field" in widget.get_widget_type():
                        over_field = True
                        break

        if not over_field:
            Mgr.set_cursor("main")
        elif widget.has_slider_control():
            Mgr.set_cursor("slider_caret")

    def on_input_commit(self):
        """ Override in derived class """

        pass

    def accept_input(self, text_handler=None):

        txt_ctrl = self._text_ctrl
        old_text = self._text
        input_text = txt_ctrl.get_text()

        value = self.__parse_input(input_text)
        valid = False

        if value is None:

            val_str = old_text

        else:

            val_str = self.__parse_value(value)

            if val_str is None:
                val_str = old_text
            else:
                valid = True

        self._text = val_str

        if valid:

            self._value = value
            txt_ctrl.set_text(val_str)
            self.on_input_commit()

            if self._is_text_shown:
                self.__update_card_image()

            state = "continuous" if self.is_sliding() else "done"
            self._value_handler(self._value_id, value, state)

            if text_handler:
                text_handler(val_str)

        else:

            txt_ctrl.set_text(old_text)

        txt_ctrl.hide()
        self.__reset_cursor()

        self._is_clicked = False

        if self._on_accept:
            self._on_accept(valid)

        return valid

    def reject_input(self):

        txt_ctrl = self._text_ctrl
        old_text = self._text
        input_text = txt_ctrl.get_text()

        if input_text != old_text:
            if old_text:
                txt_ctrl.set_text(old_text)
            else:
                txt_ctrl.clear()

        txt_ctrl.hide()
        self.__reset_cursor()

        self._is_clicked = False

        if self._on_reject:
            self._on_reject()

    def set_value(self, value, text_handler=None, handle_value=False, _force_update=False):

        val_str = self.__parse_value(value)

        if val_str is None:
            return False

        self._text = val_str
        self._value = value
        txt_ctrl = self._text_ctrl
        update_card_image = False

        if _force_update:
            update_card_image = True
        elif self.is_sliding():
            update_card_image = True
        elif txt_ctrl.get_text() != val_str:
            txt_ctrl.set_text(val_str)
            update_card_image = True

        if update_card_image and self._is_text_shown:
            self.__update_card_image()

        if handle_value:
            state = "continuous" if self.is_sliding() else "done"
            self._value_handler(self._value_id, value, state)

        if text_handler:
            text_handler(val_str)

        return True

    def get_value(self):

        return self._value

    def set_input_text(self, text):

        self._text_ctrl.set_text(text)

    def set_text(self, text, text_handler=None):

        if self._text == text:
            return False

        self._text_ctrl.set_text(text)
        self._text = text

        if self._is_text_shown:
            self.__update_card_image()

        if text_handler:
            text_handler(text)

        return True

    def get_text(self):

        return self._text

    def show_text(self, show=True):

        if self._is_text_shown == show:
            return False

        self._is_text_shown = show
        self.__update_card_image()

        return True

    def set_text_color(self, color=None):

        txt_ctrl = self._text_ctrl

        if txt_ctrl.get_color() == color:
            return False

        txt_ctrl.set_color(color if color else self._text_color)
        txt_ctrl.set_text(self._text)

        if self._is_text_shown:
            self.__update_card_image()

        return True

    def get_text_color(self):

        return self._text_ctrl.get_color()

    def clear(self, forget=True):

        txt_ctrl = self._text_ctrl
        txt_ctrl.clear()

        if forget:
            self._text = ""

        if self._is_text_shown:
            self.__update_card_image()

    def update(self, text, text_ctrl, input_init, input_parser, value_parser,
               value_handler, value_type, value):

        self._text = text
        self._text_ctrl = text_ctrl
        self._input_init = input_init
        self._input_parser = input_parser
        self._value_parser = value_parser
        self._value_handler = value_handler
        self._value_type = value_type
        self._value = value

        if self._is_text_shown:
            self.__update_card_image()

    def set_popup_menu(self, menu, manage=True):

        self._popup_menu = menu
        self._manage_popup_menu = manage
        self._popup_handler = menu.show_at_mouse_pos

    def get_popup_menu(self):

        if not self._popup_menu:
            self._popup_menu = Menu()
            self._popup_handler = self._popup_menu.show_at_mouse_pos

        return self._popup_menu

    def set_popup_handler(self, on_popup):

        if not self._popup_menu:
            self._popup_menu = Menu()

        def handle_popup():

            on_popup()
            self._popup_menu.show_at_mouse_pos()

        self._popup_handler = handle_popup

    def enable(self, enable=True, ignore_parent=False):

        if not Widget.enable(self, enable, ignore_parent):
            return False

        self.__update_card_image()

        return True


class SliderMixin:

    _clock = ClockObject()

    def __init__(self):

        self._slider_ctrl = None
        self._sliding = False
        self._checking_mouse_offset = False
        self._mouse_start_pos = ()
        self._mouse_prev = None
        self._start_value = None
        self._handler_delay = 0.

    def destroy(self):

        if self._slider_ctrl:
            self._slider_ctrl.destroy()
            self._slider_ctrl = None

    def _draw_control_image(self, image):

        if self._slider_ctrl and self._is_text_shown:
            slider_img = self._slider_ctrl.get_image()
            image.copy_sub_image(slider_img, 0, 0, 0, 0)

    def is_checking_mouse_offset(self):

        return self._checking_mouse_offset

    def __check_mouse_offset(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.x
        mouse_y = mouse_pointer.y
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            self._sliding = True
            self._on_slide_start()
            pos = self.get_pos(ref_node=self._ref_node)
            self._slider_ctrl.show(pos)
            self._mouse_prev = None
            self._start_value = self.get_value()
            Mgr.add_task(self.__slide, "slide")
            self._listener.accept("gui_mouse3-up", self._on_right_up)
            self._listener.accept("gui_+", self.__incr_handler_delay)
            self._listener.accept("gui_-", self.__decr_handler_delay)
            self._checking_mouse_offset = False
            return

        return task.cont

    def init_mouse_checking(self):

        self._checking_mouse_offset = True
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.x, mouse_pointer.y)
        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")
        self._listener.accept("gui_mouse3-up", self._on_right_up)

    def cancel_mouse_checking(self, event_id):

        Mgr.remove_task("check_mouse_offset")

        if event_id == "on_left_up":
            if self.get_mouse_watcher().get_over_region() == self.get_mouse_region():
                self._is_clicked = True
        elif event_id == "on_right_up":
            if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
                self._listener.ignore("gui_mouse1-up")

        if event_id in ("on_left_up", "on_right_down"):
            self._listener.ignore("gui_mouse3-up")

        self._checking_mouse_offset = False

    def _on_slide_start(self):
        """ Override in derived class """

        pass

    def _on_slide_end(self, cancelled=False):
        """ Override in derived class """

        pass

    def __incr_handler_delay(self):

        self._handler_delay += .05

    def __decr_handler_delay(self):

        self._handler_delay = max(0., self._handler_delay - .05)

    def __slide(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.x
        prev_value = self._slider_ctrl.get_value()
        delay = self._handler_delay

        if self._mouse_prev != mouse_x:

            x, _ = self.get_pos(ref_node=self._ref_node)
            self._slider_ctrl.update_value(mouse_x - x)

            if self._clock.get_real_time() > delay:

                value = self._slider_ctrl.get_value()

                if value != prev_value:
                    InputField.set_value(self, value, handle_value=True)

                self._clock.reset()

            self._mouse_prev = mouse_x

        elif prev_value != self.get_value() and self._clock.get_real_time() > delay:

            InputField.set_value(self, prev_value, handle_value=True)

        return task.cont

    def has_slider_control(self):

        return True

    def is_sliding(self):

        return self._sliding

    def finalize_sliding(self):

        Mgr.remove_task("slide")
        self._slider_ctrl.hide()

        if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
            Mgr.set_cursor("main")

        self._listener.ignore("gui_mouse3-up")
        self._listener.ignore("gui_+")
        self._listener.ignore("gui_-")
        self._sliding = False

        self._on_slide_end()

    def cancel_sliding(self, event_id):

        self._listener.ignore("gui_+")
        self._listener.ignore("gui_-")
        Mgr.remove_task("slide")
        self._slider_ctrl.hide()
        self._sliding = False

        if event_id == "on_right_down":

            if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
                Mgr.set_cursor("main")

            self._listener.ignore("gui_mouse3-up")

        elif event_id == "on_right_up":

            if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
                Mgr.set_cursor("main")
                self._listener.ignore("gui_mouse1-up")

        self._on_slide_end(cancelled=True)

    def set_scissor_effect(self, effect):

        if self._slider_ctrl:
            self._slider_ctrl.set_scissor_effect(effect)

    def set_size(self, size):

        if self._slider_ctrl:
            self._slider_ctrl.set_size(size)

    def set_slider_value(self, value):

        self._slider_ctrl.set_value(value)

    def get_slider_value(self):

        return self._slider_ctrl.get_value()

    def on_input_commit(self):

        if self._slider_ctrl:
            self._slider_ctrl.set_value(self.get_value())


class SliderInputField(SliderMixin, InputField):

    def __init__(self, parent, value_id, value_type, value_range, handler, width, border_gfx_data,
                 image_offset, font=None, text_color=None, back_color=None, sort=110,
                 cull_bin=("gui", 3), on_accept=None, on_reject=None, on_key_enter=None,
                 on_key_escape=None, allow_reject=True):

        SliderMixin.__init__(self)
        InputField.__init__(self, parent, value_id, value_type, handler, width, border_gfx_data,
                            image_offset, font, text_color, back_color, sort, cull_bin, on_accept,
                            on_reject, on_key_enter, on_key_escape, allow_reject)

        self._slider_ctrl = SliderControl(self, value_range, value_type, cull_bin)
        self.set_value(self._slider_ctrl.get_value())

    def destroy(self):

        SliderMixin.destroy(self)
        InputField.destroy(self)

    def _on_slide_end(self, cancelled=False):

        if cancelled:
            self.set_value(self._start_value, handle_value=True, _force_update=True)
        else:
            value = self._slider_ctrl.get_value()
            InputField.set_value(self, value, handle_value=True)

    def set_scissor_effect(self, effect):

        SliderMixin.set_scissor_effect(self, effect)
        InputField.set_scissor_effect(self, effect)

    def set_size(self, size, includes_borders=True, is_min=False):

        size = InputField.set_size(self, size, includes_borders, is_min)
        SliderMixin.set_size(self, size)

    def set_value(self, value, text_handler=None, handle_value=False, _force_update=False):

        self._slider_ctrl.set_value(value)

        return InputField.set_value(self, value, text_handler, handle_value, _force_update)


class MultiValInputField(SliderMixin, InputField):

    def __init__(self, parent, width, border_gfx_data, image_offset, font=None, text_color=None,
                 back_color=None, sort=110, cull_bin=("gui", 3), on_accept=None, on_reject=None,
                 on_key_enter=None, on_key_escape=None, allow_reject=True):

        self._text_ctrls = {}
        self._slider_ctrls = {}

        SliderMixin.__init__(self)
        InputField.__init__(self, parent, "", "", None, width, border_gfx_data, image_offset,
                            font, text_color, back_color, sort, cull_bin, on_accept, on_reject,
                            on_key_enter, on_key_escape, allow_reject)

        self._texts = {}
        self._value_id = None
        self._values = {}
        self._value_types = {}
        self._value_handlers = {}
        self._value_parsers = {}
        self._input_parsers = {}
        self._input_inits = {}

    def destroy(self):

        SliderMixin.destroy(self)
        InputField.destroy(self)

        for txt_ctrl in self._text_ctrls.values():
            txt_ctrl.destroy()

        self._text_ctrls = {}
        self._slider_ctrls = {}
        self._values = {}
        self._value_handlers = {}
        self._value_parsers = {}
        self._input_parsers = {}
        self._input_inits = {}

    def get_text_control(self, value_id=None):

        return self._text_ctrls[self._value_id if value_id is None else value_id]

    def has_slider_control(self):

        return self._value_id in self._slider_ctrls

    def _draw_control_image(self, image):

        if self.has_slider_control():
            SliderMixin._draw_control_image(self, image)
        else:
            InputField._draw_control_image(self, image)

    def set_scissor_effect(self, effect):

        SliderMixin.set_scissor_effect(self, effect)
        InputField.set_scissor_effect(self, effect)

        for txt_ctrl in self._text_ctrls.values():
            txt_ctrl.set_scissor_effect(effect)

    def set_size(self, size, includes_borders=True, is_min=False):

        size = InputField.set_size(self, size, includes_borders, is_min)
        SliderMixin.set_size(self, size)

        for txt_ctrl in self._text_ctrls.values():
            txt_ctrl.set_size(size)

    def set_input_init(self, value_id, input_init):

        self._input_inits[value_id] = input_init

    def set_input_parser(self, value_id, parser):

        self._input_parsers[value_id] = parser

    def __parse_input(self, value_id, input_text):

        val_type = self._value_types[value_id]
        default_parser = self._default_input_parsers.get(val_type)
        parser = self._input_parsers.get(value_id, default_parser)

        return parser(input_text) if parser else None

    def set_value_parser(self, value_id, parser):

        self._value_parsers[value_id] = parser

    def __parse_value(self, value_id, value):

        val_type = self._value_types[value_id]
        default_parser = self._default_value_parsers.get(val_type)
        parser = self._value_parsers.get(value_id, default_parser)

        return parser(value) if parser else None

    def add_value(self, value_id, value_type, handler, font=None, value_range=None):

        self._value_types[value_id] = value_type
        txt_ctrl = TextControl(self, font, self._text_color, self._cull_bin)
        txt_ctrl.set_scissor_effect(self._scissor_effect)
        self._text_ctrls[value_id] = txt_ctrl
        self._texts[value_id] = ""
        self._input_inits[value_id] = lambda: None

        if handler:
            self._value_handlers[value_id] = handler
        else:
            self._value_handlers[value_id] = lambda value_id, value, state: None

        if value_range:
            slider_ctrl = SliderControl(self, value_range, value_type, self._cull_bin)
            slider_ctrl.set_scissor_effect(self._scissor_effect)
            self._slider_ctrls[value_id] = slider_ctrl
            self._values[value_id] = value_range[0]
        else:
            self._values[value_id] = None

    def add_slider_value(self, value_id, value_type, value_range, handler, font=None):

        self.add_value(value_id, value_type, handler, font, value_range)

    def accept_input(self, text_handler=None):

        if InputField.accept_input(self, text_handler):
            self._texts[self._value_id] = self._text
            return True

        return False

    def set_value(self, value_id, value, text_handler=None, handle_value=False, _force_update=False):

        if value_id in self._slider_ctrls:
            self._slider_ctrls[value_id].set_value(value)

        if self._value_id == value_id:
            if InputField.set_value(self, value, text_handler, handle_value, _force_update):
                self._texts[value_id] = self._text
                return True
            else:
                return False

        val_str = self.__parse_value(value_id, value)

        if val_str is None:
            return False

        self._texts[value_id] = val_str
        txt_ctrl = self._text_ctrls[value_id]

        if txt_ctrl.get_text() != val_str:
            txt_ctrl.set_text(val_str)

        if handle_value:
            self._value_handlers[value_id](value_id, value)

        if text_handler:
            text_handler(val_str)

        return True

    def set_text(self, value_id, text, text_handler=None):

        if self._texts[value_id] == text:
            return False

        txt_ctrl = self._text_ctrls[value_id]
        txt_ctrl.set_text(text)
        self._texts[value_id] = text

        if self._value_id == value_id:
            InputField.set_text(self, text)

        if text_handler:
            text_handler(text)

        return True

    def get_text(self, value_id):

        return self._texts[value_id]

    def set_text_color(self, color=None):

        if not InputField.set_text_color(self, color):
            return False

        for value_id, txt_ctrl in self._text_ctrls.items():
            txt_ctrl.set_color(color if color else self._text_color)
            txt_ctrl.set_text(self._texts[value_id])

        return True

    def clear(self, forget=True):

        InputField.clear(self, forget)

        if forget:
            self._texts[self._value_id] = ""

    def show_value(self, value_id):

        if value_id in self._texts:
            self._value_id = value_id
            self._slider_ctrl = self._slider_ctrls.get(value_id)
            InputField.update(
                self,
                self._texts[value_id],
                self._text_ctrls[value_id],
                self._input_inits[value_id],
                self._input_parsers.get(value_id),
                self._value_parsers.get(value_id),
                self._value_handlers[value_id],
                self._value_types[value_id],
                self._values[value_id]
            )

    def _on_slide_end(self, cancelled=False):

        value = self._start_value if cancelled else self._slider_ctrl.get_value()
        self.set_value(self._value_id, value, handle_value=True, _force_update=cancelled)

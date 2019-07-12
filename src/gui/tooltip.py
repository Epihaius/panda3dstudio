from .base import *


class ToolTip:

    _card = None
    _label = None
    _tex = None
    _clock = None
    _delay = False

    @classmethod
    def init(cls):

        cm = CardMaker("tooltip")
        cm.set_frame(0., 1., -1., 0.)
        cls._card = card = Mgr.get("gui_root").attach_new_node(cm.generate())
        tex = Texture("tooltip_tex")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        cls._tex = tex
        card.set_bin("tooltip", 1)
        card.set_depth_test(False)
        card.set_depth_write(False)
        card.set_texture(tex)
        card.hide()
        cls._clock = ClockObject()

    @classmethod
    def create_label(cls, text, text_color=None):

        skin_text = Skin["text"]["tooltip"]

        if text_color:
            color = text_color
        else:
            color = skin_text["color"]

        font = skin_text["font"]
        colors = Skin["colors"]
        image = font.create_image(text, color)
        w = image.get_x_size()
        h = image.get_y_size()
        label = PNMImage(w + 8, h + 8, 4)
        painter = PNMPainter(label)
        fill = PNMBrush.make_pixel(colors["tooltip_background"])
        pen = PNMBrush.make_pixel(colors["tooltip_border"])
        painter.set_fill(fill)
        painter.set_pen(pen)
        painter.draw_rectangle(0, 0, w + 7, h + 7)
        label.blend_sub_image(image, 4, 4, 0, 0)

        return label

    @classmethod
    def set_label(cls, label):

        cls._label = label
        card = cls._card
        w = label.get_x_size()
        h = label.get_y_size()
        card.set_sx(w)
        card.set_sz(h)
        cls._tex.load(label)

        if not card.is_hidden():
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            x = mouse_pointer.get_x()
            y = mouse_pointer.get_y() + 20
            w_w, h_w = Mgr.get("window_size")
            x = max(0, min(x, w_w - w))
            y = max(0, min(y, h_w - h))
            card.set_x(x)
            card.set_z(-y)

    @classmethod
    def __show_delayed(cls, task):

        if cls._clock.get_real_time() < cls._delay:
            return task.cont

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        x = mouse_pointer.get_x()
        y = mouse_pointer.get_y() + 20
        w = cls._label.get_x_size()
        h = cls._label.get_y_size()
        w_w, h_w = Mgr.get("window_size")
        x = max(0, min(x, w_w - w))
        y = max(0, min(y, h_w - h))
        card = cls._card
        card.set_x(x)
        card.set_z(-y)
        card.show()

    @classmethod
    def show(cls, label, pos=(0, 0), delay=.5):

        cls.set_label(label)
        cls._delay = delay

        if delay:
            cls._clock.reset()
            Mgr.add_task(cls.__show_delayed, "show_tooltip_delayed")
        else:
            x, y = pos
            card = cls._card
            card.set_x(x)
            card.set_z(-y)
            card.show()

    @classmethod
    def hide(cls):

        cls._card.hide()

        if cls._delay:
            Mgr.remove_task("show_tooltip_delayed")
            cls._clock.reset()
            cls._delay = 0.

    @classmethod
    def is_hidden(cls):

        return cls._card.is_hidden()

    @classmethod
    def update(cls, label=None):

        if label:
            cls.set_label(label)
        else:
            cls._card.hide()

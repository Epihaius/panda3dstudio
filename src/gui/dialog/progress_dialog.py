from .dialog import *


class ProgressBarFrame(Widget):

    _gfx = {
        "": (
            ("dialog_inset2_border_topleft", "dialog_inset2_border_top", "dialog_inset2_border_topright"),
            ("dialog_inset2_border_left", "dialog_inset2_border_center", "dialog_inset2_border_right"),
            ("dialog_inset2_border_bottomleft", "dialog_inset2_border_bottom", "dialog_inset2_border_bottomright")
        )
    }

    def __init__(self, parent):

        Widget.__init__(self, "progress_bar_frame", parent, self._gfx, stretch_dir="both",
                        has_mouse_region=False)

    def set_progress_bar(self, progress_bar):

        sizer = Sizer("horizontal")
        self.set_sizer(sizer)
        x, y, w, h = TextureAtlas["regions"]["progress_bar_left"]
        l, r, b, t = borders = self.get_gfx_inner_borders()
        h += b + t
        sizer.set_default_size((500, h))
        self._bar_sizer = bar_sizer = Sizer("horizontal")
        sizer.add(bar_sizer, borders=borders, proportion=1.)
        self._bar_item = bar_sizer.add(progress_bar)
        self._space_item = bar_sizer.add((0, 0), proportion=1.)


class ProgressBar(Widget):

    _gfx = {"": (("progress_bar_left", "progress_bar_center", "progress_bar_right"),)}

    def __init__(self, dialog):

        frame = ProgressBarFrame(dialog)
        Widget.__init__(self, "progress_bar", frame, self._gfx, stretch_dir="horizontal",
                        has_mouse_region=False)
        frame.set_progress_bar(self)

        self._rate = 0.
        self._progress = 0.

    def get_frame(self):

        return self.get_parent()

    def set_rate(self, rate):

        if not self._rate:
            self._rate = rate

    def __update_card_image(self):

        image = self.get_image(composed=False)
        x, y = self.get_pos()
        w, h = self.get_size()
        img = PNMImage(w, h, 4)
        parent_img = self.get_parent().get_image(composed=False)
        img.copy_sub_image(parent_img, 0, 0, x, y, w, h)
        img.blend_sub_image(image, 0, 0, 0, 0)
        self.get_card().copy_sub_image(self, img, w, h)

    def advance(self):

        if self._rate:
            self._progress = min(1., self._progress + self._rate)
            sizer_item = self.get_sizer_item()
            sizer_item.set_proportion(self._progress)
            sizer = sizer_item.get_sizer()
            space_item = sizer.get_item(1)
            space_item.set_proportion(1. - self._progress)
            sizer.set_min_size_stale()
            sizer.update_min_size()
            sizer.set_size(sizer.get_size())
            sizer.calculate_positions(sizer.get_pos())
            sizer.update_images()
            self.__update_card_image()


class ProgressDialog(Dialog):

    def __init__(self, message="", choices="cancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None, cancellable=True):

        if not cancellable:
            choices = choices.replace("cancel", "")
        elif on_cancel is None:
            on_cancel = lambda: Mgr.update_remotely("long_process_cancellation")

        title = "Please wait..."

        Dialog.__init__(self, title, choices, ok_alias, on_yes, on_no, on_cancel,
                        allow_escape=cancellable)

        client_sizer = self.get_client_sizer()
        borders = (50, 50, 30, 30)
        text = DialogMessageText(self, message)
        client_sizer.add(text, borders=borders, alignment="center_h")
        self._progress_bar = bar = ProgressBar(self)
        borders = (50, 50, 30, 0)
        client_sizer.add(bar.get_frame(), borders=borders, expand=True)

        self.finalize()

    def set_rate(self, rate):

        self._progress_bar.set_rate(rate)

    def advance(self):

        self._progress_bar.advance()

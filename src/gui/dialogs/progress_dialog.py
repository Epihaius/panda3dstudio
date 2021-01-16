from ..dialog import *


class ProgressBarFrame(Widget):

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["progress_bar"]["frame"]}

        Widget.__init__(self, "progress_bar_frame", parent, gfx_ids, has_mouse_region=False)

    def set_progress_bar(self, progress_bar):

        sizer = Sizer("horizontal")
        self.sizer = sizer
        gfx_id = Skin.atlas.gfx_ids["progress_bar"][""][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        l, r, b, t = borders = self.gfx_inner_borders
        h += b + t
        sizer.default_size = (Skin.options["progress_dialog_bar_width"], h)
        bar_sizer = Sizer("horizontal")
        sizer.add(bar_sizer, proportions=(1., 0.), borders=borders)
        bar_sizer.add(progress_bar)
        bar_sizer.add((0, 0), proportions=(1., 0.))


class ProgressBar(Widget):

    def __init__(self, dialog):

        frame = ProgressBarFrame(dialog)
        gfx_ids = {"": Skin.atlas.gfx_ids["progress_bar"][""]}

        Widget.__init__(self, "progress_bar", frame, gfx_ids, has_mouse_region=False)

        frame.set_progress_bar(self)

        self._rate = 0.
        self._progress = 0.

    @property
    def frame(self):

        return self.parent

    def set_rate(self, rate):

        if not self._rate:
            self._rate = rate

    def __update_card_image(self):

        image = self.get_image(composed=False)
        x, y = self.get_pos()
        w, h = self.get_size()
        img = PNMImage(w, h, 4)
        parent_img = self.parent.get_image(composed=False)
        img.copy_sub_image(parent_img, 0, 0, x, y, w, h)
        img.blend_sub_image(image, 0, 0, 0, 0)
        self.card.copy_sub_image(self, img, w, h)

    def advance(self):

        if self._rate:
            self._progress = min(1., self._progress + self._rate)
            sizer_cell = self.sizer_cell
            sizer_cell.proportions = (self._progress, 0.)
            sizer = sizer_cell.sizer
            space_cell = sizer.cells[1]
            space_cell.proportions = (1. - self._progress, 0.)
            sizer.set_min_size_stale()
            sizer.update_min_size()
            sizer.set_size(sizer.get_size())
            sizer.update_positions()
            sizer.update_images()
            self.__update_card_image()


class ProgressDialog(Dialog):

    def __init__(self, message="", choices="cancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None, cancellable=True):

        if not cancellable:
            choices = choices.replace("cancel", "")
        elif on_cancel is None:
            on_cancel = lambda: Mgr.update_remotely("long_process_cancellation")

        Dialog.__init__(self, "", choices, ok_alias, on_yes, on_no, on_cancel,
                        allow_escape=cancellable)

        widgets = Skin.layout.create(self, "progress")
        text_cell = widgets["placeholders"]["text"]
        bar_cell = widgets["placeholders"]["bar"]

        text_cell.object = DialogText(self, message, text_type="dialog_message")
        self._progress_bar = ProgressBar(self)
        bar_cell.object = self._progress_bar.frame

        self.finalize()

    def set_rate(self, rate):

        self._progress_bar.set_rate(rate)

    def advance(self):

        self._progress_bar.advance()

from ..dialog import *
import colorsys


class ColorDialog(Dialog):

    _clock = ClockObject()
    _rgb_range_id = "255"

    @classmethod
    def __set_rgb_range(cls, range_id, fields):

        cls._rgb_range_id = range_id
        value_range = (0., 255.) if range_id == "255" else (0., 1.)
        step = 1. if range_id == "255" else .001

        for field in fields:
            field.set_value_range(value_range)
            field.set_step(step)

    def __init__(self, title="", color=(1., 1., 1.), choices="okcancel", ok_alias="OK",
                 on_yes=None, on_no=None, on_cancel=None):

        def command():

            if on_yes:
                on_yes(self._new_color)

        Dialog.__init__(self, title, choices, ok_alias, command, on_no, on_cancel)

        widgets = Skin.layout.create(self, "color")
        self._controls = ctrls = {}
        self._fields = fields = widgets["fields"]
        simple_widgets = widgets["simple_widgets"]
        btn = widgets["buttons"]["add_new"]
        btn.command = self.__add_custom_color
        radio_btns = widgets["radiobutton_groups"]["rgb_range"]

        basic_colors = simple_widgets["basic_color_swatches"]
        basic_colors.command = self.__set_color
        self._custom_colors = custom_colors = simple_widgets["custom_color_swatches"]
        custom_colors.command = self.__set_color

        self._new_color = color
        self._new_color_swatch = new_swatch = simple_widgets["new_swatch"]
        self._current_color_swatch = cur_swatch = simple_widgets["current_swatch"]
        cur_swatch.color = color
        cur_swatch.command = self.__set_color
        ctrls["luminance"] = lum_control = simple_widgets["lum_control"]
        lum_control.command = self.__set_color
        ctrls["hue_sat"] = hue_sat_control = simple_widgets["hue_sat_control"]
        hue_sat_control.command = self.__set_main_luminance_color

        rgb_fields = []
        handler = self.__handle_color_component

        val_rng = (0., 255.) if self._rgb_range_id == "255" else (0., 1.)
        step = 1. if self._rgb_range_id == "255" else .001

        for value_id in ("red", "green", "blue"):
            field = fields[value_id]
            field.value_id = value_id
            field.set_value_handler(handler)
            field.set_value_range(val_rng, False, "float")
            field.set_step(step)
            rgb_fields.append(field)

        val_rng = (0., 1.)
        step = .001

        for value_id in ("hue", "sat", "lum"):
            field = fields[value_id]
            field.value_id = value_id
            field.set_value_handler(handler)
            field.set_value_range(val_rng, False, "float")
            field.set_step(step)

        command = lambda: self.__set_rgb_range("255", rgb_fields)
        radio_btns.set_button_command("255", command)
        command = lambda: self.__set_rgb_range("1", rgb_fields)
        radio_btns.set_button_command("1", command)
        radio_btns.set_selected_button(self._rgb_range_id)

        self.finalize()
        self.__set_color(color, update_gradients=True)

    def close(self, answer=""):

        self._controls = None
        self._fields = None
        self._custom_colors = None
        self._new_color_swatch = None
        self._current_color_swatch = None

        Dialog.close(self, answer)

    def __set_main_luminance_color(self, color, continuous=False, update_fields=False):

        self._controls["luminance"].set_main_color(color, continuous, update_fields)

    def __set_color(self, color, continuous=False, update_fields=True, update_gradients=False):

        self._new_color = color
        self._new_color_swatch.color = color
        fields = self._fields

        if fields:

            if continuous:
                if self._clock.real_time > .1:
                    self._clock.reset()
                else:
                    update_fields = False

            if update_fields:

                rgb_scale = 255. if self._rgb_range_id == "255" else 1.
                r, g, b = [c * rgb_scale for c in color]
                fields["red"].set_value(r)
                fields["green"].set_value(g)
                fields["blue"].set_value(b)
                h, l, s = colorsys.rgb_to_hls(*color)
                fields["hue"].set_value(h)
                fields["sat"].set_value(s)
                fields["lum"].set_value(l)

                if update_gradients:
                    lum_ctrl = self._controls["luminance"]
                    lum_ctrl.set_luminance(l)
                    r, g, b = colorsys.hls_to_rgb(h, .5, s)
                    lum_ctrl.set_main_color((r, g, b), continuous=False, update_fields=False)
                    self._controls["hue_sat"].set_hue_sat(h, s)

    def __handle_color_component(self, component_id, value, state="done"):

        fields = self._fields
        rgb_components = ["red", "green", "blue"]
        hsl_components = ["hue", "sat", "lum"]
        rgb_scale = 255. if self._rgb_range_id == "255" else 1.

        if component_id in rgb_components:

            r, g, b = [fields[c].get_value() / rgb_scale for c in rgb_components]
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            fields["hue"].set_value(h)
            fields["sat"].set_value(s)
            fields["lum"].set_value(l)
            self._controls["luminance"].set_luminance(l)
            r_, g_, b_ = colorsys.hls_to_rgb(h, .5, s)
            self._controls["luminance"].set_main_color((r_, g_, b_), continuous=False)
            self._controls["hue_sat"].set_hue_sat(h, s)

        else:

            h, s, l = [fields[c].get_value() for c in hsl_components]
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            fields["red"].set_value(r * rgb_scale)
            fields["green"].set_value(g * rgb_scale)
            fields["blue"].set_value(b * rgb_scale)

            if component_id == "lum":
                self._controls["luminance"].set_luminance(l)
            else:
                r_, g_, b_ = colorsys.hls_to_rgb(h, .5, s)
                self._controls["luminance"].set_main_color((r_, g_, b_), continuous=False)
                self._controls["hue_sat"].set_hue_sat(h, s)

        self._new_color = color = (r, g, b)
        self._new_color_swatch.color = color

    def __add_custom_color(self):

        self._custom_colors.add_swatch(self._new_color)

    def update_widget_positions(self):

        self._new_color_swatch.update_quad_pos()
        self._controls["luminance"].update_quad_pos()
        self._controls["hue_sat"].update_quad_pos()

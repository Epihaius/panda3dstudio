from ..base import *


class ZoomIndicator:

    def __init__(self):

        self._node = GD.viewport_origin.attach_new_node("zoom_indicator")
        self._node.set_alpha_scale(.5)
        cm = CardMaker("zoom_indicator_part")
        frame = (-16., 16., -16., 16.)
        cm.set_frame(*frame)
        cm.set_has_normals(False)
        ring = self._node.attach_new_node(cm.generate())
        ring.set_texture(Mgr.load_tex(GFX_PATH + "zoom_indic_ring.png"))
        ring.set_transparency(TransparencyAttrib.M_alpha)
        self._dot = self._node.attach_new_node(cm.generate())
        self._dot.set_texture(Mgr.load_tex(GFX_PATH + "zoom_indic_dot.png"))
        self._dot.set_transparency(TransparencyAttrib.M_alpha)
        region = MouseWatcherRegion("zoom_indicator_region", *frame)
        self._mouse_region = region
        GD.mouse_watcher.add_region(region)
        self._listener = listener = DirectObject()
        listener.accept("region_enter", self.__on_region_enter)
        listener.accept("region_leave", self.__on_region_leave)
        self._clock = ClockObject.get_global_clock()
        self._alpha = .5

        Mgr.accept("update_zoom_indicator", self.__update_dot_scale)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)

    def __update_dot_scale(self):

        cam = GD.cam

        if cam.lens_type == "persp":
            scale = (1. / -cam.origin.get_y()) ** .2
        else:
            target_scale = cam.target.get_sx()
            scale = (.0004 / max(.0004, min(100000., target_scale))) ** .13

        self._dot.set_scale(scale)

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]

        # the size of the zoom indicator ring is (24, 24) pixels
        x = 24. / w
        y = 24. / h
        self._mouse_region.frame = (-x, x, -y, y)

        self._node.set_pos(w * .5, 0., -h * .5)

    def __on_region_enter(self, *args):

        name = args[0].name

        if name == "zoom_indicator_region":
            Mgr.remove_task("fade_zoom_indicator")
            Mgr.add_task(self.__fade_out, "fade_zoom_indicator")

    def __on_region_leave(self, *args):

        name = args[0].name

        if name == "zoom_indicator_region":
            Mgr.remove_task("fade_zoom_indicator")
            Mgr.add_task(self.__fade_in, "fade_zoom_indicator")

    def __fade_out(self, task):

        self._alpha = max(0., min(.5, self._alpha - self._clock.get_dt()))
        self._node.set_alpha_scale(self._alpha)
        self._node.show() if self._alpha else self._node.hide()

        return task.done if self._alpha == 0. else task.cont

    def __fade_in(self, task):

        self._alpha = max(0., min(.5, self._alpha + self._clock.get_dt()))
        self._node.set_alpha_scale(self._alpha)
        self._node.show() if self._alpha else self._node.hide()

        return task.done if self._alpha == .5 else task.cont


MainObjects.add_class(ZoomIndicator)

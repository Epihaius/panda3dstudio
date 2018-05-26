from .base import *

MAX_TEX_SIZE = 4000  # TODO: make user-configurable


class ScrollThumb(Widget):

    def __init__(self, parent, pane, gfx_data, cull_bin, scroll_dir, inner_border_id):

        Widget.__init__(self, "scrollthumb", parent, gfx_data, "normal", stretch_dir="both")

        self._pane = pane
        self._dir = scroll_dir
        self._inner_border_id = inner_border_id
        sort = parent.get_sort() + 1
        self.get_mouse_region().set_sort(sort)
        self._tex = tex = Texture("scrollthumb")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        cm = CardMaker("scrollthumb")
        cm.set_frame(0., 1., -1., 0.)
        self._quad = quad = Mgr.get("gui_root").attach_new_node(cm.generate())
        quad.set_bin(cull_bin, sort)
        quad.set_texture(self._tex)
        quad.set_transparency(TransparencyAttrib.M_alpha)
        thickness = Skin["options"]["scrollthumb_thickness"]
        min_size = (0, thickness) if scroll_dir == "horizontal" else (thickness, 0)
        self.set_size(min_size, is_min=True)
        w, h = self.get_min_size()
        l_s, r_s, b_s, t_s = TextureAtlas["inner_borders"][inner_border_id]
        self.set_pos((l_s, t_s))
        size = (0, h + b_s + t_s) if scroll_dir == "horizontal" else (w + l_s + r_s, 0)
        parent.set_size(size, is_min=True)
        self._start_mouse_crd = self._mouse_crd = 0
        self._start_scroll_offset = self._scroll_offset = 0
        self._scroll_size = 0
        self._scrolling = False
        self._listener = DirectObject()
        self._listener.accept("gui_mouse1-up", self.on_left_up)

    def destroy(self):

        Widget.destroy(self)

        self._pane = None
        self._listener.ignore_all()
        self._listener = None
        self._quad.remove_node()
        self._quad = None

    def get_direction(self):

        return self._dir

    def get_quad(self):

        return self._quad

    def update_size(self):

        pane = self._pane
        d = self._dir
        dim = 0 if d == "horizontal" else 1
        size = pane.get_size()[dim]
        size_virt = pane.get_sizer().get_virtual_size()[dim]
        l, r, b, t = self.get_gfx_inner_borders()

        if d == "horizontal":
            border = l + r
        else:
            border = b + t

        if Skin["options"]["integrate_scrollbar_in_frame"]:
            l_f, r_f, b_f, t_f = pane.get_frame().get_gfx_inner_borders()
        else:
            l_f = r_f = b_f = t_f = 0

        l_s, r_s, b_s, t_s = TextureAtlas["inner_borders"][self._inner_border_id]

        if d == "horizontal":
            self._scroll_size = size_scroll = size + l_f + r_f - l_s - r_s - border
        else:
            self._scroll_size = size_scroll = size + b_f + t_f - b_s - t_s - border

        size_thumb = border + int(1. * size_scroll * min(1., 1. * size / size_virt))

        if d == "horizontal":
            self.set_size((size_thumb, 0))
        else:
            self.set_size((0, size_thumb))

    def update_offset(self):

        pane = self._pane
        d = self._dir
        dim = 0 if d == "horizontal" else 1
        size = pane.get_size()[dim]
        size_virt = pane.get_sizer().get_virtual_size()[dim]
        self._scroll_offset = offset = max(0, min(self._scroll_offset, size_virt - min(size_virt, size)))
        pane.update_scroll_offset(offset)

    def set_offset(self, offset):

        start_scroll_offset = self._scroll_offset
        self._scroll_offset = offset
        self.update_offset()
        self.update_pos()
        self.update_mouse_region_frames()
        pane = self._pane
        pane.update_mouse_watcher_frame()
        root_node = pane.get_widget_root_node()

        if self._dir == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - start_scroll_offset + self._scroll_offset)

    def get_offset(self):

        return self._scroll_offset

    def get_page_size(self):

        pane = self._pane
        d = self._dir
        dim = 0 if d == "horizontal" else 1

        return pane.get_size()[dim]

    def update_pos(self):

        x, y = self.get_pos(from_root=True)
        pane = self._pane
        d = self._dir
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.get_sizer().get_virtual_size()[dim]
        incr = int((1. * self._scroll_offset / size_virt) * self._scroll_size)

        if d == "horizontal":
            x += incr
        else:
            y += incr

        self._quad.set_x(x)
        self._quad.set_z(-y)

    def set_size(self, size, includes_borders=True, is_min=False):

        w, h = Widget.set_size(self, size, includes_borders, is_min)
        self._quad.set_scale(w, 1., h)

    def update_images(self):

        img = Widget.update_images(self)[self.get_state()]
        self._tex.load(img)

    def update_mouse_region_frames(self, exclude=""):

        x, y = self.get_pos()
        pane = self._pane
        d = self._dir
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.get_sizer().get_virtual_size()[dim]
        offset = int((1. * self._scroll_offset / size_virt) * self._scroll_size)
        # temporarily update the thumb position with the scroll offset
        self.set_pos((x + offset, y) if d == "horizontal" else (x, y + offset))
        Widget.update_mouse_region_frames(self, exclude)
        # restore the original thumb position
        self.set_pos((x, y))

    def update(self):

        start_scroll_offset = self._scroll_offset
        self.update_size()
        self.update_offset()
        self.update_pos()
        self.update_images()
        self.update_mouse_region_frames()
        root_node = self._pane.get_widget_root_node()

        if self._dir == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - start_scroll_offset + self._scroll_offset)

    def __scroll(self, task):

        d = self._dir
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.get_x() if d == "horizontal" else mouse_pointer.get_y()

        if mouse_crd == self._mouse_crd:
            return task.cont

        d_crd = mouse_crd - self._start_mouse_crd
        pane = self._pane
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.get_sizer().get_virtual_size()[dim]
        offset = int(1. * size_virt * d_crd / self._scroll_size)
        self._scroll_offset = self._start_scroll_offset + offset
        self.update_offset()
        self.update_pos()
        self._mouse_crd = mouse_crd

        return task.cont

    def on_enter(self):

        self.set_state("hilited")
        self.update_images()

    def on_leave(self):

        if not self._scrolling:
            self.set_state("normal")
            self.update_images()

    def on_left_down(self):

        Mgr.add_task(self.__scroll, "scroll")
        self._scrolling = True
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.get_x() if self._dir == "horizontal" else mouse_pointer.get_y()
        self._start_mouse_crd = self._mouse_crd = mouse_crd
        self._start_scroll_offset = self._scroll_offset

    def on_left_up(self):

        if not self._scrolling:
            return

        Mgr.remove_task("scroll")
        self._scrolling = False
        self.update_mouse_region_frames()
        pane = self._pane
        pane.update_mouse_watcher_frame()
        root_node = pane.get_widget_root_node()

        if self._dir == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + self._start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - self._start_scroll_offset + self._scroll_offset)

        if self.get_mouse_watcher().get_over_region() != self.get_mouse_region():
            self.on_leave()


class ScrollBar(Widget):

    def __init__(self, parent, pane, gfx_data, thumb_gfx_data, cull_bin, scroll_dir,
                 inner_border_id):

        Widget.__init__(self, "scrollbar", parent, gfx_data, stretch_dir="both")

        self._dir = scroll_dir
        self._sort = sort = parent.get_sort() + 1
        self.get_mouse_region().set_sort(sort)
        self._thumb = self._create_thumb(pane, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id)
        self._start_mouse_crd = 0
        self._start_scroll_offset = 0
        self._scrolling = False
        self._clicked = False
        self._listener = DirectObject()
        self._listener.accept("gui_mouse1-up", self.on_left_up)

    def _create_thumb(self, pane, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id):
        """ Override in derived class """

        return ScrollThumb(self, pane, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id)

    def destroy(self):

        self._listener.ignore_all()
        self._listener = None
        self._thumb.destroy()
        self._thumb = None

        Widget.destroy(self)

    def get_direction(self):

        return self._dir

    def get_sort(self):

        return self._sort

    def get_thumb(self):

        return self._thumb

    def set_pos(self, pos):

        Widget.set_pos(self, pos)
        self._thumb.update_pos()

    def update_images(self):

        if self.has_state(""):
            Widget.update_images(self)[""]

        self._thumb.update_images()

    def update_mouse_region_frames(self, exclude=""):

        Widget.update_mouse_region_frames(self, exclude)
        self._thumb.update_mouse_region_frames(exclude)

    def __scroll(self, task=None):

        d = self._dir
        thumb = self._thumb
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.get_x() if d == "horizontal" else mouse_pointer.get_y()
        quad = thumb.get_quad()
        crd = quad.get_x() if d == "horizontal" else -quad.get_z()
        thumb_size = quad.get_sx() if d == "horizontal" else quad.get_sz()
        page_size = thumb.get_page_size()
        offset = thumb.get_offset()

        if crd < mouse_crd < crd + thumb_size:
            return task.again if task else None

        if mouse_crd < crd:
            thumb.set_offset(offset - page_size)
        elif mouse_crd > crd + thumb_size:
            thumb.set_offset(offset + page_size)

        return task.again if task else None

    def __start_scrolling(self, task):

        Mgr.add_task(.1, self.__scroll, "scroll")
        self._scrolling = True

    def on_left_down(self):

        self.__scroll()
        Mgr.add_task(.3, self.__start_scrolling, "start_scrolling")
        self._clicked = True

    def on_left_up(self):

        if self._scrolling:
            Mgr.remove_task("scroll")
            self._scrolling = False
        elif self._clicked:
            Mgr.remove_task("start_scrolling")
            self._clicked = False


class ScrollPaneFrame(Widget):

    def __init__(self, parent, pane, gfx_data, bar_gfx_data, thumb_gfx_data, cull_bin,
                 scroll_dir, inner_border_id, has_mouse_region=True):

        Widget.__init__(self, "scroll_pane_frame", parent, gfx_data, stretch_dir="both",
                        has_mouse_region=has_mouse_region)

        self._pane = pane
        self._scrollbar = self._create_bar(pane, bar_gfx_data, thumb_gfx_data, cull_bin,
                                           scroll_dir, inner_border_id)
        sizer = Sizer("horizontal" if scroll_dir == "vertical" else "vertical")
        self.set_sizer(sizer)

    def _create_bar(self, pane, bar_gfx_data, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id):
        """ Override in derived class """

        return ScrollBar(self, pane, bar_gfx_data, thumb_gfx_data, cull_bin, scroll_dir,
                         inner_border_id)

    def setup(self, client_size=(0, 0), append_bar=True):

        scrollbar = self._scrollbar
        scroll_dir = scrollbar.get_direction()
        l, r, b, t = borders = self.get_gfx_inner_borders()
        w, h = client_size
        w += l + r
        h += b + t

        if scroll_dir == "vertical":

            w += scrollbar.get_min_size()[0]

            if Skin["options"]["integrate_scrollbar_in_frame"]:
                w -= r if append_bar else l

        else:

            h += scrollbar.get_min_size()[1]

            if Skin["options"]["integrate_scrollbar_in_frame"]:
                h -= b if append_bar else t

        default_size = (w, h)
        sizer = self.get_sizer()
        sizer.set_default_size(default_size)

        if append_bar:
            borders = (l, 0, b, t) if scroll_dir == "vertical" else (l, r, 0, t)
        else:
            borders = (0, r, b, t) if scroll_dir == "vertical" else (l, r, b, 0)

        if Skin["options"]["integrate_scrollbar_in_frame"]:
            bar_borders = None
        else:
            if append_bar:
                bar_borders = (0, r, b, t) if scroll_dir == "vertical" else (l, r, b, 0)
            else:
                bar_borders = (l, 0, b, t) if scroll_dir == "vertical" else (l, r, 0, t)

        if append_bar:
            sizer.add(self._pane, proportion=1., expand=True, borders=borders)
            sizer.add(scrollbar, expand=True, borders=bar_borders)
        else:
            sizer.add(scrollbar, expand=True, borders=bar_borders)
            sizer.add(self._pane, proportion=1., expand=True, borders=borders)

    def destroy(self):

        Widget.destroy(self)

        self._pane = None
        self._scrollbar = None

    def get_sort(self):

        return self.get_parent().get_sort()

    def get_scrollbar(self):

        return self._scrollbar


class ScrollPane(WidgetCard):

    def __init__(self, frame_parent, pane_id, scroll_dir, cull_bin, frame_gfx_data, bar_gfx_data,
                 thumb_gfx_data, bar_inner_border_id, bg_tex_id="", frame_client_size=(0, 0),
                 stretch_dir="", frame_has_mouse_region=True, append_scrollbar=True):

        frame = self._create_frame(frame_parent, scroll_dir, cull_bin, frame_gfx_data,
            bar_gfx_data, thumb_gfx_data, bar_inner_border_id, frame_has_mouse_region)
        WidgetCard.__init__(self, pane_id, frame, stretch_dir if stretch_dir else scroll_dir)
        frame.setup(frame_client_size, append_scrollbar)

        self._background_tex_id = bg_tex_id
        self._sort = frame.get_sort() + 1
        self._widget_root_node = NodePath("pane_widget_root")
        self._display_region = None
        self._scrollthumb = frame.get_scrollbar().get_thumb()
        self._subimg_index = -1
        self._subimg_x = 0
        self._subimg_y = 0
        self._subimg_w = 0
        self._subimg_h = 0
        sizer = ScrollSizer(scroll_dir)
        sizer.set_default_size((1, 1))
        self.set_sizer(sizer)

        self._mouse_region_mask = mask = MouseWatcherRegion("{}_mask".format(pane_id), 0., 0., 0., 0.)
        mask.set_suppress_flags(MouseWatcherRegion.SF_mouse_button)
        mask.set_sort(self._get_mask_sort())
        Mgr.get("mouse_watcher").add_region(mask)
        self._mouse_watcher = MouseWatcher(pane_id)
        GlobalData["mouse_watchers"].append(self._mouse_watcher)

        self._cull_bin = cull_bin
        gui_root = Mgr.get("gui_root")
        node_0 = gui_root.attach_new_node("scissor_node_0")
        node_1 = gui_root.attach_new_node("scissor_node_1")
        scissor_effect = ScissorEffect.make_node(True)
        scissor_effect = scissor_effect.add_point((0., 0., 0.), node_0)
        scissor_effect = scissor_effect.add_point((0., 0., 0.), node_1)
        self._scissor_effect = scissor_effect
        self._scissor_nodes = (node_0, node_1)

        self._listener = listener = DirectObject()
        listener.accept("{}_mouse1".format(pane_id), self.__on_left_down)
        listener.accept("{}_mouse1-up".format(pane_id), self.__on_left_up)
        listener.accept("{}_mouse3".format(pane_id), self.__on_right_down)
        listener.accept("{}_mouse3-up".format(pane_id), self.__on_right_up)
        listener.accept("{}_wheel_up".format(pane_id), self.__on_wheel_up)
        listener.accept("{}_wheel_down".format(pane_id), self.__on_wheel_down)
        listener.accept("{}_home".format(pane_id), self.__scroll_to_start)
        listener.accept("{}_end".format(pane_id), self.__scroll_to_end)
        listener.accept("{}_page_up".format(pane_id), self.__on_page_up)
        listener.accept("{}_page_down".format(pane_id), self.__on_page_down)
        listener.accept("{}_page_up-repeat".format(pane_id), self.__on_page_up)
        listener.accept("{}_page_down-repeat".format(pane_id), self.__on_page_down)

    def _create_frame(self, parent, scroll_dir, cull_bin, gfx_data, bar_gfx_data,
                      thumb_gfx_data, bar_inner_border_id, has_mouse_region=True):
        """ Override in derived class """

        return ScrollPaneFrame(parent, self, gfx_data, bar_gfx_data, thumb_gfx_data,
                               cull_bin, scroll_dir, bar_inner_border_id, has_mouse_region)

    def _get_mask_sort(self):
        """ Override in derived class """

        return self._sort + 8

    def _contents_needs_redraw(self):
        """ Override in derived class """

        return True

    def _copy_widget_images(self, pane_image): 
        """ Override in derived class """

        pass

    def _can_scroll(self):
        """ Override in derived class """

        return True

    def _finalize_mouse_watcher_frame_update(self):
        """ Override in derived class """

        pass

    def setup(self):

        base = Mgr.get("base")
        self._display_region = region = base.win.make_display_region(0., 1., 0., 1.)
        self.update_display_region()
        self.update_mouse_watcher_frame()
        mouse_watcher_node = self._mouse_watcher
        mouse_watcher_node.set_display_region(region)
        input_ctrl = base.mouseWatcher.get_parent()
        mw = input_ctrl.attach_new_node(mouse_watcher_node)
        mouse_watcher_node.set_enter_pattern("gui_region_enter")
        mouse_watcher_node.set_leave_pattern("gui_region_leave")
        pane_id = self.get_widget_type()
        btn_thrower_node = ButtonThrower("btn_thrower_{}".format(pane_id))
        btn_thrower_node.set_prefix("{}_".format(pane_id))
        btn_thrower_node.set_modifier_buttons(ModifierButtons())
        mw.attach_new_node(btn_thrower_node)

    def destroy(self):

        self._listener.ignore_all()
        self._listener = None
        Mgr.get("mouse_watcher").remove_region(self._mouse_region_mask)

        WidgetCard.destroy(self)

        GlobalData["mouse_watchers"].remove(self._mouse_watcher)
        NodePath(self._mouse_watcher).remove_node()
        self._mouse_watcher = None
        region = self._display_region
        self._display_region = None
        base = Mgr.get("base")
        base.win.remove_display_region(region)
        self._mouse_region_mask = None
        self._scissor_effect = None

        for node in self._scissor_nodes:
            node.remove_node()

        self._scissor_nodes = None
        self._widget_root_node.remove_node()
        self._widget_root_node = None
        self._scrollthumb = None

    def get_sort(self):

        return self._sort

    def get_frame(self):

        return self.get_parent()

    def get_scrollthumb(self):

        return self._scrollthumb

    def get_widget_root_node(self):

        return self._widget_root_node

    def get_display_region(self):

        return self._display_region

    def get_scissor_effect(self):

        return self._scissor_effect

    def reset_sub_image_index(self):

        self._subimg_index = -1

    def update_scroll_offset(self, scroll_offset):

        width, height = self.get_size()
        sizer = self.get_sizer()
        w_virt, h_virt = w_subimg, h_subimg = sizer.get_virtual_size()
        scroll_dir = sizer.get_stretch_dir()
        dim = 0 if scroll_dir == "horizontal" else 1
        max_size_exceeded = False

        # To prevent downscaling of the texture due to its size exceeding the maximum size allowed
        # by the graphics device, the PNMImage loaded into it must be a smaller sub-image, small
        # enough to avoid lag while scrolling but big enough to accommodate a large scroll pane.
        # Two consecutive sub-images overlap by a portion equal to the pane size;
        # the scroll offset divided by the size limit minus this overlap yields the index
        # of the sub-image that needs to be cut out of the complete image;
        # the position of this sub-image equals that index multiplied with the shortened size
        # limit, while its size equals the virtual size minus its position, or the size limit
        # itself if this is smaller.

        if scroll_dir == "horizontal":
            if w_virt > max(width, MAX_TEX_SIZE):
                index = scroll_offset // (MAX_TEX_SIZE - width)
                x_subimg = index * (MAX_TEX_SIZE - width)
                w_subimg = min(MAX_TEX_SIZE, w_virt - x_subimg)
                max_size_exceeded = True
        else:
            if h_virt > max(height, MAX_TEX_SIZE):
                index = scroll_offset // (MAX_TEX_SIZE - height)
                y_subimg = index * (MAX_TEX_SIZE - height)
                h_subimg = min(MAX_TEX_SIZE, h_virt - y_subimg)
                max_size_exceeded = True

        size = width if scroll_dir == "horizontal" else height
        size_subimg = w_subimg if scroll_dir == "horizontal" else h_subimg
        tex_scale = min(1., 1. * size / size_subimg)
        quad = self.get_quad()

        if max_size_exceeded:

            if self._subimg_index != index:

                w = w_subimg if scroll_dir == "horizontal" else width
                h = height if scroll_dir == "horizontal" else h_subimg
                x = x_subimg if scroll_dir == "horizontal" else 0
                y = 0 if scroll_dir == "horizontal" else y_subimg

                if self._image:
                    sub_image = PNMImage(w, h, 4)
                    sub_image.copy_sub_image(self._image, 0, 0, x, y, w, h)
                    self._tex.load(sub_image)

                sx = tex_scale if scroll_dir == "horizontal" else 1.
                sy = 1. if scroll_dir == "horizontal" else tex_scale
                quad.set_tex_scale(TextureStage.get_default(), sx, sy)
                self._subimg_x = x
                self._subimg_y = y
                self._subimg_w = w
                self._subimg_h = h
                self._subimg_index = index

            scroll_offset -= x_subimg if scroll_dir == "horizontal" else y_subimg

        else:

            self._subimg_index = -1

        if scroll_dir == "horizontal":
            tex_offset = (1. * scroll_offset / size) * tex_scale
            quad.set_tex_offset(TextureStage.get_default(), tex_offset, 0.)
        else:
            tex_offset = 1. - tex_scale - (1. * scroll_offset / size) * tex_scale
            quad.set_tex_offset(TextureStage.get_default(), 0., tex_offset)

    def set_size(self, size, is_min=False):

        WidgetCard.set_size(self, size, is_min)

        self._scrollthumb.update_size()
        self._scrollthumb.update_offset()

    def update_images(self):

        width, height = self.get_size()
        sizer = self.get_sizer()
        w_virt, h_virt = w_subimg, h_subimg = sizer.get_virtual_size()
        scroll_dir = sizer.get_stretch_dir()

        if self._subimg_index > -1:
            x_subimg = self._subimg_x
            y_subimg = self._subimg_y
            w_subimg = self._subimg_w
            h_subimg = self._subimg_h

        if scroll_dir == "horizontal":
            tex_offset = (self.get_quad().get_tex_offset(TextureStage.get_default())[0], 1.)
            tex_scale = (min(1., 1. * width / w_subimg), 1.)
        else:
            tex_offset = (1., self.get_quad().get_tex_offset(TextureStage.get_default())[1])
            tex_scale = (1., min(1., 1. * height / h_subimg))

        tex = self._tex

        if self._contents_needs_redraw():

            sizer.update_images()
            w = w_virt if scroll_dir == "horizontal" else width
            h = height if scroll_dir == "horizontal" else h_virt
            img = PNMImage(w, h, 4)

            if self._background_tex_id:

                x, y, w, h = TextureAtlas["regions"][self._background_tex_id]
                src_img = PNMImage(w, h, 4)
                src_img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)

                if min(w, h) > 1:
                    painter = PNMPainter(img)
                    fill = PNMBrush.make_image(src_img, 0, 0)
                    pen = PNMBrush.make_transparent()
                    painter.set_fill(fill)
                    painter.set_pen(pen)
                    painter.draw_rectangle(0, 0, w_virt, h_virt)
                else:
                    img.unfiltered_stretch_from(src_img)

            self._copy_widget_images(img)

            if self._subimg_index > -1:
                w = w_subimg if scroll_dir == "horizontal" else width
                h = height if scroll_dir == "horizontal" else h_subimg
                x = x_subimg if scroll_dir == "horizontal" else 0
                y = 0 if scroll_dir == "horizontal" else y_subimg
                sub_image = PNMImage(w, h, 4)
                sub_image.copy_sub_image(img, 0, 0, x, y, w, h)
                tex.load(sub_image)
            else:
                tex.load(img)

            self._image = img

        l = 0
        r = min(width, w_virt) if scroll_dir == "horizontal" else width
        b = -height if scroll_dir == "horizontal" else -min(height, h_virt)
        t = 0
        quad = self.create_quad((l, r, b, t))
        x, y = self.get_pos(from_root=True)
        quad.set_pos(x, 0, -y)
        quad.set_texture(tex)
        quad.set_bin(self._cull_bin, self._sort)
        quad.set_tex_offset(TextureStage.get_default(), *tex_offset)
        quad.set_tex_scale(TextureStage.get_default(), *tex_scale)

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        img = self._image

        if not img:
            return

        x, y = widget.get_pos(ref_node=self._widget_root_node)
        x += offset_x
        y += offset_y
        img.copy_sub_image(sub_image, x, y, 0, 0, width, height)

        if self._subimg_index > -1:
            width, height = self.get_size()
            scroll_dir = self.get_sizer().get_stretch_dir()
            w = self._subimg_w if scroll_dir == "horizontal" else width
            h = height if scroll_dir == "horizontal" else self._subimg_h
            x = self._subimg_x if scroll_dir == "horizontal" else 0
            y = 0 if scroll_dir == "horizontal" else self._subimg_y
            sub_image = PNMImage(w, h, 4)
            sub_image.copy_sub_image(img, 0, 0, x, y, w, h)
            self._tex.load(sub_image)
        else:
            self._tex.load(img)

    def update_mouse_region_frames(self, exclude="", recurse=True):

        sizer = self.get_sizer()
        scroll_dir = sizer.get_stretch_dir()
        w_virt, h_virt = sizer.get_virtual_size()
        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + (min(w, w_virt) if scroll_dir == "horizontal" else w)
        b = -y - (h if scroll_dir == "horizontal" else min(h, h_virt))
        t = -y
        self._mouse_region_mask.set_frame(l, r, b, t)

        if recurse:
            sizer.update_mouse_region_frames(exclude)

        self.update_mouse_watcher_frame()

        if self._display_region:
            self.update_display_region()

    def update_display_region(self):

        sizer = self.get_sizer()
        scroll_dir = sizer.get_stretch_dir()
        w_virt, h_virt = sizer.get_virtual_size()
        w_ref, h_ref = Mgr.get("window_size")
        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = 1. * x / w_ref
        r = 1. * (x + (min(w, w_virt) if scroll_dir == "horizontal" else w)) / w_ref
        b = 1. - 1. * (y + (h if scroll_dir == "horizontal" else min(h, h_virt))) / h_ref
        t = 1. - 1. * y / h_ref
        self._display_region.set_dimensions(l, r, b, t)

        # Update the nodes controlling the ScissorEffect so it keeps geometry of input fields
        # from being rendered outside of the display region.
        scissor_nodes = self._scissor_nodes
        scissor_nodes[0].set_pos(x, 0., -y)
        scissor_nodes[1].set_pos(x + w, 0., -y - h)

    def update_mouse_watcher_frame(self):

        sizer = self.get_sizer()
        scroll_dir = sizer.get_stretch_dir()
        w_virt, h_virt = sizer.get_virtual_size()
        width, height = self.get_size()

        if scroll_dir == "horizontal":
            l = self._scrollthumb.get_offset()
            r = l + min(width, w_virt)
            self._mouse_watcher.set_frame(l, r, -height, 0)
        else:
            t = -self._scrollthumb.get_offset()
            b = t - min(height, h_virt)
            self._mouse_watcher.set_frame(0, width, b, t)

        self._finalize_mouse_watcher_frame_update()

    def get_mouse_watcher(self):

        return self._mouse_watcher

    def update_quad_pos(self):

        WidgetCard.update_quad_pos(self)

        self._scrollthumb.update_pos()

    def update_widget_root_node(self):

        scroll_dir = self.get_sizer().get_stretch_dir()

        if scroll_dir == "horizontal":
            self._widget_root_node.set_x(-self._scrollthumb.get_offset())
        else:
            self._widget_root_node.set_z(self._scrollthumb.get_offset())

    def update_layout(self):

        self._subimg_index = -1
        sizer = self.get_parent().get_sizer()
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.calculate_positions()
        sizer.update_images()
        self.update_quad_pos()
        sizer.update_mouse_region_frames()
        self.update_widget_root_node()

    def __on_left_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name == "inputfield_mask":
            Mgr.do("accept_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_down()

    def __on_left_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_up()

    def __on_right_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name == "inputfield_mask":
            Mgr.do("reject_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_down()

    def __on_right_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.get_name()

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_up()

    def __on_wheel_up(self):

        if self._can_scroll():
            offset = self._scrollthumb.get_offset()
            self._scrollthumb.set_offset(offset - Skin["options"]["scroll_step"])

    def __on_wheel_down(self):

        if self._can_scroll():
            offset = self._scrollthumb.get_offset()
            self._scrollthumb.set_offset(offset + Skin["options"]["scroll_step"])

    def __on_page_up(self):

        if self._can_scroll():
            scrollthumb = self._scrollthumb
            offset = scrollthumb.get_offset()
            page_size = scrollthumb.get_page_size()
            scrollthumb.set_offset(offset - page_size)

    def __on_page_down(self):

        if self._can_scroll():
            scrollthumb = self._scrollthumb
            offset = scrollthumb.get_offset()
            page_size = scrollthumb.get_page_size()
            scrollthumb.set_offset(offset + page_size)

    def __scroll_to_start(self):

        ctrl_down = self.get_mouse_watcher().is_button_down(KeyboardButton.control())

        if ctrl_down and self._can_scroll():
            self._scrollthumb.set_offset(0)

    def __scroll_to_end(self):

        ctrl_down = self.get_mouse_watcher().is_button_down(KeyboardButton.control())

        if ctrl_down and self._can_scroll():
            sizer = self.get_sizer()
            scroll_dir = sizer.get_stretch_dir()
            offset = sizer.get_virtual_size()[0 if scroll_dir == "horizontal" else 1]
            self._scrollthumb.set_offset(offset)

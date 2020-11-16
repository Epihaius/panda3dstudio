from .base import *

MAX_TEX_SIZE = 4000  # TODO: make user-configurable


class ScrollThumb(Widget):

    def __init__(self, parent, pane, gfx_ids, cull_bin, scroll_dir, inner_border_id):

        Widget.__init__(self, "scrollthumb", parent, gfx_ids, "normal")

        self._pane = pane
        self.direction = scroll_dir
        self._inner_border_id = inner_border_id
        sort = parent.sort + 1
        self.mouse_region.sort = sort
        self.texture = tex = Texture("scrollthumb")
        tex.minfilter = SamplerState.FT_nearest
        tex.magfilter = SamplerState.FT_nearest
        cm = CardMaker("scrollthumb")
        cm.set_frame(0., 1., -1., 0.)
        self._quad = quad = Mgr.get("gui_root").attach_new_node(cm.generate())
        quad.set_bin(cull_bin, sort)
        quad.set_texture(self.texture)
        quad.set_transparency(TransparencyAttrib.M_alpha)
        thickness = Skin.options["scrollthumb_thickness"]
        min_size = (0, thickness) if scroll_dir == "horizontal" else (thickness, 0)
        self.set_size(min_size, is_min=True)
        w, h = self.min_size
        l_s, r_s, b_s, t_s = Skin.atlas.inner_borders[inner_border_id]
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
        self._quad.detach_node()
        self._quad = None

    @property
    def quad(self):

        return self._quad

    def update_size(self):

        pane = self._pane
        d = self.direction
        dim = 0 if d == "horizontal" else 1
        size = pane.get_size()[dim]
        size_virt = pane.virtual_size[dim]
        l, r, b, t = self.gfx_inner_borders

        if d == "horizontal":
            border = l + r
        else:
            border = b + t

        if Skin.options["integrate_scrollbar_in_frame"]:
            l_f, r_f, b_f, t_f = pane.frame.gfx_inner_borders
        else:
            l_f = r_f = b_f = t_f = 0

        l_s, r_s, b_s, t_s = Skin.atlas.inner_borders[self._inner_border_id]

        if d == "horizontal":
            self._scroll_size = size_scroll = size + l_f + r_f - l_s - r_s - border
        else:
            self._scroll_size = size_scroll = size + b_f + t_f - b_s - t_s - border

        size_thumb = border + int(size_scroll * min(1., size / size_virt))

        if d == "horizontal":
            self.set_size((size_thumb, 0))
        else:
            self.set_size((0, size_thumb))

    def get_offset(self):

        return self._scroll_offset

    def set_offset(self, offset):

        start_scroll_offset = self._scroll_offset
        self._scroll_offset = offset
        self.update_offset()
        self.update_pos()
        self.update_mouse_region_frames()
        pane = self._pane
        pane.update_mouse_watcher_frame()
        root_node = pane.widget_root_node

        if self.direction == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - start_scroll_offset + self._scroll_offset)

    def update_offset(self):

        pane = self._pane
        d = self.direction
        dim = 0 if d == "horizontal" else 1
        size = pane.get_size()[dim]
        size_virt = pane.virtual_size[dim]
        self._scroll_offset = offset = max(0, min(self._scroll_offset, size_virt - min(size_virt, size)))
        pane.update_scroll_offset(offset)

    def get_page_size(self):

        pane = self._pane
        d = self.direction
        dim = 0 if d == "horizontal" else 1

        return pane.get_size()[dim]

    def update_pos(self):

        x, y = self.get_pos(from_root=True)
        pane = self._pane
        d = self.direction
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.virtual_size[dim]
        incr = int((self._scroll_offset / size_virt) * self._scroll_size)

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

        img = Widget.update_images(self)[self.state]
        self.texture.load(img)

    def update_mouse_region_frames(self, exclude=""):

        x, y = self.get_pos()
        pane = self._pane
        d = self.direction
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.virtual_size[dim]
        offset = int((self._scroll_offset / size_virt) * self._scroll_size)
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
        root_node = self._pane.widget_root_node

        if self.direction == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - start_scroll_offset + self._scroll_offset)

    def __scroll(self, task):

        d = self.direction
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.x if d == "horizontal" else mouse_pointer.y

        if mouse_crd == self._mouse_crd:
            return task.cont

        d_crd = mouse_crd - self._start_mouse_crd
        pane = self._pane
        dim = 0 if d == "horizontal" else 1
        size_virt = pane.virtual_size[dim]
        offset = int(size_virt * d_crd / self._scroll_size)
        self._scroll_offset = self._start_scroll_offset + offset
        self.update_offset()
        self.update_pos()
        self._mouse_crd = mouse_crd

        return task.cont

    def on_enter(self):

        self.state = "hilited"
        self.update_images()

    def on_leave(self):

        if not self._scrolling:
            self.state = "normal"
            self.update_images()

    def on_left_down(self):

        Mgr.add_task(self.__scroll, "scroll")
        self._scrolling = True
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.x if self.direction == "horizontal" else mouse_pointer.y
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
        root_node = pane.widget_root_node

        if self.direction == "horizontal":
            x = root_node.get_x()
            root_node.set_x(x + self._start_scroll_offset - self._scroll_offset)
        else:
            z = root_node.get_z()
            root_node.set_z(z - self._start_scroll_offset + self._scroll_offset)

        if self.mouse_watcher.get_over_region() != self.mouse_region:
            self.on_leave()


class ScrollBar(Widget):

    def __init__(self, parent, pane, gfx_ids, thumb_gfx_ids, cull_bin, scroll_dir, inner_border_id):

        Widget.__init__(self, "scrollbar", parent, gfx_ids)

        self.direction = scroll_dir
        self.sort = sort = parent.sort + 1
        self.mouse_region.sort = sort
        self._thumb = self._create_thumb(pane, thumb_gfx_ids, cull_bin, scroll_dir, inner_border_id)
        self._start_mouse_crd = 0
        self._start_scroll_offset = 0
        self._scrolling = False
        self._clicked = False
        self._listener = DirectObject()
        self._listener.accept("gui_mouse1-up", self.on_left_up)

    def _create_thumb(self, pane, thumb_gfx_ids, cull_bin, scroll_dir, inner_border_id):
        """ Override in derived class """

        return ScrollThumb(self, pane, thumb_gfx_ids, cull_bin, scroll_dir, inner_border_id)

    def destroy(self):

        self._listener.ignore_all()
        self._listener = None
        self._thumb.destroy()
        self._thumb = None

        Widget.destroy(self)

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

        d = self.direction
        thumb = self._thumb
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_crd = mouse_pointer.x if d == "horizontal" else mouse_pointer.y
        quad = thumb.quad
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

    def __init__(self, parent, pane, gfx_ids, bar_gfx_ids, thumb_gfx_ids, cull_bin,
                 scroll_dir, inner_border_id, has_mouse_region=True):

        Widget.__init__(self, "scroll_pane_frame", parent, gfx_ids,
                        has_mouse_region=has_mouse_region)

        self._pane = pane
        self._scrollbar = self._create_bar(pane, bar_gfx_ids, thumb_gfx_ids, cull_bin,
                                           scroll_dir, inner_border_id)
        sizer = Sizer("horizontal" if scroll_dir == "vertical" else "vertical")
        self.sizer = sizer

    @property
    def sort(self):

        return self.parent.sort

    def _create_bar(self, pane, bar_gfx_ids, thumb_gfx_ids, cull_bin, scroll_dir, inner_border_id):
        """ Override in derived class """

        return ScrollBar(self, pane, bar_gfx_ids, thumb_gfx_ids, cull_bin, scroll_dir,
                         inner_border_id)

    def setup(self, client_size=(0, 0), append_bar=True):

        scrollbar = self._scrollbar
        scroll_dir = scrollbar.direction
        l, r, b, t = borders = self.gfx_inner_borders
        w, h = client_size
        w += l + r
        h += b + t

        if scroll_dir == "vertical":

            w += scrollbar.min_size[0]

            if Skin.options["integrate_scrollbar_in_frame"]:
                w -= r if append_bar else l

        else:

            h += scrollbar.min_size[1]

            if Skin.options["integrate_scrollbar_in_frame"]:
                h -= b if append_bar else t

        default_size = (w, h)
        sizer = self.sizer
        sizer.default_size = default_size

        if append_bar:
            borders = (l, 0, b, t) if scroll_dir == "vertical" else (l, r, 0, t)
        else:
            borders = (0, r, b, t) if scroll_dir == "vertical" else (l, r, b, 0)

        if Skin.options["integrate_scrollbar_in_frame"]:
            bar_borders = None
        else:
            if append_bar:
                bar_borders = (0, r, b, t) if scroll_dir == "vertical" else (l, r, b, 0)
            else:
                bar_borders = (l, 0, b, t) if scroll_dir == "vertical" else (l, r, 0, t)

        if append_bar:
            sizer.add(self._pane, (1., 1.), ("expand", "expand"), borders)
            sizer.add(scrollbar, alignments=("expand", "expand"), borders=bar_borders)
        else:
            sizer.add(scrollbar, alignments=("expand", "expand"), borders=bar_borders)
            sizer.add(self._pane, (1., 1.), ("expand", "expand"), borders)

    def destroy(self):

        Widget.destroy(self)

        self._pane = None
        self._scrollbar = None

    def get_scrollbar(self):

        return self._scrollbar


class ScrollPane(WidgetCard):

    def __init__(self, frame_parent, pane_id, scroll_dir, cull_bin, frame_gfx_ids, bar_gfx_ids,
                 thumb_gfx_ids, bar_inner_border_id, bg_tex_id="", frame_client_size=(0, 0),
                 frame_has_mouse_region=True, append_scrollbar=True):

        frame = self._create_frame(frame_parent, scroll_dir, cull_bin, frame_gfx_ids,
            bar_gfx_ids, thumb_gfx_ids, bar_inner_border_id, frame_has_mouse_region)

        WidgetCard.__init__(self, pane_id, frame)

        sizer = Sizer(scroll_dir)
        self.sizer = sizer
        sizer.default_size = (1, 1)

        frame.setup(frame_client_size, append_scrollbar)

        self._background_tex_id = bg_tex_id
        self.sort = frame.sort + 1
        self.widget_root_node = NodePath("pane_widget_root")
        self.display_region = None
        self.scrollthumb = frame.get_scrollbar().get_thumb()
        self._subimg_index = -1
        self._subimg_x = 0
        self._subimg_y = 0
        self._subimg_w = 0
        self._subimg_h = 0

        self._mouse_region_mask = mask = MouseWatcherRegion(f"{pane_id}_mask", 0., 0., 0., 0.)
        mask.suppress_flags = MouseWatcherRegion.SF_mouse_button
        mask.sort = self._get_mask_sort()
        Mgr.get("mouse_watcher").add_region(mask)
        self._mouse_watcher = MouseWatcher(pane_id)
        self._mouse_watcher_np = None
        GD["mouse_watchers"].append(self._mouse_watcher)

        self._cull_bin = cull_bin
        gui_root = Mgr.get("gui_root")
        node_0 = gui_root.attach_new_node("scissor_node_0")
        node_1 = gui_root.attach_new_node("scissor_node_1")
        scissor_effect = ScissorEffect.make_node(True)
        scissor_effect = scissor_effect.add_point((0., 0., 0.), node_0)
        scissor_effect = scissor_effect.add_point((0., 0., 0.), node_1)
        self.scissor_effect = scissor_effect
        self._scissor_nodes = (node_0, node_1)

        self._listener = listener = DirectObject()
        listener.accept(f"{pane_id}_mouse1", self.__on_left_down)
        listener.accept(f"{pane_id}_mouse1-up", self.__on_left_up)
        listener.accept(f"{pane_id}_mouse3", self.__on_right_down)
        listener.accept(f"{pane_id}_mouse3-up", self.__on_right_up)
        listener.accept(f"{pane_id}_wheel_up", self.__on_wheel_up)
        listener.accept(f"{pane_id}_wheel_down", self.__on_wheel_down)
        listener.accept(f"{pane_id}_home", self.__scroll_to_start)
        listener.accept(f"{pane_id}_end", self.__scroll_to_end)
        listener.accept(f"{pane_id}_page_up", self.__on_page_up)
        listener.accept(f"{pane_id}_page_down", self.__on_page_down)
        listener.accept(f"{pane_id}_page_up-repeat", self.__on_page_up)
        listener.accept(f"{pane_id}_page_down-repeat", self.__on_page_down)

    def _create_frame(self, parent, scroll_dir, cull_bin, gfx_ids, bar_gfx_ids,
                      thumb_gfx_ids, bar_inner_border_id, has_mouse_region=True):
        """ Override in derived class """

        return ScrollPaneFrame(parent, self, gfx_ids, bar_gfx_ids, thumb_gfx_ids,
                               cull_bin, scroll_dir, bar_inner_border_id, has_mouse_region)

    @property
    def frame(self):

        return self.parent

    def _get_mask_sort(self):
        """ Override in derived class """

        return self.sort + 8

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

        self.display_region = region = GD.window.make_display_region(0., 1., 0., 1.)
        GD.window.remove_display_region(region)
        self.update_display_region()
        self.update_mouse_watcher_frame()
        mouse_watcher_node = self._mouse_watcher
        mouse_watcher_node.set_display_region(region)
        input_ctrl = GD.showbase.mouseWatcher.parent
        self._mouse_watcher_np = mw = input_ctrl.attach_new_node(mouse_watcher_node)
        mouse_watcher_node.set_enter_pattern("gui_region_enter")
        mouse_watcher_node.set_leave_pattern("gui_region_leave")
        pane_id = self.widget_type
        btn_thrower_node = ButtonThrower(f"btn_thrower_{pane_id}")
        btn_thrower_node.prefix = f"{pane_id}_"
        btn_thrower_node.modifier_buttons = ModifierButtons()
        mw.attach_new_node(btn_thrower_node)

    def destroy(self):

        self._listener.ignore_all()
        self._listener = None
        Mgr.get("mouse_watcher").remove_region(self._mouse_region_mask)

        WidgetCard.destroy(self)

        GD["mouse_watchers"].remove(self._mouse_watcher)
        self._mouse_watcher_np.detach_node()
        self._mouse_watcher_np = None
        self._mouse_watcher = None
        self.display_region = None
        self._mouse_region_mask = None
        self.scissor_effect = None

        for node in self._scissor_nodes:
            node.detach_node()

        self._scissor_nodes = None
        self.widget_root_node.detach_node()
        self.widget_root_node = None
        self.scrollthumb = None

    @property
    def min_size(self):

        min_size = list(self.sizer.min_size)
        min_size[self.sizer.prim_dim] = 0

        return tuple(min_size)

    @property
    def virtual_size(self):

        w_min, h_min = self.sizer.min_size

        return (max(1, w_min), max(1, h_min))

    @virtual_size.setter
    def virtual_size(self, size):

        w_d, h_d = self.sizer.default_size
        w, h = size
        w = max(w, w_d)
        h = max(h, h_d)
        self.sizer.min_size = (w, h)

    def reset_sub_image_index(self):

        self._subimg_index = -1

    def update_scroll_offset(self, scroll_offset):

        width, height = self.get_size()
        w_virt, h_virt = w_subimg, h_subimg = self.virtual_size
        scroll_dir = self.sizer.prim_dir
        max_size_exceeded = False

        # To prevent downscaling of the texture due to its size exceeding the maximum size allowed
        # by the graphics device, the PNMImage loaded into it must be a smaller sub-image, small
        # enough to avoid lag while scrolling but big enough to accommodate a large scroll pane.
        # Two consecutive sub-images overlap by a portion equal to the pane size;
        # the scroll offset divided by the size limit minus this overlap yields the index
        # of the sub-image that needs to be cut out of the complete image;
        # the position of this sub-image equals that index multiplied by the shortened size
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
        tex_scale = min(1., size / size_subimg)
        quad = self.quad

        if max_size_exceeded:

            if self._subimg_index != index:

                w = w_subimg if scroll_dir == "horizontal" else width
                h = height if scroll_dir == "horizontal" else h_subimg
                x = x_subimg if scroll_dir == "horizontal" else 0
                y = 0 if scroll_dir == "horizontal" else y_subimg

                if self._image:
                    sub_image = PNMImage(w, h, 4)
                    sub_image.copy_sub_image(self._image, 0, 0, x, y, w, h)
                    self.texture.load(sub_image)

                sx = tex_scale if scroll_dir == "horizontal" else 1.
                sy = 1. if scroll_dir == "horizontal" else tex_scale
                quad.set_tex_scale(TextureStage.default, sx, sy)
                self._subimg_x = x
                self._subimg_y = y
                self._subimg_w = w
                self._subimg_h = h
                self._subimg_index = index

            scroll_offset -= x_subimg if scroll_dir == "horizontal" else y_subimg

        else:

            self._subimg_index = -1

        if scroll_dir == "horizontal":
            tex_offset = (scroll_offset / size) * tex_scale
            quad.set_tex_offset(TextureStage.default, tex_offset, 0.)
        else:
            tex_offset = 1. - tex_scale - (scroll_offset / max(1, size)) * tex_scale
            quad.set_tex_offset(TextureStage.default, 0., tex_offset)

    def set_size(self, size, is_min=False):

        WidgetCard.set_size(self, size, is_min)

        self.scrollthumb.update_size()
        self.scrollthumb.update_offset()

    def get_size(self):

        return self._size

    def update_images(self):

        width, height = self.get_size()
        w_virt, h_virt = w_subimg, h_subimg = self.virtual_size
        sizer = self.sizer
        scroll_dir = sizer.prim_dir

        if self._subimg_index > -1:
            x_subimg = self._subimg_x
            y_subimg = self._subimg_y
            w_subimg = self._subimg_w
            h_subimg = self._subimg_h

        if scroll_dir == "horizontal":
            tex_offset = (self.quad.get_tex_offset(TextureStage.default)[0], 1.)
            tex_scale = (min(1., width / w_subimg), 1.)
        else:
            tex_offset = (1., self.quad.get_tex_offset(TextureStage.default)[1])
            tex_scale = (1., min(1., height / h_subimg))

        tex = self.texture

        if self._contents_needs_redraw():

            sizer.update_images()
            w = w_virt if scroll_dir == "horizontal" else width
            h = height if scroll_dir == "horizontal" else h_virt
            img = PNMImage(w, h, 4)

            if self._background_tex_id:

                x, y, w, h = Skin.atlas.regions[self._background_tex_id]
                src_img = PNMImage(w, h, 4)
                src_img.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)

                if min(w, h) > 1:
                    painter = PNMPainter(img)
                    fill = PNMBrush.make_image(src_img, 0, 0)
                    pen = PNMBrush.make_transparent()
                    painter.fill = fill
                    painter.pen = pen
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
        quad.set_bin(self._cull_bin, self.sort)
        quad.set_tex_offset(TextureStage.default, *tex_offset)
        quad.set_tex_scale(TextureStage.default, *tex_scale)

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        img = self._image

        if not img:
            return

        x, y = widget.get_pos(ref_node=self.widget_root_node)
        x += offset_x
        y += offset_y
        img.copy_sub_image(sub_image, x, y, 0, 0, width, height)

        if self._subimg_index > -1:
            width, height = self.get_size()
            scroll_dir = self.sizer.prim_dir
            w = self._subimg_w if scroll_dir == "horizontal" else width
            h = height if scroll_dir == "horizontal" else self._subimg_h
            x = self._subimg_x if scroll_dir == "horizontal" else 0
            y = 0 if scroll_dir == "horizontal" else self._subimg_y
            sub_image = PNMImage(w, h, 4)
            sub_image.copy_sub_image(img, 0, 0, x, y, w, h)
            self.texture.load(sub_image)
        else:
            self.texture.load(img)

    def update_mouse_region_frames(self, exclude="", recurse=True):

        sizer = self.sizer
        scroll_dir = sizer.prim_dir
        w_virt, h_virt = self.virtual_size
        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x
        r = x + (min(w, w_virt) if scroll_dir == "horizontal" else w)
        b = -y - (h if scroll_dir == "horizontal" else min(h, h_virt))
        t = -y
        self._mouse_region_mask.frame = (l, r, b, t)

        if recurse:
            sizer.update_mouse_region_frames(exclude)

        self.update_mouse_watcher_frame()

        if self.display_region:
            self.update_display_region()

    def update_display_region(self):

        scroll_dir = self.sizer.prim_dir
        w_virt, h_virt = self.virtual_size
        w_ref, h_ref = Mgr.get("window_size")
        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)
        l = x / w_ref
        r = (x + (min(w, w_virt) if scroll_dir == "horizontal" else w)) / w_ref
        b = 1. - (y + (h if scroll_dir == "horizontal" else min(h, h_virt))) / h_ref
        t = 1. - y / h_ref
        self.display_region.dimensions = (l, r, b, t)

        # Update the nodes controlling the ScissorEffect so it keeps geometry of input fields
        # from being rendered outside of the display region.
        scissor_nodes = self._scissor_nodes
        scissor_nodes[0].set_pos(x, 0., -y)
        scissor_nodes[1].set_pos(x + w, 0., -y - h)

    def update_mouse_watcher_frame(self):

        scroll_dir = self.sizer.prim_dir
        w_virt, h_virt = self.virtual_size
        width, height = self.get_size()

        if scroll_dir == "horizontal":
            l = self.scrollthumb.get_offset()
            r = l + min(width, w_virt)
            self._mouse_watcher.set_frame(l, r, -height, 0)
        else:
            t = -self.scrollthumb.get_offset()
            b = t - min(height, h_virt)
            self._mouse_watcher.set_frame(0, width, b, t)

        self._finalize_mouse_watcher_frame_update()

    @property
    def mouse_watcher(self):

        return self._mouse_watcher

    def get_mouse_watcher_nodepath(self):

        return self._mouse_watcher_np

    def update_quad_pos(self):

        WidgetCard.update_quad_pos(self)

        self.scrollthumb.update_pos()

    def update_widget_root_node(self):

        scroll_dir = self.sizer.prim_dir

        if scroll_dir == "horizontal":
            self.widget_root_node.set_x(-self.scrollthumb.get_offset())
        else:
            self.widget_root_node.set_z(self.scrollthumb.get_offset())

    def update_layout(self):

        self._subimg_index = -1
        sizer = self.parent.sizer
        size = sizer.update_min_size()
        sizer.set_size(size)
        sizer.update_positions()
        sizer.update_images()
        self.update_quad_pos()
        sizer.update_mouse_region_frames()
        self.update_widget_root_node()

    def __on_left_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.name

        if name == "inputfield_mask":
            Mgr.do("accept_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_down()

    def __on_left_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.name

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_left_up()

    def __on_right_down(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.name

        if name == "inputfield_mask":
            Mgr.do("reject_field_input")
        elif name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_down()

    def __on_right_up(self):

        region = self._mouse_watcher.get_over_region()

        if not region:
            return

        name = region.name

        if name.startswith("widget_"):
            widget_id = int(name.replace("widget_", ""))
            Widget.registry[widget_id].on_right_up()

    def __on_wheel_up(self):

        if self._can_scroll():
            offset = self.scrollthumb.get_offset()
            self.scrollthumb.set_offset(offset - Skin.options["scroll_step"])

    def __on_wheel_down(self):

        if self._can_scroll():
            offset = self.scrollthumb.get_offset()
            self.scrollthumb.set_offset(offset + Skin.options["scroll_step"])

    def __on_page_up(self):

        if self._can_scroll():
            scrollthumb = self.scrollthumb
            offset = scrollthumb.get_offset()
            page_size = scrollthumb.get_page_size()
            scrollthumb.set_offset(offset - page_size)

    def __on_page_down(self):

        if self._can_scroll():
            scrollthumb = self.scrollthumb
            offset = scrollthumb.get_offset()
            page_size = scrollthumb.get_page_size()
            scrollthumb.set_offset(offset + page_size)

    def __scroll_to_start(self):

        ctrl_down = self._mouse_watcher.is_button_down("control")

        if ctrl_down and self._can_scroll():
            self.scrollthumb.set_offset(0)

    def __scroll_to_end(self):

        ctrl_down = self._mouse_watcher.is_button_down("control")

        if ctrl_down and self._can_scroll():
            sizer = self.sizer
            scroll_dir = sizer.prim_dir
            offset = self.virtual_size[0 if scroll_dir == "horizontal" else 1]
            self.scrollthumb.set_offset(offset)

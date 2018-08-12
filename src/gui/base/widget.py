from .base import *
from .mgr import GUIManager as Mgr


class Widget(object):

    registry = {}
    _count = 0

    def __init__(self, widget_type, parent, gfx_data, initial_state="", stretch_dir="",
                 hidden=False, has_mouse_region=True):

        self._type = "widget"
        self._widget_type = widget_type
        self._parent = parent
        self._node = parent.get_node().attach_new_node("widget") if parent else NodePath("widget")
        self._gfx_data = gfx_data
        self._current_state = initial_state
        self._stretch_dir = stretch_dir
        self._is_hidden = hidden or not parent
        self._is_contents_hidden = False
        self._is_enabled = True
        self._is_always_enabled = False
        self._disablers = {}
        self._image_offset = (0, 0)
        self._images = {}

        tex_atlas_regions = TextureAtlas["regions"]
        h_sizes = []
        v_sizes = []

        for parts in gfx_data.values():

            if parts:

                for part_id in parts[0]:
                    x, y, w, h = tex_atlas_regions[part_id]
                    h_sizes.append(w)

                for part_row in parts:
                    x, y, w, h = tex_atlas_regions[part_row[0]]
                    v_sizes.append(h)

                break

        w = sum(h_sizes)
        h = sum(v_sizes)

        if stretch_dir in ("both", "horizontal"):
            index = len(h_sizes) // 2
            w -= h_sizes[index] if index else 0
            border_left = sum(h_sizes[:index])
            border_right = sum(h_sizes[index+1:])
        else:
            border_left = border_right = 0

        if stretch_dir in ("both", "vertical"):
            index = len(v_sizes) // 2
            h -= v_sizes[index] if index else 0
            border_bottom = sum(v_sizes[index+1:])
            border_top = sum(v_sizes[:index])
        else:
            border_bottom = border_top = 0

        self._size = self._min_size = self._gfx_size = (w, h)
        self._sizer = None
        self._sizer_item = None
        # inner borders are derived from the widget graphics
        self._gfx_inner_borders = (border_left, border_right, border_bottom, border_top)
        # custom inner borders are specified by the user in the texture atlas;
        # these are offsets within the mouse region
        self._inner_borders = (0, 0, 0, 0)
        # the outer borders are specified by the user in the texture atlas;
        # these are used to accommodate a graphics border around the widget (i.e. outside of
        # the mouse region)
        self._outer_borders = (0, 0, 0, 0)

        self._widget_id = Widget._count
        Widget._count += 1

        if has_mouse_region:
            self._mouse_region = MouseWatcherRegion("widget_{:d}".format(self._widget_id), 0., 0., 0., 0.)
            if parent and not parent.is_hidden() and not hidden:
                self.get_mouse_watcher().add_region(self._mouse_region)
        else:
            self._mouse_region = None

        Widget.registry[self._widget_id] = self

    def destroy(self):

        if self._widget_id not in Widget.registry:
            return False

        if self._node:
            self._node.remove_node()
            self._node = None

        if self._sizer:
            self._sizer.destroy()
            self._sizer = None

        self._sizer_item = None

        if self._parent:

            if self._mouse_region:
                self.get_mouse_watcher().remove_region(self._mouse_region)
                self._mouse_region = None

            self._parent = None

        self._disablers = {}

        del Widget.registry[self._widget_id]

        return True

    def get_type(self):

        return self._type

    def set_widget_type(self, widget_type):

        self._widget_type = widget_type

    def get_widget_type(self):

        return self._widget_type

    def get_ancestor(self, widget_type):

        if self._widget_type == widget_type:
            return self

        if self._parent:
            return self._parent.get_ancestor(widget_type)

    def get_widget_id(self):

        return self._widget_id

    def set_parent(self, parent, show=True):

        if parent:

            self._parent = parent
            self._node.reparent_to(parent.get_node())

            if show:
                self.show()

        else:

            self._node.detach_node()
            self.hide()
            self._parent = parent

    def get_parent(self):

        return self._parent

    def get_card(self):

        return self._parent.get_card()

    def get_gfx_inner_borders(self):

        return self._gfx_inner_borders

    def set_inner_borders(self, borders):

        self._inner_borders = borders

    def get_inner_borders(self):

        return self._inner_borders

    def set_outer_borders(self, borders):

        self._outer_borders = borders

    def get_outer_borders(self):

        return self._outer_borders

    def get_mouse_region(self):

        return self._mouse_region

    def get_node(self):

        return self._node

    def has_state(self, state):

        return state in self._gfx_data

    def set_state(self, state):

        if state in self._gfx_data:
            self._current_state = state

    def get_state(self):

        return self._current_state

    def set_pos(self, pos):

        x, y = pos
        self.get_node().set_pos(x, 0, -y)

    def get_pos(self, ref_node=None, from_root=False):

        node = self.get_node()

        if ref_node:
            x, y, z = node.get_pos(ref_node)
        elif from_root:
            x, y, z = node.get_pos(node.get_top())
        else:
            x, y, z = node.get_pos(self.get_parent().get_node())

        y = -z

        return (int(x), int(y))

    def set_sizer(self, sizer):

        if sizer:
            sizer.set_owner(self)

        self._sizer = sizer

    def get_sizer(self):

        return self._sizer

    def set_sizer_item(self, sizer_item):

        self._sizer_item = sizer_item

    def get_sizer_item(self):

        return self._sizer_item

    def get_stretch_dir(self):

        return self._stretch_dir

    def get_min_size(self, ignore_sizer=False):

        if ignore_sizer:
            return self._min_size

        return self._sizer.get_min_size() if self._sizer else self._min_size

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = size
        w_gfx, h_gfx = self._gfx_size
        l, r, b, t = self._gfx_inner_borders
        borders_h = l + r
        borders_v = b + t

        if not includes_borders:
            w_gfx -= borders_h
            h_gfx -= borders_v

        width = max(w_gfx, width)
        height = max(h_gfx, height)

        if is_min:
            w_new, h_new = width, height
        else:
            w_new, h_new = self.get_min_size()
            width, height = (max(w_new, width), max(h_new, height))

        if self._stretch_dir in ("both", "horizontal"):
            if includes_borders:
                w_new = max(width, borders_h)
            else:
                w_new = width + borders_h

        if self._stretch_dir in ("both", "vertical"):
            if includes_borders:
                h_new = max(height, borders_v)
            else:
                h_new = height + borders_v

        new_size = (w_new, h_new)

        if self._sizer:
            self._sizer.set_size(new_size)

        self._size = new_size

        if is_min:
            self._min_size = new_size

        return new_size

    def get_size(self):

        return self._sizer.get_size() if self._sizer else self._size

    def update_images(self, recurse=True, size=None):

        width, height = self.get_size() if size is None else size

        if not (width and height):
            return

        tex_atlas = TextureAtlas["image"]
        tex_atlas_regions = TextureAtlas["regions"]
        images = self._images
        l, r, b, t = self._gfx_inner_borders
        borders_h = l + r
        borders_v = b + t
        stretch_dir = self._stretch_dir

        def create_center_image(x, y, width, height, scaled_width, scaled_height):

            center_img = PNMImage(width, height, 4)
            center_img.copy_sub_image(tex_atlas, 0, 0, x, y, width, height)
            scaled_img = PNMImage(scaled_width, scaled_height, 4)

            if min(width, height) > 1:
                painter = PNMPainter(scaled_img)
                fill = PNMBrush.make_image(center_img, 0, 0)
                pen = PNMBrush.make_transparent()
                painter.set_fill(fill)
                painter.set_pen(pen)
                painter.draw_rectangle(0, 0, scaled_width, scaled_height)
            else:
                scaled_img.unfiltered_stretch_from(center_img)

            return scaled_img

        for state, part_rows in self._gfx_data.items():

            if not part_rows:
                images[state] = None
                continue

            img = PNMImage(width, height, 4)
            images[state] = img

            offset_y = 0
            i_middle = len(part_rows) // 2

            for i, part_row in enumerate(part_rows):

                j_middle = len(part_row) // 2
                offset_x = 0

                for j, part_id in enumerate(part_row):

                    x, y, w, h = tex_atlas_regions[part_id]

                    if stretch_dir == "both" and i == i_middle and j == j_middle:
                        scaled_w = width - borders_h
                        scaled_h = height - borders_v
                        center_img = create_center_image(x, y, w, h, scaled_w, scaled_h)
                        img.copy_sub_image(center_img, offset_x, offset_y, 0, 0)
                        w = scaled_w
                        h = scaled_h
                    elif stretch_dir in ("both", "horizontal") and j == j_middle:
                        scaled_w = width - borders_h
                        center_img = create_center_image(x, y, w, h, scaled_w, h)
                        img.copy_sub_image(center_img, offset_x, offset_y, 0, 0)
                        w = scaled_w
                    elif stretch_dir in ("both", "vertical") and i == i_middle:
                        scaled_h = height - borders_v
                        center_img = create_center_image(x, y, w, h, w, scaled_h)
                        img.copy_sub_image(center_img, offset_x, offset_y, 0, 0)
                        h = scaled_h
                    else:
                        img.copy_sub_image(tex_atlas, offset_x, offset_y, x, y, w, h)

                    offset_x += w

                offset_y += h

        if self._sizer and recurse:
            self._sizer.update_images()

        return images

    def get_image(self, state=None, composed=True):

        image = self._images.get(state if state else self._current_state)

        if image:
            image = PNMImage(image)

        if image and composed and self._sizer:
            image = self._sizer.get_composed_image(image)

        return image

    def set_image_offset(self, offset):

        self._image_offset = offset

    def get_image_offset(self):

        return self._image_offset

    def update_mouse_region_frames(self, exclude="", recurse=True):

        if self._sizer and recurse:
            self._sizer.update_mouse_region_frames(exclude)

        if not self._mouse_region:
            return

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)

        if exclude:
            l, r, b, t = self._mouse_region.get_frame()

        if "l" not in exclude:
            l = x

        if "r" not in exclude:
            r = x + w

        if "b" not in exclude:
            b = -y - h

        if "t" not in exclude:
            t = -y

        self._mouse_region.set_frame(l, r, b, t)

    def get_mouse_watcher(self):

        return self._parent.get_mouse_watcher()

    def set_contents_hidden(self, hidden=True):
        """ This method is relevant only for container widgets like panels """

        self._is_contents_hidden = hidden

    def is_contents_hidden(self):
        """ This method is relevant only for container widgets like panels """

        return self._is_contents_hidden

    def hide(self, recurse=True):

        if self._is_hidden:
            return False

        mouse_watcher = self.get_mouse_watcher()

        if self._mouse_region:
            mouse_watcher.remove_region(self._mouse_region)

        if recurse and self._sizer:

            for widget in self._sizer.get_widgets():

                mouse_region = widget.get_mouse_region()

                if mouse_region and not widget.is_hidden():
                    mouse_watcher.remove_region(mouse_region)

        self._is_hidden = True

        return True

    def show(self, recurse=True):

        if not self._is_hidden:
            return False

        mouse_watcher = self.get_mouse_watcher()

        if self._mouse_region:
            mouse_watcher.add_region(self._mouse_region)

        if recurse and self._sizer:

            for widget in self._sizer.get_widgets():

                mouse_region = widget.get_mouse_region()

                if mouse_region and not widget.is_hidden(check_ancestors=False):
                    mouse_watcher.add_region(mouse_region)

        self._is_hidden = False

        return True

    def is_hidden(self, check_ancestors=True):

        hidden = self._is_hidden

        if not hidden and check_ancestors and self._parent:
            return self._parent.is_contents_hidden() or self._parent.is_hidden()

        return hidden

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def set_always_enabled(self, always_enabled=True):

        self._is_always_enabled = always_enabled

        if always_enabled:
            self.enable()

    def is_always_enabled(self):

        return self._is_always_enabled

    def enable(self, enable=True, ignore_parent=False):

        if self._is_enabled == enable:
            return False

        if enable and not self._is_always_enabled:

            if not (ignore_parent or self._parent.is_enabled()):
                return False

            for disabler in self._disablers.values():
                if disabler():
                    return False

        self._is_enabled = enable

        if self._mouse_region:
            self._mouse_region.set_active(enable)

        if self._sizer:
            for widget in self._sizer.get_widgets():
                widget.enable(enable)

        return True

    def is_enabled(self):

        return self._is_enabled

    def on_enter(self): pass

    def on_leave(self): pass

    def on_left_down(self): pass

    def on_left_up(self): pass

    def on_right_down(self): pass

    def on_right_up(self): pass


class WidgetCard(object):

    def __init__(self, widget_type, parent=None, stretch_dir=""):

        self._type = "widget"
        self._widget_type = widget_type
        self._parent = parent if parent else Mgr.get("window")
        self._node = self._parent.get_node().attach_new_node("card")
        self._stretch_dir = stretch_dir
        self._size = self._min_size = (0, 0)
        self._sizer = None
        self._sizer_item = None
        self._transparent = False
        self._quad = None
        self.create_quad()
        self._tex = tex = Texture("card_tex")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
        self._image = None
        self._mouse_region = None
        self._outer_borders = (0, 0, 0, 0)

    def destroy(self):

        if self._node:
            self._node.remove_node()
            self._node = None

        if self._sizer:
            self._sizer.destroy()
            self._sizer = None

        self._sizer_item = None

        if self._quad:
            self._quad.remove_node()
            self._quad = None

        if self._mouse_region:
            self.get_mouse_watcher().remove_region(self._mouse_region)
            self._mouse_region = None

        self._image = None

    def get_type(self):

        return self._type

    def set_widget_type(self, widget_type):

        self._widget_type = widget_type

    def get_widget_type(self):

        return self._widget_type

    def get_ancestor(self, widget_type):

        if self._widget_type == widget_type:
            return self

        if self._parent:
            return self._parent.get_ancestor(widget_type)

    def set_transparent(self, transparent=True):

        self._transparent = transparent

    def create_quad(self, frame=(0., 0., 0., 0.)):

        if self._quad:
            self._quad.remove_node()

        cm = CardMaker("widget_card")
        cm.set_frame(frame)
        self._quad = quad = Mgr.get("gui_root").attach_new_node(cm.generate())

        if self._transparent:
            quad.set_transparency(TransparencyAttrib.M_alpha)

        return quad

    def get_quad(self):

        return self._quad

    def set_parent(self, parent):

        self._parent = parent
        self._node.reparent_to(parent.get_node())

    def get_parent(self):

        return self._parent

    def get_node(self):

        return self._node

    def get_card(self):

        return self

    def set_pos(self, pos):

        x, y = pos
        self._node.set_pos(x, 0, -y)
        self.update_quad_pos()

    def update_quad_pos(self):

        if self._quad:
            x, y = self.get_pos(from_root=True)
            self._quad.set_pos(x, 0, -y)

    def get_pos(self, from_root=False):

        node = self._node

        if from_root:
            x, y, z = node.get_pos(node.get_top())
        else:
            x, y, z = node.get_pos(self.get_parent().get_node())

        y = -z

        return (int(x), int(y))

    def set_sizer(self, sizer):

        sizer.set_owner(self)
        self._sizer = sizer

    def get_sizer(self):

        return self._sizer

    def set_sizer_item(self, sizer_item):

        self._sizer_item = sizer_item

    def get_sizer_item(self):

        return self._sizer_item

    def get_stretch_dir(self):

        return self._stretch_dir

    def get_min_size(self):

        return self._sizer.get_min_size() if self._sizer else self._min_size

    def set_size(self, size, is_min=False):

        width, height = size

        if is_min:
            w_new, h_new = width, height
        else:
            w_new, h_new = self.get_min_size()
            width, height = (max(w_new, width), max(h_new, height))

        if self._stretch_dir in ("both", "horizontal"):
            w_new = width

        if self._stretch_dir in ("both", "vertical"):
            h_new = height

        new_size = (w_new, h_new)

        if self._sizer:
            self._sizer.set_size(new_size)

        self._size = new_size

        if is_min:
            self._min_size = new_size

    def get_size(self):

        return self._sizer.get_size() if self._sizer else self._size

    def update_images(self):

        if self._sizer:
            self._sizer.update_images()

    def get_image(self, composed=False):

        return None

    def set_outer_borders(self, borders):

        self._outer_borders = borders

    def get_outer_borders(self):

        return self._outer_borders

    def get_image_offset(self):

        return (0, 0)

    def copy_sub_image(self, widget, sub_image, width, height, offset_x=0, offset_y=0):

        img = self._image

        if not img:
            return False

        x, y = widget.get_pos(ref_node=self._node)
        x += offset_x
        y += offset_y
        img.copy_sub_image(sub_image, x, y, 0, 0, width, height)
        self._tex.load(img)

        return True

    def get_texture(self):

        return self._tex

    def get_mouse_watcher(self):

        return self._parent.get_mouse_watcher()

    def get_mouse_region(self):

        return self._mouse_region

    def update_mouse_region_frames(self, exclude="", recurse=True):

        if self._sizer and recurse:
            self._sizer.update_mouse_region_frames(exclude)

        if not self._mouse_region:
            return

        w, h = self.get_size()
        x, y = self.get_pos(from_root=True)

        if exclude:
            l, r, b, t = self._mouse_region.get_frame()

        if "l" not in exclude:
            l = x

        if "r" not in exclude:
            r = x + w

        if "b" not in exclude:
            b = -y - h

        if "t" not in exclude:
            t = -y

        self._mouse_region.set_frame(l, r, b, t)

    def is_contents_hidden(self):
        """ This method is meaningful only for container widgets like panels """

        return False

    def is_hidden(self, check_ancestors=True):

        return self._parent.is_hidden(check_ancestors) if check_ancestors else False

    def is_enabled(self):

        return True

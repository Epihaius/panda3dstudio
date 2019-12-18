from .base import *
from .toolbar_widgets import *
from .tooltip import ToolTip
from .menu import Menu
from collections import deque


class ToolbarInsertionMarker:

    def __init__(self):

        self._type = ""
        self._cards = cards = {}
        cm = CardMaker("insertion_marker")
        tex_atlas_regions = TextureAtlas["regions"]
        tex_atlas = TextureAtlas["image"]

        for marker_type in ("v", "h", "+"):
            x, y, w, h = tex_atlas_regions[f"toolbar_insertion_marker_{marker_type}"]
            img = PNMImage(w, h, 4)
            img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
            tex = Texture("card_tex")
            tex.minfilter = SamplerState.FT_nearest
            tex.magfilter = SamplerState.FT_nearest
            tex.load(img)
            cm.set_frame(-w // 2, w // 2, -h // 2, h // 2)
            card = NodePath(cm.generate())
            card.set_texture(tex)
            card.set_transparency(TransparencyAttrib.M_alpha)
            card.set_bin("gui", 5)
            card.set_depth_test(False)
            card.set_depth_write(False)
            cards[marker_type] = card

    def set_type(self, marker_type):

        if self._type == marker_type:
            return

        cards = self._cards

        if self._type:
            cards[self._type].detach_node()

        if marker_type:
            cards[marker_type].reparent_to(Mgr.get("gui_root"))

        self._type = marker_type

    def set_pos(self, pos):

        if not self._type:
            return

        x, y = pos
        card = self._cards[self._type]
        card.set_x(x)
        card.set_z(y)

    def hide(self):

        if self._type:
            self._cards[self._type].hide()

    def show(self):

        if self._type:
            self._cards[self._type].show()


class ToolbarGhostImage:

    def __init__(self, toolbar_image):

        x, y, w, h = TextureAtlas["regions"]["toolbar_fade"]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        width, height = toolbar_image.size
        image = PNMImage(width, height, 4)
        image.unfiltered_stretch_from(img)
        image.mult_sub_image(toolbar_image, 0, 0, 0, 0)
        tex = Texture("ghost_tex")
        tex.minfilter = SamplerState.FT_nearest
        tex.magfilter = SamplerState.FT_nearest
        tex.load(image)
        cm = CardMaker("ghost_image")
        cm.set_frame(0, width, -height, 0)
        self._geom = geom = Mgr.get("gui_root").attach_new_node(cm.generate())
        geom.set_texture(tex)
        geom.set_transparency(TransparencyAttrib.M_alpha)
        geom.set_bin("gui", 4)
        geom.set_depth_test(False)
        geom.set_depth_write(False)

    def destroy(self):

        self._geom.detach_node()
        self._geom = None

    def set_pos(self, pos):

        x, y = pos
        self._geom.set_x(x)
        self._geom.set_z(-y)


class ToolbarBundleHandle(Widget):

    _gfx = {"": (("toolbar_bundle_handle_left", "toolbar_bundle_handle_center",
                  "toolbar_bundle_handle_right"),)}
    _grip_tooltip_label = None
    width = 0

    @classmethod
    def __create_grip_tooltip_label(cls):

        cls._grip_tooltip_label = ToolTip.create_label("Move toolbar bundle")

    @classmethod
    def get_grip_tooltip_label(cls):

        return cls._grip_tooltip_label

    @classmethod
    def __set_width(cls, width):

        cls.width = width

    def __init__(self, parent, bundle):

        Widget.__init__(self, "toolbar_bundle_handle", parent, self._gfx)

        if not self._grip_tooltip_label:
            self.__create_grip_tooltip_label()

        handle_id = self.widget_id
        mouse_region = self.mouse_region.name = f"tb_bundle_grip_{handle_id}"

        # Create spinner

        sizer = Sizer("horizontal")
        self.sizer = sizer
        sizer.add((0, 0), proportion=1.)
        spinner_sizer = Sizer("vertical")
        borders = TextureAtlas["outer_borders"]["toolbar_spinner"]
        sizer.add(spinner_sizer, expand=True, borders=borders)
        spin_up_btn = ToolbarSpinButton(self, bundle, "up")
        spin_down_btn = ToolbarSpinButton(self, bundle, "down")
        spinner_sizer.add(spin_up_btn)
        spinner_sizer.add((0, 0), proportion=1.)
        spinner_sizer.add(spin_down_btn)
        width = sizer.update_min_size()[0]

        if not self.width:
            self.__set_width(width)

    def update_mouse_region_frames(self, exclude="", recurse=True):

        Widget.update_mouse_region_frames(self, exclude, recurse)

        if self.is_hidden():
            return

        l, r, b, t = self.mouse_region.frame
        borders = TextureAtlas["outer_borders"]["toolbar_spinner"]
        self.mouse_region.frame = (r - borders[1], r, b, t)


class ToolbarRowHandle(Widget):

    _gfx = {"": (("toolbar_row_handle_left", "toolbar_row_handle_center",
                  "toolbar_row_handle_right"),)}
    _grip_tooltip_label = None
    min_width_in_bundle = 0

    @classmethod
    def __create_grip_tooltip_label(cls):

        cls._grip_tooltip_label = ToolTip.create_label("Move toolbar row")

    @classmethod
    def get_grip_tooltip_label(cls):

        return cls._grip_tooltip_label

    @classmethod
    def __set_min_width_in_bundle(cls, width):

        cls.min_width_in_bundle = width

    def __init__(self, row, parent):

        Widget.__init__(self, "toolbar_row_handle", parent, self._gfx)

        if not self._grip_tooltip_label:
            self.__create_grip_tooltip_label()

        self._row = row
        self._updating_row = False
        self._has_bundle_handle = False

        sizer = Sizer("horizontal")
        self.sizer = sizer
        sizer.add((0, 0), proportion=1.)
        handle_id = self.widget_id
        mouse_watcher = self.mouse_watcher
        region_name = f"tb_row_grip_{handle_id}"
        self._grip_mouse_region = MouseWatcherRegion(region_name, 0., 0., 0., 0.)
        mouse_watcher.add_region(self._grip_mouse_region)

        if not self.min_width_in_bundle:
            bundle_handle = ToolbarBundleHandle(self, None)
            w_bh = bundle_handle.width
            bundle_handle.destroy()
            w_min = self.min_size[0]
            l, r, b, t = self.gfx_inner_borders
            min_width = w_min - r + max(w_bh, r)
            self.__set_min_width_in_bundle(min_width)

    def destroy(self):

        if self._grip_mouse_region:
            self.mouse_watcher.remove_region(self._grip_mouse_region)
            self._grip_mouse_region = None

        Widget.destroy(self)

        self._row = None

    def get_row(self):

        return self._row

    def set_bundle_handle(self, bundle_handle):

        sizer = self.sizer
        sizer.add(bundle_handle)
        bundle_handle.set_parent(self)
        sizer.set_size(sizer.get_size())
        sizer.calculate_positions()
        self._has_bundle_handle = True

    def pop_bundle_handle(self):

        self._has_bundle_handle = False

        return self.sizer.pop_item().object

    def has_bundle_handle(self):

        return self._has_bundle_handle

    def adjust_default_size(self, in_bundle=False):

        w_d = self.min_width_in_bundle if in_bundle else self.gfx_size[0]
        h_d = self.sizer.default_size[1]
        self.sizer.default_size = (w_d, h_d)

    def update_grip_mouse_region(self):

        if self.is_hidden():
            return

        l, r, b, t = self.mouse_region.frame
        borders = TextureAtlas["outer_borders"]["toolbar_spinner"]
        self._grip_mouse_region.frame = (l, l + borders[1], b, t)

    def update_mouse_region_frames(self, exclude="", recurse=True):

        Widget.update_mouse_region_frames(self, exclude, recurse)

        if not self._updating_row:
            self._updating_row = True
            self.update_grip_mouse_region()
            self._row.update()
            self._updating_row = False

    def get_docking_data(self, point):

        l, r, b, t = self.mouse_region.frame
        x, y = point

        if l < x < r and b < -y < t:

            h = t - b
            w_row = self._row.get_size()[0]

            if b + h * .7 < -y < t:
                side = "top"
            elif b < -y < t - h * .7:
                side = "bottom"
            else:
                side = "center"

            positions = {"bottom": (w_row // 2, b), "top": (w_row // 2, t),
                         "center": ((l + r) // 2, (b + t) // 2)}
            widget = self if side == "center" else self._row[0]

            return widget, side, positions[side]

    def destroy_ghost_image(self):

        if self._row:
            self._row.destroy_ghost_image()

    def on_right_up(self):

        self._row.on_right_up()

    def hide(self, recurse=True):

        if not Widget.hide(self, recurse):
            return False

        self.mouse_watcher.remove_region(self._grip_mouse_region)

        return True

    def show(self, recurse=True):

        if not Widget.show(self, recurse):
            return False

        self.mouse_watcher.add_region(self._grip_mouse_region)

        return True

    def enable(self, enable=True):

        if Widget.enable(self, enable):
            self._grip_mouse_region.active = enable


class ToolbarRow:

    def __init__(self, parent):

        self._handle = ToolbarRowHandle(self, parent)
        self._toolbars = []
        self._min_width_in_bundle = 0
        self._size = (0, 0)
        self._image = None
        self._composed_image = None
        self._ghost_image = None
        self._bundle = None
        self._tooltip_label = None

    def __getitem__(self, index):

        try:
            return self._toolbars[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def destroy(self):

        self._handle.destroy()
        self._handle = None
        self._toolbars = []
        self._bundle = None

    def set_parent(self, parent):

        for toolbar in self._toolbars:
            show = not toolbar.is_hidden()
            toolbar.set_parent(parent, show)

        show = not self._handle.is_hidden()
        self._handle.set_parent(parent, show)

        if self._bundle:
            self._bundle.set_parent(self, parent)

    def get_handle(self):

        return self._handle

    def add_toolbar(self, toolbar, index=None):

        if index is None:
            index_offset = len(self._toolbars)
        else:
            index_offset = index

        if self._bundle:
            self._bundle.add_menu_item(self, index_offset, toolbar)

        if index is None:
            self._toolbars.append(toolbar)
        else:
            self._toolbars.insert(index, toolbar)

        self._tooltip_label = ToolTip.create_label(", ".join(t.name for t in self._toolbars))

    def add_toolbars(self, toolbars, index=None):

        if index is None:
            index_offset = len(self._toolbars)
        else:
            index_offset = index

        if self._bundle:
            self._bundle.add_menu_items(self, index_offset, toolbars)

        if index is None:
            self._toolbars.extend(toolbars)
        else:
            self._toolbars[index:index] = toolbars

        self._tooltip_label = ToolTip.create_label(", ".join(t.name for t in self._toolbars))

    def remove_toolbar(self, toolbar):

        self._toolbars.remove(toolbar)
        self._tooltip_label = ToolTip.create_label(", ".join(t.name for t in self._toolbars))

        if self._bundle:
            self._bundle.remove_menu_item(self, toolbar)

    def get_toolbar_names(self):

        return [toolbar.name for toolbar in self._toolbars]

    def get_tooltip_label(self):

        return self._tooltip_label

    def set_bundle(self, bundle):

        self._bundle = bundle

    def get_bundle(self):

        if not self._bundle:
            self._bundle = ToolbarBundle(self)

        return self._bundle

    def in_bundle(self):

        return self._bundle is not None

    def get_pos(self, ref_node=None):

        return self._toolbars[0].get_pos(ref_node)

    def set_min_width_in_bundle(self, width):

        if not self._handle.has_bundle_handle():
            # the given width is assumed to be the result of a call to update_min_size()
            # on the sizer of this row;
            # it is necessary to check if the row handle contains a bundle handle;
            # if not, the bundle handle width needs to be added
            width += self._handle.min_width_in_bundle - self._handle.gfx_size[0]

        self._min_width_in_bundle = width

    def get_min_width(self, in_bundle=False):

        width = self._min_width_in_bundle

        if not in_bundle:
            width -= self._handle.min_width_in_bundle - self._handle.gfx_size[0]

        return width

    def get_size(self):

        return self._size

    def update(self):

        w, h = self._toolbars[0].get_size()

        for toolbar in self._toolbars[1:]:
            w += toolbar.get_size()[0]

        w += self._handle.get_size()[0]
        self._size = (w, h)
        self.update_image()

        if self._bundle:
            self._bundle.update_other_toolbar_rows(self)

    def update_image(self):

        w, h = self._size
        w -= ToolbarBundleHandle.width
        self._image = image = PNMImage(w, h, 4)
        x = 0

        for toolbar in self._toolbars:
            image.copy_sub_image(toolbar.get_composed_image(), x, 0, 0, 0)
            x += toolbar.get_size()[0]

        image.copy_sub_image(self._handle.get_image(), x, 0, 0, 0)

    def get_image(self):

        return self._image

    def __update_ghost_image(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        pos = (mouse_pointer.x, mouse_pointer.y)
        self._ghost_image.set_pos(pos)

        return task.cont

    def create_ghost_image(self):

        self._ghost_image = ToolbarGhostImage(self._image)
        Mgr.add_task(self.__update_ghost_image, "update_ghost_image")

    def destroy_ghost_image(self):

        Mgr.remove_task("update_ghost_image")
        self._ghost_image.destroy()
        self._ghost_image = None

    def on_right_up(self):

        if self._bundle:
            self._bundle.show_menu()

    def hide(self, recurse=True):

        for toolbar in self._toolbars:
            toolbar.hide(recurse)

        self._handle.hide(recurse)

    def show(self, recurse=True):

        for toolbar in self._toolbars:
            toolbar.show(recurse)

        self._handle.show(recurse)


class Toolbar(Widget, HotkeyManager):

    registry = {}
    _gfx = {"": (("toolbar_left", "toolbar_center", "toolbar_right"),)}

    def __init__(self, parent, toolbar_id, name=""):

        Widget.__init__(self, "toolbar", parent, self._gfx)

        self.registry[toolbar_id] = self
        self.id = toolbar_id
        self.name = name
        self._grip_tooltip_label = ToolTip.create_label(f"Move {name} toolbar")
        self._row = None
        sizer = Sizer("horizontal")
        self.sizer = sizer
        self._client_sizer = client_sizer = Sizer("horizontal")
        client_sizer.add((10, 0))
        borders = self.gfx_inner_borders
        sizer.add(client_sizer, borders=borders, proportion=1., expand=True)
        region_name = f"toolbar_grip_{self.widget_id}"
        self._grip_mouse_region = MouseWatcherRegion(region_name, 0., 0., 0., 0.)
        self.mouse_watcher.add_region(self._grip_mouse_region)
        self._composed_image = None
        self._ghost_image = None
        self._hotkey_handlers = {}
        self._interface_id = ""

    def destroy(self):

        self.mouse_watcher.remove_region(self._grip_mouse_region)
        self._grip_mouse_region = None

        Widget.destroy(self)

        self._row = None
        self._hotkeys = {}

    def get_grip_tooltip_label(self):

        return self._grip_tooltip_label

    def set_row(self, row):

        self._row = row

    def get_row(self):

        return self._row

    def get_client_sizer(self):

        return self._client_sizer

    def add(self, *args, **kwargs):

        return self._client_sizer.add(*args, **kwargs)

    def add_item(self, *args, **kwargs):

        self._client_sizer.add_item(*args, **kwargs)

    def remove_item(self, *args, **kwargs):

        self._client_sizer.remove_item(*args, **kwargs)

    def pop_item(self, *args, **kwargs):

        return self._client_sizer.pop_item(*args, **kwargs)

    def set_size(self, size, includes_borders=True, is_min=False):

        if not self.sizer.item_size_locked:
            Widget.set_size(self, size, includes_borders, is_min)

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if composed:
            self._composed_image = image

        return image

    def get_composed_image(self):

        return self._composed_image

    def update_composed_image(self, widget, image=None, offset_x=0, offset_y=0):

        if widget.state == "hilited":
            return

        if not self._composed_image:
            self._composed_image = Widget.get_image(self)
            return

        toolbar_img = self.get_image(composed=False)
        widget_img = image if image else widget.get_image()

        if toolbar_img and widget_img:

            x, y = widget.get_pos()
            x += offset_x
            y += offset_y
            w, h = widget_img.size
            bg_image = PNMImage(w, h, 4)
            bg_image.copy_sub_image(toolbar_img, 0, 0, x, y, w, h)
            bg_image.blend_sub_image(widget_img, 0, 0, 0, 0)
            self._composed_image.copy_sub_image(bg_image, x, y, 0, 0)
            row_img = self._row.get_image()

            if row_img:
                row_img.copy_sub_image(bg_image, x + self.get_pos()[0], y, 0, 0)

    def update_images(self, recurse=True, size=None):

        if not self.sizer.item_size_locked:
            Widget.update_images(self, recurse, size)
            self._composed_image = Widget.get_image(self)
            self.sizer.item_size_locked = True

    def update_mouse_region_frames(self, exclude="", recurse=True):

        Widget.update_mouse_region_frames(self, exclude, recurse)

        l, r, b, t = self.mouse_region.frame
        border_left = self.gfx_inner_borders[0]
        self._grip_mouse_region.frame = (l, l + border_left, b, t)

    def get_docking_data(self, point):

        l, r, b, t = self.mouse_region.frame
        x, y = point

        if l < x < r and b < -y < t:

            w = r - l
            h = t - b
            w_row = self._row.get_size()[0]

            if b + h * .7 < -y < t:
                side = "top"
            elif b < -y < t - h * .7:
                side = "bottom"
            elif l < x < r - w * .5:
                side = "left"
            else:
                side = "right"

            positions = {"left": (l, (b + t) // 2), "right": (r, (b + t) // 2),
                         "bottom": (w_row // 2, b), "top": (w_row // 2, t)}

            return self, side, positions[side]

    def __update_ghost_image(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        pos = (mouse_pointer.x, mouse_pointer.y)
        self._ghost_image.set_pos(pos)

        return task.cont

    def create_ghost_image(self):

        self._ghost_image = ToolbarGhostImage(self.get_image())
        Mgr.add_task(self.__update_ghost_image, "update_ghost_image")

    def destroy_ghost_image(self):

        Mgr.remove_task("update_ghost_image")
        self._ghost_image.destroy()
        self._ghost_image = None

    def on_right_up(self):

        self._row.on_right_up()

    def hide(self, recurse=True):

        if not Widget.hide(self, recurse):
            return False

        self.mouse_watcher.remove_region(self._grip_mouse_region)

        return True

    def show(self, recurse=True):

        if not Widget.show(self, recurse):
            return False

        self.mouse_watcher.add_region(self._grip_mouse_region)

        return True

    def enable(self, enable=True):

        if Widget.enable(self, enable):
            self._grip_mouse_region.active = enable

    def add_hotkey(self, hotkey, command, interface_id="main"):

        registry = self.get_hotkey_registry().setdefault(interface_id, {})
        registry[hotkey] = self
        self._hotkey_handlers[hotkey] = command
        self._interface_id = interface_id

    def remove_hotkey(self, hotkey):

        registry = self.get_hotkey_registry().get(self._interface_id, {})

        if hotkey in registry:
            del registry[hotkey]

        if hotkey in self._hotkey_handlers:
            del self._hotkey_handlers[hotkey]

    def handle_hotkey(self, hotkey):

        self._hotkey_handlers.get(hotkey, lambda: None)()

    def enable_hotkeys(self, enable=True):

        registry = self.get_hotkey_registry().get(self._interface_id, {})

        if enable:
            for hotkey in self._hotkey_handlers:
                registry[hotkey] = self
        else:
            for hotkey in self._hotkey_handlers:
                if hotkey in registry:
                    del registry[hotkey]

        for widget in self._client_sizer.get_widgets():
            if widget.widget_type == "toolbar_button":
                widget.enable_hotkey(enable)


class ToolbarBundle:

    def __init__(self, toolbar_row):

        self._toolbar_rows = deque([toolbar_row])
        self._updating_other_rows = False

        self._menu = menu = Menu()

        for toolbar in toolbar_row:
            toolbar_id = toolbar.id
            command = self.__get_menu_command(toolbar_id)
            menu.add(f"toolbar_{toolbar_id}", toolbar.name, command, item_type="radio")

        row_handle = toolbar_row.get_handle()
        row_handle.adjust_default_size(in_bundle=True)
        bundle_handle = ToolbarBundleHandle(row_handle, self)
        row_handle.set_bundle_handle(bundle_handle)

    def __getitem__(self, index):

        try:
            return self._toolbar_rows[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def destroy(self):

        if not self._toolbar_rows:
            return

        self._toolbar_rows[-1].get_handle().pop_bundle_handle().destroy()
        self._toolbar_rows.clear()
        self._menu.destroy()
        self._menu = None

    def __get_menu_command(self, toolbar_id):

        def command():

            toolbar = Toolbar.registry[toolbar_id]
            index = list(self._toolbar_rows).index(toolbar.get_row())
            self.spin_toolbar_rows(len(self._toolbar_rows) - 1 - index)

        return command

    def add_menu_item(self, row, index_offset, toolbar):

        menu = self._menu
        index = menu.get_item_index(f"toolbar_{row[0].id}") + index_offset
        toolbar_id = toolbar.id
        command = self.__get_menu_command(toolbar_id)
        item_id = f"toolbar_{toolbar_id}"
        menu.add(item_id, toolbar.name, command, item_type="radio", index=index, update=True)

    def add_menu_items(self, row, index_offset, toolbars):

        menu = self._menu
        index = menu.get_item_index(f"toolbar_{row[0].id}") + index_offset

        for toolbar in toolbars[::-1]:
            toolbar_id = toolbar.id
            command = self.__get_menu_command(toolbar_id)
            item_id = f"toolbar_{toolbar_id}"
            menu.add(item_id, toolbar.name, command, item_type="radio", index=index)

        menu.update()

    def remove_menu_item(self, row, toolbar):

        item_id = f"toolbar_{toolbar.id}"
        self._menu.remove(item_id, update=True, destroy=True)
        self._menu.check_radio_item(f"toolbar_{row[0].id}")

    def get_toolbar_rows(self):

        return self._toolbar_rows

    def set_parent(self, toolbar_row, parent):

        other_rows = list(self._toolbar_rows)
        other_rows.remove(toolbar_row)

        for other_row in other_rows:

            handle = other_row.get_handle()
            show = not handle.is_hidden()
            handle.set_parent(parent, show)

            for toolbar in other_row:
                show = not toolbar.is_hidden()
                toolbar.set_parent(parent, show)

    def add_toolbar_row(self, toolbar_row):

        if toolbar_row in self._toolbar_rows:
            return

        prev_row = self._toolbar_rows[-1]
        handle = prev_row.get_handle()
        bundle_handle = handle.pop_bundle_handle()
        row_sizer = handle.sizer_item.sizer
        row_sizer.clear()
        prev_row.hide()

        if toolbar_row.in_bundle():
            row_deque = toolbar_row.get_bundle().get_toolbar_rows()
            toolbar_rows = list(row_deque)
            row_deque.clear()
            # remove the handle from the added bundle, since it will be replaced with the one
            # belonging to this bundle
            toolbar_row.get_handle().pop_bundle_handle().destroy()
        else:
            toolbar_rows = [toolbar_row]

        self._toolbar_rows.extend(toolbar_rows)
        toolbar_row.get_handle().set_bundle_handle(bundle_handle)

        for other_row in toolbar_rows[:-1]:
            other_row.hide()

        parent = handle.parent
        menu = self._menu
        index = menu.get_item_index(f"toolbar_{prev_row[0].id}")

        for row in toolbar_rows:

            row.set_bundle(self)
            handle = row.get_handle()
            show = not handle.is_hidden()
            handle.set_parent(parent, show)

            for toolbar in row[::-1]:
                toolbar_id = toolbar.id
                command = self.__get_menu_command(toolbar_id)
                item_id = f"toolbar_{toolbar_id}"
                menu.add(item_id, toolbar.name, command, item_type="radio", index=index)
                show = not toolbar.is_hidden()
                toolbar.set_parent(parent, show)

        for toolbar in toolbar_row:
            row_sizer.add_item(toolbar.sizer_item)

        for row in self._toolbar_rows:
            row.get_handle().adjust_default_size(in_bundle=True)
            size = row.get_handle().sizer.default_size

        row_sizer.add_item(toolbar_row.get_handle().sizer_item)

        menu.update()
        menu.check_radio_item(f"toolbar_{toolbar_row[0].id}")

    def remove_toolbar_row(self):

        prev_row = self._toolbar_rows[-1]
        next_row = self._toolbar_rows[-2]
        prev_row.set_bundle(None)
        next_row.show()

        prev_row.get_handle().adjust_default_size()
        row_sizer = prev_row.get_handle().sizer_item.sizer
        row_sizer.clear()

        for toolbar in next_row:
            sizer_item = toolbar.sizer_item
            row_sizer.add_item(sizer_item)

        sizer_item = next_row.get_handle().sizer_item
        row_sizer.add_item(sizer_item)

        if len(self._toolbar_rows) == 2:

            next_row.set_bundle(None)
            next_row.get_handle().adjust_default_size()
            self.destroy()

        else:

            self._toolbar_rows.pop()
            bundle_handle = prev_row.get_handle().pop_bundle_handle()
            next_row.get_handle().set_bundle_handle(bundle_handle)

            menu = self._menu

            for toolbar in prev_row:
                item_id = f"toolbar_{toolbar.id}"
                menu.remove(item_id, destroy=True)

            menu.update()
            menu.check_radio_item(f"toolbar_{next_row[0].id}")

        return next_row

    def update_other_toolbar_rows(self, toolbar_row):

        if self._updating_other_rows:
            return

        self._updating_other_rows = True

        def remove_toolbar_row(sizer, row):

            sizer.clear()
            row.hide(recurse=False)

        def add_toolbar_row(sizer, row):

            for toolbar in row:
                sizer.add_item(toolbar.sizer_item)

            sizer.add_item(row.get_handle().sizer_item)
            row.show(recurse=False)

        other_rows = list(self._toolbar_rows)
        other_rows.remove(toolbar_row)
        row_sizer = toolbar_row.get_handle().sizer_item.sizer
        remove_toolbar_row(row_sizer, toolbar_row)
        size = toolbar_row.get_size()

        for other_row in other_rows:
            add_toolbar_row(row_sizer, other_row)
            row_sizer.update_min_size()
            row_sizer.set_size(size)
            row_sizer.calculate_positions(row_sizer.get_pos())
            row_sizer.update_images()
            row_sizer.update_mouse_region_frames()
            remove_toolbar_row(row_sizer, other_row)

        add_toolbar_row(row_sizer, toolbar_row)
        row_sizer.set_min_size_stale(False)
        self._updating_other_rows = False

    def spin_toolbar_rows(self, amount):

        prev_row = self._toolbar_rows[-1]
        self._toolbar_rows.rotate(amount)
        next_row = self._toolbar_rows[-1]

        if next_row == prev_row:
            w, h = next_row.get_size()
            image = next_row.get_image()
            next_row.get_handle().card.copy_sub_image(next_row, image, w, h)
            return

        handle = prev_row.get_handle()
        row_sizer = handle.sizer_item.sizer
        row_sizer.clear()
        bundle_handle = handle.pop_bundle_handle()

        for toolbar in next_row:
            row_sizer.add_item(toolbar.sizer_item)

        handle = next_row.get_handle()
        row_sizer.add_item(handle.sizer_item)
        prev_row.hide()
        next_row.show()
        handle.set_bundle_handle(bundle_handle)
        handle.update_grip_mouse_region()
        w, h = next_row.get_size()
        image = next_row.get_image()
        handle.card.copy_sub_image(next_row, image, w, h)
        toolbar = next_row[0]
        self._menu.check_radio_item(f"toolbar_{toolbar.id}")

        config_data = GD["config"]
        side = toolbar.parent.get_side()
        toolbar_id = toolbar.id
        toolbar_id_lists = config_data["gui_layout"][GD["active_interface"]][side]

        for toolbar_id_list in toolbar_id_lists:
            if toolbar_id_list and toolbar_id in sum(toolbar_id_list, []):
                toolbar_id_list[:] = [[t.id for t in row] for row in self]
                break

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def spin_images(self, amount):

        rows = deque(self._toolbar_rows)
        rows.rotate(amount)
        row = rows[-1]
        row.get_handle().card.copy_sub_image(row, row.get_image(), *row.get_size())

    def get_min_width(self):

        return max(row.get_min_width(in_bundle=True) for row in self._toolbar_rows)

    def show_menu(self):

        self._menu.show_at_mouse_pos()


__all__ = ("Toolbar", "ToolbarRow", "ToolbarText", "ToolbarInsertionMarker",
           "ToolbarSeparator", "ToolbarButton", "ToolbarInputField",
           "ToolbarSliderField", "ToolbarSpinnerField", "ToolbarMultiValField",
           "ToolbarComboBox", "ToolbarCheckButton", "ToolbarColorBox")

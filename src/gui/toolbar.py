from .base import *
from .toolbar_widgets import *
from .tooltip import ToolTip
from .menu import Menu
from collections import deque


class ToolbarInsertionMarker(object):

    def __init__(self):

        self._type = ""
        self._cards = cards = {}
        cm = CardMaker("insertion_marker")
        tex_atlas_regions = TextureAtlas["regions"]
        tex_atlas = TextureAtlas["image"]

        for marker_type in ("v", "h", "+"):
            x, y, w, h = tex_atlas_regions["toolbar_insertion_marker_{}".format(marker_type)]
            img = PNMImage(w, h, 4)
            img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
            tex = Texture("card_tex")
            tex.set_minfilter(SamplerState.FT_nearest)
            tex.set_magfilter(SamplerState.FT_nearest)
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


class ToolbarGhostImage(object):

    def __init__(self, toolbar_image):

        x, y, w, h = TextureAtlas["regions"]["toolbar_fade"]
        img = PNMImage(w, h, 4)
        img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        width = toolbar_image.get_x_size()
        height = toolbar_image.get_y_size()
        image = PNMImage(width, height, 4)
        image.unfiltered_stretch_from(img)
        image.mult_sub_image(toolbar_image, 0, 0, 0, 0)
        tex = Texture("ghost_tex")
        tex.set_minfilter(SamplerState.FT_nearest)
        tex.set_magfilter(SamplerState.FT_nearest)
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

        self._geom.remove_node()

    def set_pos(self, pos):

        x, y = pos
        self._geom.set_x(x)
        self._geom.set_z(-y)


class Toolbar(Widget):

    registry = {}
    _gfx = {"": (("toolbar_left", "toolbar_main", "toolbar_right"),)}

    def __init__(self, parent, toolbar_id, name=""):

        Widget.__init__(self, "toolbar", parent, self._gfx, stretch_dir="horizontal")

        self.registry[toolbar_id] = self
        self._id = toolbar_id
        self._name = name
        self._tooltip_label = ToolTip.create_label(name)
        self._bundle = None
        sizer = Sizer("horizontal")
        sizer.set_default_size((0, self.get_min_size()[1]))
        self.set_sizer(sizer)
        self._client_sizer = client_sizer = Sizer("horizontal")
        client_sizer.add((10, 0))
        borders = self.get_gfx_inner_borders()
        sizer.add(client_sizer, borders=borders, proportion=1., expand=True)
        region_name = "toolbar_grip_{:d}".format(self.get_widget_id())
        self._grip_mouse_region = MouseWatcherRegion(region_name, 0., 0., 0., 0.)
        self.get_mouse_watcher().add_region(self._grip_mouse_region)
        self._composed_image = None
        self._ghost_image = None

    def destroy(self):

        self.get_mouse_watcher().remove_region(self._grip_mouse_region)
        self._grip_mouse_region = None

        Widget.destroy(self)

        self._bundle = None

    def set_parent(self, parent, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.set_parent(parent)
            return

        show = not self.is_hidden()
        Widget.set_parent(self, parent, show)

    def get_id(self):

        return self._id

    def get_name(self):

        return self._name

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

    def set_proportion(self, proportion, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.set_proportion(proportion)
            return

        self.get_sizer_item().set_proportion(proportion)

    def set_pos(self, pos, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.set_pos(pos)
            return

        Widget.set_pos(self, pos)

    def set_size(self, size, includes_borders=True, is_min=False, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.set_size(size, includes_borders, is_min)
            return

        if self.get_sizer().item_size_locked():
            return

        Widget.set_size(self, size, includes_borders, is_min)

    def get_image(self, state=None, composed=True):

        image = Widget.get_image(self, state, composed)

        if composed:
            self._composed_image = image

        return image

    def get_composed_image(self):

        return self._composed_image

    def update_composed_image(self, widget, image=None, offset_x=0, offset_y=0):

        if not self._composed_image:
            self._composed_image = self.get_image()
            return

        toolbar_img = self.get_image(composed=False)
        widget_img = image if image else widget.get_image()

        if toolbar_img and widget_img:
            x, y = widget.get_pos()
            x += offset_x
            y += offset_y
            w, h = widget_img.get_x_size(), widget_img.get_y_size()
            bg_image = PNMImage(w, h, 4)
            bg_image.copy_sub_image(toolbar_img, 0, 0, x, y, w, h)
            bg_image.blend_sub_image(widget_img, 0, 0, 0, 0)
            self._composed_image.copy_sub_image(bg_image, x, y, 0, 0)

    def update_images(self, recurse=True, size=None, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.update_images(recurse, size)
            return

        if self.get_sizer().item_size_locked():
            return

        Widget.update_images(self, recurse, size)
        self.get_image()

    def update_mouse_region_frames(self, exclude="", recurse=True, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.update_mouse_region_frames(exclude, recurse)
            return

        Widget.update_mouse_region_frames(self, exclude, recurse)

        l, r, b, t = self.get_mouse_region().get_frame()
        border_left = self.get_gfx_inner_borders()[0]
        self._grip_mouse_region.set_frame(l, l + border_left, b, t)

    def get_docking_data(self, point):

        l, r, b, t = self.get_mouse_region().get_frame()
        x, y = point

        if l < x < r and b < -y < t:

            if GlobalData["shift_down"]:
                return self, "top", ((l + r) // 2, (b + t) // 2)

            dists = {x - l: "left", r - x: "right", -b - y: "bottom", y + t: "top"}
            dist = min(dists.iterkeys())

            side = dists[dist]
            positions = {"left": (l, (b + t) // 2), "right": (r, (b + t) // 2),
                         "bottom": ((l + r) // 2, b), "top": ((l + r) // 2, t)}

            return self, side, positions[side]

    def __update_ghost_image(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        pos = (mouse_x, mouse_y)
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

        if self._bundle:
            self._bundle.show_menu()

    def hide(self):

        if not Widget.hide(self):
            return False

        self.get_mouse_watcher().remove_region(self._grip_mouse_region)

        return True

    def show(self):

        if not Widget.show(self):
            return False

        self.get_mouse_watcher().add_region(self._grip_mouse_region)

        return True

    def enable(self, enable=True, update_bundle=True):

        if update_bundle and self._bundle:
            self._bundle.enable(enable)
            return

        if Widget.enable(self, enable):
            self._grip_mouse_region.set_active(enable)

    def enable_hotkeys(self, enable=True):

        for widget in self._client_sizer.get_widgets():
            if widget.get_widget_type() == "toolbar_button":
                widget.enable_hotkey(enable)


class ToolbarBundle(object):

    def __init__(self, toolbar):

        self._toolbars = deque([toolbar])
        self._toolbars_backup = None

        # Create spinner

        spinner_sizer = Sizer("horizontal")
        spinner_sizer.add((0, 0), proportion=1.)
        spinner_edge = ToolbarSpinnerEdge(toolbar)
        spinner_sizer.add(spinner_edge)
        spinner_subsizer = Sizer("vertical")
        spinner_sizer.add(spinner_subsizer, expand=True)
        spin_up_btn = ToolbarSpinButton(toolbar, self, "up")
        spin_down_btn = ToolbarSpinButton(toolbar, self, "down")
        spinner_subsizer.add(spin_up_btn)
        spinner_subsizer.add((0, 0), proportion=1.)
        spinner_subsizer.add(spin_down_btn, alignment="bottom")
        self._spinner_item = toolbar.add(spinner_sizer, proportion=1., expand=True)

        toolbar.get_sizer().update()
        self.__update_min_size()

        self._menu = menu = Menu()
        toolbar_id = toolbar.get_id()
        command = self.__get_menu_command(toolbar_id)
        menu.add("toolbar_{}".format(toolbar_id), toolbar.get_name(), command, item_type="radio")

    def destroy(self):

        if not self._toolbars:
            return

        self._toolbars.clear()
        self._spinner_item.destroy()
        self._spinner_item = None
        self._menu.destroy()
        self._menu = None

    def __get_menu_command(self, toolbar_id):

        def command():

            toolbar = Toolbar.registry[toolbar_id]
            index = list(self._toolbars).index(toolbar)
            self.spin_toolbars(len(self._toolbars) - 1 - index)

        return command

    def get_toolbars(self):

        return self._toolbars

    def set_parent(self, parent):

        for toolbar in self._toolbars:
            toolbar.set_parent(parent, update_bundle=False)

    def __reset_min_sizes(self):

        for toolbar in self._toolbars:
            sizer = toolbar.get_sizer()
            sizer.set_min_size_stale()
            sizer.update()

    def __update_min_size(self):

        toolbars = list(self._toolbars)
        toolbar = toolbars.pop()
        w_min, h_min = toolbar.get_min_size()

        for toolbar in toolbars:

            w, h = toolbar.get_min_size()

            if w > w_min:
                w_min = w

        for toolbar in self._toolbars:
            sizer = toolbar.get_sizer()
            sizer.set_min_size((w_min, h_min))

    def add_toolbar(self, toolbar):

        if toolbar in self._toolbars:
            return

        prev_toolbar = self._toolbars[-1]
        spinner_item = prev_toolbar.pop_item()
        space_sizer = Sizer("horizontal")
        space_sizer.add((ToolbarSpinnerEdge.width, 0), proportion=1.)
        space_sizer.add((ToolbarSpinButton.width, 0))
        prev_toolbar.add(space_sizer, proportion=1.)
        prev_toolbar.hide()

        if toolbar.in_bundle():
            toolbar_deque = toolbar.get_bundle().get_toolbars()
            toolbars = list(toolbar_deque)
            toolbar_deque.clear()
            # remove the spinner from the added bundle, since it will be replaced with the one
            # belonging to this bundle
            item = toolbar.pop_item()
            item.destroy()
        else:
            toolbars = [toolbar]

        self._toolbars.extend(toolbars)
        toolbar.add_item(spinner_item)

        for widget in spinner_item.get_object().get_widgets():
            widget.set_parent(toolbar)

        for other_toolbar in toolbars[:-1]:
            other_toolbar.hide()

        parent = prev_toolbar.get_parent()
        menu = self._menu
        index = menu.get_item_index("toolbar_{}".format(prev_toolbar.get_id()))

        for toolbar in toolbars:
            toolbar_id = toolbar.get_id()
            command = self.__get_menu_command(toolbar_id)
            item_id = "toolbar_{}".format(toolbar_id)
            menu.add(item_id, toolbar.get_name(), command, item_type="radio", index=index)
            toolbar.set_parent(parent, update_bundle=False)
            toolbar.set_bundle(self)
            toolbar.get_sizer().update()

        menu.update()
        menu.check_radio_item("toolbar_{}".format(toolbar.get_id()))
        self.__update_min_size()

    def remove_toolbar(self):

        prev_toolbar = self._toolbars.pop()
        next_toolbar = self._toolbars[-1]
        spinner_item = prev_toolbar.pop_item()
        prev_toolbar.set_bundle(None)
        next_toolbar.get_sizer().update()
        next_toolbar.show()
        space_item = next_toolbar.pop_item()
        space_item.destroy()

        sizer_item = prev_toolbar.get_sizer_item()
        sizer = sizer_item.get_sizer()
        index = sizer.get_item_index(sizer_item)
        sizer.remove_item(sizer_item)
        sizer.add_item(next_toolbar.get_sizer_item(), index=index)

        if len(self._toolbars) == 1:

            next_toolbar.set_bundle(None)
            self.destroy()

        else:

            for widget in spinner_item.get_object().get_widgets():
                widget.set_parent(next_toolbar)

            next_toolbar.add_item(spinner_item)
            self.__reset_min_sizes()
            self.__update_min_size()

            menu = self._menu
            item_id = "toolbar_{}".format(prev_toolbar.get_id())
            menu.remove(item_id, update=True, destroy=True)
            menu.check_radio_item("toolbar_{}".format(next_toolbar.get_id()))

        return next_toolbar

    def spin_toolbars(self, amount):

        prev_toolbar = self._toolbars[-1]
        self._toolbars.rotate(amount)
        next_toolbar = self._toolbars[-1]

        if next_toolbar == prev_toolbar:
            w, h = next_toolbar.get_size()
            image = next_toolbar.get_image()
            next_toolbar.get_card().copy_sub_image(next_toolbar, image, w, h)
            return

        sizer_item = prev_toolbar.get_sizer_item()
        sizer = sizer_item.get_sizer()
        index = sizer.get_item_index(sizer_item)
        sizer.remove_item(sizer_item)
        spinner_item = prev_toolbar.pop_item()
        sizer.add_item(next_toolbar.get_sizer_item(), index=index)

        for widget in spinner_item.get_object().get_widgets():
            widget.set_parent(next_toolbar)

        space_item = next_toolbar.pop_item()
        prev_toolbar.add_item(space_item)
        prev_toolbar.get_sizer().set_min_size_stale(False)
        prev_toolbar.hide()
        next_toolbar.show()
        next_toolbar.add_item(spinner_item)
        next_toolbar.get_sizer().set_min_size_stale(False)
        w, h = next_toolbar.get_size()
        image = next_toolbar.get_image()
        next_toolbar.get_card().copy_sub_image(next_toolbar, image, w, h)

        self._menu.check_radio_item("toolbar_{}".format(next_toolbar.get_id()))

        config_data = GlobalData["config"]
        top_toolbar = self._toolbars[-1]
        top_toolbar_id = top_toolbar.get_id()
        side = top_toolbar.get_parent().get_side()
        layout = config_data["gui_layout"][GlobalData["active_interface"]][side]

        for toolbar_row in layout:
            if toolbar_row:
                for toolbar_ids in toolbar_row:
                    if top_toolbar_id in toolbar_ids:
                        toolbar_ids[:] = [t.get_id() for t in self._toolbars]
                        break
                else:
                    continue
                break

        with open("config", "wb") as config_file:
            cPickle.dump(config_data, config_file, -1)

    def set_pos(self, pos):

        for toolbar in self._toolbars:
            toolbar.set_pos(pos, update_bundle=False)

    def set_size(self, size, includes_borders=True, is_min=False):

        for toolbar in self._toolbars:
            toolbar.set_size(size, includes_borders, is_min, update_bundle=False)

    def set_proportion(self, proportion):

        for toolbar in self._toolbars:
            toolbar.set_proportion(proportion, update_bundle=False)

    def update_images(self, recurse=True, size=None):

        for toolbar in self._toolbars:
            toolbar.update_images(recurse, size, update_bundle=False)

    def spin_images(self, amount):

        toolbars = deque(self._toolbars)
        toolbars.rotate(amount)
        toolbar = toolbars[-1]
        w, h = toolbar.get_size()
        w -= ToolbarSpinnerEdge.width + ToolbarSpinButton.width + toolbar.get_gfx_inner_borders()[1]
        toolbar.get_card().copy_sub_image(toolbar, toolbar.get_composed_image(), w, h)

    def update_mouse_region_frames(self, exclude="", recurse=True):

        for toolbar in self._toolbars:
            toolbar.update_mouse_region_frames(exclude, recurse, update_bundle=False)

    def show_menu(self):

        self._menu.show_at_mouse_pos()

    def hide(self):

        if not self._spinner_item.get_object().hide():
            return False

        self._toolbars[-1].hide()

        return True

    def show(self):

        if not self._spinner_item.get_object().show():
            return False

        self._toolbars[-1].show()

        return True

    def enable(self, enable=True):

        for toolbar in self._toolbars:
            toolbar.enable(enable, update_bundle=False)


__all__ = ("Toolbar", "ToolbarText", "ToolbarInsertionMarker", "ToolbarSeparator", "ToolbarButton",
           "ToolbarInputField", "ToolbarComboBox", "ToolbarCheckBox", "ToolbarColorBox")

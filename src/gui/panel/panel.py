from ..base import *
from ..button import Button
from ..menu import Menu
from .section import PanelSection


class PanelHeader(Widget):

    images = {}
    height = 0
    _gfx = {"": (("expanded_panel_header_left", "expanded_panel_header_center",
            "expanded_panel_header_right"),)}

    def __init__(self, parent):

        Widget.__init__(self, "panel_header", parent, self._gfx, stretch_dir="horizontal")

        if not self.height:
            PanelHeader.height = self.get_min_size()[1]

        self.node.name = "panel_header"

    def set_size(self, size, includes_borders=True, is_min=False):

        Widget.set_size(self, size, includes_borders, is_min)

        parent = self.parent
        parent.get_collapsed_header().set_size(size)
        parent.get_collapsed_bottom().set_size(size)

    def set_pos(self, pos): pass

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            PanelHeader.images = Widget.update_images(self)

        parent = self.parent
        parent.get_collapsed_header().update_images()
        parent.get_collapsed_bottom().update_images()

    def update_mouse_region_frames(self, exclude=""):

        Widget.update_mouse_region_frames(self, exclude)
        parent = self.parent
        parent.get_collapsed_header().update_mouse_region_frames(exclude)
        parent.get_collapsed_bottom().update_mouse_region_frames(exclude)

    def on_left_up(self):

        self.parent.expand(False)

    def is_hidden(self, check_ancestors=True):

        return self.parent.is_hidden(check_ancestors=True)


class PanelBottom(Button):

    images = {}
    height = 0
    _gfx = {
        "normal": (("expanded_panel_bottom_normal",),),
        "hilited": (("expanded_panel_bottom_hilited",),)
    }

    def __init__(self, parent):

        Button.__init__(self, parent, self._gfx)

        self.widget_type = "panel_bottom"

        if not self.height:
            PanelBottom.height = self.get_min_size()[1]

        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        node = self.node
        node.name = "panel_bottom"
        node.set_z(-b)
        self._hook_node = hook_node = node.attach_new_node("hook_node")
        hook_node.set_z(-self.height)

    def set_pos(self, pos): pass

    def get_hook_node(self):

        return self._hook_node

    def update_images(self):

        if self.images:

            self._images = self.images

        else:

            Widget.update_images(self)
            width, height = self.get_size()
            tex_atlas = TextureAtlas["image"]
            tex_atlas_regions = TextureAtlas["regions"]

            for state in ("normal", "hilited"):
                x, y, w, h = tex_atlas_regions[f"expanded_panel_arrow_{state}"]
                img = PNMImage(w, h, 4)
                img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                image = self._images[state]
                x = (width - w) // 2
                y = height - h
                image.blend_sub_image(img, x, y, 0, 0, w, h)

            PanelBottom.images = self._images

    def on_left_up(self):

        if Button.on_left_up(self):
            self.parent.expand(False)

    def on_leave(self):

        if not self.parent.is_expanded():
            self._current_state = "normal"
            return

        Button.on_leave(self)

    def is_hidden(self, check_ancestors=True):

        return self.parent.is_hidden(check_ancestors=True)


class CollapsedPanelHeader(Widget):

    images = {}
    height = 0
    _gfx = {"": (("collapsed_panel_header_left", "collapsed_panel_header_center",
            "collapsed_panel_header_right"),)}

    def __init__(self, parent):

        Widget.__init__(self, "panel_header", parent, self._gfx, "", "horizontal")

        if not self.height:
            CollapsedPanelHeader.height = self.get_min_size()[1]

        self.node.name = "collapsed_panel_header"

    def set_pos(self, pos): pass

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            CollapsedPanelHeader.images = Widget.update_images(self)

    def on_left_up(self):

        self.parent.expand()

    def is_hidden(self, check_ancestors=True):

        return self.parent.is_hidden(check_ancestors=True)


class CollapsedPanelBottom(Button):

    images = {}
    height = 0
    _gfx = {
        "normal": (("collapsed_panel_bottom_normal",),),
        "hilited": (("collapsed_panel_bottom_hilited",),)
    }

    def __init__(self, parent):

        Button.__init__(self, parent, self._gfx)

        self.widget_type = "panel_bottom"

        if not self.height:
            CollapsedPanelBottom.height = self.get_min_size()[1]

        node = self.node
        node.name = "collapsed_panel_bottom"
        node.set_z(-CollapsedPanelHeader.height)
        self._hook_node = hook_node = node.attach_new_node("hook_node")
        hook_node.set_z(-self.height)

    def set_pos(self, pos): pass

    def get_hook_node(self):

        return self._hook_node

    def update_images(self):

        if self.images:

            self._images = self.images

        else:

            Widget.update_images(self)
            width, height = self.get_size()
            tex_atlas = TextureAtlas["image"]
            tex_atlas_regions = TextureAtlas["regions"]

            for state in ("normal", "hilited"):
                x, y, w, h = tex_atlas_regions[f"collapsed_panel_arrow_{state}"]
                img = PNMImage(w, h, 4)
                img.copy_sub_image(tex_atlas, 0, 0, x, y, w, h)
                image = self._images[state]
                x = (width - w) // 2
                y = height - h
                image.blend_sub_image(img, x, y, 0, 0, w, h)

            CollapsedPanelBottom.images = self._images

    def on_left_up(self):

        if Button.on_left_up(self):
            self.parent.expand()

    def on_leave(self):

        if self.parent.is_expanded():
            self._current_state = "normal"
            return

        Button.on_leave(self)

    def is_hidden(self, check_ancestors=True):

        return self.parent.is_hidden(check_ancestors=True)


class PanelContainer(Widget):

    _gfx = {"": (("panel_main",),)}

    def __init__(self, parent):

        Widget.__init__(self, "panel_container", parent, self._gfx, "", "both", has_mouse_region=False)

        sizer = Sizer("vertical")
        self.set_sizer(sizer)
        self._mouse_region_group = set()

        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        node = self.node
        node.name = "panel_container"
        node.set_pos(l, 0, -t)
        self._bottom_node = bottom_node = node.attach_new_node("panel_container_bottom")
        bottom_node.set_x(-l)
        self._hook_node = hook_node = bottom_node.attach_new_node("hook_node")

    def finalize(self):

        mouse_region_group = self._mouse_region_group

        for widget in self.get_sizer().get_widgets():

            mouse_region = widget.mouse_region

            if mouse_region:
                mouse_region_group.add(mouse_region)

        if self.is_hidden(check_ancestors=False):

            mouse_watcher = self.mouse_watcher

            for mouse_region in mouse_region_group:
                mouse_watcher.remove_region(mouse_region)

    def set_pos(self, pos): pass

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = new_size = Widget.set_size(self, size, includes_borders, is_min)
        self._bottom_node.set_z(-height)

        return new_size

    def update_images(self, recurse=True, size=None):

        if recurse:
            self._sizer.update_images()

    def get_image(self, state=None, composed=True):

        w, h = self.get_size()
        x, y = self.get_pos()
        image = PNMImage(w, h, 4)
        parent_img = self.parent.get_image(composed=False)
        image.copy_sub_image(parent_img, 0, 0, x, y, w, h)

        if composed:
            image = self._sizer.get_composed_image(image)

        return image

    def get_mouse_region_group(self):

        return self._mouse_region_group

    def get_hook_node(self):

        return self._hook_node

    def add(self, *args, **kwargs):

        self.get_sizer().add(*args, **kwargs)

    def hide(self):

        if not Widget.hide(self, recurse=False):
            return False

        if self.parent.is_expanded():

            mouse_watcher = self.mouse_watcher
            mouse_region_group = self._mouse_region_group

            for region in mouse_region_group:
                mouse_watcher.remove_region(region)

        self._hook_node.reparent_to(self.node.parent)

        return True

    def show(self):

        if not Widget.show(self, recurse=False):
            return False

        if self.parent.is_expanded():

            mouse_watcher = self.mouse_watcher
            mouse_region_group = self._mouse_region_group

            for region in mouse_region_group:

                widget_id = int(region.name.replace("widget_", ""))
                widget = Widget.registry[widget_id]

                if not widget.is_hidden():
                    mouse_watcher.add_region(region)

        self._hook_node.reparent_to(self._bottom_node)

        return True


class Panel(Widget):

    collapsed_height = 0
    _collapsed_img = None
    _gfx = {"": (("panel_main",),)}

    def __init__(self, stack, panel_id, name=""):

        Widget.__init__(self, "panel", stack, self._gfx, stretch_dir="both")

        self.id = panel_id
        self.name = name
        sizer = Sizer("vertical")
        Widget.set_sizer(self, sizer)
        self._top_container = None
        self._bottom_container = None
        self._header = header = PanelHeader(self)
        self._bottom = bottom = PanelBottom(self)
        self._collapsed_header = collapsed_header = CollapsedPanelHeader(self)
        self._collapsed_bottom = collapsed_bottom = CollapsedPanelBottom(self)
        self._client_sizer = client_sizer = Sizer("vertical")
        sizer.add(header, expand=True)
        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        borders = (0, 0, b, 0)
        sizer.add(client_sizer, expand=True, borders=borders)
        sizer.add(bottom, expand=True)
        header_region = header.mouse_region
        bottom_region = bottom.mouse_region
        collapsed_header_region = collapsed_header.mouse_region
        collapsed_bottom_region = collapsed_bottom.mouse_region
        mouse_watcher = stack.mouse_watcher
        mouse_watcher.remove_region(collapsed_header_region)
        mouse_watcher.remove_region(collapsed_bottom_region)
        regions_expanded = set([header_region, bottom_region, self.mouse_region])
        regions_collapsed = set([collapsed_header_region, collapsed_bottom_region])
        self._mouse_region_groups = {"expanded": regions_expanded, "collapsed": regions_collapsed}

        if not Panel.collapsed_height:
            Panel.collapsed_height = collapsed_header.height + collapsed_bottom.height

        # Build the node hierarchy

        prev_panels = stack.get_panels()

        if prev_panels:
            last_node = prev_panels[-1].get_hook_node()
        else:
            last_node = stack.get_widget_root_node()

        top_node = self.node
        top_node.name = f"panel_top__{panel_id}"
        top_node.reparent_to(last_node)
        self._client_node = client_node = header.node.attach_new_node("panel_client")
        client_node.set_z(-header.height)
        bottom.node.reparent_to(client_node)
        self._hook_node = bottom.get_hook_node().attach_new_node(f"panel_hook__{panel_id}")
        collapsed_header_node = collapsed_header.node
        collapsed_header_node.reparent_to(top_node)
        collapsed_bottom.node.reparent_to(collapsed_header_node)

        stack.add_panel(self)

        self._sections = []
        self._last_section_hook_node = client_node
        self._is_expanded = True
        self._widgets_to_update = []

        skin_text = Skin["text"]["panel_label"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._label = font.create_image(name, color)
        self._is_dragged = False
        self._start_mouse_y = 0
        self._start_drag_offset = 0
        self._listener = DirectObject()

    def finalize(self):

        mouse_region_group = self._mouse_region_groups["expanded"]

        if self._top_container:

            self._top_container.finalize()

            if not self._top_container.is_hidden(check_ancestors=False):
                mouse_regions = self._top_container.get_mouse_region_group()
                mouse_region_group.update(mouse_regions)

        for section in self._sections:

            section.finalize()

            if not section.is_hidden(check_ancestors=False):
                mouse_regions = section.get_mouse_region_groups()["expanded"]
                mouse_region_group.update(mouse_regions)

        if self._bottom_container:

            self._bottom_container.finalize()

            if not self._bottom_container.is_hidden(check_ancestors=False):
                mouse_regions = self._bottom_container.get_mouse_region_group()
                mouse_region_group.update(mouse_regions)

    def destroy(self):

        Widget.destroy(self)

        self._listener.ignore_all()
        self._listener = None

    def get_hook_node(self):

        return self._hook_node

    def get_collapsed_header(self):

        return self._collapsed_header

    def get_collapsed_bottom(self):

        return self._collapsed_bottom

    def set_pos(self, pos): pass

    def get_pos(self, from_root=False):

        node = self.node
        x, y, z = node.get_pos(node.get_top())
        y = -z

        return (int(x), int(y))

    def set_sizer(self, sizer): pass

    def __offset_mouse_region_frames(self):

        exclude = "lr"

        for widget in self._widgets_to_update:
            recurse = widget is not self
            widget.update_mouse_region_frames(exclude, recurse)

        self._widgets_to_update = []

    def get_top_container(self):

        if not self._top_container:

            client_node = self._client_node
            child_node = client_node.get_child(0)
            self._top_container = top_container = PanelContainer(self)
            top_container.node.reparent_to(client_node)
            hook_node = top_container.get_hook_node()
            child_node.reparent_to(hook_node)
            l, r, b, t = TextureAtlas["inner_borders"]["panel"]
            borders = (l, r, 0, t)
            self._client_sizer.add(top_container, expand=True, borders=borders)

            if self._last_section_hook_node is client_node:
                self._last_section_hook_node = hook_node

        return self._top_container

    def get_bottom_container(self):

        if not self._bottom_container:
            node = self._last_section_hook_node
            child_node = node.get_child(0)
            self._bottom_container = bottom_container = PanelContainer(self)
            bottom_container.node.reparent_to(node)
            hook_node = bottom_container.get_hook_node()
            child_node.reparent_to(hook_node)
            l, r, b, t = TextureAtlas["inner_borders"]["panel"]
            borders = (l, r, 0, t)
            self._client_sizer.add(bottom_container, expand=True, borders=borders)

        return self._bottom_container

    def show_container(self, container_id, show=True):

        container = self._top_container if container_id == "top" else self._bottom_container

        if not (container and (container.show() if show else container.hide())):
            return

        groups_expanded = self._mouse_region_groups["expanded"]
        w, h_old = self.get_size()
        h_c = container.get_size()[1]
        mouse_region_group = container.get_mouse_region_group()
        l, r, b, t = TextureAtlas["inner_borders"]["panel"]

        if show:
            groups_expanded.update(mouse_region_group)
            container.update_mouse_region_frames(exclude="lr")
            h_new = h_old + h_c + t
        else:
            groups_expanded.difference_update(mouse_region_group)
            h_new = h_old - h_c - t

        size = (w, h_new)
        self.get_sizer().set_size(size, force=True)

        widgets_to_update = self._widgets_to_update
        widgets_to_update.append(self)
        widgets_to_update.append(self._bottom)

        if container_id == "top":

            sections_to_update = [s for s in self._sections if not s.is_hidden(check_ancestors=False)]
            widgets_to_update.extend(sections_to_update)
            bottom_container = self._bottom_container

            if bottom_container and not bottom_container.is_hidden(check_ancestors=False):
                widgets_to_update.append(bottom_container)

        task = lambda: self.update_images(recurse=False)
        task_id = "update_panel_image"
        PendingTasks.add(task, task_id, id_prefix=self.id, batch_id="panel_redraw")

        task = self.__offset_mouse_region_frames
        task_id = "offset_container_mouse_region_frames"
        PendingTasks.add(task, task_id, id_prefix=self.id, batch_id="panel_mouse_region_update")

        if self._is_expanded:
            self.parent.handle_panel_resize(self)

    def handle_section_change(self, changed_section, change=""):

        groups_expanded = self._mouse_region_groups["expanded"]
        w, h_old = self.get_size()
        h_s = changed_section.get_size()[1]
        mouse_region_groups = changed_section.get_mouse_region_groups()
        l, r, b, t = TextureAtlas["inner_borders"]["panel"]

        if change == "collapse":

            groups_expanded.difference_update(mouse_region_groups["expanded"])
            groups_expanded.update(mouse_region_groups["collapsed"])
            h_new = h_old - h_s + changed_section.collapsed_height

        elif change == "expand":

            groups_expanded.difference_update(mouse_region_groups["collapsed"])
            groups_expanded.update(mouse_region_groups["expanded"])
            h_new = h_old + h_s - changed_section.collapsed_height

        elif change == "hide":

            if changed_section.is_expanded():
                groups_expanded.difference_update(mouse_region_groups["expanded"])
            else:
                groups_expanded.difference_update(mouse_region_groups["collapsed"])
                h_s = changed_section.collapsed_height

            h_new = h_old - h_s - t

        elif change == "show":

            if changed_section.is_expanded():
                groups_expanded.update(mouse_region_groups["expanded"])
            else:
                groups_expanded.update(mouse_region_groups["collapsed"])
                h_s = changed_section.collapsed_height

            h_new = h_old + h_s + t
            changed_section.update_mouse_region_frames(exclude="lr")

        size = (w, h_new)
        self.get_sizer().set_size(size, force=True)

        widgets_to_update = self._widgets_to_update
        widgets_to_update.append(self)
        index = self._sections.index(changed_section)
        sections_to_update = [s for s in self._sections[index + 1:]
            if not s.is_hidden(check_ancestors=False)]
        widgets_to_update.extend(sections_to_update)
        widgets_to_update.append(self._bottom)
        bottom_container = self._bottom_container

        if bottom_container and not bottom_container.is_hidden(check_ancestors=False):
            widgets_to_update.append(bottom_container)

        task = lambda: self.update_images(recurse=False)
        task_id = "update_panel_image"
        PendingTasks.add(task, task_id, id_prefix=self.id, batch_id="panel_redraw")

        task = self.__offset_mouse_region_frames
        task_id = "offset_section_mouse_region_frames"
        PendingTasks.add(task, task_id, id_prefix=self.id, batch_id="panel_mouse_region_update")

        if self._is_expanded:
            self.parent.handle_panel_resize(self)

    def expand(self, expand=True):

        if self._is_expanded == expand:
            return

        self._is_expanded = expand
        self.set_contents_hidden(not expand)
        mouse_watcher = self.parent.mouse_watcher
        mouse_region_groups = self._mouse_region_groups

        for region in mouse_region_groups["collapsed" if expand else "expanded"]:
            mouse_watcher.remove_region(region)

        if expand:

            for region in mouse_region_groups["expanded"]:

                widget_id = int(region.name.replace("widget_", ""))
                widget = Widget.registry[widget_id]

                if (widget in (self, self._header, self._bottom)
                        or widget.widget_type == "section_header"
                        or not widget.is_hidden()):
                    mouse_watcher.add_region(region)

        else:

            for region in mouse_region_groups["collapsed"]:
                mouse_watcher.add_region(region)

        if expand:
            self._hook_node.reparent_to(self._bottom.get_hook_node())
        else:
            self._hook_node.reparent_to(self._collapsed_bottom.get_hook_node())

        self.parent.handle_panel_resize(self)

    def is_expanded(self):

        return self._is_expanded

    def update_images(self, recurse=True, size=None):

        images = Widget.update_images(self, recurse, size)

        if not self._collapsed_img:
            collapsed_header = self._collapsed_header
            collapsed_header_img = collapsed_header.get_image()
            w, h_ch = collapsed_header.get_size()
            image = PNMImage(w, self.collapsed_height, 4)
            image.copy_sub_image(collapsed_header_img, 0, 0, 0, 0, w, h_ch)
            collapsed_bottom = self._collapsed_bottom
            collapsed_bottom_img = collapsed_bottom.get_image()
            h_cb = collapsed_bottom.get_size()[1]
            image.copy_sub_image(collapsed_bottom_img, 0, h_ch, 0, 0, w, h_cb)
            Panel._collapsed_img = image

        return images

    def get_image(self, state=None, composed=True):

        if self._is_expanded:
            image = Widget.get_image(self, state, composed)
        else:
            image = PNMImage(self._collapsed_img)

        if composed:
            width, height = self._header.get_size()
            l, r, b, t = TextureAtlas["inner_borders"]["panel_header"]
            w, h = self._label.size
            x = (width - w) // 2
            y = t + (height - b - t - h) // 2 + 1
            image.blend_sub_image(self._label, x, y, 0, 0, w, h)

        return image

    def add_section(self, section_id, label="", hidden=False):

        section = PanelSection(self, section_id, label, hidden)
        self._sections.append(section)
        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        borders = (l, r, 0, t)
        self._client_sizer.add(section, expand=True, borders=borders)

        section.node.reparent_to(self._last_section_hook_node)
        hook_node = section.get_hook_node()
        self._bottom.node.reparent_to(hook_node)

        if hidden:
            section.get_hook_node().reparent_to(self._last_section_hook_node)

        self._last_section_hook_node = hook_node

        return section

    def get_sections(self):

        return self._sections

    def get_section(self, section_id):

        return PanelSection.registry[section_id]

    def on_enter(self):

        Mgr.set_cursor("drag" if self._is_dragged else "hand")

    def on_leave(self):

        if not self._is_dragged:
            if Mgr.get("active_input_field") and not Menu.is_menu_shown():
                Mgr.set_cursor("input_commit")
            else:
                Mgr.set_cursor("main")

    def __drag(self, task):

        mouse_y = int(Mgr.get("mouse_pointer", 0).y)

        if mouse_y != self._start_mouse_y:
            scrollthumb = self.parent.get_scrollthumb()
            scrollthumb.set_offset(self._start_drag_offset - mouse_y + self._start_mouse_y)

        return task.cont

    def on_left_down(self):

        self._is_dragged = True
        self._start_mouse_y = int(Mgr.get("mouse_pointer", 0).y)
        scrollthumb = self.parent.get_scrollthumb()
        self._start_drag_offset = scrollthumb.get_offset()
        Mgr.add_task(self.__drag, "drag panel")
        self._listener.accept("gui_mouse1-up", self.__on_left_up)
        Mgr.set_cursor("drag")

    def __on_left_up(self):

        if self._is_dragged:
            region = self.mouse_watcher.get_over_region()
            Mgr.set_cursor("hand" if region == self.mouse_region else "main")
            self._listener.ignore("gui_mouse1-up")
            Mgr.remove_task("drag panel")
            self._start_mouse_y = 0
            self._start_drag_offset = 0
            self._is_dragged = False

    def on_right_up(self):

        self.parent.show_menu(self)

    def hide(self):

        if not Widget.hide(self, recurse=False):
            return False

        mouse_watcher = self.mouse_watcher
        mouse_region_groups = self._mouse_region_groups

        for region in mouse_region_groups["expanded" if self._is_expanded else "collapsed"]:
            mouse_watcher.remove_region(region)

        self._hook_node.reparent_to(self.node.parent)

        return True

    def show(self):

        if not Widget.show(self, recurse=False):
            return False

        mouse_watcher = self.mouse_watcher
        mouse_region_groups = self._mouse_region_groups

        if self._is_expanded:

            for region in mouse_region_groups["expanded"]:

                widget_id = int(region.name.replace("widget_", ""))
                widget = Widget.registry[widget_id]

                if (widget in (self, self._header, self._bottom)
                        or widget.widget_type == "section_header"
                        or not widget.is_hidden()):
                    mouse_watcher.add_region(region)

        else:

            for region in mouse_region_groups["collapsed"]:
                mouse_watcher.add_region(region)

        if self._is_expanded:
            self._hook_node.reparent_to(self._bottom.get_hook_node())
        else:
            self._hook_node.reparent_to(self._collapsed_bottom.get_hook_node())

        return True

    def enable_hotkeys(self, enable=True):

        for widget in self._client_sizer.get_widgets():
            if widget.widget_type == "panel_button":
                widget.enable_hotkey(enable)

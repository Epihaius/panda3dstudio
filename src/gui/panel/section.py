from ..base import *
from ..group import WidgetGroup


class PanelWidgetGroup(WidgetGroup):

    def __init__(self, parent, label=""):

        WidgetGroup.__init__(self, parent, "panel_main", "panel", label)

    def add_group(self, label="", add_top_border=True):

        group = PanelWidgetGroup(self, label)
        WidgetGroup.add_group(self, group, add_top_border)

        return group


class SectionHeader(Widget):

    images = {}
    _gfx = {
        "": (
            ("panel_section_header_topleft", "panel_section_header_top",
             "panel_section_header_topright"),
            ("panel_section_header_left", "panel_section_header_center",
             "panel_section_header_right"),
            ("panel_section_header_bottomleft", "panel_section_header_bottom",
             "panel_section_header_bottomright")
        )
    }

    def __init__(self, parent):

        Widget.__init__(self, "section_header", parent, self._gfx, stretch_dir="horizontal")

    def set_size(self, size, includes_borders=True, is_min=False):

        Widget.set_size(self, size, includes_borders, is_min)
        self.get_parent().get_collapsed_header().set_size(size)

    def set_pos(self, pos): pass

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            images = Widget.update_images(self)
            image = images[""]
            x, y, w, h = TextureAtlas["regions"]["section_header_minus"]
            l = self.get_gfx_inner_borders()[0]
            height = self.get_size()[1]
            tex_atlas = TextureAtlas["image"]
            image.blend_sub_image(tex_atlas, l, (height - h) // 2, x, y, w, h)
            SectionHeader.images = images

        self.get_parent().get_collapsed_header().update_images()

    def update_mouse_region_frames(self, exclude=""):

        Widget.update_mouse_region_frames(self, exclude)
        self.get_parent().get_collapsed_header().update_mouse_region_frames(exclude)

    def on_left_up(self):

        self.get_parent().expand(False)


class CollapsedSectionHeader(Widget):

    images = {}
    height = 0
    _gfx = {
        "": (
            ("panel_section_border_topleft", "panel_section_border_top",
             "panel_section_border_topright"),
            ("panel_section_border_left", "panel_main", "panel_section_border_right"),
            ("panel_section_border_bottomleft", "panel_section_border_bottom",
             "panel_section_border_bottomright")
        )
    }

    def __init__(self, parent):

        Widget.__init__(self, "section_header", parent, self._gfx, stretch_dir="horizontal")

        if not self.height:
            CollapsedSectionHeader.height = self.get_min_size()[1]

        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        self._hook_node = hook_node = self.get_node().attach_new_node("hook_node")
        hook_node.set_pos(-l, 0, -self.height)

    def set_pos(self, pos): pass

    def get_hook_node(self):

        return self._hook_node

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            images = Widget.update_images(self)
            image = images[""]
            x, y, w, h = TextureAtlas["regions"]["section_header_plus"]
            l = self.get_gfx_inner_borders()[0]
            height = self.get_size()[1]
            tex_atlas = TextureAtlas["image"]
            image.blend_sub_image(tex_atlas, l, (height - h) // 2, x, y, w, h)
            CollapsedSectionHeader.images = images

    def on_left_up(self):

        self.get_parent().expand()


class PanelSection(Widget):

    registry = {}
    collapsed_height = 0
    _gfx = {
        "": (
            ("panel_section_border_topleft", "panel_section_border_top",
             "panel_section_border_topright"),
            ("panel_section_border_left", "panel_main", "panel_section_border_right"),
            ("panel_section_border_bottomleft", "panel_section_border_bottom",
             "panel_section_border_bottomright")
        )
    }

    def __init__(self, parent, section_id, name="", hidden=False):

        Widget.__init__(self, "panel_section", parent, self._gfx, stretch_dir="both",
                        hidden=hidden, has_mouse_region=False)

        self.registry[section_id] = self
        self._id = section_id

        sizer = Sizer("vertical")
        Widget.set_sizer(self, sizer)
        self._header = header = SectionHeader(self)
        self._collapsed_header = collapsed_header = CollapsedSectionHeader(self)
        sizer.add(header, expand=True)
        self._client_sizer = client_sizer = Sizer("vertical")
        l, r, b, t = TextureAtlas["inner_borders"]["section"]
        borders = (l, r, b, t)
        sizer.add(client_sizer, expand=True, borders=borders)
        header_region = header.get_mouse_region()
        collapsed_header_region = collapsed_header.get_mouse_region()
        mouse_watcher = parent.get_mouse_watcher()
        mouse_watcher.remove_region(collapsed_header_region)
        regions_expanded = set([header_region])
        regions_collapsed = set([collapsed_header_region])
        self._mouse_region_groups = {"expanded": regions_expanded, "collapsed": regions_collapsed}

        if not PanelSection.collapsed_height:
            PanelSection.collapsed_height = collapsed_header.height

        # Build the node hierarchy

        top_node = self.get_node()
        top_node.set_name("section_top__{}".format(section_id))
        l, r, b, t = TextureAtlas["inner_borders"]["panel"]
        top_node.set_pos(l, 0, -t)
        self._bottom_node = bottom_node = top_node.attach_new_node("section_bottom")
        bottom_node.set_x(-l)
        collapsed_header.get_hook_node().reparent_to(top_node)
        self._hook_node = bottom_node.attach_new_node("section_hook__{}".format(section_id))

        self._is_expanded = True

        skin_text = Skin["text"]["panel_section_label"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._label = font.create_image(name, color)

    def finalize(self):

        mouse_region_group = self._mouse_region_groups["expanded"]

        for widget in self._client_sizer.get_widgets():

            mouse_region = widget.get_mouse_region()

            if mouse_region:
                mouse_region_group.add(mouse_region)

        if self.is_hidden(check_ancestors=False):

            mouse_watcher = self.get_mouse_watcher()

            for mouse_region in mouse_region_group:
                mouse_watcher.remove_region(mouse_region)

    def get_id(self):

        return self._id

    def get_hook_node(self):

        return self._hook_node

    def get_collapsed_header(self):

        return self._collapsed_header

    def set_pos(self, pos): pass

    def set_sizer(self, sizer): pass

    def get_client_sizer(self):

        return self._client_sizer

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = new_size = Widget.set_size(self, size, includes_borders, is_min)
        self._bottom_node.set_z(-height)

        return new_size

    def add(self, *args, **kwargs):

        self._client_sizer.add(*args, **kwargs)

    def add_group(self, label=""):

        group = PanelWidgetGroup(self, label)
        l, r, b, t = TextureAtlas["inner_borders"]["section"]
        borders = (0, 0, 0, t)
        self._client_sizer.add(group, expand=True, borders=borders)

        return group

    def expand(self, expand=True):

        if self._is_expanded == expand:
            return

        self._is_expanded = expand
        self.set_contents_hidden(not expand)

        if self.is_hidden(check_ancestors=False):
            return

        if self.get_parent().is_expanded():

            mouse_watcher = self.get_mouse_watcher()
            mouse_region_groups = self._mouse_region_groups

            for region in mouse_region_groups["collapsed" if expand else "expanded"]:
                mouse_watcher.remove_region(region)

            if expand:

                for region in mouse_region_groups["expanded"]:

                    name = region.get_name()
                    widget_id = int(name.replace("widget_", ""))
                    widget = Widget.registry[widget_id]

                    if widget is self._header or not widget.is_hidden():
                        mouse_watcher.add_region(region)

            else:

                for region in mouse_region_groups["collapsed"]:
                    mouse_watcher.add_region(region)

        if expand:
            self._hook_node.reparent_to(self._bottom_node)
        else:
            self._hook_node.reparent_to(self._collapsed_header.get_hook_node())

        self.get_parent().handle_section_change(self, "expand" if expand else "collapse")

    def is_expanded(self):

        return self._is_expanded

    def hide(self):

        if not Widget.hide(self, recurse=False):
            return False

        if self.get_parent().is_expanded():

            mouse_watcher = self.get_mouse_watcher()
            mouse_region_groups = self._mouse_region_groups

            for region in mouse_region_groups["expanded" if self._is_expanded else "collapsed"]:
                mouse_watcher.remove_region(region)

        self._hook_node.reparent_to(self.get_node().get_parent())

        self.get_parent().handle_section_change(self, "hide")

        return True

    def show(self):

        if not Widget.show(self, recurse=False):
            return False

        if self.get_parent().is_expanded():

            mouse_watcher = self.get_mouse_watcher()
            mouse_region_groups = self._mouse_region_groups

            if self._is_expanded:

                for region in mouse_region_groups["expanded"]:

                    name = region.get_name()
                    widget_id = int(name.replace("widget_", ""))
                    widget = Widget.registry[widget_id]

                    if widget is self._header or not widget.is_hidden():
                        mouse_watcher.add_region(region)

            else:

                for region in mouse_region_groups["collapsed"]:
                    mouse_watcher.add_region(region)

        if self._is_expanded:
            self._hook_node.reparent_to(self._bottom_node)
        else:
            self._hook_node.reparent_to(self._collapsed_header.get_hook_node())

        self.get_parent().handle_section_change(self, "show")

        return True

    def get_image(self, state=None, composed=True):

        if self._is_expanded:

            if self._current_state not in self._images:
                return PNMImage(0, 0, 4)

            image = PNMImage(self._images[self._current_state])

            if composed:
                image = self._sizer.get_composed_image(image)

        else:

            image = PNMImage(self._collapsed_header.get_image())

        if composed:
            width, height = self._collapsed_header.get_size()
            w = self._label.get_x_size()
            h = self._label.get_y_size()
            x = (width - w) // 2
            y = (height - h) // 2 + 1
            image.blend_sub_image(self._label, x, y, 0, 0, w, h)

        return image

    def get_mouse_region_groups(self):

        return self._mouse_region_groups

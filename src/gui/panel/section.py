from ..base import *


class SectionHeader(Widget):

    images = {}

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["panel_section"]["expanded_header"]}

        Widget.__init__(self, "section_header", parent, gfx_ids)

    def set_size(self, size, includes_borders=True, is_min=False):

        Widget.set_size(self, size, includes_borders, is_min)
        self.parent.get_collapsed_header().set_size(size)

    def set_pos(self, pos): pass

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            images = Widget.update_images(self)
            image = images[""]
            gfx_id = Skin.atlas.gfx_ids["panel_section"]["header_signs"][0][0]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            l = self.gfx_inner_borders[0]
            height = self.get_size()[1]
            tex_atlas = Skin.atlas.image
            image.blend_sub_image(tex_atlas, l, (height - h) // 2, x, y, w, h)
            SectionHeader.images = images

        self.parent.get_collapsed_header().update_images()

    def update_mouse_region_frames(self, exclude=""):

        Widget.update_mouse_region_frames(self, exclude)
        self.parent.get_collapsed_header().update_mouse_region_frames(exclude)

    def on_left_up(self):

        self.parent.expand(False)


class CollapsedSectionHeader(Widget):

    images = {}
    height = 0

    def __init__(self, parent):

        gfx_ids = {"": Skin.atlas.gfx_ids["panel_section"]["collapsed_header"]}

        Widget.__init__(self, "section_header", parent, gfx_ids)

        if not self.height:
            CollapsedSectionHeader.height = self.min_size[1]

        l, r, b, t = Skin.atlas.inner_borders["panel"]
        self.hook_node = self.node.attach_new_node("hook_node")
        self.hook_node.set_pos(-l, 0, -self.height)

    def set_pos(self, pos): pass

    def update_images(self):

        if self.images:
            self._images = self.images
        else:
            images = Widget.update_images(self)
            image = images[""]
            gfx_id = Skin.atlas.gfx_ids["panel_section"]["header_signs"][0][1]
            x, y, w, h = Skin.atlas.regions[gfx_id]
            l = self.gfx_inner_borders[0]
            height = self.get_size()[1]
            tex_atlas = Skin.atlas.image
            image.blend_sub_image(tex_atlas, l, (height - h) // 2, x, y, w, h)
            CollapsedSectionHeader.images = images

    def on_left_up(self):

        self.parent.expand()


class PanelSection(Widget):

    registry = {}
    collapsed_height = 0

    def __init__(self, parent, section_id, title="", hidden=False):

        gfx_ids = {"": Skin.atlas.gfx_ids["panel_section"][""]}

        Widget.__init__(self, "panel_section", parent, gfx_ids, hidden=hidden,
                        has_mouse_region=False)

        self.registry[section_id] = self
        self.id = section_id

        sizer = Sizer("vertical")
        sizer.set_column_proportion(0, 1.)
        Widget.sizer.fset(self, sizer)
        self._header = header = SectionHeader(self)
        self._collapsed_header = collapsed_header = CollapsedSectionHeader(self)
        sizer.add(header)
        self._client_sizer = client_sizer = Sizer("vertical")
        client_sizer.set_column_proportion(0, 1.)
        l, r, b, t = Skin.atlas.inner_borders["section"]
        borders = (l, r, b, t)
        sizer.add(client_sizer, borders=borders)
        header_region = header.mouse_region
        collapsed_header_region = collapsed_header.mouse_region
        mouse_watcher = parent.mouse_watcher
        mouse_watcher.remove_region(collapsed_header_region)
        regions_expanded = {header_region}
        regions_collapsed = {collapsed_header_region}
        self._mouse_region_groups = {"expanded": regions_expanded, "collapsed": regions_collapsed}

        if not PanelSection.collapsed_height:
            PanelSection.collapsed_height = collapsed_header.height

        # Build the node hierarchy

        top_node = self.node
        top_node.name = f"section_top__{section_id}"
        l, r, b, t = Skin.atlas.inner_borders["panel"]
        top_node.set_pos(l, 0, -t)
        self._bottom_node = bottom_node = top_node.attach_new_node("section_bottom")
        bottom_node.set_x(-l)
        collapsed_header.hook_node.reparent_to(top_node)
        self.hook_node = bottom_node.attach_new_node(f"section_hook__{section_id}")

        self._is_expanded = True

        skin_text = Skin.text["panel_section_label"]
        font = skin_text["font"]
        color = skin_text["color"]
        self._label = font.create_image(title, color)
        tex_atlas_regions = Skin.atlas.regions
        gfx_ids = Skin.atlas.gfx_ids["panel_section"]["header_signs"]
        offset = tex_atlas_regions[gfx_ids[0][0]][2]
        offset += Skin.options["section_label_offset"]
        gfx_ids = Skin.atlas.gfx_ids["panel_section"]["expanded_header"]
        w_l = tex_atlas_regions[gfx_ids[0][0]][2]
        w_r = tex_atlas_regions[gfx_ids[0][2]][2]
        sizer.default_size = (w_l + offset + self._label.size[0] + w_r, 1)

    def finalize(self):

        mouse_region_group = self._mouse_region_groups["expanded"]

        for widget in self._client_sizer.get_widgets():

            mouse_region = widget.mouse_region

            if mouse_region:
                mouse_region_group.add(mouse_region)

    def get_mouse_region_groups(self):

        return self._mouse_region_groups

    def get_collapsed_header(self):

        return self._collapsed_header

    def set_pos(self, pos): pass

    @property
    def sizer(self):

        return Widget.sizer.fget(self)

    @sizer.setter
    def sizer(self, sizer): pass

    @property
    def client_sizer(self):

        return self._client_sizer

    def set_size(self, size, includes_borders=True, is_min=False):

        width, height = new_size = Widget.set_size(self, size, includes_borders, is_min)
        self._bottom_node.set_z(-height)

        return new_size

    def expand(self, expand=True):

        if self._is_expanded == expand:
            return

        self._is_expanded = expand
        self.contents_hidden = not expand

        if self.is_hidden(check_ancestors=False):
            return

        if self.parent.is_expanded():

            mouse_watcher = self.mouse_watcher
            mouse_region_groups = self._mouse_region_groups

            for region in mouse_region_groups["collapsed" if expand else "expanded"]:
                mouse_watcher.remove_region(region)

            if expand:

                for region in mouse_region_groups["expanded"]:

                    widget_id = int(region.name.replace("widget_", ""))
                    widget = Widget.registry[widget_id]

                    if widget is self._header or not widget.is_hidden():
                        mouse_watcher.add_region(region)

            else:

                for region in mouse_region_groups["collapsed"]:
                    mouse_watcher.add_region(region)

        if expand:
            self.hook_node.reparent_to(self._bottom_node)
        else:
            self.hook_node.reparent_to(self._collapsed_header.hook_node)

        self.parent.handle_section_change(self, "expand" if expand else "collapse")

    def is_expanded(self):

        return self._is_expanded

    def hide(self):

        if not Widget.hide(self, recurse=False):
            return False

        self.sizer_cell.object = (0, 0)
        self.sizer_cell.borders = None

        if self.parent.is_expanded():

            mouse_watcher = self.mouse_watcher
            mouse_region_groups = self._mouse_region_groups

            for region in mouse_region_groups["expanded" if self._is_expanded else "collapsed"]:
                mouse_watcher.remove_region(region)

        self.hook_node.reparent_to(self.node.parent)

        self.parent.handle_section_change(self, "hide")

        return True

    def show(self):

        if not Widget.show(self, recurse=False):
            return False

        self.sizer_cell.object = self
        l, r, b, t = Skin.atlas.inner_borders["panel"]
        self.sizer_cell.borders = (l, r, 0, t)

        if self.parent.is_expanded():

            mouse_watcher = self.mouse_watcher
            mouse_region_groups = self._mouse_region_groups

            if self._is_expanded:

                for region in mouse_region_groups["expanded"]:

                    widget_id = int(region.name.replace("widget_", ""))
                    widget = Widget.registry[widget_id]

                    if widget is self._header or not widget.is_hidden():
                        mouse_watcher.add_region(region)

            else:

                for region in mouse_region_groups["collapsed"]:
                    mouse_watcher.add_region(region)

        if self._is_expanded:
            self.hook_node.reparent_to(self._bottom_node)
        else:
            self.hook_node.reparent_to(self._collapsed_header.hook_node)

        self.parent.handle_section_change(self, "show")

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
            w, h = self._label.size
            gfx_ids = Skin.atlas.gfx_ids["panel_section"]["header_signs"]
            offset = Skin.atlas.regions[gfx_ids[0][0]][2]
            offset += Skin.options["section_label_offset"]
            x = (width - w + offset) // 2
            y = (height - h) // 2 + 1
            image.blend_sub_image(self._label, x, y, 0, 0, w, h)

        return image

from ..base import *
from ..menu import Menu
from ..dialog import Dialog
from ..scroll import ScrollPaneFrame, ScrollPane
from .panel import ControlPanel


class ControlPane(ScrollPane):

    def __init__(self, frame_parent):

        frame_gfx_ids = {"": Skin.atlas.gfx_ids["scrollframe"]["panel"]}
        bar_gfx_ids = {"": Skin.atlas.gfx_ids["scrollbar"]["panel"]}
        thumb_gfx_ids = Skin.atlas.gfx_ids["panel_scrollthumb"]
        append_scrollbar = not Skin.options["panel_scrollbar_left"]

        ScrollPane.__init__(self, frame_parent, "control_pane", "vertical", "gui", frame_gfx_ids,
                            bar_gfx_ids, thumb_gfx_ids, "control_pane_scrollbar",
                            append_scrollbar=append_scrollbar)

        self._panels = []
        self._panels_to_update = set()
        self._panels_to_resize = set()
        self._panels_to_hide = set()
        self._panels_to_show = set()
        self._panel_heights = []
        self._is_contents_locked = False
        self._clicked_panel = None

        self.sizer.set_column_proportion(0, 1.)

        self._menu = menu = Menu()
        item = menu.add("panels", "Panels", item_type="submenu")
        submenu = item.get_submenu()
        item = submenu.add("scroll_to_panel", "Scroll to", item_type="submenu")
        self._panel_menu = item.get_submenu()
        self._panel_menu_items = []
        submenu.add("sep0", item_type="separator")
        command = lambda: self._clicked_panel.expand(False)
        submenu.add("collapse_panel", "Collapse", command)

        def command():

            for panel in self._panels:
                if not panel.is_hidden() and panel is not self._clicked_panel:
                    panel.expand(False)

        submenu.add("collapse_other_panels", "Collapse others", command)

        def command():

            for panel in self._panels:
                if not panel.is_hidden() and panel is not self._clicked_panel:
                    panel.expand()

        submenu.add("expand_other_panels", "Expand others", command)

        def command():

            for panel in self._panels:
                if not panel.is_hidden():
                    panel.expand(False)

        submenu.add("collapse_all_panels", "Collapse all", command)
        item = menu.add("sections", "Sections", item_type="submenu")
        submenu = item.get_submenu()

        def command():

            for section in self._clicked_panel.get_sections():
                if not section.is_hidden():
                    section.expand(False)

        submenu.add("collapse_sections", "Collapse all", command)

        def command():

            for section in self._clicked_panel.get_sections():
                if not section.is_hidden():
                    section.expand()

        submenu.add("expand_sections", "Expand all", command)

    def _create_frame(self, parent, scroll_dir, cull_bin, gfx_ids, bar_gfx_ids,
                      thumb_gfx_ids, bar_inner_border_id, has_mouse_region=True):

        return ScrollPaneFrame(parent, self, gfx_ids, bar_gfx_ids, thumb_gfx_ids,
                               cull_bin, scroll_dir, bar_inner_border_id, has_mouse_region)

    def _get_mask_sort(self):

        return 100

    def _contents_needs_redraw(self):

        return not self._is_contents_locked

    def _copy_widget_images(self, pane_image): 

        for panel in self._panels:
            x_ref, y_ref = panel.get_pos(net=True)
            pane_image.copy_sub_image(panel.get_image(), x_ref, y_ref, 0, 0)

    def _can_scroll(self):

        if (self.mouse_watcher.get_over_region() is None
                or Dialog.get_dialogs() or Mgr.get("active_input_field")
                or Menu.is_menu_shown() or not Mgr.get("gui_enabled")):
            return False

        return True

    def __scroll_to_panel(self, panel):

        offset = panel.get_pos(net=True)[1]
        self.scrollthumb.set_offset(offset)

    def finalize(self):

        self.sizer.default_size = (self.virtual_size[0], 1)
        heights = self._panel_heights
        menu = self._panel_menu
        panel_menu_items = self._panel_menu_items
        command = lambda: None
        update = False

        for panel in self._panels:
            update = panel.finalize() or update
            command = lambda p=panel: self.__scroll_to_panel(p)
            item = menu.add(f"panel_{panel.id}", panel.title, command)
            panel_menu_items.append(item)

        self._menu.update()

        for panel in self._panels:
            heights.append(panel.get_size()[1])

        if update:
            Mgr.get("window").update(Mgr.get("window_size"))

        self.sizer.cell_size_locked = True
        self.sizer.mouse_regions_locked = True
        self._is_contents_locked = True

    def destroy(self):

        ScrollPane.destroy(self)

        self._clicked_panel = None
        self._menu.destroy()
        self._menu = None

    def show_menu(self, panel):

        self._clicked_panel = panel
        self._menu.show_at_mouse_pos()

    def set_pos(self, pos):

        WidgetCard.set_pos(self, pos)

        x, y = self.get_pos(net=True)
        self.widget_root_node.set_pos(x, 0, -y + self.scrollthumb.get_offset())

    def add_panel(self, panel):

        self._panels.append(panel)
        self.sizer.add(panel)

    def get_panels(self):

        return self._panels

    def __offset_mouse_region_frames(self):

        exclude = "lr"

        for panel in self._panels_to_update:
            if not panel.is_hidden():
                panel.update_mouse_region_frames(exclude)

        self._panels_to_update = set()

    def __handle_panel_resize(self):

        heights = self._panel_heights
        new_heights = heights[:]
        h_virt_new = self.virtual_size[1]
        regions_to_copy = []
        prev_i = 0
        w = 0

        for i, panel in enumerate(self._panels):

            if panel in self._panels_to_hide | self._panels_to_show:
                continue

            if panel in self._panels_to_resize and not panel.is_hidden():

                w, h = panel.get_size()
                old_height = heights[i]
                new_height = h if panel.is_expanded() else ControlPanel.collapsed_height
                new_heights[i] = new_height
                h_virt_new += new_height - old_height
                dh = sum(heights[prev_i:i])

                if dh:
                    y_dest = sum(new_heights[:prev_i])
                    y_src = sum(heights[:prev_i])
                    regions_to_copy.append((y_dest, y_src, dh))

                prev_i = i + 1

        if w == 0:
            self._panels_to_resize = set()
            return

        dh = sum(heights[prev_i:len(self._panels)])

        if dh:
            y_dest = sum(new_heights[:prev_i])
            y_src = sum(heights[:prev_i])
            regions_to_copy.append((y_dest, y_src, dh))

        self._panel_heights = new_heights

        img = self._image
        img_new = PNMImage(w, h_virt_new)

        for y_dest, y_src, dh in regions_to_copy:
            img_new.copy_sub_image(img, 0, y_dest, 0, y_src, w, dh)

        for panel in self._panels_to_resize:
            img_new.copy_sub_image(panel.get_image(), 0, panel.get_pos(net=True)[1], 0, 0)

        tex = self.texture
        tex.load(img_new)
        self._image = img_new
        self.virtual_size = (w, h_virt_new)

        tex_offset_y = self.quad.get_tex_offset(TextureStage.default)[1]

        width, height = self.get_size()
        tex_scale = (1., min(1., height / h_virt_new))
        x, y = self.get_pos(net=True)
        l = x
        r = x + width
        b = -(y + min(height, h_virt_new))
        t = -y
        quad = self.create_quad((l, r, b, t))

        if not GD["config"]["gui_view"]["control_pane"]:
            quad.detach_node()

        quad.set_texture(tex)
        quad.set_y(-1.)
        quad.set_tex_scale(TextureStage.default, *tex_scale)
        self.reset_sub_image_index()
        self.scrollthumb.update()
        self.update_mouse_region_frames()
        index = 0

        for i, panel in enumerate(self._panels):
            if panel in self._panels_to_resize:
                index = i
                break

        self._panels_to_update.update(self._panels[index + 1:])

        task = self.__offset_mouse_region_frames
        task_id = "offset_panel_mouse_region_frames"
        PendingTasks.add(task, task_id, batch_id="panel_mouse_region_update")

        self._panels_to_resize = set()

    def handle_panel_resize(self, panel):

        self._panels_to_resize.add(panel)
        task = self.__handle_panel_resize
        task_id = "handle_panel_resize"
        PendingTasks.add(task, task_id, batch_id="panel_change")

    def __toggle_panels(self):

        heights = self._panel_heights
        new_heights = heights[:]
        h_virt_new = self.virtual_size[1]
        regions_to_copy = []
        prev_i = 0

        for i, panel in enumerate(self._panels):

            if panel in self._panels_to_hide:

                old_height = heights[i]
                new_heights[i] = 0
                h_virt_new -= old_height
                dh = sum(heights[prev_i:i])

                if dh:
                    y_dest = sum(new_heights[:prev_i])
                    y_src = sum(heights[:prev_i])
                    regions_to_copy.append((y_dest, y_src, dh))

                prev_i = i + 1

            elif panel in self._panels_to_show:

                w, h = panel.get_size()
                new_height = h if panel.is_expanded() else ControlPanel.collapsed_height
                new_heights[i] = new_height
                h_virt_new += new_height
                dh = sum(heights[prev_i:i])

                if dh:
                    y_dest = sum(new_heights[:prev_i])
                    y_src = sum(heights[:prev_i])
                    regions_to_copy.append((y_dest, y_src, dh))

                prev_i = i + 1

        dh = sum(heights[prev_i:len(self._panels)])

        if dh:
            y_dest = sum(new_heights[:prev_i])
            y_src = sum(heights[:prev_i])
            regions_to_copy.append((y_dest, y_src, dh))

        self._panel_heights = new_heights

        img = self._image
        w = img.size[0]
        img_new = PNMImage(w, h_virt_new)

        for y_dest, y_src, dh in regions_to_copy:
            img_new.copy_sub_image(img, 0, y_dest, 0, y_src, w, dh)

        for panel in self._panels_to_show:
            img_new.copy_sub_image(panel.get_image(), 0, panel.get_pos(net=True)[1], 0, 0)

        tex = self.texture
        tex.load(img_new)
        self._image = img_new
        self.virtual_size = (w, h_virt_new)

        tex_offset_y = self._quad.get_tex_offset(TextureStage.default)[1]
        self._quad.detach_node()

        width, height = self.get_size()
        tex_scale = (1., min(1., height / h_virt_new))
        x, y = self.get_pos(net=True)
        l = x
        r = x + width
        b = -(y + min(height, h_virt_new))
        t = -y
        cm = CardMaker("control_pane_quad")
        cm.set_frame(l, r, b, t)
        self._quad = quad = NodePath(cm.generate())

        if GD["config"]["gui_view"]["control_pane"]:
            quad.reparent_to(Mgr.get("gui_root"))

        quad.set_texture(tex)
        quad.set_y(-1.)
        quad.set_tex_scale(TextureStage.default, *tex_scale)
        self.reset_sub_image_index()
        self.scrollthumb.update()
        self.update_mouse_region_frames()
        index = 0

        for i, panel in enumerate(self._panels):
            if panel in self._panels_to_hide or panel in self._panels_to_show:
                index = i
                break

        self._panels_to_update.update(self._panels[index + 1:])

        task = self.__offset_mouse_region_frames
        task_id = "offset_panel_mouse_region_frames"
        PendingTasks.add(task, task_id, batch_id="panel_mouse_region_update")

        self._panels_to_hide = set()
        self._panels_to_show = set()
        self._panel_menu.update()

    def show_panel(self, panel, show=True):

        r = panel.show() if show else panel.hide()

        if not r:
            return

        panels = self._panels_to_show if show else self._panels_to_hide
        panels.add(panel)

        if show:
            index = self._panels.index(panel)
            menu_item = self._panel_menu_items[index]
            shown_panels = [p for p in self._panels if not p.is_hidden()]
            index = shown_panels.index(panel)
            self._panel_menu.add_item(menu_item, index)
        else:
            self._panel_menu.remove(f"panel_{panel.id}")

        task = self.__toggle_panels
        task_id = "toggle_panels"
        PendingTasks.add(task, task_id, batch_id="panel_change")

    def hide(self):

        self._quad.detach_node()
        self.scrollthumb.quad.detach_node()
        self.scrollthumb.hide()
        self.frame.get_scrollbar().hide()
        mw = self.get_mouse_watcher_nodepath()
        mw.detach_node()
        Mgr.get("mouse_watcher").remove_region(self._mouse_region_mask)

    def show(self):

        gui_root = Mgr.get("gui_root")
        self._quad.reparent_to(gui_root)
        self.scrollthumb.quad.reparent_to(gui_root)
        self.scrollthumb.show()
        self.frame.get_scrollbar().show()
        mw = self.get_mouse_watcher_nodepath()
        mw.reparent_to(GD.showbase.mouseWatcher.parent)
        Mgr.get("mouse_watcher").add_region(self._mouse_region_mask)

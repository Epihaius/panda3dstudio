from ..base import *
from ..toolbar import *
from ..tooltip import ToolTip
from ..text import Text
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField
from ..colorbox import ColorBox
from ..checkbox import CheckBox
from ..radiobtn import RadioButton
from ..panel import (PanelStack, PanelButton, PanelInputField, PanelCheckBox, PanelColorBox,
                     PanelRadioButtonGroup, PanelComboBox)
from ..dialog import *
from .aux_viewport import AuxiliaryViewport
from .transform import TransformToolbar
from .select import SelectionManager, SelectionToolbar, SelectionPanel
from .material import MaterialPanel, MaterialToolbar
from .hierarchy import HierarchyPanel
from .props import PropertyPanel
from .history import HistoryToolbar
from .grid import GridToolbar
from .statusbar import StatusBar
from .menubar import MenuBar
from .file import FileManager
from .create import CreationManager
from .edit import EditManager
from .view import ViewManager, ViewTileManager
from .options import OptionManager
from .render_mode import RenderModeToolbar
from .obj_props import ObjectPropertiesMenu
from .uv_edit import UVEditGUI


class Window(object):

    def __init__(self):

        self._node = NodePath("window")
        self._sizer = Sizer("vertical")

    def get_ancestor(self, widget_type):

        if widget_type == "window":
            return self

    def get_node(self):

        return self._node

    def get_mouse_watcher(self):

        return Mgr.get("mouse_watcher")

    def add(self, *args, **kwargs):

        self._sizer.add(*args, **kwargs)

    def update(self, size):

        self._sizer.update(size)
        self._sizer.update_images()
        self._sizer.update_mouse_region_frames()

    def update_min_size(self):

        return self._sizer.update_min_size()

    def get_min_size(self):

        return self._sizer.get_min_size()

    def is_hidden(self, check_ancestors=False):

        return False


class Dock(WidgetCard):

    def __init__(self, parent, side):

        stretch_dir = "horizontal" if side in ("top", "bottom") else "vertical"
        WidgetCard.__init__(self, "dock", parent, stretch_dir)

        self._side = side
        self.set_sizer(Sizer("vertical"))
        self._toolbar_sizers = []

    def get_side(self):

        return self._side

    def get_toolbar_sizers(self):

        return self._toolbar_sizers

    def update_images(self):

        sizer = self.get_sizer()
        sizer.update_images()
        x, y, w, h = TextureAtlas["regions"]["dock_background"]
        img_tmp = PNMImage(w, h, 4)
        img_tmp.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
        width, height = self.get_size()
        img = PNMImage(width, height, 4)

        if min(w, h) > 1:
            painter = PNMPainter(img)
            fill = PNMBrush.make_image(img_tmp, 0, 0)
            pen = PNMBrush.make_transparent()
            painter.set_fill(fill)
            painter.set_pen(pen)
            painter.draw_rectangle(0, 0, width, height)
        else:
            img.unfiltered_stretch_from(img_tmp)

        x, y = self.get_pos()

        for widget in sizer.get_widgets(include_children=False):

            x_w, y_w = widget.get_pos(from_root=True)
            x_w -= x
            y_w -= y
            widget_img = widget.get_image()

            if widget_img:
                img.copy_sub_image(widget_img, x_w, y_w, 0, 0)

        tex = self._tex
        tex.load(img)

        l = x
        r = x + width
        b = -(y + height)
        t = -y
        quad = self.create_quad((l, r, b, t))
        quad.set_texture(tex)
        self._image = img

    def update_mouse_region_frames(self, exclude=""):

        self.get_sizer().update_mouse_region_frames(exclude)

    def get_sort(self):

        return 1


class Components(object):

    def __init__(self):

        self._is_enabled = False
        Mgr.expose("gui_enabled", lambda: self._is_enabled)
        Mgr.accept("enable_gui", self.__enable)

        GlobalData["viewport"] = {}
        GlobalData["viewport"]["display_regions2"] = []
        GlobalData["viewport"]["mouse_watchers2"] = []
        PendingTasks.add_batch("panel_redraw", 1)
        PendingTasks.add_batch("panel_change", 2)
        PendingTasks.add_batch("widget_card_update", 3)
        PendingTasks.add_batch("panel_mouse_region_update", 4)
        CullBinManager.get_global_ptr().add_bin("dialog", CullBinManager.BT_fixed, 42)
        CullBinManager.get_global_ptr().add_bin("menu", CullBinManager.BT_fixed, 43)
        CullBinManager.get_global_ptr().add_bin("tooltip", CullBinManager.BT_fixed, 44)
        self._window = win = Window()
        Mgr.expose("window", lambda: self._window)

        InputField.init()
        CheckBox.init()
        ColorBox.init()
        RadioButton.init()
        ToolTip.init()
        Dialog.init()

        self._registry = components = {}
        components["docks"] = {}
        components["docking_targets"] = []
        self._docking_data = None
        self._dragging_toolbars = False
        self._dragged_widget = None
        self._dragged_item_type = ""
        self._toolbar_insertion_marker = ToolbarInsertionMarker()
        self._listener = DirectObject()
        self._listener.accept("gui_mouse1", self.__on_left_down)
        self._listener.accept("gui_mouse1-up", self.__on_left_up)
        cancel_dragging = lambda: self.__on_left_up(cancel_drag=True)
        self._listener.accept("gui_mouse3", cancel_dragging)
        self._listener.accept("focus_loss", cancel_dragging)
        self._aux_viewport = None
        self._screenshot = None
        d = 100000.
        self._gui_region_mask = mask = MouseWatcherRegion("viewport_mask", -d, d, -d, d)
        mask.set_sort(100000)
        cm = CardMaker("black_card")
        cm.set_frame(0., 1., -1., 0.)
        cm.set_color((0., 0., 0., 1.))
        self._black_card = Mgr.get("gui_root").attach_new_node(cm.generate())
        self._black_card.set_bin("tooltip", 100)
        self._black_card.hide()

        self._uv_editing_initialized = False

        self.__create_components()
        self.__create_layout()

        self._window_size = win.update_min_size()
        Mgr.expose("window_size", lambda: self._window_size)
        win.update(self._window_size)

        components["menubar"].finalize()
        components["panel_stack"].finalize()

        self._viewport_sizer.set_default_size((400, 300))
        win.update_min_size()

        Mgr.get("base").accept("window-event", self.__handle_window_event)

        def update_object_name_tag(is_shown, name="", is_selected=False):

            if not is_shown:
                ToolTip.hide()
                return

            color = (1., 1., 0., 1.) if is_selected else (1., 1., 1., 1.)
            label = ToolTip.create_label(name, color)
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            x = mouse_pointer.get_x()
            y = mouse_pointer.get_y()
            ToolTip.show(label, (x, y + 20), delay=0.)

        Mgr.accept("set_viewport_border_color", self.__set_viewport_border_color)
        Mgr.accept("create_main_layout", self.__create_layout)
        Mgr.accept("clear_main_layout", self.__clear_layout)
        Mgr.accept("update_main_layout", self.__update_layout)
        Mgr.accept("reset_layout_data", self.__reset_layout_data)
        Mgr.accept("set_right_dock_side", self.__set_right_dock_side)
        Mgr.accept("update_window", self.__update_window)
        Mgr.add_app_updater("object_name_tag", update_object_name_tag)
        Mgr.add_app_updater("viewport", self.__update_viewport_display_regions)
        Mgr.add_app_updater("active_viewport", self.__set_active_viewport)
        Mgr.add_app_updater("screenshot", self.__update_screenshot)
        Mgr.add_app_updater("progress", self.__update_progress)

    def setup(self):

        components = self._registry
        components["panel_stack"].setup()
        self._edit_mgr.setup()
        self._creation_mgr.setup()
        self._view_mgr.setup()
        self._option_mgr.setup()
        Toolbar.registry["transform"].setup()
        components["hierarchy_panel"].setup()
        components["selection_panel"].setup()
        components["prop_panel"].setup()
        components["material_panel"].setup()
        components["uv"].setup()

        w, h = self._window_size
        Mgr.get("gui_root").set_scale(2./w, 1., 2./h)

        x, y = self._viewport_sizer.get_pos()
        w_v, h_v = self._viewport_sizer.get_size()
        GlobalData["viewport"]["pos"] = (x, y)
        GlobalData["viewport"]["size"] = (w_v, h_v)
        GlobalData["viewport"]["frame"] = get_relative_region_frame(x, y, w_v, h_v, w, h)
        GlobalData["viewport"]["border1"] = Mgr.get("base").win
        GlobalData["viewport"]["border2"] = None
        color = Skin["colors"]["viewport_frame_default"]
        GlobalData["viewport"]["border_color1"] = color
        GlobalData["viewport"]["border_color2"] = color
        GlobalData["viewport"][1] = "main"
        GlobalData["viewport"][2] = None
        GlobalData["viewport"]["active"] = 1

        def enter_selection_mode(prev_state_id, is_active):

            self.__set_viewport_border_color("viewport_frame_default")
            self.__enable()

        def enter_navigation_mode(prev_state_id, is_active):

            self.__set_viewport_border_color("viewport_frame_navigate_scene")

        nav_states = ("panning", "orbiting", "zooming", "dollying_forward",
                      "dollying_backward")

        add_state = Mgr.add_state
        add_state("selection_mode", 0, enter_selection_mode)
        add_state("navigation_mode", -100, enter_navigation_mode)
        enter_state = lambda prev_state_id, is_active: self.__enable(False)
        exit_state = lambda next_state_id, is_active: self.__enable()

        for state in nav_states:
            add_state(state, -110, enter_state, exit_state)

        add_state("region_selection_mode", -11, enter_state, exit_state)
        add_state("processing", -200, enter_state, exit_state)
        add_state("processing_no_cancel", -200, enter_state, exit_state)

        def enter_suppressed_state(prev_state_id, is_active):

            Mgr.get("viewport_cursor_region").set_active(False)
            Mgr.get("viewport2_cursor_region").set_active(False)
            Mgr.set_cursor_regions_active("aux_viewport", False)

        def exit_suppressed_state(next_state_id, is_active):

            Mgr.get("viewport_cursor_region").set_active(True)
            Mgr.get("viewport2_cursor_region").set_active(True)
            Mgr.set_cursor_regions_active("aux_viewport")

        add_state("suppressed", -1000, enter_suppressed_state, exit_suppressed_state)

        task = lambda: Mgr.update_app("viewport")
        task_id = "update_viewport"
        PendingTasks.add(task, task_id)

    def __create_components(self):

        window = self._window
        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]

        # Create the menubar

        dock = Dock(window, "top")
        docks["top"] = dock
        window.add(dock, expand=True)
        dock_sizer = dock.get_sizer()
        dock_subsizer = Sizer("horizontal")
        dock_sizer.add(dock_subsizer, expand=True)
        menubar = MenuBar(dock)
        components["menubar"] = menubar
        docking_targets.append(menubar)
        dock_subsizer.add(menubar, proportion=1.)

        def uv_edit_command():

            if not self._uv_editing_initialized:
                Mgr.update_app("uv_edit_init")
                self._uv_editing_initialized = True

            if GlobalData["active_obj_level"] != "top":
                GlobalData["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            Mgr.enter_state("uv_edit_mode")

        self._file_mgr = FileManager(menubar)
        self.exit_handler = self._file_mgr.on_exit
        self._edit_mgr = EditManager(menubar, uv_edit_command)
        self._creation_mgr = CreationManager(menubar)
        self._sel_mgr = SelectionManager(menubar)
        self._view_mgr = ViewManager(menubar)
        self._option_mgr = OptionManager(menubar)

        # Create the toolbars

        MaterialToolbar(dock)
        TransformToolbar(dock)
        SelectionToolbar(dock)
        HistoryToolbar(dock)
        RenderModeToolbar(dock)
        GridToolbar(dock)

        # Create the viewport and the right-hand side dock

        sizer = Sizer("horizontal")
        window.add(sizer, proportion=1., expand=True)
        self._viewport_sizer = viewport_sizer = Sizer("horizontal")
        viewport_sizer.set_default_size((800, 600))
        borders = (3, 3, 3, 3)
        sizer.add(viewport_sizer, proportion=1., expand=True, borders=borders)
        # create a sizer for the adjacent auxiliary viewport
        viewport_sizer_adj = Sizer("horizontal")
        sizer.add(viewport_sizer_adj, expand=True)
        self._aux_viewport = AuxiliaryViewport(window, viewport_sizer, viewport_sizer_adj)
        docks["right"] = dock = Dock(window, "right")
        sizer.add(dock, expand=True)

        # Create the control panels

        dock_sizer = dock.get_sizer()
        dock_subsizer = Sizer("horizontal")
        alignment = "left" if Skin["options"]["panel_scrollbar_left"] else "right"
        dock_sizer.add(dock_subsizer, proportion=1., alignment=alignment)
        panel_stack = PanelStack(dock)
        panel_stack_frame = panel_stack.get_frame()
        dock_subsizer.add(panel_stack_frame, expand=True)
        components["panel_stack"] = panel_stack
        components["hierarchy_panel"] = HierarchyPanel(panel_stack)
        components["selection_panel"] = SelectionPanel(panel_stack)
        components["prop_panel"] = PropertyPanel(panel_stack)
        components["material_panel"] = MaterialPanel(panel_stack)

        # Create the statusbar

        docks["bottom"] = dock = Dock(window, "bottom")
        window.add(dock, expand=True)
        dock_sizer = dock.get_sizer()
        dock_subsizer = Sizer("horizontal")
        dock_sizer.add(dock_subsizer, expand=True)
        statusbar = StatusBar(dock)
        components["statusbar"] = statusbar
        docking_targets.append(statusbar)
        dock_subsizer.add(statusbar, proportion=1.)

        ObjectPropertiesMenu()

        components["uv"] = UVEditGUI(components)

    def __set_right_dock_side(self, side="right"):

        dock = self._registry["docks"]["right"]
        sizer_item = dock.get_sizer_item()
        sizer = sizer_item.get_sizer()
        index = sizer.get_item_index(sizer_item)

        if index == 0 and side == "left" or index > 0 and side == "right":
            return

        sizer.remove_item(sizer_item)
        index = 0 if side == "left" else None
        sizer.add_item(sizer_item, index=index)
        self.__update_window()

        config_data = GlobalData["config"]
        layout = config_data["gui_layout"]
        layout["right_dock"] = side

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __get_default_layout_data(self):

        layout = {"main": {}, "uv": {}}
        layout["main"]["top"] = [None, [["history", "selection", "render_mode", "grid"]]]
        layout["main"]["bottom"] = [[["material"], ["transform"]], None]
        layout["uv"]["top"] = [None, [["selection", "render_mode", "grid"]]]
        layout["uv"]["bottom"] = [[["uv_transform"]], None]
        layout["right_dock"] = "right"

        return layout

    def __reset_layout_data(self, interface_id=None):

        layout = self.__get_default_layout_data()
        config_data = GlobalData["config"]

        if interface_id is None:
            config_data["gui_layout"] = layout
        else:
            config_data["gui_layout"][interface_id] = layout[interface_id]
            config_data["gui_layout"]["right_dock"] = "right"

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        return layout

    def __create_layout(self):

        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]
        toolbars = Toolbar.registry
        config_data = GlobalData["config"]
        layout = config_data.get("gui_layout")

        if not layout:

            layout = self.__get_default_layout_data()
            config_data["gui_layout"] = layout

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

        side = layout["right_dock"]

        if side == "left":
            dock = docks["right"]
            sizer_item = dock.get_sizer_item()
            sizer = sizer_item.get_sizer()
            sizer.remove_item(sizer_item)
            sizer.add_item(sizer_item, index=0)

        for side, toolbar_id_lists in layout["main"].items():

            dock = docks[side]
            dock_sizer = dock.get_sizer()
            toolbar_sizers = dock.get_toolbar_sizers()

            for i, toolbar_id_list in enumerate(toolbar_id_lists):

                if toolbar_id_list is None:
                    continue

                row_sizer = Sizer("horizontal")
                dock_sizer.add(row_sizer, expand=True, index=i)
                toolbar_sizers.append(row_sizer)

                if len(toolbar_id_list) > 1:

                    bundled_rows = []

                    for toolbar_ids in toolbar_id_list:

                        toolbar_row = ToolbarRow(dock)
                        docking_targets.append(toolbar_row.get_handle())
                        bundled_rows.append(toolbar_row)

                        for toolbar_id in toolbar_ids:
                            toolbar = toolbars[toolbar_id]
                            toolbar.set_parent(dock)
                            toolbar.set_row(toolbar_row)
                            toolbar_row.add_toolbar(toolbar)
                            docking_targets.append(toolbar)

                    bottom_row = bundled_rows[0]

                    for toolbar in bottom_row:
                        row_sizer.add(toolbar)

                    row_sizer.add(bottom_row.get_handle(), proportion=1.)
                    w_min = row_sizer.update_min_size()[0]
                    bottom_row.set_min_width_in_bundle(w_min)
                    bundle = bottom_row.get_bundle()

                    for row in bundled_rows[1:]:

                        for toolbar in row:
                            row_sizer.remove_item(row_sizer.add(toolbar))

                        handle = row.get_handle()
                        row_sizer.remove_item(row_sizer.add(handle, proportion=1.))
                        bundle.add_toolbar_row(row)
                        w_min = row_sizer.update_min_size()[0]
                        row.set_min_width_in_bundle(w_min)

                    width = bundle.get_min_width()

                else:

                    toolbar_row = ToolbarRow(dock)
                    docking_targets.append(toolbar_row.get_handle())

                    for toolbar_id in toolbar_id_list[0]:
                        toolbar = toolbars[toolbar_id]
                        row_sizer.add(toolbar)
                        toolbar.set_parent(dock)
                        toolbar.set_row(toolbar_row)
                        toolbar_row.add_toolbar(toolbar)
                        docking_targets.append(toolbar)

                    row_sizer.add(toolbar_row.get_handle(), proportion=1.)
                    width = row_sizer.update_min_size()[0]
                    toolbar_row.set_min_width_in_bundle(width)

                row_sizer.set_default_size((width, 0))

    def __clear_layout(self):

        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]
        toolbars = Toolbar.registry

        toolbar_rows = set()
        bundles = set()

        for toolbar_id in ("material", "transform", "history", "render_mode", "grid", "selection"):

            toolbar = toolbars[toolbar_id]
            docking_targets.remove(toolbar)
            toolbar_row = toolbar.get_row()
            toolbar_rows.add(toolbar_row)

            if toolbar_row.in_bundle():
                bundles.add(toolbar_row.get_bundle())

            toolbar.set_sizer_item(None)
            toolbar.hide()

        for bundle in bundles:
            bundle.destroy()

        for toolbar_row in toolbar_rows:
            docking_targets.remove(toolbar_row.get_handle())
            toolbar_row.destroy()

        for side in ("top", "bottom"):

            dock = docks[side]
            dock_sizer = dock.get_sizer()
            toolbar_sizers = dock.get_toolbar_sizers()

            while toolbar_sizers:
                row_sizer = toolbar_sizers.pop()
                dock_sizer.remove_item(row_sizer.get_sizer_item())
                row_sizer.clear()
                row_sizer.destroy()

    def __update_layout(self):

        self.__clear_layout()
        self.__create_layout()
        self.__update_window()

    def __update_layout_data(self):

        config_data = GlobalData["config"]
        config_data["gui_layout"][GlobalData["active_interface"]] = layout = {}
        toolbars = Toolbar.registry
        docks = self._registry["docks"]

        for side in ("top", "bottom"):

            layout[side] = toolbar_id_lists = []
            dock = docks[side]
            dock_sizer = dock.get_sizer()
            toolbar_sizers = dock.get_toolbar_sizers()

            for item in dock_sizer.get_items():

                sizer = item.get_object()

                if sizer in toolbar_sizers:

                    toolbar_id_list = []
                    toolbar_id_lists.append(toolbar_id_list)
                    toolbar_row = sizer.get_item(0).get_object().get_row()

                    if toolbar_row.in_bundle():
                        for row in toolbar_row.get_bundle():
                            toolbar_ids = [t.get_id() for t in row]
                            toolbar_id_list.append(toolbar_ids)
                    else:
                        toolbar_ids = [t.get_id() for t in toolbar_row]
                        toolbar_id_list.append(toolbar_ids)

                else:

                    toolbar_id_lists.append(None)

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __update_progress(self, update_type, arg1=None, arg2=None):

        if update_type == "start":
            self._progress_dialog = ProgressDialog(message=arg1, cancellable=arg2)
        elif update_type == "set_rate":
            self._progress_dialog.set_rate(arg1)
        elif update_type == "advance":
            self._progress_dialog.advance()
        elif update_type == "end":
            self._progress_dialog.close(answer="yes")

    def __update_screenshot(self, update_type):

        if update_type == "create":

            # A screenshot is generated and rendered to replace the rendering of the scene.
            # This can be used to hide temporary changes in object geometry during long processes.

            if self._screenshot:
                return

            ToolTip.hide()
            Dialog.hide_dialogs()
            fps_meter_display_region = GlobalData["fps_meter_display_region"]
            fps_meter_display_region.set_active(False)
            base = Mgr.get("base")
            base.graphicsEngine.render_frame()
            tex = base.win.get_screenshot()
            Dialog.show_dialogs()
            cm = CardMaker("screenshot")
            w, h = self._window_size
            cm.set_frame(0, w, -h, 0)
            self._screenshot = Mgr.get("gui_root").attach_new_node(cm.generate())
            self._screenshot.set_texture(tex)
            self._screenshot.set_bin("gui", 0)
            Mgr.update_remotely("screenshot_removal")

        elif update_type == "remove":

            if not self._screenshot:
                return

            self._screenshot.remove_node()
            self._screenshot = None
            fps_meter_display_region = GlobalData["fps_meter_display_region"]
            fps_meter_display_region.set_active(True)

    def dragging_toolbars(self):

        return self._dragging_toolbars

    def __update_insertion_marker(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        point = (mouse_x, mouse_y)

        for target in self._registry["docking_targets"]:

            docking_data = target.get_docking_data(point)

            if docking_data:

                target_component, side, pos = docking_data

                if target_component.is_hidden():
                    continue

                if target_component.get_widget_type() == "toolbar_row_handle":
                    if side == "center":
                        if target_component is self._dragged_widget:
                            continue
                        self._toolbar_insertion_marker.set_type("+")
                    else:
                        self._toolbar_insertion_marker.set_type("h")
                elif side in ("left", "right"):
                    if (target_component is self._dragged_widget
                            or self._dragged_item_type == "toolbar_bundle"
                            or (self._dragged_item_type == "toolbar_row"
                            and target_component in self._dragged_widget.get_row())):
                        continue
                    self._toolbar_insertion_marker.set_type("v")
                else:
                    self._toolbar_insertion_marker.set_type("h")

                self._toolbar_insertion_marker.show()
                self._toolbar_insertion_marker.set_pos(pos)
                self._docking_data = docking_data
                break

        else:

            self._docking_data = None
            self._toolbar_insertion_marker.hide()

        return task.cont

    def __on_left_down(self):

        region = Mgr.get("mouse_watcher").get_over_region()

        if not region:
            return

        name = region.get_name()

        def init_toolbar_dragging(name_start):

            widget_id = int(name.replace(name_start, ""))
            widget = Widget.registry[widget_id]
            is_toolbar = name_start == "toolbar_grip_"

            if is_toolbar:
                item_type = "toolbar"
            elif name_start == "tb_row_grip_":
                item_type = "toolbar_row"
            else:
                item_type = "toolbar_bundle"
                widget = widget.get_parent()

            if is_toolbar and set([widget]) == set(widget.get_row()):
                # if the dragged toolbar is the only one in its row, this is equivalent
                # to dragging the row itself
                widget = widget.get_row().get_handle()
                item_type = "toolbar_row"
                is_toolbar = False

            self._dragged_widget = widget
            self._dragged_item_type = item_type

            if not is_toolbar:
                widget = widget.get_row()

            widget.create_ghost_image()
            ToolTip.hide()
            self._dragging_toolbars = True
            Mgr.add_task(self.__update_insertion_marker, "update_insertion_marker")
            self.__enable(False)
            Mgr.enter_state("inactive")
            interface_ids = GlobalData["viewport"]

            if interface_ids[2] is not None:
                interface_id = interface_ids[2 if interface_ids[1] == "main" else 1]
                Mgr.enter_state("inactive", interface_id)

        if name.startswith("toolbar_grip_"):
            init_toolbar_dragging("toolbar_grip_")
        elif name.startswith("tb_row_grip_"):
            init_toolbar_dragging("tb_row_grip_")
        elif name.startswith("tb_bundle_grip_"):
            init_toolbar_dragging("tb_bundle_grip_")

    def __move_toolbar(self, toolbar):

        docking_targets = self._registry["docking_targets"]
        target_component, side, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        sizer_item = toolbar.get_sizer_item()
        row_sizer = sizer_item.get_sizer()
        toolbar_row = toolbar.get_row()
        toolbar_row.remove_toolbar(toolbar)
        target_sizer_item = target_component.get_sizer_item()
        target_subsizer = target_sizer_item.get_sizer()
        target_sizer = target_subsizer.get_owner()
        toolbar.set_parent(target_sizer.get_owner())
        row_sizer.remove_item(sizer_item)
        row_sizer.set_default_size((0, 0))
        width = row_sizer.update_min_size()[0]
        toolbar_row.set_min_width_in_bundle(width)

        if toolbar_row.in_bundle():
            width = toolbar_row.get_bundle().get_min_width()
        else:
            width = toolbar_row.get_min_width(in_bundle=False)

        row_sizer.set_default_size((width, 0))

        if target_component.get_widget_type() == "toolbar_row_handle":

            dest_row = ToolbarRow(target_dock)
            toolbar.set_row(dest_row)
            dest_row.add_toolbar(toolbar)
            handle = dest_row.get_handle()
            target_subsizer.remove_item(target_subsizer.add(handle, proportion=1.))
            target_row = target_component.get_row()
            bundle = target_row.get_bundle()
            bundle.add_toolbar_row(dest_row)
            target_subsizer.set_default_size((0, 0))
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            width = bundle.get_min_width()
            target_subsizer.set_default_size((width, 0))
            docking_targets.append(handle)

        elif side in ("bottom", "top"):

            index = target_sizer.get_item_index(target_subsizer.get_sizer_item())

            if side == "bottom":
                index += 1

            new_row_sizer = Sizer("horizontal")
            new_row_sizer.add_item(sizer_item)
            dest_row = ToolbarRow(target_dock)
            toolbar.set_row(dest_row)
            dest_row.add_toolbar(toolbar)
            handle = dest_row.get_handle()
            new_row_sizer.add(handle, proportion=1.)
            w_min = new_row_sizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            w_min = dest_row.get_min_width(in_bundle=False)
            new_row_sizer.set_default_size((w_min, 0))
            target_sizer.add(new_row_sizer, expand=True, index=index)
            target_dock.get_toolbar_sizers().append(new_row_sizer)
            docking_targets.append(handle)

        else:

            index = target_subsizer.get_item_index(target_sizer_item)

            if side == "right":
                index += 1

            target_subsizer.add_item(sizer_item, index=index)
            dest_row = target_component.get_row()
            toolbar.set_row(dest_row)
            dest_row.add_toolbar(toolbar, index)
            w_d = target_subsizer.get_default_size()[0]
            target_subsizer.set_default_size((0, 0))
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            w_min = dest_row.get_min_width(in_bundle=dest_row.in_bundle())
            width = max(w_d, w_min)
            target_subsizer.set_default_size((width, 0))

    def __move_toolbar_row(self, toolbar_row_handle):

        docking_targets = self._registry["docking_targets"]
        target_component, side, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        src_dock = toolbar_row_handle.get_ancestor("dock")
        sizer_item = toolbar_row_handle.get_sizer_item()
        row_sizer = sizer_item.get_sizer()
        row_sizer_item = row_sizer.get_sizer_item()
        toolbar_row = toolbar_row_handle.get_row()
        target_sizer_item = target_component.get_sizer_item()
        target_subsizer = target_sizer_item.get_sizer()
        target_sizer = target_subsizer.get_owner()
        parent = target_sizer.get_owner()
        toolbar_row_handle.set_parent(parent)
        in_bundle = toolbar_row.in_bundle()

        if in_bundle:

            bundle = toolbar_row.get_bundle()
            rows = list(bundle)
            rows.remove(toolbar_row)
            next_row = bundle.remove_toolbar_row()

            if next_row.in_bundle():
                width = bundle.get_min_width()
            else:
                width = next_row.get_min_width(in_bundle=False)

            row_sizer.set_default_size((width, 0))

        if target_component.get_widget_type() == "toolbar_row_handle":

            target_row = target_component.get_row()
            bundle = target_row.get_bundle()
            bundle.add_toolbar_row(toolbar_row)
            target_subsizer.set_default_size((0, 0))
            w_min = target_subsizer.update_min_size()[0]
            toolbar_row.set_min_width_in_bundle(w_min)
            width = bundle.get_min_width()
            target_subsizer.set_default_size((width, 0))

            if not in_bundle:
                row_sizer_item.get_sizer().remove_item(row_sizer_item)
                row_sizer.clear()
                row_sizer.destroy()
                src_dock.get_toolbar_sizers().remove(row_sizer)

        elif side in ("bottom", "top"):

            if not in_bundle:

                if target_subsizer is row_sizer:
                    return

                row_sizer_item.get_sizer().remove_item(row_sizer_item)
                src_dock.get_toolbar_sizers().remove(row_sizer)

            index = target_sizer.get_item_index(target_subsizer.get_sizer_item())

            if side == "bottom":
                index += 1

            if in_bundle:

                row_sizer = Sizer("horizontal")

                for toolbar in toolbar_row:
                    row_sizer.add_item(toolbar.get_sizer_item())

                row_sizer.add_item(sizer_item)
                target_sizer.add(row_sizer, expand=True, index=index)

            else:

                target_sizer.add_item(row_sizer_item, index=index)

            target_dock.get_toolbar_sizers().append(row_sizer)
            row_sizer.set_default_size((toolbar_row.get_min_width(in_bundle=False), 0))

            for toolbar in toolbar_row:
                toolbar.set_parent(parent)

        else:

            index = target_subsizer.get_item_index(target_sizer_item)

            if side == "right":
                index += 1

            dest_row = target_component.get_row()
            dest_row.add_toolbars(toolbar_row, index)

            for toolbar in toolbar_row[::-1]:
                toolbar.set_parent(parent)
                toolbar.set_row(dest_row)
                target_subsizer.add_item(toolbar.get_sizer_item(), index=index)

            w_d = target_subsizer.get_default_size()[0]
            target_subsizer.set_default_size((0, 0))
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            width = max(w_d, w_min)
            target_subsizer.set_default_size((width, 0))
            toolbar_row.destroy_ghost_image()
            toolbar_row.destroy()
            docking_targets.remove(toolbar_row_handle)

            if not in_bundle:
                row_sizer_item.get_sizer().remove_item(row_sizer_item)
                row_sizer.clear()
                row_sizer.destroy()
                src_dock.get_toolbar_sizers().remove(row_sizer)

    def __move_toolbar_bundle(self, toolbar_row_handle):

        docking_targets = self._registry["docking_targets"]
        target_component, side, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        src_dock = toolbar_row_handle.get_ancestor("dock")
        sizer_item = toolbar_row_handle.get_sizer_item()
        row_sizer = sizer_item.get_sizer()
        row_sizer_item = row_sizer.get_sizer_item()
        toolbar_row = toolbar_row_handle.get_row()
        target_sizer_item = target_component.get_sizer_item()
        target_subsizer = target_sizer_item.get_sizer()
        target_sizer = target_subsizer.get_owner()

        if target_component.get_widget_type() == "toolbar_row_handle":

            row_sizer_item.get_sizer().remove_item(row_sizer_item)
            src_dock.get_toolbar_sizers().remove(row_sizer)
            target_row = target_component.get_row()
            bundle = target_row.get_bundle()
            bundle.add_toolbar_row(toolbar_row)
            width = max(bundle.get_min_width(), target_subsizer.get_default_size()[0])
            target_subsizer.set_default_size((width, 0))
            row_sizer.clear()
            row_sizer.destroy()

        else:

            if target_subsizer is row_sizer:
                return

            row_sizer_item.get_sizer().remove_item(row_sizer_item)
            src_dock.get_toolbar_sizers().remove(row_sizer)
            index = target_sizer.get_item_index(target_subsizer.get_sizer_item())

            if side == "bottom":
                index += 1

            target_sizer.add_item(row_sizer_item, index=index)
            parent = target_sizer.get_owner()
            toolbar_row.set_parent(parent)
            target_dock.get_toolbar_sizers().append(row_sizer)

    def __on_left_up(self, cancel_drag=False):

        if not self._dragging_toolbars:
            return

        Mgr.remove_task("update_insertion_marker")
        self._toolbar_insertion_marker.set_type("")
        dragged_widget = self._dragged_widget

        if self._docking_data and not cancel_drag:

            item_type = self._dragged_item_type

            if item_type == "toolbar":
                self.__move_toolbar(dragged_widget)
            elif item_type == "toolbar_row":
                self.__move_toolbar_row(dragged_widget)
            elif item_type == "toolbar_bundle":
                self.__move_toolbar_bundle(dragged_widget)

            self._window.update_min_size()
            self.__update_window()
            self.__update_layout_data()

        self._docking_data = None
        self._dragged_item_type = ""
        dragged_widget.destroy_ghost_image()
        self._dragged_widget = None
        self._dragging_toolbars = False
        self.__enable()
        Mgr.exit_state("inactive")
        interface_ids = GlobalData["viewport"]

        if interface_ids[2] is not None:
            interface_id = interface_ids[2 if interface_ids[1] == "main" else 1]
            Mgr.exit_state("inactive", interface_id)

        Mgr.set_cursor("main")

    def __set_viewport_border_color(self, color_id):

        color = Skin["colors"][color_id]
        index = 2 if GlobalData["viewport"][2] == "main" else 1
        GlobalData["viewport"]["border_color{:d}".format(index)] = color

        if GlobalData["viewport"]["active"] == index:
            GlobalData["viewport"]["border{:d}".format(index)].set_clear_color(color)

    def __set_active_viewport(self, index):

        GlobalData["viewport"]["active"] = index
        color = GlobalData["viewport"]["border_color{:d}".format(index)]
        GlobalData["viewport"]["border{:d}".format(index)].set_clear_color(color)
        color = Skin["colors"]["viewport_frame_inactive"]
        GlobalData["viewport"]["border{:d}".format(3 - index)].set_clear_color(color)
        interface_id = GlobalData["viewport"][index]
        Mgr.do("set_interface_status", interface_id)
        Mgr.get("base").messenger.send("focus_loss")

    def __update_viewport_display_regions(self):

        viewport2_id = GlobalData["viewport"][2]

        l, r, b, t = GlobalData["viewport"]["frame_aux" if viewport2_id == "main" else "frame"]
        Mgr.get("viewport_cursor_region").set_frame(2. * l - 1., 2. * r - 1., 2. * b - 1., 2. * t - 1.)

        for dr in GlobalData["viewport"]["display_regions"]:
            dr.set_dimensions(l, r, b, t)

        if viewport2_id is not None:

            l, r, b, t = GlobalData["viewport"]["frame" if viewport2_id == "main" else "frame_aux"]
            Mgr.get("viewport2_cursor_region").set_frame(2. * l - 1., 2. * r - 1., 2. * b - 1., 2. * t - 1.)

            for dr in GlobalData["viewport"]["display_regions2"]:
                dr.set_dimensions(l, r, b, t)

        w, h = self._window_size
        l, r, b, t = GlobalData["viewport"]["frame" if viewport2_id is None else "frame_aux"]
        GlobalData["fps_meter_display_region"].set_dimensions(r - 800./w, r, b, b + 600./h)

    def __update_window(self, task=None):

        w, h = w_, h_ = self._window_size
        w_min, h_min = self._window.update_min_size()
        Mgr.get("mouse_watcher").set_frame(0., w, -h, 0.)

        if w < w_min:
            w = w_min

        if h < h_min:
            h = h_min

        self._window.update((w, h))
        x, y = self._viewport_sizer.get_pos()
        w_v, h_v = self._viewport_sizer.get_size()
        GlobalData["viewport"]["pos"] = (x, y)
        GlobalData["viewport"]["size"] = (w_v, h_v)
        GlobalData["viewport"]["frame"] = get_relative_region_frame(x, y, w_v, h_v, w_, h_)

        if GlobalData["viewport"][2] is not None:
            self._aux_viewport.update()

        Mgr.update_app("viewport")
        InputField.update_active_text_pos()
        Dialog.center_dialogs()

        if PLATFORM_ID != "Windows":
            self._black_card.hide()

        if self._screenshot:
            self.__update_screenshot("remove")
            self.__update_screenshot("create")

    def __handle_window_event(self, window):

        win_props = window.get_properties()
        w, h = max(1, win_props.get_x_size()), max(1, win_props.get_y_size())

        if self._window_size != (w, h):

            self._window_size = (w, h)
            win_props = WindowProperties()
            win_props.set_size(w, h)
            window.request_properties(win_props)
            Mgr.get("gui_root").set_scale(2./w, 1., 2./h)

            if PLATFORM_ID == "Windows":
                self.__update_window()
            else:
                self._black_card.set_scale(w, 1., h)
                self._black_card.show()
                Mgr.remove_task("update_window")
                Mgr.add_task(.2, self.__update_window, "update_window")

        if not win_props.get_foreground():
            Mgr.get("base").messenger.send("focus_loss")

    def handle_hotkey(self, hotkey, hotkey_repeat):

        HotkeyManager.handle_widget_hotkey(hotkey, hotkey_repeat)

    def __enable(self, enable=True):

        if self._is_enabled == enable:
            return

        mask = self._gui_region_mask
        components = self._registry

        for mouse_watcher in GlobalData["mouse_watchers"]:
            mouse_watcher.remove_region(mask) if enable else mouse_watcher.add_region(mask)

        components["uv"].enable(enable)
        self._is_enabled = enable

    def is_enabled(self):

        return self._is_enabled

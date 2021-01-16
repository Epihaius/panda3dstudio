from ..base import *
from ..toolbar import *
from ..tooltip import ToolTip
from ..text import Text
from ..button import Button
from ..combobox import ComboBox
from ..field import InputField
from ..colorbox import ColorBox
from ..dialog import Dialog
from ..dialogs import *
from ..checkbtn import CheckButton
from ..radiobtn import RadioButton
from ..panel import ControlPane
from ..menu import Menu
from .aux_viewport import AuxiliaryViewport
from .transform_toolbar import TransformToolbar
from .align import SnapAlignToolbar
from .select import SelectionManager, SelectionToolbar, SelectionPanel
from .material import MaterialPanel, MaterialToolbar
from .hierarchy import HierarchyPanel
from .props import PropertyPanel
from .history_toolbar import HistoryToolbar
from .grid import GridToolbar
from .statusbar import StatusBar
from .menubar import MenuBar
from .file import FileManager
from .create import CreationManager
from .edit import EditManager
from .view import ViewManager
from .options import OptionManager
from .render_mode import RenderModeToolbar
from .obj_props import ObjectPropertiesMenu
from .uv_edit import UVEditGUI


class Window:

    def __init__(self):

        self.sizer = Sizer("vertical")
        self.sizer.set_column_proportion(0, 1.)
        self.sizer.set_row_proportion(1, 1.)
        self.node = NodePath("window")
        self.mouse_watcher = Mgr.get("mouse_watcher")

    def get_ancestor(self, widget_type):

        if widget_type == "window":
            return self

    def update(self, size):

        self.sizer.update(size)
        self.sizer.update_images()
        self.sizer.update_mouse_region_frames()

    def update_min_size(self):

        return self.sizer.update_min_size()

    @property
    def min_size(self):

        return self.sizer.min_size

    def is_hidden(self, check_ancestors=False):

        return False


class Dock(WidgetCard):

    def __init__(self, parent, alignment):

        WidgetCard.__init__(self, "dock", parent)

        self._alignment = alignment
        self.sizer = Sizer("vertical")
        self.sizer.set_column_proportion(0, 1.)
        self.sizer.set_row_proportion(0, 1.)
        self._toolbar_sizers = []

    @property
    def sort(self):

        return 1

    @property
    def alignment(self):

        return self._alignment

    @property
    def toolbar_sizers(self):

        return self._toolbar_sizers

    def update_images(self):

        sizer = self.sizer

        if not sizer.get_widgets(include_children=False):
            self.quad.detach_node()
            return

        sizer.update_images()
        gfx_id = Skin.atlas.gfx_ids["dock"][""][0][0]
        x, y, w, h = Skin.atlas.regions[gfx_id]
        img_tmp = PNMImage(w, h, 4)
        img_tmp.copy_sub_image(Skin.atlas.image, 0, 0, x, y, w, h)
        width, height = self.get_size()
        img = PNMImage(width, height, 4)

        if min(w, h) > 1:
            painter = PNMPainter(img)
            fill = PNMBrush.make_image(img_tmp, 0, 0)
            pen = PNMBrush.make_transparent()
            painter.fill = fill
            painter.pen = pen
            painter.draw_rectangle(0, 0, width, height)
        else:
            img.unfiltered_stretch_from(img_tmp)

        x, y = self.get_pos()

        for widget in sizer.get_widgets(include_children=False):

            x_w, y_w = widget.get_pos(net=True)
            x_w -= x
            y_w -= y
            widget_img = widget.get_image()

            if widget_img:
                img.copy_sub_image(widget_img, x_w, y_w, 0, 0)

        tex = self.texture
        tex.load(img)

        l = x
        r = x + width
        b = -(y + height)
        t = -y
        quad = self.create_quad((l, r, b, t))
        quad.set_texture(tex)
        self._image = img

    def update_mouse_region_frames(self, exclude=""):

        self.sizer.update_mouse_region_frames(exclude)


class Components:

    def __init__(self):

        self._is_enabled = False
        Mgr.expose("gui_enabled", lambda: self._is_enabled)
        Mgr.accept("enable_gui", self.__enable)

        GD["viewport"] = {}
        GD["viewport"]["display_regions2"] = []
        GD["viewport"]["mouse_watchers2"] = []
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
        CheckButton.init()
        ColorBox.init(ColorDialog)
        RadioButton.init()
        ToolTip.init()
        Dialog.init()

        self._registry = components = {}
        Mgr.expose("main_gui_components", lambda: self._registry)
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
        mask.sort = 200
        cm = CardMaker("black_card")
        cm.set_frame(0., 1., -1., 0.)
        cm.set_color((0., 0., 0., 1.))
        self._black_card = Mgr.get("gui_root").attach_new_node(cm.generate())
        self._black_card.set_bin("tooltip", 100)
        self._black_card.hide()

        self._uv_editing_initialized = False

        self.__create_components()
        self.__init_main_layout()

        self._window_size = win.update_min_size()
        Mgr.expose("window_size", lambda: self._window_size)
        win.update(self._window_size)

        components["menubar"].finalize()
        components["control_pane"].finalize()

        self._viewport_sizer.default_size = (400, 300)

        GD.showbase.accept("window-event", self.__handle_window_event)

        def update_object_name_tag(is_shown, name="", is_selected=False):

            if not is_shown:
                ToolTip.hide()
                return

            color = Skin.colors[("" if is_selected else "un") + "selected_object_name_tag"]
            label = ToolTip.create_label(name, color)
            mouse_pointer = Mgr.get("mouse_pointer", 0)
            ToolTip.show(label, (mouse_pointer.x, mouse_pointer.y + 20), delay=0.)

        Mgr.accept("set_viewport_border_color", self.__set_viewport_border_color)
        Mgr.accept("create_toolbar_layout", self.__create_toolbar_layout)
        Mgr.accept("clear_toolbar_layout", self.__clear_toolbar_layout)
        Mgr.accept("create_main_toolbar_layout", self.__create_main_toolbar_layout)
        Mgr.accept("clear_main_toolbar_layout", self.__clear_main_toolbar_layout)
        Mgr.accept("update_main_toolbar_layout", self.__update_toolbar_layout)
        Mgr.accept("reset_layout_data", self.__reset_layout_data)
        Mgr.accept("align_control_pane", self.__align_control_pane)
        Mgr.accept("show_components", self.__show_components)
        Mgr.accept("update_window", self.__update_window)
        Mgr.add_app_updater("object_name_tag", update_object_name_tag)
        Mgr.add_app_updater("viewport", self.__update_viewport_display_regions)
        Mgr.add_app_updater("active_viewport", self.__set_active_viewport)
        Mgr.add_app_updater("screenshot", self.__update_screenshot)
        Mgr.add_app_updater("progress", self.__update_progress)
        Mgr.add_app_updater("main_context", self.__show_main_context_menu)

    def setup(self):

        components = self._registry
        components["control_pane"].setup()
        self._edit_mgr.setup()
        self._creation_mgr.setup()
        self._view_mgr.setup()
        self._option_mgr.setup()
        Toolbar.registry["transform"].setup()
        Toolbar.registry["snap_align"].setup()

        for panel in components["panels"].values():
            panel.setup()

        components["uv"].setup()

        w, h = self._window_size
        Mgr.get("gui_root").set_scale(2./w, 1., 2./h)

        x, y = self._viewport_sizer.get_pos()
        w_v, h_v = self._viewport_sizer.get_size()
        GD["viewport"]["pos"] = (x, y)
        GD["viewport"]["size"] = (w_v, h_v)
        GD["viewport"]["frame"] = get_relative_region_frame(x, y, w_v, h_v, w, h)
        GD["viewport"]["border1"] = GD.window
        GD["viewport"]["border2"] = None
        color = Skin.colors["viewport_frame_default"]
        GD["viewport"]["border_color1"] = color
        GD["viewport"]["border_color2"] = color
        GD["viewport"][1] = "main"
        GD["viewport"][2] = None
        GD["viewport"]["active"] = 1

        self.__hide_components_at_startup()

        def enter_selection_mode(prev_state_id, active):

            self.__set_viewport_border_color("viewport_frame_default")
            self.__enable()

        def enter_navigation_mode(prev_state_id, active):

            self.__set_viewport_border_color("viewport_frame_navigate_scene")

        nav_states = ("panning", "orbiting", "zooming", "dollying_forward",
                      "dollying_backward")

        add_state = Mgr.add_state
        add_state("selection_mode", 0, enter_selection_mode)
        add_state("navigation_mode", -100, enter_navigation_mode)
        enter_state = lambda prev_state_id, active: self.__enable(False)

        def exit_state(next_state_id, active):

            if not GD["interactive_creation"]:
                self.__enable()

        for state in nav_states:
            add_state(state, -110, enter_state, exit_state)

        add_state("region_selection_mode", -11, enter_state, exit_state)
        add_state("processing", -200, enter_state, exit_state)
        add_state("processing_no_cancel", -200, enter_state, exit_state)

        def enter_suppressed_state(prev_state_id, active):

            Mgr.get("viewport_cursor_region").active = False
            Mgr.get("viewport2_cursor_region").active = False
            Mgr.set_cursor_regions_active("aux_viewport", False)

        def exit_suppressed_state(next_state_id, active):

            Mgr.get("viewport_cursor_region").active = True
            Mgr.get("viewport2_cursor_region").active = True
            Mgr.set_cursor_regions_active("aux_viewport")

        add_state("suppressed", -1000, enter_suppressed_state, exit_suppressed_state)

        task = lambda: Mgr.update_app("viewport")
        task_id = "update_viewport"
        PendingTasks.add(task, task_id)

    def __create_components(self):

        window = self._window
        window_sizer = window.sizer
        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]

        # Create the menubar

        dock = Dock(window, "top")
        docks["top"] = dock
        window_sizer.add(dock)
        dock_sizer = dock.sizer
        dock_subsizer = Sizer("horizontal")
        dock_sizer.add(dock_subsizer)
        menubar = MenuBar(dock)
        components["menubar"] = menubar
        docking_targets.append(menubar)
        dock_subsizer.add(menubar, proportions=(1., 0.))

        def uv_edit_command():

            if not self._uv_editing_initialized:
                Mgr.update_app("uv_edit_init")
                self._uv_editing_initialized = True

            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            task = lambda: Mgr.enter_state("uv_edit_mode")
            task_id = "enter_uv_edit_mode"
            PendingTasks.add(task, task_id, sort=1)

        self._file_mgr = FileManager(menubar)
        self.exit_handler = self._file_mgr.on_exit
        self._edit_mgr = EditManager(menubar, uv_edit_command)
        self._creation_mgr = CreationManager(menubar)
        self._sel_mgr = SelectionManager(menubar)
        self._view_mgr = ViewManager(menubar)
        self._option_mgr = OptionManager(menubar)

        # Create the main context menu

        self._extra_submenu_ids = []
        self._extra_menu_items = {}

        def on_hide():
            
            context_submenu = components["main_context_submenu"]
            btns = menubar.get_buttons()

            for menu_id, item in context_submenu.items.items():
                item.set_submenu(None)
                btn = btns[menu_id]
                menu = btn.get_menu()
                btn.set_menu(menu)

            context_menu = components["main_context_menu"]

            for menu_id in self._extra_submenu_ids:
                Mgr.do(f"restore_menu_{menu_id}")
                item = context_menu.items[menu_id]
                item.set_submenu(None)
                context_menu.remove(menu_id)

            if self._extra_submenu_ids:
                context_menu.update()

            self._extra_submenu_ids = []

        components["main_context_menu"] = menu = Menu(on_hide=on_hide)
        item = menu.add("main", "Main", item_type="submenu")
        components["main_context_submenu"] = submenu = item.get_submenu()
        components["main_context_submenu_items"] = context_submenu_items = {}
        item = menu.add("tools", "Tools", item_type="submenu")
        components["main_context_tools_menu"] = tools_menu = item.get_submenu()

        for menu_id, btn in menubar.get_buttons().items():
            item = submenu.add(menu_id, btn.get_text(), item_type="submenu")
            item.enable()
            context_submenu_items[menu_id] = item

        menu.update()

        # Create the toolbars

        MaterialToolbar(dock)
        TransformToolbar(dock)
        SelectionToolbar(dock)
        HistoryToolbar(dock)
        RenderModeToolbar(dock)
        GridToolbar(dock)
        SnapAlignToolbar(dock)

        tools_menu.update()

        # Create the viewport and the right-hand side dock

        sizer = Sizer("horizontal")
        window_sizer.add(sizer, proportions=(1., 1.))
        self._viewport_sizer = viewport_sizer = Sizer("horizontal")
        viewport_sizer.default_size = (800, 600)
        border = Skin.options["viewport_border_thickness"]
        borders = (border,) * 4
        sizer.add(viewport_sizer, (1., 1.), borders=borders)
        # create a sizer for the adjacent auxiliary viewport
        viewport_sizer_adj = Sizer("horizontal")
        sizer.add(viewport_sizer_adj)
        self._aux_viewport = AuxiliaryViewport(window, viewport_sizer, viewport_sizer_adj)
        docks["right"] = dock = Dock(window, "right")
        sizer.add(dock)

        # Create the control panels

        dock_sizer = dock.sizer
        dock_subsizer = Sizer("horizontal")
        dock_sizer.add(dock_subsizer, (0., 1.))
        control_pane = ControlPane(dock)
        control_pane_frame = control_pane.frame
        dock_subsizer.add(control_pane_frame, (0., 1.))
        components["control_pane"] = control_pane
        components["panels"] = panels = {}
        panel_classes = {}
        panel_classes["hierarchy"] = HierarchyPanel
        panel_classes["selection"] = SelectionPanel
        panel_classes["obj_props"] = PropertyPanel
        panel_classes["materials"] = MaterialPanel

        for panel_id in Skin.layout.control_panels["main"]:
            panels[panel_id] = panel_classes[panel_id](control_pane)

        # Create the statusbar

        docks["bottom"] = dock = Dock(window, "bottom")
        window_sizer.add(dock)
        dock_sizer = dock.sizer
        dock_subsizer = Sizer("horizontal")
        dock_sizer.add(dock_subsizer)
        statusbar = StatusBar(dock)
        components["statusbar"] = statusbar
        docking_targets.append(statusbar)
        dock_subsizer.add(statusbar, proportions=(1., 0.))

        ObjectPropertiesMenu()

        components["uv"] = UVEditGUI(components)

    def __align_control_pane(self, alignment="right"):

        dock = self._registry["docks"]["right"]
        sizer_cell = dock.sizer_cell
        sizer = sizer_cell.sizer
        index = sizer.cells.index(sizer_cell)

        if index == 0 and alignment == "left" or index > 0 and alignment == "right":
            return

        sizer.remove_cell(sizer_cell)
        index = 0 if alignment == "left" else None
        sizer.add_cell(sizer_cell, index=index)
        self.__update_window()

        config_data = GD["config"]
        config_data["gui_layout"]["control_pane_alignment"] = alignment

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __show_menubar_message(self, task=None):

        MessageDialog(title="Menu access",
                      message="The menu bar is hidden, but its menus can still\n"
                              "be accessed through the main context menu\n"
                              "(Ctrl + right-click in the viewport).",
                      choices="ok")

    def __hide_components_at_startup(self):

        components = self._registry
        docks = components["docks"]
        config_data = GD["config"]
        component_view = config_data["gui_view"]
        docking_targets = components["docking_targets"]

        if not component_view["menubar"]:
            menubar = components["menubar"]
            dock = docks["top"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[0]
            subsizer = subsizer_cell.object
            subsizer.remove_cell(menubar.sizer_cell)
            menubar.hide()
            docking_targets.remove(menubar)
            Mgr.do_next_frame(self.__show_menubar_message, "show_menubar_message")

        if not component_view["statusbar"]:
            statusbar = components["statusbar"]
            dock = docks["bottom"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[-1]
            subsizer = subsizer_cell.object
            subsizer.remove_cell(statusbar.sizer_cell)
            statusbar.hide()
            docking_targets.remove(statusbar)

        if not component_view["toolbars"]:
            self.__clear_toolbar_layout(config_data["gui_layout"]["toolbars"]["main"])

        if not component_view["control_pane"]:
            control_pane = components["control_pane"]
            control_pane_frame = control_pane.frame
            dock = docks["right"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[0]
            subsizer = subsizer_cell.object
            subsizer.remove_cell(control_pane_frame.sizer_cell)
            control_pane.hide()

        if False in component_view.values():
            self.__update_window()

    def __show_components(self, component_types, show=True):

        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]
        config_data = GD["config"]

        if "menubar" in component_types:

            menubar = components["menubar"]
            dock = docks["top"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[0]
            subsizer = subsizer_cell.object

            if show:
                menubar.show()
                subsizer.add(menubar, proportions=(1., 0.))
                docking_targets.append(menubar)
            else:
                subsizer.remove_cell(menubar.sizer_cell)
                menubar.hide()
                docking_targets.remove(menubar)

        if "statusbar" in component_types:

            statusbar = components["statusbar"]
            dock = docks["bottom"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[-1]
            subsizer = subsizer_cell.object

            if show:
                statusbar.show()
                subsizer.add(statusbar, proportions=(1., 0.))
                docking_targets.append(statusbar)
            else:
                subsizer.remove_cell(statusbar.sizer_cell)
                statusbar.hide()
                docking_targets.remove(statusbar)

        if "toolbars" in component_types:

            layout = config_data["gui_layout"]["toolbars"]
            interface_id = "main"
            viewport_data = GD["viewport"]

            if viewport_data[2]:
                if viewport_data[2] == "main":
                    interface_id = viewport_data[1]
                else:
                    interface_id = viewport_data[2]

            if show:
                self.__create_toolbar_layout(layout[interface_id])
            else:
                self.__clear_toolbar_layout(layout[interface_id])

        if "control_pane" in component_types:

            control_pane = components["control_pane"]
            control_pane_frame = control_pane.frame
            dock = docks["right"]
            sizer = dock.sizer
            subsizer_cell = sizer.cells[0]
            subsizer = subsizer_cell.object

            if show:
                control_pane.show()
                subsizer.add(control_pane_frame, proportions=(0., 1.))
            else:
                subsizer.remove_cell(control_pane_frame.sizer_cell)
                control_pane.hide()

        self.__update_window()

        if "menubar" in component_types and not show:
            self.__show_menubar_message()

        component_view = config_data["gui_view"]

        for component_type in component_types:
            component_view[component_type] = show

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __get_default_component_view(self):

        component_view = {}
        component_view["menubar"] = True
        component_view["statusbar"] = True
        component_view["toolbars"] = True
        component_view["control_pane"] = True

        return component_view

    def __create_toolbar_layout(self, layout_data):

        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]
        toolbars = Toolbar.registry

        for alignment, toolbar_id_lists in layout_data.items():

            dock = docks[alignment]
            dock_sizer = dock.sizer
            toolbar_sizers = dock.toolbar_sizers

            for i, toolbar_id_list in enumerate(toolbar_id_lists):

                if toolbar_id_list is None:
                    continue

                row_sizer = Sizer("horizontal")
                dock_sizer.add(row_sizer, alignments=("expand", "min"), index=i)
                toolbar_sizers.append(row_sizer)

                if len(toolbar_id_list) > 1:

                    bundled_rows = []

                    for toolbar_ids in toolbar_id_list:

                        toolbar_row = ToolbarRow(dock)
                        docking_targets.append(toolbar_row.handle)
                        bundled_rows.append(toolbar_row)

                        for toolbar_id in toolbar_ids:
                            toolbar = toolbars[toolbar_id]
                            toolbar.set_parent(dock)
                            toolbar.row = toolbar_row
                            toolbar_row.add_toolbar(toolbar)
                            docking_targets.append(toolbar)

                    bottom_row = bundled_rows[0]

                    for toolbar in bottom_row:
                        row_sizer.add(toolbar)

                    row_sizer.add(bottom_row.handle, proportions=(1., 0.))
                    w_min = row_sizer.update_min_size()[0]
                    bottom_row.set_min_width_in_bundle(w_min)
                    bundle = bottom_row.bundle

                    for row in bundled_rows[1:]:

                        for toolbar in row:
                            row_sizer.remove_cell(row_sizer.add(toolbar))

                        handle = row.handle
                        row_sizer.remove_cell(row_sizer.add(handle, proportions=(1., 0.)))
                        bundle.add_toolbar_row(row)
                        w_min = row_sizer.update_min_size()[0]
                        row.set_min_width_in_bundle(w_min)

                    width = bundle.get_min_width()

                else:

                    toolbar_row = ToolbarRow(dock)
                    docking_targets.append(toolbar_row.handle)

                    for toolbar_id in toolbar_id_list[0]:
                        toolbar = toolbars[toolbar_id]
                        row_sizer.add(toolbar)
                        toolbar.set_parent(dock)
                        toolbar.row = toolbar_row
                        toolbar_row.add_toolbar(toolbar)
                        docking_targets.append(toolbar)

                    row_sizer.add(toolbar_row.handle, proportions=(1., 0.))
                    width = row_sizer.update_min_size()[0]
                    toolbar_row.set_min_width_in_bundle(width)

                row_sizer.default_size = (width, 0)

    def __clear_toolbar_layout(self, layout_data):

        components = self._registry
        docks = components["docks"]
        docking_targets = components["docking_targets"]
        toolbars = Toolbar.registry

        toolbar_rows = set()
        bundles = set()
        toolbar_ids = []

        for toolbar_id_lists in layout_data.values():

            for toolbar_id_list in toolbar_id_lists:

                if toolbar_id_list is None:
                    continue

                for id_list in toolbar_id_list:
                    toolbar_ids.extend(id_list)

        for toolbar_id in toolbar_ids:

            toolbar = toolbars[toolbar_id]
            docking_targets.remove(toolbar)
            toolbar_row = toolbar.row
            toolbar_rows.add(toolbar_row)

            if toolbar_row.in_bundle:
                bundles.add(toolbar_row.bundle)

            toolbar.sizer_cell = None
            toolbar.hide()

        for bundle in bundles:
            bundle.destroy()

        for toolbar_row in toolbar_rows:
            docking_targets.remove(toolbar_row.handle)
            toolbar_row.destroy()

        for alignment in ("top", "bottom"):

            dock = docks[alignment]
            dock_sizer = dock.sizer
            toolbar_sizers = dock.toolbar_sizers

            while toolbar_sizers:
                row_sizer = toolbar_sizers.pop()
                dock_sizer.remove_cell(row_sizer.sizer_cell)
                row_sizer.clear()
                row_sizer.destroy()

    def __reset_layout_data(self, interface_id=None):

        import copy

        config_data = GD["config"]

        if interface_id is None:
            config_data["gui_layout"]["toolbars"] = copy.deepcopy(Skin.layout.toolbars)
        else:
            toolbar_layout = copy.deepcopy(Skin.layout.toolbars[interface_id])
            config_data["gui_layout"]["toolbars"][interface_id] = toolbar_layout

        config_data["gui_layout"]["control_pane_alignment"] = "right"

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __init_main_layout(self):

        import copy

        config_data = GD["config"]
        layout = config_data.get("gui_layout")
        component_view = config_data.get("gui_view")

        if not layout:
            config_data["gui_layout"] = layout = {}
            layout["toolbars"] = copy.deepcopy(Skin.layout.toolbars)
            layout["control_pane_alignment"] = "right"

        if not component_view:
            component_view = self.__get_default_component_view()
            config_data["gui_view"] = component_view

        if not (layout or component_view):
            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

        alignment = layout["control_pane_alignment"]

        if alignment == "left":
            dock = self._registry["docks"]["right"]
            sizer_cell = dock.sizer_cell
            sizer = sizer_cell.sizer
            sizer.remove_cell(sizer_cell)
            sizer.add_cell(sizer_cell, index=0)

        self.__create_toolbar_layout(layout["toolbars"]["main"])

    def __create_main_toolbar_layout(self):

        config_data = GD["config"]

        if config_data["gui_view"]["toolbars"]:
            layout_data = config_data["gui_layout"]["toolbars"]["main"]
            self.__create_toolbar_layout(layout_data)

    def __clear_main_toolbar_layout(self):

        config_data = GD["config"]

        if config_data["gui_view"]["toolbars"]:
            layout_data = config_data["gui_layout"]["toolbars"]["main"]
            self.__clear_toolbar_layout(layout_data)

    def __update_toolbar_layout(self):

        self.__clear_main_toolbar_layout()
        self.__create_main_toolbar_layout()
        self.__update_window()

    def __update_layout_data(self):

        config_data = GD["config"]
        config_data["gui_layout"]["toolbars"][GD["active_interface"]] = layout = {}
        toolbars = Toolbar.registry
        docks = self._registry["docks"]

        for alignment in ("top", "bottom"):

            layout[alignment] = toolbar_id_lists = []
            dock = docks[alignment]
            dock_sizer = dock.sizer
            toolbar_sizers = dock.toolbar_sizers

            for cell in dock_sizer.cells:

                sizer = cell.object

                if sizer in toolbar_sizers:

                    toolbar_id_list = []
                    toolbar_id_lists.append(toolbar_id_list)
                    toolbar_row = sizer.cells[0].object.row

                    if toolbar_row.in_bundle:
                        for row in toolbar_row.bundle:
                            toolbar_ids = [t.id for t in row]
                            toolbar_id_list.append(toolbar_ids)
                    else:
                        toolbar_ids = [t.id for t in toolbar_row]
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
            fps_meter_display_region = GD["fps_meter_display_region"]
            fps_meter_display_region.active = False
            GD.showbase.graphicsEngine.render_frame()
            tex = GD.window.get_screenshot()
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

            self._screenshot.detach_node()
            self._screenshot = None
            fps_meter_display_region = GD["fps_meter_display_region"]
            fps_meter_display_region.active = True

    def __show_main_context_menu(self, *extra_submenu_ids):

        ToolTip.hide()
        components = self._registry
        menubar = components["menubar"]
        context_submenu = components["main_context_submenu"]

        for menu_id, item in context_submenu.items.items():
            menu = menubar.get_menu(menu_id)
            item.set_submenu(menu)

        context_menu = components["main_context_menu"]
        self._extra_submenu_ids = extra_submenu_ids
        extra_menu_items = self._extra_menu_items

        for menu_id in extra_submenu_ids:

            menu_name, menu = Mgr.get(f"menu_{menu_id}")

            if menu_id in extra_menu_items:
                item = extra_menu_items[menu_id]
                context_menu.add_item(item)
            else:
                item = context_menu.add(menu_id, menu_name, item_type="submenu")
                item.get_submenu().destroy()
                item.enable()
                extra_menu_items[menu_id] = item

            item.set_submenu(menu)

        if extra_submenu_ids:
            context_menu.update()

        context_menu.show_at_mouse_pos()

    def dragging_toolbars(self):

        return self._dragging_toolbars

    def __update_insertion_marker(self, task):

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        point = (mouse_pointer.x, mouse_pointer.y)

        for target in self._registry["docking_targets"]:

            docking_data = target.get_docking_data(point)

            if docking_data:

                target_component, alignment, pos = docking_data

                if target_component.is_hidden():
                    continue

                if target_component.widget_type == "toolbar_row_handle":
                    if alignment == "center":
                        if target_component is self._dragged_widget:
                            continue
                        self._toolbar_insertion_marker.set_type("+")
                    else:
                        self._toolbar_insertion_marker.set_type("h")
                elif alignment in ("left", "right"):
                    if (target_component is self._dragged_widget
                            or self._dragged_item_type == "toolbar_bundle"
                            or (self._dragged_item_type == "toolbar_row"
                            and target_component in self._dragged_widget.row)):
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

        name = region.name

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
                widget = widget.parent

            if is_toolbar and {widget} == set(widget.row):
                # if the dragged toolbar is the only one in its row, this is equivalent
                # to dragging the row itself
                widget = widget.row.handle
                item_type = "toolbar_row"
                is_toolbar = False

            self._dragged_widget = widget
            self._dragged_item_type = item_type

            if not is_toolbar:
                widget = widget.row

            widget.create_ghost_image()
            ToolTip.hide()
            self._dragging_toolbars = True
            Mgr.add_task(self.__update_insertion_marker, "update_insertion_marker")
            self.__enable(False)
            Mgr.enter_state("inactive")
            interface_ids = GD["viewport"]

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
        target_component, alignment, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        sizer_cell = toolbar.sizer_cell
        row_sizer = sizer_cell.sizer
        toolbar_row = toolbar.row
        toolbar_row.remove_toolbar(toolbar)
        target_sizer_cell = target_component.sizer_cell
        target_subsizer = target_sizer_cell.sizer
        target_sizer = target_subsizer.owner
        toolbar.set_parent(target_sizer.owner)
        row_sizer.remove_cell(sizer_cell)
        row_sizer.default_size = (0, 0)
        width = row_sizer.update_min_size()[0]
        toolbar_row.set_min_width_in_bundle(width)

        if toolbar_row.in_bundle:
            width = toolbar_row.bundle.get_min_width()
        else:
            width = toolbar_row.get_min_width(in_bundle=False)

        row_sizer.default_size = (width, 0)

        if target_component.widget_type == "toolbar_row_handle":

            dest_row = ToolbarRow(target_dock)
            toolbar.row = dest_row
            dest_row.add_toolbar(toolbar)
            handle = dest_row.handle
            target_subsizer.remove_cell(target_subsizer.add(handle, proportions=(1., 0.)))
            target_row = target_component.row
            bundle = target_row.bundle
            bundle.add_toolbar_row(dest_row)
            target_subsizer.default_size = (0, 0)
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            width = bundle.get_min_width()
            target_subsizer.default_size = (width, 0)
            docking_targets.append(handle)

        elif alignment in ("bottom", "top"):

            index = target_sizer.cells.index(target_subsizer.sizer_cell)

            if alignment == "bottom":
                index += 1

            new_row_sizer = Sizer("horizontal")
            new_row_sizer.add_cell(sizer_cell)
            dest_row = ToolbarRow(target_dock)
            toolbar.row = dest_row
            dest_row.add_toolbar(toolbar)
            handle = dest_row.handle
            new_row_sizer.add(handle, proportions=(1., 0.))
            w_min = new_row_sizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            w_min = dest_row.get_min_width(in_bundle=False)
            new_row_sizer.default_size = (w_min, 0)
            target_sizer.add(new_row_sizer, alignments=("expand", "min"), index=index)
            target_dock.toolbar_sizers.append(new_row_sizer)
            docking_targets.append(handle)

        else:

            index = target_subsizer.cells.index(target_sizer_cell)

            if alignment == "right":
                index += 1

            target_subsizer.add_cell(sizer_cell, index=index)
            dest_row = target_component.row
            toolbar.row = dest_row
            dest_row.add_toolbar(toolbar, index)
            w_d = target_subsizer.default_size[0]
            target_subsizer.default_size = (0, 0)
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            w_min = dest_row.get_min_width(in_bundle=dest_row.in_bundle)
            width = max(w_d, w_min)
            target_subsizer.default_size = (width, 0)

    def __move_toolbar_row(self, toolbar_row_handle):

        docking_targets = self._registry["docking_targets"]
        target_component, alignment, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        src_dock = toolbar_row_handle.get_ancestor("dock")
        sizer_cell = toolbar_row_handle.sizer_cell
        row_sizer = sizer_cell.sizer
        row_sizer_cell = row_sizer.sizer_cell
        toolbar_row = toolbar_row_handle.row
        target_sizer_cell = target_component.sizer_cell
        target_subsizer = target_sizer_cell.sizer
        target_sizer = target_subsizer.owner
        parent = target_sizer.owner
        toolbar_row_handle.set_parent(parent)
        in_bundle = toolbar_row.in_bundle

        if in_bundle:

            bundle = toolbar_row.bundle
            rows = list(bundle)
            rows.remove(toolbar_row)
            next_row = bundle.remove_toolbar_row()

            if next_row.in_bundle:
                width = bundle.get_min_width()
            else:
                width = next_row.get_min_width(in_bundle=False)

            row_sizer.default_size = (width, 0)

        if target_component.widget_type == "toolbar_row_handle":

            target_row = target_component.row
            bundle = target_row.bundle
            bundle.add_toolbar_row(toolbar_row)
            target_subsizer.default_size = (0, 0)
            w_min = target_subsizer.update_min_size()[0]
            toolbar_row.set_min_width_in_bundle(w_min)
            width = bundle.get_min_width()
            target_subsizer.default_size = (width, 0)

            if not in_bundle:
                row_sizer_cell.sizer.remove_cell(row_sizer_cell)
                row_sizer.clear()
                row_sizer.destroy()
                src_dock.toolbar_sizers.remove(row_sizer)

        elif alignment in ("bottom", "top"):

            if not in_bundle:

                if target_subsizer is row_sizer:
                    return

                row_sizer_cell.sizer.remove_cell(row_sizer_cell)
                src_dock.toolbar_sizers.remove(row_sizer)

            index = target_sizer.cells.index(target_subsizer.sizer_cell)

            if alignment == "bottom":
                index += 1

            if in_bundle:

                row_sizer = Sizer("horizontal")

                for toolbar in toolbar_row:
                    row_sizer.add_cell(toolbar.sizer_cell)

                row_sizer.add_cell(sizer_cell)
                target_sizer.add(row_sizer, alignments=("expand", "min"), index=index)

            else:

                target_sizer.add_cell(row_sizer_cell, index=index)

            target_dock.toolbar_sizers.append(row_sizer)
            row_sizer.default_size = (toolbar_row.get_min_width(in_bundle=False), 0)

            for toolbar in toolbar_row:
                toolbar.set_parent(parent)

        else:

            index = target_subsizer.cells.index(target_sizer_cell)

            if alignment == "right":
                index += 1

            dest_row = target_component.row
            dest_row.add_toolbars(toolbar_row, index)

            for toolbar in toolbar_row[::-1]:
                toolbar.set_parent(parent)
                toolbar.row = dest_row
                target_subsizer.add_cell(toolbar.sizer_cell, index=index)

            w_d = target_subsizer.default_size[0]
            target_subsizer.default_size = (0, 0)
            w_min = target_subsizer.update_min_size()[0]
            dest_row.set_min_width_in_bundle(w_min)
            width = max(w_d, w_min)
            target_subsizer.default_size = (width, 0)
            toolbar_row.destroy_ghost_image()
            toolbar_row.destroy()
            docking_targets.remove(toolbar_row_handle)

            if not in_bundle:
                row_sizer_cell.sizer.remove_cell(row_sizer_cell)
                row_sizer.clear()
                row_sizer.destroy()
                src_dock.toolbar_sizers.remove(row_sizer)

    def __move_toolbar_bundle(self, toolbar_row_handle):

        docking_targets = self._registry["docking_targets"]
        target_component, alignment, _ = self._docking_data
        target_dock = target_component.get_ancestor("dock")
        src_dock = toolbar_row_handle.get_ancestor("dock")
        sizer_cell = toolbar_row_handle.sizer_cell
        row_sizer = sizer_cell.sizer
        row_sizer_cell = row_sizer.sizer_cell
        toolbar_row = toolbar_row_handle.row
        target_sizer_cell = target_component.sizer_cell
        target_subsizer = target_sizer_cell.sizer
        target_sizer = target_subsizer.owner

        if target_component.widget_type == "toolbar_row_handle":

            row_sizer_cell.sizer.remove_cell(row_sizer_cell)
            src_dock.toolbar_sizers.remove(row_sizer)
            target_row = target_component.row
            bundle = target_row.bundle
            bundle.add_toolbar_row(toolbar_row)
            width = max(bundle.get_min_width(), target_subsizer.default_size[0])
            target_subsizer.default_size = (width, 0)
            row_sizer.clear()
            row_sizer.destroy()

        else:

            if target_subsizer is row_sizer:
                return

            row_sizer_cell.sizer.remove_cell(row_sizer_cell)
            src_dock.toolbar_sizers.remove(row_sizer)
            index = target_sizer.cells.index(target_subsizer.sizer_cell)

            if alignment == "bottom":
                index += 1

            target_sizer.add_cell(row_sizer_cell, index=index)
            parent = target_sizer.owner
            toolbar_row.set_parent(parent)
            target_dock.toolbar_sizers.append(row_sizer)

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
        interface_ids = GD["viewport"]

        if interface_ids[2] is not None:
            interface_id = interface_ids[2 if interface_ids[1] == "main" else 1]
            Mgr.exit_state("inactive", interface_id)

        Mgr.set_cursor("main")

    def __set_viewport_border_color(self, color_id):

        color = Skin.colors[color_id]
        index = 2 if GD["viewport"][2] == "main" else 1
        GD["viewport"][f"border_color{index}"] = color

        if GD["viewport"]["active"] == index:
            GD["viewport"][f"border{index}"].clear_color = color

    def __set_active_viewport(self, index):

        GD["viewport"]["active"] = index
        color = GD["viewport"][f"border_color{index}"]
        GD["viewport"][f"border{index}"].clear_color = color
        color = Skin.colors["viewport_frame_inactive"]
        GD["viewport"][f"border{3 - index}"].clear_color = color
        interface_id = GD["viewport"][index]
        Mgr.do("set_interface_status", interface_id)
        Mgr.send("focus_loss")

    def __update_viewport_display_regions(self):

        viewport2_id = GD["viewport"][2]

        l, r, b, t = GD["viewport"]["frame_aux" if viewport2_id == "main" else "frame"]
        frame = (2. * l - 1., 2. * r - 1., 2. * b - 1., 2. * t - 1.)
        Mgr.get("viewport_cursor_region").frame = frame

        for dr in GD["viewport"]["display_regions"]:
            dr.dimensions = (l, r, b, t)

        if viewport2_id is not None:

            l, r, b, t = GD["viewport"]["frame" if viewport2_id == "main" else "frame_aux"]
            frame = (2. * l - 1., 2. * r - 1., 2. * b - 1., 2. * t - 1.)
            Mgr.get("viewport2_cursor_region").frame = frame

            for dr in GD["viewport"]["display_regions2"]:
                dr.dimensions = (l, r, b, t)

        w, h = self._window_size
        l, r, b, t = GD["viewport"]["frame" if viewport2_id is None else "frame_aux"]
        GD["fps_meter_display_region"].dimensions = (r - 800./w, r, b, b + 600./h)

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
        GD["viewport"]["pos"] = (x, y)
        GD["viewport"]["size"] = (w_v, h_v)
        GD["viewport"]["frame"] = get_relative_region_frame(x, y, w_v, h_v, w_, h_)

        if GD["viewport"][2] is not None:
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

        win_props = window.properties
        w, h = win_props.size
        w, h = max(1, w), max(1, h)

        if self._window_size != (w, h):

            self._window_size = (w, h)
            win_props = WindowProperties()
            win_props.size = (w, h)
            window.request_properties(win_props)
            Mgr.get("gui_root").set_scale(2./w, 1., 2./h)

            if PLATFORM_ID == "Windows":
                self.__update_window()
            else:
                self._black_card.set_scale(w, 1., h)
                self._black_card.show()
                Mgr.remove_task("update_window")
                Mgr.add_task(.2, self.__update_window, "update_window")

        if not win_props.foreground:
            Mgr.send("focus_loss")

    def handle_hotkey(self, hotkey, hotkey_repeat):

        HotkeyManager.handle_widget_hotkey(hotkey, hotkey_repeat)

    def __enable(self, enable=True):

        if self._is_enabled == enable:
            return

        mask = self._gui_region_mask
        components = self._registry

        for mouse_watcher in GD["mouse_watchers"]:
            mouse_watcher.remove_region(mask) if enable else mouse_watcher.add_region(mask)

        components["uv"].enable(enable)
        self._is_enabled = enable

    def is_enabled(self):

        return self._is_enabled

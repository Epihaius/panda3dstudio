from .base import *
from .data import UVDataObject, VertexEditManager, EdgeEditManager, PolygonEditManager
from .cam import UVNavigationBase, UVTemplateSaver
from .uv_select import UVSelectionBase
from .uv_transform import UVTransformationBase
from .world_select import SelectionManager
from .helpers import Grid, UVTransformGizmo


class UVEditor(UVNavigationBase, UVSelectionBase, UVTransformationBase,
               VertexEditManager, EdgeEditManager, PolygonEditManager):

    def __init__(self):

        uv_space = NodePath("uv_space")
        lens = OrthographicLens()
        lens.set_near(-10.)
        lens.set_film_size(600. / 512.)
        cam_node = Camera("main_uv_cam", lens)
        cam_node.set_active(False)
        mask = BitMask32.bit(24)
        cam_node.set_camera_mask(mask)
        UVMgr.expose("render_mask", lambda: mask)
        cam = uv_space.attach_new_node(cam_node)
        cam.set_pos(.5, -10., .5)
        geom_root = uv_space.attach_new_node("uv_geom_root")
        BaseObject.init(uv_space, cam, cam_node, lens, geom_root)
        UVMgr.init(verbose=True)

        self._uv_registry = {}
        self._uv_data_objs = {}
        self._uv_data_obj_copies = {}
        self._models = []

        UVNavigationBase.__init__(self)
        UVSelectionBase.__init__(self)
        UVTransformationBase.__init__(self)

        self._world_sel_mgr = SelectionManager(self)
        self._uv_template_saver = UVTemplateSaver()
        self._grid = Grid()
        self._transf_gizmo = UVTransformGizmo()

        self._window = None

        self._obj_lvl = "top"
        UVMgr.expose("active_obj_level", lambda: self._obj_lvl)

        self._uv_set_id = 0
        UVMgr.expose("active_uv_set", lambda: self._uv_set_id)

        state_np = NodePath("render_state")
        state_np.set_light_off()
        state_np.set_texture_off()
        state_np.set_material_off()
        state_np.set_shader_off()
        state_np.set_depth_write(False)
        state_np.set_depth_test(False)
        state_np.set_color_off()
        state_np.set_transparency(TransparencyAttrib.M_none)

        vert_state_np = NodePath(state_np.node().make_copy())
        vert_state_np.set_render_mode_thickness(7)
        vert_state_np.set_bin("background", 13)

        edge_state_np = NodePath(state_np.node().make_copy())
        edge_state_np.set_bin("background", 11)

        poly_unsel_state_np = NodePath(state_np.node().make_copy())
        poly_unsel_state_np.set_two_sided(True)
        poly_unsel_state_np.set_transparency(TransparencyAttrib.M_alpha)
        poly_unsel_color = VBase4(.3, .3, .3, .5)
        poly_unsel_state_np.set_color(poly_unsel_color)
        poly_unsel_state_np.set_bin("background", 10)

        poly_sel_state_np = NodePath(poly_unsel_state_np.node().make_copy())
        poly_sel_color = VBase4(1., 0., 0., 1.)
        poly_sel_state_np.set_color(poly_sel_color)
        tex_stage = TextureStage("uv_poly_selection")
        tex_stage.set_mode(TextureStage.M_add)
        poly_sel_state_np.set_tex_gen(tex_stage, RenderAttrib.M_world_position)
        poly_sel_state_np.set_tex_projector(tex_stage, BaseObject.uv_space, BaseObject.cam)
        tex = Texture()
        tex.read(Filename(GFX_PATH + "sel_tex.png"))
        poly_sel_state_np.set_texture(tex_stage, tex)
        poly_sel_state_np.set_tex_scale(tex_stage, 100.)

        vert_state = vert_state_np.get_state()
        edge_state = edge_state_np.get_state()
        poly_unsel_state = poly_unsel_state_np.get_state()
        poly_sel_state = poly_sel_state_np.get_state()
        poly_sel_effects = poly_sel_state_np.get_effects()
        self._poly_colors = {"unselected": poly_unsel_color, "selected": poly_sel_color}
        self._poly_states = {"unselected": poly_unsel_state, "selected": poly_sel_state}
        UVMgr.expose("vert_render_state", lambda: vert_state)
        UVMgr.expose("edge_render_state", lambda: edge_state)
        UVMgr.expose("poly_states", lambda: self._poly_states)
        UVMgr.expose("poly_selection_effects", lambda: poly_sel_effects)

        vert_colors = {"selected": (1., 0., 0., 1.), "unselected": (.5, .5, 1., 1.)}
        edge_colors = {"selected": (1., 0., 0., 1.), "unselected": (1., 1., 1., 1.)}
        seam_colors = {"selected": (1., .5, 1., 1.), "unselected": (0., 1., 0., 1.)}
        self._uv_sel_colors = {"vert": vert_colors, "edge": edge_colors, "seam": seam_colors}
        UVMgr.expose("uv_selection_colors", lambda: self._uv_sel_colors)

        UVMgr.accept("clear_unselected_poly_state", self.__clear_unselected_poly_state)
        UVMgr.accept("reset_unselected_poly_state", self.__reset_unselected_poly_state)

        Mgr.add_app_updater("uv_viewport", self.__toggle_viewport)

    def setup(self):

        if not self._transf_gizmo.setup():
            return False

        self._world_sel_mgr.setup()

        return True

    def __toggle_viewport(self, create, size=None, parent_handle=None):

        if GlobalData["ctrl_down"]:
            GlobalData["ctrl_down"] = False

        core = Mgr.get("core")

        if not create:

            if self._window:
                self.__update_history()
                Mgr.update_interface_locally("uv_window", "uv_background", "show_on_models", False)
                Mgr.remove_task("update_cursor_uvs")
                Mgr.remove_interface("uv_window")
                UVMgr.get("picking_cam").set_active(False)
                self.cam_node.set_active(False)
                self.delete_selections()
                self.__destroy_uv_data()
                self._obj_lvl = "top"
                self._uv_set_id = 0
                self.__update_object_level()
                self._transf_gizmo.hide()
                Mgr.exit_state("uv_edit_mode")
                core.close_window(self._window, keepCamera=True)
                self._window = None
                self._models = []

            return

        wp = WindowProperties.get_default()
        wp.set_foreground(False)
        wp.set_origin(0, 0)
        wp.set_size(*size)

        try:
            wp.set_parent_window(parent_handle)
        except OverflowError:
            wp.set_parent_window(parent_handle & 0xffffffff)

        self._window = win = core.open_window(props=wp, name="uv_window", makeCamera=False)
        display_region = win.get_display_region(0)
        display_region.set_camera(self.cam)
        display_region.set_active(True)
        data_root = core.buttonThrowers[0].get_top()
        input_ctrl = data_root.attach_new_node(MouseAndKeyboard(win, 0, "input_ctrl_uv_win"))
        mouse_watcher_node = MouseWatcher()
        mouse_watcher_node.set_display_region(display_region)
        mouse_watcher_node.set_modifier_buttons(ModifierButtons())
        Mgr.add_interface("uv_window", "uv_win_", mouse_watcher_node)
        BaseObject.set_mouse_watcher(mouse_watcher_node)
        mouse_watcher = input_ctrl.attach_new_node(mouse_watcher_node)
        btn_thrower_node = ButtonThrower("btn_thrower_uv_win")
        btn_thrower_node.set_prefix("uv_win_")
        btn_thrower_node.set_modifier_buttons(ModifierButtons())
        mouse_watcher.attach_new_node(btn_thrower_node)
        self._reset_view()
        self.cam_node.set_active(True)
        UVMgr.get("picking_cam").set_active()
        self._models = self._world_sel_mgr.get_models()

        UVSelectionBase.setup(self)
        UVNavigationBase.setup(self)
        UVTransformationBase.setup(self)
        VertexEditManager.setup(self)
        EdgeEditManager.setup(self)
        PolygonEditManager.setup(self)
        Mgr.set_initial_state("uv_edit_mode", "uv_window")

        def set_obj_level(obj_lvl):

            self._obj_lvl = obj_lvl
            self.__update_object_level()

        Mgr.add_interface_updater("uv_window", "uv_level", set_obj_level)
        Mgr.add_interface_updater("uv_window", "active_uv_set", self.__update_uv_set)
        Mgr.add_interface_updater("uv_window", "uv_set_copy", self.__copy_uv_set)
        Mgr.add_interface_updater("uv_window", "uv_set_paste", self.__paste_uv_set)
        Mgr.add_interface_updater("uv_window", "poly_color", self.__update_poly_color)

        self._grid.add_interface_updaters()
        self._uv_template_saver.add_interface_updaters()
        self._transf_gizmo.add_interface_updaters()
        self._transf_gizmo.update_transform_handles()
        GlobalData["active_uv_transform_type"] = ""
        Mgr.update_interface("uv_window", "active_transform_type", "")

        for sel_state in ("unselected", "selected"):
            r, g, b, a = self._poly_colors[sel_state]
            Mgr.update_interface_remotely("uv_window", "poly_color", sel_state, "rgb", (r, g, b))
            Mgr.update_interface_remotely("uv_window", "poly_color", sel_state, "alpha", a)

        self.__create_uv_data()
        self.create_selections()

        self._obj_lvl = "poly"
        self.__update_object_level()

        UVMgr.do("remotely_update_background")
        UVMgr.do("remotely_update_template_props")

    def __create_uv_data(self):

        models = self._models
        uv_set_id = self._uv_set_id
        self._uv_registry[uv_set_id] = uv_registry = {"vert": {}, "edge": {}, "poly": {}}
        self._uv_data_objs[uv_set_id] = uv_data_objs = {}

        for model in models:
            geom_data_obj = model.get_geom_object().get_geom_data_object()
            uv_data_objs[geom_data_obj] = UVDataObject(uv_set_id, uv_registry, geom_data_obj)

        # render a frame to make sure that GeomPrimitives with temporary vertices
        # will still be rendered after making them empty (in the next frame)
        Mgr.render_frame()

    def __destroy_uv_data(self):

        for uv_data_objs in self._uv_data_objs.itervalues():
            for uv_data_obj in uv_data_objs.itervalues():
                uv_data_obj.destroy()

        for geom_data_obj, uv_data_obj in self._uv_data_obj_copies.iteritems():
            geom_data_obj.clear_copied_uvs()

        self._uv_registry.clear()
        self._uv_data_objs.clear()
        self._uv_data_obj_copies.clear()

    def __update_object_level(self):

        obj_lvl = self._obj_lvl
        self._world_sel_mgr.set_object_level(obj_lvl)

        if obj_lvl != "top":

            for uv_data_objs in self._uv_data_objs.itervalues():
                for uv_data_obj in uv_data_objs.itervalues():
                    uv_data_obj.show_subobj_level(obj_lvl)

            self.update_selection(recreate=True)

    def __update_uv_set(self, uv_set_id):

        if uv_set_id == self._uv_set_id:
            return

        uv_data_objs = self._uv_data_objs[self._uv_set_id]

        for uv_data_obj in uv_data_objs.itervalues():
            uv_data_obj.hide()

        self._uv_set_id = uv_set_id

        if uv_set_id in self._uv_data_objs:

            uv_data_objs = self._uv_data_objs[uv_set_id]

            for geom_data_obj, uv_data_obj in uv_data_objs.iteritems():
                geom_data_obj.set_tex_seams(uv_set_id)
                uv_data_obj.show()

        else:

            self.__create_uv_data()
            self.create_selections()
            self.__update_object_level()

        self.update_selection()

        for obj_lvl in ("vert", "edge", "poly"):

            selection = self._selections[uv_set_id][obj_lvl]

            if obj_lvl == "poly":

                color_ids = [subobj.get_picking_color_id() for subobj in selection]

            else:

                color_ids = []

                for subobj in selection:
                    color_ids.extend(subobj.get_picking_color_ids())

            self._world_sel_mgr.sync_selection(color_ids, object_level=obj_lvl)

    def __copy_uv_set(self):

        uv_set_id = self._uv_set_id
        uv_data_objs = self._uv_data_objs[uv_set_id]
        copies = self._uv_data_obj_copies

        for geom_data_obj, uv_data_obj in uv_data_objs.iteritems():
            copies[geom_data_obj] = uv_data_obj.copy()
            geom_data_obj.copy_uvs(uv_set_id)

    def __paste_uv_set(self):

        copies = self._uv_data_obj_copies

        if not copies:
            return

        uv_set_id = self._uv_set_id
        self._uv_registry[uv_set_id] = uv_registry = {"vert": {}, "edge": {}, "poly": {}}
        uv_data_objs = self._uv_data_objs[uv_set_id]
        self.create_selections()
        selections = {"vert": [], "edge": [], "poly": []}

        for geom_data_obj, uv_data_obj in uv_data_objs.iteritems():

            uv_data_obj.destroy()
            copy = copies[geom_data_obj].copy(uv_set_id)
            copy.show()
            uv_data_objs[geom_data_obj] = copy

            for subobj_type in ("vert", "edge", "poly"):
                uv_registry[subobj_type] = dict((s.get_picking_color_id(), s)
                                                for s in copy.get_subobjects(subobj_type).itervalues())
                selections[subobj_type] = copy.get_selection(subobj_type)

            geom_data_obj.paste_uvs(uv_set_id)

        for subobj_type in ("vert", "edge", "poly"):
            self._selections[uv_set_id][subobj_type].set(selections[subobj_type])

        self.__update_object_level()

        for obj_lvl in ("vert", "edge", "poly"):

            selection = self._selections[uv_set_id][obj_lvl]

            if obj_lvl == "poly":

                color_ids = [subobj.get_picking_color_id() for subobj in selection]

            else:

                color_ids = []

                for subobj in selection:
                    color_ids.extend(subobj.get_picking_color_ids())

            self._world_sel_mgr.sync_selection(color_ids, object_level=obj_lvl)

    def __clear_unselected_poly_state(self):

        uv_data_objs = self._uv_data_objs[self._uv_set_id]
        state = RenderState.make_empty()

        for uv_data_obj in uv_data_objs.itervalues():
            uv_data_obj.set_poly_state("unselected", state)

    def __reset_unselected_poly_state(self):

        uv_data_objs = self._uv_data_objs[self._uv_set_id]
        state = self._poly_states["unselected"]

        for uv_data_obj in uv_data_objs.itervalues():
            uv_data_obj.set_poly_state("unselected", state)

    def __update_poly_color(self, sel_state, channels, value):

        poly_colors = self._poly_colors
        poly_states = self._poly_states
        color = poly_colors[sel_state]
        state = poly_states[sel_state]

        if channels == "rgb":
            for i in range(3):
                color[i] = value[i]
        elif channels == "alpha":
            color[3] = value

        state = state.add_attrib(ColorAttrib.make_flat(color))

        poly_colors[sel_state] = color
        poly_states[sel_state] = state

        uv_data_objs = self._uv_data_objs[self._uv_set_id]

        for uv_data_obj in uv_data_objs.itervalues():
            uv_data_obj.set_poly_state(sel_state, state)

        r, g, b, a = poly_colors[sel_state]
        value = {"rgb": (r, g, b), "alpha": a}[channels]
        Mgr.update_interface_remotely("uv_window", "poly_color", sel_state, channels, value)

    def _set_cursor(self, cursor_id):

        win_props = WindowProperties()

        if cursor_id == "main":
            win_props.set_cursor_filename(Filename())
        else:
            win_props.set_cursor_filename(Mgr.get("cursors")[cursor_id])

        self._window.request_properties(win_props)

    def __update_history(self):

        geom_data_objs = self._uv_data_objs[self._uv_set_id].iterkeys()
        changed_objs = [obj for obj in geom_data_objs if obj.get_uv_change()]

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        names = []
        obj_data = {}

        for geom_data_obj in changed_objs:
            model = geom_data_obj.get_toplevel_object()
            obj_data[model.get_id()] = geom_data_obj.get_data_to_store("prop_change", "uvs")
            names.append(model.get_name())

        if len(names) > 1:
            event_descr = 'Edit UVs of objects:\n'
            event_descr += "".join(['\n    "%s"' % name for name in names])
        else:
            event_descr = 'Edit UVs of "%s"' % names[0]

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(UVEditor, "uv_window")

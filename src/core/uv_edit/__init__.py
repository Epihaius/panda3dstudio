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
        cam_node = Camera("main_uv_cam", lens)
        cam_node.set_active(False)
        mask = BitMask32.bit(14)
        cam_node.set_camera_mask(mask)
        UVMgr.expose("render_mask", lambda: mask)
        cam = uv_space.attach_new_node(cam_node)
        cam.set_pos(.5, -10., .5)
        geom_root = uv_space.attach_new_node("uv_geom_root")
        BaseObject.init(uv_space, cam, cam_node, lens, geom_root)
        UVMgr.init(verbose=True)

        uv_edit_options = {
            "pick_via_poly": False,
            "pick_by_aiming": False,
            "sel_edges_by_seam": False,
            "sel_polys_by_cluster": False
        }
        copier = dict.copy
        GlobalData.set_default("uv_edit_options", uv_edit_options, copier)

        self._uv_registry = {}
        self._uv_data_objs = {}
        self._uv_set_names = {}
        self._uv_data_obj_copies = {}
        self._models = []

        UVNavigationBase.__init__(self)
        UVSelectionBase.__init__(self)
        UVTransformationBase.__init__(self)

        self._world_sel_mgr = SelectionManager(self)
        self._uv_template_saver = UVTemplateSaver()
        self._grid = Grid()
        self._transf_gizmo = UVTransformGizmo()

        # The following variables are used for aimed picking of subobjects
        self._draw_start_pos = Point3()
        normal = Vec3.forward()
        self._draw_plane = Plane(normal, cam.get_pos() + normal * 10.)

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
        poly_unsel_state_np.set_bin("background", 10)
        poly_unsel_state_np.set_transparency(TransparencyAttrib.M_alpha)
        poly_unsel_color = VBase4(.3, .3, .3, .5)
        poly_unsel_state_np.set_color(poly_unsel_color)

        # A separate LensNode projects the selection texture onto selected polygons

        poly_sel_state_np = NodePath(poly_unsel_state_np.node().make_copy())
        poly_sel_color = VBase4(1., 0., 0., 1.)
        poly_sel_state_np.set_color(poly_sel_color)
        tex_stage = TextureStage("uv_poly_selection")
        tex_stage.set_mode(TextureStage.M_add)
        poly_sel_state_np.set_tex_gen(tex_stage, RenderAttrib.M_world_position)
        self._projector_lens = projector_lens = OrthographicLens()
        projector_node = LensNode("projector", projector_lens)
        projector = cam.attach_new_node(projector_node)
        poly_sel_state_np.set_tex_projector(tex_stage, uv_space, projector)
        tex = Texture()
        tex.read(Filename(GFX_PATH + "sel_tex.png"))
        poly_sel_state_np.set_texture(tex_stage, tex)

        vert_state = vert_state_np.get_state()
        edge_state = edge_state_np.get_state()
        poly_unsel_state = poly_unsel_state_np.get_state()
        poly_sel_state = poly_sel_state_np.get_state()
        poly_sel_effects = poly_sel_state_np.get_effects()
        color = VBase4(0., .7, .5, 1.)
        poly_sel_state_np.set_color(color)
        tmp_poly_sel_state = poly_sel_state_np.get_state()
        self._poly_colors = {"unselected": poly_unsel_color, "selected": poly_sel_color}
        self._poly_states = {"unselected": poly_unsel_state, "selected": poly_sel_state,
                             "tmp_selected": tmp_poly_sel_state}
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
        UVMgr.accept("start_drawing_aux_picking_viz", self.__start_drawing_aux_picking_viz)
        UVMgr.accept("end_drawing_aux_picking_viz", self.__end_drawing_aux_picking_viz)

        Mgr.add_app_updater("uv_interface", self.__toggle_interface)

    def setup(self):

        if not self._transf_gizmo.setup():
            return False

        self._world_sel_mgr.setup()
        aux_picking_viz = Mgr.get("aux_picking_viz")
        aux_picking_viz.hide(UVMgr.get("picking_mask"))

        return True

    def __toggle_interface(self, show, display_region=None, mouse_watcher_node=None):

        base = Mgr.get("base")
        transf_gizmo = self._transf_gizmo

        if not show:

            self.__update_history()
            Mgr.update_interface_locally("uv", "uv_background", "show_on_models", False)
            Mgr.remove_task("update_cursor_uvs")
            Mgr.remove_interface("uv")
            UVMgr.get("picking_cam").set_active(False)
            self.cam_node.set_active(False)
            self.delete_selections()
            self.__destroy_uv_data()
            self._obj_lvl = "top"
            self._uv_set_id = 0
            self.__update_object_level()
            transf_gizmo.hide()
            Mgr.exit_state("uv_edit_mode")
            Mgr.update_remotely("active_obj_level")
            BaseObject.mouse_watcher = None
            self._models = []
            Mgr.remove_notification_handler("suppressed_state_enter", "uv_editor")
            Mgr.remove_notification_handler("suppressed_state_exit", "uv_editor")
            GlobalData["active_interface"] = "main"

            return

        Mgr.add_notification_handler("suppressed_state_enter", "uv_editor", self.__enter_suppressed_state)
        Mgr.add_notification_handler("suppressed_state_exit", "uv_editor", self.__exit_suppressed_state)
        self.__handle_viewport_resize(start=True)
        display_region.set_camera(self.cam)
        Mgr.add_interface("uv", "uv_edit_", mouse_watcher_node)
        GlobalData["active_interface"] = "uv"
        BaseObject.mouse_watcher = mouse_watcher_node
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
        Mgr.set_initial_state("uv_edit_mode", "uv")

        def set_obj_level(obj_lvl):

            self._obj_lvl = obj_lvl
            self.__update_object_level()

        Mgr.add_app_updater("uv_level", set_obj_level, interface_id="uv")
        Mgr.add_app_updater("active_uv_set", self.__update_uv_set, interface_id="uv")
        Mgr.add_app_updater("uv_set_copy", self.__copy_uv_set, interface_id="uv")
        Mgr.add_app_updater("uv_set_paste", self.__paste_uv_set, interface_id="uv")
        Mgr.add_app_updater("uv_name", self.__set_uv_name, interface_id="uv")
        Mgr.add_app_updater("uv_name_target_select", self.__select_uv_name_target, interface_id="uv")
        Mgr.add_app_updater("poly_color", self.__update_poly_color, interface_id="uv")
        Mgr.add_app_updater("picking_via_poly", self.__set_uv_picking_via_poly, interface_id="uv")
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize, interface_id="uv")

        self._grid.add_interface_updaters()
        self._uv_template_saver.add_interface_updaters()
        transf_gizmo.add_interface_updaters()
        transf_gizmo.update_transform_handles()
        GlobalData["active_uv_transform_type"] = ""
        Mgr.update_interface("uv", "active_transform_type", "")

        for sel_state in ("unselected", "selected"):
            r, g, b, a = self._poly_colors[sel_state]
            Mgr.update_interface_remotely("uv", "poly_color", sel_state, "rgb", (r, g, b))
            Mgr.update_interface_remotely("uv", "poly_color", sel_state, "alpha", a)

        self.__create_uv_data()
        self.create_selections()

        self._obj_lvl = "poly"
        self.__update_object_level()

        uv_set_names = self._uv_set_names
        target_names = OrderedDict()

        for model in self._models:
            geom_data_obj = model.get_geom_object().get_geom_data_object()
            uv_set_names[geom_data_obj] = geom_data_obj.get_uv_set_names()[:]
            target_names[model.get_id()] = model.get_name()

        Mgr.update_interface_remotely("uv", "uv_name_targets", target_names)
        Mgr.update_interface_remotely("uv", "uv_edit_options")

        UVMgr.do("remotely_update_background")
        UVMgr.do("remotely_update_template_props")

    def __handle_viewport_resize(self, start=False):

        w, h = GlobalData["viewport"]["size" if GlobalData["viewport"][2] == "main" else "size_aux"]
        lens = self.cam_lens
        size_h, size_v = (1., 1.) if start else lens.get_film_size()

        if h < w:
            size_v = min(size_h, size_v)
            size_h = size_v * w / h
        else:
            size_h = min(size_h, size_v)
            size_v = size_h * h / w

        lens.set_film_size(size_h, size_v)

        self._transf_gizmo.set_relative_scale(512. / min(w, h))
        self._projector_lens.set_film_size(7. / min(w, h))

    def __enter_suppressed_state(self, info=""):

        self._transf_gizmo.enable(False)
        UVMgr.get("picking_cam").set_active(False)

    def __exit_suppressed_state(self, info=""):

        UVMgr.get("picking_cam").set_active()
        self._transf_gizmo.enable()

    def get_uv_data_object(self, geom_data_obj):

        return self._uv_data_objs[self._uv_set_id][geom_data_obj]

    def __create_uv_data(self):

        models = self._models
        uv_set_id = self._uv_set_id
        self._uv_registry[uv_set_id] = uv_registry = {"vert": {}, "edge": {}, "poly": {}}
        self._uv_data_objs[uv_set_id] = uv_data_objs = {}

        for model in models:
            geom_data_obj = model.get_geom_object().get_geom_data_object()
            uv_data_objs[geom_data_obj] = UVDataObject(uv_set_id, uv_registry, geom_data_obj)

    def __destroy_uv_data(self):

        for uv_data_objs in self._uv_data_objs.values():
            for uv_data_obj in uv_data_objs.values():
                uv_data_obj.destroy()

        for geom_data_obj, uv_data_obj in self._uv_data_obj_copies.items():
            geom_data_obj.clear_copied_uvs()

        self._uv_registry.clear()
        self._uv_data_objs.clear()
        self._uv_data_obj_copies.clear()
        self._uv_set_names.clear()

    def __update_object_level(self):

        obj_lvl = self._obj_lvl
        self._world_sel_mgr.set_object_level(obj_lvl)

        if obj_lvl != "top":

            uv_data_objs = self._uv_data_objs[self._uv_set_id]

            for uv_data_obj in uv_data_objs.values():
                uv_data_obj.show_subobj_level(obj_lvl)

            self.update_selection(recreate=True)

    def __update_uv_set(self, uv_set_id):

        if uv_set_id == self._uv_set_id:
            return

        pick_via_poly = GlobalData["uv_edit_options"]["pick_via_poly"]

        if pick_via_poly:
            self.__set_uv_picking_via_poly(False)

        uv_data_objs = self._uv_data_objs[self._uv_set_id]

        for uv_data_obj in uv_data_objs.values():
            uv_data_obj.hide()

        self._uv_set_id = uv_set_id

        if uv_set_id in self._uv_data_objs:

            uv_data_objs = self._uv_data_objs[uv_set_id]

            for geom_data_obj, uv_data_obj in uv_data_objs.items():
                geom_data_obj.set_tex_seams(uv_set_id)
                uv_data_obj.show_subobj_level(self._obj_lvl)
                uv_data_obj.show()

        else:

            self.__create_uv_data()
            self.create_selections()
            self.__update_object_level()

        uv_set_names = self._uv_set_names
        uv_names = {}

        for model in self._models:
            geom_data_obj = model.get_geom_object().get_geom_data_object()
            uv_set_name = uv_set_names[geom_data_obj][uv_set_id]
            uv_names[model.get_id()] = uv_set_name

        Mgr.update_interface_remotely("uv", "target_uv_name", uv_names)

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

        if pick_via_poly:
            self.__set_uv_picking_via_poly(True)

    def __copy_uv_set(self):

        pick_via_poly = GlobalData["uv_edit_options"]["pick_via_poly"]

        if pick_via_poly:
            self.__set_uv_picking_via_poly(False)

        uv_set_id = self._uv_set_id
        uv_data_objs = self._uv_data_objs[uv_set_id]
        copies = self._uv_data_obj_copies

        for geom_data_obj, uv_data_obj in uv_data_objs.items():
            copies[geom_data_obj] = uv_data_obj.copy()
            geom_data_obj.copy_uvs(uv_set_id)

        if pick_via_poly:
            self.__set_uv_picking_via_poly(True)

    def __paste_uv_set(self):

        copies = self._uv_data_obj_copies

        if not copies:
            return

        uv_set_id = self._uv_set_id
        self._uv_registry[uv_set_id] = uv_registry = {"vert": {}, "edge": {}, "poly": {}}
        uv_data_objs = self._uv_data_objs[uv_set_id]
        self.create_selections()
        selections = {"vert": [], "edge": [], "poly": []}
        del selections[self._obj_lvl]

        for geom_data_obj, uv_data_obj in uv_data_objs.copy().items():

            uv_data_obj.destroy()
            copy = copies[geom_data_obj].copy(uv_set_id)
            copy.show()
            uv_data_objs[geom_data_obj] = copy

            for subobj_type in ("vert", "edge", "poly"):
                uv_registry[subobj_type].update(dict((s.get_picking_color_id(), s)
                                                for s in copy.get_subobjects(subobj_type).values()))

            for subobj_type in selections:
                selections[subobj_type].extend(copy.get_selection(subobj_type))

            geom_data_obj.paste_uvs(uv_set_id)

        for subobj_type in selections:
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

        if GlobalData["uv_edit_options"]["pick_via_poly"]:
            self.__set_uv_picking_via_poly(True)

    def __set_uv_name(self, model_id, uv_set_name):

        model = Mgr.get("model", model_id)
        uv_set_id = self._uv_set_id
        geom_data_obj = model.get_geom_object().get_geom_data_object()
        uv_set_names = self._uv_set_names[geom_data_obj][:]
        del uv_set_names[uv_set_id]

        if uv_set_name == "" and "" in uv_set_names:
            uv_set_name = "0"

        if uv_set_name != "":
            uv_set_name = get_unique_name(uv_set_name, uv_set_names)

        self._uv_set_names[geom_data_obj][uv_set_id] = uv_set_name
        Mgr.update_interface_remotely("uv", "uv_name", uv_set_name)

    def __select_uv_name_target(self, model_id):

        model = Mgr.get("model", model_id)
        uv_set_id = self._uv_set_id
        geom_data_obj = model.get_geom_object().get_geom_data_object()
        uv_set_name = self._uv_set_names[geom_data_obj][uv_set_id]
        Mgr.update_interface_remotely("uv", "uv_name", uv_set_name)

    def __clear_unselected_poly_state(self):

        uv_data_objs = self._uv_data_objs[self._uv_set_id]
        state = RenderState.make_empty()

        for uv_data_obj in uv_data_objs.values():
            uv_data_obj.set_poly_state("unselected", state)

    def __reset_unselected_poly_state(self):

        uv_data_objs = self._uv_data_objs[self._uv_set_id]
        state = self._poly_states["unselected"]

        for uv_data_obj in uv_data_objs.values():
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

        for uv_data_objs in self._uv_data_objs.values():
            for uv_data_obj in uv_data_objs.values():
                uv_data_obj.set_poly_state(sel_state, state)

        r, g, b, a = poly_colors[sel_state]
        value = {"rgb": (r, g, b), "alpha": a}[channels]
        Mgr.update_interface_remotely("uv", "poly_color", sel_state, channels, value)

    def __set_uv_picking_via_poly(self, via_poly=False):

        Mgr.update_interface_locally("", "picking_via_poly", via_poly)
        GlobalData["uv_edit_options"]["pick_via_poly"] = via_poly
        uv_data_objs = self._uv_data_objs[self._uv_set_id]

        if not via_poly:
            for uv_data_obj in uv_data_objs.values():
                uv_data_obj.restore_selection_backup("poly")

        obj_lvl = self._obj_lvl

        if obj_lvl not in ("vert", "edge"):
            return

        for uv_data_obj in uv_data_objs.values():
            uv_data_obj.init_subobj_picking(obj_lvl)

    def __start_drawing_aux_picking_viz(self):

        cam = self.cam
        plane = self._draw_plane
        point = Point3()

        if not self.mouse_watcher.has_mouse():
            return

        screen_pos = self.mouse_watcher.get_mouse()
        near_point = Point3()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(cam, point)
        plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))

        line = Mgr.get("aux_picking_viz")
        line_node = line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(0)
            pos_writer.set_data3f(point)

        line.reparent_to(self.uv_space)
        self._draw_start_pos = point

        Mgr.add_task(self.__draw_aux_picking_viz, "draw_aux_uv_picking_viz")

    def __draw_aux_picking_viz(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam
        near_point = Point3()
        far_point = Point3()
        self.cam_lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.uv_space.get_relative_point(cam, point)
        point = Point3()
        self._draw_plane.intersects_line(point, rel_pt(near_point), rel_pt(far_point))
        start_pos = self._draw_start_pos
        point = start_pos + (point - start_pos) * 3.

        line = Mgr.get("aux_picking_viz")
        line_node = line.node()

        for i in range(line_node.get_num_geoms()):
            vertex_data = line_node.modify_geom(i).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(1)
            pos_writer.set_data3f(point)

        return task.cont

    def __end_drawing_aux_picking_viz(self):

        Mgr.remove_task("draw_aux_uv_picking_viz")
        Mgr.get("aux_picking_viz").detach_node()

    def __update_history(self):

        uv_name_change = []
        uv_set_names = self._uv_set_names

        for model in self._models:

            geom_data_obj = model.get_geom_object().get_geom_data_object()

            if geom_data_obj.set_uv_set_names(uv_set_names[geom_data_obj]):
                uv_name_change.append(geom_data_obj)

        geom_data_objs = iter(self._uv_data_objs[self._uv_set_id].keys())
        changed_objs = [obj for obj in geom_data_objs if obj.get_uv_change()]

        if not (uv_name_change or changed_objs):
            return

        Mgr.do("update_history_time")
        obj_data = {}

        event_descr = ''

        if uv_name_change:

            names = []

            for geom_data_obj in uv_name_change:
                model = geom_data_obj.get_toplevel_object()
                obj_data[model.get_id()] = geom_data_obj.get_data_to_store("prop_change", "uv_set_names")
                names.append(model.get_name())

            if len(names) > 1:
                event_descr += 'Change UV set name(s) of objects:\n'
                event_descr += ''.join(['\n    "{}"'.format(name) for name in names])
            else:
                event_descr += 'Change UV set name(s) of "{}"'.format(names[0])

            if changed_objs:
                event_descr += '\n\n'

        if changed_objs:

            names = []

            for geom_data_obj in changed_objs:
                model = geom_data_obj.get_toplevel_object()
                data = geom_data_obj.get_data_to_store("prop_change", "uvs")
                obj_data.setdefault(model.get_id(), {}).update(data)
                names.append(model.get_name())

            if len(names) > 1:
                event_descr += 'Edit UVs of objects:\n'
                event_descr += ''.join(['\n    "{}"'.format(name) for name in names])
            else:
                event_descr += 'Edit UVs of "{}"'.format(names[0])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(UVEditor, "uv")

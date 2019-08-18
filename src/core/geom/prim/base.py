from ..base import *


class TemporaryPrimitive:

    def __init__(self, prim_type, color, pos):

        self.type = prim_type
        pivot = Mgr.get("object_root").attach_new_node("temp_prim_pivot")
        origin = pivot.attach_new_node("temp_prim_origin")
        origin.set_color(color)
        self.pivot = pivot
        self.origin = origin

        grid = Mgr.get("grid")
        active_grid_plane = grid.plane_id
        grid_origin = grid.origin

        if active_grid_plane == "xz":
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 90.))
        else:
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 0.))

        obj_id = "temp_" + prim_type + "_prim"
        Mgr.add_notification_handler("long_process_cancelled", obj_id, self.destroy, once=True)

    def __del__(self):

        logging.debug('TemporaryPrimitive garbage-collected.')

    def destroy(self, info=None):

        if info is None:
            obj_id = "temp_" + self.type + "_prim"
            Mgr.remove_notification_handler("long_process_cancelled", obj_id)
        elif info and info != "creation":
            return

        self.pivot.remove_node()
        self.pivot = None
        self.origin = None

    def define_geom_data(self):
        """
        Define the low-poly geometry of this temporary object; the vertex properties
        and how those vertices are combined into triangles and polygons.

        Override in derived class.

        """

    def create_geometry(self, geom_data):

        vertex_format_basic = Mgr.get("vertex_format_basic")
        vertex_format_full = Mgr.get("vertex_format_full")
        vertex_data_poly = GeomVertexData("poly_data", vertex_format_full, Geom.UH_dynamic)

        pos_writer = GeomVertexWriter(vertex_data_poly, "vertex")
        normal_writer = GeomVertexWriter(vertex_data_poly, "normal")

        polys = []
        vert_count = 0
        tri_vert_count = 0

        for poly_data in geom_data:

            verts_by_pos = {}
            edge_vert_ids = []
            tri_vert_ids = []

            for tri_data in poly_data:

                tri_vert_count += 3
                vert_ids = []

                for vert_data in tri_data:

                    pos = vert_data["pos"]

                    if pos in verts_by_pos:
                        vert_id = verts_by_pos[pos]
                    else:
                        pos_writer.add_data3(*pos)
                        normal_writer.add_data3(vert_data["normal"])
                        vert_id = vert_count
                        verts_by_pos[pos] = vert_count
                        vert_count += 1

                    vert_ids.append(vert_id)

                for i, j in ((0, 1), (1, 2), (0, 2)):

                    v_ids = sorted([vert_ids[i], vert_ids[j]])

                    if v_ids in edge_vert_ids:
                        edge_vert_ids.remove(v_ids)
                    else:
                        edge_vert_ids.append(v_ids)

                tri_vert_ids.append(tuple(vert_ids))

            polygon = {"edge_vert_ids": edge_vert_ids, "tri_vert_ids": tri_vert_ids}
            polys.append(polygon)

        origin = self.origin

        picking_mask = Mgr.get("picking_mask")

        render_mode = GD["render_mode"]
        create_wire = "wire" in render_mode
        create_shaded = "shaded" in render_mode

        if create_wire:
            lines_prim = GeomLines(Geom.UH_static)
            lines_prim.reserve_num_vertices(vert_count)

        if create_shaded:
            tris_prim = GeomTriangles(Geom.UH_static)
            tris_prim.reserve_num_vertices(tri_vert_count)

        for poly in polys:

            if create_wire:
                for edge_vert_ids in poly["edge_vert_ids"]:
                    lines_prim.add_vertices(*edge_vert_ids)

            if create_shaded:
                for tri_vert_ids in poly["tri_vert_ids"]:
                    tris_prim.add_vertices(*tri_vert_ids)

        if create_wire:

            pos_array = vertex_data_poly.get_array(0)
            vertex_data_edge = GeomVertexData("edge_data", vertex_format_basic, Geom.UH_dynamic)
            vertex_data_edge.reserve_num_rows(vert_count)
            vertex_data_edge.set_num_rows(vert_count)
            vertex_data_edge.set_array(0, pos_array)

            state_np = NodePath("state")
            state_np.set_light_off()
            state_np.set_texture_off()
            state_np.set_material_off()
            state_np.set_shader_off()
            state_np.set_transparency(TransparencyAttrib.M_none)
            state_np.set_attrib(DepthTestAttrib.make(RenderAttrib.M_less_equal))
            state_np.set_bin("fixed", 1)
            wire_state = state_np.get_state()

            lines_geom = Geom(vertex_data_edge)
            lines_geom.add_primitive(lines_prim)
            geom_node = GeomNode("wire_geom")
            geom_node.add_geom(lines_geom)
            wire_geom = origin.attach_new_node(geom_node)
            wire_geom.set_state(wire_state)
            wire_geom.hide(picking_mask)

        if create_shaded:

            tris_geom = Geom(vertex_data_poly)
            tris_geom.add_primitive(tris_prim)
            geom_node = GeomNode("shaded_geom")
            geom_node.add_geom(tris_geom)
            shaded_geom = origin.attach_new_node(geom_node)
            shaded_geom.hide(picking_mask)

            if GD["two_sided"]:
                origin.set_two_sided(True)

    def finalize(self):

        def create_primitive():

            pos = self.pivot.get_pos(Mgr.get("grid").origin)
            size = self.get_size()

            for step in Mgr.do(f"create_{self.type}", pos, size):
                yield

            self.destroy()

        return create_primitive()

    def is_valid(self):

        return False


class Primitive(GeomDataOwner):

    def __getstate__(self):

        state = GeomDataOwner.__getstate__(self)

        state["_type"] = state.pop("type")

        return state

    def __setstate__(self, state):

        GeomDataOwner.__setstate__(self, state)

        state["type"] = state.pop("_type")

    def __init__(self, prim_type, model, type_prop_ids):

        GeomDataOwner.__init__(self, [], type_prop_ids, model)

        self.type = prim_type
        # the following "initial coordinates" correspond to the vertex positions
        # at the time the geometry is created or recreated; it is kept around to
        # facilitate reshaping the primitive (when "baking" the new size into
        # the vertices or computing the new vertex positions)
        self._initial_coords = {}

    def define_geom_data(self):
        """
        Define the geometry of the primitive; the vertex properties and how those
        vertices are combined into triangles and polygons.

        Override in derived class.

        """

        pass

    def update(self, data):
        """
        Update the primitive with the given data.

        Override in derived class.

        """

        pass

    def create(self, poly_count, force_gradual=False):

        progress_steps = (poly_count // 20) * 4
        gradual = True if force_gradual else progress_steps > 80

        if gradual and not force_gradual:
            GD["progress_steps"] = progress_steps

        geom_data_obj = Mgr.do("create_geom_data", self)
        self.geom_data_obj = geom_data_obj
        geom_data = self.define_geom_data()

        for data in geom_data_obj.process_geom_data(geom_data, gradual=gradual):
            if gradual:
                yield

        self.update(data)
        geom_data_obj.init_normal_sharing()
        geom_data_obj.update_smoothing()

        for step in geom_data_obj.create_geometry(self.type, gradual=gradual):
            if gradual:
                yield

        geom_data_obj.update_vertex_normals()

    def cancel_geometry_recreation(self, info):

        if info == "creation":

            geom_data_backup = self.get_geom_data_backup()

            if not geom_data_backup:
                return

            self.geom_data_obj.cancel_creation()
            model = self.model
            geom_data_backup.origin.reparent_to(model.origin)
            self.geom_data_obj = geom_data_backup
            self.set_geom_data_backup(None)
            model.bbox.update(*self.origin.get_tight_bounds())

    def recreate_geometry(self, poly_count):

        obj_id = self.toplevel_obj.id
        id_str = str(obj_id) + "_geom_data"
        handler = self.cancel_geometry_recreation
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", id_str)
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix=id_str, sort=100)

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        geom_data_obj = self.geom_data_obj
        geom_data_obj.unregister()
        Mgr.do("update_picking_col_id_ranges")
        Mgr.update_locally("screenshot_removal")

        def task():

            progress_steps = (poly_count // 20) * 4
            gradual = progress_steps > 80

            if gradual:
                Mgr.update_remotely("screenshot", "create")
                GD["progress_steps"] = progress_steps

            geom_data_obj = self.geom_data_obj
            self.set_geom_data_backup(geom_data_obj)
            self.get_geom_data_backup().origin.detach_node()
            geom_data_obj = Mgr.do("create_geom_data", self)
            self.geom_data_obj = geom_data_obj
            geom_data = self.define_geom_data()

            for data in geom_data_obj.process_geom_data(geom_data, gradual=gradual):
                if gradual:
                    yield True

            self.update(data)
            geom_data_obj.init_normal_sharing()
            geom_data_obj.update_smoothing()

            for step in geom_data_obj.create_geometry(self.type, gradual=gradual):
                if gradual:
                    yield True

            if self.has_flipped_normals():
                geom_data_obj.flip_normals(delay=False)

            geom_data_obj.update_vertex_normals(update_tangent_space=False)

            self.update_initial_coords()
            self.finalize()

            geom_data_obj.register(restore=False)

            if self.model.has_tangent_space():
                geom_data_obj.init_tangent_space()

            Mgr.notify("pickable_geom_altered", self.toplevel_obj)

            yield False

        task_id = "set_geom_data"
        descr = "Updating geometry..."
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id, gradual=True,
                         process_id="creation", descr=descr, cancellable=True)

        self.model.update_group_bbox()

    def is_valid(self):

        return False

    def update_initial_coords(self):

        self._initial_coords = self.geom_data_obj.vertex_coords

    def reset_initial_coords(self):

        self.geom_data_obj.vertex_coords = self._initial_coords

    def restore_initial_coords(self, coords):

        self._initial_coords = coords

    def get_initial_coords(self):

        return self._initial_coords

    def get_initial_pos(self, vertex_id):

        return self._initial_coords[vertex_id]

    def finalize(self):

        self.geom_data_obj.finalize_geometry()

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

        if prop_id == "geom_data":
            val.restore_data(["self"], restore_type, old_time_id, new_time_id)


class PrimitiveManager(CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self, prim_type, custom_creation=False):

        CreationPhaseManager.__init__(self, prim_type, has_color=True)
        ObjPropDefaultsManager.__init__(self, prim_type)

        Mgr.accept(f"create_{prim_type}", self.__create)

        if custom_creation:
            Mgr.accept(f"create_custom_{prim_type}", self.create_custom_primitive)

    def setup(self, creation_phases, status_text):

        phase_starter, phase_handler = creation_phases.pop(0)
        creation_starter = self.__get_prim_creation_starter(phase_starter)
        creation_phases.insert(0, (creation_starter, phase_handler))

        return CreationPhaseManager.setup(self, creation_phases, status_text)

    def __get_prim_creation_starter(self, main_creation_func):

        def start_primitive_creation():

            next_color = self.get_next_object_color()
            tmp_prim = self.create_temp_primitive(next_color, self.get_origin_pos())
            self.init_object(tmp_prim)

            main_creation_func()

        return start_primitive_creation

    def get_temp_primitive(self):

        return self.get_object()

    def create_temp_primitive(self, color, pos):
        """ Override in derived class """

        return None

    def create_primitive(self, model):
        """ Override in derived class """

        yield None

    def init_primitive_size(self, prim, size=None):
        """ Override in derived class """

        pass

    def __create(self, origin_pos, size=None):

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        model_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        model = Mgr.do("create_model", model_id, name, origin_pos)
        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = None
        gradual = True

        for result in self.create_primitive(model):
            if result:
                prim, gradual = result
            if gradual:
                yield True

        self.init_primitive_size(prim, size)
        geom_data_obj = prim.geom_data_obj
        geom_data_obj.finalize_geometry()
        self.set_next_object_color()
        Mgr.exit_state("processing")
        model.register(restore=False)
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(model)

        yield False

    def create_custom_primitive(self, *args, **kwargs):
        """ Override in derived class """

        yield None

from ...base import *
from ..locked_geom import create_aux_geom, LockedGeomBase, LockedGeomManagerBase
import array


def _create_geom(geom_data, temp=False, initial_coords=None):

    vert_count = sum(len(poly_data["verts"]) for poly_data in geom_data)
    prim = GeomTriangles(Geom.UH_static)
    prim_size = sum(len(poly_data["tris"]) * 3 for poly_data in geom_data)
    int_format = "H"

    if prim_size >= 2 ** 16:
        prim.set_index_type(Geom.NT_uint32)
        int_format = "I"

    prim.reserve_num_vertices(prim_size)
    prim_array = prim.modify_vertices()
    prim_array.unclean_set_num_rows(prim_size)
    memview = memoryview(prim_array).cast("B").cast(int_format)
    data_array = array.array(int_format, [])
    vert_ids = []

    for poly_data in geom_data:
        vert_ids.extend(id(v) for v in poly_data["verts"])
        data_array.extend(vert_ids.index(id(v)) for tri in poly_data["tris"] for v in tri)

    memview[:] = data_array

    vertex_format = Mgr.get("vertex_format_full")
    vertex_data = GeomVertexData("vert_data", vertex_format, Geom.UH_static)
    vertex_data.reserve_num_rows(vert_count)
    vertex_data.set_num_rows(vert_count)
    pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
    normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
    uv_view = memoryview(vertex_data.modify_array(4)).cast("B").cast("f")
    coords = array.array("f", [x for p in geom_data for v in p["verts"] for x in v["pos"]])

    if initial_coords is not None:
        coords2 = array.array("f", [x for p in geom_data for t in p["tris"]
            for v in t for x in v["pos"]])
        initial_coords[:] = coords, coords2

    pos_view[:] = coords
    normal_view[:] = array.array("f", [x for p in geom_data for v in p["verts"] for x in v["normal"]])

    if not temp:
        uv_view[:] = array.array("f", [x for p in geom_data for v in p["verts"] for x in v["uvs"][0]])

    geom = Geom(vertex_data)
    geom.add_primitive(prim)
    geom_node = GeomNode("")
    geom_node.add_geom(geom)

    return NodePath(geom_node)


class TemporaryPrimitive:

    def __init__(self, prim_type, color, pos):

        self.type = prim_type
        pivot = Mgr.get("object_root").attach_new_node("temp_prim_pivot")
        origin = pivot.attach_new_node("temp_prim_origin")
        origin.set_color(color)
        origin.node().set_bounds(OmniBoundingVolume())
        origin.node().set_final(True)
        self.pivot = pivot
        self.origin = origin

        grid = Mgr.get("grid")
        active_grid_plane = grid.plane_id
        grid_origin = grid.origin
        pos = grid_origin.get_relative_point(GD.world, pos)

        if active_grid_plane == "xz":
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 90.))
        else:
            pivot.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 0.))

    def __del__(self):

        Notifiers.obj.debug('TemporaryPrimitive garbage-collected.')

    def destroy(self, info=None):

        self.pivot.detach_node()
        self.pivot = None
        self.origin = None

    def define_geom_data(self):
        """
        Define the low-poly geometry of this temporary object; the vertex properties
        and how those vertices are combined into triangles and polygons.

        Override in derived class.

        """

    def create_geometry(self, geom_data):

        origin = self.origin
        picking_mask = Mgr.get("picking_mask")

        render_mode = GD["render_mode"]
        create_shaded = "shaded" in render_mode
        create_wire = "wire" in render_mode

        if create_shaded:
            shaded_geom = _create_geom(geom_data, temp=True)
            shaded_geom.name = "shaded"
            shaded_geom.reparent_to(origin)
            shaded_geom.hide(picking_mask)

        if create_wire:
            wire_geom = create_aux_geom(geom_data)
            wire_geom.name = "wire"
            wire_geom.reparent_to(origin)
            wire_geom.hide(picking_mask)
            # set wireframe shader
            shader = shaders.Shaders.locked_wireframe
            wire_geom.set_shader(shader)
            wire_geom.set_shader_input("inverted", False)
            wire_geom.set_shader_input("two_sided", GD["two_sided"])
            wire_geom.set_shader_input("snap_type_id", 1.)

        if GD["two_sided"]:
            origin.set_two_sided(True)

    def finalize(self):

        pos = self.pivot.get_pos(Mgr.get("grid").origin)
        size = self.get_size()
        Mgr.do(f"create_{self.type}", pos, size)
        self.destroy()

    def is_valid(self):
        """
        Override in derived class.

        """

        return False


class Primitive(LockedGeomBase):

    def __getstate__(self):

        state = LockedGeomBase.__getstate__(self)
        state["geom_root"] = None
        state["geom"] = None
        state["aux_geom"] = None

        return state

    def __init__(self, prim_type, model, type_prop_ids, picking_col_id, geom_data):

        self.type = prim_type
        self._prop_ids = []
        self._type_prop_ids = type_prop_ids + ["inverted_geom"]
        # the following "initial coordinates" correspond to the vertex positions
        # at the time the geometry is created or recreated; it is kept around to
        # facilitate reshaping the primitive
        self.initial_coords = []
        geom = _create_geom(geom_data, False, self.initial_coords)
        LockedGeomBase.__init__(self, model, geom, geom_data, picking_col_id)
        self.update_render_mode(False)

    def recreate(self, geom_data):

        self.geom_data = geom_data
        self.geom = _create_geom(geom_data, False, self.initial_coords)
        self.aux_geom = create_aux_geom(geom_data)
        self.setup_geoms()

        Mgr.notify("pickable_geom_altered", self.toplevel_obj)

    def update_poly_centers(self):

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        pos_array = vertex_data.get_array(0)
        pos_view = memoryview(pos_array).cast("B").cast("f")
        snap_values = array.array("f", [])
        i = 0

        for poly in self.geom_data:
            s = len(poly["verts"])
            pos = tuple(sum((Point3(*p) for p in (pos_view[i+j*3:i+(j+1)*3]
                for j in range(s))), Point3()) / s)
            i += s * 3
            snap_values.extend(pos * len(poly["tris"]) * 3)

        vertex_data = self.aux_geom.node().modify_geom(0).modify_vertex_data()
        snap_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
        snap_view[:] = snap_values

    def is_valid(self):
        """
        Override in derived class.

        """

        return False

    def reset_vertex_colors(self):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vertex_data_copy = vertex_data.set_color((1., 1., 1., 1.))
        array = vertex_data_copy.get_array(1)
        vertex_data.set_array(1, GeomVertexArrayData(array))

    def get_uv_set_names(self):

        return ["", "1", "2", "3", "4", "5", "6", "7"]

    def __define_indices(self):

        class MergedVertex:

            __slots__ = ("_ids",)

            def __init__(self, vert_ids):

                self._ids = vert_ids

            def __getitem__(self, index):

                return self._ids[index]

        class MergedUV:

            __slots__ = ("merged_vert", "uv")

            def __init__(self, merged_vert, u, v):

                self.merged_vert = merged_vert
                self.uv = [u, v]

        verts = {}
        verts_by_pos_ind = {}
        merged_verts = {}
        merged_uvs = {}
        processed_mvs = []
        processed_muvs = []

        for poly_data in self.geom_data:

            for vert_data in poly_data["verts"]:
                vert_id = id(vert_data)
                verts[vert_id] = vert_data
                verts_by_pos_ind.setdefault(vert_data["pos_ind"], []).append(vert_id)

        for vert_ids in verts_by_pos_ind.values():
            merged_vertex = MergedVertex(vert_ids)
            merged_verts.update({v_id: merged_vertex for v_id in vert_ids})

        del verts_by_pos_ind

        for merged_vert in set(merged_verts.values()):

            verts_by_uv = {}

            for vert_id in merged_vert:

                vert = verts[vert_id]
                uv = vert["uvs"].get(0, (0., 0.))

                if uv in verts_by_uv:
                    verts_by_uv[uv].append(vert_id)
                else:
                    verts_by_uv[uv] = [vert_id]

            for (u, v), vert_ids in verts_by_uv.items():
                merged_uv = MergedUV(merged_vert, u, v)
                merged_uvs.update({v_id: merged_uv for v_id in vert_ids})

        for poly_data in self.geom_data:

            for vert_data in poly_data["verts"]:

                vert_id = id(vert_data)
                merged_vertex = merged_verts[vert_id]
                merged_uv = merged_uvs[vert_id]

                if merged_vertex in processed_mvs:
                    vert_data["pos_ind"] = processed_mvs.index(merged_vertex)
                else:
                    vert_data["pos_ind"] = len(processed_mvs)
                    processed_mvs.append(merged_vertex)

                if merged_uv in processed_muvs:
                    vert_data["uv_ind"] = processed_muvs.index(merged_uv)
                else:
                    vert_data["uv_ind"] = len(processed_muvs)
                    processed_muvs.append(merged_uv)

    def update_vertex_positions(self):
        """
        Replace the initial vertex positions with their current coordinates.

        """

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        pos_array = vertex_data.get_array(0)
        pos_view = memoryview(pos_array).cast("B").cast("f")
        i = 0

        for p in self.geom_data:
            for v in p["verts"]:
                v["pos"][:] = pos_view[i:i+3]
                i += 3

    def get_subdivision_data(self):

        self.update_vertex_positions()
        self.__define_indices()

        return LockedGeomBase.get_subdivision_data(self)

    def unlock_geometry(self, unlocked_geom, update_normal_data=False):

        self.update_vertex_positions()
        LockedGeomBase.unlock_geometry(self, unlocked_geom, update_normal_data)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "inverted_geom":
            return self.has_inverted_geometry()

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "inverted_geom":
            Mgr.update_remotely("selected_obj_prop", "locked_geom", prop_id, value)
            return self.invert_geometry(value)


class PrimitiveManager(CreationPhaseManager, ObjPropDefaultsManager, LockedGeomManagerBase):

    def __init__(self, prim_type, custom_creation=False):

        CreationPhaseManager.__init__(self, prim_type, has_color=True)
        ObjPropDefaultsManager.__init__(self, prim_type)
        LockedGeomManagerBase.__init__(self)

        Mgr.accept(f"create_{prim_type}", self.__create)

        if custom_creation:
            Mgr.accept(f"create_custom_{prim_type}", self.create_custom_primitive)

    def setup(self, creation_phases, status_text):

        phase_data = creation_phases.pop(0)

        if len(phase_data) == 3:
            phase_starter, phase_handler, phase_finisher = phase_data
        else:
            phase_starter, phase_handler = phase_data
            phase_finisher = lambda: None

        creation_starter = self.__get_prim_creation_starter(phase_starter)
        creation_phases.insert(0, (creation_starter, phase_handler, phase_finisher))

        return CreationPhaseManager.setup(self, creation_phases, status_text)

    def __get_prim_creation_starter(self, main_creation_func):

        def start_primitive_creation():

            if not self.get_object():
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

    def create_primitive(self, model, picking_col_id, geom_data):
        """ Override in derived class """

        return None

    def init_primitive_size(self, prim, size=None):
        """ Override in derived class """

        pass

    def define_geom_data(self):
        """
        Define the geometry data; the vertex properties and how those vertices
        are combined into triangles and polygons.

        Override in derived class.

        """

        return None

    def __create(self, origin_pos, size=None):

        model_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        model = Mgr.do("create_model", model_id, name, origin_pos)
        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        picking_col_id = self.get_next_picking_color_id()
        geom_data = self.define_geom_data()
        prim = self.create_primitive(model, picking_col_id, geom_data)
        self.init_primitive_size(prim, size)
        self.set_next_object_color()
        model.register(restore=False)

        if self.get_object():
            model.pivot.set_hpr(self.get_object().pivot.get_hpr())

        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(model)

    def create_custom_primitive(self, *args, **kwargs):
        """ Override in derived class """

        return None

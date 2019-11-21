from ..base import *


class Edge:

    __slots__ = ("type", "id", "picking_color_id", "_vert_ids",
                 "polygon_id", "geom_data_obj", "creation_time")

    def __getstate__(self):

        state = {
            "_id": self.id,
            "_picking_col_id": self.picking_color_id,
            "_creation_time": self.creation_time,
            "_vert_ids": self._vert_ids,
            "_poly_id": self.polygon_id
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "edge"
        self.geom_data_obj = None
        self.id = state["_id"]
        self.picking_color_id = state["_picking_col_id"]
        self.creation_time = state["_creation_time"]
        self._vert_ids = state["_vert_ids"]
        self.polygon_id = state["_poly_id"]

    def __init__(self, edge_id, picking_col_id, geom_data_obj, vert_ids):

        self.type = "edge"
        self.id = edge_id
        self.picking_color_id = picking_col_id
        self.geom_data_obj = geom_data_obj
        self.creation_time = None
        self.polygon_id = None
        self._vert_ids = vert_ids

    def __getitem__(self, index):

        try:
            return self._vert_ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    @property
    def merged_subobj(self):

        return self.geom_data_obj.get_merged_edge(self.id)

    @property
    def merged_edge(self):

        return self.geom_data_obj.get_merged_edge(self.id)

    @property
    def vertices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    @property
    def start_row_index(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return verts[self._vert_ids[0]].row_index

    @property
    def row_indices(self):

        verts = self.geom_data_obj.get_subobjects("vert")
        count = len(verts)
        r1, r2 = (verts[vert_id].row_index for vert_id in self._vert_ids)

        return [r1, r2 + count]

    def get_center_pos(self, ref_node=None):

        verts = self.geom_data_obj.get_subobjects("vert")

        return sum([verts[v_id].get_pos(ref_node) for v_id in self._vert_ids], Point3()) * .5

    def get_point_at_screen_pos(self, screen_pos):

        verts = self.geom_data_obj.get_subobjects("vert")
        v_ids = self._vert_ids
        world = GD.world
        cam = GD.cam()
        point1 = verts[v_ids[0]].get_pos(world)
        point2 = verts[v_ids[1]].get_pos(world)
        edge_vec = V3D(point1 - point2)
        cam_vec = V3D(world.get_relative_vector(cam, Vec3.forward()))
        cross_vec = edge_vec ** cam_vec

        if not cross_vec.normalize():
            return point1

        point3 = point1 + cross_vec
        plane = Plane(point1, point2, point3)

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def get_direction_vector(self, origin_vertex_id):

        verts = self.geom_data_obj.get_subobjects("vert")
        v1_id, v2_id = self._vert_ids
        v1 = verts[v1_id]
        v2 = verts[v2_id]

        if origin_vertex_id == v1_id:
            return (v2.get_pos() - v1.get_pos()).normalized()
        else:
            return (v1.get_pos() - v2.get_pos()).normalized()


class MergedEdge:

    __slots__ = ("type", "full_type", "_ids", "geom_data_obj")

    def __getstate__(self):

        state = {
            "_ids": self._ids
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "edge"
        self.full_type = "merged_edge"
        self.geom_data_obj = None
        self._ids = state["_ids"]

    def __init__(self, geom_data_obj, edge_id=None):

        self.type = "edge"
        self.full_type = "merged_edge"
        self.geom_data_obj = geom_data_obj
        self._ids = [] if edge_id is None else [edge_id]

    def __getitem__(self, index):

        try:
            return self._ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):

        return len(self._ids)

    def append(self, edge_id):

        self._ids.append(edge_id)

    def extend(self, edge_ids):

        self._ids.extend(edge_ids)

    def remove(self, edge_id):

        self._ids.remove(edge_id)

    @property
    def id(self):

        edge = self.geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.id if edge else None

    @property
    def picking_color_id(self):

        edge = self.geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.picking_color_id if edge else None

    @property
    def picking_color_ids(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[e_id].picking_color_id for e_id in self._ids]

    @property
    def polygon_ids(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[e_id].polygon_id for e_id in self._ids]

    @property
    def connected_verts(self):

        geom_data_obj = self.geom_data_obj
        merged_verts = geom_data_obj.merged_verts
        verts = geom_data_obj.get_subobjects("vert")
        edges = geom_data_obj.get_subobjects("edge")

        return set(verts[v_id] for mv_id in edges[self._ids[0]] for v_id in merged_verts[mv_id])

    @property
    def connected_edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")
        edge_ids = set()

        for vert in self.connected_verts:
            edge_ids.update(vert.edge_ids)

        return set(edges[e_id] for e_id in edge_ids)

    @property
    def connected_polys(self):

        polys = self.geom_data_obj.get_subobjects("poly")

        return set(polys[v.polygon_id] for v in self.connected_verts)

    def get_connected_subobjs(self, subobj_type):

        if subobj_type == "vert":
            return self.connected_verts
        elif subobj_type == "edge":
            return self.connected_edges
        elif subobj_type == "poly":
            return self.connected_polys

    @property
    def special_selection(self):

        edges = [self]

        if GD["subobj_edit_options"]["sel_edges_by_border"] and len(self._ids) == 1:
            edges = self.geom_data_obj.get_containing_surface_border(self)

        return edges

    @property
    def start_row_indices(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[e_id].start_row_index for e_id in self._ids]

    @property
    def row_indices(self):

        edges = self.geom_data_obj.get_subobjects("edge")
        row_indices = []

        for e_id in self._ids:
            row_indices.extend(edges[e_id].row_indices)

        return row_indices

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_center_pos(self, ref_node=None):

        edge = self.geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_center_pos(ref_node)

    def get_point_at_screen_pos(self, screen_pos):

        edge = self.geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_point_at_screen_pos(screen_pos)

    def get_direction_vector(self, origin_vertex_id):

        merged_verts = self.geom_data_obj.merged_verts
        edge = self.geom_data_obj.get_subobject("edge", self._ids[0])
        v1_id, v2_id = edge
        mv1 = merged_verts[v1_id]
        mv2 = merged_verts[v2_id]

        if origin_vertex_id in mv1:
            return (mv2.get_pos() - mv1.get_pos()).normalized()
        else:
            return (mv1.get_pos() - mv2.get_pos()).normalized()

    def is_facing_camera(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        for edge_id in self._ids:

            poly = self.geom_data_obj.get_subobject("poly", edges[edge_id].polygon_id)

            if poly.is_facing_camera():
                return True

        return False


class EdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "edge", self.__create_edge, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("edge")
        Mgr.accept("create_merged_edge", self.__create_merged_edge)

    def __create_edge(self, geom_data_obj, verts):

        edge_id = self.get_next_id()
        picking_col_id = self.get_next_picking_color_id()
        edge = Edge(edge_id, picking_col_id, geom_data_obj, verts)

        return edge

    def __create_merged_edge(self, geom_data_obj, edge_id=None):

        edge = MergedEdge(geom_data_obj, edge_id)

        return edge


MainObjects.add_class(EdgeManager)

from ..base import *


class Edge(BaseObject):

    def __getstate__(self):

        # When pickling an Edge, it should not have a GeomDataObject, since this
        # will be pickled separately.

        state = self.__dict__.copy()
        state["_geom_data_obj"] = None

        return state

    def __init__(self, edge_id, picking_col_id, geom_data_obj, vert_ids):

        self._type = "edge"
        self._id = edge_id
        self._picking_col_id = picking_col_id
        self._geom_data_obj = geom_data_obj
        self._creation_time = None
        self._poly_id = None
        self._vert_ids = vert_ids

    def __getitem__(self, index):

        try:
            return self._vert_ids[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def get_type(self):

        return self._type

    def get_id(self):

        return self._id

    def get_picking_color_id(self):

        return self._picking_col_id

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def set_creation_time(self, time_id):

        self._creation_time = time_id

    def get_creation_time(self):

        return self._creation_time

    def get_toplevel_object(self, get_group=False):

        return self._geom_data_obj.get_toplevel_object(get_group)

    def get_merged_object(self):

        return self._geom_data_obj.get_merged_edge(self._id)

    def get_merged_edge(self):

        return self._geom_data_obj.get_merged_edge(self._id)

    def set_polygon_id(self, polygon_id):

        self._poly_id = polygon_id

    def get_polygon_id(self):

        return self._poly_id

    def get_vertices(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    def get_start_row_index(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return verts[self._vert_ids[0]].get_row_index()

    def get_row_indices(self):

        verts = self._geom_data_obj.get_subobjects("vert")
        count = len(verts)
        r1, r2 = (verts[vert_id].get_row_index() for vert_id in self._vert_ids)

        return [r1, r2 + count]

    def get_center_pos(self, ref_node=None):

        verts = self._geom_data_obj.get_subobjects("vert")

        return sum([verts[v_id].get_pos(ref_node) for v_id in self._vert_ids], Point3()) * .5

    def get_point_at_screen_pos(self, screen_pos):

        verts = self._geom_data_obj.get_subobjects("vert")
        v_ids = self._vert_ids
        world = self.world
        cam = self.cam()
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
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point


class MergedEdge:

    def __getstate__(self):

        # When pickling a MergedEdge, it should not have a GeomDataObject, since
        # this will be pickled separately.

        state = self.__dict__.copy()
        state["_geom_data_obj"] = None

        return state

    def __init__(self, geom_data_obj, edge_id=None):

        self._type = "edge"
        self._full_type = "merged_edge"
        self._geom_data_obj = geom_data_obj
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

    def get_type(self):

        return self._type

    def get_full_type(self):

        return self._full_type

    def get_id(self):

        edge = self._geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_id() if edge else None

    def get_picking_color_id(self):

        edge = self._geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_picking_color_id() if edge else None

    def get_picking_color_ids(self):

        edges = self._geom_data_obj.get_subobjects("edge")

        return [edges[e_id].get_picking_color_id() for e_id in self._ids]

    def get_polygon_ids(self):

        edges = self._geom_data_obj.get_subobjects("edge")

        return [edges[e_id].get_polygon_id() for e_id in self._ids]

    def get_connected_verts(self):

        geom_data_obj = self._geom_data_obj
        merged_verts = geom_data_obj.get_merged_vertices()
        verts = geom_data_obj.get_subobjects("vert")
        edges = geom_data_obj.get_subobjects("edge")

        return set(verts[v_id] for mv_id in edges[self._ids[0]] for v_id in merged_verts[mv_id])

    def get_connected_edges(self):

        edges = self._geom_data_obj.get_subobjects("edge")
        edge_ids = set()

        for vert in self.get_connected_verts():
            edge_ids.update(vert.get_edge_ids())

        return set(edges[e_id] for e_id in edge_ids)

    def get_connected_polys(self):

        polys = self._geom_data_obj.get_subobjects("poly")

        return set(polys[v.get_polygon_id()] for v in self.get_connected_verts())

    def get_connected_subobjs(self, subobj_type):

        if subobj_type == "vert":
            return self.get_connected_verts()
        elif subobj_type == "edge":
            return self.get_connected_edges()
        elif subobj_type == "poly":
            return self.get_connected_polys()

    def get_special_selection(self):

        edges = [self]

        if GlobalData["subobj_edit_options"]["sel_edges_by_border"] and len(self._ids) == 1:
            edges = self._geom_data_obj.get_border_edges(self)

        return edges

    def get_start_row_indices(self):

        edges = self._geom_data_obj.get_subobjects("edge")

        return [edges[e_id].get_start_row_index() for e_id in self._ids]

    def get_row_indices(self):

        edges = self._geom_data_obj.get_subobjects("edge")
        row_indices = []

        for e_id in self._ids:
            row_indices.extend(edges[e_id].get_row_indices())

        return row_indices

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def get_toplevel_object(self, get_group=False):

        return self._geom_data_obj.get_toplevel_object(get_group)

    def set_previous_property_time(self, prop_id, time_id):

        edges = self._geom_data_obj.get_subobjects("edge")

        for edge_id in self._ids:
            edges[edge_id].set_previous_property_time(prop_id, time_id)

    def get_previous_property_time(self, prop_id):

        edge = self._geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_previous_property_time(prop_id)

    def get_center_pos(self, ref_node=None):

        edge = self._geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_center_pos(ref_node)

    def get_point_at_screen_pos(self, screen_pos):

        edge = self._geom_data_obj.get_subobject("edge", self._ids[0])

        return edge.get_point_at_screen_pos(screen_pos)

    def is_facing_camera(self):

        edges = self._geom_data_obj.get_subobjects("edge")

        for edge_id in self._ids:

            poly = self._geom_data_obj.get_subobject("poly", edges[edge_id].get_polygon_id())

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

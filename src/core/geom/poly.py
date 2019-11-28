from ..base import *


class Polygon:

    __slots__ = ("type", "id", "picking_color_id", "vertex_ids", "edge_ids", "geom_data_obj",
                 "creation_time", "_prev_prop_time", "_tri_data", "_center_pos", "_normal")

    def __getstate__(self):

        state = {
            "_id": self.id,
            "_picking_col_id": self.picking_color_id,
            "_creation_time": self.creation_time,
            "_prev_prop_time": self._prev_prop_time,
            "_tri_data": self._tri_data,
            "_vert_ids": self.vertex_ids,
            "_edge_ids": self.edge_ids,
            "_center_pos": self._center_pos,
            "_normal": self._normal
            # leave out the GeomDataObject, as it is pickled separately
        }

        return state

    def __setstate__(self, state):

        self.type = "poly"
        self.geom_data_obj = None
        self.id = state["_id"]
        self.picking_color_id = state["_picking_col_id"]
        self.creation_time = state["_creation_time"]
        self._prev_prop_time = state["_prev_prop_time"]
        self._tri_data = state["_tri_data"]
        self.vertex_ids = state["_vert_ids"]
        self.edge_ids = state["_edge_ids"]
        self._center_pos = state["_center_pos"]
        self._normal = state["_normal"]

    def __init__(self, poly_id, picking_col_id, geom_data_obj, triangle_data, edges, verts):

        self.type = "poly"
        self.id = poly_id
        self.picking_color_id = picking_col_id
        self.geom_data_obj = geom_data_obj
        self.creation_time = None
        self._prev_prop_time = {"tri_data": None}
        self._tri_data = triangle_data  # sequence of 3-tuples of vertex IDs
        self.vertex_ids = [vert.id for vert in verts]
        self.edge_ids = [edge.id for edge in edges]
        # the IDs of the vertices and edges belonging to this polygon should be listed
        # in an order that can be used to define the winding of a new triangulation,
        # consistent with the winding direction of the existing triangles.

        for vert in verts:
            vert.polygon_id = poly_id

        for edge in edges:
            edge.polygon_id = poly_id

        self._center_pos = Point3()
        self._normal = Vec3()

    def __getitem__(self, index):

        try:
            return self._tri_data[index]
        except IndexError:
            raise IndexError("Index out of range.")
        except TypeError:
            raise TypeError("Index must be an integer value.")

    def __len__(self):
        """
        Return the size of the polygon as the number of data rows of the associated
        GeomTriangles object.
        Note that this is NOT the same as the number of vertices belonging to this
        polygon! Use Polygon.vertex_count for this.

        """

        return len(self._tri_data) * 3

    def get_toplevel_object(self, get_group=False):

        return self.geom_data_obj.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    @property
    def merged_subobj(self):

        return self

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_triangle_data(self, triangle_data):

        self._tri_data = triangle_data

    @property
    def neighbor_ids(self):

        merged_verts = self.geom_data_obj.merged_verts
        neighbor_ids = set()

        for vert_id in self.vertex_ids:
            neighbor_ids.update(merged_verts[vert_id].polygon_ids)

        neighbor_ids.remove(self.id)

        return neighbor_ids

    @property
    def vertices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self.vertex_ids]

    @property
    def edges(self):

        edges = self.geom_data_obj.get_subobjects("edge")

        return [edges[edge_id] for edge_id in self.edge_ids]

    @property
    def vertex_count(self):

        return len(self.vertex_ids)

    @property
    def row_indices(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        return [verts[vert_id].row_index for vert_id in self.vertex_ids]

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self.geom_data_obj.origin
            return ref_node.get_relative_point(origin, self._center_pos)

        return self._center_pos

    @property
    def center_pos(self):

        return self.get_center_pos()

    @center_pos.setter
    def center_pos(self, center_pos):

        self._center_pos = center_pos

    def update_center_pos(self):

        verts = self.vertices
        positions = [vert.get_pos() for vert in verts]
        self._center_pos = sum(positions, Point3()) / len(positions)

    def get_triangle_normal(self, triangle_index):

        verts = self.geom_data_obj.get_subobjects("vert")
        tri_verts = [verts[vert_id] for vert_id in self._tri_data[triangle_index]]
        pos1, pos2, pos3 = [vert.get_pos() for vert in tri_verts]

        return V3D(pos2 - pos1) ** V3D(pos3 - pos2)

    def get_normal(self, ref_node=None):

        if ref_node:
            origin = self.geom_data_obj.origin
            return ref_node.get_relative_vector(origin, self._normal)

        return self._normal

    @property
    def normal(self):

        return self.get_normal()

    @normal.setter
    def normal(self, normal):

        self._normal = normal

    def update_normal(self):

        tri_count = len(self._tri_data)
        normals = [self.get_triangle_normal(i) for i in range(tri_count)]
        self._normal = sum(normals, Vec3()) / tri_count

    def reverse_normal(self):

        self._normal *= -1.

    @property
    def connected_verts(self):

        merged_verts = self.geom_data_obj.merged_verts
        verts = self.geom_data_obj.get_subobjects("vert")

        return set(verts[v_id] for mv_id in self.vertex_ids for v_id in merged_verts[mv_id])

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

        polys = [self]

        if GD["subobj_edit_options"]["sel_polys_by_surface"]:
            polys = self.geom_data_obj.get_polygon_surface(self.id)

        if GD["subobj_edit_options"]["sel_polys_by_smoothing"]:

            geom_data_obj = self.geom_data_obj
            poly_set = set(polys)

            for poly in polys:
                poly_set.update(geom_data_obj.get_smoothed_polys(poly.id))

            polys = list(poly_set)

        return polys

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        ref_node = GD.world
        plane = Plane(self.get_normal(ref_node), self.get_center_pos(ref_node))

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: ref_node.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def is_facing_camera(self):

        verts = self.geom_data_obj.get_subobjects("vert")

        for vert_ids in self._tri_data:

            plane = Plane(*[verts[vert_id].get_pos(GD.world) for vert_id in vert_ids])

            if plane.dist_to_plane(GD.cam().get_pos(GD.world)) > 0.:
                return True

        return False

    def update_tangent_space(self, flip_tangent=False, flip_bitangent=False):

        verts = self.geom_data_obj.get_subobjects("vert")
        processed_verts = []
        epsilon = 1.e-010

        for vert_ids in self._tri_data:

            for vert_id in vert_ids:

                if vert_id in processed_verts:
                    continue

                vert = verts[vert_id]
                othervertex_ids = list(vert_ids)
                othervertex_ids.remove(vert_id)
                other_verts = [verts[v_id] for v_id in othervertex_ids]
                pos = vert.get_pos()
                pos1, pos2 = [v.get_pos() for v in other_verts]
                pos_vec1 = pos1 - pos
                pos_vec2 = pos2 - pos
                uv = Point2(vert.get_uvs(0))
                uv1, uv2 = [Point2(v.get_uvs(0)) for v in other_verts]
                uv_vec1 = uv1 - uv
                uv_vec2 = uv2 - uv

                # compute a vector pointing in the +U direction, in texture space
                # and in world space

                if abs(uv_vec1.y) < epsilon:
                    u_vec_local = uv_vec1
                    u_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.y) < epsilon:
                    u_vec_local = uv_vec2
                    u_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.y / uv_vec2.y)
                    u_vec_local = uv_vec1 - uv_vec2 * scale
                    # u_vec_local.y will be 0 and thus point in the -/+U direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space U-vector
                    u_vec_world = pos_vec1 - pos_vec2 * scale

                if u_vec_local.x < 0.:
                    u_vec_world *= -1.

                # compute a vector pointing in the +V direction, in texture space
                # and in world space

                if abs(uv_vec1.x) < epsilon:
                    v_vec_local = uv_vec1
                    v_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.x) < epsilon:
                    v_vec_local = uv_vec2
                    v_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.x / uv_vec2.x)
                    v_vec_local = uv_vec1 - uv_vec2 * scale
                    # v_vec_local.x will be 0 and thus point in the -/+V direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space V-vector
                    v_vec_world = pos_vec1 - pos_vec2 * scale

                if v_vec_local.y < 0.:
                    v_vec_world *= -1.

                normal = vert.normal
                tangent_plane = Plane(normal, Point3())
                # the tangent vector is the world-space U-vector projected onto
                # the tangent plane
                tangent = Vec3(tangent_plane.project(Point3(u_vec_world)))

                if not tangent.normalize():
                    continue

                # the bitangent vector is the world-space V-vector projected onto
                # the tangent plane
                bitangent = Vec3(tangent_plane.project(Point3(v_vec_world)))

                if not bitangent.normalize():
                    continue

                if flip_tangent:
                    tangent *= -1.

                if flip_bitangent:
                    bitangent *= -1.

                tangent_space = (tangent, bitangent)
                vert.tangent_space = tangent_space
                processed_verts.append(vert_id)


class PolygonManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "poly", self.__create_polygon, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("poly")

    def __create_polygon(self, geom_data_obj, triangle_data, edges, verts):

        poly_id = self.get_next_id()
        picking_col_id = self.get_next_picking_color_id()
        polygon = Polygon(poly_id, picking_col_id, geom_data_obj, triangle_data, edges, verts)

        return polygon


MainObjects.add_class(PolygonManager)

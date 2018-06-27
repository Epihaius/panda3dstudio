from ..base import *


class Polygon(BaseObject):

    def __getstate__(self):

        # When pickling a Polygon, it should not have a GeomDataObject, since this
        # will be pickled separately.

        state = self.__dict__.copy()
        state["_geom_data_obj"] = None

        return state

    def __init__(self, poly_id, picking_col_id, geom_data_obj, triangle_data, edges, verts):

        self._type = "poly"
        self._id = poly_id
        self._picking_col_id = picking_col_id
        self._geom_data_obj = geom_data_obj
        self._creation_time = None
        self._prev_prop_time = {"tri_data": None}
        self._tri_data = triangle_data  # sequence of 3-tuples of vertex IDs
        self._vert_ids = [vert.get_id() for vert in verts]
        self._edge_ids = [edge.get_id() for edge in edges]

        for vert in verts:
            vert.set_polygon_id(poly_id)

        for edge in edges:
            edge.set_polygon_id(poly_id)

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
        polygon! Use Polygon.get_vertex_count() for this.

        """

        return len(self._tri_data) * 3

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

    def get_toplevel_object(self, get_group=False):

        return self._geom_data_obj.get_toplevel_object(get_group)

    def get_merged_object(self):

        return self

    def set_creation_time(self, time_id):

        self._creation_time = time_id

    def get_creation_time(self):

        return self._creation_time

    def set_previous_property_time(self, prop_id, time_id):

        self._prev_prop_time[prop_id] = time_id

    def get_previous_property_time(self, prop_id):

        return self._prev_prop_time[prop_id]

    def set_triangle_data(self, triangle_data):

        self._tri_data = triangle_data

    def get_neighbor_ids(self):

        merged_verts = self._geom_data_obj.get_merged_vertices()
        neighbor_ids = set()

        for vert_id in self._vert_ids:
            neighbor_ids.update(merged_verts[vert_id].get_polygon_ids())

        neighbor_ids.remove(self._id)

        return neighbor_ids

    def get_vertex_ids(self):
        """
        Return the IDs of the vertices belonging to this polygon, in an order that
        can be used to define the winding of a new triangulation, consistent
        with the winding direction of the existing triangles.

        """

        return self._vert_ids

    def get_edge_ids(self):
        """
        Return the IDs of the edges belonging to this polygon, in an order that
        can be used to define the winding of a new triangulation, consistent
        with the winding direction of the existing triangles.

        """

        return self._edge_ids

    def get_vertices(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[vert_id] for vert_id in self._vert_ids]

    def get_edges(self):

        edges = self._geom_data_obj.get_subobjects("edge")

        return [edges[edge_id] for edge_id in self._edge_ids]

    def get_vertex_count(self):

        return len(self._vert_ids)

    def get_row_indices(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        return [verts[vert_id].get_row_index() for vert_id in self._vert_ids]

    def get_triangle_normal(self, triangle_index):

        verts = self._geom_data_obj.get_subobjects("vert")
        tri_verts = [verts[vert_id] for vert_id in self._tri_data[triangle_index]]
        pos1, pos2, pos3 = [vert.get_pos() for vert in tri_verts]

        return V3D(pos2 - pos1) ** V3D(pos3 - pos2)

    def update_normal(self):

        tri_count = len(self._tri_data)
        normals = [self.get_triangle_normal(i) for i in range(tri_count)]
        self._normal = sum(normals, Vec3()) / tri_count

    def reverse_normal(self):

        self._normal *= -1.

    def get_normal(self, ref_node=None):

        if ref_node:
            origin = self._geom_data_obj.get_origin()
            return ref_node.get_relative_vector(origin, self._normal)

        return self._normal

    def get_special_selection(self):

        polys = [self]

        if GlobalData["subobj_edit_options"]["sel_polys_by_surface"]:
            polys = self._geom_data_obj.get_polygon_surface(self._id)

        if GlobalData["subobj_edit_options"]["sel_polys_by_smoothing"]:

            geom_data_obj = self._geom_data_obj
            poly_set = set(polys)

            for poly in polys:
                poly_set.update(geom_data_obj.get_smoothed_polys(poly.get_id()))

            polys = list(poly_set)

        return polys

    def update_center_pos(self):

        verts = self.get_vertices()
        positions = [vert.get_pos() for vert in verts]
        self._center_pos = sum(positions, Point3()) / len(positions)

    def set_center_pos(self, center_pos):

        self._center_pos = center_pos

    def get_center_pos(self, ref_node=None):

        if ref_node:
            origin = self._geom_data_obj.get_origin()
            return ref_node.get_relative_point(origin, self._center_pos)

        return self._center_pos

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        ref_node = self.world
        plane = Plane(self.get_normal(ref_node), self.get_center_pos(ref_node))

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: ref_node.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def is_facing_camera(self):

        verts = self._geom_data_obj.get_subobjects("vert")

        for vert_ids in self._tri_data:

            plane = Plane(*[verts[vert_id].get_pos(self.world) for vert_id in vert_ids])

            if plane.dist_to_plane(self.cam().get_pos(self.world)) > 0.:
                return True

        return False

    def update_tangent_space(self, flip_tangent=False, flip_bitangent=False):

        verts = self._geom_data_obj.get_subobjects("vert")
        processed_verts = []
        epsilon = 1.e-010

        for vert_ids in self._tri_data:

            for vert_id in vert_ids:

                if vert_id in processed_verts:
                    continue

                vert = verts[vert_id]
                other_vert_ids = list(vert_ids)
                other_vert_ids.remove(vert_id)
                other_verts = [verts[v_id] for v_id in other_vert_ids]
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

                normal = vert.get_normal()
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
                vert.set_tangent_space(tangent_space)
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

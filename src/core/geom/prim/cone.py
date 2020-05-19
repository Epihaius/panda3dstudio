from .base import *
from math import pi, sin, cos, sqrt
import array


def _define_geom_data(segments, smooth, temp=False):

    geom_data = []
    pos_objs = []
    positions_main = []
    # keep track of row indices, one SparseArray per generatrix;
    # compute the initial vertex positions the same for all generatrices, as if
    # they were all lying in the front plane, centered at the cone origin;
    # these will then be transformed with the following matrix:
    #     shear_mat (delta_radius) * scale_mat (height) * translate_mat (bottom_radius)
    #     * rotate_mat (generatrix angle)
    # for each generatrix, using the corresponding SparseArray.
    generatrix_arrays = []
    generatrix_arrays_by_vert_id = {}
    generatrix_rot_by_vert_id = {}

    if not temp:
        uvs_main = []

    segs_c = segments["circular"]
    segs_h = segments["height"]
    segs_cap = segments["caps"]
    d_h = 1. / segs_h
    generatrix_pos = [(0., 0., d_h * i) for i in range(segs_h + 1)]

    # Define vertex data

    vert_id = 0
    angle_h = 360. / segs_c
    up_vec = Vec3.up()
    translate_mat = Mat4.translate_mat(1., 0., 0.)

    for i in range(segs_c):

        if not temp:
            u = i / segs_c

        # two SparseArrays are needed; one for per-poly vertices (to shape the main geom)
        # and another for per-triangle vertices (to shape the auxiliary geom, used for
        # wireframe display and snapping)
        sparse_arrays = (SparseArray(), SparseArray())
        generatrix_arrays.append(sparse_arrays)
        mat = translate_mat * Mat4.rotate_mat_normaxis(angle_h * i, up_vec)

        for j in range(segs_h + 1):

            pos_obj = PosObj(generatrix_pos[j])
            pos_objs.append(pos_obj)
            positions_main.append(pos_obj)

            if not temp:
                v = d_h * j
                uvs_main.append((u, v))

            generatrix_arrays_by_vert_id[vert_id] = sparse_arrays
            generatrix_rot_by_vert_id[vert_id] = mat
            vert_id += 1

    positions_main.extend(positions_main[:segs_h + 1])
    sparse_arrays = generatrix_arrays[0]
    generatrix_arrays_by_vert_id.update({vi: sparse_arrays
        for vi in range(vert_id, vert_id + segs_h + 1)})
    generatrix_rot_by_vert_id.update({vi: translate_mat
        for vi in range(vert_id, vert_id + segs_h + 1)})

    if not temp:
        for u, v in uvs_main[:segs_h + 1]:
            uvs_main.append((1., v))

    if segs_cap:

        angle = 2 * pi / segs_c

        positions_cap_bottom = positions_main[::segs_h + 1]
        positions_cap_top = positions_main[segs_h::segs_h + 1][::-1]

        if not temp:
            uvs_cap_bottom = []
            uvs_cap_top = []

        def add_cap_data(cap_id):

            # Add data related to vertices along the cap segments

            if cap_id == "bottom":

                positions = positions_cap_bottom
                z = -1.
                y_factor = 1.

                if not temp:
                    uvs = uvs_cap_bottom

            else:

                positions = positions_cap_top
                z = 1.
                y_factor = -1.

                if not temp:
                    uvs = uvs_cap_top

            vert_id = segs_c + 1

            if not temp:
                for j in range(segs_c + 1):
                    angle_h = angle * j
                    u = .5 + cos(angle_h) * .5
                    v = .5 - sin(angle_h) * .5
                    uvs.append((u, v))

            for i in range(1, segs_cap):

                r = 1. - i / segs_cap

                for j in range(segs_c + 1):

                    angle_h = angle * j
                    x = r * cos(angle_h)
                    y = r * sin(angle_h) * y_factor

                    if j < segs_c:
                        pos = (x, y, z)
                        pos_obj = PosObj(pos)
                        pos_objs.append(pos_obj)
                    else:
                        pos_obj = positions[vert_id - segs_c]

                    positions.append(pos_obj)

                    if not temp:
                        uvs.append((.5 + x * .5, .5 - y * y_factor * .5))

                    vert_id += 1

            # Add data related to center vertex of cap

            pos = (0., 0., z)
            pos_obj = PosObj(pos)
            pos_objs.append(pos_obj)
            positions.append(pos_obj)

            if not temp:
                uvs.append((.5, .5))

        add_cap_data("bottom")
        add_cap_data("top")

    flat_normals = array.array("f", [])
    smooth_normals = array.array("f", [])
    normals = {"flat": flat_normals, "smooth": smooth_normals}

    # Define faces

    row = 0
    row_alt = 0
    vec = Vec3(1., 0., 1.)

    for i in range(segs_c):

        s = segs_h + 1
        k = i * s

        for j in range(segs_h):

            vi1 = k + j
            vi2 = vi1 + s
            vi3 = vi2 + 1
            vi4 = vi1 + 1
            vert_data = {}
            vert_ids = (vi1, vi2, vi3, vi4)

            plane_points = [generatrix_rot_by_vert_id[vi].xform_point(Point3(*positions_main[vi]))
                for vi in vert_ids[:3]]
            plane = Plane(*plane_points)
            poly_normal = plane.get_normal()
            poly_normal.z = 1.

            for vi in vert_ids:

                pos = positions_main[vi]
                h_mat = generatrix_rot_by_vert_id[vi]
                smooth_normal = h_mat.xform_vec(vec)
                normal = smooth_normal if smooth else poly_normal
                flat_normals.extend(poly_normal)
                smooth_normals.extend(smooth_normal)

                if temp:
                    vert_data[vi] = {"pos": pos, "normal": normal}
                else:
                    uv = uvs_main[vi]
                    vert_data[vi] = {"pos": pos, "normal": normal, "uvs": {0: uv},
                        "pos_ind": pos_objs.index(pos)}

                generatrix_arrays_by_vert_id[vi][0].set_bit(row)
                row += 1

            poly_verts = [vert_data[vi] for vi in vert_ids]
            vert_ids = (vi1, vi2, vi3)
            tri_data1 = [vert_data[vi] for vi in vert_ids]

            for vi in vert_ids:
                generatrix_arrays_by_vert_id[vi][1].set_bit(row_alt)
                row_alt += 1

            vert_ids = (vi1, vi3, vi4)
            tri_data2 = [vert_data[vi] for vi in vert_ids]

            for vi in vert_ids:
                generatrix_arrays_by_vert_id[vi][1].set_bit(row_alt)
                row_alt += 1

            tris = (tri_data1, tri_data2)  # quadrangular face
            poly_data = {"verts": poly_verts, "tris": tris}
            geom_data.append(poly_data)

    cap_arrays = {"bottom": (SparseArray(), SparseArray()), "top":  (SparseArray(), SparseArray())}

    if segs_cap:

        def define_cap_faces(cap_id, row_start, row_alt_start):

            row = row_start
            row_alt = row_alt_start

            if cap_id == "bottom":

                positions = positions_cap_bottom
                sign = 1.

                if not temp:
                    uvs = uvs_cap_bottom

            else:

                positions = positions_cap_top
                sign = -1.

                if not temp:
                    uvs = uvs_cap_top

            sparse_arrays = cap_arrays[cap_id]

            # Define quadrangular faces of cap

            for i in range(segs_cap - 1):

                s = segs_c + 1
                k = i * s

                for j in range(segs_c):

                    vi1 = k + j
                    vi2 = vi1 + s
                    vi3 = vi2 + 1
                    vi4 = vi1 + 1
                    vert_data = {}
                    vert_ids = (vi1, vi2, vi3, vi4)

                    for vi in vert_ids:

                        pos = positions[vi]
                        normal = Vec3(0., 0., -1. * sign)
                        flat_normals.extend(normal)
                        smooth_normals.extend(normal)

                        if temp:
                            vert_data[vi] = {"pos": pos, "normal": normal}
                        else:
                            uv = uvs[vi]
                            vert_data[vi] = {"pos": pos, "normal": normal, "uvs": {0: uv},
                                "pos_ind": pos_objs.index(pos)}

                        if pos in positions_main:
                            index = positions_main.index(pos)
                            generatrix_arrays_by_vert_id[index][0].set_bit(row)
                        else:
                            sparse_arrays[0].set_bit(row)

                        row += 1

                    poly_verts = [vert_data[vi] for vi in vert_ids]
                    vert_ids = (vi1, vi2, vi3)
                    tri_data1 = [vert_data[vi] for vi in vert_ids]

                    for vi in vert_ids:
                        pos = positions[vi]
                        if pos in positions_main:
                            index = positions_main.index(pos)
                            generatrix_arrays_by_vert_id[index][1].set_bit(row_alt)
                        else:
                            sparse_arrays[1].set_bit(row_alt)
                        row_alt += 1

                    vert_ids = (vi1, vi3, vi4)
                    tri_data2 = [vert_data[vi] for vi in vert_ids]

                    for vi in vert_ids:
                        pos = positions[vi]
                        if pos in positions_main:
                            index = positions_main.index(pos)
                            generatrix_arrays_by_vert_id[index][1].set_bit(row_alt)
                        else:
                            sparse_arrays[1].set_bit(row_alt)
                        row_alt += 1

                    tris = (tri_data1, tri_data2)  # quadrangular face
                    poly_data = {"verts": poly_verts, "tris": tris}
                    geom_data.append(poly_data)

            # Define triangular faces at center of cap

            s = segs_c + 1
            vi1 = segs_cap * s

            for j in range(segs_c):

                vi2 = vi1 - 1 - j
                vi3 = vi2 - 1
                vert_ids = (vi1, vi2, vi3)
                tri_data = []

                for vi in vert_ids:

                    pos = positions[vi]
                    normal = Vec3(0., 0., -1. * sign)
                    flat_normals.extend(normal)
                    smooth_normals.extend(normal)

                    if temp:
                        tri_data.append({"pos": pos, "normal": normal})
                    else:
                        uv = uvs[vi]
                        tri_data.append({"pos": pos, "normal": normal, "uvs": {0: uv},
                            "pos_ind": pos_objs.index(pos)})

                    if pos in positions_main:
                        index = positions_main.index(pos)
                        generatrix_arrays_by_vert_id[index][0].set_bit(row)
                        generatrix_arrays_by_vert_id[index][1].set_bit(row_alt)
                    else:
                        sparse_arrays[0].set_bit(row)
                        sparse_arrays[1].set_bit(row_alt)

                    row += 1
                    row_alt += 1

                tris = (tri_data,)  # triangular face
                poly_data = {"verts": tri_data, "tris": tris}
                geom_data.append(poly_data)

            return row, row_alt

        row, row_alt = define_cap_faces("bottom", row, row_alt)
        define_cap_faces("top", row, row_alt)

    return geom_data, normals, (generatrix_arrays, cap_arrays)


class TemporaryCone(TemporaryPrimitive):

    def __init__(self, segments, is_smooth, color, pos):

        TemporaryPrimitive.__init__(self, "cone", color, pos)

        self._bottom_radius = 0.
        self._top_radius = 0.
        self._height = 0.
        geom_data, normals, arrays = _define_geom_data(segments, is_smooth, True)
        generatrix_arrays, cap_arrays = arrays
        self.create_geometry(geom_data)
        origin = self.origin
        origin.set_shader_input("bottom_radius", 1.)
        origin.set_shader_input("top_radius", 1.)
        origin.set_shader_input("height", .001)
        origin.set_shader_input("smooth_normals", is_smooth)
        cone_shaded = shaders.Shaders.cone_shaded
        cone_wire = shaders.Shaders.cone_wire
        scale_mat = Mat4.scale_mat(1., 1., 0.)
        scale_z_bottom = abs(self._height) if self._height < 0. else 0.
        cap_mat = Mat4.scale_mat(1., 1., scale_z_bottom)

        for child in origin.get_children():

            vertex_data = child.node().modify_geom(0).modify_vertex_data()
            tmp_mat = Mat4.translate_mat(1., 0., 0.)
            angle = 360. / segments["circular"]
            axis_vec = Vec3.up()
            index = 0 if child.name == "shaded" else 1

            for i, rows in enumerate(generatrix_arrays):
                mat = tmp_mat * Mat4.rotate_mat_normaxis(angle * i, axis_vec)
                vertex_data.transform_vertices(mat, rows[index])

            vertex_data.transform_vertices(cap_mat, cap_arrays["bottom"][index])

            if child.name == "shaded":
                normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
                vert_count = segments["circular"] * segments["height"] * 4
                size = vert_count * 3
                normal_view[:size] = normals["smooth" if is_smooth else "flat"][:size]
                tmp_vertex_data = GeomVertexData(vertex_data)
                tmp_vertex_data.set_array(0, tmp_vertex_data.modify_array(2))
                tmp_vertex_data.transform_vertices(scale_mat, 0, vert_count)
                vertex_data.set_array(2, tmp_vertex_data.modify_array(0))
                child.set_shader(cone_shaded)
            else:
                child.set_shader(cone_wire)

    def update_size(self, bottom_radius=None, top_radius=None, height=None):

        origin = self.origin

        if bottom_radius is not None:

            r = max(bottom_radius, .001)

            if self._bottom_radius != r:
                self._bottom_radius = r
                origin.set_shader_input("bottom_radius", r)

        if top_radius is not None:

            r = max(top_radius, 0.)

            if self._top_radius != r:
                self._top_radius = r
                origin.set_shader_input("top_radius", r)

        if height is not None:

            abs_h = max(abs(height), .001)
            h = -abs_h if height < 0. else abs_h

            if self._height != h:
                self._height = h
                origin.set_shader_input("height", h)

    def get_size(self):

        return self._bottom_radius, self._top_radius, self._height

    def get_height(self):

        return self._height

    def is_valid(self):

        return min(max(self._bottom_radius, self._top_radius), abs(self._height)) > .001


class Cone(Primitive):

    def __getstate__(self):

        state = Primitive.__getstate__(self)
        del state["_normals"]
        del state["_generatrix_arrays"]
        del state["_cap_arrays"]

        return state

    def __init__(self, model, segments, is_smooth, picking_col_id, geom_data,
                 normals, arrays):

        self._segments = segments
        self._bottom_radius = 0.
        self._top_radius = 0.
        self._height = 0.
        self._is_smooth = is_smooth
        self._normals = normals
        self._generatrix_arrays, self._cap_arrays = arrays

        prop_ids = ["segments", "radius_bottom", "radius_top", "height", "smoothness"]

        Primitive.__init__(self, "cone", model, prop_ids, picking_col_id, geom_data)

        self.uv_mats = [[Mat4(Mat4.ident_mat()) for _ in range(3)] for uv_set_id in range(8)]

    def create_parts(self, start_color_id):

        segments = self._segments
        segs_c = segments["circular"]
        segs_h = segments["height"]
        segs_cap = segments["caps"]
        data_row_ranges = []
        end_index = segs_c * segs_h * 4
        data_row_ranges.append((0, end_index))

        if segs_cap:
            start_index = end_index
            size = self.geom.node().get_geom(0).get_vertex_data().get_num_rows()
            cap_size = (size - start_index) // 2
            end_index = start_index + cap_size
            data_row_ranges.append((start_index, end_index))
            start_index = end_index
            end_index = start_index + cap_size
            data_row_ranges.append((start_index, end_index))

        end_index = segs_c * segs_h * 6
        prim_row_ranges = [(0, end_index)]

        if segs_cap:
            start_index = end_index
            size = self.geom.node().get_geom(0).get_primitive(0).get_num_vertices()
            cap_size = (size - start_index) // 2
            end_index = start_index + cap_size
            prim_row_ranges.append((start_index, end_index))
            start_index = end_index
            end_index = start_index + cap_size
            prim_row_ranges.append((start_index, end_index))

        row1 = 0
        row3 = segs_c * segs_h * 4 - 2
        row2 = row3 - segs_h * 4 + 3
        row4 = segs_h * 4 - 1
        uv_rows_main = (row1, row2, row3, row4)
        uv_rows = [uv_rows_main]

        if segs_cap:
            if segs_cap > 1:
                row1 = segs_c * segs_h * 4 + 3
                uv_rows_cap = [row1]
                for i in range(1, segs_c):
                    uv_rows_cap.append(row1 + i * 4)
                uv_rows.append(uv_rows_cap[::-1])
                row1 += segs_c * ((segs_cap - 1) * 4 + 3) - 3
                uv_rows_cap = [row1]
                for i in range(1, segs_c):
                    uv_rows_cap.append(row1 + i * 4)
                uv_rows.append(uv_rows_cap[::-1])
            else:
                row1 = segs_c * segs_h * 4 + 1
                uv_rows_cap = [row1]
                for i in range(1, segs_c):
                    uv_rows_cap.append(row1 + i * 3)
                uv_rows.append(uv_rows_cap)
                row1 += segs_c * segs_cap * 3
                uv_rows_cap = [row1]
                for i in range(1, segs_c):
                    uv_rows_cap.append(row1 + i * 3)
                uv_rows.append(uv_rows_cap)

        seam_rows_main = []
        a = segs_h * 6
        b = (segs_h - 1) * 6
        c = (segs_c - 1) * segs_h * 6
        for i in range(segs_h):
            seam_rows_main.extend([i * 6 + 3, i * 6 + 5])
        for i in range(segs_c):
            seam_rows_main.extend([i * a, i * a + 1, i * a + b + 2, i * a + b + 4, i * a + b + 5])
        for i in range(segs_h):
            seam_rows_main.extend([c + i * 6 + 1, c + i * 6 + 2, c + i * 6 + 4])
        seam_rows = [seam_rows_main]

        if segs_cap:
            if segs_cap > 1:
                row1 = segs_c * segs_h * 6 + 3
                seam_rows_cap = [row1, row1 + 2]
                for i in range(1, segs_c):
                    seam_rows_cap.extend([row1 + i * 6, row1 + i * 6 + 2])
                seam_rows.append(seam_rows_cap)
                row1 += segs_c * ((segs_cap - 1) * 6 + 3)
                seam_rows_cap = [row1, row1 + 2]
                for i in range(1, segs_c):
                    seam_rows_cap.extend([row1 + i * 6, row1 + i * 6 + 2])
                seam_rows.append(seam_rows_cap)
            else:
                row1 = segs_c * segs_h * 6 + 1
                seam_rows_cap = [row1, row1 + 1]
                for i in range(1, segs_c):
                    seam_rows_cap.extend([row1 + i * 3, row1 + i * 3 + 1])
                seam_rows.append(seam_rows_cap)
                row1 += segs_c * segs_cap * 3
                seam_rows_cap = [row1, row1 + 1]
                for i in range(1, segs_c):
                    seam_rows_cap.extend([row1 + i * 3, row1 + i * 3 + 1])
                seam_rows.append(seam_rows_cap)

        return Primitive.create_parts(self, data_row_ranges, prim_row_ranges,
            uv_rows, seam_rows, start_color_id)

    def apply_uv_matrices(self):

        mats = self.uv_mats
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        segments = self._segments
        segs_c = segments["circular"]
        segs_h = segments["height"]
        segs_cap = segments["caps"]
        end_index = segs_c * segs_h * 4
        row_ranges = [(0, end_index)]

        if segs_cap:
            start_index = end_index
            size = vertex_data.get_num_rows()
            cap_size = (size - start_index) // 2
            end_index = start_index + cap_size
            row_ranges.append((start_index, end_index))
            start_index = end_index
            end_index = start_index + cap_size
            row_ranges.append((start_index, end_index))

        for uv_set_id in range(8):
            for mat, (start_row, end_row) in zip(mats[uv_set_id], row_ranges):
                rows = SparseArray.range(start_row, end_row - start_row)
                Mgr.do("transform_primitive_uvs", vertex_data, uv_set_id, mat, rows)

    def recreate(self):

        geom_data, normals, arrays = _define_geom_data(self._segments, self._is_smooth)
        self._normals = normals
        self._generatrix_arrays, self._cap_arrays = arrays
        Primitive.recreate(self, geom_data)

    def set_segments(self, segments):

        if self._segments == segments:
            return False

        self._segments = segments

        return True

    def __update_size(self):

        height = abs(self._height)
        b_radius = self._bottom_radius
        t_radius = self._top_radius
        segments = self._segments

        if self._height < 0.:
            z = self._height
            scale_xy_bottom = t_radius
            scale_xy_top = b_radius
            scale_z_bottom = height
            scale_z_top = 0.
        else:
            z = 0.
            scale_xy_bottom = b_radius
            scale_xy_top = t_radius
            scale_z_bottom = 0.
            scale_z_top = height

        delta_radius = scale_xy_bottom - scale_xy_top
        angle = 360. / segments["circular"]
        axis_vec = Vec3.up()

        for i, geom in enumerate((self.geom, self.aux_geom)):

            vertex_data = geom.node().modify_geom(0).modify_vertex_data()
            pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
            pos_view[:] = self.initial_coords[i]
            # use shearing per generatrix to update the vertex positions
            shear = -delta_radius
            tmp_mat = Mat4.shear_mat(0., shear, 0.) * Mat4.scale_mat(1., 1., height)
            tmp_mat = tmp_mat * Mat4.translate_mat(scale_xy_bottom, 0., z)

            for j, rows in enumerate(self._generatrix_arrays):
                mat = tmp_mat * Mat4.rotate_mat_normaxis(angle * j, axis_vec)
                vertex_data.transform_vertices(mat, rows[i])

            bottom_array = self._cap_arrays["bottom"][i]
            top_array = self._cap_arrays["top"][i]
            scale_mat = Mat4.scale_mat(scale_xy_bottom, scale_xy_bottom, scale_z_bottom)
            vertex_data.transform_vertices(scale_mat, bottom_array)
            scale_mat = Mat4.scale_mat(scale_xy_top, scale_xy_top, scale_z_top)
            vertex_data.transform_vertices(scale_mat, top_array)

        self.__update_normals()
        self.update_poly_centers()

        self.model.bbox.update(self.geom.get_tight_bounds())

    def init_size(self, bottom_radius, top_radius, height):

        self._bottom_radius = max(bottom_radius, .001)
        self._top_radius = max(top_radius, 0.)
        self._height = max(abs(height), .001) * (-1. if height < 0. else 1.)
        self.__update_size()

    def set_bottom_radius(self, radius):

        if self._bottom_radius == radius:
            return False

        self._bottom_radius = radius

        return True

    def set_top_radius(self, radius):

        if self._top_radius == radius:
            return False

        self._top_radius = radius

        return True

    def set_height(self, height):

        if self._height == height:
            return False

        self._height = height

        return True

    def set_smooth(self, is_smooth=True):

        if self._is_smooth == is_smooth:
            return False

        self._is_smooth = is_smooth

        return True

    def __update_normals(self):

        # Use non-uniform scaling to update the vertex normals:
        # the default normals should be (sin(x), cos(x), 1.), so they can be scaled
        # along the Z-axis by the sine of the new vertical angle and along both the
        # X- and Y-axes by the cosine of that angle;
        # this sine is delta_radius / d, while the cosine is height / d in the code
        # below (note that a different delta_radius is needed for flat normals).

        segments = self._segments
        height = abs(self._height)
        b_radius = self._bottom_radius
        t_radius = self._top_radius
        delta_radius = (t_radius - b_radius) if self._height < 0. else (b_radius - t_radius)

        if not self._is_smooth:
            delta_radius *= cos(pi / segments["circular"])

        end_index = segments["circular"] * segments["height"] * 4
        size = end_index * 3
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
        normal_view[:size] = self._normals["smooth" if self._is_smooth else "flat"][:size]
        tmp_vertex_data = GeomVertexData(vertex_data)
        tmp_vertex_data.set_array(0, tmp_vertex_data.modify_array(2))
        d = sqrt(delta_radius ** 2. + height ** 2.)
        scale_xy = height / d
        scale_z = delta_radius / d
        scale_mat = Mat4.scale_mat(scale_xy, scale_xy, scale_z)
        tmp_vertex_data.transform_vertices(scale_mat, 0, end_index)
        vertex_data.set_array(2, tmp_vertex_data.modify_array(0))

        if self.has_inverted_geometry():
            geom = self.geom.node().modify_geom(0)
            vertex_data = geom.get_vertex_data().reverse_normals()
            reverse_view = memoryview(vertex_data.get_array(2)).cast("B").cast("f")
            vertex_data = geom.modify_vertex_data()
            normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
            normal_view[:size] = reverse_view[:size]

    def unlock_geometry(self, unlocked_geom):

        Primitive.unlock_geometry(self, unlocked_geom, update_normal_data=True)

    def get_data_to_store(self, event_type, prop_id=""):

        if event_type == "prop_change" and prop_id in self.get_type_property_ids():

            data = {}
            data[prop_id] = {"main": self.get_property(prop_id)}

            if prop_id == "segments":
                data["uvs"] = {"main": self.get_property("uvs")}

            return data

        return Primitive.get_data_to_store(self, event_type, prop_id)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "segments":
            if for_remote_update:
                return self._segments
            else:
                return {"count": self._segments, "pos_data": self.initial_coords,
                        "normals": self._normals, "generatrix_arrays": self._generatrix_arrays,
                        "cap_arrays": self._cap_arrays, "geom_data": self.geom_data,
                        "geom": self.geom_for_pickling, "aux_geom": self.aux_geom_for_pickling}
        elif prop_id == "radius_bottom":
            return self._bottom_radius
        elif prop_id == "radius_top":
            return self._top_radius
        elif prop_id == "height":
            return self._height
        elif prop_id == "smoothness":
            return self._is_smooth
        else:
            return Primitive.get_property(self, prop_id, for_remote_update)

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "cone", prop_id,
                                self.get_property(prop_id, True))

        obj_id = self.toplevel_obj.id

        if prop_id == "segments":

            if restore:
                segments = value["count"]
                self.initial_coords = value["pos_data"]
                self._normals = value["normals"]
                self._generatrix_arrays = value["generatrix_arrays"]
                self._cap_arrays = value["cap_arrays"]
                self.geom_data = value["geom_data"]
                self.geom = value["geom"]
                self.aux_geom = value["aux_geom"]
                self.model.bbox.update(self.geom.get_tight_bounds())
                self.setup_geoms()
                vertex_data = self.geom.node().get_geom(0).get_vertex_data()
                uv_view = memoryview(vertex_data.get_array(4)).cast("B").cast("f")
                self.default_uvs = array.array("f", uv_view)
            else:
                segments = self._segments.copy()
                segments.update(value)

            task = self.__update_size
            sort = PendingTasks.get_sort("set_normals", "object") - 1
            PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
            self.model.update_group_bbox()

            change = self.set_segments(segments)

            if change:

                if not restore:
                    self.recreate()

                update_app()

            return change

        elif prop_id == "radius_bottom":

            change = self.set_bottom_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "radius_top":

            change = self.set_top_radius(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "height":

            change = self.set_height(value)

            if change:
                task = self.__update_size
                sort = PendingTasks.get_sort("set_normals", "object") - 1
                PendingTasks.add(task, "upd_size", "object", sort, id_prefix=obj_id)
                self.model.update_group_bbox()
                update_app()

            return change

        elif prop_id == "smoothness":

            change = self.set_smooth(value)

            if restore:
                task = self.__update_normals
                PendingTasks.add(task, "set_normals", "object", id_prefix=obj_id)
            elif change:
                self.__update_normals()

            if change:
                update_app()

            return change

        else:

            return Primitive.set_property(self, prop_id, value, restore)


class ConeManager(PrimitiveManager):

    def __init__(self):

        PrimitiveManager.__init__(self, "cone")

        self._height_axis = V3D(0., 0., 1.)
        self._draw_plane = None
        self._draw_plane_normal = V3D()
        self._dragged_point = Point3()
        self._top_point = Point3()
        self._top_radius_vec = V3D()

        self.set_property_default("radius_bottom", 1.)
        self.set_property_default("radius_top", 0.)
        self.set_property_default("height", 1.)
        self.set_property_default("smoothness", True)
        self.set_property_default("temp_segments", {"circular": 12, "height": 1, "caps": 1})
        self.set_property_default("segments", {"circular": 24, "height": 6, "caps": 1})
        # minimum circular segments = 3
        # minimum height segments = 1
        # minimum cap segments = 0: no caps

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1,
                          self.__finish_creation_phase1)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase2, self.__creation_phase2,
                          self.__finish_creation_phase2)
        creation_phases.append(creation_phase)
        creation_phase = (self.__start_creation_phase3, self.__creation_phase3,
                          self.__finish_creation_phase3)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "cone"
        status_text["phase1"] = "draw out the base"
        status_text["phase2"] = "draw out the height"
        status_text["phase3"] = "draw out the top"

        return PrimitiveManager.setup(self, creation_phases, status_text)

    def define_geom_data(self):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]

        return _define_geom_data(segments, is_smooth)

    def create_temp_primitive(self, color, pos):

        segs = self.get_property_defaults()["segments"]
        tmp_segs = self.get_property_defaults()["temp_segments"]
        segments = {k: min(segs[k], tmp_segs[k]) for k in ("circular", "height", "caps")}
        is_smooth = self.get_property_defaults()["smoothness"]
        tmp_prim = TemporaryCone(segments, is_smooth, color, pos)

        return tmp_prim

    def create_primitive(self, model, picking_col_id, geom_data):

        prop_defaults = self.get_property_defaults()
        segments = prop_defaults["segments"]
        is_smooth = prop_defaults["smoothness"]
        prim = Cone(model, segments, is_smooth, picking_col_id, *geom_data)

        return prim

    def init_primitive_size(self, prim, size=None):

        if size is None:
            prop_defaults = self.get_property_defaults()
            prim.init_size(prop_defaults["radius_bottom"], prop_defaults["radius_top"],
                           prop_defaults["height"])
        else:
            prim.init_size(*size)

    def __start_creation_phase1(self):
        """ Start drawing out cone base """

        tmp_prim = self.get_temp_primitive()
        origin = tmp_prim.origin
        self._height_axis = GD.world.get_relative_vector(origin, V3D(0., 0., 1.))

    def __creation_phase1(self):
        """ Draw out cone base """

        point = None
        grid = Mgr.get("grid")
        grid_origin = grid.origin
        origin_pos = grid_origin.get_relative_point(GD.world, self.get_origin_pos())
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_1"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_1"]

        if snap_on and snap_tgt_type != "increment":
            point = Mgr.get("snap_target_point")

        if point is None:

            if snap_on and snap_tgt_type != "increment":
                Mgr.do("set_projected_snap_marker_pos", None)

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            point = grid.get_point_at_screen_pos(screen_pos, origin_pos)

        else:

            point = grid.get_projected_point(point, origin_pos)
            proj_point = GD.world.get_relative_point(grid_origin, point)
            Mgr.do("set_projected_snap_marker_pos", proj_point)

        if not point:
            return

        radius_vec = point - origin_pos
        radius = radius_vec.length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            radius = round(radius / offset_incr) * offset_incr
            point = origin_pos + radius_vec.normalized() * radius

        self._dragged_point = GD.world.get_relative_point(grid_origin, point)
        self.get_temp_primitive().update_size(radius, radius)

    def __finish_creation_phase1(self):
        """ End creation phase 1 by setting default cone base radius """

        prop_defaults = self.get_property_defaults()
        radius = prop_defaults["radius_bottom"]
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(radius, radius)

    def __start_creation_phase2(self):
        """ Start drawing out cone height """

        cam = GD.cam()
        cam_forward_vec = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        normal = V3D(cam_forward_vec - cam_forward_vec.project(self._height_axis))

        # If the plane normal is the null vector, the axis must be parallel to
        # the forward camera direction. In this case, a new normal can be chosen
        # arbitrarily, e.g. a horizontal vector perpendicular to the axis.

        if normal.length_squared() < .0001:

            x, y, z = self._height_axis

            # if the height axis is nearly vertical, any horizontal vector will
            # qualify as plane normal, e.g. a vector pointing in the positive
            # X-direction; otherwise, the plane normal can be computed as
            # perpendicular to the axis
            normal = V3D(1., 0., 0.) if max(abs(x), abs(y)) < .0001 else V3D(y, -x, 0.)

        self._draw_plane = Plane(normal, self._dragged_point)

        if GD.cam.lens_type == "persp":

            cam_pos = cam.get_pos(GD.world)

            if normal * V3D(self._draw_plane.project(cam_pos) - cam_pos) < .0001:
                normal *= -1.

        self._draw_plane_normal = normal

        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_2"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_2"]

        if snap_on and snap_tgt_type == "grid_point":

            # Snapping to any point on the active grid plane would just set the height
            # to zero, so a different grid plane needs to be set temporarily;
            # out of the two possible planes, choose the one that faces the camera most.

            grid_origin = Mgr.get("grid").origin
            active_plane_id = GD["active_grid_plane"]
            normal1 = Vec3()
            normal2 = Vec3()
            normal1["xyz".index(active_plane_id[0])] = 1.
            normal2["xyz".index(active_plane_id[1])] = 1.
            normal1 = GD.world.get_relative_vector(grid_origin, normal1)
            normal2 = GD.world.get_relative_vector(grid_origin, normal2)
            plane_id1 = "xyz".replace(active_plane_id[0], "")
            plane_id2 = "xyz".replace(active_plane_id[1], "")

            if abs(cam_forward_vec * normal1) > abs(cam_forward_vec * normal2):
                Mgr.update_app("active_grid_plane", plane_id1)
            else:
                Mgr.update_app("active_grid_plane", plane_id2)

            GD["active_grid_plane"] = active_plane_id

        if snap_on and snap_tgt_type != "increment":
            self._top_point = self._dragged_point

    def __creation_phase2(self):
        """ Draw out cone height """

        self._dragged_point = None
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_2"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_2"]

        if snap_on and snap_tgt_type != "increment":
            self._dragged_point = Mgr.get("snap_target_point")

        if self._dragged_point is None:

            if snap_on and snap_tgt_type != "increment":
                Mgr.do("set_projected_snap_marker_pos", None)

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            cam = GD.cam()
            lens_type = GD.cam.lens_type

            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)
            self._dragged_point = Point3()

            if lens_type == "persp":
                # the height cannot be calculated if the cursor points away from the plane
                # in which it is drawn out
                if V3D(far_point - near_point) * self._draw_plane_normal < .0001:
                    return

            if not self._draw_plane.intersects_line(self._dragged_point, near_point, far_point):
                return

        else:

            grid_origin = Mgr.get("grid").origin
            self._dragged_point = GD.world.get_relative_point(grid_origin, self._dragged_point)
            vec = self._dragged_point - self._top_point
            proj_point = self._top_point + vec.project(self._height_axis)
            Mgr.do("set_projected_snap_marker_pos", proj_point)

        tmp_prim = self.get_temp_primitive()
        origin = tmp_prim.origin
        x, y, z = origin.get_relative_point(GD.world, self._dragged_point)

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_2"]
            z = round(z / offset_incr) * offset_incr
            self._dragged_point = GD.world.get_relative_point(origin, Point3(x, y, z))

        tmp_prim.update_size(height=z)

    def __finish_creation_phase2(self):
        """ End creation phase 2 by setting default cone height """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(height=prop_defaults["height"])

    def __start_creation_phase3(self):
        """ Start drawing out cone top """

        tmp_prim = self.get_temp_primitive()
        origin = tmp_prim.origin
        height = tmp_prim.get_height()
        self._top_point = origin.get_pos(GD.world) + self._height_axis * height
        cam = GD.cam()
        cam_pos = cam.get_pos(GD.world)
        cam_forward_vec = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        self._draw_plane = Plane(cam_forward_vec, self._top_point)
        point = Point3()
        self._draw_plane.intersects_line(point, cam_pos, self._dragged_point)
        self._top_radius_vec = V3D((point - self._top_point).normalized())

    def __creation_phase3(self):
        """ Draw out cone top """

        point = None
        grid = Mgr.get("grid")
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_3"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_3"]

        if snap_on and snap_tgt_type != "increment":
            point = Mgr.get("snap_target_point")

        if point is None:

            if snap_on and snap_tgt_type != "increment":
                Mgr.do("set_projected_snap_marker_pos", None)

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            near_point = Point3()
            far_point = Point3()
            point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            cam = GD.cam()
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)

            if not self._draw_plane.intersects_line(point, near_point, far_point):
                return

            vec = V3D(point - self._top_point)

            if vec * self._top_radius_vec <= 0.:
                top_radius = 0.
            else:
                top_radius = (vec.project(self._top_radius_vec)).length()

        else:

            point_in_plane = grid.origin.get_relative_point(GD.world, self._top_point)
            point = grid.get_projected_point(point, point_in_plane)
            top_radius = (point - point_in_plane).length()
            proj_point = GD.world.get_relative_point(grid.origin, point)
            Mgr.do("set_projected_snap_marker_pos", proj_point)

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_3"]
            top_radius = round(top_radius / offset_incr) * offset_incr

        self.get_temp_primitive().update_size(top_radius=top_radius)

    def __finish_creation_phase3(self):
        """ End creation phase 3 by setting default cone top radius """

        prop_defaults = self.get_property_defaults()
        tmp_prim = self.get_temp_primitive()
        tmp_prim.update_size(top_radius=prop_defaults["radius_top"])


MainObjects.add_class(ConeManager)

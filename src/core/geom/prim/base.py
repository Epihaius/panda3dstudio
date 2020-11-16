from ...base import *
from ..locked_geom import create_aux_geom, LockedGeomBase, LockedGeomManagerBase
import array


def _create_geom(geom_data, initial_coords=None):

    prim = GeomTriangles(Geom.UH_static)
    prim_size = sum(len(poly_data["tris"]) * 3 for poly_data in geom_data)
    int_format = "H"

    if prim_size >= 2 ** 16:
        prim.set_index_type(Geom.NT_uint32)
        int_format = "I"

    prim.reserve_num_vertices(prim_size)
    prim_array = prim.modify_vertices()
    prim_array.unclean_set_num_rows(prim_size)
    prim_view = memoryview(prim_array).cast("B").cast(int_format)
    verts = [v for p in geom_data for v in p["verts"]]
    vert_count = len(verts)
    vert_ids = [id(v) for v in verts]
    prim_view[:] = array.array(int_format, [vert_ids.index(id(v)) for p in geom_data
        for t in p["tris"] for v in t])

    vertex_format = Mgr.get("vertex_format_full")
    vertex_data = GeomVertexData("vert_data", vertex_format, Geom.UH_static)
    vertex_data.reserve_num_rows(vert_count)
    vertex_data.set_num_rows(vert_count)
    pos_view = memoryview(vertex_data.modify_array(0)).cast("B").cast("f")
    pos_coords1 = array.array("f", [x for v in verts for x in v["pos"]])
    pos_view[:] = pos_coords1
    normal_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("f")
    normal_view[:] = array.array("f", [x for v in verts for x in v["normal"]])

    if initial_coords is not None:

        pos_coords2 = array.array("f", [x for p in geom_data for t in p["tris"]
            for v in t for x in v["pos"]])
        initial_coords[:] = pos_coords1, pos_coords2
        uv_coords = array.array("f", [x for v in verts for x in v["uvs"][0]])

        for uv_set_id in range(8):
            uv_view = memoryview(vertex_data.modify_array(4 + uv_set_id)).cast("B").cast("f")
            uv_view[:] = uv_coords

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
            shaded_geom = _create_geom(geom_data)
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


class PrimitivePart:

    def __init__(self, picking_color_id, owner, data_row_range, geom_prim, uv_borders,
                 uv_defaults):

        self.picking_color_id = picking_color_id
        self.owner = owner
        self.data_row_range = data_row_range
        self.geom_prim = geom_prim
        self.uv_borders = uv_borders  # lists of UV coordinates at border vertices
        self.uv_defaults = uv_defaults  # array of default UV coordinates at border vertices
        self.uv_parts = {}
        self.is_selected = False


class Primitive(LockedGeomBase):

    def __getstate__(self):

        state = LockedGeomBase.__getstate__(self)
        state["geom_root"] = None
        state["geom"] = None
        state["aux_geom"] = None
        del state["default_uvs"]
        del state["uv_mats"]

        return state

    def __init__(self, prim_type, model, type_prop_ids, picking_col_id, geom_data):

        self.type = prim_type
        self._prop_ids = ["uvs", "uv_set_names"]
        self._type_prop_ids = type_prop_ids + ["inverted_geom"]
        # the following "initial coordinates" correspond to the vertex positions
        # at the time the geometry is created or recreated; it is kept around to
        # facilitate reshaping the primitive
        self.initial_coords = []
        geom = _create_geom(geom_data, self.initial_coords)

        vertex_data = geom.node().get_geom(0).get_vertex_data()
        uv_view = memoryview(vertex_data.get_array(4)).cast("B").cast("f")
        self.default_uvs = array.array("f", uv_view)
        self.uv_mats = []  # matrices to transform each distinct part of this primitive
        self._uv_set_names = ["", "1", "2", "3", "4", "5", "6", "7"]

        LockedGeomBase.__init__(self, model, geom, geom_data, picking_col_id)

        self.update_render_mode(False)

    @property
    def geom_for_pickling(self):

        # Make sure that self.geom gets pickled as a copy with default UV coordinates.

        geom = LockedGeomBase.geom_for_pickling.fget(self)
        g = geom.node().modify_geom(0)
        vertex_data = GeomVertexData(g.get_vertex_data())

        for uv_set_id in range(8):
            uv_view = memoryview(vertex_data.modify_array(4 + uv_set_id)).cast("B").cast("f")
            uv_view[:] = self.default_uvs

        g.set_vertex_data(vertex_data)

        return geom

    def set_index_offset(self, index_offset):
        """
        Set the offset to be added to the indices of the distinct parts of the model
        primitive, so they can be region-selected in the UV interface.

        """

        self._pickable_geom.set_shader_input("index_offset", index_offset)

    def apply_uv_matrices(self):
        """
        Update the UVs of the distinct parts of the model primitive by applying their
        associated matrices to the corresponding row ranges.
        Override in derived class.

        """

        pass

    def recreate(self, geom_data):

        self.geom_data = geom_data
        self.geom = _create_geom(geom_data, self.initial_coords)
        self.aux_geom = create_aux_geom(geom_data)
        self.setup_geoms()

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        uv_view = memoryview(vertex_data.get_array(4)).cast("B").cast("f")
        self.default_uvs = array.array("f", uv_view)

        self.apply_uv_matrices()

        Mgr.notify("pickable_geom_altered", self.toplevel_obj)

    def can_edit_uvs(self):
        """
        For backward compatibility, check if this primitive can have its UVs
        edited.
        Return False if this primitive was created with an older version of
        the application.

        """

        return "uvs" in self._prop_ids

    @property
    def parts(self):
        """
        Get the distinct parts of the model primitive as separate, selectable
        subobjects, specifically for the purpose of editing their UVs.

        """

        if not hasattr(self, "_parts"):
            msg = "The parts needed for UV editing have not been created"
            msg += f'\nfor primitive "{self.model.name}"!'
            Notifiers.geom.warning(msg)
            return []

        return self._parts

    def create_parts(self, data_row_ranges, prim_row_ranges, uv_rows, seam_rows, start_color_id):
        """
        Create the distinct parts of the model primitive as separate, selectable
        subobjects, specifically for the purpose of editing their UVs.

        """

        vertex_data = self.aux_geom.node().modify_geom(0).modify_vertex_data()
        sides_view = memoryview(vertex_data.modify_array(1)).cast("B").cast("I")
        self._sides_data = array.array("I", sides_view)
        tris_prim = self.aux_geom.node().get_geom(0).get_primitive(0)
        int_format = "I" if tris_prim.index_type == Geom.NT_uint32 else "H"
        prim_view = memoryview(tris_prim.get_vertices()).cast("B").cast(int_format)
        prim_values = array.array(int_format, prim_view)

        seam_data = GeomVertexData(vertex_data)
        # create new vertex data to generate sides column initialized with zeroes
        tmp_data = GeomVertexData("tmp", Mgr.get("aux_locked_vertex_format"), Geom.UH_static)
        tmp_data.set_num_rows(seam_data.get_num_rows())
        seam_data.set_array(1, tmp_data.get_array(1))
        seam_view = memoryview(seam_data.modify_array(1)).cast("B").cast("I")
        seam_geom = Geom(seam_data)
        seam_prim = GeomTriangles(Geom.UH_static)
        seam_prim.set_index_type(Geom.NT_uint32)
        seam_geom.add_primitive(seam_prim)
        geom_node = GeomNode("uv_seams")
        geom_node.add_geom(seam_geom)
        self._seams_geom = seams = self.geom_root.attach_new_node(geom_node)
        seams.set_light_off()
        seams.set_color(0., 1., 0., 1.)
        seams.set_shader(self.aux_geom.get_shader())
        seams.set_shader_input("inverted", self.has_inverted_geometry())
        seams.set_shader_input("two_sided", GD["two_sided"])

        processed_tris = []

        for rows in seam_rows:

            for row in rows:

                i = prim_values.index(row) // 3 * 3

                if i not in processed_tris:

                    vi1, vi2, vi3 = prim_values[i:i+3]
                    seam_prim.add_vertices(vi1, vi2, vi3)
                    old_sides = sides_view[vi1]
                    old_s1 = old_sides >> 2
                    old_s2 = (old_sides ^ (old_s1 << 2)) >> 1
                    old_s3 = old_sides ^ (old_s1 << 2) ^ (old_s2 << 1)
                    s1 = 0 if {vi1, vi2}.issubset(rows) else 1
                    s2 = 0 if {vi2, vi3}.issubset(rows) else 1
                    s3 = 0 if {vi3, vi1}.issubset(rows) else 1
                    seam_s1 = (1 - s1) * old_s1
                    seam_s2 = (1 - s2) * old_s2
                    seam_s3 = (1 - s3) * old_s3
                    s1 *= old_s1
                    s2 *= old_s2
                    s3 *= old_s3
                    sides = array.array("I", [s1 << 2 | s2 << 1 | s3])

                    for vi in (vi1, vi2, vi3):
                        sides_view[vi:vi+1] = sides

                    sides = array.array("I", [seam_s1 << 2 | seam_s2 << 1 | seam_s3])

                    for vi in (vi1, vi2, vi3):
                        seam_view[vi:vi+1] = sides

                    processed_tris.append(i)

        color_id = start_color_id
        self._parts = parts = []
        self._geom_prim = prim = self.geom.node().get_geom(0).get_primitive(0)
        index_type = prim.index_type
        int_format = "I" if index_type == Geom.NT_uint32 else "H"
        from_view = memoryview(prim.get_vertices()).cast("B").cast(int_format)
        geom = self.geom.node().modify_geom(0)
        geom.clear_primitives()
        vertex_data = geom.modify_vertex_data()

        uv_views = []
        self._start_uvs = []
        self._start_mats = []
        uv_mats = self.uv_mats

        for i in range(8):
            uv_view = memoryview(vertex_data.get_array(4 + i)).cast("B").cast("f")
            uv_views.append(uv_view)
            self._start_uvs.append(array.array("f", uv_view))
            self._start_mats.append([Mat4(mat) for mat in uv_mats[i]])

        node = GeomNode("selected_prim_parts")
        node.add_geom(Geom(vertex_data))
        self._selected_geom = selected_geom = self.geom_root.attach_new_node(node)
        selected_geom.set_state(Mgr.get("poly_selection_state"))
        selected_geom.set_effects(Mgr.get("poly_selection_effects"))
        selected_geom.show(Mgr.get("render_mask"))
        node = GeomNode("pickable_prim_parts")
        self._pickable_geom = pickable_geom = self.geom_root.attach_new_node(node)
        vertex_data = vertex_data.convert_to(PrimitiveManager.pickable_part_vertex_format)
        node.add_geom(Geom(vertex_data))
        node.add_geom(Geom(vertex_data))
        pickable_geom.show_through(Mgr.get("picking_mask"))
        pickable_geom.hide(Mgr.get("render_mask"))
        color_values = bytearray()
        index_values = array.array("I", [])
        pickable_type_id = PickableTypes.get_id("primitive_part")
        geom2 = pickable_geom.node().modify_geom(1)
        default_uvs = self.default_uvs

        if self.has_inverted_geometry():
            sizes = [end - start for start, end in prim_row_ranges][::-1]
            prim_row_ranges = [(sum(sizes[:i]), sum(sizes[:i+1])) for i in range(len(sizes))][::-1]

        for i, (data_row_range, prim_row_range, rows) in enumerate(zip(data_row_ranges,
                prim_row_ranges, uv_rows)):
            r = color_id >> 16
            g = (color_id ^ (r << 16)) >> 8
            b = color_id ^ (r << 16) ^ (g << 8)
            picking_color = (r, g, b, pickable_type_id)
            start_row, end_row = data_row_range
            row_count = end_row - start_row
            color_values.extend(picking_color * row_count)
            index_values.extend((i for _ in range(row_count)))
            part_prim = GeomTriangles(Geom.UH_static)
            part_prim.set_index_type(index_type)
            prim_array = part_prim.modify_vertices()
            start_row, end_row = prim_row_range
            row_count = end_row - start_row
            prim_array.unclean_set_num_rows(row_count)
            prim_view = memoryview(prim_array).cast("B").cast(int_format)
            prim_view[:] = from_view[start_row:end_row]
            geom.add_primitive(part_prim)
            geom2.add_primitive(part_prim)
            uv_borders = []

            for uv_view in uv_views:
                uv_border = [tuple(uv_view[row*2:row*2+2]) for row in rows]
                uv_borders.append(uv_border)

            defaults = array.array("f", [])

            for row in rows:
                x, z = default_uvs[row*2:row*2+2]
                defaults.extend((x, 0., z))

            part = PrimitivePart(color_id, self, data_row_range, part_prim, uv_borders, defaults)
            parts.append(part)
            color_id += 1

        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        color_array = vertex_data.modify_array(1)
        color_view = memoryview(color_array).cast("B")
        color_view[:] = color_values
        index_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("I")
        index_view[:] = index_values
        vertex_data = pickable_geom.node().modify_geom(1).modify_vertex_data()
        color_array = vertex_data.modify_array(1)
        color_view = memoryview(color_array).cast("B")
        color_view[:] = color_values
        index_view = memoryview(vertex_data.modify_array(2)).cast("B").cast("I")
        index_view[:] = index_values
        self._parts_shown = True
        self._copied_uv_array = None
        self._copied_uv_mats = None
        self.uvs_changed = False

        return parts

    def destroy_parts(self):
        """
        Destroy the distinct parts of the model primitive that were created as separate,
        selectable subobjects, specifically for the purpose of editing their UVs.

        """

        if not hasattr(self, "_parts"):
            return

        geom = self.geom.node().modify_geom(0)
        geom.clear_primitives()
        geom.add_primitive(self._geom_prim)
        vertex_data = self.aux_geom.node().modify_geom(0).modify_vertex_data()
        sides_view = memoryview(vertex_data.modify_array(1)).cast("B").cast("I")
        sides_view[:] = self._sides_data
        self._selected_geom.detach_node()
        self._pickable_geom.detach_node()
        self._seams_geom.detach_node()
        del self._sides_data
        del self._geom_prim
        del self._selected_geom
        del self._pickable_geom
        del self._seams_geom
        del self._parts
        del self._parts_shown
        del self._start_uvs
        del self._start_mats
        del self._copied_uv_array
        del self._copied_uv_mats
        del self.uvs_changed

    def show_parts(self, show=True):
        """
        Show or hide the distinct parts of the model primitive that were created as
        separate, selectable subobjects, specifically for the purpose of editing their UVs.

        """

        if not hasattr(self, "_parts"):
            return

        self._parts_shown = show
        picking_mask = Mgr.get("picking_mask")
        render_mask = Mgr.get("render_mask")
        selected_geom = self._selected_geom
        pickable_geom = self._pickable_geom

        if show:

            pickable_geom.show_through(picking_mask)
            selected_geom.set_state(Mgr.get("poly_selection_state"))
            selected_geom.set_effects(Mgr.get("poly_selection_effects"))
            selected_geom.show(render_mask)

        else:

            pickable_geom.hide(picking_mask)
            selected_geom.set_state(RenderState.make_empty())
            selected_geom.clear_effects()

            if "shaded" in GD["render_mode"]:
                selected_geom.show(render_mask)
            else:
                selected_geom.hide(render_mask)

    def get_selected_parts(self):
        """
        Get the distinct parts of the model primitive, selected for UV editing.

        """

        return [p for p in self._parts if p.is_selected]

    def set_selected_parts(self, parts):
        """
        Select distinct parts of the model primitive, so their UVs can be edited
        separately from the unselected parts.

        """

        sel_geom = self._selected_geom.node().modify_geom(0)
        sel_geom.clear_primitives()
        unsel_geom = self.geom.node().modify_geom(0)
        unsel_geom.clear_primitives()
        sel_geom_pickable = self._pickable_geom.node().modify_geom(0)
        sel_geom_pickable.clear_primitives()
        unsel_geom_pickable = self._pickable_geom.node().modify_geom(1)
        unsel_geom_pickable.clear_primitives()

        for part in self._parts:
            if part in parts:
                sel_geom.add_primitive(part.geom_prim)
                sel_geom_pickable.add_primitive(part.geom_prim)
                part.is_selected = True
            else:
                unsel_geom.add_primitive(part.geom_prim)
                unsel_geom_pickable.add_primitive(part.geom_prim)
                part.is_selected = False

    def transform_uvs(self, uv_set_id, part_indices, mat, is_rel_value=True):
        """
        Transform the UVs of the selected, distinct parts of the model primitive.

        """

        vertex_data = self._selected_geom.node().modify_geom(0).modify_vertex_data()

        if not is_rel_value:
            start_uvs = self._start_uvs[uv_set_id]
            uv_array = vertex_data.modify_array(4 + uv_set_id)
            uv_view = memoryview(uv_array).cast("B").cast("f")
            start_mats = self._start_mats[uv_set_id]

        rows = SparseArray()
        uv_mats = self.uv_mats[uv_set_id]

        for i in part_indices:

            part = self._parts[i]
            start_row, end_row = part.data_row_range
            rows.set_range(start_row, end_row - start_row)

            if not is_rel_value:
                uv_view[start_row*2:end_row*2] = start_uvs[start_row*2:end_row*2]
                uv_mats[i] = Mat4(start_mats[i])

            uv_mats[i] *= mat

        Mgr.do("transform_primitive_uvs", vertex_data, uv_set_id, mat, rows)
        uv_array = vertex_data.get_array(4 + uv_set_id)
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(4 + uv_set_id, uv_array)

        self.uvs_changed = True

    def copy_uvs(self, uv_set_id):

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        self._copied_uv_array = GeomVertexArrayData(vertex_data.get_array(4 + uv_set_id))
        self._copied_uv_mats = [Mat4(mat) for mat in self.uv_mats[uv_set_id]]

    def paste_uvs(self, uv_set_id):

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(4 + uv_set_id, self._copied_uv_array)
        vertex_data = self._selected_geom.node().modify_geom(0).modify_vertex_data()
        vertex_data.set_array(4 + uv_set_id, self._copied_uv_array)
        self.uv_mats[uv_set_id] = [Mat4(mat) for mat in self._copied_uv_mats]

        if uv_set_id == 0:

            model = self.model

            if model.has_tangent_space():
                model.update_tangent_space()
            else:
                self.is_tangent_space_initialized = False

            material = model.get_material()

            if material:

                vert_color_map = material.get_tex_map("vertex color")
                texture = vert_color_map.get_texture()

                if vert_color_map.active and texture:
                    self.bake_texture(texture)

        self.uvs_changed = True

    def reset_default_part_uvs(self, uv_set_id):
        """
        Reset the UVs of the selected, distinct parts of the model primitive
        to their default values.

        """

        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()
        uv_view1 = memoryview(vertex_data.modify_array(4 + uv_set_id)).cast("B").cast("f")
        vertex_data = self._selected_geom.node().modify_geom(0).modify_vertex_data()
        uv_view2 = memoryview(vertex_data.modify_array(4 + uv_set_id)).cast("B").cast("f")
        sel_parts = self.get_selected_parts()

        if not sel_parts:
            return

        uv_mats = self.uv_mats[uv_set_id]

        for part in sel_parts:
            start_row, end_row = part.data_row_range
            default_uvs = self.default_uvs[start_row*2:end_row*2]
            uv_view1[start_row*2:end_row*2] = default_uvs
            uv_view2[start_row*2:end_row*2] = default_uvs
            uv_mats[self._parts.index(part)] = Mat4(Mat4.ident_mat())

        self.uvs_changed = True

    def get_uvs(self):

        uv_values = []
        vertex_data = self.geom.node().get_geom(0).get_vertex_data()

        for i in range(8):
            uv_array = vertex_data.get_array(4 + i)
            uv_view = memoryview(uv_array).cast("B").cast("f")
            uv_values.append(array.array("f", uv_view))

        return (uv_values, self.uv_mats)

    def set_uvs(self, uv_data):

        uvs, self.uv_mats = uv_data
        vertex_data = self.geom.node().modify_geom(0).modify_vertex_data()

        for i in range(8):
            uv_array = vertex_data.modify_array(4 + i)
            uv_view = memoryview(uv_array).cast("B").cast("f")
            uv_view[:] = uvs[i]

    def get_uv_set_names(self):

        # for backward compatibility
        if not hasattr(self, "_uv_set_names"):
            return ["", "1", "2", "3", "4", "5", "6", "7"]

        return self._uv_set_names

    def set_uv_set_names(self, uv_set_names):

        if self._uv_set_names == uv_set_names:
            return False

        self._uv_set_names = uv_set_names

        return True

    def update_render_mode(self, is_selected):

        if not self.geom:
            return

        LockedGeomBase.update_render_mode(self, is_selected)

        if hasattr(self, "_parts") and not self._parts_shown:
            if "shaded" in GD["render_mode"]:
                self._selected_geom.show(Mgr.get("render_mask"))
            else:
                self._selected_geom.hide(Mgr.get("render_mask"))

    def set_two_sided(self, two_sided=True):

        LockedGeomBase.set_two_sided(self, two_sided)

        if hasattr(self, "_parts"):
            self._seams_geom.set_shader_input("two_sided", two_sided)

    def update_poly_centers(self):

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        pos_array = vertex_data.get_array(0)
        pos_view = memoryview(pos_array).cast("B").cast("f")
        snap_values = array.array("f", [])
        i = 0

        for poly in self.geom_data:
            s = len(poly["verts"])
            pos = tuple(sum((Point3(*pos_view[i+j*3:i+(j+1)*3]) for j in range(s)), Point3()) / s)
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

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        pos_array = vertex_data.get_array(0)
        pos_view = memoryview(pos_array).cast("B").cast("f")
        i = 0

        for p in self.geom_data:
            for v in p["verts"]:
                v["pos"][:] = pos_view[i:i+3]
                i += 3

    def update_uv_coordinates(self):
        """
        Replace the initial UV coordinates with their current values.

        """

        vertex_data = self.geom.node().get_geom(0).get_vertex_data()
        uv_views = []

        for uv_set_id in range(8):
            uv_view = memoryview(vertex_data.get_array(4 + uv_set_id)).cast("B").cast("f")
            uv_views.append(uv_view)

        i = 0

        for p in self.geom_data:
            for v in p["verts"]:
                uvs = v["uvs"]
                for uv_set_id, uv_view in enumerate(uv_views):
                    uvs[uv_set_id] = tuple(uv_view[i:i+2])
                i += 2

    def get_subdivision_data(self):

        self.update_vertex_positions()
        self.update_uv_coordinates()
        self.__define_indices()

        return LockedGeomBase.get_subdivision_data(self)

    def unlock_geometry(self, unlocked_geom, update_normal_data=False):

        self.update_vertex_positions()
        self.update_uv_coordinates()
        LockedGeomBase.unlock_geometry(self, unlocked_geom, update_normal_data)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "inverted_geom":
            return self.has_inverted_geometry()
        elif prop_id == "uv_set_names":
            return self._uv_set_names
        elif prop_id == "uvs":
            return self.get_uvs()

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "inverted_geom":
            Mgr.update_remotely("selected_obj_prop", "locked_geom", prop_id, value)
            return self.invert_geometry(value)
        elif prop_id == "uv_set_names":
            return self.set_uv_set_names(value)
        elif prop_id == "uvs":
            task = lambda: self.set_uvs(value)
            task_id = "set_uvs"
            PendingTasks.add(task, task_id, "object", id_prefix=self.model.id)


class PrimitiveManager(CreationPhaseManager, ObjPropDefaultsManager, LockedGeomManagerBase):

    pickable_part_vertex_format = None
    uv2_format = None
    uv3_format = None

    @staticmethod
    def define_vertex_formats():

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        vertex_format.add_array(array_format)
        array_format = GeomVertexArrayFormat()
        # provide a color column for the purpose of picking distinct parts of model primitives
        # in the UV interface
        array_format.add_column(InternalName.make("color"), 4, Geom.NT_uint8, Geom.C_color)
        vertex_format.add_array(array_format)
        array_format = GeomVertexArrayFormat()
        # provide an index column for the purpose of region-selecting distinct parts of model
        # primitives in the UV interface
        array_format.add_column(InternalName.make("index"), 1, Geom.NT_int32, Geom.C_index)
        vertex_format.add_array(array_format)
        PrimitiveManager.pickable_part_vertex_format = GeomVertexFormat.register_format(vertex_format)

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("texcoord"), 2,
            Geom.NT_float32, Geom.C_texcoord)
        vertex_format.add_array(array_format)

        for uv_set_id in range(1, 8):
            array_format = GeomVertexArrayFormat()
            array_format.add_column(InternalName.make(f"texcoord.{uv_set_id}"), 2,
                Geom.NT_float32, Geom.C_texcoord)
            vertex_format.add_array(array_format)

        PrimitiveManager.uv2_format = GeomVertexFormat.register_format(vertex_format)

        vertex_format = GeomVertexFormat()
        array_format = GeomVertexArrayFormat()
        array_format.add_column(InternalName.make("texcoord"), 3,
            Geom.NT_float32, Geom.C_point)
        vertex_format.add_array(array_format)

        for uv_set_id in range(1, 8):
            array_format = GeomVertexArrayFormat()
            array_format.add_column(InternalName.make(f"texcoord.{uv_set_id}"), 3,
                Geom.NT_float32, Geom.C_point)
            vertex_format.add_array(array_format)

        PrimitiveManager.uv3_format = GeomVertexFormat.register_format(vertex_format)

    def __init__(self, prim_type, custom_creation=False):

        CreationPhaseManager.__init__(self, prim_type, has_color=True)
        ObjPropDefaultsManager.__init__(self, prim_type)
        LockedGeomManagerBase.__init__(self)
        PickableTypes.add("primitive_part")

        if not self.pickable_part_vertex_format:
            self.define_vertex_formats()

        Mgr.accept(f"create_{prim_type}", self.__create)
        Mgr.accept("transform_primitive_uvs", self.__transform_uvs)

        if custom_creation:
            Mgr.accept(f"create_custom_{prim_type}", self.create_custom_primitive)

    def setup(self, creation_phases, status_text):

        phase_data = creation_phases.pop(0)

        if len(phase_data) == 3:
            phase_starter, phase_handler, phase_finisher = phase_data
        else:
            phase_starter, phase_handler = phase_data
            phase_finisher = lambda: None

        creation_starter = lambda: self.__start_primitive_creation(phase_starter)
        creation_phases.insert(0, (creation_starter, phase_handler, phase_finisher))

        return CreationPhaseManager.setup(self, creation_phases, status_text)

    def __start_primitive_creation(self, main_creation_func):

        if not self.get_object():
            next_color = self.get_next_object_color()
            tmp_prim = self.create_temp_primitive(next_color, self.get_origin_pos())
            self.init_object(tmp_prim)

        main_creation_func()

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

    def __transform_uvs(self, vertex_data, uv_set_id, mat, rows=None):

        if mat.is_identity():
            return

        uv2_data = GeomVertexData("uv", self.uv2_format, Geom.UH_dynamic)
        uv2_data.unclean_set_num_rows(vertex_data.get_num_rows())
        uv_array = vertex_data.get_array(4 + uv_set_id)
        uv2_data.set_array(uv_set_id, uv_array)
        uv3_data = GeomVertexData(uv2_data.convert_to(self.uv3_format))

        if rows is None:
            uv3_data.transform_vertices(mat)
        else:
            uv3_data.transform_vertices(mat, rows)

        uv2_data = uv3_data.convert_to(self.uv2_format)
        uv_array = uv2_data.get_array(uv_set_id)
        vertex_data.set_array(4 + uv_set_id, uv_array)

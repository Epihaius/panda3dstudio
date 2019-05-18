from .base import *


class ExportManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("export", self.__update_export)

    def __merge_duplicate_vertices(self, geom_data_obj):

        verts = geom_data_obj.get_subobjects("vert")
        merged_verts = set(geom_data_obj.get_merged_vertex(v_id) for v_id in verts)
        rows = list(range(len(verts)))
        dupes = {}

        for merged_vert in merged_verts:

            verts1 = [verts[v_id] for v_id in merged_vert]
            verts2 = verts1[:]

            for vert1 in verts1:

                pos1 = vert1.get_pos()
                normal1 = vert1.get_normal()
                uv1 = vert1.get_uvs()
                col1 = vert1.get_color()
                row1 = vert1.get_row_index()

                if row1 in dupes:
                    continue

                for vert2 in verts2[:]:

                    if vert2 is vert1:
                        continue

                    pos2 = vert2.get_pos()
                    normal2 = vert2.get_normal()
                    uv2 = vert2.get_uvs()
                    col2 = vert2.get_color()

                    if pos2 == pos1 and normal2 == normal1 and uv2 == uv1 and col2 == col1:
                        row2 = vert2.get_row_index()
                        rows.remove(row2)
                        verts2.remove(vert2)
                        dupes[row2] = row1

        geom = geom_data_obj.get_toplevel_node().get_geom(0)
        vdata_src = geom.get_vertex_data()
        vdata_dest = GeomVertexData(vdata_src)
        vdata_dest.unclean_set_num_rows(len(rows))
        thread = Thread.get_main_thread()

        for row_dest, row_src in enumerate(rows):
            vdata_dest.copy_row_from(row_dest, vdata_src, row_src, thread)

        for row2, row1 in list(dupes.items()):
            dupes[row2] = rows.index(row1)

        prim_src = geom.get_primitive(0)
        prim_dest = GeomTriangles(Geom.UH_static)
        rows_src = prim_src.get_vertex_list()
        rows_dest = [dupes[row] if row in dupes else rows.index(row) for row in rows_src]

        for indices in (rows_dest[i:i + 3] for i in range(0, len(rows_dest), 3)):
            prim_dest.add_vertices(*indices)

        geom_dest = Geom(vdata_dest)
        geom_dest.add_primitive(prim_dest)
        geom_node = GeomNode("")
        geom_node.add_geom(geom_dest)

        return NodePath(geom_node)

    def __update_vertex_format(self, node, uv_set_names, tex_stages):

        default_uv_names = ["", "1", "2", "3", "4", "5", "6", "7"]
        stages_by_uv_name = {}

        if uv_set_names != default_uv_names:

            for tex_stage in tex_stages:
                internal_name = tex_stage.get_texcoord_name()
                uv_name = internal_name.get_name()
                uv_name = "" if uv_name == "texcoord" else internal_name.get_basename()
                stages_by_uv_name.setdefault(uv_name, []).append(tex_stage)

        main_array = GeomVertexArrayFormat()
        main_array.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        main_array.add_column(InternalName.get_color(), 1, Geom.NT_packed_dabc, Geom.C_color)
        main_array.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        main_array.add_column(InternalName.get_tangent(), 3, Geom.NT_float32, Geom.C_vector)
        main_array.add_column(InternalName.get_binormal(), 3, Geom.NT_float32, Geom.C_vector)
        uv_arrays = []
        internal_uv_names = []

        for default_name, uv_name in zip(default_uv_names, uv_set_names):

            if uv_name == "":
                internal_name = InternalName.get_texcoord()
            else:
                internal_name = InternalName.get_texcoord_name(uv_name)

            uv_array = GeomVertexArrayFormat()
            uv_array.add_column(internal_name, 2, Geom.NT_float32, Geom.C_texcoord)
            uv_arrays.append(uv_array)
            internal_uv_names.append(internal_name)

            if uv_name != default_name and default_name in stages_by_uv_name:
                for tex_stage in stages_by_uv_name[default_name]:
                    tex_stage.set_texcoord_name(uv_name)

        vertex_data = node.node().modify_geom(0).modify_vertex_data()

        if uv_set_names != default_uv_names:

            vertex_format = GeomVertexFormat()
            vertex_format.add_array(main_array)

            for uv_array in uv_arrays:
                vertex_format.add_array(uv_array)

            vertex_format = GeomVertexFormat.register_format(vertex_format)
            new_vertex_data = vertex_data.convert_to(vertex_format)
            node.node().modify_geom(0).set_vertex_data(new_vertex_data)
            new_vertex_data = node.node().modify_geom(0).modify_vertex_data()

            for i in range(8):
                from_array = vertex_data.get_array(4 + i)
                from_view = memoryview(from_array).cast("B")
                to_array = new_vertex_data.modify_array(1 + i)
                to_view = memoryview(to_array).cast("B")
                to_view[:] = from_view

            vertex_data = new_vertex_data

        array = GeomVertexArrayFormat(main_array)

        for internal_name in internal_uv_names:
            array.add_column(internal_name, 2, Geom.NT_float32, Geom.C_texcoord)

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array)

        vertex_format = GeomVertexFormat.register_format(vertex_format)
        new_vertex_data = vertex_data.convert_to(vertex_format)
        node.node().modify_geom(0).set_vertex_data(new_vertex_data)

    def __prepare_export(self):

        if Mgr.get("selection_top"):
            Mgr.update_remotely("export", "export")
        elif Mgr.get("objects"):
            Mgr.update_remotely("export", "confirm_entire_scene")
        else:
            Mgr.update_remotely("export", "empty_scene")

    def __export_to_bam(self, filename):

        objs = set(obj.get_root() for obj in Mgr.get("selection_top"))

        if not objs:
            objs = set(obj.get_root() for obj in Mgr.get("objects"))

        root = NodePath(ModelRoot(os.path.basename(filename)))
        fullpath = Filename.from_os_specific(filename)
        directory = Filename(fullpath.get_dirname())

        child_geom_nodes = {}
        child_collision_nodes = {}
        data = [(objs, root, None, None)]

        while data:

            children, parent_node, geom_node, collision_node = data.pop()

            for child in children:

                child_geom_node = None
                child_collision_node = None
                child_is_group = child.get_type() == "group"

                if child.get_type() == "model":

                    geom_obj = child.get_geom_object()
                    geom_type = child.get_geom_type()

                    if geom_type == "basic_geom":

                        node = NodePath(geom_obj.get_geom().node().make_copy())
                        uv_set_names = geom_obj.get_uv_set_names()

                        for key in node.get_tag_keys():
                            node.clear_tag(key)

                    else:

                        geom_data_obj = geom_obj.get_geom_data_object()
                        node = self.__merge_duplicate_vertices(geom_data_obj)
                        uv_set_names = geom_data_obj.get_uv_set_names()

                        if geom_obj.has_flipped_normals():
                            node.node().modify_geom(0).reverse_in_place()

                    masks = Mgr.get("render_mask") | Mgr.get("picking_masks")
                    node.show(masks)

                    origin = child.get_origin()
                    pivot = child.get_pivot()
                    node.set_name(child.get_name())
                    node.set_state(origin.get_state())

                    tex_stages = node.find_all_texture_stages()
                    self.__update_vertex_format(node, uv_set_names, tex_stages)

                    # make texture filenames relative to the model directory
                    for tex_stage in tex_stages:
                        texture = node.get_texture(tex_stage).make_copy()
                        filename = Filename(texture.get_fullpath())
                        filename.make_relative_to(directory)
                        texture.set_filename(filename)
                        texture.set_fullpath(filename)
                        filename = Filename(texture.get_alpha_fullpath())
                        filename.make_relative_to(directory)
                        texture.set_alpha_filename(filename)
                        texture.set_alpha_fullpath(filename)
                        node.set_texture(tex_stage, texture)

                    parent = child.get_parent()

                    if parent and parent.get_type() != "model":
                        parent = None

                    material = child.get_material()
                    parent_material = parent.get_material() if parent else None
                    parent_origin = parent.get_origin() if parent else None

                    if material and parent_material and material.equals(parent_material):

                        node.set_state(RenderState.make_empty())

                    else:

                        if material and not material.has_base_properties():
                            node.clear_material()

                        if not material:
                            node.clear_color()

                        if origin.get_transparency() == TransparencyAttrib.M_none:
                            node.clear_transparency()
                            node.clear_color_scale()

                        if parent_material:

                            if parent_origin.has_color() and not node.has_color():
                                state = node.get_state()
                                attr = ColorAttrib.make_off()
                                state = state.add_attrib(attr)
                                node.set_state(state)

                            if parent_origin.has_color_scale() and not node.has_color_scale():
                                node.set_color_scale_off()

                            if parent_origin.has_material() and not node.has_material():
                                node.set_material_off()

                            tex_stages = parent_origin.find_all_texture_stages()

                            for tex_stage in tex_stages:
                                if parent_origin.has_texture(tex_stage) and not node.has_texture(tex_stage):
                                    node.set_texture_off(tex_stage)

                            if parent_material.get_base_properties()["alpha"]["on"]:
                                if not node.has_transparency():
                                    node.set_transparency(TransparencyAttrib.M_none)

                    mat = origin.get_mat(pivot)
                    vertex_data = node.node().modify_geom(0).modify_vertex_data()
                    vertex_data.transform_vertices(mat)
                    node.set_transform(pivot.get_transform(parent_node))
                    node.node().copy_tags(origin.node())

                    if geom_node:

                        state = node.get_state()
                        geom = node.node().modify_geom(0)
                        mat = pivot.get_mat(child.get_parent_pivot())
                        vertex_data = geom.modify_vertex_data()
                        vertex_data.transform_vertices(mat)
                        geom_node.add_geom(geom, state)
                        node = parent_node

                    elif collision_node:

                        # collision solids must be scaled uniformly
                        scale = pivot.get_scale()
                        sx = scale[0]
                        pivot.set_scale(sx)
                        group_pivot = child.get_group().get_pivot()
                        coll_solid = None

                        if geom_type == "sphere":

                            center = origin.get_pos(group_pivot)
                            radius = geom_obj.get_property("radius") * sx

                            if geom_obj.has_flipped_normals():
                                coll_solid = CollisionInvSphere(center, radius)
                            else:
                                coll_solid = CollisionSphere(center, radius)

                        elif geom_type == "cylinder":

                            pos = origin.get_pos()
                            height_vec = Vec3.up() * geom_obj.get_property("height")
                            height_vec = pivot.get_relative_vector(origin, height_vec)
                            point_a = group_pivot.get_relative_point(pivot, pos)
                            point_b = group_pivot.get_relative_point(pivot, pos + height_vec)
                            radius = geom_obj.get_property("radius") * sx
                            coll_solid = CollisionCapsule(point_a, point_b, radius)

                        elif geom_type == "box":

                            pos = origin.get_pos(group_pivot)
                            size_x = geom_obj.get_property("size_x") * .5
                            size_y = geom_obj.get_property("size_y") * .5
                            height = geom_obj.get_property("size_z") * .5
                            size_z = abs(height)
                            height_vec = group_pivot.get_relative_vector(origin, Vec3.up() * height)
                            center = pos + height_vec

                            if geom_obj.has_flipped_normals():

                                # an inverted Box is exported as 6 CollisionPlanes
                                x_vec = group_pivot.get_relative_vector(origin, Vec3.right() * size_x)
                                y_vec = group_pivot.get_relative_vector(origin, Vec3.forward() * size_y)
                                z_vec = group_pivot.get_relative_vector(origin, Vec3.up() * size_z)

                                for vec in (x_vec, y_vec, z_vec):
                                    normal = vec.normalized()
                                    collision_node.add_solid(CollisionPlane(Plane(-normal, center + vec)))
                                    collision_node.add_solid(CollisionPlane(Plane(normal, center - vec)))

                            else:

                                # note that a CollisionBox cannot be rotated
                                coll_solid = CollisionBox(center, size_x * sx, size_y * sx, size_z * sx)

                        elif geom_type == "plane":

                            normal = Vec3.down() if geom_obj.has_flipped_normals() else Vec3.up()
                            normal = group_pivot.get_relative_vector(origin, normal)
                            point = origin.get_pos(group_pivot)
                            coll_solid = CollisionPlane(Plane(normal, point))

                        else:

                            # CollisionPolygons can be scaled non-uniformly
                            pivot.set_scale(scale)

                            if geom_type == "basic_geom":

                                mat = pivot.get_mat(group_pivot)
                                geom = node.node().modify_geom(0)
                                vertex_data = geom.modify_vertex_data()
                                vertex_data.transform_vertices(mat)
                                pos_reader = GeomVertexReader(vertex_data, "vertex")
                                index_list = geom.get_primitive(0).get_vertex_list()
                                index_count = len(index_list)

                                for indices in (index_list[i:i+3] for i in range(0, len(index_list), 3)):

                                    points = []

                                    for index in indices:
                                        pos_reader.set_row(index)
                                        points.append(pos_reader.get_data3())

                                    coll_poly = CollisionPolygon(*points)
                                    collision_node.add_solid(coll_poly)

                            else:

                                polys = iter(geom_data_obj.get_subobjects("poly").values())
                                verts = geom_data_obj.get_subobjects("vert")
                                epsilon = 1.e-005

                                for poly in polys:

                                    is_quad = False

                                    if poly.get_vertex_count() == 4:

                                        is_quad = True
                                        is_planar = False
                                        tri_vert_ids = poly[0]
                                        tri_verts = (verts[v_id] for v_id in tri_vert_ids)
                                        points = [v.get_pos(group_pivot) for v in tri_verts]

                                        for i, v_id in enumerate(poly[1]):
                                            if v_id not in tri_vert_ids:
                                                point = verts[v_id].get_pos(group_pivot)
                                                preceding_v_id = poly[1][i - 1]
                                                index = tri_vert_ids.index(preceding_v_id) + 1
                                                break

                                        if abs(Plane(*points).dist_to_plane(point)) < epsilon:
                                            points.insert(index, point)
                                            is_planar = True

                                        coll_poly = CollisionPolygon(*points)
                                        collision_node.add_solid(coll_poly)

                                        if is_planar:
                                            continue

                                    for tri_vert_ids in poly[1 if is_quad else 0:]:
                                        tri_verts = (verts[v_id] for v_id in tri_vert_ids)
                                        points = [v.get_pos(group_pivot) for v in tri_verts]
                                        coll_poly = CollisionPolygon(*points)
                                        collision_node.add_solid(coll_poly)

                        if coll_solid:
                            collision_node.add_solid(coll_solid)

                        pivot.set_scale(scale)
                        node = parent_node

                    else:

                        node.reparent_to(parent_node)

                else:

                    if child_is_group and child.get_member_types_id() == "model":
                        child_geom_node = GeomNode(child.get_name())
                        child_geom_nodes[child.get_name()] = child_geom_node
                        node = parent_node.attach_new_node(child_geom_node)
                    elif child_is_group and child.get_member_types_id() == "collision":
                        child_collision_node = CollisionNode(child.get_name())
                        child_collision_nodes[child.get_name()] = child_collision_node
                        node = parent_node.attach_new_node(child_collision_node)
                    else:
                        node = parent_node.attach_new_node(child.get_name())

                    node.set_transform(child.get_pivot().get_transform(child.get_parent_pivot()))
                    node.node().copy_tags(child.get_origin().node())

                if child_is_group:
                    data.append((child.get_members(), node, child_geom_node, child_collision_node))

                if child.get_children():
                    data.append((child.get_children(), node, None, None))

        for name, child_geom_node in child_geom_nodes.items():
            if child_geom_node.get_num_geoms() == 0:
                PandaNode(name).replace_node(child_geom_node)

        for name, child_collision_node in child_collision_nodes.items():
            if child_collision_node.get_num_solids() == 0:
                PandaNode(name).replace_node(child_collision_node)

        root.write_bam_file(fullpath)
        root.remove_node()

    def __export_to_obj(self, filename):

        objs = list(set(obj.get_root() for obj in Mgr.get("selection_top")))

        if not objs:
            return

        material_data = {}
        flat_color_index = 0
        row_offset = 1
        namelist = []

        with open(filename, "w") as obj_file:

            obj_file.write("# Created with Panda3D Studio\n\n")
            fname = os.path.basename(filename)
            mtllib_name = os.path.splitext(fname)[0]
            obj_file.write("mtllib {}.mtl\n".format(mtllib_name))

            while objs:

                obj = objs.pop()

                if obj.get_type() == "model":

                    name = get_unique_name(obj.get_name().replace(" ", "_"), namelist)
                    namelist.append(name)
                    obj_file.write("\ng {}\n\n".format(name))

                    geom_obj = obj.get_geom_object()

                    if obj.get_geom_type() == "basic_geom":

                        node = NodePath(geom_obj.get_geom().node().make_copy())

                    else:

                        geom_data_obj = geom_obj.get_geom_data_object()
                        node = NodePath(geom_data_obj.get_toplevel_geom().node().make_copy())

                        if geom_obj.has_flipped_normals():
                            node.node().modify_geom(0).reverse_in_place()

                    material = obj.get_material()

                    if material:

                        material_name = material.get_name()

                        if not material_name:
                            material_name = "<Unnamed>"

                        if material in material_data:

                            material_alias = material_data[material]["alias"]

                        else:

                            data = {}
                            material_data[material] = data
                            material_alias = "material_{:03d}".format(len(material_data))
                            data["name"] = material_name
                            data["alias"] = material_alias
                            data["is_flat_color"] = False
                            base_material = material.get_base_material()
                            dif = base_material.get_diffuse() if base_material.has_diffuse() \
                                else material.get_flat_color()
                            data["diffuse"] = dif
                            alpha = material.get_base_properties()["alpha"]

                            if alpha["on"]:
                                data["dissolve"] = alpha["value"]

                            color_map = material.get_tex_map("color")

                            if color_map.is_active() and color_map.get_texture():

                                rgb_filename, alpha_filename = color_map.get_tex_filenames()
                                data["diffuse_map"] = os.path.basename(rgb_filename)

                                if alpha_filename:
                                    data["dissolve_map"] = os.path.basename(alpha_filename)

                    else:

                        color = (1., 1., 1., 1.)

                        if color in material_data:
                            material_name = material_data[color]["name"]
                            material_alias = material_data[color]["alias"]
                        else:
                            flat_color_index += 1
                            material_name = "Flat color {:d}".format(flat_color_index)
                            data = {}
                            material_data[color] = data
                            data["name"] = material_name
                            material_alias = "material_{:03d}".format(len(material_data))
                            data["alias"] = material_alias
                            data["is_flat_color"] = True

                    vertex_data = node.node().modify_geom(0).modify_vertex_data()
                    convert_mat = Mat4.convert_mat(CS_default, CS_yup_right)
                    origin = obj.get_origin()
                    mat = origin.get_net_transform().get_mat() * convert_mat
                    vertex_data.transform_vertices(mat)
                    pos_reader = GeomVertexReader(vertex_data, "vertex")
                    uv_reader = GeomVertexReader(vertex_data, "texcoord")
                    normal_reader = GeomVertexReader(vertex_data, "normal")
                    row_count = vertex_data.get_num_rows()

                    for i in range(row_count):
                        x, y, z = pos_reader.get_data3()
                        u, v = uv_reader.get_data2()
                        xn, yn, zn = normal_reader.get_data3()
                        obj_file.write("v {:.6f} {:.6f} {:.6f}\n".format(x, y, z))
                        obj_file.write("vt {:.6f} {:.6f}\n".format(u, v))
                        obj_file.write("vn {:.6f} {:.6f} {:.6f}\n".format(xn, yn, zn))

                    obj_file.write("\nusemtl {}\n".format(material_alias))
                    obj_file.write("# {}\n".format(material_name))

                    index_list = node.node().get_geom(0).get_primitive(0).get_vertex_list()
                    index_count = len(index_list)

                    for i in range(0, index_count, 3):
                        i1, i2, i3 = [j + row_offset for j in index_list[i:i+3]]
                        indices = (i1, i1, i1, i2, i2, i2, i3, i3, i3)
                        obj_file.write("f {:d}/{:d}/{:d} {:d}/{:d}/{:d} {:d}/{:d}/{:d}\n".format(*indices))

                    row_offset += row_count

                if obj.get_type() == "group":
                    children = obj.get_members()
                else:
                    children = obj.get_children()

                if children:
                    objs.extend(children)

        mtllib_fname = os.path.splitext(filename)[0] + ".mtl"

        with open(mtllib_fname, "w") as mtl_file:

            mtl_file.write("# Created with Panda3D Studio\n\n")

            for material, data in material_data.items():

                material_alias = data["alias"]
                mtl_file.write("\n\nnewmtl {}\n".format(material_alias))
                material_name = data["name"]
                mtl_file.write("# {}\n\n".format(material_name))
                r, g, b, a = material if data["is_flat_color"] else data["diffuse"]
                mtl_file.write("Kd {:.6f} {:.6f} {:.6f}\n".format(r, g, b))

                if "dissolve" in data:
                    mtl_file.write("d {:.6f}\n".format(data["dissolve"]))

                if "diffuse_map" in data:
                    mtl_file.write("map_Kd {}\n".format(data["diffuse_map"]))

                if "dissolve_map" in data:
                    mtl_file.write("map_d {}\n".format(data["dissolve_map"]))

    def __export(self, filename):

        ext = os.path.splitext(filename)[1]

        if ext == ".bam":
            self.__export_to_bam(filename)
        elif ext == ".obj":
            self.__export_to_obj(filename)

    def __update_export(self, update_type, *args):

        if update_type == "prepare":
            self.__prepare_export()
        elif update_type == "export":
            self.__export(*args)


MainObjects.add_class(ExportManager)

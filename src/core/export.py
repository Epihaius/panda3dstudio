from .base import *


class ExportManager(BaseObject):

    def __init__(self):

        Mgr.add_app_updater("export", self.__export)

    def __merge_duplicate_vertices(self, geom_data_obj):

        verts = geom_data_obj.get_subobjects("vert")
        merged_verts = set(geom_data_obj.get_merged_vertex(v_id) for v_id in verts)
        rows = range(len(verts))
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

        for row2, row1 in dupes.items():
            dupes[row2] = rows.index(row1)

        prim_src = geom.get_primitive(0)
        prim_dest = GeomTriangles(Geom.UH_static)
        rows_src = prim_src.get_vertex_list()
        rows_dest = [dupes[row] if row in dupes else rows.index(row) for row in rows_src]

        for indices in (rows_dest[i:i + 3] for i in xrange(0, len(rows_dest), 3)):
            prim_dest.add_vertices(*indices)

        geom_dest = Geom(vdata_dest)
        geom_dest.add_primitive(prim_dest)
        geom_node = GeomNode("")
        geom_node.add_geom(geom_dest)

        return NodePath(geom_node)

    def __prepare_export_to_bam(self, parent, children, directory, geom_node=None,
                                collision_node=None):

        for child in children:

            child_geom_node = None
            child_collision_node = None
            child_is_group = child.get_type() == "group"

            if child.get_type() == "model":

                geom_obj = child.get_geom_object()
                geom_type = child.get_geom_type()

                if geom_type == "basic_geom":

                    node = NodePath(geom_obj.get_geom().node().make_copy())

                    for key in node.get_tag_keys():
                        node.clear_tag(key)

                else:

                    geom_data_obj = geom_obj.get_geom_data_object()
                    node = self.__merge_duplicate_vertices(geom_data_obj)
                    masks = Mgr.get("render_masks")["all"] | Mgr.get("picking_masks")["all"]
                    node.show(masks)

                origin = child.get_origin()
                pivot = child.get_pivot()
                node.set_name(child.get_name())
                node.set_state(origin.get_state())
                material = child.get_material()

                if material and not material.has_base_properties():
                    node.clear_material()

                if not material:
                    node.clear_color()

                if origin.get_transparency() == TransparencyAttrib.M_none:
                    node.clear_transparency()
                    node.clear_color_scale()

                mat = origin.get_mat(pivot)
                vertex_data = node.node().modify_geom(0).modify_vertex_data()
                vertex_data.transform_vertices(mat)
                node.set_transform(pivot.get_transform(parent))
                node.node().copy_tags(origin.node())

                tex_stages = node.find_all_texture_stages()

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

                if geom_node:

                    state = node.get_state()
                    geom = node.node().modify_geom(0)
                    mat = pivot.get_mat(child.get_parent_pivot())
                    vertex_data = geom.modify_vertex_data()
                    vertex_data.transform_vertices(mat)
                    geom_node.add_geom(geom, state)
                    node = parent

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
                        coll_solid = CollisionSphere(center, radius)

                    elif geom_type == "cylinder":

                        pos = origin.get_pos()
                        height_vec = Vec3.up() * geom_obj.get_property("height")
                        height_vec = pivot.get_relative_vector(origin, height_vec)
                        point_a = group_pivot.get_relative_point(pivot, pos)
                        point_b = group_pivot.get_relative_point(pivot, pos + height_vec)
                        radius = geom_obj.get_property("radius") * sx
                        coll_solid = CollisionTube(point_a, point_b, radius)

                    elif geom_type == "box":

                        # note that a CollisionBox cannot be rotated
                        pos = origin.get_pos()
                        size_x = geom_obj.get_property("size_x") * .5 * sx
                        size_y = geom_obj.get_property("size_y") * .5 * sx
                        height = geom_obj.get_property("size_z") * .5
                        size_z = abs(height) * sx
                        height_vec = Vec3.up() * height
                        height_vec = pivot.get_relative_vector(origin, height_vec)
                        center = group_pivot.get_relative_point(pivot, pos + height_vec)
                        coll_solid = CollisionBox(center, size_x, size_y, size_z)

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

                            for indices in (index_list[i:i+3] for i in xrange(0, len(index_list), 3)):

                                points = []

                                for index in indices:
                                    pos_reader.set_row(index)
                                    points.append(pos_reader.get_data3f())

                                coll_poly = CollisionPolygon(*points)
                                collision_node.add_solid(coll_poly)

                        else:

                            polys = geom_data_obj.get_subobjects("poly").itervalues()
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
                    node = parent

                else:

                    node.reparent_to(parent)

            else:

                if child_is_group and child.get_member_types_id() == "model":
                    child_geom_node = GeomNode(child.get_name())
                    node = parent.attach_new_node(child_geom_node)
                elif child_is_group and child.get_member_types_id() == "collision":
                    child_collision_node = CollisionNode(child.get_name())
                    node = parent.attach_new_node(child_collision_node)
                else:
                    node = parent.attach_new_node(child.get_name())

                node.set_transform(child.get_pivot().get_transform(child.get_parent_pivot()))
                node.node().copy_tags(child.get_origin().node())

            if child_is_group:

                self.__prepare_export_to_bam(node, child.get_members(), directory,
                                             child_geom_node, child_collision_node)

                if child_geom_node and child_geom_node.get_num_geoms() == 0:
                    PandaNode(child.get_name()).replace_node(child_geom_node)
                if child_collision_node and child_collision_node.get_num_solids() == 0:
                    PandaNode(child.get_name()).replace_node(child_collision_node)

            if child.get_children():
                self.__prepare_export_to_bam(node, child.get_children(), directory)

    def __export_to_bam(self, filename):

        objs = set(obj.get_root() for obj in Mgr.get("selection", "top"))

        if not objs:
            return

        root = NodePath(ModelRoot(os.path.basename(filename)))
        fullpath = Filename.from_os_specific(filename)
        directory = Filename(fullpath.get_dirname())
        self.__prepare_export_to_bam(root, objs, directory)

        root.write_bam_file(fullpath)
        root.remove_node()

    def __prepare_export_to_obj(self, obj_file, children, material_data,
                                counters, namelist):

        for child in children:

            if child.get_type() == "model":

                name = get_unique_name(child.get_name().replace(" ", "_"), namelist)
                namelist.append(name)
                obj_file.write("\ng %s\n\n" % name)

                geom_obj = child.get_geom_object()

                if child.get_geom_type() == "basic_geom":
                    node = NodePath(geom_obj.get_geom().node().make_copy())
                else:
                    geom_data_obj = geom_obj.get_geom_data_object()
                    node = NodePath(geom_data_obj.get_toplevel_geom().node().make_copy())

                material = child.get_material()

                if material:

                    material_name = material.get_name()

                    if not material_name:
                        material_name = "<Unnamed>"

                    if material in material_data:

                        material_alias = material_data[material]["alias"]

                    else:

                        data = {}
                        material_data[material] = data
                        material_alias = "material_%03d" % len(material_data)
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
                        counters["flat_color"] += 1
                        material_name = "Flat color %d" % counters["flat_color"]
                        data = {}
                        material_data[color] = data
                        data["name"] = material_name
                        material_alias = "material_%03d" % len(material_data)
                        data["alias"] = material_alias
                        data["is_flat_color"] = True

                vertex_data = node.node().modify_geom(0).modify_vertex_data()
                convert_mat = Mat4.convert_mat(CS_default, CS_yup_right)
                origin = child.get_origin()
                mat = origin.get_net_transform().get_mat() * convert_mat
                vertex_data.transform_vertices(mat)
                pos_reader = GeomVertexReader(vertex_data, "vertex")
                uv_reader = GeomVertexReader(vertex_data, "texcoord")
                normal_reader = GeomVertexReader(vertex_data, "normal")
                row_count = vertex_data.get_num_rows()
                row_offset = counters["row_offset"]

                for i in xrange(row_count):
                    x, y, z = pos_reader.get_data3f()
                    u, v = uv_reader.get_data2f()
                    xn, yn, zn = normal_reader.get_data3f()
                    obj_file.write("v %.6f %.6f %.6f\n" % (x, y, z))
                    obj_file.write("vt %.6f %.6f\n" % (u, v))
                    obj_file.write("vn %.6f %.6f %.6f\n" % (xn, yn, zn))

                obj_file.write("\nusemtl %s\n" % material_alias)
                obj_file.write("# %s\n" % material_name)

                index_list = node.node().get_geom(0).get_primitive(0).get_vertex_list()
                index_count = len(index_list)

                for i in xrange(0, index_count, 3):
                    i1, i2, i3 = [j + row_offset for j in index_list[i:i+3]]
                    indices = (i1, i1, i1, i2, i2, i2, i3, i3, i3)
                    obj_file.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % indices)

                counters["row_offset"] += row_count

            if child.get_children():
                self.__prepare_export_to_obj(obj_file, child.get_children(),
                                             material_data, counters, namelist)

    def __export_to_obj(self, filename):

        objs = set(obj.get_root() for obj in Mgr.get("selection", "top"))

        if not objs:
            return

        material_data = {}
        counters = {"flat_color": 0, "row_offset": 1}

        with open(filename, "w") as obj_file:

            obj_file.write("# Created with Panda3D Studio\n\n")
            fname = os.path.basename(filename)
            mtllib_name = os.path.splitext(fname)[0]
            obj_file.write("mtllib %s.mtl\n" % mtllib_name)
            self.__prepare_export_to_obj(obj_file, objs, material_data,
                                         counters, [])

        mtllib_fname = os.path.splitext(filename)[0] + ".mtl"

        with open(mtllib_fname, "w") as mtl_file:

            mtl_file.write("# Created with Panda3D Studio\n\n")

            for material, data in material_data.iteritems():

                material_alias = data["alias"]
                mtl_file.write("\n\nnewmtl %s\n" % material_alias)
                material_name = data["name"]
                mtl_file.write("# %s\n\n" % material_name)
                r, g, b, a = material if data["is_flat_color"] else data["diffuse"]
                mtl_file.write("Kd %.6f %.6f %.6f\n" % (r, g, b))

                if "dissolve" in data:
                    mtl_file.write("d %.6f\n" % data["dissolve"])

                if "diffuse_map" in data:
                    mtl_file.write("map_Kd %s\n" % data["diffuse_map"])

                if "dissolve_map" in data:
                    mtl_file.write("map_d %s\n" % data["dissolve_map"])

    def __export(self, filename):

        ext = os.path.splitext(filename)[1]

        if ext == ".bam":
            self.__export_to_bam(filename)
        elif ext == ".obj":
            self.__export_to_obj(filename)


MainObjects.add_class(ExportManager)

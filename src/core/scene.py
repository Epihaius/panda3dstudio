from .base import *


class SceneManager(BaseObject):

    def __init__(self):

        Mgr.set_global("unsaved_scene", False)

        self._handlers = {
            "reset": self.__reset,
            "load": self.__load,
            "save": self.__save,
            "export": self.__export,
            "import": self.__import,
        }
        Mgr.add_app_updater("scene", lambda handler_id, *args, **kwargs:
                            self._handlers[handler_id](*args, **kwargs))

    def __reset(self):

        Mgr.enter_state("selection_mode")

        for obj in Mgr.get("objects"):
            obj.destroy(add_to_hist=False)

        Mgr.do("reset_history")
        PendingTasks.remove("update_selection", "ui")
        task = lambda: Mgr.get("selection", "top").update_ui(force=True)
        PendingTasks.add(task, "update_selection", "ui")
        PendingTasks.handle(["object", "ui"], True)

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        if Mgr.get_global("render_mode") != "shaded":
            Mgr.set_global("render_mode", "shaded")
            Mgr.update_app("render_mode")

        if Mgr.get_global("object_links_shown"):
            Mgr.set_global("object_links_shown", False)
            Mgr.update_app("object_link_viz", False)

        if Mgr.get_global("transform_target_type") != "all":
            Mgr.set_global("transform_target_type", "all")
            Mgr.update_app("transform_target_type")

        Mgr.do("update_picking_col_id_ranges")
        Mgr.do("reset_cam_transform")
        Mgr.do("update_world_axes")
        Mgr.do("update_nav_gizmo")
        Mgr.update_app("coord_sys", "world")
        Mgr.update_app("transf_center", "sel_center")
        Mgr.update_app("active_grid_plane", "XY")
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", "select", "")

        Mgr.reset_globals()

        for transf_type in ("translate", "rotate", "scale"):
            constraints = Mgr.get_global("axis_constraints_%s" % transf_type)
            Mgr.update_app("axis_constraints", transf_type, constraints)

        for obj_type in Mgr.get("object_types"):
            Mgr.do("set_last_%s_obj_id" % obj_type, 0)

    def __load(self, filename):

        self.__reset()

        scene_file = Multifile()
        scene_file.open_read(Filename.from_os_specific(filename))
        scene_data_str = scene_file.read_subfile(scene_file.find_subfile("scene/data"))
        Mgr.do("load_history", scene_file)
        scene_file.close()
        scene_data = cPickle.loads(scene_data_str)

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            Mgr.do("set_last_%s_obj_id" % obj_type, scene_data[data_id])

        for transf_type in ("translate", "rotate", "scale"):
            constraints = scene_data["axis_constraints"][transf_type]
            Mgr.set_global("axis_constraints_%s" % transf_type, constraints)
            Mgr.update_app("axis_constraints", transf_type, constraints)

        transf_type = scene_data["active_transform_type"]
        Mgr.set_global("active_transform_type", transf_type)
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

        for x in ("coord_sys", "transf_center"):
            x_type = scene_data[x]["type"]
            obj = Mgr.get("object", scene_data[x]["obj_id"])
            name = obj.get_name() if obj else None
            Mgr.update_locally(x, x_type, obj)
            Mgr.update_remotely(x, x_type, name)

        self.cam.set_y(scene_data["cam"])
        Mgr.get(("cam", "target")).set_mat(scene_data["cam_target"])
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_world_axes")
        Mgr.do("update_nav_gizmo")
        active_grid_plane = scene_data["grid_plane"]
        Mgr.update_app("active_grid_plane", active_grid_plane)
        PendingTasks.handle(["object", "ui"], True)

    def __save(self, filename):

        scene_data = {}
        scene_data["cam"] = self.cam.get_y()
        scene_data["cam_target"] = Mgr.get(("cam", "target")).get_mat()
        scene_data["grid_plane"] = Mgr.get_global("active_grid_plane")

        for x in ("coord_sys", "transf_center"):
            scene_data[x] = {}
            scene_data[x]["type"] = Mgr.get_global("%s_type" % x)
            obj = Mgr.get("%s_obj" % x)
            scene_data[x]["obj_id"] = obj.get_id() if obj else None

        transf_type = Mgr.get_global("active_transform_type")
        scene_data["active_transform_type"] = transf_type
        scene_data["axis_constraints"] = {}

        for transf_type in ("translate", "rotate", "scale"):
            constraints = Mgr.get_global("axis_constraints_%s" % transf_type)
            scene_data["axis_constraints"][transf_type] = constraints

        for obj_type in Mgr.get("object_types"):
            data_id = "last_%s_obj_id" % obj_type
            scene_data[data_id] = Mgr.get(data_id)

        scene_file = Multifile()
        scene_file.open_write(Filename.from_os_specific(filename))
        scene_data_stream = StringStream(cPickle.dumps(scene_data, -1))
        scene_file.add_subfile("scene/data", scene_data_stream, 6)
        Mgr.do("save_history", scene_file)

        if scene_file.needs_repack():
            scene_file.repack()

        scene_file.flush()
        scene_file.close()

        Mgr.set_global("unsaved_scene", False)

    def __prepare_for_export_to_bam(self, parent, children, tmp_node):

        for child in children:

            if child.get_type() == "model":

                geom_data_obj = child.get_geom_object().get_geom_data_object()
                origin = child.get_origin()
                pivot = child.get_pivot()
                node = geom_data_obj.get_toplevel_geom().copy_to(tmp_node)
                node.set_name(child.get_name())
                node.set_state(origin.get_state())
                mat = origin.get_mat(pivot)
                vertex_data = node.node().modify_geom(0).modify_vertex_data()
                vertex_data.transform_vertices(mat)
                node.set_transform(pivot.get_transform(parent))
                node.node().copy_tags(origin.node())

                tex_stages = node.find_all_texture_stages()

                # require texture files to be in model directory
                for tex_stage in tex_stages:
                    texture = node.get_texture(tex_stage).make_copy()
                    tex_basename = texture.get_filename().get_basename()
                    texture.set_filename(tex_basename)
                    texture.set_fullpath(tex_basename)
                    node.set_texture(tex_stage, texture)

                node.reparent_to(parent)

            else:

                node = parent.attach_new_node(child.get_name())
                node.set_transform(child.get_pivot().get_transform(parent))
                node.node().copy_tags(child.get_origin().node())

            if child.get_children():
                self.__prepare_for_export_to_bam(node, child.get_children(), tmp_node)

    def __export_to_bam(self, filename):

        objs = set([obj.get_root() for obj in Mgr.get("selection", "top")])

        if not objs:
            return

        tmp_node = NodePath("tmp_node")
        root = NodePath(ModelRoot(os.path.basename(filename)))
        self.__prepare_for_export_to_bam(root, objs, tmp_node)

        root.write_bam_file(Filename.from_os_specific(filename))
        root.remove_node()
        tmp_node.remove_node()

    def __prepare_for_export_to_obj(self, obj_file, children, tmp_node,
                                    material_data, counters):

        for child in children:

            if child.get_type() == "model":

                obj_file.write("\no %s\n\n" % child.get_name())

                origin = child.get_origin()
                geom_data_obj = child.get_geom_object().get_geom_data_object()
                node = geom_data_obj.get_toplevel_geom().copy_to(tmp_node)

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
                            else child.get_color()
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

                    color = child.get_color()

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
                mat = origin.get_net_transform().get_mat() * convert_mat
                vertex_data.transform_vertices(mat)
                pos_reader = GeomVertexReader(vertex_data, "vertex")
                uv_reader = GeomVertexReader(vertex_data, "texcoord")
                normal_reader = GeomVertexReader(vertex_data, "normal")
                verts = geom_data_obj.get_subobjects("vert")
                polys = geom_data_obj.get_subobjects("poly").itervalues()
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

                for poly in polys:

                    for tri_data in poly:
                        i1, i2, i3 = [verts[v_id].get_row_index() + row_offset
                                      for v_id in tri_data]
                        indices = (i1, i1, i1, i2, i2, i2, i3, i3, i3)
                        obj_file.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % indices)

                counters["row_offset"] += row_count

            if child.get_children():
                self.__prepare_for_export_to_obj(obj_file, child.get_children(),
                                                 tmp_node, material_data, counters)

    def __export_to_obj(self, filename):

        objs = set([obj.get_root() for obj in Mgr.get("selection", "top")])

        if not objs:
            return

        tmp_node = NodePath("tmp_node")

        material_data = {}
        counters = {"flat_color": 0, "row_offset": 1}

        with open(filename, "w") as obj_file:

            obj_file.write("# Created with Panda3D Studio\n\n")
            fname = os.path.basename(filename)
            mtllib_name = os.path.splitext(fname)[0]
            obj_file.write("mtllib %s.mtl\n" % mtllib_name)
            self.__prepare_for_export_to_obj(obj_file, objs, tmp_node,
                                             material_data, counters)

        tmp_node.remove_node()

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

    def __import(self, filename, simple_edit=False):

        pass


MainObjects.add_class(SceneManager)

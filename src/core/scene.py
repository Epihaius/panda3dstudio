from .base import *
from panda3d.egg import *


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
            obj.destroy()

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
        scene_data_str = scene_file.read_subfile(
            scene_file.find_subfile("scene/data"))
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

    def __export_to_bam(self, filename):

        root = NodePath("p3ds_scene_root")
        tmp_node = NodePath("tmp_node")
        objs = [obj for obj in Mgr.get(
            "selection", "top") if obj.get_type() == "model"]

        for obj in objs:

            geom_data_obj = obj.get_geom_object().get_geom_data_object()
            origin = obj.get_origin()
            geom_top = geom_data_obj.get_toplevel_geom().copy_to(tmp_node)
            geom_top.set_name(obj.get_name())
            geom_top.set_state(origin.get_state())
            geom_top.set_transform(origin.get_transform())
            geom_top.node().copy_tags(origin.node())
            geom_top.wrt_reparent_to(root)

            tex_stages = geom_top.find_all_texture_stages()

            # make texture filenames relative
            for tex_stage in tex_stages:
                texture = geom_top.get_texture(tex_stage).make_copy()
                rel_tex_filename = texture.get_filename().get_basename()
                texture.set_filename(rel_tex_filename)
                texture.set_fullpath(rel_tex_filename)
                geom_top.set_texture(tex_stage, texture)

        root.write_bam_file(Filename.from_os_specific(filename))
        tmp_node.remove_node()
        root.remove_node()

    def __export_to_obj(self, filename):

        objs = [obj for obj in Mgr.get(
            "selection", "top") if obj.get_type() == "model"]

        if not objs:
            return

        tmp_node = NodePath("tmp_node")

        material_data = {}
        flat_color_count = 0

        with open(filename, "w") as obj_file:

            obj_file.write("# Created with Panda3D Studio\n\n")
            fname = os.path.basename(filename)
            mtllib_name = os.path.splitext(fname)[0]
            default_material = None
            obj_file.write("mtllib %s.mtl\n" % mtllib_name)
            row_offset = 1

            for obj in objs:

                obj_file.write("\no %s\n\n" % obj.get_name())

                origin = obj.get_origin()
                geom_data_obj = obj.get_geom_object().get_geom_data_object()
                geom_top = geom_data_obj.get_toplevel_geom().copy_to(tmp_node)

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
                        material_alias = "material_%03d" % len(material_data)
                        data["name"] = material_name
                        data["alias"] = material_alias
                        data["is_flat_color"] = False
                        base_material = material.get_base_material()
                        dif = base_material.get_diffuse() if base_material.has_diffuse() \
                            else obj.get_color()
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

                    color = obj.get_color()

                    if color in material_data:
                        material_name = material_data[color]["name"]
                        material_alias = material_data[color]["alias"]
                    else:
                        flat_color_count += 1
                        material_name = "Flat color %d" % flat_color_count
                        data = {}
                        material_data[color] = data
                        data["name"] = material_name
                        material_alias = "material_%03d" % len(material_data)
                        data["alias"] = material_alias
                        data["is_flat_color"] = True

                vertex_data = geom_top.node().modify_geom(0).modify_vertex_data()
                convert_mat = Mat4.convert_mat(CS_default, CS_yup_right)
                mat = origin.get_mat() * convert_mat
                vertex_data.transform_vertices(mat)
                pos_reader = GeomVertexReader(vertex_data, "vertex")
                uv_reader = GeomVertexReader(vertex_data, "texcoord")
                normal_reader = GeomVertexReader(vertex_data, "normal")
                verts = geom_data_obj.get_subobjects("vert")
                polys = geom_data_obj.get_subobjects("poly").itervalues()
                row_count = vertex_data.get_num_rows()

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

                row_offset += row_count

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

    def __import(self, filename):
        pass


MainObjects.add_class(SceneManager)

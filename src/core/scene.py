from .base import *


class SceneManager(BaseObject):

    def __init__(self):

        GlobalData.set_default("unsaved_scene", False)

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
        obj_lvl = GlobalData["active_obj_level"]
        GlobalData["active_obj_level"] = "top"
        PendingTasks.remove("update_selection", "ui")

        def task():

            selection = Mgr.get("selection", "top")
            selection.update_ui()
            selection.update_obj_props(force=True)

        PendingTasks.add(task, "update_selection", "ui")
        PendingTasks.handle(["object", "ui"], True)

        if obj_lvl != "top":
            Mgr.update_app("active_obj_level")

        if GlobalData["object_links_shown"]:
            GlobalData["object_links_shown"] = False
            Mgr.update_app("object_link_viz", False)

        if GlobalData["transform_target_type"] != "all":
            GlobalData["transform_target_type"] = "all"
            Mgr.update_app("transform_target_type")

        Mgr.do("update_picking_col_id_ranges")
        Mgr.do("clear_user_views")
        Mgr.update_remotely("material_library", "clear")
        Mgr.update_locally("material_library", "clear")
        Mgr.update_app("view", "reset_all")
        Mgr.update_app("coord_sys", "world")
        Mgr.update_app("transf_center", "adaptive")
        Mgr.update_app("active_transform_type", "")
        Mgr.update_app("status", "select", "")

        GlobalData.reset()

        for transf_type, axes in GlobalData["axis_constraints"].iteritems():
            Mgr.update_app("axis_constraints", transf_type, axes)

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

        GlobalData["axis_constraints"] = constraints = scene_data["axis_constraints"]

        for transf_type, axes in constraints.iteritems():
            Mgr.update_app("axis_constraints", transf_type, axes)

        GlobalData["rel_transform_values"] = scene_data["rel_transform_values"]
        transf_type = scene_data["active_transform_type"]
        GlobalData["active_transform_type"] = transf_type
        Mgr.update_app("active_transform_type", transf_type)

        if transf_type:
            Mgr.update_app("status", "select", transf_type, "idle")
        else:
            Mgr.update_app("status", "select", "")

        for x in ("coord_sys", "transf_center"):
            x_type = scene_data[x]["type"]
            obj = Mgr.get("object", scene_data[x]["obj_id"])
            name = obj.get_name(as_object=True) if obj else None
            Mgr.update_locally(x, x_type, obj)
            Mgr.update_remotely(x, x_type, name)

        Mgr.do("set_view_data", scene_data["view_data"])
        Mgr.do("set_material_library", scene_data["material_library"])
        PendingTasks.handle(["object", "ui"], True)

    def __save(self, filename):

        scene_data = {}
        scene_data["material_library"] = Mgr.get("material_library")
        scene_data["view_data"] = Mgr.get("view_data")

        for x in ("coord_sys", "transf_center"):
            scene_data[x] = {}
            scene_data[x]["type"] = GlobalData["%s_type" % x]
            obj = Mgr.get("%s_obj" % x)
            scene_data[x]["obj_id"] = obj.get_id() if obj else None

        scene_data["active_transform_type"] = GlobalData["active_transform_type"]
        scene_data["rel_transform_values"] = GlobalData["rel_transform_values"]
        scene_data["axis_constraints"] = GlobalData["axis_constraints"]

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

        GlobalData["unsaved_scene"] = False

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
                row1 = vert1.get_row_index()

                if row1 in dupes:
                    continue

                for vert2 in verts2[:]:

                    if vert2 is vert1:
                        continue

                    pos2 = vert2.get_pos()
                    normal2 = vert2.get_normal()
                    uv2 = vert2.get_uvs()

                    if pos2 == pos1 and normal2 == normal1 and uv2 == uv1:
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

        return geom_node

    def __prepare_export_to_bam(self, parent, children, tmp_node, directory, geom_node=None):

        for child in children:

            child_geom_node = None

            if child.get_type() == "model":

                geom_obj = child.get_geom_object()

                if child.get_geom_type() == "basic_geom":

                    node = geom_obj.get_geom().copy_to(tmp_node)

                    for key in node.get_tag_keys():
                        node.clear_tag(key)

                else:

                    geom_data_obj = geom_obj.get_geom_data_object()
                    optimized_geom_node = self.__merge_duplicate_vertices(geom_data_obj)
                    node = tmp_node.attach_new_node(optimized_geom_node)
                    masks = Mgr.get("render_masks")["all"] | Mgr.get("picking_masks")["all"]
                    node.show(masks)

                origin = child.get_origin()
                pivot = child.get_pivot()
                node.set_name(child.get_name())
                node.set_state(origin.get_state())
                material = child.get_material()
                r, g, b, a = origin.get_color()

                if material and not material.has_base_properties():
                    node.clear_material()

                if not material or r == g == b == a == 1.:
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

                if geom_node and child.get_optimization_for_export():
                    state = node.get_state()
                    geom = node.node().modify_geom(0)
                    mat = node.get_mat(parent)
                    vertex_data = geom.modify_vertex_data()
                    vertex_data.transform_vertices(mat)
                    geom_node.add_geom(geom, state)
                    node = parent
                else:
                    node.reparent_to(parent)

                if child.get_child_optimization_for_export():
                    child_geom_node = node.node()

            else:

                if child.get_child_optimization_for_export():
                    child_geom_node = GeomNode(child.get_name())
                    node = parent.attach_new_node(child_geom_node)
                else:
                    node = parent.attach_new_node(child.get_name())

                node.set_transform(child.get_pivot().get_transform(parent))
                node.node().copy_tags(child.get_origin().node())

            if child.get_children():
                self.__prepare_export_to_bam(node, child.get_children(), tmp_node,
                                             directory, child_geom_node)

    def __export_to_bam(self, filename):

        objs = set(obj.get_root() for obj in Mgr.get("selection", "top"))

        if not objs:
            return

        tmp_node = NodePath("tmp_node")
        root = NodePath(ModelRoot(os.path.basename(filename)))
        fullpath = Filename.from_os_specific(filename)
        directory = Filename(fullpath.get_dirname())
        self.__prepare_export_to_bam(root, objs, tmp_node, directory)

        root.write_bam_file(fullpath)
        root.remove_node()
        tmp_node.remove_node()

    def __prepare_export_to_obj(self, obj_file, children, tmp_node, material_data,
                                counters, namelist):

        for child in children:

            if child.get_type() == "model":

                name = get_unique_name(child.get_name().replace(" ", "_"), namelist)
                namelist.append(name)
                obj_file.write("\ng %s\n\n" % name)

                geom_obj = child.get_geom_object()

                if child.get_geom_type() == "basic_geom":
                    node = geom_obj.get_geom().copy_to(tmp_node)
                else:
                    geom_data_obj = geom_obj.get_geom_data_object()
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
                self.__prepare_export_to_obj(obj_file, child.get_children(), tmp_node,
                                             material_data, counters, namelist)

    def __export_to_obj(self, filename):

        objs = set(obj.get_root() for obj in Mgr.get("selection", "top"))

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
            self.__prepare_export_to_obj(obj_file, objs, tmp_node, material_data,
                                         counters, [])

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

    def __create_point_helper(self, name, transform):

        size = 10.
        on_top = True
        colors = {"unselected": (0., .5, .5, 1.), "selected": (1., 1., 1., 1.)}
        point_helper = Mgr.do("create_custom_point_helper", name, size, on_top, colors, transform)

        return point_helper

    def __import_children(self, basic_edit, parent_id, children, objs_to_store):

        children.detach()

        for child in children:

            if child.is_empty():
                continue

            name = child.get_name()

            if not name.strip():
                name = "object 0001"

            name = get_unique_name(name, GlobalData["obj_names"])
            node = child.node()

            if basic_edit:

                node_type = node.get_class_type().get_name()

                if node_type == "GeomNode":

                    bounds_node = child
                    geom_count = node.get_num_geoms()

                    if geom_count > 1:

                        obj = self.__create_point_helper(name, child.get_transform())
                        obj.set_child_optimization_for_export()
                        obj_id = obj.get_id()

                        for i in range(geom_count):
                            state = node.get_geom_state(i)
                            new_node = GeomNode("basic_geom_part")
                            new_node.add_geom(node.modify_geom(i))
                            new_geom = NodePath(new_node)
                            new_geom.set_state(state)
                            part_name = name + " [part %d]" % (i + 1)
                            part_name = get_unique_name(part_name, GlobalData["obj_names"])
                            new_geom.node().modify_geom(0).decompose_in_place()
                            part = Mgr.do("create_basic_geom", new_geom, part_name).get_model()
                            part.set_parent(obj_id, add_to_hist=False)
                            part.get_bbox().update(*new_geom.get_tight_bounds())
                            part.set_optimization_for_export()
                            objs_to_store.append(part)

                    else:

                        if node.get_geom_state(0).is_empty():
                            new_geom = child
                        else:
                            state = node.get_geom_state(0)
                            new_node = GeomNode("basic_geom")
                            new_node.add_geom(node.modify_geom(0))
                            new_geom = NodePath(new_node)
                            new_geom.set_state(state)
                            new_geom.set_transform(child.get_transform())
                            bounds_node = new_geom

                        new_geom.node().modify_geom(0).decompose_in_place()
                        basic_geom = Mgr.do("create_basic_geom", new_geom, name)
                        obj = basic_geom.get_model()
                        obj.set_optimization_for_export()

                else:

                    obj = self.__create_point_helper(name, child.get_transform())

                obj.set_parent(parent_id, add_to_hist=False)

                self.__import_children(basic_edit, obj.get_id(), child.get_children(),
                                       objs_to_store)

                if obj.get_type() == "model":
                    obj.get_bbox().update(*bounds_node.get_tight_bounds())

                objs_to_store.append(obj)

                continue

    def __import(self, filename, basic_edit=True):

        path = Filename.from_os_specific(filename)
        loader_options = LoaderOptions(LoaderOptions.LF_no_cache)
        model_root = Mgr.load_model(path, okMissing=True, loaderOptions=loader_options)

        if not model_root:
            return

        objs_to_store = []
        self.__import_children(basic_edit, None, model_root.get_children(),
                               objs_to_store)
        model_root.remove_node()

        # make undo/redoable

        Mgr.do("update_history_time")
        obj_data = {}
        event_data = {"objects": obj_data}
        event_descr = 'Import "%s"' % os.path.basename(filename)

        for obj in objs_to_store:
            obj_data[obj.get_id()] = obj.get_data_to_store("creation")

        if not obj_data:
            return

        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(SceneManager)

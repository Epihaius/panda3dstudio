from .base import *
from .geom.material import render_state_to_material


class ImportManager(BaseObject):

    def __init__(self):

        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._obj_data = {"geom": {}, "collision": {}, "other": {}}
        self._obj_names = []
        self._imported_file = ""
        self._imported_file_type = ""
        self._imported_objs = []

        Mgr.add_app_updater("import", self.__update_import)

    def __prepare_import(self, filename):

        self._imported_file = filename
        path = Filename.from_os_specific(filename)
        loader_options = LoaderOptions(LoaderOptions.LF_no_cache)
        model_root = Mgr.load_model(path, okMissing=True, loaderOptions=loader_options)

        if not (model_root and model_root.get_children()):
            return

        self._imported_file_type = path.get_extension()
        self._model_root = model_root
        hierarchy = self._hierarchy

        obj_names = GlobalData["obj_names"]
        self._obj_names = new_obj_names = []
        obj_data = self._obj_data
        node_paths = [(model_root, 0, None)]

        while node_paths:

            node_path, index, parent_index = node_paths.pop()

            if node_path.is_empty():
                continue

            child_indices = []
            node_data = {"node_path": node_path, "children": child_indices}
            hierarchy[index] = node_data
            children = node_path.get_children()
            children.detach()

            for child in children:
                self._obj_index += 1
                child_index = self._obj_index
                child_indices.append(child_index)
                node_paths.append((child, child_index, index))

            if node_path is model_root:
                continue

            old_name = node_path.get_name()
            new_name = obj_name = old_name.strip()

            if not new_name:
                new_name = "object 0001"

            new_name = get_unique_name(new_name, obj_names + new_obj_names)

            if not old_name:
                old_name = "<Unnamed>"

            node = node_path.node()
            node_type = node.get_class_type().get_name()
            data = {"parent_index": parent_index, "old_name": old_name, "new_name": new_name}
            node_data["data"] = data

            if node_type == "GeomNode" and Geom.PT_polygons in [geom.get_primitive_type()
                    for geom in node.get_geoms()]:
                data["editing"] = "full"
                obj_data["geom"][index] = data
            elif node_type == "CollisionNode":
                new_name = obj_name if obj_name else "collision object 0001"
                new_name = get_unique_name(new_name, obj_names + new_obj_names)
                data["new_name"] = new_name
                data["editing"] = "basic"
                obj_data["collision"][index] = data
            else:
                obj_data["other"][index] = data

            new_obj_names.append(new_name)

        Mgr.update_remotely("import", obj_data, new_obj_names)

    def __cancel_import(self):

        self._model_root.remove_node()
        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._obj_data = {"geom": {}, "collision": {}, "other": {}}
        self._obj_names = []
        self._imported_file = ""
        self._imported_file_type = ""

    def __create_point_helper(self, name, transform):

        size = 10.
        on_top = True
        colors = {"unselected": (.5, 0., 1., 1.), "selected": (1., 1., 1., 1.)}
        point_helper = Mgr.do("create_custom_point_helper", name, size, on_top, colors, transform)
        point_helper.update_pos()

        return point_helper

    def __create_collision_primitive(self, obj_type, *args):

        if obj_type == "CollisionSphere":
            name, radius, pos = args
            segments = 16
            creator = Mgr.do("create_custom_sphere", name, radius, segments, pos)
        elif obj_type == "CollisionTube":
            name, radius, height, pos, hpr = args
            segments = {"circular": 12, "height": 1, "caps": 1}
            creator = Mgr.do("create_custom_cylinder", name, radius, height, segments, pos)
        elif obj_type == "CollisionBox":
            name, x, y, z, pos = args
            segments = {"x": 1, "y": 1, "z": 1}
            creator = Mgr.do("create_custom_box", name, x, y, z, segments, pos)

        model = creator.next()
        model.register(restore=False)

        if obj_type == "CollisionTube":
            pivot = model.get_pivot()
            pivot.set_hpr(hpr)
            pivot.set_p(pivot, -90.)

        return model

    def __create_collision_model(self, name, polys, editing):

        IPos = ImprecisePos
        impr_coords = []
        poly_count = 0

        if editing == "basic":

            vertex_format = GeomVertexFormat.get_v3n3()
            vertex_data = GeomVertexData("basic_geom", vertex_format, Geom.UH_static)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            normal_writer = GeomVertexWriter(vertex_data, "normal")
            tris = GeomTriangles(Geom.UH_static)
            row = 0

            for poly in polys:

                points = [IPos(tuple(crd for crd in point), epsilon=1.e-005) for point in poly]
                rows_by_pos = {}

                for i, point in enumerate(points):
                    for impr_crd in impr_coords:
                        if point == impr_crd:
                            points[i] = impr_crd
                            break
                    else:
                        impr_coords.append(point)

                plane = Plane(*poly[:3])
                normal = plane.get_normal()
                pos = points.pop(0)
                pos_writer.add_data3f(*pos)
                normal_writer.add_data3f(normal)
                rows_by_pos[pos] = row1 = row
                row += 1

                for positions in (points[i:i+2] for i in range(len(points) - 1)):

                    tris.add_vertex(row1)

                    for pos in positions:
                        if pos in rows_by_pos:
                            tris.add_vertex(rows_by_pos[pos])
                        else:
                            pos_writer.add_data3f(*pos)
                            normal_writer.add_data3f(normal)
                            rows_by_pos[pos] = row
                            tris.add_vertex(row)
                            row += 1

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

            geom = Geom(vertex_data)
            geom.add_primitive(tris)
            node = GeomNode("basic_geom")
            node.add_geom(geom)
            node_path = NodePath(node)
            model = Mgr.do("create_basic_geom", node_path, name).get_model()
            model.get_bbox().update(*node_path.get_tight_bounds())

        else:

            geom_data = []

            for poly in polys:

                points = [IPos(tuple(crd for crd in point), epsilon=1.e-005) for point in poly]

                for i, point in enumerate(points):
                    for impr_crd in impr_coords:
                        if point == impr_crd:
                            points[i] = impr_crd
                            break
                    else:
                        impr_coords.append(point)

                plane = Plane(*poly[:3])
                normal = plane.get_normal()
                pos = points.pop(0)
                vert_data1 = {"pos": pos, "normal": normal, "uvs": {0: (0., 0.)}}
                tris = []

                for positions in (points[i:i+2] for i in range(len(points) - 1)):

                    tri_data = [vert_data1]

                    for pos in positions:
                        tri_data.append({"pos": pos, "normal": normal, "uvs": {0: (0., 0.)}})

                    tris.append(tri_data)

                poly_data = {"tris": tris, "smoothing": [(0, False)]}
                geom_data.append(poly_data)

                poly_count += 1

                if poly_count == 20:
                    yield
                    poly_count = 0

            editable_geom = Mgr.do("create_editable_geom", name=name)
            model = editable_geom.get_model()

            id_str = str(model.get_id())
            handler = lambda info: model.cancel_creation() if info == "import" else None
            Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)

            geom_data_obj = editable_geom.get_geom_data_object()

            for step in geom_data_obj.process_geom_data(geom_data, gradual=True):
                yield

            for step in editable_geom.create(gradual=True):
                yield

            model.get_bbox().update(*geom_data_obj.get_origin().get_tight_bounds())
            Mgr.remove_notification_handler("long_process_cancelled", id_str)

        r, g, b = [random.random() * .4 + .5 for i in range(3)]
        color = (r, g, b, 1.)
        model.set_color(color, update_app=False)
        model.register(restore=False)

        yield model

    def __create_editable_model(self, name, src_geom, render_state):

        IPos = ImprecisePos
        impr_coords = []
        geom_data = []
        poly_count = 0

        geom = src_geom.decompose().unify(1000000, False)
        vertex_data = geom.get_vertex_data()
        vertex_format = vertex_data.get_format()
        pos_reader = GeomVertexReader(vertex_data, "vertex")

        if vertex_data.has_column("normal"):
            normal_reader = GeomVertexReader(vertex_data, "normal")
        else:
            normal_reader = None

        if vertex_data.has_column("color"):
            col_reader = GeomVertexReader(vertex_data, "color")
        else:
            col_reader = None

        default_uv_set_name = InternalName.get_texcoord()
        uv_set_list = [default_uv_set_name]
        uv_set_list += [InternalName.get_texcoord_name(str(i)) for i in range(1, 8)]
        uv_readers = {}
        material, uv_set_names = render_state_to_material(render_state, vertex_format,
                                                          for_basic_geom=False)

        for src_uv_set, dest_uv_set in uv_set_names.iteritems():
            uv_reader = GeomVertexReader(vertex_data, src_uv_set)
            uv_set_id = uv_set_list.index(dest_uv_set)
            uv_readers[uv_set_id] = uv_reader

        extracted_data = {}
        indices = geom.get_primitive(0).get_vertex_list()

        for rows in (indices[i:i+3] for i in xrange(0, len(indices), 3)):

            tri_data = []

            for row in rows:

                if row in extracted_data:

                    vert_data = extracted_data[row]

                else:

                    vert_data = {}
                    pos_reader.set_row(row)
                    pos = IPos(tuple(crd for crd in pos_reader.get_data3f()), epsilon=1.e-005)

                    for impr_crd in impr_coords:
                        if pos == impr_crd:
                            pos = impr_crd
                            break
                    else:
                        impr_coords.append(pos)

                    vert_data["pos"] = pos

                    if normal_reader:
                        normal_reader.set_row(row)
                        vert_data["normal"] = Vec3(normal_reader.get_data3f())

                    if col_reader:
                        col_reader.set_row(row)
                        vert_data["color"] = tuple(x for x in col_reader.get_data4f())

                    uvs = {}

                    for uv_set_id, uv_reader in uv_readers.iteritems():
                        uv_reader.set_row(row)
                        u, v = uv_reader.get_data2f()
                        uvs[uv_set_id] = (u, v)

                    vert_data["uvs"] = uvs
                    extracted_data[row] = vert_data

                tri_data.append(vert_data)

            if normal_reader is None:

                points = [Point3(*vert_data["pos"]) for vert_data in tri_data]
                plane = Plane(*points)
                normal = plane.get_normal()

                for vert_data in tri_data:
                    vert_data["normal"] = normal

            poly_data = {"tris": [tri_data], "smoothing": [(0, False)]}
            geom_data.append(poly_data)

            poly_count += 1

            if poly_count == 20:
                yield
                poly_count = 0

        has_vert_colors = False if col_reader is None else True
        editable_geom = Mgr.do("create_editable_geom", name=name, has_vert_colors=has_vert_colors)
        model = editable_geom.get_model()

        id_str = str(model.get_id())
        handler = lambda info: model.cancel_creation() if info == "import" else None
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)

        geom_data_obj = editable_geom.get_geom_data_object()

        for step in geom_data_obj.process_geom_data(geom_data, gradual=True):
            yield

        geom_data_obj.recompute_smoothing()

        for step in editable_geom.create(gradual=True):
            yield

        if col_reader:
            geom_data_obj.set_initial_vertex_colors()

        r, g, b = [random.random() * .4 + .5 for i in range(3)]
        color = (r, g, b, 1.)
        model.set_color(color, update_app=False)
        model.register(restore=False)
        Mgr.remove_notification_handler("long_process_cancelled", id_str)

        if material:
            model.set_material(material)

        yield model

    def __create_model_group(self, name, transform):

        model_group = Mgr.do("create_group", name, ["model"], "model", transform)

        return model_group

    def __create_collision_group(self, name, transform):

        coll_group = Mgr.do("create_group", name, ["collision"], "collision", transform)

        return coll_group

    def __import_objects(self):

        model_root = self._model_root
        hierarchy = self._hierarchy
        data = [(hierarchy[0], None)]

        while data:

            node_data, parent_id = data.pop()
            node_path = node_data["node_path"]

            if node_path is model_root:

                obj_id = None

            else:

                obj_name = node_data["data"]["new_name"]
                node = node_path.node()
                node_type = node.get_class_type().get_name()
                editing = node_data["data"].get("editing", "")
                node_state = node_path.get_state()

                if node_type == "GeomNode" and Geom.PT_polygons in [geom.get_primitive_type()
                        for geom in node.get_geoms()]:

                    bounds_node = node_path
                    geom_indices = [i for i, geom in enumerate(node.get_geoms())
                                    if geom.get_primitive_type() == Geom.PT_polygons]
                    geom_count = len(geom_indices)

                    if editing == "basic":

                        if geom_count > 1:

                            obj = self.__create_model_group(obj_name, node_path.get_transform())
                            obj_names = GlobalData["obj_names"] + self._obj_names
                            obj_names.remove(obj_name)

                            for i in geom_indices:
                                state = node.get_geom_state(i)
                                new_node = GeomNode("basic_geom")
                                new_node.add_geom(node.modify_geom(i).decompose().unify(1000000, False))
                                new_geom = NodePath(new_node)
                                new_geom.set_state(state)
                                member_name = "object 0001"
                                member_name = get_unique_name(member_name, obj_names)
                                obj_names.append(member_name)
                                member = Mgr.do("create_basic_geom", new_geom, member_name).get_model()
                                member.register(restore=False)
                                Mgr.do("add_group_member", member, obj, restore="import")
                                member.get_bbox().update(*new_geom.get_tight_bounds())
                                self._imported_objs.append(member)

                        else:

                            index = geom_indices[0]
                            state = node.get_geom_state(index)

                            if state.is_empty():
                                new_geom = node_path
                                new_node = node_path.node()
                            else:
                                new_node = GeomNode("basic_geom")
                                new_node.add_geom(node.modify_geom(index))
                                new_geom = NodePath(new_node)
                                new_geom.set_state(state)
                                new_geom.set_transform(node_path.get_transform())
                                bounds_node = new_geom

                            new_node.decompose()
                            new_node.unify(1000000, False)
                            obj = Mgr.do("create_basic_geom", new_geom, obj_name).get_model()
                            obj.register(restore=False)

                    else:

                        if geom_count > 1:

                            obj = self.__create_model_group(obj_name, node_path.get_transform())
                            obj_names = GlobalData["obj_names"] + self._obj_names
                            obj_names.remove(obj_name)

                            for i in geom_indices:

                                state = node.get_geom_state(i)

                                if state.is_empty():
                                    state = node_state

                                member_name = "object 0001"
                                member_name = get_unique_name(member_name, obj_names)
                                obj_names.append(member_name)
                                src_geom = node.modify_geom(i)

                                for member in self.__create_editable_model(member_name, src_geom, state):
                                    yield

                                member.register(restore=False)
                                Mgr.do("add_group_member", member, obj, restore="import")
                                geom_data_obj = member.get_geom_object().get_geom_data_object()
                                origin = geom_data_obj.get_origin()
                                member.get_bbox().update(*origin.get_tight_bounds())
                                self._imported_objs.append(member)

                        else:

                            state = node.get_geom_state(0)

                            if state.is_empty():
                                state = node_state

                            src_geom = node.modify_geom(0)

                            for obj in self.__create_editable_model(obj_name, src_geom, state):
                                yield

                            obj.register(restore=False)
                            obj.get_pivot().set_transform(node_path.get_transform())
                            bounds_node = obj.get_geom_object().get_origin()

                elif node_type == "CollisionNode":

                    coll_objs = []
                    coll_polys = []
                    obj_names = GlobalData["obj_names"] + self._obj_names

                    for solid in node.get_solids():

                        obj_type = solid.get_class_type().get_name()

                        if obj_type not in ("CollisionSphere", "CollisionTube",
                                            "CollisionBox", "CollisionPolygon"):
                            continue

                        if obj_type == "CollisionPolygon":

                            if solid.is_valid():
                                poly = solid.get_points()
                                coll_polys.append(poly)

                        else:

                            name = "object 0001"
                            name = get_unique_name(name, obj_names)
                            obj_names.append(name)

                            if obj_type == "CollisionSphere":

                                radius = solid.get_radius()
                                pos = solid.get_center()
                                args = (name, radius, pos)

                            elif obj_type == "CollisionTube":

                                radius = solid.get_radius()
                                a = solid.get_point_a()
                                b = solid.get_point_b()
                                height_vec = V3D(b - a)
                                height = height_vec.length()
                                hpr = height_vec.get_hpr()
                                args = (name, radius, height, a, hpr)

                            elif obj_type == "CollisionBox":

                                pos = Point3(solid.get_center())
                                size = {"x": 0., "y": 0., "z": 0.}

                                for i in range(6):
                                    plane = solid.get_plane(i)
                                    x, y, z = plane.get_normal()
                                    dist = abs(plane.dist_to_plane(pos))
                                    size["x" if abs(x) else ("y" if abs(y) else "z")] = dist * 2.

                                x = size["x"]
                                y = size["y"]
                                z = size["z"]
                                pos += Vec3.up() * z * -.5
                                args = (name, x, y, z, pos)

                            coll_objs.append(self.__create_collision_primitive(obj_type, *args))

                    self._imported_objs.extend(coll_objs)

                    if coll_polys:

                        name = "object 0001"
                        name = get_unique_name(name, obj_names)
                        obj_names.append(name)

                        for model in self.__create_collision_model(name, coll_polys, editing):
                            yield

                        coll_objs.append(model)
                        self._imported_objs.append(model)

                    if not coll_objs:
                        continue

                    obj = self.__create_collision_group(obj_name, node_path.get_transform())
                    Mgr.do("add_group_members", coll_objs, obj, add_to_hist=False, restore="import")

                else:

                    obj = self.__create_point_helper(obj_name, node_path.get_transform())

                obj.restore_link(parent_id, None)

                if obj.get_type() == "model":
                    obj.get_bbox().update(*bounds_node.get_tight_bounds())

                self._imported_objs.append(obj)
                obj_id = obj.get_id()
                self._obj_names.remove(obj_name)

            child_indices = node_data["children"]

            for child_index in child_indices:
                if child_index in hierarchy:
                    child_data = hierarchy[child_index]
                    data.append((child_data, obj_id))

            yield

    def __get_progress_steps(self):

        progress_steps = 0
        hierarchy = self._hierarchy
        obj_data = self._obj_data

        for index, data in obj_data["geom"].iteritems():

            basic_or_full = data["editing"]

            if basic_or_full == "full":

                node_data = hierarchy[index]
                node = node_data["node_path"].node()

                geom_indices = [i for i, geom in enumerate(node.get_geoms())
                                if geom.get_primitive_type() == Geom.PT_polygons]

                for i in geom_indices:
                    geom = node.modify_geom(i)
                    geom.decompose_in_place()
                    geom.unify_in_place(1000000, False)
                    poly_count = len(geom.get_primitive(0).get_vertex_list()) / 3
                    progress_steps += (poly_count // 20) * 5
                    progress_steps += poly_count // 50

        for index, data in obj_data["collision"].iteritems():

            node_data = hierarchy[index]
            node = node_data["node_path"].node()

            coll_poly_count = 0

            for solid in node.get_solids():

                obj_type = solid.get_class_type().get_name()

                if obj_type == "CollisionPolygon" and solid.is_valid():
                    coll_poly_count += 1

            if data["editing"] == "full":
                progress_steps += (coll_poly_count // 20) * 5 + coll_poly_count // 50
            else:
                progress_steps += coll_poly_count // 20

        return progress_steps

    def __import(self):

        progress_steps = self.__get_progress_steps()
        gradual = progress_steps > 100

        yield True

        if gradual:
            Mgr.show_screenshot()
            GlobalData["progress_steps"] = progress_steps

        Mgr.do("update_history_time")

        for step in self.__import_objects():
            if gradual:
                yield True

        self._model_root.remove_node()
        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._obj_data = {"geom": {}, "collision": {}, "other": {}}
        self._imported_file_type = ""

        if not self._imported_objs:
            yield False

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        event_descr = 'Import "%s"' % os.path.basename(self._imported_file)
        self._imported_file = ""

        for obj in self._imported_objs:
            obj_data[obj.get_id()] = obj.get_data_to_store("creation")

        self._imported_objs = []
        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __cancel_import_process(self, info):

        if info == "import":

            for obj in self._imported_objs:
                obj.destroy(unregister=False, add_to_hist=False)

        self._model_root.remove_node()
        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._obj_data = {"geom": {}, "collision": {}, "other": {}}
        self._obj_names = []
        self._imported_file = ""
        self._imported_file_type = ""
        self._imported_objs = []
        Mgr.do("clear_added_history")

    def __start_import(self):

        Mgr.do("create_material_registry_backup")
        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        do_import = False
        process = self.__import()

        for step in process:
            if step:
                do_import = True
                break

        if do_import and process.next():
            handler = self.__cancel_import_process
            Mgr.add_notification_handler("long_process_cancelled", "import_mgr", handler, once=True)
            task = lambda: Mgr.remove_notification_handler("long_process_cancelled", "import_mgr")
            task_id = "remove_notification_handler"
            PendingTasks.add(task, task_id, "object", id_prefix="import_mgr", sort=100)
            descr = "Importing..."
            Mgr.do_gradually(process, "import", descr, cancellable=True)

    def __update_import(self, update_type, *args):

        if update_type == "prepare":
            self.__prepare_import(*args)
        elif update_type == "cancel":
            self.__cancel_import()
        elif update_type == "start":
            self.__start_import()


MainObjects.add_class(ImportManager)

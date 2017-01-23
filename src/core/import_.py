from .base import *


class ImportManager(BaseObject):

    def __init__(self):

        self._imported_file_type = ""
        self._imported_objs = []
        self._progress_steps = 0

        Mgr.add_app_updater("import", self.__do_import)

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

    def __create_collision_model(self, name, polys):

        IPos = ImprecisePos
        geom_data = []

        for poly in polys:

            points = [IPos(tuple(crd for crd in point), epsilon=1.e-005) for point in poly]
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

        editable_geom = Mgr.do("create_editable_geom", name=name)
        model = editable_geom.get_model()

        id_str = str(model.get_id())
        handler = lambda info: model.cancel_creation() if info == "import" else None
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)

        r, g, b = [random.random() * .4 + .5 for i in range(3)]
        color = (r, g, b, 1.)
        geom_data_obj = editable_geom.get_geom_data_object()
        yield

        for step in geom_data_obj.process_geom_data(geom_data, gradual=True):
            yield

        for step in editable_geom.create(gradual=True):
            yield

        model.set_color(color, update_app=False)
        model.get_bbox().update(*geom_data_obj.get_origin().get_tight_bounds())
        model.register(restore=False)
        Mgr.remove_notification_handler("long_process_cancelled", id_str)

        yield model

    def __create_model_group(self, name, transform):

        model_group = Mgr.do("create_group", name, ["model"], "model", transform)

        return model_group

    def __create_collision_group(self, name, transform):

        coll_group = Mgr.do("create_group", name, ["collision"], "collision", transform)

        return coll_group

    def __import_children(self, basic_edit, parent_id, children):

        children.detach()

        for child in children:

            if child.is_empty():
                continue

            obj_name = child_name = child.get_name().strip()

            if not obj_name:
                obj_name = "object 0001"

            obj_name = get_unique_name(obj_name, GlobalData["obj_names"])
            node = child.node()

            if basic_edit:

                node_type = node.get_class_type().get_name()

                if node_type == "GeomNode":

                    bounds_node = child
                    geom_count = node.get_num_geoms()

                    if geom_count > 1:

                        obj = self.__create_model_group(obj_name, child.get_transform())

                        for i in range(geom_count):
                            state = node.get_geom_state(i)
                            new_node = GeomNode("basic_geom")
                            new_node.add_geom(node.modify_geom(i).decompose())
                            new_geom = NodePath(new_node)
                            new_geom.set_state(state)
                            member_name = "object 0001"
                            member_name = get_unique_name(member_name, GlobalData["obj_names"])
                            member = Mgr.do("create_basic_geom", new_geom, member_name).get_model()
                            member.register(restore=False)
                            Mgr.do("add_group_member", member, obj, restore="import")
                            member.get_bbox().update(*new_geom.get_tight_bounds())
                            self._imported_objs.append(member)

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
                        basic_geom = Mgr.do("create_basic_geom", new_geom, obj_name)
                        obj = basic_geom.get_model()
                        obj.register(restore=False)

                elif node_type == "CollisionNode":

                    coll_objs = []
                    coll_polys = []

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
                            name = get_unique_name(name, GlobalData["obj_names"])

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
                        name = get_unique_name(name, GlobalData["obj_names"])

                        for model in self.__create_collision_model(name, coll_polys):
                            yield

                        coll_objs.append(model)
                        self._imported_objs.append(model)

                    if not coll_objs:
                        continue

                    obj_name = child_name if child_name else "collision object 0001"
                    obj_name = get_unique_name(obj_name, GlobalData["obj_names"])
                    obj = self.__create_collision_group(obj_name, child.get_transform())
                    Mgr.do("add_group_members", coll_objs, obj, add_to_hist=False, restore="import")

                else:

                    obj = self.__create_point_helper(obj_name, child.get_transform())

                obj.restore_link(parent_id, None)

                if obj.get_type() == "model":
                    obj.get_bbox().update(*bounds_node.get_tight_bounds())

                self._imported_objs.append(obj)

                for step in self.__import_children(basic_edit, obj.get_id(), child.get_children()):
                    yield

                yield
                continue

    def __update_progress_steps(self, basic_edit, children):

        for child in children:

            if child.is_empty():
                continue

            node = child.node()

            if basic_edit:

                node_type = node.get_class_type().get_name()

                if node_type == "CollisionNode":

                    coll_poly_count = 0

                    for solid in node.get_solids():

                        obj_type = solid.get_class_type().get_name()

                        if obj_type == "CollisionSphere":
                            pass
                        elif obj_type == "CollisionTube":
                            pass
                        elif obj_type == "CollisionBox":
                            pass
                        elif obj_type == "CollisionPolygon":
                            if solid.is_valid():
                                coll_poly_count += 1
                        else:
                            continue

                    self._progress_steps += coll_poly_count // 10
                    self._progress_steps += coll_poly_count // 50
                    self._progress_steps += coll_poly_count // 20

                self.__update_progress_steps(basic_edit, child.get_children())

                continue

    def __import(self, filename, basic_edit=True):

        path = Filename.from_os_specific(filename)
        loader_options = LoaderOptions(LoaderOptions.LF_no_cache)
        model_root = Mgr.load_model(path, okMissing=True, loaderOptions=loader_options)

        if not model_root:
            return

        children = model_root.get_children()

        if not children:
            return

        self.__update_progress_steps(basic_edit, children)
        gradual = self._progress_steps > 100

        yield True

        if gradual:
            Mgr.show_screenshot()
            GlobalData["progress_steps"] = self._progress_steps

        self._progress_steps = 0

        self._imported_file_type = path.get_extension()
        Mgr.do("update_history_time")

        for step in self.__import_children(basic_edit, None, children):
            if gradual:
                yield True

        model_root.remove_node()
        self._imported_file_type = ""

        if not self._imported_objs:
            yield False

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        event_descr = 'Import "%s"' % os.path.basename(filename)

        for obj in self._imported_objs:
            obj_data[obj.get_id()] = obj.get_data_to_store("creation")

        self._imported_objs = []
        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        yield False

    def __cancel_import(self, info):

        if info == "import":

            for obj in self._imported_objs:
                obj.destroy(unregister=False, add_to_hist=False)

        self._imported_objs = []
        Mgr.do("clear_added_history")

    def __do_import(self, filename, basic_edit=True):

        Mgr.do("create_registry_backups")
        Mgr.do("create_id_range_backups")
        do_import = False
        process = self.__import(filename, basic_edit)

        for step in process:
            if step:
                do_import = True
                break

        if do_import and process.next():
            handler = self.__cancel_import
            Mgr.add_notification_handler("long_process_cancelled", "import_mgr", handler, once=True)
            task = lambda: Mgr.remove_notification_handler("long_process_cancelled", "import_mgr")
            task_id = "remove_notification_handler"
            PendingTasks.add(task, task_id, "object", id_prefix="import_mgr", sort=100)
            descr = "Importing..."
            Mgr.do_gradually(process, "import", descr, cancellable=True)


MainObjects.add_class(ImportManager)

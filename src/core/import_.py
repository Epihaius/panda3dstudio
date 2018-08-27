from .base import *
from .geom.material import render_state_to_material


class ImportManager(BaseObject):

    def __init__(self):

        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._coll_obj_indices = []
        self._obj_names = []
        self._imported_file = ""
        self._imported_file_type = ""
        self._imported_materials = []
        self._imported_objs = []

        Mgr.add_app_updater("import", self.__update_import)

    def __prepare_import(self, filename):

        self._imported_file = filename
        path = Filename.from_os_specific(filename)
        model_root = Mgr.load_model(path, noCache=True, okMissing=True)

        if not (model_root and model_root.get_children()):
            return

        self._imported_file_type = path.get_extension()
        self._model_root = model_root
        hierarchy = self._hierarchy

        obj_names = GlobalData["obj_names"]
        self._obj_names = new_obj_names = []
        coll_indices = self._coll_obj_indices
        node_paths = [(model_root, 0, None)]

        while node_paths:

            node_path, index, parent_index = node_paths.pop()

            if node_path.is_empty():
                continue

            child_indices = []
            node_data = {"node_path": node_path, "child_indices": child_indices}
            hierarchy[index] = node_data
            children = node_path.get_children()

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
            node_data["parent_index"] = parent_index
            node_data["old_name"] = old_name
            node_data["new_name"] = new_name

            if node_type == "GeomNode" and Geom.PT_polygons in [geom.get_primitive_type()
                    for geom in node.get_geoms()]:
                node_data["geom_type"] = "regular"
            elif node_type == "CollisionNode":
                new_name = obj_name if obj_name else "collision object 0001"
                new_name = get_unique_name(new_name, obj_names + new_obj_names)
                node_data["new_name"] = new_name
                node_data["geom_type"] = "collision"
                coll_indices.append(index)
            else:
                node_data["geom_type"] = "none"

            new_obj_names.append(new_name)

        Mgr.update_remotely("import", hierarchy, new_obj_names)

    def __cancel_import(self):

        self._model_root.remove_node()
        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._coll_obj_indices = []
        self._obj_names = []
        self._imported_file = ""
        self._imported_file_type = ""
        self._imported_materials = []

    def __create_point_helper(self, name, transform):

        size = 10.
        on_top = True
        colors = {"unselected": (.5, 0., 1., 1.), "selected": (1., 1., 1., 1.)}
        point_helper = Mgr.do("create_custom_point_helper", name, size, on_top, colors, transform)
        point_helper.update_pos()

        return point_helper

    def __create_collision_planes(self, plane_data, obj_names):

        # check if the given planes form an inverted box
        if len(plane_data) == 6:

            data_to_process = plane_data[:]
            opposite_sides = []
            side_normals = []

            while data_to_process:

                side_plane = data_to_process.pop()
                point = side_plane.get_point()
                normal = V3D(side_plane.get_normal())

                # check if side is perpendicular to previous sides
                for other_normal in side_normals:
                    if abs(normal * other_normal) > .001:
                        break

                # check if there is a side facing this one
                for other_side_plane in data_to_process:

                    other_normal = V3D(other_side_plane.get_normal())

                    # check if planes are facing opposite directions
                    if normal * other_normal < -.99:

                        dist = other_side_plane.dist_to_plane(point)

                        # check if planes are facing each other
                        # ("inner" half-spaces do not intersect)
                        if dist > 0.:
                            opposite_sides.append((side_plane, other_side_plane, dist))
                            side_normals.append(normal)
                            data_to_process.remove(other_side_plane)
                            break

                else:

                    break

            if len(side_normals) == 3:

                up_vec = V3D(Vec3.up())
                dot_prod = 0.
                z_vec = None
                xy_plane_data = None

                # use the normal closest to the world Z vector as the local Z vector
                for normal, side_data in zip(side_normals, opposite_sides):

                    dot_prod_tmp = up_vec * normal

                    if abs(dot_prod_tmp) > abs(dot_prod):
                        dot_prod = dot_prod_tmp
                        z_vec = normal
                        xy_plane_data = side_data

                side_normals.remove(z_vec)
                opposite_sides.remove(xy_plane_data)

                if dot_prod < 0.:
                    z_vec *= -1.
                    xy_plane = xy_plane_data[1]
                else:
                    xy_plane = xy_plane_data[0]

                x_vec = side_normals[0]
                y_vec = z_vec ** x_vec
                yz_plane_data, xz_plane_data = opposite_sides
                yz_plane = yz_plane_data[0]

                x = yz_plane_data[2]
                y = xz_plane_data[2]
                z = xy_plane_data[2]

                point = Point3()
                xy_plane.intersects_plane(point, Vec3(), yz_plane)
                corners = [xz_plane.project(point) for xz_plane in xz_plane_data[:2]]
                pos = sum(corners, Point3()) * .5 + x_vec * .5 * x

                quat = Quat()
                look_at(quat, y_vec, z_vec)
                hpr = quat.get_hpr()

                name = "object 0001"
                name = get_unique_name(name, obj_names)
                obj_names.append(name)

                segments = {"x": 1, "y": 1, "z": 1}
                creator = Mgr.do("create_custom_box", name, x, y, z, segments, pos, inverted=True)
                model = next(creator)
                model.register(restore=False)
                model.get_pivot().set_hpr(hpr)

                return [model]

        plane_models = []

        for plane in plane_data:

            pos = plane.project(Point3(0., 0., 0.))
            normal = plane.get_normal()

            if normal.x < -.999:
                hpr = VBase3(0., 0., 90.)
            elif normal.x > .999:
                hpr = VBase3(0., 0., -90.)
            elif normal.y < -.999:
                hpr = VBase3(0., -90., 0.)
            elif normal.y > .999:
                hpr = VBase3(0., 90., 0.)
            elif normal.z < -.999:
                hpr = VBase3(0., 180., 0.)
            elif normal.z > .999:
                hpr = VBase3(0., 0., 0.)
            else:
                point = Point3(normal)
                # project the normal onto the world XY-plane...
                point.z = 0.
                # ...and project that projected point onto the given plane
                # to compute its local forward vector
                y_vec = plane.project(point) - pos
                quat = Quat()
                look_at(quat, y_vec, normal)
                hpr = quat.get_hpr()

            name = "object 0001"
            name = get_unique_name(name, obj_names)
            obj_names.append(name)

            x = y = 10.
            segments = {"x": 1, "y": 1}
            creator = Mgr.do("create_custom_plane", name, x, y, segments, pos)
            model = next(creator)
            model.register(restore=False)
            model.get_pivot().set_hpr(hpr)
            plane_models.append(model)

        return plane_models

    def __create_collision_primitive(self, obj_type, *args):

        if obj_type in ("CollisionSphere", "CollisionInvSphere"):
            name, radius, pos = args
            segments = 16
            inverted = obj_type == "CollisionInvSphere"
            creator = Mgr.do("create_custom_sphere", name, radius, segments, pos, inverted)
        elif obj_type == "CollisionTube":
            name, radius, height, pos, hpr = args
            segments = {"circular": 12, "height": 1, "caps": 1}
            creator = Mgr.do("create_custom_cylinder", name, radius, height, segments, pos)
        elif obj_type == "CollisionBox":
            name, x, y, z, pos = args
            segments = {"x": 1, "y": 1, "z": 1}
            creator = Mgr.do("create_custom_box", name, x, y, z, segments, pos)

        model = next(creator)
        model.register(restore=False)

        if obj_type == "CollisionTube":
            pivot = model.get_pivot()
            pivot.set_hpr(hpr)
            pivot.set_p(pivot, -90.)

        return model

    def __create_collision_model(self, name, polys):

        coords = []
        poly_count = 0

        vertex_format = GeomVertexFormat.get_v3n3()
        vertex_data = GeomVertexData("basic_geom", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        normal_writer = GeomVertexWriter(vertex_data, "normal")
        tris = GeomTriangles(Geom.UH_static)
        row = 0

        for poly in polys:

            points = [point for point in poly]
            rows_by_pos = {}

            for i, point in enumerate(points):
                for impr_crd in coords:
                    if point == impr_crd:
                        points[i] = impr_crd
                        break
                else:
                    coords.append(point)

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
        r, g, b = [random.random() * .4 + .5 for i in range(3)]
        color = (r, g, b, 1.)
        model.set_color(color, update_app=False)
        model.register(restore=False)

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

                obj_name = node_data["new_name"]
                node = node_path.node()
                node_type = node.get_class_type().get_name()

                if node_type == "GeomNode" and Geom.PT_polygons in [geom.get_primitive_type()
                        for geom in node.get_geoms()]:

                    bounds_node = node_path
                    geom_indices = [i for i, geom in enumerate(node.get_geoms())
                                    if geom.get_primitive_type() == Geom.PT_polygons]
                    geom_count = len(geom_indices)

                    materials = self._imported_materials

                    if geom_count > 1:

                        obj = self.__create_model_group(obj_name, node_path.get_transform())
                        obj.get_origin().node().copy_tags(node)
                        obj_names = GlobalData["obj_names"] + self._obj_names
                        obj_names.remove(obj_name)

                        for i in geom_indices:
                            state = node.get_geom_state(i)
                            tmp_np = node_path.attach_new_node("temp")
                            tmp_np.set_state(state)
                            state = tmp_np.get_net_state()
                            tmp_np.remove_node()
                            new_node = GeomNode("basic_geom")
                            new_node.add_geom(node.modify_geom(i).decompose().unify(1000000, False))
                            new_geom = NodePath(new_node)
                            new_geom.set_state(state)
                            member_name = "object 0001"
                            member_name = get_unique_name(member_name, obj_names)
                            obj_names.append(member_name)
                            member = Mgr.do("create_basic_geom", new_geom, member_name, materials).get_model()
                            member.register(restore=False)
                            Mgr.do("add_group_member", member, obj, restore="import")
                            member.get_bbox().update(*new_geom.get_tight_bounds())
                            self._imported_objs.append(member)
                            material = member.get_material()

                            if material and material not in materials:
                                materials.append(material)

                    else:

                        index = geom_indices[0]
                        state = node.get_geom_state(index)
                        tmp_np = node_path.attach_new_node("temp")
                        tmp_np.set_state(state)
                        state = tmp_np.get_net_state()
                        tmp_np.remove_node()
                        new_node = GeomNode("basic_geom")
                        new_node.add_geom(node.modify_geom(index))
                        new_geom = NodePath(new_node)
                        new_geom.set_state(state)
                        new_geom.set_transform(node_path.get_transform())
                        bounds_node = new_geom

                        new_node.decompose()
                        new_node.unify(1000000, False)
                        obj = Mgr.do("create_basic_geom", new_geom, obj_name, materials).get_model()
                        obj.register(restore=False)
                        obj.get_origin().node().copy_tags(node)
                        material = obj.get_material()

                        if material and material not in materials:
                            materials.append(material)

                elif node_type == "CollisionNode":

                    coll_objs = []
                    coll_polys = []
                    coll_planes = []
                    obj_names = GlobalData["obj_names"] + self._obj_names

                    for solid in node.get_solids():

                        obj_type = solid.get_class_type().get_name()

                        if obj_type not in ("CollisionSphere", "CollisionInvSphere", "CollisionTube",
                                            "CollisionBox", "CollisionPlane", "CollisionPolygon"):
                            continue

                        if obj_type == "CollisionPolygon":

                            if solid.is_valid():
                                poly = solid.get_points()
                                coll_polys.append(poly)

                        elif obj_type == "CollisionPlane":

                            coll_planes.append(solid.get_plane())

                        else:

                            name = "object 0001"
                            name = get_unique_name(name, obj_names)
                            obj_names.append(name)

                            if obj_type in ("CollisionSphere", "CollisionInvSphere"):

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

                        for model in self.__create_collision_model(name, coll_polys):
                            yield

                        coll_objs.append(model)
                        self._imported_objs.append(model)

                    if coll_planes:
                        plane_models = self.__create_collision_planes(coll_planes, obj_names)
                        coll_objs.extend(plane_models)
                        self._imported_objs.extend(plane_models)

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

            child_indices = node_data["child_indices"]

            for child_index in child_indices:
                if child_index in hierarchy:
                    child_data = hierarchy[child_index]
                    data.append((child_data, obj_id))

            yield

    def __get_progress_steps(self):

        progress_steps = 0
        hierarchy = self._hierarchy

        for index in self._coll_obj_indices:

            node_data = hierarchy[index]
            node = node_data["node_path"].node()

            coll_poly_count = 0

            for solid in node.get_solids():

                obj_type = solid.get_class_type().get_name()

                if obj_type == "CollisionPolygon" and solid.is_valid():
                    coll_poly_count += 1

            progress_steps += coll_poly_count // 20

        return progress_steps

    def __import(self):

        progress_steps = self.__get_progress_steps()
        gradual = progress_steps > 80

        yield True

        if gradual:
            Mgr.update_remotely("screenshot", "create")
            GlobalData["progress_steps"] = progress_steps

        Mgr.do("update_history_time")

        for step in self.__import_objects():
            if gradual:
                yield True

        self._model_root.remove_node()
        self._model_root = None
        self._hierarchy = {}
        self._obj_index = 0
        self._coll_obj_indices = []
        self._imported_file_type = ""
        self._imported_materials = []

        if not self._imported_objs:
            yield False

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        event_descr = 'Import "{}"'.format(os.path.basename(self._imported_file))
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
            self._coll_obj_indices = []
            self._obj_names = []
            self._imported_file = ""
            self._imported_file_type = ""
            self._imported_materials = []
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

        if do_import and next(process):
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

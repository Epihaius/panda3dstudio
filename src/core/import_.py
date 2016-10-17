from .base import *


class ImportManager(BaseObject):

    def __init__(self):

        self._imported_file_type = ""

        Mgr.add_app_updater("import", self.__import)

    def __create_point_helper(self, name, transform):

        size = 10.
        on_top = True
        colors = {"unselected": (.5, 0., 1., 1.), "selected": (1., 1., 1., 1.)}
        point_helper = Mgr.do("create_custom_point_helper", name, size, on_top, colors, transform)
        point_helper.update_pos()

        return point_helper

    def __create_sphere(self, name, radius, pos):

        segments = 16
        sphere = Mgr.do("create_custom_sphere", name, radius, segments, pos)

        return sphere

    def __create_cylinder(self, name, radius, height, pos):

        segments = {"circular": 12, "height": 1, "caps": 1}
        cylinder = Mgr.do("create_custom_cylinder", name, radius, height, segments, pos)

        return cylinder

    def __create_box(self, name, x, y, z, pos):

        segments = {"x": 1, "y": 1, "z": 1}
        box = Mgr.do("create_custom_box", name, x, y, z, segments, pos)

        return box

    def __create_editable_model(self, name, polys):

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

                vert_data = [vert_data1]

                for pos in positions:
                    vert_data.append({"pos": pos, "normal": normal, "uvs": {0: (0., 0.)}})

                tri_data = {"verts": vert_data}
                tris.append(tri_data)

            poly_data = {"tris": tris, "smoothing": [(0, False)]}
            geom_data.append(poly_data)

        editable_geom = Mgr.do("create_editable_geom", name=name)
        model = editable_geom.get_model()
        r, g, b = [random.random() * .4 + .5 for i in range(3)]
        color = (r, g, b, 1.)
        model.set_color(color, update_app=False)
        geom_data_obj = editable_geom.get_geom_data_object()
        geom_data_obj.process_geom_data(geom_data)
        editable_geom.create()
        model.get_bbox().update(*geom_data_obj.get_origin().get_tight_bounds())

        return model

    def __create_model_group(self, name, transform):

        model_group = Mgr.do("create_group", name, ["model"], "model", transform)

        return model_group

    def __create_collision_group(self, name, transform):

        coll_group = Mgr.do("create_group", name, ["collision"], "collision", transform)

        return coll_group

    def __import_children(self, basic_edit, parent_id, children, objs_to_store):

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
                            new_node = GeomNode("basic_geom_part")
                            new_node.add_geom(node.modify_geom(i))
                            new_geom = NodePath(new_node)
                            new_geom.set_state(state)
                            part_name = "object 0001"
                            part_name = get_unique_name(part_name, GlobalData["obj_names"])
                            new_geom.node().modify_geom(0).decompose_in_place()
                            part = Mgr.do("create_basic_geom", new_geom, part_name).get_model()
                            Mgr.do("add_group_member", part, obj, restore="import")
                            part.get_bbox().update(*new_geom.get_tight_bounds())
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
                        basic_geom = Mgr.do("create_basic_geom", new_geom, obj_name)
                        obj = basic_geom.get_model()

                elif node_type == "CollisionNode":

                    coll_objs = []
                    coll_polys = []

                    for solid in node.get_solids():

                        coll_type = solid.get_class_type().get_name()

                        if coll_type == "CollisionSphere":

                            name = "object 0001"
                            name = get_unique_name(name, GlobalData["obj_names"])
                            radius = solid.get_radius()
                            pos = solid.get_center()
                            sphere = self.__create_sphere(name, radius, pos)
                            coll_objs.append(sphere)

                        elif coll_type == "CollisionTube":

                            name = "object 0001"
                            name = get_unique_name(name, GlobalData["obj_names"])
                            radius = solid.get_radius()
                            a = solid.get_point_a()
                            b = solid.get_point_b()
                            height_vec = V3D(b - a)
                            height = height_vec.length()
                            hpr = height_vec.get_hpr()
                            cylinder = self.__create_cylinder(name, radius, height, a)
                            pivot = cylinder.get_pivot()
                            pivot.set_hpr(hpr)
                            pivot.set_hpr(pivot, -90.)
                            coll_objs.append(cylinder)

                        elif coll_type == "CollisionBox":

                            name = "object 0001"
                            name = get_unique_name(name, GlobalData["obj_names"])
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
                            box = self.__create_box(name, x, y, z, pos)
                            coll_objs.append(box)

                        elif coll_type == "CollisionPolygon":

                            if solid.is_valid():
                                poly = solid.get_points()
                                coll_polys.append(poly)

                        else:

                            continue

                    if coll_polys:
                        name = "object 0001"
                        name = get_unique_name(name, GlobalData["obj_names"])
                        model = self.__create_editable_model(name, coll_polys)
                        coll_objs.append(model)

                    if not coll_objs:
                        continue

                    obj_name = child_name if child_name else "collision object 0001"
                    obj_name = get_unique_name(obj_name, GlobalData["obj_names"])
                    obj = self.__create_collision_group(obj_name, child.get_transform())
                    objs_to_store.extend(coll_objs)
                    Mgr.do("add_group_members", coll_objs, obj, add_to_hist=False, restore="import")

                else:

                    obj = self.__create_point_helper(obj_name, child.get_transform())

                obj.restore_link(parent_id, None)

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

        children = model_root.get_children()

        if not children:
            return

        self._imported_file_type = path.get_extension()
        Mgr.do("update_history_time")
        objs_to_store = []
        self.__import_children(basic_edit, None, children, objs_to_store)
        model_root.remove_node()
        self._imported_file_type = ""

        if not objs_to_store:
            return

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        event_descr = 'Import "%s"' % os.path.basename(filename)

        for obj in objs_to_store:
            obj_data[obj.get_id()] = obj.get_data_to_store("creation")

        event_data["object_ids"] = set(Mgr.get("object_ids"))
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(ImportManager)

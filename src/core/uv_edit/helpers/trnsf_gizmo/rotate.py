from ...base import *


class RotationComponent:

    def __init__(self, gizmo):

        self._gizmo = gizmo
        self._type = "rotate"
        self._origin = gizmo.root.attach_new_node("uv_rotation_gizmo")
        self._render_mask = UVMgr.get("render_mask")
        self._picking_mask = UVMgr.get("picking_mask")
        self._handle_root = self._origin.attach_new_node("handle_root")
        self._handle = None
        self._handle_names = {}
        self._hilited_handles = []
        self._active = True

        self.__create_handles()

    def __create_handles(self):

        self._radius = .15
        self._origin.set_scale(self._radius)

        yellow = (1., 1., 0., 1.)

        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        plane = "uv"
        color_id = self._gizmo.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = plane
        handle = self.__create_axis_handle(self._handle_root, color_vec, plane, "w_axis_handle")
        handle.set_color(yellow)
        self._handle = handle

    def __create_axis_handle(self, parent, color, plane, node_name):

        segments = 10
        angle = .4 * math.pi / segments

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("axis_circle_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        circle = GeomLines(Geom.UH_static)
        offsets = (.55 * math.pi, 1.55 * math.pi)

        for j, offset in enumerate(offsets):

            x = math.cos(offset)
            z = math.sin(offset)
            pos_writer.add_data3(x, 0., z)
            col_writer.add_data4(color)

            for i in range(1, segments + 1):
                x = math.cos(offset + angle * i)
                z = math.sin(offset + angle * i)
                pos_writer.add_data3(x, 0., z)
                col_writer.add_data4(color)
                k = j * (segments + 1) + i
                circle.add_vertices(k - 1, k)

        circle_geom = Geom(vertex_data)
        circle_geom.add_primitive(circle)
        circle_node = GeomNode(node_name)
        circle_node.add_geom(circle_geom)
        circle_np = parent.attach_new_node(circle_node)

        return circle_np

    def get_transform_type(self):

        return self._type

    def hilite_handle(self, color_id):

        if color_id not in self._handle_names:
            return

        hilited_handles = []
        handle_name = self._handle_names[color_id]
        hilited_handles.append(handle_name)

        if self._hilited_handles != hilited_handles:
            self.remove_hilite()
            self._hilited_handles = hilited_handles
            cyan = (0., 1., 1., 1.)
            self._handle.set_color(cyan)
            GD["uv_cursor"] = self._type

    def remove_hilite(self):

        if self._hilited_handles:

            if self._active:
                rgb = (1., 1., 0., 1.)
            else:
                rgb = (.5, .5, .5, 1.)

            self._handle.set_color(rgb)
            self._hilited_handles = []
            GD["uv_cursor"] = ""

    def select_handle(self, color_id):

        if color_id in self._handle_names:
            return "w"

    def get_active_axes(self):

        return "w"

    def set_active_axes(self, axes):

        self.remove_hilite()

    @property
    def active(self):

        return self._active

    @active.setter
    def active(self, active):

        if self._active == active:
            return

        if active:
            rgb = (1., 1., 0., 1.)
        else:
            rgb = (.5, .5, .5, 1.)

        self._handle.set_color(rgb)
        self._active = active

    def show(self):

        self._origin.show()

    def hide(self):

        self._origin.hide()

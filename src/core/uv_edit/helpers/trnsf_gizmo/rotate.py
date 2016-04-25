from ...base import *


class RotationComponent(object):

    def __init__(self, gizmo):

        self._gizmo = gizmo
        self._type = "rotate"
        self._origin = gizmo.get_root().attach_new_node("uv_rotation_gizmo")
        self._render_mask = UVMgr.get("render_mask")
        self._picking_mask = UVMgr.get("picking_mask")
        self._handle_root = self._origin.attach_new_node("handle_root")
        self._handles = {"axes": {}, "planes": {}, "quads": {}}
        self._handle_names = {}
        self._hilited_handles = []
        self._axis_colors = {}
        self._selected_axes = "uv"

        self.__create_handles()

    def __create_handles(self):

        self._radius = .15
        self._origin.set_scale(self._radius)

        yellow = VBase4(1., 1., 0., 1.)

        self._axis_colors = {"uv": yellow}
        pickable_type_id = PickableTypes.get_id("transf_gizmo")

        plane = "uv"
        color_id = self._gizmo.get_next_picking_color_id()
        color_vec = get_color_vec(color_id, pickable_type_id)
        self._handle_names[color_id] = plane
        handle = self.__create_axis_handle(self._handle_root, color_vec, plane, "w_axis_handle")
        handle.set_color(self._axis_colors[plane])
        self._handles["planes"][plane] = handle

    def __create_axis_handle(self, parent, color, plane, node_name):

        segments = 10
        angle = .4 * math.pi / segments

        vertex_format = GeomVertexFormat.get_v3cp()
        vertex_data = GeomVertexData("axis_circle_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        circle = GeomLines(Geom.UH_static)
        offsets = (.55 * math.pi, 1.55 * math.pi)

        for j, offset in enumerate(offsets):

            x = math.cos(offset)
            z = math.sin(offset)
            pos_writer.add_data3f(x, 0., z)
            col_writer.add_data4f(color)

            for i in xrange(1, segments + 1):
                x = math.cos(offset + angle * i)
                z = math.sin(offset + angle * i)
                pos_writer.add_data3f(x, 0., z)
                col_writer.add_data4f(color)
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

        if handle_name in self._handles["planes"]:
            hilited_handles.append(handle_name)

        if self._hilited_handles != hilited_handles:

            self.remove_hilite()
            self._hilited_handles = hilited_handles

            cyan = VBase4(0., 1., 1., 1.)

            for handle_name in hilited_handles:
                self._handles["planes"][handle_name].set_color(cyan)

    def remove_hilite(self):

        if self._hilited_handles:

            yellow = VBase4(1., 1., 0., 1.)
            yellow_alpha = VBase4(1., 1., 0., .25)

            for handle_name in self._hilited_handles:
                color = yellow if handle_name == self._selected_axes \
                    else self._axis_colors[handle_name]
                self._handles["planes"][handle_name].set_color(color)

            self._hilited_handles = []

    def select_handle(self, color_id):

        if color_id in self._handle_names:
            return "w"

    def set_active_axes(self, axes):

        self.remove_hilite()

    def show(self):

        self._origin.show()

    def hide(self):

        self._origin.hide()

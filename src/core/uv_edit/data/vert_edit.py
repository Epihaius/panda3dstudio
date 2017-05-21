from ..base import *
from .vert import MergedVertex
from .edge import MergedEdge


class VertexEditBase(BaseObject):

    def break_vertices(self):

        selected_vert_ids = self._selected_subobj_ids["vert"]

        if not selected_vert_ids:
            return False

        verts = self._subobjs["vert"]
        merged_verts = self._merged_verts
        verts_to_break = set(merged_verts[v_id] for v_id in selected_vert_ids)
        edge_ids = set(e_id for v in verts_to_break for v_id in v
                       for e_id in verts[v_id].get_edge_ids())

        return self.split_edges(edge_ids)


class VertexEditManager(BaseObject):

    def setup(self):

        Mgr.add_interface_updater("uv_window", "vert_break", self.__break_vertices)

    def __break_vertices(self):

        selection = self._selections[self._uv_set_id]["vert"]
        uv_data_objs = selection.get_uv_data_objects()

        for data_obj in uv_data_objs:
            data_obj.break_vertices()

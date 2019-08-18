from .. import *


class VertexMerger:

    def merge_duplicate_vertices(self, geom_data_obj):

        self.__check_duplicate_verts(geom_data_obj)
        self.__create_vertex_data(geom_data_obj)
        self.__create_geom_primitive()
        geom_node = self.__create_geom_node()

        return NodePath(geom_node)
      
    def __set_merged_verts_to_compare(self, verts, merged_vert):

        self.verts1 = [verts[v_id] for v_id in merged_vert]
        self.verts2 = self.verts1[:]

    def __compare_merged_verts(self):

        for vert1 in self.verts1:

            row1 = vert1.row_index

            if row1 not in self.dupes:
                for vert2 in self.verts2[:]:
                    self.__check_if_verts_equal(vert1, vert2, row1)

    def __check_if_verts_equal(self, vert1, vert2, row1):

        if vert2 is not vert1:

            pos1 = vert1.get_pos()
            normal1 = vert1.normal
            uv1 = vert1.get_uvs()
            col1 = vert1.color

            pos2 = vert2.get_pos()
            normal2 = vert2.normal
            uv2 = vert2.get_uvs()
            col2 = vert2.color

            if pos2 == pos1 and normal2 == normal1 and uv2 == uv1 and col2 == col1:
                row2 = vert2.row_index
                self.rows.remove(row2)
                self.verts2.remove(vert2)
                self.dupes[row2] = row1

    def __create_vertex_data(self, geom_data_obj):

        self.geom = geom_data_obj.toplevel_geom.node().get_geom(0)
        vdata_src = self.geom.get_vertex_data()
        self.vdata_dest = GeomVertexData(vdata_src)
        self.vdata_dest.unclean_set_num_rows(len(self.rows))
        thread = Thread.get_main_thread()

        for row_dest, row_src in enumerate(self.rows):
            self.vdata_dest.copy_row_from(row_dest, vdata_src, row_src, thread)

        for row2, row1 in list(self.dupes.items()):
            self.dupes[row2] = self.rows.index(row1)

    def __create_geom_primitive(self): 

        prim_src = self.geom.get_primitive(0)
        self.prim_dest = prim_dest = GeomTriangles(Geom.UH_static)
        rows_src = prim_src.get_vertex_list()
        dupes = self.dupes
        rows = self.rows
        rows_dest = [dupes[row] if row in dupes else rows.index(row) for row in rows_src]

        for indices in (rows_dest[i:i + 3] for i in range(0, len(rows_dest), 3)):
            prim_dest.add_vertices(*indices)

    def __create_geom_node(self):

        geom_dest = Geom(self.vdata_dest)
        geom_dest.add_primitive(self.prim_dest)
        geom_node = GeomNode("")
        geom_node.add_geom(geom_dest)

        return geom_node

    def __check_duplicate_verts(self, geom_data_obj):

        verts = geom_data_obj.get_subobjects("vert")
        merged_verts = set(geom_data_obj.merged_verts.values())
        self.rows = list(range(len(verts)))
        self.dupes = {}

        for merged_vert in merged_verts:
            self.__set_merged_verts_to_compare(verts, merged_vert)
            self.__compare_merged_verts()

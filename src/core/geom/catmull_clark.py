# This module contains a Python adaptation of the Catmull-Clark subdivision
# surface algorithm implemented in JavaScript, as found here:
# https://github.com/Erkaman/gl-catmull-clark/blob/master/index.js
# Its license is included below:
'''
This software is released under the MIT license:

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

from panda3d.core import Point3, Vec3


class Point:

    __slots__ = ("_pos", "new_point", "index", "faces", "edges")

    def __init__(self, x=0., y=0., z=0.):

        self._pos = [x, y, z]
        self.new_point = None
        self.index = None
        self.faces = []
        self.edges = set()

    def __getitem__(self, index):

        return self._pos[index]

    def __setitem__(self, index, rhs):

        self._pos[index] = rhs

    def __add__(self, rhs):

        x1, y1, z1 = self._pos
        x2, y2, z2 = rhs

        return Point(x1 + x2, y1 + y2, z1 + z2)

    def __iadd__(self, rhs):

        x1, y1, z1 = self._pos
        x2, y2, z2 = rhs
        self._pos = [x1 + x2, y1 + y2, z1 + z2]

        return self

    def __mul__(self, rhs):

        x, y, z = self._pos

        return Point(x * rhs, y * rhs, z * rhs)

    def __imul__(self, rhs):

        x, y, z = self._pos
        self._pos = [x * rhs, y * rhs, z * rhs]

        return self

    def __div__(self, rhs):

        x, y, z = self._pos

        return Point(x / rhs, y / rhs, z / rhs)

    def __idiv__(self, rhs):

        x, y, z = self._pos
        self._pos = [x / rhs, y / rhs, z / rhs]

        return self

    def __truediv__(self, rhs):

        x, y, z = self._pos

        return Point(x / rhs, y / rhs, z / rhs)

    def __itruediv__(self, rhs):

        x, y, z = self._pos
        self._pos = [x / rhs, y / rhs, z / rhs]

        return self


class UV:

    __slots__ = ("_uv", "point_index", "index", "faces", "edges")

    def __init__(self, u=0., v=0., point_index=0):

        self._uv = [u, v]
        # store the index of the associated point in world space
        self.point_index = point_index
        self.index = None
        self.faces = []
        self.edges = set()

    def __getitem__(self, index):

        return self._uv[index]

    def __setitem__(self, index, rhs):

        self._uv[index] = rhs

    def __add__(self, rhs):

        u1, v1 = self._uv
        u2, v2 = rhs

        return UV(u1 + u2, v1 + v2)

    def __iadd__(self, rhs):

        u1, v1 = self._uv
        u2, v2 = rhs
        self._uv = [u1 + u2, v1 + v2]

        return self

    def __mul__(self, rhs):

        u, v = self._uv

        return UV(u * rhs, v * rhs)

    def __imul__(self, rhs):

        u, v = self._uv
        self._uv = [u * rhs, v * rhs]

        return self

    def __div__(self, rhs):

        u, v = self._uv

        return UV(u / rhs, v / rhs)

    def __idiv__(self, rhs):

        u, v = self._uv
        self._uv = [u / rhs, v / rhs]

        return self

    def __truediv__(self, rhs):

        u, v = self._uv

        return UV(u / rhs, v / rhs)

    def __itruediv__(self, rhs):

        u, v = self._uv
        self._uv = [u / rhs, v / rhs]

        return self


class Edge:

    __slots__ = ("_points", "point", "mid_point", "faces")

    def __init__(self, point1, point2):

        self._points = [point1, point2]
        self.point = None
        self.mid_point = None
        self.faces = []

    def __getitem__(self, index):

        return self._points[index]


class Face:

    __slots__ = ("_points", "point", "edges")

    def __init__(self):

        self._points = []
        self.point = None
        self.edges = []

    def __getitem__(self, index):

        return self._points[index]

    def __len__(self):

        return len(self._points)

    def append(self, point):

        self._points.append(point)


def _quads_to_tris(quads):

    tris = []

    for quad in quads:
        tris.append([quad[0], quad[1], quad[2]])
        tris.append([quad[0], quad[2], quad[3]])

    return tris


def _sort(edge):

    '''
    Example:
        given (0, 4), return (0, 4);
        given (2, 1), return (1, 2).
    '''

    return edge if edge[0] < edge[1] else (edge[1], edge[0])


# Implement the Catmull-Clark subdivision for UVs
def _subdivide_uvs(uvs, old_uv_faces, quads):

    # Original UVs, indexed by their indices.
    # For every UV, we store adjacent UV faces and adjacent UV edges.
    original_uvs = {}

    # Original UV faces, in their original order.
    # For every UV face, we store the UV edges, the UV points, and the UV face point.
    uv_faces = {}

    # Original UV edges, indexed by the sorted indices of their UVs.
    # So the UV edge whose UVs have indices `6` and `2` will be 
    # indexed by the tuple (2, 6).
    uv_edges = {}

    # First we collect all the information that we need to run the algorithm.
    # Each UV must know its adjacent edges and faces.
    # Each face must know its edges and UVs.
    # Each edge must know its adjacent faces and UVs.
    # We collect all this information in the following loop.

    for i in range(len(old_uv_faces)):

        uv_indices = old_uv_faces[i]

        # initialize:
        uv_faces[i] = uv_face = Face()

        # go through all of the UVs of the UV face
        for uv_index in uv_indices:

            if uv_index in original_uvs:
                # use a previously created UV object
                uv_obj = original_uvs[uv_index]
            else:
                # create a new UV object
                (u, v), point_index = uvs[uv_index]
                uv_obj = UV(u, v, point_index)
                original_uvs[uv_index] = uv_obj

            # every UV should hold a reference to its faces
            uv_obj.faces.append(uv_face)
            # every face should know its UVs
            uv_face.append(uv_obj)

        avg = UV()

        # now compute the face point (see Wikipedia)
        for uv in uv_face:
            avg += uv

        avg /= len(uv_face)
        uv_face.point = avg

        index_count = len(uv_indices)

        # go through all of the edges of the face
        for j in range(index_count):

            i1 = j
            i2 = 0 if i1 + 1 == index_count else i1 + 1
            edge = (uv_indices[i1], uv_indices[i2])

            # every edge is represented by the sorted indices of its UVs
            # (the sorting ensures that (1, 2) and (2, 1) are considered to be
            # the same edge, which they are)
            edge = _sort(edge)

            if edge in uv_edges:
                # use a previously created edge object
                edge_obj = uv_edges[edge]
            else:
                # create a new edge object
                edge_obj = Edge(original_uvs[edge[0]], original_uvs[edge[1]])
                uv_edges[edge] = edge_obj

            # every edge should know its adjacent faces
            edge_obj.faces.append(uv_face)

            # every UV should know its adjacent edges
            edge_obj[0].edges.add(edge_obj)
            edge_obj[1].edges.add(edge_obj)

            # every face should know its edges
            uv_face.edges.append(edge_obj)

    # Compute the edge point and the midpoint of every edge.
    for edge in uv_edges.values():

        # compute the midpoint
        edge.mid_point = (edge[0] + edge[1]) * .5

        if len(edge.faces) == 1:
            # the edge belongs to a hole border;
            # the edge point is just the midpoint in this case
            edge.point = edge.mid_point
            continue

        avg = UV()
        count = 0

        # add face points of edge
        for uv_face in edge.faces:
            avg += uv_face.point
            count += 1

        # sum together with the two endpoints
        for uv in edge:
            avg += uv
            count += 1

        # finally, compute edge point
        avg /= count
        edge.point = avg

    new_uvs = []
    new_uv_faces = []

    def get_index():

        index = 0

        while True:
            yield index
            index += 1

    index_generator = get_index()

    # We create new indices using the following method.
    # The index of every UV vertex is stored in the UV object, in an attribute named `index`.

    def get_new_vertex_index(uv):

        uv.index = next(index_generator)
        new_uvs.append((uv[:], uv.point_index))

        return uv.index

    # We go through all of the faces.
    # We subdivide n-sided faces into n new quads.

    for i in range(len(uv_faces)):

        uv_face = uv_faces[i]

        for j in range(len(uv_face)):

            edge_count = len(uv_face.edges)
            a_, b_, c_, d_ = quads.pop(0)
            a = uv_face[j]
            a.point_index = a_.index
            b = uv_face.edges[j % edge_count].point
            b.point_index = b_.index
            c = uv_face.point
            c.point_index = c_.index
            d = uv_face.edges[(j + edge_count - 1) % edge_count].point
            d.point_index = d_.index

            ia = get_new_vertex_index(a) if a.index is None else a.index
            ib = get_new_vertex_index(b) if b.index is None else b.index
            ic = get_new_vertex_index(c) if c.index is None else c.index
            id = get_new_vertex_index(d) if d.index is None else d.index

            new_uv_faces.append([id, ia, ib, ic])

    return new_uvs, new_uv_faces


# Implement Catmull-Clark subdivision, as it is described on Wikipedia
def _subdivide(positions, uvs, old_faces, old_uv_faces):

    # Original points, indexed by their indices.
    # For every point, we store adjacent faces and adjacent edges.
    original_points = {}

    # Original faces, in their original order.
    # For every face, we store the edges, the points, and the face point.
    faces = {}

    # Original edges, indexed by the sorted indices of their points.
    # So the edge whose points have indices `6` and `2` will be 
    # indexed by the tuple (2, 6).
    edges = {}

    # First we collect all the information that we need to run the algorithm.
    # Each point must know its adjacent edges and faces.
    # Each face must know its edges and points.
    # Each edge must know its adjacent faces and points.
    # We collect all this information in the following loop.

    for i in range(len(old_faces)):

        point_indices = old_faces[i]

        # initialize:
        faces[i] = face = Face()

        # go through all of the points of the face
        for point_index in point_indices:

            if point_index in original_points:
                # use a previously created point object
                point_obj = original_points[point_index]
            else:
                # create a new point object
                point_obj = Point(*positions[point_index])
                original_points[point_index] = point_obj

            # every point should have a reference to its faces
            point_obj.faces.append(face)
            # every face should know its points
            face.append(point_obj)

        avg = Point()

        # now compute the face point (see Wikipedia)
        for p in face:
            avg += p

        avg /= len(face)
        face.point = avg

        index_count = len(point_indices)

        # go through all of the edges of the face
        for j in range(index_count):

            i1 = j
            i2 = 0 if i1 + 1 == index_count else i1 + 1
            edge = (point_indices[i1], point_indices[i2])

            # every edge is represented by the sorted indices of its points
            # (the sorting ensures that (1, 2) and (2, 1) are considered to be
            # the same edge, which they are)
            edge = _sort(edge)

            if edge in edges:
                # use a previously created edge object
                edge_obj = edges[edge]
            else:
                # create a new edge object
                edge_obj = Edge(original_points[edge[0]], original_points[edge[1]])
                edges[edge] = edge_obj

            # every edge should know its adjacent faces
            edge_obj.faces.append(face)

            # every point should know its adjacent edges
            edge_obj[0].edges.add(edge_obj)
            edge_obj[1].edges.add(edge_obj)

            # every face should know its edges
            face.edges.append(edge_obj)

    # Compute the edge point and the midpoint of every edge.
    for edge in edges.values():

        # compute the midpoint
        edge.mid_point = (edge[0] + edge[1]) * .5

        if len(edge.faces) == 1:
            # the edge belongs to a hole border;
            # the edge point is just the midpoint in this case
            edge.point = edge.mid_point
            continue

        avg = Point()
        count = 0

        # add face points of edge
        for face in edge.faces:
            avg += face.point
            count += 1

        # sum together with the two endpoints
        for point in edge:
            avg += point
            count += 1

        # finally, compute edge point
        avg /= count
        edge.point = avg

    # Each original point is moved to the position (F + 2R + (n-3)P) / n.
    # See the Wikipedia article for more details.

    for i in range(len(positions)):

        point = original_points[i]
        new_point = Point()
        n = len(point.faces)

        if n != len(point.edges):

            # the point lies on the border of a hole;
            # the new point is the weighted average of the endpoints of both
            # border edges connected at the original point and that point (p):
            # new_point = 1/8 ep1 + 1/8 ep2 + 6/8 p
            # where ep1 and ep2 are the two border points neighboring p;
            # using the midpoints (mp1 and mp2) of those border edges, since:
            # mp1 == 1/2 ep1 + 1/2 p
            # and:
            # mp2 == 1/2 ep2 + 1/2 p
            # this comes down to:
            # new_point = 1/4 mp1 + 1/4 mp2 + 1/2 p

            for edge in point.edges:
                if len(edge.faces) == 1:
                    new_point += edge.mid_point * .25

            new_point += point * .5
            point.new_point = new_point

            continue

        avg = Point()

        for face in point.faces:
            avg += face.point

        avg /= n
        new_point += avg
        avg = Point()

        for edge in point.edges:
            avg += edge.mid_point

        avg /= n
        new_point += avg * 2.
        new_point += point * (n - 3)
        new_point /= n
        point.new_point = new_point

    new_positions = []
    new_faces = []
    quads = []

    def get_index():

        index = 0

        while True:
            yield index
            index += 1

    index_generator = get_index()

    # We create new indices using the following method.
    # The index of every vertex is stored in the Point object, in an attribute named `index`.

    def get_new_vertex_index(p):

        p.index = next(index_generator)
        new_positions.append(p[:])

        return p.index

    # We go through all of the faces.
    # We subdivide n-sided faces into n new quads.

    for i in range(len(faces)):

        face = faces[i]

        for j in range(len(face)):

            point = face[j]
            edge_count = len(face.edges)
            a = point.new_point
            b = face.edges[j % edge_count].point
            c = face.point
            d = face.edges[(j + edge_count - 1) % edge_count].point

            ia = get_new_vertex_index(a) if a.index is None else a.index
            ib = get_new_vertex_index(b) if b.index is None else b.index
            ic = get_new_vertex_index(c) if c.index is None else c.index
            id = get_new_vertex_index(d) if d.index is None else d.index

            new_faces.append([id, ia, ib, ic])
            quads.append([a, b, c, d])

    new_uvs, new_uv_faces = _subdivide_uvs(uvs, old_uv_faces, quads)

    return {"positions": new_positions, "uvs": new_uvs,
            "faces": new_faces, "uv_faces": new_uv_faces}


def subdivide(positions, uvs, faces, uv_faces, subdivision_count):

    if subdivision_count < 1:
        raise RuntimeError("`subdivision_count` must be a positive number!")

    data = {"positions": positions, "uvs": uvs, "faces": faces, "uv_faces": uv_faces}

    for i in range(subdivision_count):
        data = _subdivide(data["positions"], data["uvs"], data["faces"], data["uv_faces"])

    data["faces"] = _quads_to_tris(data["faces"])

    return data


def convert_data(subdiv_data, vert_normals):

    positions = subdiv_data["positions"]
    uvs = subdiv_data["uvs"]
    subdiv_uv_faces = subdiv_data["uv_faces"]
    geom_data = []
    processed_data = {}
    processed_mvs = []
    processed_uv_mvs = []

    for face in subdiv_uv_faces:

        for i in face:

            vert_data = {}
            (u, v), j = uvs[i]
            vert_data["pos"] = Point3(*positions[j])
            vert_data["normal"] = Vec3(vert_normals[j])
            vert_data["uvs"] = {0: (u, v)}

            if j in processed_mvs:
                vert_data["pos_ind"] = processed_mvs.index(j)
            else:
                vert_data["pos_ind"] = len(processed_mvs)
                processed_mvs.append(j)

            if i in processed_uv_mvs:
                vert_data["uv_ind"] = processed_uv_mvs.index(i)
            else:
                vert_data["uv_ind"] = len(processed_uv_mvs)
                processed_uv_mvs.append(i)

            processed_data[i] = vert_data

        tris = []

        for indices in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
            tri_data = [processed_data[i] for i in indices]
            tris.append(tri_data)

        poly_verts = [processed_data[i] for i in face]
        poly_data = {"verts": poly_verts, "tris": tris}
        geom_data.append(poly_data)

    return geom_data

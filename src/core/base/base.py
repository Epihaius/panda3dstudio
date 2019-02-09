from ...base import logging, re, pickle, GlobalData, ObjectName, get_unique_name, DirectObject
from panda3d.core import *
from collections import OrderedDict
import weakref
import sys
import os
import math
import random
import time
import datetime
import copy
import struct

GFX_PATH = "res/"


# All objects that need access to core variables should derive from the
# following class
class BaseObject(object):

    world = None
    screen = None
    viewport = None
    mouse_watcher = None
    cam = None

    _defaults = {
        "data_retriever": lambda *args, **kwargs: None
    }

    _verbose = False

    @classmethod
    def init(cls, world, screen, viewport, mouse_watcher, verbose):

        cls.world = world
        cls.screen = screen
        cls.viewport = viewport
        cls.mouse_watcher = mouse_watcher
        cls._verbose = verbose

    @classmethod
    def set_cam(cls, cam):

        if not cls.cam:
            cls.cam = cam

    def __init__(self):

        # structure to store callables through which data can be retrieved by id
        self._data_retrievers = {}

    def setup(self, *args, **kwargs):
        """
        Should be called to set up things that cannot be handled during __init__(),
        e.g. because they depend on objects that were not created yet.
        Should return True if successful.

        Override in derived class.

        """

        return True

    def expose(self, data_id, retriever):
        """ Make data publicly available by id through a callable """

        self._data_retrievers[data_id] = retriever

    def get(self, data_id, *args, **kwargs):
        """
        Obtain data by id. The arguments provided will be passed to the callable
        that returns the data.

        """

        if data_id not in self._data_retrievers:

            logging.warning('CORE: data "{}" is not defined.'.format(data_id))

            if self._verbose:
                print('CORE warning: data "{}" is not defined.'.format(data_id))

        retriever = self._data_retrievers.get(data_id, self._defaults["data_retriever"])

        return retriever(*args, **kwargs)


# All main objects, especially those that need to be set up at the start of the
# program, should be added to the following class
class MainObjects(object):

    _classes = {}
    _objs = {}
    _setup_results = {}

    @classmethod
    def add_class(cls, main_cls, interface_id="main"):

        cls._classes.setdefault(interface_id, []).append(main_cls)

    @classmethod
    def init(cls, interface_id="main"):

        for main_cls in cls._classes.get(interface_id, []):
            cls._objs.setdefault(interface_id, []).append(main_cls())

    @classmethod
    def setup(cls, interface_id="main"):

        objs_to_setup = cls._objs.get(interface_id, [])[:]

        # if an object's setup failed because it depends on the setup of another
        # object, it will be tried again later
        while objs_to_setup:

            setup_successful = False

            for obj in objs_to_setup[:]:

                setup_result = obj.setup()

                if setup_result:
                    cls._setup_results.setdefault(interface_id, []).append(setup_result)
                    setup_successful = True
                    objs_to_setup.remove(obj)

            if not setup_successful:
                msg = 'Setup failed for one or more main objects!'
                logging.critical(msg)
                raise AssertionError(msg)

        del cls._setup_results[interface_id]

    @classmethod
    def get_setup_results(cls, interface_id="main"):
        """
        This method can be called by the main objects during their setup to check
        if the setup of a particular main object has already successfully completed.

        """

        return cls._setup_results.get(interface_id, [])


class _PendingTask(object):

    _long_process_handler = None

    @classmethod
    def init(cls, long_process_handler):

        cls._long_process_handler = long_process_handler

    def __init__(self, func, gradual=False, process_id="", descr="", cancellable=False):

        self._func = func
        self._process_id = process_id
        self._descr = descr
        self._cancellable = cancellable
        self.gradual = gradual

    def __call__(self):

        if self.gradual:

            process = self._func()

            if next(process):
                self._long_process_handler(process, self._process_id, self._descr, self._cancellable)
            else:
                self.gradual = False

        else:

            self._func()


class _Tasks(object):

    def __init__(self):

        self._data = {}

    def __call__(self):

        return self._data

    def __lt__(self, other):

        return id(self) < id(other)

    def __le__(self, other):

        return id(self) <= id(other)

    def __gt__(self, other):

        return id(self) < id(other)

    def __ge__(self, other):

        return id(self) <= id(other)


class PendingTasks(object):

    _tasks = {}
    _sorted_tasks = []
    _task_ids = {
        "object": (
            "set_geom_obj",
            "merge_subobjs",
            "share_normals",
            "restore_geometry",
            "unregister_subobjs",
            "register_subobjs",
            "update_picking_col_id_ranges",
            "set_subobj_sel",
            "upd_subobj_sel",
            "upd_verts_to_transf",
            "set_subobj_transf",
            "set_uvs",
            "set_poly_triangles",
            "set_poly_smoothing",
            "flip_normals",
            "set_normals",
            "set_normal_lock",
            "set_material",
            "update_tangent_space",
            "set_geom_data",
            "make_editable",
            "update_selection",
            "set_obj_level",
            "update_texproj",
            "object_removal",
            "object_linking",
            "pivot_transform",
            "origin_transform",
            "center_group_pivot",
            "update_group_bboxes",
            "set_group_member_types",
            "obj_link_viz_update",
            "obj_transf_info_reset"
        ),
        "ui": (
            "coord_sys_update",
            "transf_center_update",
            "update_selection"
        ),
        "uv_object": (
            "update_selection"
        ),
        "uv_ui": (
            "update_selection"
        )
    }
    _is_handling_tasks = False
    _is_suspended = False

    @classmethod
    def add(cls, task, task_id, task_type="", sort=None, id_prefix=None,
            gradual=False, process_id="", descr="", cancellable=False):
        """
        Add a task that needs to be handled later - and only once - through a call
        to handle(), optionally with a type and/or sort value.
        Additionally, a prefix for the task ID can be given to make it unique (so
        this task doesn't overwrite a previously added task with the same ID and
        type), while retaining the sort value associated with the given task_id (if
        the given sort value is None).

        """

        if cls._is_handling_tasks:
            return False

        if sort is None:

            task_ids = cls._task_ids.get(task_type, ())

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        if id_prefix:
            task_id = "{}_{}".format(id_prefix, task_id)

        pending_task = _PendingTask(task, gradual, process_id, descr, cancellable)
        t = _Tasks()
        cls._tasks.setdefault(task_type, {}).setdefault(sort, t)()[task_id] = pending_task

        return True

    @classmethod
    def remove(cls, task_id, task_type="", sort=None):
        """
        Remove the task with the given ID (and optionally, type and/or sort value)
        and return it (or None if not found).

        """

        if cls._is_handling_tasks:
            return

        if sort is None:

            task_ids = cls._task_ids.get(task_type, ())

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        return cls._tasks.get(task_type, {}).get(sort, _Tasks())().pop(task_id, None)

    @classmethod
    def clear(cls, task_type=None):
        """
        Clear the tasks of the given type if it is specified, or all tasks if it is
        None.

        """

        if cls._sorted_tasks:
            cls._sorted_tasks = []
            cls._is_handling_tasks = False

        if cls._is_handling_tasks:
            return

        (cls._tasks if task_type is None else cls._tasks.get(task_type, {})).clear()

    @classmethod
    def handle(cls, task_types=None, sort_by_type=False):
        """
        Handle tasks that were added through add(), in an order that corresponds to
        their sort values (and optionally, their type).

        If a list of task_types is given, only those types of tasks will be handled.

        If sort_by_type is True, tasks will first be processed in the order that
        their types appear in the list of task_types, and then by sort value.
        Otherwise, task types are ignored and the tasks are handled in the order
        given by their sort values only.

        """

        if cls._is_suspended:
            return

        if cls._is_handling_tasks and not cls._sorted_tasks:
            return

        cls._is_handling_tasks = True

        if cls._sorted_tasks:

            sorted_tasks = cls._sorted_tasks
            cls._sorted_tasks = []

        else:

            if not cls._tasks:
                cls._is_handling_tasks = False
                return

            pending_tasks = cls._tasks

            if task_types is None:
                task_types = list(pending_tasks.keys())

            if sort_by_type:
                sorted_tasks = [task for task_type in task_types for _, tasks in
                                sorted(list(pending_tasks.pop(task_type, {}).items()))
                                for task in tasks().values()]
            else:
                l = (i for task_type in task_types for i in pending_tasks.pop(task_type, {}).items())
                sorted_tasks = [task for _, tasks in sorted(l) for task in tasks().values()]

        while sorted_tasks:

            task = sorted_tasks.pop(0)
            task()

            if task.gradual:

                if not sorted_tasks:
                    dummy_task = _PendingTask(lambda: None)
                    sorted_tasks.append(dummy_task)

                cls._sorted_tasks = sorted_tasks
                return

        cls._is_handling_tasks = False

    @classmethod
    def get_sort(cls, task_id, task_type=""):
        """
        Return the sort value of the task with the given ID, or None if the task ID
        is not defined.

        """

        task_ids = cls._task_ids.get(task_type, ())

        if task_id in task_ids:
            return task_ids.index(task_id)

    @classmethod
    def suspend(cls, is_suspended=True):
        """
        Set whether the handling of tasks should be suspended or resumed.

        """

        cls._is_suspended = is_suspended


# All pickable object types should be registered through the following class;
# certain non-editable types like gizmo handles should be considered "special"
class PickableTypes(object):

    _count = 0
    _special_types = []
    _types = {}
    _type_ids = {}

    @classmethod
    def add(cls, pickable_type, special=False):

        cls._types[cls._count] = pickable_type
        cls._type_ids[pickable_type] = cls._count
        old_count = cls._count
        cls._count += 1

        if special:
            cls._special_types.append(pickable_type)

        return old_count

    @classmethod
    def get(cls, type_id):

        return cls._types.get(type_id)

    @classmethod
    def get_all(cls):

        return [t for t in cls._types.values() if t not in cls._special_types]

    @classmethod
    def get_id(cls, pickable_type):

        return cls._type_ids.get(pickable_type)


# All managers of non-pickable objects should use the following generator function
# to generate object IDs containing a timestamp and index to make them unique
def id_generator():

    prev_time = 0
    prev_index = 0

    while True:

        cur_time = int(time.time())
        index = prev_index + 1 if cur_time == prev_time else 0
        prev_time = cur_time
        prev_index = index

        yield (cur_time, index)


def get_color_vec(color_id, alpha):

    r = (color_id >> 16)
    g = (color_id ^ (r << 16)) >> 8
    b = (color_id ^ (r << 16) ^ (g << 8))

    return VBase4(r, g, b, alpha) / 255.


# The following class allows a position (passed in as a tuple or list) to be
# used as a dictionary key when 2 identical positions should still be treated
# as different keys (e.g. to differentiate between two vertices that share the
# same location in space).
class PosObj(object):

    def __init__(self, pos):

        self._pos = pos

    def __repr__(self):

        x, y, z = self._pos

        return "PosObj({:f}, {:f}, {:f})".format(x, y, z)

    def __getitem__(self, index):

        return self._pos[index]


# The following class is a wrapper around Vec3 that uses operator overloading
# to allow concise vector math
class V3D(Vec3):

    def __str__(self):

        x, y, z = self

        return "V3D({:f}, {:f}, {:f})".format(x, y, z)

    def get_h(self):
        """ Get the heading of this vector """

        quat = Quat()
        look_at(quat, self, Vec3.up())

        return quat.get_hpr().x

    def get_p(self):
        """ Get the pitch of this vector """

        quat = Quat()
        look_at(quat, self, Vec3.up())

        return quat.get_hpr().y

    def get_hpr(self):
        """ Get the direction of this vector """

        quat = Quat()
        look_at(quat, self, Vec3.up())

        return quat.get_hpr()

    def __mul__(self, rhs):
        """
        Overload "*" operator:
            the right hand side operand can be:
                - another vector -> dot product;
                - a matrix -> point transformation;
                - a single number -> uniform scaling
                - a sequence of 3 numbers -> non-uniform scaling.

        """

        if isinstance(rhs, Vec3):

            return self.dot(rhs)

        elif isinstance(rhs, Mat4):

            return V3D(rhs.xform_point(self))

        else:

            try:
                scale_x, scale_y, scale_z = rhs
            except:
                return V3D(Vec3.__mul__(self, rhs))

            x, y, z = self

            return V3D(x * scale_x, y * scale_y, z * scale_z)

    def __imul__(self, rhs):
        """
        Overload "*=" operator:
            the right hand side operand can be:
                - a matrix -> in-place point transformation;
                - a single number -> in-place uniform scaling
                - a sequence of 3 numbers -> in-place non-uniform scaling.

        """

        if isinstance(rhs, Vec3):

            raise TypeError("Cannot perform dot product in-place.")

        elif isinstance(rhs, Mat4):

            self.set(*rhs.xform_point(self))

            return self

        else:

            try:
                scale_x, scale_y, scale_z = rhs
            except:
                self.set(*Vec3.__mul__(self, rhs))
                return self

            x, y, z = self
            self.set(x * scale_x, y * scale_y, z * scale_z)

            return self

    def __pow__(self, vector):
        """
        Overload "**" operator:
            the other operand must be another vector -> cross product.

        """

        return V3D(self.cross(vector))

    def __ipow__(self, vector):
        """
        Overload "**=" operator:
            the other operand must be another vector -> in-place cross product.

        """

        self.cross_into(vector)

        return self

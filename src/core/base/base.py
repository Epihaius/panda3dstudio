from panda3d.core import *
import weakref
import sys
import os
import math
import random
import time
import datetime
import cPickle
import re

GFX_PATH = "res/core/"


# All objects that need access to core variables should derive from the
# following class
class BaseObject(object):

    world = None
    screen = None
    cam = None
    cam_node = None
    cam_lens = None
    mouse_watcher = None

    _defaults = {
        "data_retriever": lambda *args, **kwargs: None
    }

    _verbose = False

    @classmethod
    def init(cls, world, screen, cam, cam_node, cam_lens, mouse_watcher, verbose):

        cls.world = world
        cls.screen = screen
        cls.cam = cam
        cls.cam_node = cam_node
        cls.cam_lens = cam_lens
        cls.mouse_watcher = mouse_watcher
        cls._verbose = verbose

    def __init__(self):

        # structure to store callables through which data can be retrieved by
        # id
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

        if self._verbose and data_id not in self._data_retrievers:
            print 'Core warning: data "%s" is not defined.' % data_id

        retriever = self._data_retrievers.get(
            data_id, self._defaults["data_retriever"])

        return retriever(*args, **kwargs)


# All main objects, especially those that need to be set up at the start of the
# program, should be added to the following class
class MainObjects(object):

    _classes = {}
    _objs = {}
    _setup_results = {}

    @classmethod
    def add_class(cls, main_cls, group_id=""):

        cls._classes.setdefault(group_id, []).append(main_cls)

    @classmethod
    def init(cls, group_id=""):

        for main_cls in cls._classes.get(group_id, []):
            cls._objs.setdefault(group_id, []).append(main_cls())

    @classmethod
    def setup(cls, group_id=""):

        objs_to_setup = cls._objs.get(group_id, [])[:]

        # if an object's setup failed because it depends on the setup of another
        # object, it will be tried again later
        while objs_to_setup:

            setup_successful = False

            for obj in objs_to_setup[:]:

                setup_result = obj.setup()

                if setup_result:
                    cls._setup_results.setdefault(
                        group_id, []).append(setup_result)
                    setup_successful = True
                    objs_to_setup.remove(obj)

            assert setup_successful, "Setup failed for one or more main objects!"

        del cls._setup_results[group_id]

    @classmethod
    def get_setup_results(cls, group_id=""):
        """
        This method can be called by the main objects during their setup to check
        if the setup of a particular main object has already successfully completed.

        """

        return cls._setup_results.get(group_id, [])


class PendingTasks(object):

    _tasks = {}
    _task_ids = {}
    _is_handling_tasks = False

    @classmethod
    def add(cls, task, task_id, task_type="", sort=None, id_prefix=None):
        """
        Add a task that needs to be handled later - and only once - through a call
        to handle(), optionally with a type and/or sort value.
        Additionally, a prefix for the task ID can be given to make it unique (so
        this task doesn't overwrite a previously added task with the same ID and
        type), while retaining the sort value associated with the given task_id (if
        the given sort value is None).

        """

        if cls._is_handling_tasks:
            return

        if sort is None:

            task_ids = cls._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        if id_prefix:
            task_id = "%s_%s" % (id_prefix, task_id)

        cls._tasks.setdefault(task_type, {}).setdefault(
            sort, {})[task_id] = task

    @classmethod
    def remove(cls, task_id, task_type="", sort=None):
        """
        Remove the task with the given ID (and optionally, type and/or sort value)
        and return it (or None if not found).

        """

        if cls._is_handling_tasks:
            return

        if sort is None:

            task_ids = cls._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        return cls._tasks.get(task_type, {}).get(sort, {}).pop(task_id, None)

    @classmethod
    def clear(cls, task_type=None):
        """
        Clear the tasks of the given type if it is specified, or all tasks if it is
        None.

        """

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

        if cls._is_handling_tasks:
            return

        cls._is_handling_tasks = True

        pending_tasks = cls._tasks

        if task_types is None:
            task_types = pending_tasks.keys()

        if sort_by_type:
            sorted_tasks = [task for task_type in task_types for sort, tasks in
                            sorted(pending_tasks.pop(
                                task_type, {}).iteritems())
                            for task in tasks.itervalues()]
        else:
            sorted_tasks = [task for sort, tasks in sorted([i for task_type in task_types
                                                            for i in pending_tasks.pop(task_type, {}).iteritems()])
                            for task in tasks.itervalues()]

        for task in sorted_tasks:
            task()

        cls._is_handling_tasks = False

    @classmethod
    def add_task_id(cls, task_id, task_type="", sort=None):
        """
        Add a task ID, optionally associated with a particular task type, and with
        an optional sort value.

        """

        task_ids = cls._task_ids.setdefault(task_type, [])

        if sort is None:
            task_ids.append(task_id)
        else:
            task_ids.insert(sort, task_id)

    @classmethod
    def get_sort(cls, task_id, task_type=""):
        """
        Return the sort value of the task with the given ID, or None if the task ID
        is not defined.

        """

        task_ids = cls._task_ids.get(task_type, [])

        if task_id in task_ids:
            return task_ids.index(task_id)


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

        return [t for t in cls._types.itervalues() if t not in cls._special_types]

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

    # Credit to coppertop @ panda3d.org

    r = (color_id >> 16)
    g = (color_id ^ (r << 16)) >> 8
    b = (color_id ^ (r << 16) ^ (g << 8))

    return VBase4(r, g, b, alpha) / 255.


def get_unique_name(requested_name, namestring, default_search_pattern="",
                    default_naming_pattern="", default_min_index=1):

    search_pattern = default_search_pattern
    naming_pattern = default_naming_pattern
    min_index = default_min_index

    if requested_name:

        pattern = r"(.*?)(\s*)(\d*)$"
        basename, space, index_str = re.search(
            pattern, requested_name).groups()

        if index_str:

            min_index = int(index_str)
            search_pattern = r"^%s\s*(\d+)$" % re.escape(basename)
            zero_padding = len(index_str) if index_str.startswith("0") else 0
            naming_pattern = basename + space + "%0" + str(zero_padding) + "d"

        else:

            # also search for "(<index>)" at the end
            pattern = r"(.*?)(\s*)(?:\((\d*)\))*$"
            basename, space, index_str = re.search(
                pattern, requested_name).groups()

            if index_str:

                min_index = int(index_str)
                search_pattern = r"^%s\s*\((\d+)\)$" % re.escape(basename)
                zero_padding = len(
                    index_str) if index_str.startswith("0") else 0
                naming_pattern = basename + space + \
                    "(%0" + str(zero_padding) + "d)"

            else:

                search_pattern = r"^%s$" % re.escape(basename)

                if re.findall(search_pattern, namestring, re.M):
                    min_index = 2
                    search_pattern = r"^%s\s*\((\d+)\)$" % re.escape(basename)
                    naming_pattern = basename + " (%d)"
                else:
                    return basename

    names = re.finditer(search_pattern, namestring, re.M)
    inds = [int(name.group(1)) for name in names]
    max_index = min_index + len(inds)

    for i in xrange(min_index, max_index):
        if i not in inds:
            return naming_pattern % i

    return naming_pattern % max_index


# The following class allows a position (passed in as a tuple or list) to be
# used as a dictionary key when 2 identical positions should still be treated
# as different keys (e.g. to differentiate between two vertices that share the
# same location in space).
class PosObj(object):

    def __init__(self, pos):

        self._pos = pos

    def __getitem__(self, index):

        return self._pos[index]


# The following class is a wrapper around Vec3 that uses operator overloading
# to allow compact vector math
class V3D(Vec3):

    def __str__(self):

        x, y, z = self

        return "V3D(%s, %s, %s)" % (x, y, z)

    def get_h(self, *args):
        """ Get the heading of this vector """

        np = NodePath("")

        x, y, z = self
        np.look_at(x, y, z)
        heading = np.get_h(*args)
        np.remove_node()

        return heading

    def get_p(self, *args):
        """ Get the pitch of this vector """

        np = NodePath("")

        x, y, z = self
        np.look_at(x, y, z)
        pitch = np.get_p(*args)
        np.remove_node()

        return pitch

    def get_hpr(self, *args):
        """ Get the direction of this vector """

        np = NodePath("")

        x, y, z = self
        np.look_at(x, y, z)
        hpr = np.get_hpr(*args)
        np.remove_node()

        return hpr

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

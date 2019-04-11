from .base import logging, GlobalData, EventBinder, StateManager, StateBinder, DirectObject
from panda3d.core import load_prc_file_data, MouseWatcherRegion, WindowProperties, Filename
from direct.showbase.ShowBase import ShowBase

load_prc_file_data("",
"""
sync-video false
model-cache-dir
geom-cache-size 0
window-type none
depth-bits 24
notify-output p3ds.log
garbage-collect-states false
load-file-type p3assimp
notify-level-linmath error

"""
)

# the CursorManager class is used to set the mouse cursor image, but also to reset it to the image
# that was last used for a particular region (GUI, viewport, etc.) when entering that region again
class CursorManager(object):

    def __init__(self, base, mouse_watcher_node):

        self._base = base
        self._mouse_watcher_node = mouse_watcher_node
        self._regions = {}
        self._cursor_filenames = {}
        self._listener = listener = DirectObject()
        pattern = "cursor_region_enter"
        listener.accept(pattern, self.__set_cursor)
        mouse_watcher_node.set_enter_pattern(pattern)

    def add_cursor_region(self, interface_id, region):

        self._regions.setdefault(interface_id, []).append(region)
        self._mouse_watcher_node.add_region(region)
        self._cursor_filenames[region.get_name()] = Filename()

    def remove_cursor_regions(self, interface_id):

        if interface_id in self._regions:

            for region in self._regions[interface_id]:
                self._mouse_watcher_node.remove_region(region)
                del self._cursor_filenames[region.get_name()]

            del self._regions[interface_id]

    def set_cursor_regions_active(self, interface_id, active=True):

        if interface_id in self._regions:
            for region in self._regions[interface_id]:
                region.set_active(active)

    def __set_cursor(self, *args):

        region_id = args[0].get_name()
        self.set_cursor(region_id)

    def set_cursor(self, region_id, cursor_filename=None):

        filenames = self._cursor_filenames

        if region_id not in filenames:
            return

        c_f = filenames[region_id] if cursor_filename is None else cursor_filename
        filenames[region_id] = c_f
        region = self._mouse_watcher_node.get_over_region()

        if region and region.get_name() == region_id:
            win_props = WindowProperties()
            win_props.set_cursor_filename(c_f)
            self._base.win.request_properties(win_props)


# the AppManager is responsible for unifying the two main components of the
# application: the Core and the GUI
class AppManager(object):

    def __init__(self, verbose=False):

        self._base = ShowBase()
        self._verbose = verbose
        self._updaters = {}
        self._state_mgrs = {}
        self._key_handlers = {}
        self._cursor_manager = None
        GlobalData["mod_key_codes"] = {"alt": 1, "ctrl": 2, "shift": 4}

    def setup(self, listener, key_handlers):

        self._state_mgrs["main"] = {"CORE": StateBinder(EventBinder(listener)),
                                    "GUI": StateManager()}
        self._key_handlers["main"] = key_handlers

    def get_base(self):

        return self._base

    def remove_interface(self, interface_id):

        self.remove_state_managers(interface_id)
        self.remove_key_handlers(interface_id)
        self.remove_updaters(interface_id)
        self.remove_cursor_regions(interface_id)

    def add_state_manager(self, interface_id, component_id, listener=None):

        if listener:
            state_mgr = StateBinder(EventBinder(listener))
        else:
            state_mgr = StateManager()

        self._state_mgrs.setdefault(interface_id, {})[component_id] = state_mgr

    def remove_state_managers(self, interface_id):

        if interface_id not in self._state_mgrs:
            return

        state_mgrs = self._state_mgrs[interface_id]

        for component_id in state_mgrs:

            state_mgr = state_mgrs[component_id]

            if state_mgr.is_state_binder():
                event_binder = state_mgr.get_event_binder()
                event_binder.ignore_all()

        del self._state_mgrs[interface_id]

    def add_key_handlers(self, interface_id, key_handlers):

        self._key_handlers[interface_id] = key_handlers

    def remove_key_handlers(self, interface_id):

        handlers = self._key_handlers

        if interface_id in handlers:
            del handlers[interface_id]

    def init_cursor_manager(self, mouse_watcher):

        self._cursor_manager = CursorManager(self._base, mouse_watcher)

    def add_cursor_region(self, interface_id, mouse_region):

        self._cursor_manager.add_cursor_region(interface_id, mouse_region)

    def remove_cursor_regions(self, interface_id):

        self._cursor_manager.remove_cursor_regions(interface_id)

    def set_cursor_regions_active(self, interface_id, active=True):

        self._cursor_manager.set_cursor_regions_active(interface_id, active)

    def set_cursor(self, region_id, cursor_filename):

        self._cursor_manager.set_cursor(region_id, cursor_filename)

    def add_state(self, interface_id, component_id, state_id, persistence,
                  on_enter=None, on_exit=None):

        self._state_mgrs[interface_id][component_id].add_state(state_id, persistence,
                                                               on_enter, on_exit)

    def set_default_state(self, interface_id, state_id):
        """
        Set the default state of a particular application interface.

        """

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].set_default_state(state_id)
        state_mgrs["GUI"].set_default_state(state_id)

    def enter_state(self, interface_id, state_id):

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].enter_state(state_id)
        state_mgrs["GUI"].enter_state(state_id)

    def exit_state(self, interface_id, state_id):

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].exit_state(state_id)
        state_mgrs["GUI"].exit_state(state_id)

    def exit_states(self, interface_id, min_persistence=None):

        state_mgrs = self._state_mgrs[interface_id]
        state_mgrs["CORE"].exit_states(min_persistence)
        state_mgrs["GUI"].exit_states(min_persistence)

    def get_state_id(self, interface_id, component_id):

        return self._state_mgrs[interface_id][component_id].get_current_state_id()

    def get_state_persistence(self, interface_id, component_id, state_id):

        return self._state_mgrs[interface_id][component_id].get_state_persistence(state_id)

    def is_state_active(self, interface_id, component_id, state_id):

        return self._state_mgrs[interface_id][component_id].is_state_active(state_id)

    def bind_state(self, interface_id, state_id, binding_id, event_props, event_handler):

        self._state_mgrs[interface_id]["CORE"].bind(state_id, binding_id, event_props,
                                                    event_handler)

    def activate_bindings(self, interface_id, binding_ids, exclusive=False):

        self._state_mgrs[interface_id]["CORE"].accept(binding_ids, exclusive)

    def add_updater(self, component_id, update_id, updater, kwargs=None, interface_id="main"):
        """
        Add an updater for the property with the given update_id, in either the core
        or the GUI.
        The optional kwargs is a list of parameter names that are defined for
        this updater, but not necessarily for other updaters for the same property.
        This list includes names of parameters for which values will be passed as
        keyword arguments, especially parameters that are not defined for at least
        one of the other updaters.
        When calling all updaters for the property with the given update_id, only
        arguments with keywords that are in this list will be passed along to this
        updater.

        """

        data = (updater, kwargs if kwargs else [])
        self._updaters.setdefault(interface_id, {}).setdefault(
            component_id, {}).setdefault(update_id, []).append(data)

    def update(self, component_id, locally, remotely, update_id, *args, **kwargs):
        """
        Call all updaters defined for the property with the given update_id.
        Each updater will handle the update in either the core or the GUI, so both
        components can be updated simultaneously using this method, which can be
        called from either component.
        This unifies the updating of both components, while allowing data to be
        passed on selectively to each updater by passing along the given keyword
        arguments to only those updaters that accept them.

        """

        dest = "GUI" if component_id == "CORE" else "CORE"
        local_updaters = []
        remote_updaters = []

        for updaters in self._updaters.values():
            local_updaters.extend(updaters.get(component_id, {}).get(update_id, []))

        for updaters in self._updaters.values():
            remote_updaters.extend(updaters.get(dest, {}).get(update_id, []))

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.items() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.items() if k in param_ids)
                updater(*args, **_kwargs)

    def update_interface(self, interface_id, component_id, locally, remotely,
                         update_id, *args, **kwargs):
        """
        Same as update(), but for a specific interface.

        """

        dest = "GUI" if component_id == "CORE" else "CORE"
        local_updaters = self._updaters.get(interface_id, {}).get(component_id, {}).get(update_id, [])
        remote_updaters = self._updaters.get(interface_id, {}).get(dest, {}).get(update_id, [])

        if locally:
            for updater, param_ids in local_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.items() if k in param_ids)
                updater(*args, **_kwargs)

        if remotely:
            for updater, param_ids in remote_updaters:
                _kwargs = dict((k, v) for k, v in kwargs.items() if k in param_ids)
                updater(*args, **_kwargs)

    def remove_updaters(self, interface_id):
        """
        Remove all updaters defined for a specific interface.

        """

        if interface_id in self._updaters:
            del self._updaters[interface_id]

    def handle_key_down(self, interface_id, key_code):

        return self._key_handlers[interface_id]["down"](key_code)

    def handle_key_up(self, interface_id, key_code):

        return self._key_handlers[interface_id]["up"](key_code)

import os
import logging
from importlib import import_module

path = os.path.join("src", "core", "geom", "prim")

names = set(os.path.splitext(name)[0] for name in os.listdir(path))
names = [name for name in names if name not in ("__init__", "base")]

package_path = "src.core.geom.prim."

for name in names:
    try:
        import_module(package_path + name)
    except ImportError:
        logging.critical('Failed to load module "{}"!'.format(name))
        raise ImportError('Failed to load module "{}"!'.format(name))

import os
import logging
from importlib import import_module

path = os.path.join("src", "core", "geom", "prim")

names = set(os.path.splitext(name)[0] for name in os.listdir(path))
names = [name for name in names if name not in ("__pycache__", "__init__", "base")]

package_path = "src.core.geom.prim."

for name in names:
    try:
        import_module(package_path + name)
    except ImportError:
        logging.critical(f'Failed to load module "{name}"!')
        raise ImportError(f'Failed to load module "{name}"!')

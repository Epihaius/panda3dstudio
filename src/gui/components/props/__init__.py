from .base import PropertyPanel
import os
import logging

path = os.path.join("src", "gui", "components", "props")

names = set(os.path.splitext(name)[0] for name in os.listdir(path))
names = [name for name in names if name not in ("__init__", "base")]

package_path = "src.gui.components.props."

for name in names:
    try:
        __import__(package_path + name)
    except ImportError:
        logging.critical('Failed to load module "%s"!', name)
        raise ImportError('Failed to load module "%s"!' % name)

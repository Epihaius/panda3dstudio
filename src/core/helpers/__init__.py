import os

path = os.path.join("src", "core", "helpers")

names = set(os.path.splitext(name)[0] for name in os.listdir(path))
names = [name for name in names if name not in ("__init__",)]

package_path = "src.core.helpers."

for name in names:
    try:
        __import__(package_path + name)
    except ImportError:
        print "Failed to load module '%s'!" % name

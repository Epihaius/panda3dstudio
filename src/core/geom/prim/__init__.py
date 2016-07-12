import os

path = os.path.join("src", "core", "geom", "prim")

names = set(os.path.splitext(name)[0] for name in os.listdir(path))
names = [name for name in names if name not in ("__init__", "base")]

package_path = "src.core.geom.prim."

for name in names:
    try:
        __import__(package_path + name)
    except ImportError:
        print "Failed to load module '%s'!" % name

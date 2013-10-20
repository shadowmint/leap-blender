# Leap motion bindings for blender

Dirty hacks to get a leap motion binding working~

## Quick start:

    git submodule init
    git submodule update

Load blender and open the console and:

    import sys
    sys.path.append('/Users/doug/projects/blender')
    import bleap
    bleap.register()
    bleap.start()
    str(bleap.poll())

Check the output; should be something like:

    "<<class 'cleap.leap.Frame'> 319591 timestamp:27004105576 bounds:<<class 'cleap.leap.Bounds'> size:<<class 'cleap.leap.Vector'> 221.42 221.42 154.74> center<<class 'cleap.leap.Vector'> 0.00 200.00 0.00>>>"

Right! Turn object motion tracking on:

    import sys
    sys.path.append('/Users/doug/projects/blender') # <-- Or you cloned path
    import bleap
    bleap.register()
    bleap.start()
    bpy.ops.bleap.track()

## Operations

Move to come, currently supported are:

### Movement

Select an object, and use one finger to move it around.
To place the object, enter second hand then remove both.

#### TODO

    - Should take into account current camera for correct relative motion; currently absolute xyz coordinates
    - Support scaling for large objects; currently the 'scale' is the leap scale, ie. 0 -> ~300
    - Relative motion?

## Extra

In unindented mode for easy copy-paste...

import sys
sys.path.append('/Users/doug/projects/blender') # <-- Or you cloned path
import bleap
bleap.register()
bleap.start()
bpy.ops.bleap.track()

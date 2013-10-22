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

Select an object, and use one finger to move it in and out relative to the camera.
To place the object, enter second hand then remove both.

#### TODO

    - Support scaling for large objects; currently the 'scale' is arbitrary
    - Better way to 'halt' once done moving stuff around.

### TODO

    - Use finger vector for rotation while in motion mode
    - Use palm rotation to control camera
    - key bindings?

## Extra

In unindented mode for easy copy-paste...

import sys
sys.path.append('/Users/doug/projects/blender/leap-blender') # <-- Or you cloned path
import bleap
bleap.register()
bpy.ops.bleap.track()

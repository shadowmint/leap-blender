"""
    Quick start:

import sys
sys.path.append('/Users/doug/projects/blender')
import periodic
periodic.register()
bpy.ops.periodic.update()
"""
import bpy

x = 0


bl_info = {
  "name": "Move X Axis",
  "category": "Object",
}

def register():
  bpy.utils.register_module(__name__, verbose=True)


def unregister():
  bpy.utils.unregister_module(__name__)


class update(bpy.types.Operator):
    bl_idname = "periodic.update"
    bl_label = "Your Operator"

    def __init__(self, *args, **kwargs):
      super(update, self).__init__(*args, **kwargs)
      self._updating = False
      self._timer = None
      self._test = 0
      global x
      x += 1

    def track(self):
        # would be good if you can break up your calcs
        # so when looping over a list, you could do batches
        # of 10 or so by slicing through it.
        # do your calcs here and when finally done
        self._test += 1
        global x
        x += 1
       

    def modal(self, context, event):
        try:
          if event.type == 'TIMER' and not self._updating:
              print('Tracking...')
              self._updating = True
              self.track()
              self._updating = False
          if self._test > 5:
              self.cancel(context)
        except Exception as e:
          print(e)
        return {'PASS_THROUGH'}

    def execute(self, context):
        global x
        x += 1
        context.window_manager.modal_handler_add(self)
        self._updating = False
        self._timer = context.window_manager.event_timer_add(0.5, context.window)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        self._timer = None
        global x 
        x = 9999
        return {'CANCELLED'}

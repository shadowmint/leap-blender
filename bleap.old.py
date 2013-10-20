"""
    Quick start:

import sys
sys.path.append('/Users/doug/projects/blender')
import bleap
b = BLeap(C)
b.start()
b.track(C.scene.objects['Camera'])

"""
import os
import sys
import time
from os.path import dirname, join, abspath
sys.path.append(join(dirname(__file__), 'lib', 'cleap', 'src'))

# Set DLL path for leap libraries
os.environ['LEAP_DLL_PATH'] = abspath(join(dirname(__file__), 'lib', 'cleap', 'dll'))

# Import leap
from cleap.leap import *

class BLeap(object):

  def __init__(self, context):
    self._context = context

  def start(self):
    c = leap_controller()
    l = leap_listener(500)
    leap_add_listener(c, l)
    leap_enable_background(c)
    self.c = c
    self.l = l

  def callback(self):
    print('CAllback!')
    c = self.c
    l = self.l
    waiting = True
    while not waiting:
      event = leap_poll_listener(l)
      if event:
        e = Event(event)
        if e.code == LEAP_ON_FRAME:
          if len(e.frame.hands) == 1:
            self.context.location.x = e.frame.hands[0].fingers[0].position.points[0]
            self.context.location.y = e.frame.hands[0].fingers[0].position.points[1]
            self.context.location.z = e.frame.hands[0].fingers[0].position.points[2]
      else:
        waiting = True

  def track(self, context):
    self.context = context
    self.o = BleapOp()

  def stop(self):
    context.window_manager.event_timer_remove(self._timer)

  def shutdown(self):
    c = self.c
    l = self.l
    leap_remove_listener(c, l)
    leap_listener_dispose(l)
    leap_controller_dispose(c)

class BLeapOp(bpy.types.Operator):
    bl_idname = "youroperatorname"
    bl_label = "Your Operator"

    _updating = False
    _timer = None
    _test = 0

    def track(self):
        # would be good if you can break up your calcs
        # so when looping over a list, you could do batches
        # of 10 or so by slicing through it.
        # do your calcs here and when finally done
        self._test += 1
       

    def modal(self, context, event):
        if event.type == 'TIMER' and not self._updating:
            print('Tracking...')
            self._updating = True
            self.track()
            self._updating = False
        if self._test > 5:
            self.cancel(context)

        return {'PASS_THROUGH'}

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        self._updating = False
        self._timer = context.window_manager.event_timer_add(0.5, context.window)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        self._timer = None
        return {'CANCELLED'}

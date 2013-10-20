# Copyright 2012 Douglas Linder
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
from os.path import dirname, join, abspath

import bpy


# Setup paths and import
os.environ['LEAP_DLL_PATH'] = abspath(join(dirname(__file__), 'lib', 'cleap', 'dll'))
sys.path.append(join(dirname(__file__), 'lib', 'cleap', 'src'))
from cleap.leap import *


# metadata
bl_info = {
  "name": "LEAP motion tracker",
  "category": "Object",
}

# Global BLeap instance, so we don't have multiple controllers screwing things up
controller = None


def register():
  """ Regsiter this operator """
  bpy.utils.register_module(__name__, verbose=True)


def unregister():
  """ Remove this operator """
  bpy.utils.unregister_module(__name__)


def stop():
  """ Stop all track and all running ops """
  global controller
  if controller is not None:
    controller.shutdown()
  controller = None


def start():
  """ Start global tracking

      Notice that until something calls poll the public frame will not be updated~
      You can manually step to the next frame using poll() if you want to.
  """
  global controller
  if controller is None:
    controller = BLeap()
    controller.start()


def poll():
  """ Consume the next buffered leap frame and expose it to bleap.frame """
  global controller
  return next(controller.poll())


class BLeap(object):
  """ Track things """

  def start(self):
    """ Start tracking """
    c = leap_controller()
    l = leap_listener(500)  # buffer size
    leap_add_listener(c, l)
    leap_enable_background(c)
    self.dead = False
    self.c = c
    self.l = l

  def poll(self):
    """ Yield frames while available, then wait for next opportunity """
    l = self.l
    waiting = False
    while not waiting:
      event = leap_poll_listener(l)
      if event:
        e = Event(event)
        if e.code == LEAP_ON_FRAME:
          yield e.frame
      else:
        waiting = True

  def shutdown(self):
    """ Halt all tracking """
    c = self.c
    l = self.l
    leap_remove_listener(c, l)
    leap_listener_dispose(l)
    leap_controller_dispose(c)
    self.dead = True


class track(bpy.types.Operator):
  """ Operator for actually doing useful things """

  bl_idname = "bleap.track"
  bl_label = "LEAP motion tracking"

  def __init__(self, *args, **kwargs):
    super(track, self).__init__(*args, **kwargs)
    self._updating = False
    self._timer = None
    global controller
    self._leap = controller

  def track(self, context):
    """ Actually convert leap data into useful data like motion """
    for frame in self._leap.poll():
      if len(frame.hands) == 1 and len(frame.hands[0].fingers) == 1:

        # Make the origin 0,0,0 instead of mystical LEAP units
        # (which makes Z = rubbing your face in the leap device)
        x = frame.hands[0].fingers[0].position.points[0] - frame.bounds.center.points[0]
        y = frame.hands[0].fingers[0].position.points[1] - frame.bounds.center.points[1]
        z = frame.hands[0].fingers[0].position.points[2] - frame.bounds.center.points[2]

        # Apply arbitrary scaling to make it more useable
        x = x / 50.0
        y = y / 50.0
        z = z / 50.0

        try:
          for t in context.scene.objects.active:
            t.location.x = x
            t.location.y = y
            t.location.z = z
        except:  # Fark, not an iterable
          t = context.scene.objects.active
          t.location.x = x
          t.location.y = y
          t.location.z = z


  def modal(self, context, event):
    if event.type == 'TIMER' and not self._updating:
      if self._leap.dead:
        self.cancel(context)
      else:
        self._updating = True
        self.track(context)
        self._updating = False
    return {'PASS_THROUGH'}

  def execute(self, context):
    context.window_manager.modal_handler_add(self)
    self._updating = False
    self._timer = context.window_manager.event_timer_add(0.1, context.window)
    return {'RUNNING_MODAL'}

  def cancel(self, context):
    context.window_manager.event_timer_remove(self._timer)
    self._timer = None
    return {'CANCELLED'}

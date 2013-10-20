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
import math
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

        # Normalize
        x = 0.0
        y = 0.0
        z = 1.0 - (z / frame.bounds.size.points[2])

        # Arbitrary scaling constant
        scale = 10.0

        utils = BlenderUtils(context)

        # Find the view we're working in
        views = utils.views
        if len(views) > 0:
          view = views[0]
          look_at, camera_pos, rotation = utils.camera(view)
          z_vector = [look_at[0] - camera_pos[0], look_at[1] - camera_pos[1], look_at[2] - camera_pos[2]]
          z_vector = utils.unit_vector(z_vector)
          global debug
          debug = z_vector

          for o in utils.active:
            o.location.x = z * z_vector[0] * scale
            o.location.y = z * z_vector[1] * scale
            o.location.z = z * z_vector[2] * scale

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


class BlenderUtils(object):
  """ Useful utilities for obscure blender functionality """

  def __init__(self, context):
    self.context = context

  @property
  def active(self):
    """ Currently selected objects """
    try:
      for t in self.context.scene.objects.active:
        yield t
    except:  # Fark, not an iterable
      yield self.context.scene.objects.active

  @property
  def views(self):
    """ Returns the set of 3D views.
        Seriously, this api is stupid. WTF.
    """
    rtn = []
    for a in self.context.window.screen.areas:
      if a.type == 'VIEW_3D':
        rtn.append(a)
    return rtn

  def camera(self, view):
    """ Return position, rotation data about a given view for the first space attached to it """
    look_at = view.spaces[0].region_3d.view_location
    matrix = view.spaces[0].region_3d.view_matrix
    camera_pos = self.camera_position(matrix)
    rotation = view.spaces[0].region_3d.view_rotation
    return look_at, camera_pos, rotation

  def camera_position(self, matrix):
    """ From 4x4 matrix, calculate camera location """
    t = (matrix[0][3], matrix[1][3], matrix[2][3])
    r = (
      (matrix[0][0], matrix[0][1], matrix[0][2]),
      (matrix[1][0], matrix[1][1], matrix[1][2]),
      (matrix[2][0], matrix[2][1], matrix[2][2])
    )
    rp = (
      (-r[0][0], -r[1][0], -r[2][0]),
      (-r[0][1], -r[1][1], -r[2][1]),
      (-r[0][2], -r[1][2], -r[2][2])
    )
    output = (
      rp[0][0] * t[0] + rp[0][1] * t[1] + rp[0][2] * t[2],
      rp[1][0] * t[0] + rp[1][1] * t[1] + rp[1][2] * t[2],
      rp[2][0] * t[0] + rp[2][1] * t[1] + rp[2][2] * t[2],
    )
    return output

  def unit_vector(self, vector):
    """ Calculate a unit vector
    """
    sum = vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]
    sqrt = math.sqrt(sum)
    if sqrt == 0:
      sqrt = 0.01
    return [vector[0] / sqrt, vector[1] / sqrt, vector[2] / sqrt]

  def unit_vectors(self, location, matrix):
    """ Return unit vectors for the given matrix in x, y, z domains relative to it.
    """
    pass

  def apply_transform(self, target, matrix, magnitude, scale):
    """ Apply a transformation to the point 'target'
        :param target: The target (x, y, z)
        :param matrix: The matrix being applied
        :param magnitude: The magnitude of the matrix to apply.
        :param scale: A scale factor to the result
    """
    pass

debug = None

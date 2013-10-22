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
  start()


def unregister():
  """ Remove this operator """
  stop()
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
    global controller
    super(track, self).__init__(*args, **kwargs)
    self._updating = False
    self._timer = None
    self._leap = controller

  def track(self, context):
    """ Actually convert leap data into useful data like motion """
    ui = LeapObjectMove(context)
    for frame in self._leap.poll():
      ui.on_frame(frame)

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


class BleapUtils(object):
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

  def unit_vectors(self, look_at, camera_pos, rotation):
    """ Return unit vectors for the given matrix in x, y, z domains relative to it.
    """
    z_vector = [look_at[0] - camera_pos[0], look_at[1] - camera_pos[1], look_at[2] - camera_pos[2]]
    z_vector = self.unit_vector(z_vector)

    y_vector = [0, 1, 0]
    y_vector = self.rotate_vector(y_vector, rotation)

    x_vector = [1, 0, 0]
    x_vector = self.rotate_vector(x_vector, rotation)

    return x_vector, y_vector, z_vector

  def add_vector(self, target, vector, magnitude, scale):
    """ Apply a transformation to the point 'target'
        :param target: An [x, y, z] vector to modify.
        :param vector: The [x, y, z] vector to apply.
        :param magnitude: The magnitude of the vector to apply.
        :param scale: A scale factor to the result
    """
    target[0] += magnitude * vector[0] * scale
    target[1] += magnitude * vector[1] * scale
    target[2] += magnitude * vector[2] * scale

  def normalized_input(self, frame, fingers):
    """ Returns normalized 0.0 -> 1.0 input for the 3 dimensions of leap input
        The 'location' it given by the averaged position of the given fingers.
        :param frame: The frame object.
        :param fingers: The fingers to use.
    """
    avg = [0, 0, 0]
    for f in fingers:
      avg[0] += f.position.points[0]
      avg[1] += f.position.points[1]
      avg[2] += f.position.points[2]
    avg[0] = avg[0] / float(len(fingers))
    avg[1] = avg[1] / float(len(fingers))
    avg[2] = avg[2] / float(len(fingers))

    x = (avg[0] - frame.bounds.center.points[0]) / frame.bounds.size.points[0]
    y = (avg[1] - frame.bounds.center.points[1]) / frame.bounds.size.points[1]
    z = 1.0 - (avg[2] - frame.bounds.center.points[2]) / frame.bounds.size.points[2]

    return [x, y, z]

  def quanternion_conj(self, q):
    """ Calculate the conjugate of a quaternion (w, x, y, z)
        :param q: The quaternion to process
    """
    return [q[0], -q[1], -q[2], -q[3]]

  def hamilton_transform(self, a, b):
    """ Calculate the hamilton transform AB between two quaternions a and b
    """
    return [
      a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
      a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
      a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
      a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0],
    ]

  def rotate_vector(self, vector, quaternion):
    """ Rotate the vector (x,y,z) by the quaternion (w,x,y,z)
    """
    p = [0, vector[0], vector[1], vector[2]]
    r = quaternion
    rx = self.quanternion_conj(quaternion)
    output = self.hamilton_transform(self.hamilton_transform(r, p), rx)
    return output[1:]  # drop w component


class LeapInteraction(object):
  """ Common base for interaction strategies """

  def __init__(self, context):
    self.utils = BleapUtils(context)

  def on_frame(self, frame):
    pass


class LeapObjectMove(LeapInteraction):
  """ Move objects using the right hand with left hand as command mode.

      Left 5-fingers: stop motion of object
      Left 3-fingers: resume motion of object

      Right 1-finger: control location and rotation relative to camera.
  """

  def on_frame(self, frame):
    if len(frame.hands) == 1 and len(frame.hands[0].fingers) == 1:

      # Normalized leap coordinates
      x, y, z = self.utils.normalized_input(frame, [frame.hands[0].fingers[0]])

      # Arbitrary scaling constant
      scale = 10.0

      # Find the view we're working in
      views = self.utils.views
      if len(views) > 0:
        view = views[0]  # Well, the first view that we can find anyway
        x_vector, y_vector, z_vector = self.utils.unit_vectors(*self.utils.camera(view))

        for o in self.utils.active:
          t = [0, 0, 0]
          self.utils.add_vector(t, x_vector, x, scale)
          self.utils.add_vector(t, y_vector, y, scale)
          self.utils.add_vector(t, z_vector, z, scale)
          o.location.x = t[0]
          o.location.y = t[1]
          o.location.z = t[2]

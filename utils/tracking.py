from utils.contour import is_point_in_contour
import numpy as np
from scipy.optimize import linear_sum_assignment

class PedestrianTracking:
  """ Class to keep track of mapping of pedestrian indexes to bboxes and detection zone (up/down)"""

  def __init__(self):
    self.positions = dict()
    self._up = 0
    self._down = 1

  def any_currently_tracked(self):
    return len(self.positions)>0

  def get_tracked_bboxes(self):
    return self.positions

  def update_pos(self, idxsToRemove, idxsUp, peds_bboxes_up, idxsDown, peds_bboxes_down):
    for i in idxsToRemove:
      if i in self.positions:
        del self.positions[i]
    going_up = []
    going_down = []
    for idxs, bboxes, direction, going in zip((idxsUp, idxsDown), (peds_bboxes_up, peds_bboxes_down), (self._up, self._down), (going_up, going_down)):
      for i, bbox in zip(idxs, bboxes):
        bbox.direction = direction
        if i in self.positions and self.positions[i].direction!=direction:
          going.append(i)
        self.positions[i] = bbox

    return going_up, going_down

class VehicleTracking:
  """ Class to keep track of mapping of vehicle indexes to bboxes"""

  def __init__(self):
    self.positions = dict()

  def any_currently_tracked(self):
    return len(self.positions)>0

  def get_tracked_bboxes(self):
    return self.positions

  def update_pos(self, idxsToRemove, idxsPresent, bboxes):
    for i in idxsToRemove:
      if i in self.positions:
        del self.positions[i]
    areNew = []
    for i, bbox in zip(idxsPresent, bboxes):
      if i not in self.positions:
        areNew.append(i)
      self.positions[i] = bbox
    return areNew


def create_costs_matrix(A : np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Function to get a matrix C from two vectors of positions (A and B) so C_i_j is the cost (distance) between i-th element from A and j-th element from B.
    inputs:
        A : np.ndarray -> Numpy array with shape (n,2).
        B : np.ndarray -> Numpy array with shape (m,2).

    outputs:
        C : np.ndarray -> Numpy array with shape (n,m).
    """

    #print(B)
    assert len(A.shape) == 2
    assert len(B.shape) == 2
    assert A.shape[1] == 2
    assert B.shape[1] == 2

    n = A.shape[0]
    m = B.shape[0]
    C = -1*np.ones(shape=(n, m))

    for i in range(n):
        for j in range(m):
            C[i,j] = np.linalg.norm(A[i]-B[j])

    return C


class Trace:
    """
    Class to represent a complete trace.
    """

    def __init__(self, trace_id:int, initial_position:np.ndarray):
        """
        inputs:
            trace_id : int -> trace identification number.
            initial_position : np.ndarray -> Numpy array with shape (2).
        """
        self.id = trace_id                          # Trace id.
        self.positions = [initial_position]         # Last known position.
        self.skipped_frames = 0                     # Number of frames already skipped.

    def skipped(self):
        self.add_None_position()
        self.skipped_frames += 1

    def get_last_position(self):
        return self.positions[-1]

    def get_last_not_None_position(self):
        for p in reversed(self.positions):
            if not p is None:
                return p

    def add_position(self, position):
        assert not position is None
        self.positions.append(position)
        self.skipped_frames = 0

    def add_None_position(self):
        self.positions.append(None)

    def get_skipped_frames(self):
        return self.skipped_frames

    def get_id(self):
        return self.id

    def get_positions(self):
        return self.positions

    def get_not_None_positions(self):

        l = []
        for p in self.positions:
            if not p is None:
                l.append(p)
        return l

class Tracker:
    """
    Class to rerepresent a Tracker.
    """
    def __init__(self, maximum_distance_to_assign:int, maximum_frames_to_skip_before_set_trace_as_inactive:int, value_to_use_as_inf = 50000):
        """
        inputs:
            maximum_distance_to_assign : int -> The reference we will use as maximum distance in order to avoid assignments between positions too far.
            maximum_frames_to_skip_before_set_trace_as_inactive : int -> The amount of frames we will allow to be skkiped by a trace before setting it as inactive.
            value_to_use_as_inf : int -> The value to use instead of infinite as "very large value" in order to avoid numerical problems.
        """
        self.active_traces = []                                         # Active traces.
        #self.inactive_traces = []                                       # Old traces. self.active_traces and self.inactive_traces should be disjoint sets.
        self.next_trace_id = 0                                          # Next trace id.
        self.maximum_distance_to_assign = maximum_distance_to_assign    # Beyond this distance, any association will be discarded.
        self.maximum_frames_to_skip_before_set_trace_as_inactive = maximum_frames_to_skip_before_set_trace_as_inactive # Maximum skipped frames number before set a trace as inactive.

        self.value_to_use_as_inf = value_to_use_as_inf

    def new_trace(self, position):
        self.active_traces.append(Trace(self.next_trace_id, position))
        self.next_trace_id += 1

        return self.next_trace_id-1

    def active_traces_last_positions(self):
        last_positions = []
        for trace in self.active_traces:
            last_positions.append(trace.get_last_not_None_position())

        return np.array(last_positions)

    def get_active_traces(self):
        return self.active_traces

    def assign_incomming_positions(self, new_positions:np.ndarray):
        """
        Method to insert new positions in order to be associated to active traces. All position without valid association will start its own new trace.
        intpus:
            new_positions : np.ndarray -> A numpy array with shape (n,2).

        outputs:
            associated_ids : np.ndarray -> Each trace id associated to the incomming positions.
        """
        associated_ids = new_positions.shape[0]*[None]
        inactive_traces = []

        # If there are no active traces.
        if len(self.active_traces) == 0:
            for pos_index in range(new_positions.shape[0]):
                new_trace_id = self.new_trace(new_positions[pos_index])
                associated_ids[pos_index] = new_trace_id

        # If there are no new positions.
        if new_positions.shape[0] == 0:
            # We will increase skipped frames for each trace.
            for trace_index in range(len(self.active_traces)):
                self.active_traces[trace_index].skipped()

            # We will move each active trace with too much skipped frames to inactive traces.
            for trace_index in reversed(list(range(len(self.active_traces)))):
                if self.active_traces[trace_index].get_skipped_frames() > self.maximum_frames_to_skip_before_set_trace_as_inactive:
                    trace = self.active_traces.pop(trace_index)
                    #self.inactive_traces.append(trace)
                    inactive_traces.append(trace.get_id())

        if len(self.active_traces) > 0 and  new_positions.shape[0] > 0:
            traces_last_positions = self.active_traces_last_positions()

            costs_matrix = create_costs_matrix(traces_last_positions, new_positions) # We get the assignment cost between incomming positions and active traces last known positions.

            assert costs_matrix.shape[0] == traces_last_positions.shape[0]
            assert costs_matrix.shape[1] == new_positions.shape[0]

            # We set any cost value greater than self.maximum_distance_to_assign as self.value_to_use_as_inf.
            costs_matrix[costs_matrix > self.maximum_distance_to_assign] = self.value_to_use_as_inf

            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
            trace_indices, pos_indices = linear_sum_assignment(costs_matrix)

            assigned_positions = []
            assigned_traces = []

            # Now the i-th index in trace_indices and i-th in pos_indices should be the optimal assignment.
            for trace_index, pos_index in zip(trace_indices, pos_indices):
                cost = costs_matrix[trace_index, pos_index]
                # If the assignment has lesser cost than self.maximum_distance_to_assign, we assignt the position to the trace.
                if cost < self.maximum_distance_to_assign:
                    self.active_traces[trace_index].add_position(new_positions[pos_index])
                    assigned_positions.append(pos_index)
                    assigned_traces.append(trace_index)
                    associated_ids[pos_index] = self.active_traces[trace_index].get_id()

            # We will increase skipped frames for each non assigned trace.
            for trace_index in range(len(self.active_traces)):
                if not trace_index in assigned_traces:
                    self.active_traces[trace_index].skipped()

            # We will move each active trace with too much skipped frames to inactive traces.
            for trace_index in reversed(list(range(len(self.active_traces)))):
                if self.active_traces[trace_index].get_skipped_frames() > self.maximum_frames_to_skip_before_set_trace_as_inactive:
                    trace = self.active_traces.pop(trace_index)
                    #self.inactive_traces.append(trace)
                    inactive_traces.append(trace.get_id())

            # We will generate new traces from non assigned positions.
            for pos_index in range(new_positions.shape[0]):
                if not pos_index in assigned_positions:
                    new_trace_id = self.new_trace(new_positions[pos_index])
                    associated_ids[pos_index] = new_trace_id

        return associated_ids, inactive_traces

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import json
import time
import datetime

import warnings


class Counter:
  """ dumb counter class """
  __slots__ = 'minute', 'hour', 'day'
  def __init__(self):
    self.reset_all()
  def add(self, n):
    self.minute += n
    self.hour   += n
    self.day  += n
  def reset(self, period):
    setattr(self, period, 0)
  def reset_all(self):
    self.minute = 0
    self.hour   = 0
    self.day  = 0


class DataCounter:
  """ Class keeping track of all counters """

  def __init__(self):
    self.vehicles  = Counter()
    self.peds      = Counter()
    self.peds_up   = Counter()
    self.peds_down = Counter()
    self.all       = [self.vehicles, self.peds, self.peds_up, self.peds_down]

  def any_counted(self, period):
    return any(getattr(c, period)>0 for c in self.all)

  def add_ped_up(self, n):
    self.peds.add(n)
    self.peds_up.add(n)

  def add_ped_down(self, n):
    self.peds.add(n)
    self.peds_down.add(n)

  def add_vehicle(self, n):
    self.vehicles.add(n)

  def reset(self, period):
    for c in self.all:
      c.reset(period)

  def reset_all(self):
    for c in self.all:
      c.reset_all()

  def get_data(self, period):
    """ Generate dictionary of counters. Keys have two letters.
      The first one is one of 'v' (vehicles), 'p' (pedestrians), 'u' (ped. going up), or 'd' (ped. going down).
      The last one is one of 'm' (minute), 'h', (hour), or 'd' (day)."""
    return {k+period[0]: getattr(c, period) for k, c in zip('vpud', self.all)}

class BackEnd:
  """ class to write vehicle / pedestrian counters to the cloud backend """

  def __init__(self, projName, credfile):
    cred = credentials.Certificate(credfile)
    firebase_admin.initialize_app(cred, {
      'projectId': projName,
    })

    self.fb = firestore.client()

    self.format = {'minute': "%Y:%m:%d:%H:%M", 'hour': "%Y:%m:%d:%H", 'day': "%Y:%m:%d"}

  def post_data(self, data, now, period):
    entry = now.strftime(self.format[period])
    try:
      doc_ref = self.fb.collection('by_'+period).document(entry)
      doc_ref.set(data)
    except:
      print('Failed to POST data to by_%s at %s: %s' % (period, entry, str(data)))

class RecordCounters:
  """ Glue logic to count things and save the counters to the backend """
  def __init__(self, record_minute, record_hour, record_day, projName, credFile):
    self.record_minute = record_minute
    self.record_hour   = record_hour
    self.record_day    = record_day
    self.recordAny     = self.record_day or self.record_hour or self.record_minute
    if self.recordAny:
      self.counters    = DataCounter()
      self.backend     = BackEnd(projName, credFile)
      self.start()

  def start(self):
    now = datetime.datetime.now()
    self.current_minute = now.minute
    self.current_hour   = now.hour
    self.current_day    = now.day
    self.counters.reset_all()
    periods    = ['minute', 'hour', 'day']
    currents   = ['current_'+p for p in periods]
    records    = [getattr(self, 'record_'+p) for p in periods]
    self.names = list(zip(periods, currents, records))


  def add(self, new_vehicles, new_peds_up, new_peds_down):
    """ This is the only method to call from the outside """
    if self.recordAny:
      self.counters.add_vehicle( len(new_vehicles))
      self.counters.add_ped_up(  len(new_peds_up))
      self.counters.add_ped_down(len(new_peds_down))
      self.record()

  def record(self):
    """ record minute / hour / day stats on the backend """
    now = datetime.datetime.now()
    # this check is redundant with the next one, but this way we avoid multiple dynamic checks every frame
    if self.current_minute != now.minute:
      for period, current, record in self.names:
        actual = getattr(now, period)
        if getattr(self, current)!=actual:
          setattr(self, current, actual)
          if record and self.counters.any_counted(period):
           data = self.counters.get_data(period)
           self.backend.post_data(data, now, period)
           self.counters.reset(period)
        else:
          break


# Author : Tim Destan
#
# Basic unit tests for the canopies blocker.

from canopies import *
import unittest
from math import log
from collections import defaultdict

def cheap_compare(r1,r2):
  abs(log(r1+1) - log(r2+1))

def mod12_er(rs):
  h = defaultdict(list)
  for rset in rs:
    for r in rset:
      h[r%12].append(r)
  return h.values()

class CanopiesTests(unittest.TestCase):
  """
  Test cases for canopies blocker.
  """
  def create(self):
    records = range(100)
    #shuffle(records)
    return CanopiesBlocker(records, cheap_compare,mod12_er,2,1, randomize=True)

  def test_create(self):
    """
    Blocker should be created successfully
    """
    blocker = self.create()
    self.assertIsNotNone(blocker)

  def test_t1_less_than_t2(self):
    """
    Blocker should detect error
    """
    raised = False
    try:
      blocker = CanopiesBlocker(range(100), lambda (x,y): 0, lambda r:[], 2, 3)
    except ValueError:
      raised = True
    self.assertTrue(raised)

  def test_run(self):
    """
    Simple test run
    """
    blocker = self.create()
    clustering = blocker.cluster()
    self.assertIsNotNone(clustering)
    self.assertGreater(len(clustering),0)
    for cluster in clustering:
      first = None
      for baserecord in cluster:
        if first is None:
          first = baserecord
        else:
          self.assertEquals(first%12, baserecord%12)
    #print clustering
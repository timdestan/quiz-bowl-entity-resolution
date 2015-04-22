# Author : Tim Destan
#
# This file contains basic unit tests for the
# Lego blocker.

import unittest
from lego import *
from random import shuffle
from collections import defaultdict

def compare_with(rs, fn):
  h = defaultdict(set)
  for r in rs:
    h[fn(r)].add(r)
  return h.values()

cmp_mod2 = lambda rs: compare_with(rs, lambda n: n % 2)
cmp_mod3 = lambda rs: compare_with(rs, lambda n: n % 3)
cmp_mod4 = lambda rs: compare_with(rs, lambda n: n % 4)

comparers = [cmp_mod2, cmp_mod3, cmp_mod4]

def mod12_er(rs):
  h = defaultdict(set)
  for r in rs:
    val = 0
    for base in r:
      val |= base % 12
    [h[val%12].add(base) for base in r]
  return h.values()

class LegoTests(unittest.TestCase):
  """
  Test cases for lego blocker.
  """
  def create(self):
    records = range(100)
    shuffle(records)
    return LegoBlocker(records, comparers, mod12_er)

  def test_create(self):
    """
    Blocker should be created successfully
    """
    blocker = self.create()
    self.assertIsNotNone(blocker)

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

# Author: Tim Destan
# Min Hash tests

from minhash import *
import unittest
import random

MAX_HASHES = 20

strings = ["you","have","no","faith","in","medicine"]

s12 = set([strings[x] for x in [1,2]])
s13 = set([strings[x] for x in [1,3]])
s123 = set([strings[x] for x in [1,2,3]])

s2 = set([strings[x] for x in [2]])
s23 = set([strings[x] for x in [2,3]])
s24 = set([strings[x] for x in [2,4]])

ss = [s12, s12, s123, s2, s23, s24]

available_hash_ids = range(MAX_HASHES)

class MinHashTests(unittest.TestCase):
  """
  Not much to test here, can only test that the
  hashes are deterministic for sets of equal
  content.
  """
  
  def create(self):
    return MinHashGenerator()

  def test_deterministic(self):
    gen = self.create()
    for hshid in available_hash_ids:
      for s in ss:
        h1 = gen.minhash(s, hshid)
        h2 = gen.minhash(s.copy(), hshid)
        self.assertEquals(h1,h2)

  def test_det_hashes(self):
    hshids = [1,4,3,12,7,5]
    gen = self.create()
    for s in ss:
      hs1 = gen.minhashes(s,hshids)
      hs2 = gen.minhashes(s.copy(),hshids)
      self.assertEquals(hs1, hs2)
  
  def test_reset(self):
    gen = self.create()
    for hshid in available_hash_ids:
      for s in ss:
        # Could get unlucky here but hope not
        h1 = gen.minhash(s, hshid)
        # fake randomness...
        gen.reset(seed = random.getrandbits(64))
        h2 = gen.minhash(s, hshid)
        self.assertNotEquals(h1,h2)


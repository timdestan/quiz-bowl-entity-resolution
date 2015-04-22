# Author : Tim Destan
# Clustering tests

import unittest
from cluster import *

base = [1,2,10,12,13,34]
records = range(len(base))

def distance(x,y,normalizer=1):
  return abs(x["xposition"] - y["xposition"])

def dumb_features(x):
  return dict([("xposition",base[x])])

class FeatureBasedClustererTests(unittest.TestCase):

  def create(self, threshold=None, distanceFunction=distance):
    return AgglomerativeCluster([set({x}) for x in records], [dumb_features(x) for x in xrange(len(base))],\
      threshold=threshold, distanceFunction=distanceFunction)

  def test_create(self):
    c = self.create()
    self.assertIsNotNone(c)

  def test_cluster(self):
    c = self.create()
    clusters = c.cluster()
    self.assertEquals(1, len(clusters))
    for cluster in clusters:
      for b in records:
        self.assertTrue(b in cluster)

  def test_cluster_with_feat_dist(self):
    c = self.create(distanceFunction=feature_distance)
    clusters = c.cluster()
    self.assertEquals(1, len(clusters))
    for cluster in clusters:
      for b in records:
        self.assertTrue(b in cluster)

  def test_cluster_with_threshold(self):
    c = self.create(threshold=5)
    clusters = c.cluster()
    self.assertEquals(3, len(clusters))
    for cluster in clusters:
      realCluster = [base[x] for x in cluster]
      #print "Here be cluster:",realCluster
      if 1 in realCluster:
        self.assertEquals(2, len(realCluster))
        self.assertTrue(2 in realCluster)
      if 10 in realCluster:
        self.assertEquals(3, len(realCluster))
        self.assertTrue(12 in realCluster)
        self.assertTrue(13 in realCluster)
      if 34 in realCluster:
        self.assertEquals(1, len(realCluster))

  def test_cluster_with_threshold_and_feat_dist(self):
    c = self.create(threshold=5, distanceFunction=feature_distance)
    clusters = c.cluster()
    self.assertEquals(3, len(clusters))
    for cluster in clusters:
      realCluster = [base[x] for x in cluster]
      #print "Here be cluster:",realCluster
      if 1 in realCluster:
        self.assertEquals(2, len(realCluster))
        self.assertTrue(2 in realCluster)
      if 10 in realCluster:
        self.assertEquals(3, len(realCluster))
        self.assertTrue(12 in realCluster)
        self.assertTrue(13 in realCluster)
      if 34 in realCluster:
        self.assertEquals(1, len(realCluster))

# Author : Tim Destan
# Feature based clusterer

from collections import defaultdict
from qbcommon import all_pairs_symmetric
from featurespace import *

import logging
logger = logging.getLogger("FeatureClusterer")

class ScoreTypes(object):
  DISTANCE = "DISTANCE"
  SIMILARITY = "SIMILARITY"

class GuidGenerator(object):
  """
  Generates globally unique identifiers.
  """
  def __init__(self):
    self.next = 0

  def new_id(self):
    """
    Returns a new ID
    """
    self.next += 1
    return self.next

class AgglomerativeCluster(object):
  """
  Agglomerative clusterer based on a feature distance function that takes
  features as vectors from names to values.
  """
  def __init__(self, compositeRecords, featureSets, scoreFunction,
      threshold=None, scoreType=ScoreTypes.DISTANCE, baseDistanceCache={},
      guidGenerator=GuidGenerator(), globalClusters={}):
    """
    Constructor

    :param compositeRecords: Collection of composite records to classify.
    :param featureSets: List of featuresets. Each base record is
      interpreted as an index into this list.
    :param threshold: Optional distance threshold for when to stop merging clusters.
    :param scoreFunction: A distance function to compute the distance between two
      feature vectors. Should be a distance metric.
    :param baseDistanceCache: A cache of distances between base records.
    """
    self.baseFeatureArray = featureSets
    self.scoreFunction = scoreFunction

    self.onMerge = lambda slf, thresh: ()

    self.informative_features = defaultdict(float)

    if scoreType == ScoreTypes.DISTANCE:
      self.scoreIsBetter = lambda score, best: score < best
    elif scoreType == ScoreTypes.SIMILARITY:
      self.scoreIsBetter = lambda score, best: score > best
    else:
      raise ValueError("Unknown Score type: %s" % repr(scoreType))

    if threshold is None:
      logger.warn("Threshold should probably be specified.. Defaulting to infinity..")
      self.threshold = InfiniteFeatureComparisonResult()
    else:
      self.threshold = ConstantValueFeatureComparisonResult(threshold)

    # Define two maps, one from records to cluster identifiers (which we will
    # start with each record in a cluster with its own identifier) and a second
    # from cluster identifiers to the records contained therein.
    #
    self.b2c = {}
    self.c2b = {}
   
    # Presently unused
    self.globalClusters = globalClusters

    self.guidGenerator = guidGenerator

    for compositeRecord in compositeRecords:
      clusterIndex = self._newClusterId()
      self.c2b[clusterIndex] = compositeRecord
      for baseRecord in compositeRecord:
        self.b2c[baseRecord] = clusterIndex

    # Cache distances between two clusters and between base recs.
    #
    if baseDistanceCache:
      self.baseDistanceCache = baseDistanceCache
    else:
      self.baseDistanceCache = {}
    self.clusterDistanceCache = {}

  def _newClusterId(self):
    """Gets a new cluster ID unique to this object"""
    return self.guidGenerator.new_id()

  def _baseDistance(self, b1, b2):
    """
    Computes the distance between two base records

    :param b1: one record
    :param b2: another one
    """
    if b1 > b2:
      b1, b2 = b2, b1
    distance = self.baseDistanceCache.get((b1,b2), None)
    if distance is None:
      distance = self.scoreFunction(\
        self.baseFeatureArray[b1], self.baseFeatureArray[b2])
      self.baseDistanceCache[(b1,b2)] = distance
    return distance

  def distance(self, c1, c2):
    """
    Computes the difference between the clusters with the given identifiers.

    :param c1: a cluster identifier
    :param c2: another cluster identifier

    :returns: The distance between the two identified clusters.
    """
    # Concrete class should provide implementation.
    #
    raise NotImplemented

  def mergeClusters(self,c1,c2):
    """
    Merges the two argument clusters.

    :param c1: A cluster identifier
    :param c2: Another cluster identifier.
    """
    combinedBaseRecords = (self.c2b[c1] | self.c2b[c2])
    # Remove these two clusters.
    del self.c2b[c1]
    del self.c2b[c2]
    cNew = self._newClusterId()
    self.c2b[cNew] = combinedBaseRecords
    for baseRecord in combinedBaseRecords:
      self.b2c[baseRecord] = cNew

  def mergeNearestClusters(self):
    """
    Finds the two clusters at the minimum distance and merges them together.
    
    :returns: True if we merged any clusters.
    """
    if len(self.c2b) <= 1:
      # Cannot merge if there is only 1 cluster remaining.
      #
      logger.debug("Only one cluster left, terminating clustering.")
      return False

    bestDistance = None
    cbest1, cbest2 = None, None

    for c1,c2 in all_pairs_symmetric(self.c2b.keys()):
      distance = self.distance(c1,c2)
      if (not bestDistance) or self.scoreIsBetter(distance, bestDistance):
        bestDistance = distance
        cbest1, cbest2 = c1, c2

    #assert(cbest1 is not None and cbest2 is not None)

    if self.scoreIsBetter(self.threshold, bestDistance):
      logger.debug("Best score %g passed score threshold %g, terminating clustering." % \
        (bestDistance.total(), self.threshold.total()))
      return False
    contrib = bestDistance.feature_contributions()
    for feat in contrib:
      self.informative_features[feat] += contrib[feat]
    # This line is just too much output, makes debug level unusuable. Occasionally
    # uncommented when something in this class needs to be carefully debugged.
    #
    #logger.debug("Merging " + repr(self.c2b[cbest1]) + " and " + repr(self.c2b[cbest2]) + \
    #  " with score " + repr(bestDistance.total()) + ".")
    self.mergeClusters(cbest1, cbest2)
    self.onMerge(self, bestDistance)
    return True

  def cluster(self):
    """Clusters the records and returns the resulting clusters"""
    logger.debug("Beginning feature based clustering on %d clusters." % len(self.c2b))
    # Merge the two nearest clusters until we can't.
    #
    while self.mergeNearestClusters():
      pass
    logger.debug("After clustering, there are now %d clusters remaining." % len(self.c2b))
    return self.c2b.values()

class MinDistanceAgglomerativeCluster(AgglomerativeCluster):
  """
  Agglomerative clusterer that compares two clusters by the distance between
  their closest two points.
  """
  def distance(self, c1, c2):
    """
    Computes the difference between the clusters with the given identifiers.

    :param c1: a cluster identifier
    :param c2: another cluster identifier

    :returns: The distance between the two identified clusters.
    """
    if c1 > c2:
      c1, c2 = c2, c1
    clusterDistance = self.clusterDistanceCache.get((c1,c2), None)
    if clusterDistance is None:
      # Find the minimum distance between any two pairs in the clusters.
      #
      minDistance = InfiniteFeatureComparisonResult()
      for b1 in self.c2b[c1]:
        for b2 in self.c2b[c2]:
          baseDistance = self._baseDistance(b1, b2)
          if baseDistance < minDistance:
            minDistance = baseDistance
      clusterDistance = minDistance
      self.clusterDistanceCache[(c1,c2)] = clusterDistance
    return clusterDistance

class MaxDistanceAgglomerativeCluster(AgglomerativeCluster):
  """
  Agglomerative clusterer that compares two clusters by the distance between
  their farthest two points.
  """
  def distance(self, c1, c2):
    """
    Computes the difference between the clusters with the given identifiers.

    :param c1: a cluster identifier
    :param c2: another cluster identifier

    :returns: The distance between the two identified clusters.
    """
    if c1 > c2:
      c1, c2 = c2, c1
    clusterDistance = self.clusterDistanceCache.get((c1,c2), None)
    if clusterDistance is None:
      # Find the maximum distance between any two pairs in the clusters.
      #
      maxDistance = ConstantValueFeatureComparisonResult(0.0)
      for b1 in self.c2b[c1]:
        for b2 in self.c2b[c2]:
          baseDistance = self._baseDistance(b1, b2)
          if baseDistance > maxDistance:
            maxDistance = baseDistance
      clusterDistance = maxDistance
      self.clusterDistanceCache[(c1,c2)] = clusterDistance
    return clusterDistance

class AverageDistanceAgglomerativeCluster(AgglomerativeCluster):
  """
  Agglomerative clusterer that compares two clusters by the average distance
  between the points in those clusters.
  """
  def distance(self, c1, c2):
    """
    Computes the difference between the clusters with the given identifiers.

    :param c1: a cluster identifier
    :param c2: another cluster identifier

    :returns: The distance between the two identified clusters.
    """
    if c1 > c2:
      c1, c2 = c2, c1
    clusterDistance = self.clusterDistanceCache.get((c1,c2), None)
    if clusterDistance is None:
      totalDistance = FeatureComparisonResult() # 0.0
      count = 0
      for b1 in self.c2b[c1]:
        for b2 in self.c2b[c2]:
          totalDistance = totalDistance.add(self._baseDistance(b1, b2))
          count += 1
      if count == 0:
        clusterDistance = FeatureComparisonResult() # 0.0
      else:
        clusterDistance = totalDistance.normalize(count)
      self.clusterDistanceCache[(c1,c2)] = clusterDistance
    return clusterDistance
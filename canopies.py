# Author: Tim Destan
#
# Implementation of Canopies meta-algorithm

from random import shuffle
from cluster import ScoreTypes
import logging
logger = logging.getLogger("Canopies")

class Canopy(object):
  """
  Class representing a single canopy.

  Just wraps the records. Thought this would need to do something, but it
  turned out it didn't.
  """
  def __init__(self, records):
    """
    Constructor

    :param records: The records in this canopy.
    """
    self.records = records

class CanopiesBlocker(object):
  """
  Class to do blocking using canopies.
  """
  def __init__(self, records, cheapDistanceMetric,ermethod,t1,t2,scoreType, randomize=True):
    """
    Constructor

    :param records: all the records to cluster
    :param cheapDistanceMetric: A cheap distance metric used to form the canopies.
    :param ermethod: An ER method to do the full clustering within each canopy.
    :param t1: First threshold for canopies
    :param t2: Second threshold for canopies
    :param randomize: If true, randomize the order the records are considered in.
    """
    self.records = records
    self.cheapMetric = cheapDistanceMetric
    if not callable(self.cheapMetric):
      raise ValueError("Cheap distance metric must be callable function.")
    self.method = ermethod
    self.t1 = t1
    self.t2 = t2

    if scoreType == ScoreTypes.DISTANCE:
      self.scoreIsBetter = lambda score, best: score < best
    elif scoreType == ScoreTypes.SIMILARITY:
      self.scoreIsBetter = lambda score, best: score > best
    else:
      raise ValueError("Unknown Score type: %s" % repr(scoreType))

    if self.scoreIsBetter(self.t1, self.t2):
      raise ValueError("T1 must be a worse threshold than T2")
    self.randomize = randomize

    self.canopies = [] # postpone construction until later.
    self.num_canopies = 0

  def _measure_cheap_distances(self, lst, center):
    """
    Measure all the (cheap) distances from points in lst to center.

    :param lst: List of points under consideration
    :param center: Center to measure distances from.
    :returns: Dictionary of distances.
    """
    distances = {}
    for pnt in lst:
      # Assume it is symmetric so we don't care the order.
      distances[pnt] = self.cheapMetric(pnt, center)
    return distances

  def _find_points_within_thresholds(self, lst, center):
    """
    Find all points within thresholds of center in lst.
    
    :param lst: List of records to consider
    :param center: center of the canopy being constructed.
    :returns: A pair (within_t1, within_t2) of sets of points
      within thresholds 1 and 2 respectively.
    """
    cheapDistances = self._measure_cheap_distances(lst, center)
    within_t1 = set([center])
    within_t2 = set([center])
    for (record, distance) in cheapDistances.items():
      if self.scoreIsBetter(distance, self.t2):
        # T1 is worse than T2, so therefore distance <= self.t1 as well.
        within_t1.add(record)
        within_t2.add(record)
      elif self.scoreIsBetter(distance, self.t1):
        within_t1.add(record)
    return within_t1, within_t2

  def _form_canopies(self):
    """
    Forms the canopies to be used in clustering.
    """
    logger.info("Forming canopies for %i records" % len(self.records))
    toBeAssigned = list(self.records)
    if self.randomize:
      shuffle(toBeAssigned)
    toBeAssigned = set(toBeAssigned)

    totalCanopySize = 0.0

    # Continue until all are assigned.
    while len(toBeAssigned) > 0:
      # Pick a new exemplar/center from the points that need to
      # be assigned.
      exemplar = toBeAssigned.pop()
      # Find all points within threshold t1 and t2.
      within_t1, within_t2 = self._find_points_within_thresholds(toBeAssigned, exemplar)
      # Create a new canopy of all the points within threshold
      # T1 and add it to the list.
      #
      newCanopy = Canopy(within_t1)
      self.canopies.append(newCanopy)
      totalCanopySize += len(newCanopy.records)
      # Remove all points within threshold 2 from those
      # that will be considered.
      #
      toBeAssigned -= within_t2

    self.num_canopies = len(self.canopies)
    assert(self.num_canopies > 0)
    logger.info("%i canopies formed, average size = %.3f" % \
      (self.num_canopies, totalCanopySize / self.num_canopies))

  def _transitive_closure(self, clusterings):
    """
    Computes a transitive closure from the given clusterings.

    :param clusterings: An enumerable of clusterings, each of which
      is an enumerable of clusters, each of which is a set of records.
    :returns: The transitive closure implied by all these clusterings.
    """
    
    finalClusters = []
    finalClusterLookup = {}

    for clustering in clusterings:
      for cluster in clustering:
        # Find any existing clusters that need to be merged.
        #
        existingClusters = []
        for record in cluster:
          if record in finalClusterLookup:
            existingClusters.append(finalClusterLookup[record])
        # If there are one or more existing clusters, remove these
        # from the final cluster list and merge them into this one.
        #
        if len(existingClusters) > 0:
          for existingCluster in existingClusters:
            # The same cluster can show up in existing clusters more than once,
            # so we need to check if it is in the final clusters. If it is, we
            # want to remove it and union it with the cluster that is replacing
            # it.
            #
            if existingCluster in finalClusters:
              finalClusters.remove(existingCluster)
              cluster |= existingCluster
        # Add our cluster to the final cluster list.
        #
        finalClusters.append(cluster)
        # Update the lookup data structure for every record inside.
        #
        for record in cluster:
          finalClusterLookup[record] = cluster

    return finalClusters

  def cluster(self):
    """
    Runs the ER technique with canopies, producing a clustering
    of the input records.

    :returns: The clusters found by the algorithm (a list of sets of base records)
    """
    self._form_canopies()
    clusterings = []
    # Make clusterings for each canopy.
    for canopy in self.canopies:
      recordsInCanopy = [set([x]) for x in canopy.records]
      # Use ER method to cluster 
      logger.info("Clustering canopy of size %i" % len(recordsInCanopy))
      clustering = self.method(recordsInCanopy)
      clusterings.append(clustering)
    return self._transitive_closure(clusterings)

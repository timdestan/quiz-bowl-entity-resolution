# Author: Tim Destan
# Evaluation-related code in here

from math import log
from collections import defaultdict
import logging
logger = logging.getLogger("Evaluation")

from qbcommon import all_pairs_symmetric
from nltk.util import ngrams
from settings import getRelevantOptions, getRelevantOptionNames

def cluster_by_label(labeled_featuresets):
  """
  Form the gold standard cluster by clustering
  the indices of the questions by their label.
  """
  ii = 0
  clusters = defaultdict(set)
  # Just add each question index to a cluster
  # corresponding to its answer label.
  #
  for (features, label) in labeled_featuresets:
    clusters[label].add(ii)
    ii += 1
  return clusters.values()

def report_informative_features(informative_features):
  features = sorted(informative_features.items(), key=lambda (k,v):v, reverse=True)
  print "Informative Features for clustering:"
  for (feat, value) in features:
    print "\t",feat, ":", value

def makebase2idhash(clustering):
  """
  Makes a hash from the clustering with unique IDs.

  :param clustering: A list of sets of base records.
  :returns: A hash such that:
    Each key is a base record.
    Each value is a unique identifier of a cluster.
  """
  nextIdentifier = 0
  rv = {}
  for cluster in clustering:
    for baseRecord in cluster:
      rv[baseRecord] = nextIdentifier
    nextIdentifier += 1
  return rv

def reverse_hash(hsh):
  """
  Reverses a hash.
  """
  rv = defaultdict(set)
  for key in hsh:
    rv[hsh[key]].add(key)
  return rv

def pairwise_f1(baserecords, experimental, golden):
  """
  F1 score based on fraction of pairs in the two clusters.

  :param baserecords: Base records.
  :param experimental: Cluster generated experimentally.
  :param golden: The cluster that is known to be whatever we are calling
    the "right" answer.
  :returns; pairwise F1, precision, and recall
  """
  experimentalHash = makebase2idhash(experimental)
  goldenHash = makebase2idhash(golden)

  r_den = 0.0 # Recall denominator
  p_den = 0.0 # Precision denominator
  num = 0.0   # Numerator (both)
  # Enumerate all possible pairs.
  #
  for b1,b2 in all_pairs_symmetric(baserecords):
    gmatch = (goldenHash[b1] == goldenHash[b2])
    ematch = (experimentalHash[b1] == experimentalHash[b2])
    # Accumulate counts.
    # If the gold cluster matches a pair but not the experimental cluster,
    #   this counts against the recall.
    # If the experimental cluster matches a pair but not the gold cluster,
    #   this counts against the precision.
    #
    if gmatch:
      r_den += 1
      if ematch:
        num += 1
      # else:
      #   logging.debug("%d and %d together in reference clusters but not experimental." % (b1,b2))
    if ematch:
      p_den += 1

  precision = 0.0
  if p_den > 0:
    precision = num / p_den
  recall = 0.0
  if r_den > 0:
    recall = num / r_den
  f1 = 0.0
  if (precision + recall) > 0:
    f1 = 2.0 * (precision * recall) / (precision + recall)
  return f1,precision,recall

def cluster_report(clustering):
  for cluster in clustering:
    print "\t%s" % repr(cluster)

def cluster_f1(experimental, golden):
  """
  F1 score based on overlap of the clusters.

  :param experimental: Cluster generated experimentally.
  :param golden: The cluster that is known to be whatever we are calling
    the "right" answer.
  :returns: The cluster-based F1, precision, and recall
  """
  
  # Denominators here are just the number of clusters in each.
  p_den = len(experimental)
  r_den = len(golden)

  # Numerator is the size of the intersection.
  num = 0.0
  for cluster in golden:
    if cluster in experimental:
      num += 1
  precision = 0.0
  if p_den > 0:
    precision = num / p_den
  recall = 0.0
  if r_den > 0:
    recall = num / r_den
  f1 = 0.0
  if (precision + recall) > 0:
    f1 = 2.0 * (precision * recall) / (precision + recall)
  return f1,precision,recall

def variation_of_information(experimental, golden, n):
  """
  Computes the variation of Information

  :param n: Number of records.
  :param experimental: Clustering generated experimentally.
  :param golden: The clustering that is known to be whatever we are calling
    the "right" answer.
  :returns: The VI measure
  """
  n = float(n)
  
  e_entropy = 0.0
  for cluster in experimental:
    ratio = len(cluster) / n
    e_entropy -= ratio * log(ratio)

  r_entropy = 0.0
  for cluster in golden:
    ratio = len(cluster) / n
    r_entropy -= ratio * log(ratio)

  mutual_information = 0.0
  for e_cluster in experimental:
    e_size = len(e_cluster)
    for g_cluster in golden:
      g_size = len(g_cluster)
      intersect_size = len(e_cluster.intersection(g_cluster))
      if intersect_size > 0:
        mutual_information += (intersect_size / n) * \
          log( (intersect_size * n) / (e_size * g_size))

  return e_entropy + r_entropy - 2 * mutual_information

def write_csv_column_names():
  """
  Write names of columns used in CSV output.
  """
  logger.info("Writing column names...")
  print ",".join([str(x) for x in ["pairwise f1", "pairwise precision", "pairwise recall", \
    "cluster f1", "cluster precision", "cluster recall", "VI"] + getRelevantOptionNames()])

def report_feature_distances(allClues, clusters, labeledFeaturesets, distance):
  """
  Reports the feature distance between every pair of clues. Note if they share a cluster.
  """
  logger.info("Writing all possible thresholds ...")
  b2id = makebase2idhash(clusters)
  
  scores = {}
  
  total_possible = 0.0

  for x1, x2 in all_pairs_symmetric(allClues):
    if x1 > x2:
      x1,x2 = x2,x1
    scores[(x1,x2)] = distance(labeledFeaturesets[x1][0], labeledFeaturesets[x2][0])
    if b2id[x1] == b2id[x2]:
      total_possible += 1

  total_right = 0
  total_assigned = 0.0
  print "threshold,precision,recall,f1"
  for ((x1,x2), distanceValue) in sorted(scores.iteritems(), key=lambda (k,v): v, reverse=True):
    total_assigned += 1.0
    if b2id[x1] == b2id[x2]:
      total_right += 1
    precision = total_right / total_assigned
    recall = total_right / total_possible
    f1 = 0.0
    if precision + recall > 0.0:
      f1 = 2*precision*recall / (precision + recall)
    print "%f,%f,%f,%f" % (distanceValue.total(), precision, recall, f1)

def report_accuracy(baserecords, experimental, golden, options):
  """
  Report accuracy of an already trained classifier.

  :param baserecords: All base records
  :param experimental: Clusters produced experimentally.
  :param golden: Gold standard clusters 
  :param options: User specified options.
  """
  pf1, pprecision, precall = pairwise_f1(baserecords, experimental, golden)
  cf1, cprecision, crecall = cluster_f1(experimental, golden)
  vi = variation_of_information(experimental, golden, len(baserecords))

  if options.output_format == "VERBOSE":
    print 'Results for', options.algorithm, ' with blocking method =', options.blocking_method
    print 'Reference Clusters:', len(golden)
    print 'Experimentally Generated Clusters:', len(experimental)
    print ("Pairwise: F1:%g, Precision:%g, Recall:%g" % (pf1, pprecision, precall))
    print ("Cluster: F1:%g, Precision:%g, Recall:%g" % (cf1, cprecision, crecall))
    print ("Variation of Information: %g" % vi)
  elif options.output_format == "CSV":
    print ",".join([str(x) for x in [pf1, pprecision, precall, cf1, cprecision, crecall, vi] + getRelevantOptions(options)])
  else:
    assert(options.output_format == "NONE" or options.output_format == "MERGE-CSV")
    pass

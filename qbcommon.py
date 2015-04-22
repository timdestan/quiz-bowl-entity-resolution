# Author: Tim Destan
#
# Common functionality needed by other files is
# gathered here.
#

from collections import defaultdict
from nltk.util import ngrams
from nltk.tokenize import wordpunct_tokenize

def expand_frequencies(dictionary):
  """
  Expands a dictionary where the keys are items and the values are
  counts to an explicit list representation where each key occurs
  exactly that many times.
  """
  return [item for key in dictionary for item in [key] * dictionary[key]]

def merge_clusters(c1,c2):
  """
  Merge the two given clusters.
  """
  ids = {}
  merged = defaultdict(set)
  nextId = 0

  for cluster in c1:
    for base in cluster:
      ids[base] = nextId
      merged[nextId].add(base)
    nextId += 1

  for cluster in c2:
    overlap = set([ids[base] for base in cluster if base in ids])
    if len(overlap) == 0:
      for base in cluster:
        ids[base] = nextId
        merged[nextId].add(base)
      nextId += 1
    else: # len(overlap) >= 1
      # We overlap one or more of the other clusters.
      # Choose one of the overlapping cluster IDs, change
      # any remaining cluster IDs to be that one (to merge
      # them), and then add all our base records to this cluster
      # ID as well.
      #
      clusterId = overlap.pop()
      for otherId in overlap:
        for base in merged[otherId]:
          ids[base] = otherId
          merged[clusterId].add(base)
        del merged[otherId]
      for base in cluster:
        ids[base] = clusterId
        merged[clusterId].add(base)
  return merged.values()

def ngrams_in_question(question,ngram_size=3):
  """
  Returns set of ngrams from question, joined by ~'s.
  """
  words1 = wordpunct_tokenize(question.text.decode('utf8'))
  return set(["~".join(x) for x in ngrams(words1, ngram_size)])

def all_pairs_symmetric(records):
  """
  Generates the cartesian product of record array with itself.
  1) Ignores (x,x) pairs.
  2) Includes only one of (x,y) and (y,x) for y != x
  """
  size = len(records)
  for x in xrange(0, size):
    for y in xrange(x+1, size):
      yield records[x],records[y]

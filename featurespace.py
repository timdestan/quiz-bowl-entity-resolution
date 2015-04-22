# Author: Tim Destan
#
# Classes and functions related to distance of features.
#
# The features of each clue are represented as a FeatureRepresentation
# object. When two of these are compared, the result is returned as a
# FeatureComparisonResult object, which stores the result of the
# comparison as a number, plus which features contributed most heavily
# to the result.

from collections import defaultdict
import logging
from nltk.corpus import wordnet as wn
from nltk.corpus import wordnet_ic
from math import exp, sqrt

logger = logging.getLogger("FeatureSpace")

def sigmoid(x):
  """Computes a sigmoid function"""
  return 1.0 / (1.0 + exp(-x))
  #return 2.0 / (1.0 + exp(-x)) - 1.0
  #return x / (1.0 + abs(x))

class FeatureRepresentation(object):
  """
  Object that contains the feature representation of a given
  clue.
  """
  def __init__(self):
    """Constructor"""
    self.tfidf_features = {}
    self.category = None
    self.referers = []
    self.named_entities = defaultdict(int)

  def __str__(self):
    """ Returns a string representation of this object """
    representation = "Category: " + self.category + "\n"
    representation += "Named Entities:\n"
    for ent in self.named_entities:
      if self.named_entities[ent] > 0:
        representation += "\t" + ent + "\n"
    representation += "Referers:\n"
    for ref in self.referers:
      representation += "\t" + ref + "\n"
    return representation

def make_featuresets(questions, index, options, db=None, disambiguations={}):
  """
  Takes a list of questions and returns a list of feature
  dictionaries and correct classification labels.

  :param questions: The questions to process
  :param index: Inverted index over the questions.
  :param options: Options specified by the user.
  :param db: Database. Only necessary if features have not yet been
    retrieved from the SQLite database.
  :param disambiguations: lookup from question IDs to hand-resolved answers.
    Populated by hand for certain answers known to cause trouble because they
    refer to multiple entities. Note that this isn't "cheating" because if we
    don't do this, the clustering actually does a better job than our reference
    clustering but is penalized for it.

  :returns: A list of tuples. Each tuple if of the form
    (feature dictionary, classification label), which is the format
    most of the NLTK classifiers like. Our algorithms use the features
    from the tuple -- the labels are primarily used to reconstruct the
    reference clusters.
  """
  logger.info("Computing feature representations for %d questions...",
    len(questions))
  labeled_featuresets = []
  for ii in xrange(len(questions)):
    q = questions[ii]

    featureRep = FeatureRepresentation()

    # Create a new feature distribution for this question.
    featDist = defaultdict(float)

    # Enumerate features to fill out the dictionary. The
    # first element in the tuple is the index
    for (_, feat) in q.features(db=db):
      if feat in index.vocab:
        score = index.termFrequency(feat, ii) * index.inverseDocumentFrequency(feat)    
        featDist[feat] += score
      else:
        logger.warning("%s not in vocab" % feat)
        featDist[feat] += 1

    featureRep.tfidf_features = featDist
    featureRep.category = q.cat
    featureRep.referers = q.referers
    featureRep.named_entities = q.named_entities

    label = q.label_id()
    if q.id in disambiguations:
      label = disambiguations[q.id]

    labeled_featuresets.append((featureRep, label))

  return labeled_featuresets

class FeatureComparisonResultBase(object):
  """ Result of a feature comparison (base class)"""

  def __lt__(self, other):
    return (self.total() < other.total())

  def __le__(self, other):
    return (self.total() <= other.total())

  def __gt__(self, other):
    return (self.total() > other.total())

  def __ge__(self, other):
    return (self.total() >= other.total())

  def __eq__(self, other):
    return (self.total() == other.total())

  def __ne__(self, other):
    return (self.total() != other.total())

  def total(self):
    raise NotImplemented

  def add(self, other):
    raise NotImplemented
  
  def normalize(self, normalizer):
    raise NotImplemented

  def feature_contributions(self):
    raise NotImplemented

class FeatureComparisonResult(FeatureComparisonResultBase):
  """ Result of Feature Comparison """
  def __init__(self):
    self.tfidf_comparison = 0.0
    self.category_comparison = 0.0
    self.referers_comparison = 0.0
    self.named_entities_comparison = 0.0
    self._total = 0.0

  def feature_contributions(self):
    """
    Returns a description of which features contributed
    which values.
    """
    contributions = {}
    contributions['tfidf'] = self.tfidf_comparison
    contributions['category'] = self.category_comparison
    contributions['referers'] = self.referers_comparison
    contributions['named'] = self.named_entities_comparison
    return contributions

  def computeTotal(self):
    """
    Taking a lot more time than I thought to add these 4 numbers
    (20% of compute time in some cases!) each time someone calls total
    so now I just call this whenever I change something.

    Less convenient but faster.
    """
    self._total = (self.tfidf_comparison + self.category_comparison + 
      self.referers_comparison + self.named_entities_comparison)

  def total(self):
    """ Gets the total similarity/score value """
    return self._total

  def add(self,other):
    result = FeatureComparisonResult()
    result.tfidf_comparison = self.tfidf_comparison + other.tfidf_comparison
    result.category_comparison = self.category_comparison + other.category_comparison
    result.referers_comparison = self.referers_comparison + other.referers_comparison
    result.named_entities_comparison = self.named_entities_comparison + other.named_entities_comparison
    result.computeTotal()
    return result

  def normalize(self, normalizer):
    if normalizer == 0.0:
      raise ValueError("Can't normalize with a zero")
    result = FeatureComparisonResult()
    result.tfidf_comparison = self.tfidf_comparison / normalizer
    result.category_comparison = self.category_comparison / normalizer 
    result.referers_comparison = self.referers_comparison / normalizer
    result.named_entities_comparison = self.named_entities_comparison / normalizer
    result.computeTotal()
    return result

class ConstantValueFeatureComparisonResult(FeatureComparisonResultBase):
  """
  Represents a feature comparison result that involves
  """
  def __init__(self, value):
    self.value = value

  def total(self):
    return self.value

class InfiniteFeatureComparisonResult(FeatureComparisonResultBase):
  """
  An infinitely large comparison result for comparing two feature 
  representations.
  """
  def total(self):
    return float('inf')

class FeatureComparer(object):
  """
  Comparerer that compares two feature representations.
  """
  def __init__(self, options):
    """ Constructor """
    self.tfidf_weight = options.tf_idf_weight
    self.category_weight = options.category_weight
    self.referers_weight = options.referers_weight
    self.named_entities_weight = options.named_entities_weight
    self.information_content_filename = 'ic-bnc.dat'
    self.ic = wordnet_ic.ic(self.information_content_filename)

    self.synsetCache = defaultdict(float)

  def compare(self, fr1, fr2):
    """
    Compare the two feature representations

    :param fr1: One feature representation
    :param fr2: Another One
    :returns: A similarity score.
    """
    result = FeatureComparisonResult()
    result.tfidf_comparison = self.compareTfIdfDifferences(fr1.tfidf_features, fr2.tfidf_features) * self.tfidf_weight
    if fr1.category == fr1.category:
      result.category_comparison = self.category_weight
    result.named_entities_comparison = self.compareNamedEntities(fr1.named_entities, fr2.named_entities) * self.named_entities_weight
    result.referers_comparison = self.compareReferers(fr1.referers, fr2.referers) * self.referers_weight
    result.computeTotal()
    return result

  def getSynsets(self, referers):
    """ Get all noun synsets for referers """
    synsets = []
    for referer in referers:
      synsets.extend(wn.synsets(referer, pos=wn.NOUN))
    return synsets

  def getSynsetSimilarity(self, s1, s2):
    """
    Get the similarity between the two synsets.
    """
    if s2 < s1:
      s1, s2 = s2, s1
    if (s1,s2) in self.synsetCache:
      return self.synsetCache[(s1,s2)]
    else:
      score = s1.jcn_similarity(s2, self.ic)
      self.synsetCache[(s1,s2)] = score
      return score

  def findBestSynsetDistance(self, ss1, ss2):
    """
    Finds the minimum distance between any synset in ss1 and
    any synset in ss2.
    """
    bestScore = 0.0
    for s1 in ss1:
      for s2 in ss2:
        score = self.getSynsetSimilarity(s1,s2)
        if score > bestScore:
          bestScore = score
    return bestScore

  def compareReferers(self, r1, r2):
    """
    Compare two referers.
    """
    # if len(r1) == 0 and len(r1) == 0:
    #   return 0.0
    # return float(len(r1.intersection(r2))) / len(r1.union(r2))
    r1synsets = self.getSynsets(r1)
    r2synsets = self.getSynsets(r2)
    return sigmoid(self.findBestSynsetDistance(r1synsets, r2synsets))
    
  def compareNamedEntities(self, ne1, ne2):
    """
    Compare two entity sets. Each is represented as a
    dictionary from names of entities to counts of occurrences.

    Counts the agreements in the named entities, weighted by the
    number of appearances.
    """
    score = 0.0
    for k1 in ne1:
      score += ne1[k1] * ne2[k1]
    return score

  def compareTfIdfDifferences(self, q1features, q2features):
    """
    A feature based similarity function between two questions

    :param q1features: features of first question (dictionary)
    :param q2features: features of second question (dictionary)

    :return: The similarity between the two questions.
    """
    allkeys = set(q1features.keys()).intersection(set(q2features.keys()))
    rawscore = sum([(q1features[key] * \
      q2features[key]) for key in allkeys])
    return rawscore
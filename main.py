# Main driver program
# Loads everything else and runs a single experiment.
#
# Author: Tim Destan

from settings import *
from evaluation import *
from minhash import *
from invertedindex import *
from lego import *
from canopies import *
from cluster import *
from chunker import *
from qbcommon import *
from featurespace import *

from math import log, sqrt
from collections import defaultdict

# Main entry point to application
#
if __name__ == "__main__":
  options = parseOptions()
  if options.write_csv_column_names:
    write_csv_column_names()
    exit()
  configureLogger(options.debug_level, options.log_filename)
  disambigutions = loadDisambiguations(options.disambiguations_file)

  questions = None
  db = None
  if not options.stored_questions:
    db = loadDatabase(options.question_database)
    # Get all the questions.
    #
    questions = [q for q in db.questions(limit=options.limit, \
      restrict_to_dupes=options.restrict_to_dupes)]
    set_question_entities(questions)
    saveQuestions(questions)
  else:
    questions = loadQuestions(options.stored_questions)
  
  # Set limit = the number of questions for output display purposes
  # if there was no limit.
  #
  if options.limit is None or options.limit < 0:
    options.limit = len(questions)

  writeQuestionIds(questions)

  # Get the range of the questions.
  #
  questionRange = range(len(questions))

  # Build inverted index, labeled feature sets,
  # and reference clusters.
  #
  index = buildInvertedIndex(questions)
  namedEntityIndex = buildInvertedIndex(questions, useNamedEntities=True)
  labeledFeaturesets = make_featuresets(questions,index, \
    options, disambiguations=disambigutions)
  golden_clusters = cluster_by_label(labeledFeaturesets)

  guidGenerator = GuidGenerator()

  featureSets = [x[0] for x in labeledFeaturesets]
  clustererConstructor = CLUSTER_FUNCTIONS_BY_NAME[options.algorithm]
  featureComparer = FeatureComparer(options)

  informative_features = defaultdict(float)

  baseDistanceCache = {}

  def feature_distance(fr1,fr2):
    return featureComparer.compare(fr1,fr2)

  def report_current_accuracy(clusterer, threshold):
    experimental = clusterer.c2b.values()
    f1, precision, recall = pairwise_f1(questionRange, experimental, golden_clusters)
    print "%f,%f,%f,%f" % (threshold.total(), precision, recall, f1)

  if options.output_format == "MERGE-CSV":
    options.feature_distance_threshold = -1.0
    print "threshold,precision,recall,f1"

  if options.write_thresholds:
    report_feature_distances(questionRange, golden_clusters, labeledFeaturesets, feature_distance)
    exit()
  
  def ermethod(rs):
    clusterer = clustererConstructor(rs, featureSets,
      feature_distance, threshold=options.feature_distance_threshold,
      scoreType=ScoreTypes.SIMILARITY, baseDistanceCache=baseDistanceCache,
      guidGenerator=guidGenerator)
    if options.output_format == "MERGE-CSV":
      clusterer.onMerge = report_current_accuracy
    result = clusterer.cluster()
    feats = clusterer.informative_features
    for feat in feats:
      informative_features[feat] += feats[feat]
    return result

  clusters = None
  if options.blocking_method == "NONE":
    # Just run the ER algorithm on the entire range of questions.
    #
    clusters = ermethod([set([x]) for x in questionRange])
  elif options.blocking_method == "CANOPIES":
    t1 = 0.0
    t2 = 1.0 / len(questions)
    if options.tight_threshold == "INVERSESQRT":
      t2 = 1.0 / sqrt(len(questions))
    elif options.tight_threshold == "INVERSELOG":
      t2 = 1.0 / log(len(questions))

    neScoresHash = {}

    def cheapDistanceFunction(x,y):
      # Retrieve a hash for the distances from x to all other
      # points. Those points not in the hash are considered
      # infinitely distant.
      #
      if x not in neScoresHash:
        neScoresHash[x] = namedEntityIndex.scores(x)
      neScores = neScoresHash[x]
      # Look up similarity to y in the hash.
      # (return zero if it's not in there)
      #
      return neScores.get(y,0.0)
    
    canopiesBlocker = CanopiesBlocker(questionRange, \
      cheapDistanceFunction, ermethod, t1, t2, ScoreTypes.SIMILARITY)
    clusters = canopiesBlocker.cluster()
  else:
    assert options.blocking_method == "LEGO"
    # Set seed here for repeatable random runs.
    gen = MinHashGenerator(seed=options.random_seed)
    num_criteria = options.num_criteria
    criteria = []
    # Regardless of criteria argument, block once by category, although this
    # could result in some large-ish blocks.
    #
    criteria.append(lambda rs: block_by_category(rs, questions,
      featureSets, gen, options.category_mask))
    # Now block once for each randomly generated hash function.
    #
    for ii in xrange(num_criteria):
      criteria.append(lambda rs: block_by(rs, featureSets, gen, ii + 1, options.blocking_mask))

    legoBlocker = LegoBlocker(questionRange, criteria, ermethod)
    clusters = legoBlocker.cluster()
  assert(clusters is not None)
  report_accuracy(questionRange, clusters, golden_clusters, options)

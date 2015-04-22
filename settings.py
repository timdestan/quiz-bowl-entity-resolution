# Author : Tim Destan
#
# Code for configuring from user input
# Reads command line input, loads database, configures loggers.
# All configurable settings and defaults in the project are
# (intended to be) set in this file.

from optparse import OptionParser
import logging
logger = logging.getLogger('settings')
import json                         
from extract_db import QuestionDatabase
from cluster import *
import pickle
import os

# Names for clustering methods.
CLUSTER_FUNCTIONS_BY_NAME = { \
  "MINCLUSTER":MinDistanceAgglomerativeCluster, \
  "MEANCLUSTER":AverageDistanceAgglomerativeCluster, \
  "MAXCLUSTER":MaxDistanceAgglomerativeCluster }

ALGORITHMS = CLUSTER_FUNCTIONS_BY_NAME.keys()

# Names for available blocking methods.
BLOCKING_METHODS = ["LEGO","CANOPIES","NONE"]
OUTPUT_FORMATS = ["CSV","VERBOSE","MERGE-CSV","NONE"]

TIGHT_THRESHOLDS = ["INVERSE", "INVERSELOG", "INVERSESQRT"]

DEFAULT_QUESTION_DUMPSITE = 'Data/questions.pickle'

DEFAULT_QUESTION_ID_FILE = "Data/question-ids.csv"

def configureLogger(debug, log_filename):
  """
  Configures the basic logger.

  :param debug: Debugging level
  :param log_filename: Filename to log to, or None for console
  """
  levelsDict = {0: logging.ERROR, 1: logging.WARNING, 2: logging.INFO, 3:logging.DEBUG }
  log_level = levelsDict[debug]
  FORMAT = '%(name)s - %(levelname)s: %(message)s'
  if log_filename is None:
    logging.basicConfig(format=FORMAT, level=log_level)
  else:
    logging.basicConfig(format=FORMAT, filename=log_filename, level=log_level)

def getRelevantOptionNames():
  """
  Returns names of the options returned by getRelevantOptions
  """
  return ["Threshold","Limit"]

def getRelevantOptions(options):
  """
  Returns the options that are "relevant" to the output in a list.

  Note:
  Don't read too much into the relevance judgments. I basically just
  changed these whenever I wanted different columns in my output. Should
  make it configureable but NO TIME, and also not clear how the program
  could even tell automatically.
  """
  return [options.tight_threshold, options.limit]

def parseOptions():
  """
  Parse and return the command line options from the user.
  """
  usage = "usage: %prog [options] (--help for help)"
  opt_parser = OptionParser(usage)

  opt_parser.add_option("--debug-level", action="store",
    type='int', help="Debugging output level -- 0 = very little, 3 = lots of debugging output")
  opt_parser.add_option("--blocking-method", action="store",
    help="Method to use for blocking. Choices are: " + ", ".join(BLOCKING_METHODS))
  opt_parser.add_option("--question-database", action="store",
    help="File containing the question database (SQLite3 format)")
  opt_parser.add_option("--disambiguations-file", action="store",
    help="File containing hand-created disambiguations.")
  opt_parser.add_option("--log-filename", action="store",
    help="Name of a file for logging output (Logs to console if not set)")
  opt_parser.add_option("--limit", action="store",
    type='int', help="A limit for the number of clues to consider.")
  opt_parser.add_option("--output-format", action="store",
    help="Output format. Choices are: " + ", ".join(OUTPUT_FORMATS))
  opt_parser.add_option("--algorithm", action="store",
    help="Base clustering algorithm. Choices are: " + ", ".join(ALGORITHMS))
  opt_parser.add_option("--write-csv-column-names", action="store_true",
    help="Does no computation -- Just writes CSV column names to standard output.")
  opt_parser.add_option("--stored-questions", action="store",
    help="Path to serialized questions objects.")

  # This is by default now.
  #
  # opt_parser.add_option("--restrict-to-dupes", action="store_true",
  #   help="Set to restrict clues to those with duplicates.")
  opt_parser.add_option("--preserve-old-logs", action="store_true",
    help="Set to preserve log contents across multiple runs.")
  opt_parser.add_option("--write-thresholds", action="store_true",
    help="Set to write all possible distance thresholds and associated F1's.")
  
  # Feature representation weights.
  #
  opt_parser.add_option("--tf-idf-weight", action="store", type='float',
    help="Weight given to TF-IDF portion of distance function.")
  opt_parser.add_option("--category-weight", action="store", type='float',
    help="Weight given to category in distance function.")
  opt_parser.add_option("--referers-weight", action="store", type='float',
    help="Weight given to the phrases referring to the entity in distance function.")
  opt_parser.add_option("--named-entities-weight", action="store", type='float',
    help="Weight given to named entities in distance function.")
  opt_parser.add_option("--feature-distance-threshold", action="store",
    type='float', help="Feature distance threshold for feature based clusterer.")

  # Canopies only options
  #
  opt_parser.add_option("--tight-threshold", action="store",
    help="Tight threshold type for canopies blocker. Options are " + " ".join(TIGHT_THRESHOLDS))

  # LEGO - only options.
  #
  opt_parser.add_option("--num-criteria", action="store", type="int",
    help="Number of blocking criteria for Lego iterative blocker.")
  opt_parser.add_option("--random-seed", action="store", type="int",
    help="Random seed for min-hash generator.")
  opt_parser.add_option("--category-mask", action="store", type="int",
    help="Mask for the blocking by category.")
  opt_parser.add_option("--blocking-mask", action="store",type="int",
    help="Bitmask for blocking hashes")

  opt_parser.set_defaults(debug_level=2, log_filename=None,
    question_database="Data/questions.db",
    disambiguations_file="Data/disambiguations.data",
    blocking_method="NONE", limit=-1, feature_distance_threshold=2.0,
    output_format="VERBOSE", algorithm="MEANCLUSTER",
    write_csv_column_names=False, blocking_mask=0b111, category_mask = 0b11,
    stored_questions=None, restrict_to_dupes=True,
    preserve_old_logs=False, write_thresholds=False,
    tf_idf_weight=1.0, category_weight=0.0,
    referers_weight=1.0, named_entities_weight=1.0,
    num_criteria=3, random_seed=None,
    tight_threshold="INVERSE")

  options = None
  (options,_) = opt_parser.parse_args()

  options.blocking_method = options.blocking_method.upper()
  options.output_format = options.output_format.upper()
  options.algorithm = options.algorithm.upper()
  options.tight_threshold = options.tight_threshold.upper()

  # Validate that what they asked for made sense
  #
  if options.blocking_method not in BLOCKING_METHODS:
    print options.blocking_method, "is not a valid blocking method."
    print "Choices are ", ", ".join(BLOCKING_METHODS)
    exit()
  if options.output_format not in OUTPUT_FORMATS:
    print options.output_format, "is not a valid output format."
    print "Choices are ", ", ".join(OUTPUT_FORMATS)
    exit()
  if options.algorithm not in ALGORITHMS:
    print options.algorithm, "is not a valid algorithm."
    print "Choices are ", ", ".join(ALGORITHMS)
    exit()
  if options.tight_threshold not in TIGHT_THRESHOLDS:
    print options.tight_threshold, "is not a valid tight threshold type."
    print "Choices are ", ", ".join(TIGHT_THRESHOLDS)
    exit()


  if options.log_filename and not options.preserve_old_logs:
    exists = True
    try:
      os.stat(options.log_filename)
    except:
      # Probably doesn't exist.
      exists = False
    if exists:
      try:
        os.remove(options.log_filename)
      except OSError as err:
        print "Couldn't clear out", options.log_filename
  
  return options

def loadDisambiguations(filename):
  """ Loads disambiguations from a file"""
  logger.info("Loading disambiguations from file %s" % filename)
  disambiguations = {}
  try:
    with open(filename, "r") as f:
      for line in f.readlines():
        identifier, category = line.strip().split(",")
        identifier = int(identifier)
        disambiguations[identifier] = category
  except:
    logger.error("Could not read file %s" % filename) 
  return disambiguations

def loadQuestions(filename):
  """ Loads questions from a file"""
  logger.info("Loading questions from file %s" % filename)
  with open(filename,'r') as f:
    return pickle.load(f)

def saveQuestions(questions, filename=DEFAULT_QUESTION_DUMPSITE):
  """ Saves questions to a file """
  logger.info("Saving %d questions to file %s" % (len(questions), filename))
  with open(filename,'w+') as f:
    pickle.dump(questions, f)

def writeQuestionIds(questions, filename=DEFAULT_QUESTION_ID_FILE):
  """Write information about which ID is which question ID"""
  logger.info("Writing question IDs to file %s" % filename)
  with open(filename,'w+') as f:
    for ii in xrange(len(questions)):
      f.write(",".join([str(ii), str(questions[ii].id),
        str(questions[ii].label()), str(questions[ii].label_id())]))
      f.write("\n")

def readWikiDocs():
  """
  Read the wiki docs into an in-memory data structure.
  """
  FILENAME = 'wikidocs.json' 
  logger.info("Loading wiki docs from %s ...", FILENAME)
  with open(FILENAME, 'r') as f:
    return json.loads(f.read())

def loadDatabase(dbpath):
  """
  Loads the database into memory.

  :param dbpath: path to the question database
  """
  logger.info("Loading question database %s ...", dbpath)
  db = QuestionDatabase(dbpath)
  db.load_answers()
  return db

def defaultSetup():
  """
  Convenience method to call from console to set up everything with default
  options. Primarily a tool for easier debugging.

  :returns: The database
  """
  configureLogger(1, None)
  return loadDatabase("Data/questions.db")
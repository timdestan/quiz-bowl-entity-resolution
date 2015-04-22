# Author : Tim Destan
#
# Implementation of Lego blocking meta-algorithm

from qbcommon import expand_frequencies
from nltk.probability import FreqDist
from collections import defaultdict
import logging
logger = logging.getLogger("Lego")


def block_by_category(records, questions, featureSets, generator, mask):
  dictionary = defaultdict(set)
  for ii in records:
    dictionary[questions[ii].cat].add(ii)
  byCategory = dictionary.values()
  finals = []
  for subset in byCategory:
    finals.extend(block_by(subset, featureSets, generator, 0, mask))
  return finals

def block_by(records, featureSets, generator, hashNumber, mask=0b111):
  """
  Form a partitioning of the given record IDs into blocks, based on the provided
  generator and hash number.

  :param records: A list of indexes of records to block.
  :param featureSets: Feature representation for each record. Each record is an
    index into this list.
  :param generator: A generator of hash functions.
  :param hashNumber: An integer to specify which hash function we want from the
    generator. Still pseudo-random, but the generator always returns the same
    hash function for the same number.
  :param mask: A mask to apply so only a certain subset of the bits of the hash
    are taken into account when creating the blocks.

  :return: A partitioning of records.
  """
  dictionary = defaultdict(set)
  for ii in records:
    named_ents = expand_frequencies(featureSets[ii].named_entities)
    if len(named_ents) > 0:
      hsh = generator.minhash(named_ents, hashNumber, mask)
      key = hsh
      dictionary[key].add(ii)
    else:
      logger.warn("Clue %d has no named entities." % ii)
  #logger.debug("%i blocks generated." % len(dictionary.values()))
  return dictionary.values()

class BlockQueue(object):
  """
  Queue to hold the blocks to process for the Lego blocking algorithm.

  Used by LegoBlocker, not really intended for external use.
  """
  def __init__(self, initials=[]):
    """
    Constructor

    :param initials: initial blocks
    """
    self.hit_counts = defaultdict(int)
    self.base2affected = defaultdict(set)
    self.max_id = -1
    self.hash = {}
    for block in initials:
      self.enqueue(block)

  def _new_id(self):
    """
    Return a new ID for internal use
    """
    new_id = self.max_id + 1
    self.max_id = new_id
    return new_id

  def enqueue(self, block):
    """
    Insert a single block into the queue.
    
    :param block: A list of records (each of which is a set of base records)
    """
    # Produce new ID
    block_id = self._new_id()
    self.hash[block_id] = block
    self.hit_counts[block_id] = 0
    baserecs = set()
    for compositeRecord in block:
      baserecs = baserecs.union(compositeRecord)
    for baserec in baserecs:
      self.base2affected[baserec].add(block_id)

  def __len__(self):
    """
    The number of blocks waiting to be processed.
    """
    return len(self.hit_counts)
    
  def hit(self, baseRecords, originatingBlockId):
    """
    Process a hit for each base record provided.

    :param baseRecords: A list/set/iterable of base records.
    :param originatingBlockId: Block that caused this.
    """
    for baseRecord in baseRecords:
      for blockid in self.base2affected[baseRecord]:
        if blockid != originatingBlockId:
          if blockid not in self.hit_counts:
            logger.debug("Block %d brought back into consideration." % blockid)
          self.hit_counts[blockid] += 1

  def max_hits(self):
    """
    Return block id with most hits
    """
    if len(self) == 0:
      raise ValueError("Queue is empty.")
    max_v = -1
    max_k = None
    for (k,v) in self.hit_counts.iteritems():
      if (v > max_v):
        max_v = v
        max_k = k
    return max_k

  def dequeue(self):
    """
    Removes a block from the queue.
    """
    # Find block with most hits, reset its
    # hit count and return it.
    #
    block_id = self.max_hits()
    del self.hit_counts[block_id]
    return self.hash[block_id], block_id

class LegoBlocker(object):
  """
  Implementation of the Lego blocking algorithm, an iterative
  blocking algorithm
  """
  def __init__(self, records, criteria, ermethod):
    """
    Constructor

    :param records: All possible records to be compared
    :param criteria: A list of blocking criteria to determine blocks.
    :param ermethod: An ER algorithm to compare records within
      the blocks.
    """
    self.method = ermethod
    if not callable(self.method):
      raise ValueError("ermethod must be callable.")
    self.records = records
    self.criteria = criteria
    for criterion in self.criteria:
      if not callable(criterion):
        raise ValueError("%s criterion must be callable." % criterion)

    # Set up the tracker maximal values for each base record.
    self.maximals = {}
    for ii in self.records:
      self.maximals[ii] = set([ii])

  def get_maximal(self, record):
    """
    Gets maximal set for a record.
    """
    s = set()
    for base in record:
      s = s.union(self.maximals[base])
    return s

  def _merge(self,clusters):
    """
    Merge duplicates within clusters.
    """
    final = []
    for c1 in clusters:
      new = True
      for c2 in final:
        if c2 == c1:
          new = False
      if new:
        final.append(c1)
    return final

  def block(self):
    """
    Construct all the initial blocks, using all the provided
    blocking criteria.
    """
    for criterion in self.criteria:
      for blocking in criterion(self.records):
        yield [set([x]) for x in blocking]

  def cluster(self):
    """
    Runs the ER technique with blocking, producing a clustering
    of the input records.

    :returns: The clusters found by the algorithm (a list of sets of base records)
    """

    iteration = 1
    
    # Produce the initial set of blocks and add them all
    # to the queue.
    queue = BlockQueue(initials=self.block())

    # Loop until the queue is empty:
    while len(queue) > 0:
      block, block_id = queue.dequeue()

      logger.info("Starting iteration %d on block %d: Queue size is %d" %
        (iteration, block_id, len(queue)))
      
      # Update block to get any additional information
      # from other blocks via the maximal hash.
      block = self._merge(self.get_maximal(x) for x in block)
      # Updates the queue on the current state of this
      # block.
      #queue.update(block_id, block)
      
      # Call the ER method on this particular block.
      clustering = self.method(block)

      newlyAffectedRecords = set()

      # Look through each cluster in the clustering.
      for setOfBaseRecords in clustering:
        assert(isinstance(setOfBaseRecords,set))
        # Determine if any of this is new information.
        #
        for baseRecord in setOfBaseRecords:
          if self.maximals[baseRecord] != setOfBaseRecords:
            newlyAffectedRecords = newlyAffectedRecords.union(setOfBaseRecords)
            break
      
      # Hit the queue.
      queue.hit(newlyAffectedRecords, block_id)
      
      for setOfBaseRecords in clustering:
        # Update the maximal hash to point to this total set of
        # records for each base record.
        for baseRecord in setOfBaseRecords:
          self.maximals[baseRecord] = setOfBaseRecords

      iteration = iteration + 1

    # Done
    return self._makeClusters()

  def _makeClusters(self):
    """
    Finds all the unique values in maximal records and returns a list of them.
    This return value, a list of sets of base records, can be interpreted as
    the set of clusters found after a full run of cluster.

    :returns: The clusters found by the algorithm.
    """
    
    baseRecordsSeen = set()
    allClusters = []
    # For every possible base record:
    for baseRecord in self.maximals:
      # If we haven't seen a cluster with this guy in
      # it yet:
      if baseRecord not in baseRecordsSeen:
        # Get the maximal set of base records judged to
        # be equal to this base record.
        cluster = self.maximals[baseRecord]
        # Append it as a new cluster in our output array.
        allClusters.append(cluster)
        # Mark all base records from that cluster as seen,
        # so we don't include this same cluster again.
        baseRecordsSeen = baseRecordsSeen.union(cluster)

    # Return all the clusters.
    return allClusters
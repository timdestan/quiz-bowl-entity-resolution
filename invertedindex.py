# Author: Tim Destan
# Inverted Index Class

import math
from nltk.probability import ConditionalFreqDist, FreqDist
from nltk.corpus import stopwords
from collections import defaultdict
from qbcommon import expand_frequencies
import extract_db

import logging
logger = logging.getLogger("InvertedIndex")

stopwords_EN = set(stopwords.words('english'))
stopwords_EN = stopwords_EN.union(extract_db.QB_STOP)

def buildInvertedIndex(questions, useNamedEntities=False):
  """
  Builds an inverted index for the given questions.

  :param questions: A list of question objects.
  :returns: An inverted index using the question text as documents.
  """
  if useNamedEntities:
    logger.info("Building inverted index for named entities.")
  else:
    logger.info("Building inverted index for features.")
  index = InvertedIndex()
  i0 = 0
  for question in questions:
    doc = None
    if useNamedEntities:
      # Get named entities.
      #
      doc = expand_frequencies(question.named_entities)
    else:
      # Get features.
      #
      doc = [feat for (i1,feat) in question.features()]
    docId = index.addDocument(doc)
    assert(docId == i0)
    i0 += 1
  return index

class InvertedIndex(object):
  """
  A class for an inverted index that tracks both the frequency
  with which terms appear, and the frequency with which each term
  appears across all documents.
  """
  def __init__(self):
    """Constructor"""
    # The term frequencies are conditioned on the document ID.
    #
    self.termFrequencies = ConditionalFreqDist()

    # Hash structure to look up all the document IDs a term appears in.
    #
    self.termsToDocuments = defaultdict(set)
    self.num_docs = 0
    
    # Vocab mapping words to numbers
    #
    self.vocab = {}
    self.vocab_length = 0

    self._idf = None

  def _getTermId(self,term):
    """
    Get integer for given term
    :param term: A term
    :returns: An integer to stand in for the term.
    """
    if term not in self.vocab:
      # Add it if it wasn't already there.
      #
      self.vocab[term] = self.vocab_length
      self.vocab_length += 1
    return self.vocab[term]

  def filterTerm(self,term):
    """
    Filter whether to include term or not.

    Term is excluded if it's in the NLTK English stopwords or if
    it's a small word (less than three characters).

    :param term: A candidate term
    :return: True to include in the index, false to exclude
    """
    #return term.lower() not in stopwords_EN and len(term) > 3
    return True

  def _newDocumentId(self):
    """
    Returns a new document ID (also increments num_docs)
    """
    newId = self.num_docs
    self.num_docs += 1
    return newId

  def documentFrequency(self, term):
    """
    Return the number of documents the given term appears in.

    :param term: A term.
    :returns: The number of documents this term has been seen in.
    """
    termid = self._getTermId(term)
    return len(self.termsToDocuments[termid])

  def termFrequency(self, term, docId):
    """
    Find the frequency with which this term appeared in the document
    with the given ID.

    :param term: A term
    :param docId: A document ID
    :returns: The term frequency in this document.
    """
    termid = self._getTermId(term)
    return self.termFrequencies[docId][termid]

  def addDocument(self, document):
    """
    Adds a document to the index. The document is assumed to be
    a list or enumerable of terms (ascii or unicode text).

    :param document: A document to add.
    :returns: The ID used by this class to refer to the document.
      Save this for your records.
    """
    # Get a new document ID
    #
    docId = self._newDocumentId()
    # Make all terms in the document lowercase and remove stopwords.
    #
    document = [term.lower() for term in document if self.filterTerm(term)]
    doclen = len(document)
    for term in document:
      termid = self._getTermId(term)
      self.termFrequencies[docId].inc(termid, 1.0/doclen)
      self.termsToDocuments[termid].add(docId)
    # Return the ID to the caller.
    #
    return docId

  def _computeIdfs(self):
    """
    Compute the inverse document frequency for each term.
    """
    self._idf = defaultdict(float)
    for termid in self.vocab.itervalues():
      self._idf[termid] = math.log(self.num_docs / len(self.termsToDocuments[termid]))

  def inverseDocumentFrequency(self,term):
    """
    Gets inverse document frequency of the given term
    """
    if not self._idf:
      self._computeIdfs()
    termid = self._getTermId(term)
    return self._idf[termid]
    
  def scores(self, docId):
    """
    Return the score from the given document to every other
    document in the index. Documents not listed are assumed
    to have no similarity detected by shared terms.

    :param docId: ID of doc to compare other docs to.
    :returns: A list of tuples of (document ID, similarity score).
      Larger scores are better.
    """
    if not self._idf:
      self._computeIdfs()
    # Track the scores
    #
    docScores = FreqDist()
    for termid, freq in self.termFrequencies[docId].iteritems():
      # Find the frequency with which this term appears in other documents.
      #
      inverseDocumentFrequency = self._idf[termid]
      for otherDocId in self.termsToDocuments[termid]:
        if otherDocId == docId:
          # Skip this document
          continue
        # Find the term frequency of the term in the other document. 
        #
        otherFreq = self.termFrequencies[docId][termid]
        # Score proportional to product of frequencies times the inverse of
        # the document frequency.
        #
        docScores.inc(otherDocId, freq * otherFreq * inverseDocumentFrequency)

    return docScores

  def report(self):
    """
    Reports diagnostic information about self.
    """
    for term in self.vocab:
      print "Term %s appears in %d documents." % \
        (term, len(self.termsToDocuments[self.vocab[term]]))
    for docId in xrange(self.num_docs):
      print "Doc ID %d contains %d terms." % \
        (docId, len(self.termFrequencies[docId]))

# Author : Tim Destan
#
# This file contains basic unit tests for the
# Inverted index.

from invertedindex import *
import unittest

sent1 = ["colorless","green","ideas","sleep","furiously"]
sent2 = ["jolly","jolly","green","giant"]
sent3 = ["jolly","roger","himself"]
sent4 = ["drove","my","chevy","to","the","levee"]
sent5 = ["but","the","levee","was","dry"]

class InvertedIndexTests(unittest.TestCase):

  def create(self):
    """Create an index and document ids"""
    index = InvertedIndex()
    docids = []
    docids.append(index.addDocument(sent1))
    docids.append(index.addDocument(sent2))
    docids.append(index.addDocument(sent3))
    docids.append(index.addDocument(sent4))
    docids.append(index.addDocument(sent5))
    return index, docids

  def test_create(self):
    """Should be able to create an index"""
    index, docids = self.create()
    self.assertIsNotNone(index)

  def test_term_freq(self):
    """Should be able to retrieve term frequencies"""
    index, docids = self.create()
    self.assertAlmostEqual(1.0 / 5.0, index.termFrequency("green", docids[0]))
    self.assertAlmostEqual(2.0 / 4.0, index.termFrequency("jolly", docids[1]))

  def test_document_freq(self):
    """Should be able to get document frequencies"""
    index, docids = self.create()
    self.assertEquals(2, index.documentFrequency("jolly"))
    self.assertEquals(0, index.documentFrequency("brownstone"))
    self.assertEquals(1, index.documentFrequency("chevy"))
    self.assertEquals(2, index.documentFrequency("green"))

  def test_stopwords(self):
    """Should be ignoring obvious stopwords"""
    index,docids = self.create()
    self.assertEquals(0, index.termFrequency("the", docids[4]))
    self.assertEquals(0, index.documentFrequency("the"))
    self.assertEquals(0, index.termFrequency("himself", docids[2]))
    self.assertEquals(0, index.documentFrequency("himself"))

  def test_scoring(self):
    """ Scoring should work"""
    index,docids = self.create()
    docsAndScores = index.scores(docids[1])
    
    self.assertEquals(2, len(docsAndScores))
    
    self.assertTrue(docids[0] in docsAndScores.keys())
    self.assertTrue(docids[2] in docsAndScores.keys())

    # The third doc should have a better score than the first.
    self.assertGreater(docsAndScores[docids[2]], docsAndScores[docids[0]])

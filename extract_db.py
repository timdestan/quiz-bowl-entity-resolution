from collections import defaultdict
import re
import sqlite3
# from chunker import *
from nltk.tokenize import wordpunct_tokenize
import logging
logger = logging.getLogger("Extractor")

# Modified slightly from Jordan's original file. Now caches questions
# so we don't need to look them up from the database every time. Also
# slightly modified output messages to use logging module.

# TODO(jbg): This is a suboptimal regexp, but it works for now
YEAR_REGEXP = re.compile("[8-9][0-9]|2[0-9]{3}")
VALID_CHARS_REGEXP = re.compile("[a-z0-9]*")
FTP_REGEXP = re.compile("(f|F)or 10 points")


CENSORED_WORD = "OTHER"
START_SYMBOL = ""
BAD_CATEGORIES = set(["Unknown", "Non Selected", ""])

# Add additional regressors as thresholds
INDEX_POINTS = [30, 60, 90]

QB_STOP = ["name", "one", "points", "ftp", "10", "man", "another", "", "whose",
       "named", "include", "used", "ten", "called", "identify"]

class Answer:
  """
  An object giving the answer provided by a human (or a reference answer).
  """
  def __init__(self, user, text, position, correct):
    self.user = user
    self.text = text
    self.position = position
    self.correct = correct
    self.score = None

class AnswerLookup:
  """
  Maps from question ids to human and reference answers.
  """

  def __init__(self):
    self._reference = defaultdict(list)
    self._human = defaultdict(list)
    self._id = {}

  def add_answer(self, row):
    username, qid, date, text, correct, words, reference = row

    if reference == 1:
      self._reference[qid].append(text)
    if username != 'default':
      a = Answer(username, text, words, correct)
      self._human[qid].append(a)


  def add_id(self, row):
    qid, aid, text, count = row
    self._id[qid] = (aid, text)

  def __getitem__(self, qid):
    """
    Given a question ID, returns a tuple containing a list of the reference
    answers, human answers (Answer objects), and the canonical answer id
    """

    ref = []
    if qid in self._reference:
      ref = self._reference[qid]

    hum = []
    if qid in self._human:
      hum = self._human[qid]

    aid = [-1, ""]
    if qid in self._id:
      aid = self._id[qid]
    else:
      logger.warning("Answer ID %s missing" % qid)

    return ref, hum, aid

class Question:
  """
  Represents a single question.
  """

  def __init__(self, row, correct_answers, user_answers, label, label_id,
         reducer=None):
    self.id, self.text, self.cat, self.author, self.round, \
      self.tournament = row

    self.named_entities = []
    self.referers = []

    # Replace "For 10 points" with FTP
    self.text = FTP_REGEXP.sub("FTP", self.text)

    if reducer:
      self.cat = reducer(self.cat)

    self.answers = correct_answers

    self.responses = user_answers
    self.correct = [0, 0]
    for ii in self.responses:
      if ii.correct:
        self.correct[1] += 1
      else:
        self.correct[0] += 1

    self._label = label
    self._label_id = label_id

    self._ftp_pos = -1

    self.dev = False
    self.test = False

    self._features = []

  def __repr__(self):
    """
    Returns a string reprentation of this object.
    """
    dictionary = {"Question Text": self.text, "Answers": " ".join(self.answers), \
      "Referers": " ".join(self.referers), "Named entities": " ".join(self.named_entities) }
    return repr(dictionary)

  def label(self):
    return self._label

  def label_id(self):
    return self._label_id

  def _load_features(self, question_db):
    self._ftp_pos, self._features = question_db.load_features(self.id)

  def __len__(self):
    if not self._features:
      assert False, "Features must be loaded first"
    return len(self._features)

  def features(self, db=None, vocab=None):
    """
    An iterator over the features present in a question.
    """

    if not self._features:
      if not db:
        raise ValueError("Must provide a database if we haven't already loaded the features.")
      self._load_features(db)

    if vocab:
      yield 0, vocab[START_SYMBOL]
    else:
      yield 0, START_SYMBOL

    for index, feat in self._features:
      if vocab:
        if feat in vocab:
          yield index, vocab[feat]
      else:
        yield index, feat


def find_ftp(features):
  """
  Given a question, find where "ftp" occurs.  Assumes features have been preprocessed.
  """
  ftp_pos = -1
  for ii in xrange(len(features)):
    index, word = features[ii]
    if word == 'ftp':
      ftp_pos = index
  return ftp_pos


def category_reducer(category):
  """
  Creates a more compact set of categories.
  """
  if not "--" in category:
    if category in BAD_CATEGORIES:
      return "Unknown"
    return category

  main, sub = category.split("--")

  main = main.strip()
  if main in ["Science"]:
    return sub.strip()
  else:
    return main


class QuestionDatabase:

  def __init__(self, filename, train_count=4, dev_count=0, test_count=1,
         reduce_categories=True, cache_db=True):
    """

    @param filename: The source sqlite database
    @param train_count: reserves (at least) that many questions per answer as training data
    @param dev_count: reserves (exactly) that many questions for development data
    @param test_count: reserves (exactly) that many questions
    @param reduce_categories: Reduce categories or not
    @param cache_db: cache the Database in memory or not
    """
    self._conn = sqlite3.connect(filename)

    self._answer_count = None
    self._answers = None
    self._answers_loaded = False

    self._test_count = test_count
    self._dev_count = dev_count
    self._train_count = train_count
    self._reduce_categories = reduce_categories
    self._censored = set()
    self._vocab = {}
    self._questions_cache = {}

  def censored(self):
    """
    The set of words that are ignored (e.g. stopwords)
    """
    if not self._vocab:
      self.vocab()
    return self._censored

  def vocab(self):
    """
    Return the vocab dictionary
    """
    num_words = -1
    if not self._vocab:
      c = self._conn.cursor()
      c.execute('select feature, censored, word_id from vocab')

      d = {}
      for ww, cc, ii in c:
        d[ii] = ww
        d[ww] = ii
        if cc == 1:
          self._censored.add(ww)
        num_words = max(ii, num_words)

      logger.info("Loaded vocab with %i words; %i censored" % \
            (len(d) / 2, len(self._censored)))

      # Add the start symbol
      if not START_SYMBOL in d:
        d[START_SYMBOL] = num_words + 1
        d[num_words + 1] = START_SYMBOL

      logger.info("Retrieved %i words" % num_words)
      self._vocab = d

    return self._vocab

  def cursor(self):
    """
    Returns a cursor for the database.
    """
    return self._conn.cursor()

  def categories(self):
    c = self._conn.cursor()
    c.execute('select category from cat_backup group by (category)')

    cats = [x[0] for x in c]

    if self._reduce_categories:
      cats = [category_reducer(x) for x in cats]

    cats = list(set(cats))

    return cats

  def load_answers(self):
    if self._answers_loaded:
      logger.warn("Answers already loaded, skipping load_answers.")
      return
    c = self._conn.cursor()
    c.execute('select * from answers order by question_id')
    self._answers = AnswerLookup()

    for row in c:
      self._answers.add_answer(row)

    c.execute('select question_id, question_mapping.answer_id, ' +
          'answer_text, count from question_mapping join ' +
          'cannonical_answer on question_mapping.answer_id = ' +
          'cannonical_answer.answer_id')
    for row in c:
      self._answers.add_id(row)

    self._answers_loaded = True

  def answers(self):
    """
    Return all of the cannonical answers
    """
    assert self._answer_count
    for ii in self._answer_count:
      yield ii

  def load_features(self, id):
    c = self._conn.cursor()
    c.execute('select offset, feature from features ' +
          'where question_id = %i;' % id)

    features = [x for x in c]

    ftp_pos = find_ftp(features)

    return ftp_pos, features

  def questions(self, limit=-1, get_features=True, restrict_to_dupes=True):
    """
    If get_features is true, loads all features in addition to just returning
    questions.
    """
    if not self._answers_loaded:
      self.load_answers()

    if (limit, get_features, restrict_to_dupes) in self._questions_cache:
      # Found in cache, no need to hit database.
      cached = self._questions_cache[(limit, get_features, restrict_to_dupes)]
      for ii in cached:
        yield ii
    else:

      reducer = None
      if self._reduce_categories:
        reducer = category_reducer

      c = self._conn.cursor()

      acceptable_questions = set()

      min_count = self._dev_count + self._train_count + self._test_count
      self._answer_count = {}

      
      cmd = ('select questions.question_id, question_mapping.answer_id, ' +
              ' answer_text, count from questions join question_mapping on ' +
              'questions.question_id = question_mapping.question_id join ' +
              'cannonical_answer on cannonical_answer.answer_id = ' +
              'question_mapping.answer_id')
      if restrict_to_dupes:
        cmd += ' where count >= %s' % min_count
        cmd += ' order by count desc'

      c.execute(cmd)
      for ques, ans_id, ans_text, count in c:
        self._answer_count[ans_text] = 0
        acceptable_questions.add(ques)

        if limit > 0 and len(acceptable_questions) >= limit:
          break

      logger.debug("Found %d questions with %d answers with enough appearances (limit %d)" % \
        (len(acceptable_questions), len(self._answer_count), limit))

      c.execute('select * from questions')

      question_count = 0

      cache = {}

      questions = []

      for row in c:
        if not row[0] in acceptable_questions:
          continue

        question_count += 1

        ref, hum, label = self._answers[row[0]]

        label_id, label = label
        q = Question(row, ref, hum, label, label_id, reducer)

        q.train = False

        if restrict_to_dupes:
          if self._answer_count[label] < self._test_count:
            q.test = True
          elif self._answer_count[label] < self._dev_count + \
              self._test_count and \
              self._answer_count[label] >= self._test_count:
            assert not q.test, "Question %i already is test"
            q.dev = True
          else:
            q.train = True
            assert not (q.dev or q.test)
          self._answer_count[label] += 1

        if get_features:
          cache[q.id] = q
        else:
          questions.append(q)
          yield q

      if get_features:
        cache = self._batch_get_features(cache)

      for ii in cache:
        questions.append(cache[ii])
        yield cache[ii]

      self._questions_cache[(limit, get_features, restrict_to_dupes)] = questions

  def _batch_get_features(self, cache):
    """
    For a dictionary of question objects, return all of the features
    associated with those questions.
    """
    c = self._conn.cursor()
    c.execute('select * from features order by question_id, offset')
    questions_seen = set()

    last_id = -1
    for id, offset, feature in c:
      if id in cache:
        questions_seen.add(id)
        cache[id]._features.append((offset, feature))
        if id != last_id and last_id != -1:
          cache[last_id]._ftp_pos = \
            find_ftp(cache[last_id]._features)
          if cache[last_id]._ftp_pos < 0:
            pass #logger.debug(cache[last_id]._features)
          if len(questions_seen) == len(cache):
            break
        last_id = id
    return cache

if __name__ == "__main__":
  conn = sqlite3.connect('data/questions.db')
  cursor = conn.cursor()

  query = ('select questions.question_id, question_mapping.answer_id, body,' +
    ' answer_text, count from questions join question_mapping on ' +
    'questions.question_id = question_mapping.question_id join ' +
    'cannonical_answer on cannonical_answer.answer_id = ' +
    'question_mapping.answer_id where count >= 5 order by count desc, answer_text')

  cursor.execute(query)
  print ",".join(["question id", "answer id", "body", "answer text", "count"])
  for qid, aid, body, atext, count in cursor:
    body = body.replace('"','')
    body = '"' + body + '"'
    print ",".join([str(qid),str(aid),str(body),str(atext),str(count)])

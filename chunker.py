# Noun phrase chunker
# Author : Tim Destan

from nltk import pos_tag
from nltk.tokenize import wordpunct_tokenize
from nltk.chunk import RegexpParser, ne_chunk

from collections import defaultdict

import logging
logger = logging.getLogger("Chunker")

# Optional determiner or possessive, followed by
# optional adjectives and then one or more nouns.
#
simple_grammar = 'NP:{<DT|PP\$>?<JJ.*>*<NN.*>+}'
prep_phrase_grammar = 'NP:{<DT|PP\$>?<JJ.*>*<NN.*>+(<IN><DT|PP\$>?<JJ.*>*<NN.*>+)*}'

simple_chunker = RegexpParser(simple_grammar)
prep_phrase_chunker = RegexpParser(prep_phrase_grammar)

ENTITY_TYPES = ['PERSON','ORGANIZATION']

#NAME_THIS_REGEXP = re.compile("(N|n)ame this (\w+ [ \w+]*)")
#THIS_UNDERSCORE_REGEXP = re.compile("(t|T)his_(\w+)")

def set_question_entities(questions):
  logger.info("Finding referers and named entities for questions...")
  for clue in questions:
    clue.named_entities = get_named_entities(clue.text)
    clue.referers = set([extract_words(np) for np in get_np_chunks(clue.text) if np[0][0] == "this"])

def extract_words(np):
  """
  Gets the words out of the pairs of words and tags.
  """
  # Drop FTP acronym (For ten points)
  # Drop leading "this"
  #
  return " ".join(x[0] for x in np[1:] if x[0] != "FTP")

def get_np_chunks(sentence):
  """
  Get noun phrase chunks.
  """
  tokens = wordpunct_tokenize(sentence)
  posTaggedTokens = pos_tag(tokens)
  tree = simple_chunker.parse(posTaggedTokens)
  return [x.leaves() for x in tree.subtrees() if x.node == "NP"]

def dropFirst(enumerable):
  first = True
  for x in enumerable:
    if first:
      first = False
    else:
      yield x

def get_named_entities(sentence):
  """
  Get named entities from a sentence.
  """
  tokens = wordpunct_tokenize(sentence)
  posTaggedTokens = pos_tag(tokens)
  tree = ne_chunk(posTaggedTokens)
  subtrees = dropFirst(tree.subtrees())
  entities = defaultdict(int)
  for subtree in subtrees:
    # We could add the entity type here (e.g. PERSON, ORGANIZATION)
    # entity = subtree.node + " "
    #
    words = [word for (word,pos) in subtree if word != "FTP"]
    if len(words) > 0:
      entities[" ".join(words)] += 1
  return entities
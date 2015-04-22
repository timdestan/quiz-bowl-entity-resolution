# Author : Tim Destan
# Min hash functionality

import random
from datetime import datetime

#    Jenkins Hash implementation
#    Original copyright notice:
#    By Bob Jenkins, 1996.  bob_jenkins@burtleburtle.net.  You may use this
#    code any way you wish, private, educational, or commercial.  Its free.

def rot(x,k):
  return (((x)<<(k)) | ((x)>>(32-(k))))

def mix(a, b, c):
  a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
  a -= c; a &= 0xffffffff; a ^= rot(c,4);  a &= 0xffffffff; c += b; c &= 0xffffffff
  b -= a; b &= 0xffffffff; b ^= rot(a,6);  b &= 0xffffffff; a += c; a &= 0xffffffff
  c -= b; c &= 0xffffffff; c ^= rot(b,8);  c &= 0xffffffff; b += a; b &= 0xffffffff
  a -= c; a &= 0xffffffff; a ^= rot(c,16); a &= 0xffffffff; c += b; c &= 0xffffffff
  b -= a; b &= 0xffffffff; b ^= rot(a,19); b &= 0xffffffff; a += c; a &= 0xffffffff
  c -= b; c &= 0xffffffff; c ^= rot(b,4);  c &= 0xffffffff; b += a; b &= 0xffffffff
  return a, b, c

def final(a, b, c):
  a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
  c ^= b; c &= 0xffffffff; c -= rot(b,14); c &= 0xffffffff
  a ^= c; a &= 0xffffffff; a -= rot(c,11); a &= 0xffffffff
  b ^= a; b &= 0xffffffff; b -= rot(a,25); b &= 0xffffffff
  c ^= b; c &= 0xffffffff; c -= rot(b,16); c &= 0xffffffff
  a ^= c; a &= 0xffffffff; a -= rot(c,4);  a &= 0xffffffff
  b ^= a; b &= 0xffffffff; b -= rot(a,14); b &= 0xffffffff
  c ^= b; c &= 0xffffffff; c -= rot(b,24); c &= 0xffffffff
  return a, b, c

def hashlittle2(data, initval = 0, initval2 = 0):
  length = lenpos = len(data)

  a = b = c = (0xdeadbeef + (length) + initval)

  c += initval2; c &= 0xffffffff

  p = 0  # string offset
  while lenpos > 12:
    a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24)); a &= 0xffffffff
    b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); b &= 0xffffffff
    c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); c &= 0xffffffff
    a, b, c = mix(a, b, c)
    p += 12
    lenpos -= 12

  if lenpos == 12: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16) + (ord(data[p+11])<<24)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 11: c += (ord(data[p+8]) + (ord(data[p+9])<<8) + (ord(data[p+10])<<16)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 10: c += (ord(data[p+8]) + (ord(data[p+9])<<8)); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 9:  c += (ord(data[p+8])); b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 8:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16) + (ord(data[p+7])<<24)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 7:  b += (ord(data[p+4]) + (ord(data[p+5])<<8) + (ord(data[p+6])<<16)); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 6:  b += ((ord(data[p+5])<<8) + ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
  if lenpos == 5:  b += (ord(data[p+4])); a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24));
  if lenpos == 4:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16) + (ord(data[p+3])<<24))
  if lenpos == 3:  a += (ord(data[p+0]) + (ord(data[p+1])<<8) + (ord(data[p+2])<<16))
  if lenpos == 2:  a += (ord(data[p+0]) + (ord(data[p+1])<<8))
  if lenpos == 1:  a += ord(data[p+0])
  a &= 0xffffffff; b &= 0xffffffff; c &= 0xffffffff
  if lenpos == 0: return c, b

  a, b, c = final(a, b, c)

  return c, b

def hashlittle(data, initval=0):
  c, b = hashlittle2(data, initval, 0)
  return c


class MinHashGenerator(object):
  """
  Generates random-ish min-hash functions uniquely
  determined by the starting seed and the provided
  integer.
  """
  def __init__(self, seed = None):
    """ Constructor """
    self._memomask = {}
    self.reset(seed)

  def reset(self, seed = None):
    """
    Resets this generator using the provided seed.
    """
    if seed is None:
      self.seed_mask = hashlittle(str(datetime.now()))
    else:
      self.seed_mask = seed
    self._memomask.clear()

  def _hash_function(self, n):
    """
    Gets a hash function determined by the passed integer parameter.

    :param n: An integer to identify which hash you want.
    :returns: A hash function that can be used to hash strings. Will
      always return same function for same n.

    Based on idea posted by Alex Martelli on StackOverflow for
    generating a family of hash functions.
    """
    # Get the mask for this n, or make a new one of 32 random bits.
    mask = self._memomask.get(n)
    if mask is None:
      random.seed(n ^ self.seed_mask)
      mask = self._memomask[n] = int(random.getrandbits(32))
    # Now return a function that uses Jenkins Hash
    #
    def somehash(x):
      return hashlittle(x, mask)
    return somehash

  # def minhashes(self, s, iis):
  #   """
  #   Minhash for set s for each of the ii hash functions.
  #   """
  #   return [self.minhash(s,ii) for ii in iis]

  def minhash(self, s, ii, mask):
    """
    Minhash of a set s.

    :param s: A set of something
    :param ii: Which hash to use
    """
    fn = self._hash_function(ii)
    return min([fn(x) & mask for x in s])

# Author : Tim Destan
# This file loads and runs all the tests for the entire
# project.

import unittest

from main import configureLogger

# Import all the other tests.
from legotest import *
from canopiestest import *
from invertedindextest import *
from clustertest import *
from minhashtest import *

# Run all the tests.
if __name__ == "__main__":
  unittest.main()
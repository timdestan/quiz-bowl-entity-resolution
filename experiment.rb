#!/usr/bin/env ruby -wKU
# Author : Tim Destan

require 'fileutils'

DEFAULT_PICKLE = "Data\\questions.pickle"

def cart_prod(*args)
  final_output = [[]]
  until args.empty?
    t, final_output = final_output, []
    b, *args = args
    t.each { |a|
      b.each { |n|
        final_output << a + [n]
      }
    }
  end
  final_output
end

DEBUG_LEVEL = 0

DATA_FOLDER = "Data"
RESULTS_FOLDER = "Results"

CSV_FILE = "#{RESULTS_FOLDER}\\canopies.csv"
PROG_NAME = "python main.py"

#methods = %w{none lego canopies}

types = ["meancluster", "maxcluster", "mincluster"]
limits = [10,40,100,250,500]

#thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
threshs = %w{INVERSE INVERSESQRT INVERSELOG}

scores_threshold = 2.0

num_criteria = 5

all_bools = [false, true]
zero_one = [0.0, 1.0]

mask = 0b1111
catmask = 0b111
mthd = "canopies"

cmd = "#{PROG_NAME} --write-csv-column-names > #{CSV_FILE}"

system(cmd)

#limits.each do |lim|
cart_prod(limits, threshs).each do |lim, thresh|
  cmd = PROG_NAME
  #cmd += " --algorithm=#{type}"
  picklepath = File.join(DATA_FOLDER, "q#{lim}.pickle")
  cmd += " --limit=#{lim}"
  stored = File.exists?(picklepath)
  if stored
    cmd += " --stored-questions=#{picklepath}"
  end
  #cmd += " --feature-distance-threshold=#{thresh}"
  #cmd += " --num-criteria=#{num_criteria}"
  cmd += " --debug-level=#{DEBUG_LEVEL}"
  cmd += " --blocking-method=#{mthd}"
  #cmd += " --algorithm=#{type}"
  #cmd += " --blocking-mask=#{mask}"
  #cmd += " --category-mask=#{catmask}"
  cmd += " --tight-threshold=#{thresh}"
  cmd += " --output-format=csv"
  cmd += " >> #{CSV_FILE}"
  #total_time = 0.0
  # 4.times do
    $stderr.puts(cmd)
  #  before = Time.now
    system(cmd)
  #  after = Time.now
  #  total_time += (after - before)
  #end
  #total_time /= 4
  #puts "Average time for #{thresh} is #{total_time}"

  # This never works anyway.
  #
  if $!
    puts "Python exited with an error. Aborting."
    exit()
  end

  # Store the questions in a pickle if they weren't
  # already, so we can just load them from there next
  # time.
  #
  unless stored
    puts "Moving #{DEFAULT_PICKLE} to #{picklepath}"
    FileUtils.mv DEFAULT_PICKLE, picklepath, :force => true
  end
end
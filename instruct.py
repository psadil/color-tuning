
from main import Experiment
from psychopy import core

experiment = Experiment(no_demographics=True, task='instruct')
experiment.instruct()
core.quit()


from main import Experiment
from psychopy import core

if __name__ == "__main__":

    experiment = Experiment(no_demographics=True, task='instruct')
    experiment.instruct()
    core.quit()

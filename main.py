# -*- coding: utf-8 -*-

# TODO:
# - all four shapes '''
# - sql database (for defining trials)
# - consistent isi (need waiter, note: addTrialHandlerRecord blocks)
# - monitor configurations (for lab + hmrc)
# - demographics (how to get inside hdf5 file?)
# - make portable?
# - runinfo? anything really useful?

import argparse

from datetime import datetime
import git
# import numpy as np

from psychopy import core, visual, data, clock, monitors
# import psychopy.info
from psychopy.iohub import launchHubServer

example_usage = '''example:
  python main.py 
  python main.py -s 1 -r 1
'''

parser = argparse.ArgumentParser(epilog=example_usage, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-s", "--sub", help="Subject ID. defaults to 999", type=int, default=999)
parser.add_argument("-r", "--run", help="run ID. defaults to 999", type=int, default=999)
args = parser.parse_args()

mon = monitors.Monitor("default", distance=60.96)

# create a window to draw in
win = visual.Window(
    fullscr=True,
    allowGUI=False,
    winType='pyglet',
    blendMode='avg', 
    useFBO=True,
    units="deg",
    monitor=mon)

# runinfo = dict(psychopy.info.RunTimeInfo(
#         win=win,    
#         refreshTest=False,
#         verbose=True))
# # for serializing into hdf5
# runinfo = {key: (value.tolist() if isinstance(value, np.ndarray) else value) for key, value in runinfo.items()}

# create list of stimuli
stimList = []
for direction in range(0, 360, 90):
    stimList.append({
        'direction': direction,
        'fix_start': float('NaN'),
        'cue_start': float('NaN'),
        'dots_start': float('NaN'),
        'response_time': float('NaN'),
        'response_key': ''})

# organize them with the trial handler
trials = data.TrialHandler(
    stimList, 
    nReps=1)

# Start the ioHub process. 'io' can now be used during the
# experiment to access iohub devices and read iohub device events.
io = launchHubServer(
    experiment_code='color',
    datastore_name = 'data',
    experiment_info = {
        'version': str(git.repo.fun.rev_parse(git.Repo(), 'HEAD'))[0:6]
    },
    session_info = {
        'user_variables': {
            'date': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'sub': args.sub,
            'run': args.run}
    })

# Inform the ioHub server about the TrialHandler
io.createTrialHandlerRecordTable(trials)
keyboard = io.devices.keyboard


fix = visual.Circle(win=win, radius=0.1, size=1, fillColor="white")

triangle = visual.ShapeStim(win=win)

dots = visual.DotStim(
    win=win,
    fieldShape="circle",
    dotSize=3,
    dotLife=20,
    coherence=1,
    nDots=30,
    fieldSize=5,
    speed=0.01,
    noiseDots='direction')

waiter = clock.StaticPeriod(screenHz=60)

win.flip()
# run the experiment
for t, trial in enumerate(trials):  
    dots.dir = trial.direction
    
    # fixation
    fix.draw()
    trial['fix_start'] = win.flip()
    waiter.start(0.5)

    # cue
    triangle.draw()
    waiter.complete()
    trial['cue_start'] = win.flip()
    waiter.start(1)
        
    # 1 second, hard coded at 60hz refresh rate
    for flip in range(0, 60):
        dots.draw()

        if flip == 0: 
            waiter.complete()
            io.clearEvents()

        now = win.flip()
        io.sendMessageEvent(f'{now:.8f}', category = "flip")

        if flip == 0:
            trial['dots_start'] = now
            
        presses = keyboard.getPresses()
        if presses:
            trial['response_time'] = presses[0].time
            trial['response_key'] = presses[0].key
            break
    
    # At the end of each trial, before getting
    # the next trial handler row, send the trial
    # variable states to iohub so they can be stored for future
    # reference.
    # caution: this blocks until completion, messing with the ISI
    io.addTrialHandlerRecord(trial)


io.quit()
win.close()
core.quit()
 


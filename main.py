# TODO:
# - consistent isi (need waiter, note: addTrialHandlerRecord blocks)
# - monitor configurations (for lab + hmrc)
# - demographics (how to get inside hdf5 file?)
# - make portable?
# - add colors (true cielab requires info about monitor -- and info not specified in paper)
# - change display backed to pyglfw (to enable setting refresh rate)
# - implement eyetracking
# - gamma?

# notes to be careful about:
# To prevent learning of dot patterns, new stimuli were generated for each
# recording session. To rule out effects of stimulus variability on neuronal choice
# information, the same stimulus (dot pattern) was used for all trials per recording session.



import argparse
import pickle
import os
import math
import typing
from datetime import datetime

import numpy as np
import pandas as pd

import git

from psychopy import core, visual, data, clock, monitors
import psychopy.info
from psychopy.iohub import launchHubServer
from psychopy.tools import colorspacetools as cst

example_usage = '''example:
  python main.py 
  python main.py -s 1 -r 1
'''

parser = argparse.ArgumentParser(epilog=example_usage, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-s", "--sub", help="Subject ID. defaults to 0", type=int, default=0)
parser.add_argument("-r", "--run", help="run ID. defaults to 999", type=int, default=999)
args = parser.parse_args()


clut = pd.read_csv('stimuli/asus-clut.csv')
# r = psychopy.monitors.GammaCalculator(np.linspace(0,1, 1024), clut.to_numpy()[:,0], bitsIN=10, bitsOUT=10, eq=1)
# g = psychopy.monitors.GammaCalculator(np.linspace(0,1, 1024), clut.to_numpy()[:,1], bitsIN=10, bitsOUT=10, eq=1)
# b = psychopy.monitors.GammaCalculator(np.linspace(0,1, 1024), clut.to_numpy()[:,2], bitsIN=10, bitsOUT=10, eq=1)

# rgb2xyz = np.linalg.inv(pd.read_csv('stimuli/asus-rgb2xyz.csv').to_numpy())

mon = monitors.Monitor("default", distance=60.96)

linewidth = 3
radius = 0.75

# create a window to draw in
win = visual.Window(
    fullscr=True,
    allowGUI=False,
    winType='pyglet',
    blendMode='avg', 
    useFBO=True,
    units="deg",
    monitor=mon,
    gamma = [r.gamma, g.gamma, b.gamma],
    color='black')

win.setMouseVisible(False)

runinfo = dict(psychopy.info.RunTimeInfo(
        win=win,    
        refreshTest=False,
        verbose=True))
# with open(os.path.join('data-raw', f'sub-{args.sub}_run-{args.run}_info.pkl'), 'xb') as file:
#     pickle.dump(runinfo, file)columns

# create list of stimuli
d = pd.read_csv('stimuli/design.csv')

d_sub = (d.loc[d['sub']==0]
            .sort_values(by=['block','trial'])
            .assign(
                fix_start = float('NaN'),
                cue_start = float('NaN'),
                dots_start = float('NaN'),
                response_time = float('NaN'),
                response_key = '',
                a = lambda x: x.chroma * np.cos(np.radians(x.hue)),
                b = lambda x: x.chroma * np.sin(np.radians(x.hue)),
                rgb = lambda x: cst.cielab2rgb(
                    x.loc[:,['lightness','a','b']],
                    # whiteXYZ=[0.9642, 1.0, 0.8521],
                    # conversionMatrix=rgb2xyz, 
                    clip=True).tolist()))
d_sub['R'] = [x[0] for x in d_sub['rgb']]
d_sub['G'] = [x[1] for x in d_sub['rgb']]
d_sub['B'] = [x[2] for x in d_sub['rgb']]
d_sub = d_sub.drop('rgb', axis=1)

# organize them with the trial handler
trials = data.TrialHandler(
    [x for x in (d_sub.T.to_dict()).values()], 
    nReps=1,
    method='sequential') # randomization already done

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

# cues for color
triangle = visual.Polygon(win=win, radius=radius, lineColor="gray", lineWidth=linewidth)
circle = visual.Circle(win=win, radius=radius, lineColor="gray", lineWidth=linewidth)

# cues for direction
line1 = visual.Line(win=win, lineWidth=linewidth, start=(-math.sqrt(3)/2, math.sqrt(3)/2), 
                    end=(math.sqrt(3)/2, -math.sqrt(3)/2), lineColor="gray", size=radius)
line2 = visual.Line(win=win, lineWidth=linewidth, start=(-math.sqrt(3)/2, -math.sqrt(3)/2), 
                    end=(math.sqrt(3)/2, math.sqrt(3)/2), lineColor="gray", size=radius)

def make_vertices(angle: float, a: float = radius, b: float = radius/3) -> typing.Tuple[float, float]:
    theta = math.atan2(a*math.tan(angle), b)
    return (a*math.cos(theta), b*math.sin(theta))
n = 10
vertices = []
vertices.extend([make_vertices(angle) for angle in np.linspace(-math.pi/4, math.pi/4, num=n, endpoint=False)])
vertices.extend([make_vertices(angle, a=radius/3, b=radius) for angle in np.linspace(math.pi/4, math.pi/2, num=n//2, endpoint=False)])
vertices.extend([make_vertices(angle, a=radius/3, b=-radius) for angle in np.linspace(-math.pi/2, -math.pi/4, num=n//2, endpoint=False)])
vertices.extend([make_vertices(angle, a=-radius) for angle in np.linspace(-math.pi/4, math.pi/4, num=n)])
vertices.extend([make_vertices(angle, a=radius/3, b=-radius) for angle in np.linspace(math.pi/4, math.pi/2, num=n//2, endpoint=False)])
vertices.extend([make_vertices(angle, a=radius/3, b=radius) for angle in np.linspace(-math.pi/2, -math.pi/4, num=n//2, endpoint=False)])
fleur = visual.ShapeStim(win=win, size=radius, lineColor="gray", lineWidth=linewidth, vertices=vertices)

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
    dots.color = [trial.R, trial.G, trial.B]
    
    # fixation
    fix.draw()
    trial['fix_start'] = win.flip()
    waiter.start(0.5)

    # cue
    if trial.shape == 'triangle':
        triangle.draw()
    elif trial.shape == 'cross':
        line1.draw()
        line2.draw()
    elif trial.shape == 'circle':
        circle.draw()
    else: 
        fleur.draw()
        
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


# @atexit.register
# def exit() -> None:
io.quit()
win.close()
core.quit()

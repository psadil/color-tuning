# TODO:
# - monitor configurations (for lab + hmrc)
# - make portable?
# - add colors (true cielab requires info about monitor -- and info not specified in paper)
# - change display backed to pyglfw (to enable setting refresh rate)
# - implement eyetracking
# - gamma?
# - check that trial['dots_end'] and trial['fix_start'] are 1 refresh cycle apart
# - dots seem to be asymmetric?

# notes to be careful about:
# To prevent learning of dot patterns, new stimuli were generated for each
# recording session. To rule out effects of stimulus variability on neuronal choice
# information, the same stimulus (dot pattern) was used for all trials per recording session.

# also, pylink install is manual. that is, it's downloaded from sr-research site, unpacked
# and then put into psychopy/lib/python3.6/site-packages/pylink


import argparse
import pickle
import os
import math
from datetime import datetime
from typing import TextIO, Tuple, List

import numpy as np
import pandas as pd

import git

from psychopy import core, visual, data, clock, monitors
from psychopy.data.trial import TrialHandler
from psychopy.info import RunTimeInfo
from psychopy.iohub.client import ioHubConnection
from psychopy.iohub.client.connect import launchHubServer
from psychopy.tools import colorspacetools as cst
from psychopy.tools.monitorunittools import deg2pix
from psychopy.gui import Dlg
from dot import WrappedDot
# from psychopy.iohub.util import getCurrentDateTimeString


class Experiment(object):
    
    linewidth = 3
    radius = 0.75
    fix_radius = 0.1
    n_fleur_vertex = 10
    refresh_rate = 60
    cue_sec = 1
    dot_sec = 3
    n_flips_per_dots = dot_sec * refresh_rate
    isi_sec = 0.5
    dot_speed_deg_per_sec = 1.67

    def __init__(self, no_demographics = False, sub=0, run=999):

        if not no_demographics:
            demographics = self.solicit_demographics()

        iohub_config = {
          'eyetracker.hw.sr_research.eyelink.EyeTracker': {
            'name': 'tracker',
            'model_name': 'EYELINK 1000 DESKTOP',
            'enable_interface_without_connection': True,
            'runtime_settings': {
              'sampling_rate': 1000,
              'track_eyes': 'RIGHT'
              }
            },
            'experiment_code': 'color',
            'datastore_name': 'data',
            'experiment_info': {
              'version': str(git.repo.fun.rev_parse(git.Repo(), 'HEAD'))[0:6]
                },
            'session_info': {
            'user_variables': {
                'date': datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
                'sub': sub,
                'run': run,
                'sex': demographics[0],
                'ethnicity': demographics[1],
                'race': demographics[2],
                'age': demographics[3]}}}

        self.trials = os.path.join('stimuli','design.csv')
        self.io = iohub_config

        self.mon = monitors.Monitor("default", distance=60.96)

        # create a window to draw in
        self.win = visual.Window(
            fullscr=True,
            allowGUI=False,
            winType='pyglet',
            blendMode='avg', 
            useFBO=True,
            units="deg",
            monitor=self.mon,
            # gamma = [r.gamma, g.gamma, b.gamma],
            color='black')

        runinfo = RunTimeInfo(verbose=True, userProcsDetailed=True, win=self.win, refreshTest=True)
        with open(os.path.join('data-raw', f'sub-{sub}_run-{run}_runinfo.pkl'), 'xb') as f:
            pickle.dump(runinfo, f)

        self.fix = visual.Circle(win=self.win, radius=self.fix_radius, size=1, fillColor="white")
        # cues for color
        self.triangle = visual.Polygon(win=self.win, radius=self.radius, lineColor="gray", lineWidth=self.linewidth)
        self.circle = visual.Circle(win=self.win, radius=self.radius, lineColor="gray", lineWidth=self.linewidth)

        # cues for direction
        self.line1 = visual.Line(win=self.win, lineWidth=self.linewidth, start=(-math.sqrt(3)/2, math.sqrt(3)/2), 
            end=(math.sqrt(3)/2, -math.sqrt(3)/2), lineColor="gray", size=self.radius)
        self.line2 = visual.Line(win=self.win, lineWidth=self.linewidth, start=(-math.sqrt(3)/2, -math.sqrt(3)/2), 
            end=(math.sqrt(3)/2, math.sqrt(3)/2), lineColor="gray", size=self.radius)
        self.fleur = visual.ShapeStim(win=self.win, size=self.radius, lineColor="gray", lineWidth=self.linewidth, vertices=self.__make_vertices())

        self.dots = WrappedDot(
            win=self.win,
            units='deg',
            fieldShape="circle",
            dotSize=deg2pix(0.08, self.mon),
            dotLife=-1,
            coherence=1,
            nDots=400,
            fieldSize=3.2, # diameter
            speed=self.dot_speed_deg_per_sec / self.refresh_rate)

        self.waiter = clock.StaticPeriod(screenHz=self.refresh_rate)
    
                
    @property
    def trials(self) -> TrialHandler:
        return self.__trials


    @trials.setter
    def trials(self, design: TextIO):
        d = pd.read_csv(design)
                
        d_sub = (d.loc[d['sub']==0]
            .sort_values(by=['block','trial'])
            .assign(
                fix_start = float('NaN'),
                cue_start = float('NaN'),
                dots_start = float('NaN'),
                dots_end = float('NaN'),
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
        self.__trials = data.TrialHandler(
            [x for x in (d_sub.T.to_dict()).values()], 
            nReps=1,
            method='sequential') # randomization already done


    @property
    def io(self) -> ioHubConnection:
        return self.__io


    @io.setter
    def io(self, iohub_config: dict):
        # Start the ioHub process. 'io' can now be used during the
        # # experiment to access iohub devices and read iohub device events.
        io = launchHubServer(**iohub_config)

        # Inform the ioHub server about the TrialHandler
        io.createTrialHandlerRecordTable(self.trials)

        # run eyetracker calibration
        io.devices.tracker.runSetupProcedure()

        self.__io = io

    @staticmethod
    def solicit_demographics() -> Tuple[str, str, str, str]:

        dlg = Dlg(title="Demographics")
        dlg.addText('''The National Institute of Health requests basic demographic information (sex, ethnicity, race, and age)
        for clinical or behavioral studies, to the extent that this information is provided by research participants.
    
        You are under no obligation to provide this information. If you would rather not answer these questions, 
        you will still receive full compensation for your participation in this study and the data you provide will still be useful for our research.
        ''')
        dlg.addField('sex at birth:', choices=['Female', 'Male', 'Other', 'Rather not say'])
        dlg.addField('ethnicity:', choices= ['Hispanic or Latino', 'Not Hispanic or Latino', 'Rather not say'])
        dlg.addField('race:', choices= ['American Indian/Alaska Native', 'Asian', 'Black or African American', 'Native Hawaiian or Other Pacific Islander', 'White', 'Rather not say'])
        dlg.addField('age:', choices=[x for x in range(18, 51)] + ['Rather not say'])
        demographics = dlg.show()

        if dlg.OK == False: # user pressed cancel
            # fine to quit here, since nothing important has been opened
            core.quit()  

        return demographics
        

    @staticmethod
    def __make_vertex(angle: float, a: float = radius, b: float = radius/3) -> Tuple[float, float]:
        theta = math.atan2(a*math.tan(angle), b)
        return (a*math.cos(theta), b*math.sin(theta))


    def __make_vertices(self) -> List[float]:
        vertices = []
        vertices.extend([self.__make_vertex(angle) for angle in 
            np.linspace(-math.pi/4, math.pi/4, num=self.n_fleur_vertex, endpoint=False)])
        vertices.extend([self.__make_vertex(angle, a=self.radius/3, b=self.radius) for angle in 
            np.linspace(math.pi/4, math.pi/2, num=self.n_fleur_vertex//2, endpoint=False)])
        vertices.extend([self.__make_vertex(angle, a=self.radius/3, b=-self.radius) for angle in 
            np.linspace(-math.pi/2, -math.pi/4, num=self.n_fleur_vertex//2, endpoint=False)])
        vertices.extend([self.__make_vertex(angle, a=-self.radius) for angle in 
            np.linspace(-math.pi/4, math.pi/4, num=self.n_fleur_vertex)])
        vertices.extend([self.__make_vertex(angle, a=self.radius/3, b=-self.radius) for angle in 
            np.linspace(math.pi/4, math.pi/2, num=self.n_fleur_vertex//2, endpoint=False)])
        vertices.extend([self.__make_vertex(angle, a=self.radius/3, b=self.radius) for angle in 
            np.linspace(-math.pi/2, -math.pi/4, num=self.n_fleur_vertex//2, endpoint=False)])
        return vertices


    def __drawcue(self, shape) -> None:
        if shape == 'triangle':
            self.triangle.draw()
        elif shape == 'cross':
            self.line1.draw()
            self.line2.draw()
        elif shape == 'circle':
            self.circle.draw()
        else: 
            self.fleur.draw()


    def prep_dots(self, trial: dict) -> None:
        self.dots.dir = trial.direction
        self.dots.color = [trial.R, trial.G, trial.B]


    # run the experiment
    def run(self) -> None:
        self.win.setMouseVisible(False)

        self.io.devices.tracker.setRecordingState(True)
        self.win.flip()
        self.waiter.start(self.isi_sec)
        for t, trial in enumerate(self.trials):  
                        
            # fixation
            self.fix.draw()
            trial['fix_start'] = self.win.flip()
            self.io.devices.tracker.sendMessage(f'TRIALID {t}')
            self.io.devices.tracker.sendCommand('record_status_message', f'TRIAL {t}')
            self.prep_dots(trial)
            
            # cue
            self.__drawcue(trial.shape)
            self.fix.draw()
            self.waiter.complete()
            trial['cue_start'] = self.win.flip()
            self.waiter.start(self.cue_sec)

            # stim
            # 1 second, hard coded at 60hz refresh rate
            for flip in range(0, self.n_flips_per_dots):
                self.dots.draw()
                self.fix.draw()

                if flip == 0: 
                    self.waiter.complete()
                    self.io.clearEvents()
                
                now = self.win.flip()
                self.io.sendMessageEvent(f'trial-{t}_flip-{flip}', category="flip", sec_time=now)

                if flip == 0:
                    trial['dots_start'] = now
            
                presses = self.io.devices.keyboard.getPresses(keys=['left','right','escape'])
                if presses:
                    break                    
                                        
            # record trial results (if any) and prepare for next trial
            self.waiter.start(self.isi_sec)
            trial['dots_end'] = now
            if presses:                    
                trial['response_time'] = presses[0].time
                trial['response_key'] = presses[0].key

            # At the end of each trial, before getting
            # the next trial handler row, send the trial
            # variable states to iohub so they can be stored for future
            # reference.
            self.io.addTrialHandlerRecord(trial)

            # stop running if last press said to
            if presses and presses[0].key == 'escape':
                return


    def __del__(self):
        self.io.devices.tracker.setRecordingState(False)
        self.io.devices.tracker.setConnectionState(False)
        self.io.quit()
        self.win.close()
        

if __name__ == "__main__":
    example_usage = '''example:
    python main.py 
    python main.py -s 1 -r 1
    python main.py --no-demographics
    '''
    
    parser = argparse.ArgumentParser(epilog=example_usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--sub", help="Subject ID. defaults to 0", type=int, default=0)
    parser.add_argument("-r", "--run", help="run ID. defaults to 999", type=int, default=999)
    parser.add_argument("--no-demographics", help="don't ask for demographic information", action='store_true', default=False)
    args = parser.parse_args()

    experiment = Experiment(no_demographics=args.no_demographics, sub=args.sub, run=args.run)
    experiment.run()
    core.quit()

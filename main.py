# TODO:
# - monitor configurations (for lab + hmrc)
# - make portable?
# - add colors (true cielab requires info about monitor -- and info not specified in paper)
# - change display backed to pyglfw (to enable setting refresh rate)
# - gamma?
# - check that trial['dots_end'] and trial['fix_start'] are 1 refresh cycle apart
# - annex data
# - eyetracking

# notes to be careful about:
# - pylink install is manual. that is, it's downloaded from sr-research site, unpacked
#   and then put into psychopy/lib/python3.6/site-packages/pylink


import argparse
import pickle
import os
import math
from datetime import datetime
from typing import TextIO, Tuple, List, Optional
import sys
from platform import node

import numpy as np
import pandas as pd
import git

from psychopy import core, visual, data, clock, monitors
from psychopy.info import RunTimeInfo
from psychopy.iohub.client import ioHubConnection
from psychopy.iohub.client.connect import launchHubServer
from psychopy.tools import colorspacetools as cst
from psychopy.tools.monitorunittools import deg2pix
from psychopy.gui import Dlg
from psychopy.visual.text import TextStim

from dot import WrappedDot


class Experiment(object):
    
    linewidth = 3
    radius = 0.75
    fix_radius = 0.1
    n_fleur_vertex = 10
    refresh_rate = 60
    cue_sec = 1
    dot_sec = 3
    n_flips_per_dots = dot_sec * refresh_rate
    fix_sec = 0.5
    dot_speed_deg_per_sec = 1.67
    dotsize_deg = 0.08
    ndots = 400
    dotfield_diameter_deg = 3.2
    dot_coherence = 1
    feedback_sec = 0.5

    initial_pause_sec = 0.5

    def __init__(
        self, 
        no_demographics = False, 
        task = 'test'):        
        
        if task=='main':
            self.sub = self.solicit_subid()
            demographics = self.solicit_demographics(no_demographics)            
            iohub_config = {
                'experiment_code': 'color',
                'datastore_name': node(),
                'session_code': task,
                'experiment_info': {
                    'version': str(git.repo.fun.rev_parse(git.Repo(), 'HEAD'))[0:6]},
                'session_info': {
                'user_variables': {
                    'date': datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
                    'sub': self.sub,
                    'sex': demographics[0],
                    'ethnicity': demographics[1],
                    'race': demographics[2],
                    'age': demographics[3]}}}
        else:
            iohub_config = {}
            self.sub = 0

        self.trialdf = self.__prep_df(os.path.join('stimuli','design.csv'))

        self.io = iohub_config

        # Inform the ioHub server about the TrialHandler
        # randomization already done (hence 'sequential')
        self.io.createTrialHandlerRecordTable(data.TrialHandler(
            [x for x in (self.trialdf.T.to_dict()).values()], 
            nReps=1,
            method='sequential')) 

        self.mon = monitors.Monitor("default", distance=60.96)

        # create a window to draw in
        self.win = visual.Window(
            size=(1920, 1080),
            fullscr=True,
            allowGUI=False,
            winType='pyglet',
            blendMode='avg', 
            useFBO=True,
            units="deg",
            monitor=self.mon,
            # gamma = [r.gamma, g.gamma, b.gamma],
            color='black')

        if task == 'main':
            runinfo = RunTimeInfo(verbose=True, userProcsDetailed=True, win=self.win, refreshTest=True)
            with open(os.path.join('data-raw', f'sub-{self.sub}_task-{task}_runinfo.pkl'), 'xb') as f:pickle.dump(runinfo, f)

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
            dotSize=deg2pix(self.dotsize_deg, self.mon),
            dotLife=-1,
            coherence=self.dot_coherence,
            nDots=self.ndots,
            fieldSize=self.dotfield_diameter_deg,
            speed=self.dot_speed_deg_per_sec / self.refresh_rate)

        self.correct = TextStim(self.win, text = "CORRECT", color="green")
        self.incorrect = TextStim(self.win, text = "INCORRECT", color="red")
        self.welcome = TextStim(self.win, text=
        '''
        welcome to the experiment

        Press "c" to continue
        ''',
        wrapWidth=50,
        alignText="left")
        self.rest = TextStim(
            self.win,
            pos=(0, 6),
            alignText="left",
            wrapWidth=50)

        self.waiter = clock.StaticPeriod(screenHz=self.refresh_rate)

    
    @property
    def win(self) -> visual.Window:
        return self.__win

    
    @win.setter
    def win(self, win: visual.Window) -> None:
        self.__win = win

    
    @win.deleter
    def win(self) -> None:
        self.__win.close()
        del self.__win


    def __prep_df(self, design: TextIO) -> pd.DataFrame:
        d = pd.read_csv(design)
                
        d_sub = (d.loc[d['sub']==self.sub]
            .sort_values(by=['block','trial'])
            .assign(
                fix_start = float('NaN'),
                cue_start = float('NaN'),
                dots_start = float('NaN'),
                dots_end = float('NaN'),
                response_time = float('NaN'),
                feedback_start = float('NaN'),
                correct = None, 
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
        return d_sub.drop('rgb', axis=1)


    @property
    def trialdf(self) -> pd.DataFrame:
        return self.__trialdf


    @trialdf.setter
    def trialdf(self, df: pd.DataFrame) -> None:
        self.__trialdf = df


    @property
    def io(self) -> ioHubConnection:
        return self.__io


    @io.setter
    def io(self, iohub_config: dict) -> None:
        # Start the ioHub process. 'io' can now be used during the
        # # experiment to access iohub devices and read iohub device events.
        io = launchHubServer(**iohub_config)
        self.__io = io


    @io.deleter
    def io(self) -> None:
        self.__io.quit()
        del self.__io


    @staticmethod
    def solicit_demographics(no_demographics) -> Tuple[str, str, str, str]:

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
        if not no_demographics:
            demographics = dlg.show()
            if dlg.OK == False: # user pressed cancel
                # fine to quit here, since nothing important has been opened
                core.quit()  
        else:
            demographics = ['na', 'na', 'na', 'na']

        return demographics
        

    @staticmethod
    def solicit_subid() -> int:

        dlg = Dlg(title="Participant")
        dlg.addField('ID:', choices=[x for x in range(0, 31)])
        ID = dlg.show()        
        if dlg.OK == False: # user pressed cancel
            # fine to quit here, since nothing important has been opened
            core.quit()  

        return ID[0]

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


    def __prep_dots(self, direction: float, rgb: Tuple[float, float, float]) -> None:
        self.dots.dir = direction
        self.dots.color = rgb


    @property
    def presses(self) -> dict:
        return self.__presses

    
    @presses.setter
    def presses(self, presses: Optional[dict]) -> None:

        if presses and presses[0].key == 'escape':
            sys.exit()
        else:    
            self.__presses = presses
    

    # run the experiment
    def run(self) -> None:
        self.win.setMouseVisible(False)

        self.welcome.draw()
        self.win.flip()
        self.io.clearEvents()
        self.io.devices.keyboard.waitForPresses(keys=['c'])

        for block in self.trialdf.block.unique():
            self.rest.text = f'''
            you are about to start part {block+1} of {self.trialdf.block.max()+1} in the experiment                         

            remember:
            cross and flower shapes mean categorize direction
            triangle and circle mean categorize color

            when you are categorizing direction, press "left" for upwards and "right" for downwards
            when you are categorizing color, press "left" for redder and "right" for greener

            when you are ready to begin this part, press "c"
            '''
            self.rest.draw()
            self.win.flip()
            self.io.clearEvents()
            self.io.devices.keyboard.waitForPresses(keys=['c'])

            self.fix.draw()
            self.win.flip()
            self.waiter.start(self.initial_pause_sec)
            for __t in self.trialdf.query(f'block == {block}').itertuples():
                trial = __t._asdict()
                # fixation
                self.fix.draw()
                self.waiter.complete()
                trial['fix_start'] = self.win.flip()
                self.waiter.start(self.fix_sec)
                self.__prep_dots(trial['direction'], (trial['R'], trial['G'], trial['B']))
            
                # cue
                self.__drawcue(trial['shape'])
                self.fix.draw()
                self.waiter.complete()
                trial['cue_start'] = self.win.flip()
                self.waiter.start(self.cue_sec)

                # stim
                for flip in range(0, self.n_flips_per_dots):
                    self.draw_list([self.dots, self.fix])

                    if flip == 0: 
                        self.waiter.complete()
                        self.io.clearEvents()
                
                    now = self.win.flip()
                    self.io.sendMessageEvent(f'trial-{trial["trial"]}_flip-{flip}', category="flip", sec_time=now)

                    if flip == 0:
                        trial['dots_start'] = now
            
                    self.presses = self.io.devices.keyboard.getPresses(keys=['left','right','escape'])
                    if self.presses:
                        break                    
                                        
                # record trial results (if any) and prepare for next trial            
                trial['dots_end'] = now
                if self.presses:                    
                    trial['response_time'] = self.presses[0].time
                    trial['response_key'] = self.presses[0].key

                trial['correct'] = (
                    (trial['response_key'] == 'left' and 
                      ((trial['shape'] in ['triangle', 'circle'] and trial['hue'] <= 90) 
                      or (trial['shape'] in ['cross', 'fleur'] and trial['direction'] >= 0)))
                or (trial['response_key'] == 'right' and 
                    ((trial['shape'] in ['triangle', 'circle'] and trial['hue'] >= 90) 
                    or (trial['shape'] in ['cross', 'fleur'] and trial['direction'] <= 0))))
                if trial['correct']:
                    self.correct.draw()
                else:
                    self.incorrect.draw()

                trial['feedback_start'] = self.win.flip()
                self.waiter.start(self.feedback_sec)            
            
                # At the end of each trial, before getting
                # the next trial handler row, send the trial
                # variable states to iohub so they can be stored for future
                # reference.
                self.io.addTrialHandlerRecord(trial)
            
            if block == self.trialdf.block.max():
                msg = '''
                you have reached the end of the experiment!

                please go find the researcher and let them know you finished
                '''
            else:
                msg = f'''
                congrats! you have just finished that part
                the time is currently {datetime.now().strftime("%H:%M")}

                please take a brief break

                when you are ready to continue, press "c"
                '''

            self.rest.text = msg
            self.rest.draw()
            self.waiter.complete()
            self.win.flip()
            self.io.clearEvents()
            self.io.devices.keyboard.waitForPresses(keys=['c'])



    @staticmethod
    def draw_list(stims) -> None:
        for x in stims:
            x.draw()


    def instruct(self) -> None:
        self.win.setMouseVisible(False)

        text = visual.TextStim(
            win=self.win,
            text='''
            in this experiment you will see a bunch of colored dots move together
            you will be asked to categorize either the color or the direction of motion
            
            press "c" to continue
            ''',
            pos=(0, 6),
            alignText="left",
            wrapWidth = 50)

        text.draw()
        self.win.flip()
        self.io.clearEvents()
        self.io.devices.keyboard.waitForPresses(keys=['c'])

        text = visual.TextStim(
            win=self.win,
            text='''
            when you see these cues, categorize the motion
            when the dots are moving upwards, press "left"
            when the dots are moving downwards, press "right"
            
            press "c" to continue
            ''',
            pos=(0, 6),
            alignText="left",
            wrapWidth = 50)

        # motion cues
        self.line1.pos = (-1,0)
        self.line2.pos = (-1,0)
        self.fleur.pos = (1,0)
        self.dots.dir = 30
        self.dots.color = cst.cielch2rgb([90,15,120], clip=True)
        text.draw()
        self.__drawcue('cross')
        self.__drawcue('fluer')
        self.win.flip()        
        self.line1.pos = (0,0)
        self.line2.pos = (0,0)
        self.fleur.pos = (0,0)

        self.io.clearEvents()
        self.io.devices.keyboard.waitForPresses(keys=['c'])

        text.text = '''
        here, the dots are moving upwards
        so you want to press "left"
        '''

        self.io.clearEvents()
        while 1:
            self.draw_list([text, self.dots, self.fix])
            self.win.flip()    
            self.presses = self.io.devices.keyboard.getPresses(keys=['left','escape'])
            if self.presses:
                break

        # color cues
        text.text = '''
        when you see these cues, categorize the color
        when the dots are more red, press "left"
        when the dots are more green, press "right
            
        press "c" to continue"
        '''

        self.triangle.pos = (-1,0)
        self.circle.pos = (1,0)
        text.draw()
        self.__drawcue('triangle')
        self.__drawcue('circle')
        self.win.flip()
        self.io.clearEvents()
        self.triangle.pos = (0,0)
        self.circle.pos = (0,0)

        self.io.devices.keyboard.waitForPresses(keys=['c'])
        text.text = '''
        here, the dots are more green
        so you want to press "right"
        '''

        self.io.clearEvents()
        while 1:
            self.draw_list([text, self.dots, self.fix])
            self.win.flip()    
            self.presses = self.io.devices.keyboard.getPresses(keys=['right','escape'])
            if self.presses:
                break

        text.text = '''
        in summary: 
        cross and flower shapes mean categorize direction
        triangle and circle mean categorize color

        when you are categorizing direction, press "left" for upwards and "right" for downwards
        when you are categorizing color, press "left" for redder and "right" for greener

        in the actual experiment, everything will happen more quickly
            
        press "c" to continue to a regular trial
        '''

        text.draw()
        self.win.flip()
        self.io.clearEvents()
        self.io.devices.keyboard.waitForPresses(keys=['c'])

        # fixation
        self.fix.draw()
        self.win.flip()
        self.waiter.start(self.fix_sec)

        # cue
        self.draw_list([self.triangle, self.fix])
        self.waiter.complete()
        self.win.flip()
        self.waiter.start(self.cue_sec)

        # stim
        for flip in range(0, self.n_flips_per_dots):
            self.draw_list([self.dots, self.fix])

            if flip == 0: 
                self.waiter.complete()
                self.io.clearEvents()
                
            self.win.flip()
            self.presses = self.io.devices.keyboard.getPresses(keys=['right', 'escape'])
            if self.presses:
                break

    
        text.text = '''
        lastly, a white dot will be visible throughout the experiment

        when it is visible, please keep your eyes focused on that dot

        press 'c' to conclude the instructions
        '''

        self.io.clearEvents()
        self.draw_list([text, self.fix])
        self.win.flip()
        self.io.clearEvents()
        self.io.devices.keyboard.waitForPresses(keys=['c'])
            

if __name__ == "__main__":
    example_usage = '''example:
    python main.py 
    python main.py -t main
    python main.py --no-demographics
    '''
    
    parser = argparse.ArgumentParser(epilog=example_usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-t", "--task", help="task flag. one of 'test', 'instruct', 'main'", choices=['test', 'instruct', 'main'], default='main')
    parser.add_argument("--no-demographics", help="don't ask for demographic information", action='store_true', default=False)
    args = parser.parse_args()

    experiment = Experiment(no_demographics=args.no_demographics, task=args.task)
    experiment.run()
    core.quit()

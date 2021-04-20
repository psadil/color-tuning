import numpy as np
import pandas as pd

from psychopy import core, visual, data, clock, monitors
from psychopy.iohub.client.connect import launchHubServer
from psychopy.tools import colorspacetools as cst

def make_palette(luminance):
  ss = 2**8
  s = 2**7
  lab = luminance*np.ones([ss,ss,3], dtype=float)
  lab[:,:,1:] = np.transpose(np.mgrid[-s:s,-s:s], axes=(2,1,0))
  
  rgb = cst.cielab2rgb(lab, clip=True)
  palette = visual.ImageStim(win=win, image=rgb, units='pix', size=(ss, ss), ori=90)
  return palette

win = visual.Window(
            size=(1920, 1080),
            fullscr=True,
            allowGUI=False,
            winType='pyglet',
            blendMode='avg', 
            useFBO=True,
            units="deg",
            monitor=monitors.Monitor("default", distance=60.96),
            # gamma = [r.gamma, g.gamma, b.gamma],
            color='black')

# text = visual.TextStim(win=win)

io = launchHubServer()
lumas = np.linspace(80, 100, 8, dtype=float)

palletes = [make_palette(luminance=l) for l in lumas]

for pallete, x in zip(palletes, np.linspace(-800, 800, len(palletes))):
  pallete.pos = (x,0)
  pallete.draw()

win.flip()
io.clearEvents()
io.devices.keyboard.waitForPresses()
core.quit()

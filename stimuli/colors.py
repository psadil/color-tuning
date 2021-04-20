import numpy as np
import pandas as pd

from psychopy import core, visual, data, clock, monitors
# from psychopy.iohub.client.connect import launchHubServer
from psychopy.tools import colorspacetools as cst

def make_palette(luminance, chroma):
  size0 = 50
  size1 = 50
  lab = luminance*np.ones([size0,size1,3], dtype=float)
  hues = np.radians(np.linspace(0, 360, size1, endpoint=True))
  lab[:,:,1] = chroma*np.cos(hues)
  lab[:,:,2] = chroma*np.sin(hues)
  
  rgb = cst.cielab2rgb(lab, clip=True)
  palette = visual.ImageStim(win=win, image=rgb, units='pix', size=(size0, size1), ori=90)
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

# io = launchHubServer()
lumas = np.linspace(80, 100, 8, dtype=float)
chromas = np.linspace(0, 20, 8, dtype=float)

palletes = [[make_palette(luminance=l, chroma=c) for l in lumas] for c in chromas]

for c, x in zip(palletes, np.linspace(-400, 400, len(palletes))):
  for pallete, y in zip(c, np.linspace(-400, 400, len(c))):
    pallete.pos = (x,y)
    pallete.draw()

win.flip()

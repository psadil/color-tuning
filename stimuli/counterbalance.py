import os

from itertools import product
from random import sample

import pandas as pd

options = {
    'sub': range(0,2),
    'block': range(0,2),
    'repetition': range(0,2),
    'direction': [-90, -30, -5, 0, 5, 30, 90], 
    # 'hue': [-90, -30, -5, 0, 5, 30, 90],
    'hue': [0, 60, 85, 90, 95, 120, 180],
    'chroma': [100],
    'lightness': [100],
    'shape': ['fleur', 'circle', 'cross', 'triangle']}

# list of dictionaries. each element is a trial
d = pd.DataFrame({r: dict(zip(options.keys(),v)) for r, v in enumerate(product(*options.values()))}).T

d['trial'] = d.groupby(['sub','block'])['direction'].transform(lambda x: sample(range(0, len(x)), len(x)))

d.to_csv(os.path.join('stimuli', 'design.csv'), index_label=False)

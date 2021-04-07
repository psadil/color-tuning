import os

from itertools import product, repeat, chain
from random import sample, seed

seed(1234)

import pandas as pd

options = {
    'sub': range(0, 20),
    'repetition': range(0, 2),
    'direction': [-90, -30, -5, 0, 5, 30, 90],
    'hue': [0, 60, 85, 90, 95, 120, 180],
    'chroma': [100],
    'lightness': [100],
    'shape': ['fleur', 'circle', 'cross', 'triangle']}

d = pd.DataFrame({r: dict(zip(options.keys(),v)) for r, v in enumerate(product(*options.values()))}).T

d['observation'] = d.groupby(['sub'])['direction'].transform(lambda x: sample(range(0, len(x)), len(x)))
d = d.sort_values(by=['sub', 'observation'])

d['block'] = d.groupby(['sub', 'repetition'])['chroma'].transform(lambda x: list(chain.from_iterable(repeat(y, len(x)//4) for y in range(0, 4))))
d['block'] += ((1 + max(d.block.values)) * d.repetition)

d['trial'] = d.groupby(['sub', 'block'])['direction'].transform(lambda x: range(0, len(x)))

d = d.sort_values(by=['sub', 'repetition', 'block', 'trial'])

d.to_csv(os.path.join('stimuli', 'design.csv'), index=False, index_label=False)

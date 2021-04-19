# %%
import os
import git

from itertools import product, repeat, chain
from random import sample, seed

import pandas as pd
import numpy as np

seed(1234)


options = {
    'sub': range(0, 40),
    'repetition': range(0, 3),
    'direction': range(0,7),
    'hue': range(0,7),
    'chroma': [15],
    'lightness': [90],
    'shape': ['fleur', 'circle', 'cross', 'triangle']}

# %%
d = (
    pd.DataFrame({r: dict(zip(options.keys(),v)) for r, v in enumerate(product(*options.values()))})
    .T
    .assign(group = lambda x: np.where(x['sub'].mod(2), 'even', 'hard'))
    )

d['observation'] = d.groupby(['sub'])['direction'].transform(lambda x: sample(range(0, len(x)), len(x)))
d = d.sort_values(by=['sub', 'observation'])

d['block'] = d.groupby(['sub', 'repetition'])['chroma'].transform(lambda x: list(chain.from_iterable(repeat(y, len(x)//4) for y in range(0, 4))))
d['block'] += ((1 + max(d.block.values)) * d.repetition)

d['trial'] = d.groupby(['sub', 'block'])['direction'].transform(lambda x: range(0, len(x)))
d['direction'] = np.where(
    d.group=='even', 
    [[-90, -60, -30, 0, 30, 60, 90][x] for x in d.direction],
    [[-90, -30, -5, 0, 5, 30, 90][x] for x in d.direction])
d['hue'] = np.where(
    d.group=='even', 
    [[0, 30, 60, 90, 120, 150, 180][x] for x in d.hue],
    [[0, 60, 85, 90, 95, 120, 180][x] for x in d.hue])    

d = d.sort_values(by=['sub', 'repetition', 'block', 'trial'])


# %%
d.to_csv(
    os.path.join(
        git.Repo('.', search_parent_directories=True).working_tree_dir, 
        'stimuli', 
        'design.csv'), 
    index=False, index_label=False)


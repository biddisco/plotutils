import argparse
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import itertools
import os
import importlib
from IPython.display import Image, display, HTML
from PIL import Image
import glob

# -------------------------------------------------
def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

# -------------------------------------------------
if is_notebook():
    # this makes the notebook wider on a larger screen using %x of the display
    display(HTML("<style>.container { width:100% !important; }</style>"))
                 
# Tell pandas to display more columns without wrapping in dataframe output\n",
pd.set_option('display.max_rows',    30)
pd.set_option('display.max_columns', 30)
pd.set_option('display.width',       1000)

# -------------------------------------------------
# For debugging : print any object
def title_print(string, thing):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    print(thing)
    print('\n' + '-'*20)

# -------------------------------------------------
# For debugging print all data in a dataframe (warning: can be huge)
def title_print_all(string, thing):
    print('\n' + '-'*20, '\n' + string, '\n' + '-'*20)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
        print(thing)
    print('\n' + '-'*20)

# =================================================================
# Takes axes from subplot and makes a grid even when r==1 or c==1
# access grid using axes[r][c]
# =================================================================
def axes_to_row_col_grid(rows, cols, ax):
    axes = ax
    if rows==1:
        axes = [axes]
    if cols==1:
        axes = [[a] for a in axes]
    return axes

# =================================================================
# Global dataset management
# =================================================================
global_dataframe = pd.DataFrame()
global_datadict = {}
def add_to_global_data(data, dirname):
    global global_dataframe
    global global_datadict
    if dirname in global_datadict:
        print('Data previously loaded {} lines'.format(len(global_dataframe.index)))
    else:
        global_dataframe = pd.concat([global_dataframe, data], ignore_index=True, sort=False)
        global_datadict[dirname] = 1
        print('Total data loaded {} lines'.format(len(global_dataframe.index)))
    return global_dataframe

# =================================================================
# Miscellaneous list flattening including numpy arrays (graphs lists)
# =================================================================
def flatten(x):
    if isinstance(x, list) or isinstance(x, np.ndarray):
        return [a for i in x for a in flatten(i)]
    else:
        return [x]

# Read a CSV file and convert the known numeric columns to float types
def read_pandas_csv(filename):
    print('Reading', filename)
    data = pd.read_csv(filename, index_col=0)
    for col in ['futures', 'time', 'ftime', 'numa', 'threads']:
        data[col] = data[col].astype(float)
    return data

def load_csv_files_in_dir(dirname):
    data = pd.DataFrame()
    filenames = glob.glob(os.path.join(dirname, '*-*.csv'))
    for filename in filenames :
        data = pd.concat([data, read_pandas_csv(filename)], sort=False)
    add_to_all_data(data, dirname)
    
# =================================================================
# Holder for axis info for plot routine
# =================================================================
class axis(object):
    def __init__(self, label='No label', limits=None, 
                 scale='linear', base=10, 
                 format=lambda v,pos: str(int(v)), majloc=None, minloc=None,
                 fontsize=12):
        self.label    = label
        self.limits   = limits
        self.scale    = scale
        self.base     = base
        self.format   = format
        self.majloc   = majloc
        self.minloc   = minloc
        self.fontsize = fontsize

# =================================================================
# Plot combinations of series
# =================================================================
def plot_graph_series(data, Rows, Cols, select, plotvars, xparams, yparams, size=(8,4)):
    
    # select only the data wanted
    for series in select:
        #print('selecting', series, select[series])
        if isinstance(select[series], list):
            #print('We got a list', select[series])
            data = data[data[series].isin(select[series])]
        else:
            data = data[data[series] == select[series]]

    # decide how many rows, columns will be needed
    num_rows = 1
    num_cols = 1
    if len(Cols)>0:
        #print('columns', Cols)
        num_cols = 0
        for col in Cols:
            unique_col_entries = data[col].unique().tolist()
            num_cols = num_cols + len(unique_col_entries)
    if len(Rows)>0:
        #print('rows', Rows)
        num_rows = 0
        for row in Rows:
            unique_row_entries = data[row].unique().tolist()
            num_rows = num_rows + len(unique_row_entries)

    #print('Using Rows {}, Cols {}'.format(num_rows, num_cols))
    
    # break the wanted data into groups of series
    grouplist = []
    xvar = ''
    yvar = ''
    for entry in plotvars:
        if entry=='y':
            yvar = plotvars[entry]
            pass
        elif entry=='x':
            xvar = plotvars[entry]
            pass
        else:
            grouplist = plotvars[entry] + grouplist

    #print('x', xvar, 'y', yvar, 'Grouplist', grouplist)
    width  = np.clip(size[0]*num_cols, size[0], 20)
    height = size[1]*num_rows 
    fig, axes = plt.subplots(nrows = num_rows, ncols = num_cols, figsize=(width,height), dpi= 80, facecolor='w', edgecolor='k')    
    graph_rows_cols = axes_to_row_col_grid(num_rows, num_cols, axes)
    #print(num_rows, num_cols, graph_rows_cols)

    markers        = ('+', '.', 'o', '*', '^', 's', 'v', '<', '>', '8', 's', 'p', 'h', 'H', 'D', 'd', ',')
    filled_markers = ('o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd')
    majorLocator   = MultipleLocator(5)
    majorFormatter = FormatStrFormatter('%d')
    minorLocator   = MultipleLocator(1)
        
    grouplen = 1
    
    def plot_series_recursive(data, x, y, groups, prefix, ax1):
        head, tail = groups[0], groups[1:]
        #print('Grouping by', head)
        for g, grps in data.groupby(head):
            if len(tail)>0:
                #print('Recursing into ({}) {}'.format(tail, g))
                plot_series_recursive(grps, x, y, tail, g, ax1)
            else:
                #print('Processing into ({}) {}'.format(head, g))
                # average each series in case three are duplicates
                mean = grps.groupby([head, x]).mean().reset_index()
                
                temp = ax1.plot(mean[x], mean[y],
                    #marker=markers[l],
                    linestyle='-',
                    marker=next(localmarkers),
                    markersize=6,
                    label = str(prefix) + ',' + str(g) if prefix!='' else str(g)
                )
  
    # ------------------------------------------------
    for row in range(num_rows):
        rsubset = data
        if num_rows>1:
            #print('Selecting row using ', Rows[0], unique_row_entries[row])
            rsubset = data[data[Rows[0]]==unique_row_entries[row]]
        for col in range(num_cols):
            csubset = rsubset
            if num_cols>1:
                #print('Selecting column using ', Cols[0], unique_col_entries[col])
                csubset = rsubset[rsubset[Cols[0]]==unique_col_entries[col]]
            
            ax1 = graph_rows_cols[row][col]
            # restart markers and colours from beginning of list for each new graph
            localmarkers = itertools.cycle(markers)    
            plot_series_recursive(csubset, xvar, yvar, grouplist, '', ax1)

            # ------------------------------------------------
            if xparams.limits is not None:
                ax1.set_xlim(xparams.limits[0], xparams.limits[1])
            if xparams.scale is not None:
                ax1.set_xscale(xparams.scale, basex=xparams.base)
            if xparams.label is not None:
                ax1.set_xlabel(xparams.label, fontsize=xparams.fontsize)
            if xparams.format is not None:
                ax1.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(xparams.format))
            if xparams.majloc is not None:
                ax1.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(xparams.majloc))
            if xparams.minloc is not None:
                ax1.xaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(xparams.minloc))
            if (xparams.majloc is not None) and (xparams.minloc is not None):
                ax1.xaxis.set_ticks_position('both')
                
            # ------------------------------------------------
            if yparams.limits is not None:
                ax1.set_ylim(yparams.limits[0], yparams.limits[1])
            if yparams.scale is not None:
                ax1.set_yscale(yparams.scale, basey=yparams.base)
            if yparams.label is not None:
                ax1.set_ylabel(yparams.label, fontsize=yparams.fontsize)
            if yparams.format is not None:
                ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(yparams.format))
            if yparams.majloc is not None:
                ax1.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(yparams.majloc))
            if yparams.minloc is not None:
                ax1.yaxis.set_minor_locator(matplotlib.ticker.MultipleLocator(yparams.minloc))
            if (yparams.majloc is not None) and (yparams.minloc is not None):
                ax1.yaxis.set_ticks_position('both')
                
            ax1.legend(loc='best', ncol=1)    
    
    if len(Cols)>0:
        for txt, col in zip(unique_col_entries, range(len(unique_col_entries))):
            ax = graph_rows_cols[0][col] 
            ax.annotate(str(Cols[0]) + ' ' + str(txt), 
                        xy=(0.5, 1), xytext=(0, 10),
                        xycoords='axes fraction', textcoords='offset points',
                        size='large', ha='center', va='baseline')        
    if len(Rows)>0:
        for txt, row in zip(unique_row_entries, range(len(unique_row_entries))):
            ax = graph_rows_cols[row][0]
            ax.annotate(str(Rows[0]) + ' ' + str(txt), 
                xy=(0, 0.5), xytext=(-ax.yaxis.labelpad - 32, 0),
                xycoords=ax.yaxis.label, textcoords='offset points',
                size='large', ha='right', va='center')
    plt.tight_layout()
    return fig  
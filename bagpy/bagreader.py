#!/usr/bin/env python
# coding: utf-8

# Author : Rahul Bhadani
# Initial Date: March 2, 2020
# About: bagreader class to read  ros bagfile and extract relevant data
# License: MIT License

#   Permission is hereby granted, free of charge, to any person obtaining
#   a copy of this software and associated documentation files
#   (the "Software"), to deal in the Software without restriction, including
#   without limitation the rights to use, copy, modify, merge, publish,
#   distribute, sublicense, and/or sell copies of the Software, and to
#   permit persons to whom the Software is furnished to do so, subject
#   to the following conditions:

#   The above copyright notice and this permission notice shall be
#   included in all copies or substantial portions of the Software.

#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
#   ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
#   TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#   PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
#   SHALL THE AUTHORS, COPYRIGHT HOLDERS OR ARIZONA BOARD OF REGENTS
#   BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
#   AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#   OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = 'Rahul Bhadani'
__email__  = 'rahulbhadani@email.arizona.edu'
__version__ = "0.0.0" # this is set to actual version later


import sys
import ntpath
import os
import time
from io import BytesIO
import csv
import inspect

import rosbag
from std_msgs.msg import String, Header
from geometry_msgs.msg  import Twist, Pose, PoseStamped
from nav_msgs.msg import Path, Odometry
from geometry_msgs.msg import Point, Twist
from sensor_msgs.msg import LaserScan


import numpy  as np
import pandas as pd
from scipy.spatial.transform import Rotation
import plotly.graph_objects as go

from packaging import version

from pathlib import Path
version_src = ''

try:
    import importlib.resources as pkg_resources
    with pkg_resources.path('bagpy', 'version') as rsrc:
        version_src = rsrc
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    print("Python older than 3.7 detected. ")
    try:
        import importlib_resources as pkg_resources
        with pkg_resources.path('bagpy', 'version') as rsrc:
            version_src = rsrc
    except ImportError:
        print("importlib_resources not found. Install backported importlib_resources through `pip install importlib-resources`")

try:
    v = Path(version_src).open(encoding = "utf-8").read().splitlines()
except TypeError:
    v = Path(str(version_src)).open(encoding = "utf-8").read().splitlines()
__version__ = v[0].strip()

def timeout(func, args=(), timeout_duration=2, default=None, **kwargs):
    """This spwans a thread and runs the given function using the args, kwargs and
    return the given default value if the timeout_duration is exceeded
    """
    import threading

    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = default

        def run(self):
            try:
                self.result = func(*args, **kwargs)
            except:
                pass

    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    return it.result

def get_latest_bagpy_version():
    from subprocess import check_output, CalledProcessError

    try:  # needs to work offline as well
        result = check_output(["yolk", "-V", "bagpy"])
        return result.split()[1].decode("utf-8")
    except CalledProcessError:
        return "0.0.0"


def check_for_latest_version():

    latest_version = timeout(
        get_latest_bagpy_version, timeout_duration=5, default="0.0.0"
    )
    if version.parse(__version__) < version.parse(latest_version):
        import warnings
        warnings.warn("{}\n{}\n{}\n{}\n{}\n{}".format(
            "There is a newer version of bagpy available on PyPI:\n",
            "Your version: \t",
            __version__,
            "Latest version: \t",
            latest_version,
            "Consider updating it by using command pip install --upgrade bagpy"
        ))


check_for_latest_version()

class bagreader:
    '''
    `bagreader` class provides API to read rosbag files in an effective easy manner with significant hassle.
    This class is reimplementation of its MATLAB equivalent that can be found at https://github.com/jmscslgroup/ROSBagReader

    Parameters
    ----------------
    bagfile: `string`
        Bagreader constructor takes name of a bag file as an  argument. name of the bag file can be provided as the full qualified path, relative path or just the file name.

    verbose: `bool`
        If True, prints some relevant information. Default: `True`
    
    tmp: `bool`
        If True, creates directory in /tmp folder. Default: `False`

    Attributes
    --------------
    bagfile: `string`
        Full path of the bag  file, e.g `/home/ece446/2019-08-21-22-00-00.bag`
    
    reader: `rosbag.Bag`
        rosbag.Bag object that 

    topic: `pandas dataframe`
        stores the available topic from bag file being read as a table
    
    n_messages: `integer`
        stores the number of messages
    
    message_types:`list`, `string`
        stores all the available message types
    
    datafolder: `string`
        stores the path/folder where bag file is present - may be relative to the bag file or full-qualified path.

    topic_table: `pandas.DataFrame`
        A pandas DataFrame showing list of topics, their types, frequencies and message counts

        E.g. If bag file is at `/home/ece446/2019-08-21-22-00-00.bag`, then datafolder is `/home/ece446/2019-08-21-22-00-00/`

    message_dictionary: `dictionary`
        message_dictionary will be a python dictionary to keep track of what datafile have been generated mapped by types

    Example
    ---------
    >>> b = bagreader('2020-03-01-23-52-11.bag') 

    '''

    def __init__(self , bagfile , verbose=True , tmp = False):
        self.bagfile = bagfile

        self.reader = rosbag.Bag(self.bagfile)

        info = self.reader.get_type_and_topic_info() 
        self.topic_tuple = info.topics.values()
        self.topics = info.topics.keys()

        self.message_types = []
        for t1 in self.topic_tuple: self.message_types.append(t1.msg_type)

        self.n_messages = []
        for t1 in self.topic_tuple: self.n_messages.append(t1.message_count)

        self.frequency = []
        for t1 in self.topic_tuple: self.frequency.append(t1.frequency)

        self.topic_table = pd.DataFrame(list(zip(self.topics, self.message_types, self.n_messages, self.frequency)), columns=['Topics', 'Types', 'Message Count', 'Frequency'])

        self.start_time = self.reader.get_start_time()
        self.end_time = self.reader.get_end_time()

        self.datafolder = bagfile[0:-4]

        self.bag_df_dict = {}

        if tmp:
            self.datafolder = '/tmp/' + bagfile.split('/')[-1][0:-4]

        self.verbose = verbose

        if os.path.exists(self.datafolder):
            if self.verbose:
                print("[INFO]  Data folder {0} already exists. Not creating.".format(self.datafolder))
        else:
            try:
                os.mkdir(self.datafolder)
            except OSError:
                print("[ERROR] Failed to create the data folder {0}.".format(self.datafolder))
            else:
                if self.verbose:
                    print("[INFO]  Successfully created the data folder {0}.".format(self.datafolder))
 

    def message_by_topic(self, topic, tstart = None, tend = None):
        '''
        Class method `message_by_topic` to extract message from the ROS Bag by topic name `topic`

        Parameters
        ---------------
        topic: `str`
            
            Topic from which to extract messages.
        Returns
        ---------
        `dataframe`
            pandas dataframe

        Example
        -----------
        >>> b = bagreader('bagfile.bag') 
        >>> msg_file = b.message_by_topic(topic='/catvehicle/vel')

        '''

        if topic in self.bag_df_dict.keys():
            return self.bag_df_dict.get(topic)
          
        data = []
        for topic, msg, t in self.reader.read_messages(topics=topic, start_time=tstart, end_time=tend): 
            vals = []
            cols = []
            slots = msg.__slots__
            for s in slots:
                v, s = slotvalues(msg, s)
                if isinstance(v, tuple):
                    snew_array = [] 
                    p = list(range(0, len(v)))
                    snew_array = [s + "_" + str(pelem) for pelem in p]
                    s = snew_array

                if isinstance(s, list):
                    for i, s1 in enumerate(s):
                        vals.append(v[i])
                        cols.append(s1)
                else:
                    vals.append(v)
                    cols.append(s)
            data.append(vals)

        df = pd.DataFrame(data, columns=cols)
        self.bag_df_dict[topic] = df
        return df

    def get_same_type_of_topics(self, type_to_look=""):
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        
        for topic in topics_to_read:
            self.bag_df_dict[topic] = self.message_by_topic(topic)
            
        return {k: self.bag_df_dict[k] for k in topics_to_read}

    def plot(self, msg_dict, save_fig = False):
        '''
        `plot` plots the timseries given topic and its indexes
        
        Parameters
        -------------
        save_fig: `bool`

        If `True` figures are saved in the data directory.
        '''
        fig = go.Figure()
        marker_symbols = np.array(['circle', 'square', 'diamond', 'cross'])
        legend = []
        for topic_name in msg_dict:
            if topic_name not in self.bag_df_dict.keys():
                self.message_by_topic(topic_name)
            for i, msg_index in enumerate(msg_dict[topic_name]):
                legend.append(msg_index)
                np.roll(marker_symbols,1)
                fig.add_trace(go.Scatter(x = self.bag_df_dict[topic_name]['header.stamp.secs'], y = self.bag_df_dict[topic_name][msg_index], 
                                         mode = "lines+markers", name = str(topic_name+"/"+msg_index), line=dict(width=1), marker=dict(symbol=marker_symbols[0])))
        
        # Customize the layout (optional)
        title = ' '.join([str(elem) for elem in list(msg_dict.keys())])
        fig.update_layout(
            title=title,
            xaxis_title='Time',
            yaxis_title='Message',
        )
        if save_fig:
            fig.write_image("plot.pdf")

        fig.show()

    def animate_laser(self):
        raise NotImplementedError("To be implemented")



def slotvalues(m, slot):
    vals = getattr(m, slot)
    try:
        slots = vals.__slots__
        varray = []
        sarray = []
        for s in slots:
            vnew, snew = slotvalues(vals, s)       
            if isinstance(snew, list):
                for i, snn in enumerate(snew):
                    sarray.append(slot + '.' + snn)
                    varray.append(vnew[i])
            elif isinstance(snew, str):
                sarray.append(slot + '.' + snew)
                varray.append(vnew)    
                
        return varray, sarray
    except AttributeError:
        return vals, slot
        
def _get_func_name():
    return inspect.stack()[1][3]

def animate_timeseries(time, message, **kwargs):
    '''
    `animate_timeseries` will animate a time series data. Time and Message pandas series are expected
    
    
    Parameters
    ----------
    
    time: `pandas.core.series.Series`
        Time Vector in the form of Pandas Timeseries
        
    message: `pandas.core.series.Series`
        Message Vector in the form of Pandas Timeseries
        
    
    kwargs: variable keyword arguments
            
        title: `str`

            Title of the plot. By Default, it is `Timeseries Plot`
            
    '''
    
    
    import IPython 
    shell_type = IPython.get_ipython().__class__.__name__
    
    
    assert (len(time) == len(message)), ("Time and Message Vector must be of same length. Current Length of Time Vector: {0}, Current Length of Message Vector: {0}".format(len(time), len(message)))
    
    plot_title = 'Timeseries Plot'
    try:
        plot_title = kwargs["title"]
    except KeyError as e:
        pass

    fig, ax = create_fig(1)
    ax = ax[0]
    plt.style.use('ggplot')
    plt.rcParams['figure.figsize'] = [15, 10]
    plt.rcParams['font.size'] = 16.0
    plt.rcParams['legend.fontsize'] = 14.0
    plt.rcParams['xtick.labelsize'] = 14.0
    plt.rcParams['ytick.labelsize'] = 14.0
    plt.rcParams['legend.markerscale']  = 2.0

    if shell_type in ['ZMQInteractiveShell', 'TerminalInteractiveShell']:

        if shell_type == 'ZMQInteractiveShell':
            IPython.get_ipython().run_line_magic('matplotlib', 'inline')
        
        print('Warning: Animation is being executed in IPython/Jupyter Notebook. Animation may not be real-time.')
        l, = ax.plot([np.min(time),np.max(time)],[np.min(message),np.max(message)], alpha=0.6, 
                     marker='o', markersize=5, linewidth=0, markerfacecolor='#275E56')


        def animate(i):

            l.set_data(time[:i], message[:i])
            ax.set_xlabel('Time', fontsize=15)
            ax.set_ylabel('Message', fontsize=15)
            ax.set_title(plot_title, fontsize=16)

        for index in range(len(message)-1):
            animate(index)
            IPython.display.clear_output(wait=True)
            display(fig)
            plt.pause(time[index + 1] - time[index])

    else:
        for index in range(0, len(message)-1):
            ax.clear()
            if index < 500:
                sea.lineplot(time[:index], message[:index],  linewidth=2.0, color="#275E56")
            else:
                sea.lineplot(time[index - 500:index], message[index - 500:index],  linewidth=2.0, color="#275E56")
            ax.set_title(plot_title, fontsize=16)
            ax.set_xlabel('Time', fontsize=15)
            ax.set_ylabel('Message', fontsize=15)
            plt.draw()
            plt.pause(time[index + 1] - time[index])

def timeindex(df, inplace=False):
    '''
    Convert multi Dataframe of which on column must be 'Time'  to pandas-compatible timeseries where timestamp is used to replace indices

    Parameters
    --------------

    df: `pandas.DataFrame`
        A pandas dataframe with two columns with the column names "Time" and "Message"

    inplace: `bool`
        Modifies the actual dataframe, if true, otherwise doesn't.

    Returns
    -----------
    `pandas.DataFrame`
        Pandas compatible timeseries with a single column having column name "Message" where indices are timestamp in hum  an readable format.
    '''
    
    if inplace:
        newdf = df
    else:
        newdf =df.copy(deep = True)

    newdf['Time'] = df['Time']
    Time = pd.to_datetime(newdf['Time'], unit='s')
    newdf['Clock'] = pd.DatetimeIndex(Time)
    
    if inplace:
        newdf.set_index('Clock', inplace=inplace)
    else:
        newdf = newdf.set_index('Clock')
    return newdf

def _setplots(**kwargs):
    import IPython 
    
    shell_type = IPython.get_ipython().__class__.__name__

    ncols = 1
    nrows= 1
    if kwargs.get('ncols'):
        ncols = kwargs['ncols']

    if kwargs.get('nrows'):
        nrows = kwargs['nrows']

    if shell_type in ['ZMQInteractiveShell', 'TerminalInteractiveShell']:

        plt.style.use('default')
        plt.rcParams['figure.figsize'] = [12*ncols, 6*nrows]
        plt.rcParams['font.size'] = 22.0 + 3*(ncols-1)
        plt.rcParams["font.family"] = "serif"
        plt.rcParams["mathtext.fontset"] = "dejavuserif"
        plt.rcParams['figure.facecolor'] = '#ffffff'
        #plt.rcParams[ 'font.family'] = 'Roboto'
        #plt.rcParams['font.weight'] = 'bold'
        plt.rcParams['xtick.color'] = '#01071f'
        plt.rcParams['xtick.minor.visible'] = True
        plt.rcParams['ytick.minor.visible'] = True
        plt.rcParams['xtick.labelsize'] = 16 + 2*(ncols-1)
        plt.rcParams['ytick.labelsize'] = 16 + 2*(ncols-1)
        plt.rcParams['ytick.color'] = '#01071f'
        plt.rcParams['axes.labelcolor'] = '#000000'
        plt.rcParams['text.color'] = '#000000'
        plt.rcParams['axes.labelcolor'] = '#000000'
        plt.rcParams['grid.color'] = '#f0f1f5'
        plt.rcParams['axes.labelsize'] = 20+ 3*(ncols-1)
        plt.rcParams['axes.titlesize'] = 25+ 3*(ncols-1)
        #plt.rcParams['axes.labelweight'] = 'bold'
        #plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams["figure.titlesize"] = 30.0 + 4*(ncols-1) 
        #plt.rcParams["figure.titleweight"] = 'bold'

        plt.rcParams['legend.markerscale']  = 2.0
        plt.rcParams['legend.fontsize'] = 10.0 + 3*(ncols-1)
        plt.rcParams["legend.framealpha"] = 0.5
        
    else:
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = [18*ncols, 6*nrows]
        plt.rcParams["font.family"] = "serif"
        plt.rcParams["mathtext.fontset"] = "dejavuserif"
        plt.rcParams['font.size'] = 12.0
        plt.rcParams['figure.facecolor'] = '#ffffff'
        #plt.rcParams[ 'font.family'] = 'Roboto'
        #plt.rcParams['font.weight'] = 'bold'
        plt.rcParams['xtick.color'] = '#01071f'
        plt.rcParams['xtick.minor.visible'] = True
        plt.rcParams['ytick.minor.visible'] = True
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['ytick.color'] = '#01071f'
        plt.rcParams['axes.labelcolor'] = '#000000'
        plt.rcParams['text.color'] = '#000000'
        plt.rcParams['axes.labelcolor'] = '#000000'
        plt.rcParams['grid.color'] = '#f0f1f5'
        plt.rcParams['axes.labelsize'] = 10
        plt.rcParams['axes.titlesize'] = 10
        #plt.rcParams['axes.labelweight'] = 'bold'
        #plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams["figure.titlesize"] = 24.0
        #plt.rcParams["figure.titleweight"] = 'bold'
        plt.rcParams['legend.markerscale']  = 1.0
        plt.rcParams['legend.fontsize'] = 8.0
        plt.rcParams["legend.framealpha"] = 0.5
        

def create_fig(num_of_subplots=1, **kwargs):

    import IPython 
    shell_type = IPython.get_ipython().__class__.__name__


    nrows = num_of_subplots
    ncols = 1
    
    if kwargs.get('ncols'):
        ncols = kwargs['ncols']
    
    if kwargs.get('nrows'):
        nrows = kwargs['nrows']
    
    _setplots(ncols=ncols, nrows=nrows)
    fig, ax = plt.subplots(ncols=ncols, nrows=nrows)
    

    if nrows == 1 and ncols == 1:
        ax_ = []
        ax_.append(ax)
        ax = ax_
    else:
        ax = ax.ravel()

    if sys.hexversion >= 0x3000000:
        for a in ax:
            a.minorticks_on()
            a.grid(which='major', linestyle='-', linewidth='0.25', color='dimgray')
            a.grid(which='minor', linestyle=':', linewidth='0.25', color='dimgray')
            a.patch.set_facecolor('#fafafa')
            a.spines['bottom'].set_color('#161616')
            a.spines['top'].set_color('#161616')
            a.spines['right'].set_color('#161616')
            a.spines['left'].set_color('#161616')
    else:
        for a in ax:
            a.minorticks_on()
            a.grid(True, which='both')
            
    fig.tight_layout(pad=0.3*nrows)
    return fig, ax


def set_colorbar(fig, ax, im, label):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    axins1 = inset_axes(ax,
                width="50%",  # width = 50% of parent_bbox width
                height="3%",  # height : 5%
                loc='upper right')
    cbr = fig.colorbar(im, ax=ax, cax=axins1, orientation="horizontal")
    cbr.set_label(label, fontsize = 20)

    return cbr

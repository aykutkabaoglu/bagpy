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

__author__ = 'Rahul Bhadani, Aykut Kabaoglu'
__email__  = 'rahulbhadani@email.arizona.edu, aykutkabaoglu@gmail.com'
__version__ = "0.0.0" # this is set to actual version later


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

    Parameters
    ----------------
    bagfile: `string`
        Bagreader constructor takes name of a bag file as an  argument. name of the bag file can be provided as the full qualified path, relative path or just the file name.

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

    topic_table: `pandas.DataFrame`
        A pandas DataFrame showing list of topics, their types, frequencies and message counts

        E.g. If bag file is at `/home/ece446/2019-08-21-22-00-00.bag`, then datafolder is `/home/ece446/2019-08-21-22-00-00/`

    message_dictionary: `dictionary`
        message_dictionary will be a python dictionary to keep track of what datafile have been generated mapped by types

    Example
    ---------
    >>> b = bagreader('2020-03-01-23-52-11.bag') 

    '''

    def __init__(self , bagfile):
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

        self.bag_df_dict = {}

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
        time = []
        for topic, msg, t in self.reader.read_messages(topics=topic, start_time=tstart, end_time=tend): 
            vals = []
            cols = []
            # get precise time from header.stamp
            time.append(t.secs + t.nsecs*1e-9)
            # divide message into name index
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
        # convert seconds to human readable date and time
        df['Time'] = pd.to_datetime(time, unit='s')
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
                marker_symbols = np.roll(marker_symbols,1)
                fig.add_trace(go.Scatter(x = self.bag_df_dict[topic_name]['Time'], y = self.bag_df_dict[topic_name][msg_index], 
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

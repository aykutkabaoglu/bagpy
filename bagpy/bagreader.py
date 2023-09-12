#!/usr/bin/env python3
# coding: utf-8

# Author : Rahul Bhadani, Aykut Kabaoglu
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

import rosbag

import copy
import numpy  as np
import pandas as pd
from scipy.spatial.transform import Rotation
import plotly.graph_objects as go

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

class bagreader:
    '''
    `bagreader` class provides API to read rosbag files in an effective easy manner with significant hassle.

    Parameters
    ----------------
    bagfile: `string`
        Bagreader constructor takes name of a bag file as an  argument. name of the bag file can be provided as the full qualified path, relative path or just the file name.

    Attributes
    --------------    
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

    bag_df_dict: `dictionary`
        dictionary to keep dataframes of each topic by name. it only stores the requested topics

    Example
    ---------
    >>> b = bagreader('2020-03-01-23-52-11.bag') 

    '''

    def __init__(self , bagfile):

        self.reader = rosbag.Bag(bagfile)

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

        # store all read topics' dataframe in a dictionary
        self.bag_df_dict = {}
        self.app = dash.Dash(__name__)

    def is_topic_found(self, topic_name):
        '''
        returns whether the topic is found in bag file
        '''
        return bool(self.topic_table[self.topic_table['Topics'] == topic_name].index.array)

    def is_topic_type_valid(self, topic_name, topic_type):
        '''
        checks topic type is as desired
        '''
        return bool((self.topic_table[self.topic_table['Topics'] == topic_name].Types.array == topic_type)[0])

    def update_topic_dataframe(self, topic):
        '''
        Class method `update_topic_dataframe` to extract message from the ROS Bag by topic name `topic` and stores it in the class's dataframe
          It is intended to update the class attribute and is used a helper method like a private function
        Parameters
        ---------------
        topic: `str`
            Topic from which to extract messages.
        Returns
        ---------
        `bool`
            result of the update process' success
        '''
        # do not read same topics multiple time
        if topic in self.bag_df_dict.keys():
            return True
        if not self.is_topic_found(topic):
            print(topic, "is an invalid name, check topic_table")
            return False
          
        # get messages and update topic dataframe dictionary
        try:
            data = []
            time = []
            cols = []
            for topic, msg, t in self.reader.read_messages(topics=topic, start_time=None, end_time=None): 
                vals = []
                cols.clear() # to get the columns from the last iteration
                # get precise time from header.stamp
                time.append(t.secs + t.nsecs*1e-9)
                # divide message into name index
                slots = msg.__slots__
                for s in slots:
                    v, s = slotvalues(msg, s)
                    if isinstance(s, list):
                        for i, s1 in enumerate(s):
                            vals.append(v[i])
                            cols.append(s1)
                    else:
                        vals.append(v)
                        cols.append(s)
                data.append(vals)

            df = pd.DataFrame(data, columns=cols)
            # add roll, pitch, yaw columns to dataframe when quaternion message found
            df = self.quaternion_to_euler(df)
            # convert seconds to human readable date and time
            df['Time'] = pd.to_datetime(time, unit='s')
            # store newly generated dataframe
            self.bag_df_dict[topic] = df
            return True
        except:
            print("Couldn't get the message from bag file:", topic)
            return False

    def get_message_by_topic(self, topics):
        '''
        gets single topic name as a string or list of topic names and returns single dataframe or dataframe dictionary that it's keys are topic names
        '''
        if type(topics) is list:
            for topic in topics:
               if not self.update_topic_dataframe(topic):
                  return
            return {k: self.bag_df_dict[k] for k in topics}
        elif self.update_topic_dataframe(topics):
            return self.bag_df_dict[topics]

    def get_same_type_of_topics(self, type_to_look=""):
        '''
        collects the same type of topics and returns the list of topic names
        '''
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        
        return topics_to_read

    def quaternion_to_euler(self, df):
        '''
        convert quaternions to euler if there is a quaternion type message
        checks '.w' or 'w' pattern in the end of columns and adds 'Roll', 'Pitch', 'Yaw' columns to given dataframe
        '''
        quaternion_indices = ''
        for column in df.columns:
            if len(column) == 1 and column == 'w':
                quaternion_indices = column
                break
            elif '.w' == column[-2::]:
                quaternion_indices = column
                break
        if not quaternion_indices:
            return df

        orient_vec = [str(quaternion_indices[:-1]+'x'), str(quaternion_indices[:-1]+'y'), 
                      str(quaternion_indices[:-1]+'z'), str(quaternion_indices[:-1]+'w')]
        try:
            df['Roll'],df['Pitch'],df['Yaw'] = np.transpose(Rotation.from_quat(df[orient_vec]).as_euler("xyz",degrees=True))
        except:
            print("Quaternion transform error")
        return(df)

    def plot(self, msg_dict, save_fig = False):
        '''
        plots the timseries given topic and its indexes
        
        Parameters
        -------------
        save_fig: `bool`

        If `True` figures are saved in the data directory.
        '''
        fig = go.Figure()
        marker_symbols = np.array(['circle', 'square', 'diamond', 'cross'])
        legend = []
        for topic_name in msg_dict:
            if not self.update_topic_dataframe(topic_name):
                return
            for msg_index in msg_dict[topic_name]:
                legend.append(msg_index)
                marker_symbols = np.roll(marker_symbols,1)
                fig.add_trace(go.Scatter(x = self.bag_df_dict[topic_name]['Time'], y = self.bag_df_dict[topic_name][msg_index], 
                                         mode = "lines+markers", name = str(topic_name+"/"+msg_index), line=dict(width=1), marker=dict(symbol=marker_symbols[0])))
        
        # Customize the layout
        title = ' '.join([str(elem) for elem in list(msg_dict.keys())])
        fig.update_layout(
            title=title,
            xaxis_title='Time',
            yaxis_title='Message',
        )
        if save_fig:
            fig.write_image("plot.pdf")

        fig.show()

    def run_server(self):
        self.app.run_server(debug=False)
        
    def app_properties(self, fig, msg_size):
        '''
        layout properties of the dash
        '''
        self.app.layout = html.Div([
        dcc.Graph(id='scatter-plot', figure=fig),
        dcc.Slider(
              id='slider',
              min=1,
              max=msg_size,
              step=1,
              value=1,
              tooltip={"placement": "bottom", "always_visible": True},
              marks={i: str(i) for i in range(0, msg_size, msg_size//10)},
              updatemode='drag',
          )
        ])

    def plot_laserscan(self, laser_topic=''):
        '''
        plots the laserscan in polar coordinates as an interactive graph and the viewing message can be updated by slider
        
        Parameters
        ----------
        laser_topic: `str` (optional)
          topic name can be given otherwise it plots the first laserScan message in the topic_table if there is
        '''
        if laser_topic and (not self.update_topic_dataframe(topic=laser_topic) or not self.is_topic_type_valid(laser_topic, 'sensor_msgs/LaserScan')):
            return
        else:
            topic_list = self.get_same_type_of_topics("sensor_msgs/LaserScan")
            if topic_list:
                laser_topic = topic_list[0]
                self.update_topic_dataframe(topic=laser_topic)
            else:
                print("There is no LaserScan message")
                return
        
        fig = go.Figure()
        fig.update_polars(radialaxis_range=[0,self.bag_df_dict[laser_topic].range_max[0]])
        fig.layout['title'] = laser_topic

        self.app_properties(fig, len(self.bag_df_dict[laser_topic]))
      
        @self.app.callback(
        Output('scatter-plot', 'figure'),
        [Input('slider', 'value')],
        [State('scatter-plot', 'relayoutData')]
        )
        def update_figure(selected_value, relayout_data):
            '''
            slider callback: updates figure whenever slider is moved and keeps the zoom value
            '''
            row = self.bag_df_dict[laser_topic].loc[selected_value]
            new_figure = copy.deepcopy(fig) # to deal with the concurrent requests
            new_figure.data = []
            angles = np.arange(row.angle_min, row.angle_max, row.angle_increment)
            new_figure.add_trace(
                go.Scatterpolargl(
                    r = row.ranges,
                    theta = angles,
                    thetaunit = 'radians',
                    mode = "markers",
                    marker = dict(size=2),
                    name = 'Timestamp:' + str(row.Time),
                    showlegend = True
                ))
            if relayout_data and 'polar.radialaxis.range' in relayout_data:
                new_figure['layout.polar.radialaxis.range'] = relayout_data['polar.radialaxis.range']
            return new_figure
          
        update_figure(0, fig['layout'])
        self.run_server()

    def plot_pointcloud(self, pointcloud_topic=''):
        '''
        plots the pointcloud in cartesian coordinates as an interactive graph and the viewing message can be updated by slider
        
        Parameters
        ----------
        pointcloud_topic: `str` (optional)
          topic name can be given otherwise it plots the first pointcloud message in the topic_table if there is
        '''      
        if pointcloud_topic and (not self.update_topic_dataframe(topic=pointcloud_topic) or not self.is_topic_type_valid(pointcloud_topic, 'sensor_msgs/PointCloud')):
            return
        else:
            topic_list = self.get_same_type_of_topics("sensor_msgs/PointCloud")
            if topic_list:
                pointcloud_topic = topic_list[0]
                self.update_topic_dataframe(topic=pointcloud_topic)
            else:
                print("There is no PointCloud message")
                return
        
        # declare axis range before plotting the data. causes additional iteration but provides static and easy visualization
        min_x, min_y, min_z, max_x, max_y, max_z = 10000, 10000, 10000, 0, 0, 0
        for points in self.bag_df_dict[pointcloud_topic].points:
            x_values = [point.x for point in points]
            y_values = [point.y for point in points]
            z_values = [point.z for point in points]
            min_x, max_x = min(min(x_values), min_x), max(max(x_values), max_x)
            min_y, max_y = min(min(y_values), min_y), max(max(y_values), max_y)
            min_z, max_z = min(min(z_values), min_z), max(max(z_values), max_z)
            
        fig = go.Figure()
        fig.layout['title'] = pointcloud_topic
        
        self.app_properties(fig, len(self.bag_df_dict[pointcloud_topic]))
      
        @self.app.callback(
        Output('scatter-plot', 'figure'),
        Input('slider', 'value'),
        State('scatter-plot', 'relayoutData')
        )
        def update_figure(selected_value, relayout_data):
            '''
            slider callback: updates figure whenever slider is moved and keeps the zoom value
            '''
            row = self.bag_df_dict[pointcloud_topic].loc[selected_value]
            new_figure = copy.deepcopy(fig)
            new_figure.data = []
            new_figure.add_trace(
                go.Scatter3d(
                    x = [point.x for point in row.points],
                    y = [point.y for point in row.points],
                    z = [point.z for point in row.points],
                    mode = "markers",
                    marker = dict(size=2),
                    name = 'Timestamp:' + str(row.Time),
                    showlegend = True
                ))

            if relayout_data:
                new_figure['layout'] = relayout_data
                
            new_figure.update_layout(scene=dict(
                aspectmode='manual',
                aspectratio={'x':abs(max_x-min_x), 'y':abs(max_y-min_y), 'z':abs(max_z-min_z)},
                xaxis = dict(range=[min_x, max_x], ticks='outside', tickwidth=5, tickcolor='red'),
                yaxis = dict(range=[min_y, max_y], ticks='outside', tickwidth=5, tickcolor='green'),
                zaxis = dict(range=[min_z, max_z], ticks='outside', tickwidth=5, tickcolor='blue'),
            ))
                
            return new_figure
          
        update_figure(0, fig['layout'])
        self.run_server()
        
        
    def plot_diagnostics(self, topic_name="/diagnostics", name_filter=[], annotate_names=False):
        '''
        plots diagnostics messages according the their levels like OK, WARN, ERROR, STALE. it hovers the details of each message over the graph
        
        Parameters
        ----------
        topic_name: `str`
        name_filter: `list` (optional)
          list of strings that can be used to plot only the desired named messages. it acts as searching and don't have to be exact name
          if it is empty, plots all messages
        annotate_names: `bool`
          names can be viewed over the marker in addition to hover text. this is a time consuming process
        '''
        if topic_name and (not self.update_topic_dataframe(topic=topic_name) or not self.is_topic_type_valid(topic_name, 'diagnostic_msgs/DiagnosticArray')):
            return
        
        def keys_to_text(values):
            text_list = []
            for keys in values:
                text_list.append([f'{value}<br>' for value in keys])
            return text_list
        
        fig = go.Figure()
        fig.layout['title'] = topic_name
        
        # OK=0
        # WARN=1
        # ERROR=2
        # STALE=3
        levels = ['OK', 'WARN', 'ERROR', 'STALE']
        df_list = [pd.DataFrame(columns=['Time','name','message','hardware_id','values'])] * 4
        marker_symbols = np.array(['circle', 'square', 'diamond', 'cross'])
        
        for _, row in self.bag_df_dict[topic_name].iterrows():
            for state in row.status:
                if not name_filter or [name for name in name_filter if name in state.name]:
                    df_list[state.level] = df_list[state.level].append({'Time': row.Time, 'name': state.name, 'message': state.message, 'hardware_id': state.hardware_id, 'values': state.values}, ignore_index=True)

        for i in range(len(df_list)):
            hover_text = [
                f'{name}<br> {message}<br> {values}'
                for name, message, values in zip(df_list[i]['name'], df_list[i]['message'], keys_to_text(df_list[i]['values']))
            ]
            fig.add_trace(go.Scatter(x = df_list[i]['Time'], y = [-1*i]*len(df_list[i]), 
                                  mode = "lines+markers", name = levels[i], line = dict(width=1), marker = dict(symbol=marker_symbols[i]),
                                  hovertext = hover_text))

            # annotate name of the each message (it is resource consuming but go.Scatter do not provide better option)
            if annotate_names:
                for x_val, text in zip(df_list[i]['Time'], df_list[i]['name']):
                    fig.add_annotation(
                      go.layout.Annotation(
                          x=x_val,
                          y=-1*i,
                          text=text,
                          showarrow=False,
                          font=dict(size=10),
                          xref='x',
                          yref='y',
                          textangle=90,  # Rotate the text by 90 degrees
                      )
                    )

        # Customize the layout (optional)
        fig.update_layout(
            title='diagnostics',
            xaxis_title='Time',
            yaxis_title='Message',
        )
        fig.show()
        
        
    def plot_rosout(self, topic_name="/rosout", name_filter=[], annotate_names=False):
        '''
        plots rosout messages according the their levels like DEBUG, INFO, WARN, ERROR, FATAL. it hovers the details of each message over the graph
        
        Parameters
        ----------
        topic_name: `str`
        name_filter: `list` (optional)
          list of strings that can be used to plot only the desired named messages. it acts as searching and don't have to be exact name
          if it is empty, plots all messages
        annotate_names: `bool`
          names can be viewed over the marker in addition to hover text. this is a time consuming process
        '''
        import math
        
        if topic_name and (not self.update_topic_dataframe(topic=topic_name) or not self.is_topic_type_valid(topic_name, 'rosgraph_msgs/Log')):
            return

        fig = go.Figure()
        fig.layout['title'] = topic_name
        
        # DEBUG=1 #debug level
        # INFO=2  #general level
        # WARN=4  #warning level
        # ERROR=8 #error level
        # FATAL=16 #fatal/critical level
        levels = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL']
        df_list = [pd.DataFrame(columns=['Time','name','message'])] * 5
        marker_symbols = np.array(['circle', 'square', 'diamond', 'cross','x'])
        
        for _, row in self.bag_df_dict[topic_name].iterrows():
            if not name_filter or [name for name in name_filter if name in row['name']]:
                df_list[int(math.log2(row.level))] = df_list[int(math.log2(row.level))].append({'Time': row.Time, 'name': row['name'], 'message': row.msg}, ignore_index=True)

        for i in range(len(df_list)):
            hover_text = [
                f'{name}<br> {message}'
                for name, message in zip(df_list[i]['name'], df_list[i]['message'])
            ]
            fig.add_trace(go.Scatter(x = df_list[i]['Time'], y = [-1*i]*len(df_list[i]), 
                                  mode = "lines+markers", name = levels[i], line = dict(width=1), marker = dict(symbol=marker_symbols[i]),
                                  hovertext = hover_text))

            # annotate name of the each message (it is resource consuming but go.Scatter do not provide better option)
            if annotate_names:
                for x_val, text in zip(df_list[i]['Time'], df_list[i]['name']):
                    fig.add_annotation(
                      go.layout.Annotation(
                          x=x_val,
                          y=-1*i,
                          text=text,
                          showarrow=False,
                          font=dict(size=10),
                          xref='x',
                          yref='y',
                          textangle=90,  # Rotate the text by 90 degrees
                      )
                    )

        # Customize the layout (optional)
        fig.update_layout(
            title='rosout',
            xaxis_title='Time',
            yaxis_title='Message',
        )
        fig.show()

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

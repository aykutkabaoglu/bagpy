# Changes and New Features over Original Bagpy
- matplotlib changed with plotly
- bagreader does not read and write csv files over and over again. Instead, all requested topics for plotting are stored in pandas dataframes. It is faster and more efficient.
- Multiple topics including different types can be viewed together by passing a dictionary. Pass topic names as the dictionary's keys and values are the index array of each topic.
- All traces are shown as in the recorded date and time format
- Converts quaternion to Euler angles automatically in dataframes by adding new column names 'Roll', 'Pitch', 'Yaw', if there is some quaternion data inside the topic.
- sensor_msgs/LaserScan and sensor_msgs/pointCloud messages can be viewed interactively with slider callbacks. It is memory efficient and gets data from dataframes whenever the slider is dragged.
- /rosout and /diagnostics messages can be viewed according to their levels of operations.

# How to Use
```
from bagpy import bagreader

b = bagreader('../data/2016-06-01-14-57-13.bag')
```
Pass a dictionary to view the data. keys are the topic names and values are the list of strings. The strings must be full indexes of the topic. You can plot different type of topics together.
```
plot_dict = {
             "/catvehicle/cmd_vel": ["linear.x", "linear.y"],
             "/catvehicle/vel": ["linear.x", "linear.y"],
             "/catvehicle/distanceEstimator/angle": ["data"],
             }
b.plot(plot_dict)
```
"Roll", "Pitch", "Yaw" column labels are automatically created in the dataframe. You can plot them only by indexing their names.
```
plot_dict = {"/gps_odom": ["Roll", "Pitch", "Yaw"]}
b.plot(plot_dict)
```
plot_laserscan() and plot_pointcloud() functions use the dash app and data can be viewed by moving the slider. You can pass a topic name if there are multiple LaserScan or PointCloud messages. Otherwise, it plots the first proper topic in the topic_table
```
b.plot_laserscan()
```
/rosout and /diagnositcs messages also can be viewed as traces. The traces are drawn according to their severity. You can view the details of messages as hover text. There can be huge amounts of messages; therefore, you can optionally filter them out by passing name_filter list of text patterns. It filters according to the name of the messages. Additionally, you can view the names directly over the markers in the plot with the annotate_names parameters. All function arguments are optional.
```
b.plot_rosout('/rosout',name_filter=['mapping', 'searching_text'], annotate_names=True)
b.plot_diagnostics(name_filter=['searching_text'], annotate_names=False)
# b.plot_diagnostics()
```
Note 1: All plots are drawn according to the recorded ros::Time.
Note 2: Except sensor_msgs/LaserScan and sensor_msgs/TTPointCloud messages, array-type messages are not supported.

** Check the [notebook](https://github.com/aykutkabaoglu/bagpy/blob/master/notebook/Bagpy%20tutorial.ipynb) for more options.

------------------------------------------------------
# bagpy
__A Python package to facilitate the reading of a rosbag file based on semantic datatypes.__

__`bagpy`__ provides a wrapper class `bagreader` written in python that provides an easy to use interface for reading 
[bag files](http://wiki.ros.org/Bags) recorded by `rosbag record` command. This wrapper class uses ROS's python API `rosbag`
internally to perform all operations.

## Requirements
- Ubuntu 18.04 or later
- Python 3.6 or higher. **Now, the preferred version is Python 3.9**. With other versions, there are some dependency issues as how pip works has changed.
- Python 2.x support not available. Python 3.x virtual environment is recommended for pip installation.
- **Note: it is not compatible with ROS 2.**

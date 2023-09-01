"""Test bagreader functionality.

"""

__authors__ = "D. Knowles"
__date__ = "18 Aug 2022"

import os

import pytest
import pandas as pd

from bagpy import bagreader

@pytest.fixture(name="bag_path")
def fixture_bag_path():
    """Path to example bag file.

    Returns
    -------
    bag_path : string
        Path to example bag file.

    """
    root_path = os.path.dirname(
                os.path.dirname(
                os.path.realpath(__file__)))
    bag_path = os.path.join(root_path, 'data',
                             "2016-06-01-14-57-13.bag")

    return bag_path

@pytest.fixture(name="test_bag")
def read_test_bag(bag_path):
    """Read test bag file.

    Parameters
    ----------
    bag_path : string
        Path to example bag file.

    Returns
    -------
    test_bag : bagreader.bagreader
        bagreader instance for test bag.

    """
    test_bag = bagreader(bag_path)

    return test_bag

def test_topic_table(test_bag):
    """Test topic table.

    Parameters
    ----------
    test_bag : bagreader.bagreader
        bagreader instance for test bag.

    """

    assert isinstance(test_bag.topic_table,pd.DataFrame)
    assert test_bag.topic_table.shape == (17,4)

    # check some random values to make sure that it parsed ok
    assert test_bag.topic_table.loc[7,"Topics"] == "/catvehicle/vel"
    assert test_bag.topic_table.loc[13,"Types"] == "nav_msgs/Odometry"
    assert test_bag.topic_table.loc[11,"Message Count"] == 56
    assert test_bag.topic_table.loc[16,"Frequency"] == 73.37060490501347

def test_message_by_topic(test_bag):
    """Test message by topic.

    Parameters
    ----------
    test_bag : bagreader.bagreader
        bagreader instance for test bag.

    """

    catvehicle_msg = test_bag.message_by_topic("/catvehicle/vel")
    df_catvehicle = pd.read_csv(catvehicle_msg)

    assert df_catvehicle.shape == (1120,7)


def test_bagreader_attributes(test_bag):
    """Test bagreader attributes.

    Parameters
    ----------
    test_bag : bagreader.bagreader
        bagreader instance for test bag.

    """

    assert test_bag.bagfile.split("/")[-1] == "2016-06-01-14-57-13.bag"
    assert test_bag.start_time == 1464818234.3037877
    assert len(test_bag.frequency) == 17
    assert max(test_bag.frequency) == 1258.0395920815836
    assert min(test_bag.frequency) == 0.9992773989794005

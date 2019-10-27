#!/usr/bin/env python
# coding: utf-8

# In[5]:


# for OTF2
import sys
sys.path.append('/home/biddisco/apps/otf2/2.2/lib/python3.7/site-packages')
import otf2
import _otf2
from otf2.enums import Type
#
import time
import csv
import shutil
import argparse
from pprint import pprint
from IPython.display import display, HTML


# In[6]:


import inspect
import os.path
scriptname = inspect.getframeinfo(inspect.currentframe()).filename
scriptpath = os.path.dirname(os.path.abspath(scriptname))


# In[10]:


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
    
if is_notebook():
    # this makes the notebook wider on a larger screen using %x of the display
    display(HTML("<style>.container { width:100% !important; }</style>"))
    # save this notebook as a raw python file as well please
    get_ipython().system('jupyter nbconvert --to script csv2otf2.ipynb')


# In[8]:


#
# https://silc.zih.tu-dresden.de/otf2-2.1/python/examples.html
# Note : In OTF2 all timestamps are 64-Bit integers. As time.time() returns a float, a conversion is needed. 
#

TIMER_GRANULARITY = 1000000
def t():
    return int(round(time.time() * TIMER_GRANULARITY))

def csv_time(t):
    return t * TIMER_GRANULARITY


# In[9]:


colors = {
  "task_colors": {
    "HP Fact. Diag Block": "8800FF",
    "HP Update Panel": "0000FF",
    "HP Update Trailing Matrix": "FF0000",
    "HP Update Diag Trailing Matrix": "FF00FF"
  },
  "task_group_colors": {
    "Comm": "FFFF00",
    "Panel": "000088"
  }
}


# In[41]:


def get_group_name(rank):
    return "Rank {:03d}".format(rank)

def get_thread_name(rank, thread_id):
    if thread_id_en==-1:
        print("Error? thread id is -1")
        thread_name = "R{:03d}".format(rank) + ".Tsys"
    else:
        thread_name = "R{:03d}".format(rank) + ".T{:03d}".format(thread_id_en)
    return thread_name

def write_task(trace, attr, rank, taskname, taskgroup, thread_id_st, time_st, thread_id_en, time_en):
        
    global function_groups
    global task_map
    
    # Create a new event, or fetch existing one, with the given task name
    hpx_task = trace.definitions.region(taskname)

    if taskgroup in function_groups:
        pass
    else:
        #fg = trace.definitions.group(taskgroup, group_type=otf2.GroupType.REGIONS, members=trace.definitions.regions)
        function_groups.add(taskgroup)
        
    if taskgroup in task_map:
        task_map[taskgroup].add(hpx_task)
    else:
        task_map[taskgroup] = set()
        task_map[taskgroup].add(hpx_task)
         
    # thread Id - we use the thread that the task completes on, rather than starts
    # it might have been suspended and resumed elsewhere ...
    group_name = get_group_name(rank)
    thread_name = get_thread_name(rank, thread_id_st)            
    location = trace.definitions.location_group(thread_name, system_tree_parent=system_tree_node)
    writer = trace.event_writer(thread_name, group=location)
    try:
        writer.enter(int(time_st/1000), hpx_task, {attr: taskgroup})
        writer.leave(int(time_en/1000), hpx_task, {attr: taskgroup})
    except Exception as e:
        # try with different thread id
#         thread_name = get_thread_name(rank, thread_id_st)
#         location = trace.definitions.location_group(thread_name, system_tree_parent=system_tree_node)
#         writer = trace.event_writer(thread_name, group=location)
        
#         diff = time_en - time_st
#         print('Exception start', int(time_st/1000), 'end', int(time_en/1000))
#         newtime = int(time_st/1000 + (diff/10))
        print('Exception ', str(e), '\nadding task\n', rank, taskname, taskgroup, thread_id_st, time_st, thread_id_en, time_en)
#         writer.enter(int(newtime), hpx_task, {attr: taskgroup})
#         writer.enter(int(time_st/1000), hpx_task, {attr: taskgroup})
#         writer.leave(int(time_en/1000), hpx_task, {attr: taskgroup})
        


# In[95]:


parser = argparse.ArgumentParser(description='Insert the data of a csv profile in a nvprof profile')
parser.add_argument('--filename', help='name of the csv profile (input file)', nargs='+')
parser.add_argument('--output', '-o', help='The name of the nvprof profile to be created or modified (Default: filename with extension changed to ".nvprof")')

output_filename = None
if not is_notebook():
    args            = parser.parse_args()
    output_filename = args.output
    filename        = args.filename
    if args.filename == None:
        filename = "/home/biddisco/build/linear_algebra/profile_cholesky_0_1.csv /home/biddisco/build/linear_algebra/profile_cholesky_1_2.csv"
else:
    filename = ["/home/biddisco/build/linear_algebra/profile_cholesky_0_2.csv", "/home/biddisco/build/linear_algebra/profile_cholesky_1_2.csv"]
#    filename = ["/home/biddisco/build/hpx-debug/scheduler_test.csv"]
#    filename = "/home/biddisco/build/linalg_R/profile_cholesky_0_2.csv /home/biddisco/build/linalg_R/profile_cholesky_1_2.csv"
#    filename = "/home/biddisco/build/hpx-debug/profile_scheduler.csv"

rank_id = 0
color_filename = ""
combined = 0

if output_filename == None:
  i = filename[0].find('.')
  if i == -1:
    output_filename = filename[0]+ '.otf2'
  else:
    output_filename = filename[0][:i] + '.otf2'  

print("Filename :", filename)
print("Output   :", output_filename + "/trace.otf2")

try:
    shutil.rmtree(output_filename)
    print ("Deleted dir: %s" % (output_filename))
except OSError as e:
    print ("Did not delete dir: %s - %s." % (e.filename, e.strerror))

function_groups = set()
task_map = {}

# top level dir/folder that holds the otf2 files
with otf2.writer.open(output_filename, timer_resolution=TIMER_GRANULARITY) as trace:

    # root node 
    root_node = trace.definitions.system_tree_node("node")
    system_tree_node = trace.definitions.system_tree_node("myHost", parent=root_node)
    
    # why ???
    trace.definitions.system_tree_node_property(system_tree_node, "color", value="black")
    trace.definitions.system_tree_node_property(system_tree_node, "rack #", value=42)

    # location group, ??? what is it for
    loc_groups = []
    #location_group = trace.definitions.location_group("HPX_Group", system_tree_parent=system_tree_node)

    attr = trace.definitions.attribute("Function Group", "Grouping of tasks", Type.STRING)

    first_time = True
    # otf_writer, loc = create_trace(output_filename)

    first_timestamp = 0
    rank = 0
    for fname in filename:
        print("processing", fname)
        time_flag = True
        time_offset = 0
        with open(fname) as csvfile:
          tasks = csv.reader(csvfile, delimiter=',')
          for task in tasks:
            task_name    = task[0].strip()
            task_group   = task[1].strip()
            thread_id_st = int(task[2].strip())
            time_st      = int(task[3].strip())
            thread_id_en = int(task[4].strip())
            time_en      = int(task[5].strip())
            # make sure times are roughly aligned on each rank
            if first_timestamp == 0:
                first_timestamp = time_st
            if time_flag and first_timestamp<time_st:
                time_offset = time_st - first_timestamp
                print('Rank', rank, 'time shift set to', time_offset)
                time_flag = False            
            time_st = time_st - time_offset
            time_en = time_en - time_offset    
            
            #print(task_name, task_group, tid_st, time_st, tid_en, time_en)
            if thread_id_en is not None:
                write_task(trace, attr, rank, task_name, task_group, thread_id_st, time_st, thread_id_en, time_en)
        # assume filenames are in rank order
        rank = rank+1

    for group in task_map:
        pprint(task_map[group])
        function_group = trace.definitions.group(group, group_type=otf2.GroupType.REGIONS, members=task_map[group])


# In[49]:


if is_notebook:
    # you can create a Group definition with type 'OTF2_GROUP_TYPE_REGION' and fill the members array with the region IDs.
    #
    # no, you don't assign groups to events. You create a group of regions, and the regions are used in the events.

    try:
        shutil.rmtree("/home/biddisco/TestArchive")
    except OSError as e:
        pass

    with otf2.writer.open("/home/biddisco/TestArchive", timer_resolution=TIMER_GRANULARITY) as trace:

        function_group1 = trace.definitions.group("Comms", group_type=otf2.GroupType.REGIONS, members=trace.definitions.regions)
        function_group2 = trace.definitions.group("HP",    group_type=otf2.GroupType.REGIONS, members=trace.definitions.regions)
        function_group3 = trace.definitions.group("NP",    group_type=otf2.GroupType.REGIONS, members=trace.definitions.regions)

        fg1 = trace.definitions.groups.create("FG1", group_type=otf2.GroupType.REGIONS, members={temp_region1})

        temp_region1 = trace.definitions.region("Function 1")    
        temp_region2 = trace.definitions.region("Function 2")
        temp_region3 = trace.definitions.region("Function 3")
        temp_region4 = trace.definitions.region("Function 4")

        function_group2 = trace.definitions.group("Group2", group_type=otf2.GroupType.REGIONS, members=trace.definitions.regions)

        function = trace.definitions.region("My Function")

        parent_node = trace.definitions.system_tree_node("node")
        system_tree_node = trace.definitions.system_tree_node("myHost", parent=parent_node)

        trace.definitions.system_tree_node_property(system_tree_node, "color", value="black")
        trace.definitions.system_tree_node_property(system_tree_node, "rack #", value=42)

        location_group = trace.definitions.location_group("Master Process",
                                                       system_tree_parent=system_tree_node)

        attr = trace.definitions.attribute("StringTest", "A test attribute", Type.STRING)
        float_attr = trace.definitions.attribute("FloatTest", "Another test attribute",
                                              Type.DOUBLE)

        writer = trace.event_writer("Main Thread", group=location_group)

        # Write enter and leave event
        writer.enter(t(), temp_region1, {attr: "Hello World"})
        writer.leave(t(), temp_region1, attributes={float_attr: 42.0, attr: "Wurst?"})
        writer.enter(t(), temp_region2 )
        writer.leave(t(), temp_region2)

        # Get convenience metric object and write one metric event
        temperature = trace.definitions.metric("Time since last coffee", unit="min")
        writer.metric(t(), temperature, 72.0)

        # Get metric members
        temp_member = trace.definitions.metric_member("Temperature", "C", otf2.MetricType.OTHER,
                                                   otf2.MetricMode.ABSOLUTE_POINT)
        power_member = trace.definitions.metric_member("Power", "W")
        # Add metric members to the metric class object
        mclass = trace.definitions.metric_class([temp_member, power_member])
        # Add metric object to the location object
        writer.metric(t(), mclass, [42.0, 12345.6])


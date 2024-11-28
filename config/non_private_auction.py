# Our custom modules.
from Kernel import Kernel
from agent.non_private_auction.ClientAgent import ClientAgent as ClientAgent
from agent.non_private_auction.ServiceAgent import ServiceAgent as ServiceAgent
from model.LatencyModel import LatencyModel
from util import util
from util import param

# Standard modules.
from datetime import timedelta
import numpy as np
import pandas as pd
from sys import exit
from time import time

# Some config files require additional command line parameters to easily
# control agent or simulation hyperparameters during coarse parallelization.
import argparse

parser = argparse.ArgumentParser(description='Detailed options for DP darkpool config.')
parser.add_argument('-a', '--clear_learning', action='store_true',
                    help='Learning in the clear (vs SMP protocol)')
parser.add_argument('-c', '--config', required=True,
                    help='Name of config file to execute')
parser.add_argument('-i', '--num_iterations', type=int, default=5,
                    help='Number of iterations for the secure multiparty protocol)')
parser.add_argument('-k', '--skip_log', action='store_true',
                    help='Skip writing agent logs to disk')
parser.add_argument('-l', '--log_dir', default=None,
                    help='Log directory name (default: unix timestamp at program start)')
parser.add_argument('-n', '--num_clients', type=int, default=5,
                    help='Number of clients for the secure multiparty protocol)')
parser.add_argument('--round_time', type=int, default=10,
                    help='Fixed time the server waits for one round')
parser.add_argument('-s', '--seed', type=int, default=None,
                    help='numpy.random.seed() for simulation')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Maximum verbosity!')
parser.add_argument('-p', '--parallel_mode', type=bool, default=True,
                    help='turn on parallel mode at server side')
parser.add_argument('-d', '--debug_mode', type=bool, default=False,
                    help='print debug info')
parser.add_argument('--config_help', action='store_true',
                    help='Print argument options for this config file')

args, remaining_args = parser.parse_known_args()

if args.config_help:
    parser.print_help()
    exit()

# Historical date to simulate.  Required even if not relevant.
historical_date = pd.to_datetime('2023-01-01')

# Requested log directory.
log_dir = args.log_dir
skip_log = args.skip_log

# Random seed specification on the command line.  Default: None (by clock).
# If none, we select one via a specific random method and pass it to seed()
# so we can record it for future use.  (You cannot reasonably obtain the
# automatically generated seed when seed() is called without a parameter.)

# Note that this seed is used to (1) make any random decisions within this
# config file itself and (2) to generate random number seeds for the
# (separate) Random objects given to each agent.  This ensure that when
# the agent population is appended, prior agents will continue to behave
# in the same manner save for influences by the new agents.  (i.e. all prior
# agents still have their own separate PRNG sequence, and it is the same as
# before)

seed = args.seed
if not seed: seed = int(pd.Timestamp.now().timestamp() * 1000000) % (2**32 - 1)
np.random.seed(seed)

# Config parameter that causes util.util.print to suppress most output.
util.silent_mode = not args.verbose
num_clients = args.num_clients
round_time = args.round_time
num_iterations = args.num_iterations
parallel_mode = args.parallel_mode
debug_mode = args.debug_mode

if not param.assert_power_of_two(num_clients):
    raise ValueError("Number of clients must be power of 2")


print ("Silent mode: {}".format(util.silent_mode))
print ("Configuration seed: {}\n".format(seed))


# Since the simulator often pulls historical data, we use a real-world
# nanosecond timestamp (pandas.Timestamp) for our discrete time "steps",
# which are considered to be nanoseconds.  For other (or abstract) time
# units, one can either configure the Timestamp interval, or simply
# interpret the nanoseconds as something else.

# What is the earliest available time for an agent to act during the
# simulation?
midnight = historical_date
kernelStartTime = midnight

# When should the Kernel shut down?
kernelStopTime = midnight + pd.to_timedelta('2000:00:00')

# This will configure the kernel with a default computation delay
# (time penalty) for each agent's wakeup and recvMsg.  An agent
# can change this at any time for itself.  (nanoseconds)
defaultComputationDelay = 1000000000 * 0.1  # ns

# IMPORTANT NOTE CONCERNING AGENT IDS: the id passed to each agent must:
#    1. be unique
#    2. equal its index in the agents list
# This is to avoid having to call an extra getAgentListIndexByID()
# in the kernel every single time an agent must be referenced.


### Configure the Kernel.
kernel = Kernel("Base Kernel", random_state = np.random.RandomState(seed=np.random.randint(low=0,high=2**32, dtype='uint64')))

### Obtain random state for whatever latency model will be used.
latency_rstate = np.random.RandomState(seed=np.random.randint(low=0,high=2**32, dtype='uint64'))

### Configure the agents.  When conducting "agent of change" experiments, the
### new agents should be added at the END only.
agent_count = 0
agents = []
agent_types = []

### Configure a population of cooperating learning client agents.
a, b = agent_count, agent_count + num_clients
print(f"Agent: {a}, Client: {b}")

### Configure a service agent.
service_init_start = time()
agents.extend([ ServiceAgent(
    id = a,   # set id to be a number after all clients
    name = "Service Agent",
    type = "ServiceAgent",
    random_state = np.random.RandomState(seed=np.random.randint(low=0,high=2**32, dtype='uint64')),
    msg_fwd_delay=0,
    users = [*range(a+1, b+1)],
    iterations = num_iterations,
    round_time = pd.Timedelta(f"{round_time}s"),
    num_clients = num_clients,
    parallel_mode = parallel_mode,
    debug_mode = debug_mode,
) ])

agent_types.extend(["ServiceAgent"])

service_init_end = time()
init_seconds = service_init_end - service_init_start
td_init_s = timedelta(seconds = init_seconds)
print (f"Service init took {td_init_s}")

client_init_start = time()

# Iterate over all client IDs.
# Client index number starts from 1.
for i in range (a+1, b+1):
    agents.append(ClientAgent(id = i,
                              name = "DarkPool Client Agent {}".format(i),
                              type = "ClientAgent",
                              iterations = num_iterations,
                              random_state = np.random.RandomState(seed=np.random.randint(low=0,high=2**32,  dtype='uint64'))))

agent_types.extend([ "ClientAgent" for i in range(a+1,b+1) ])


client_init_end = time()
init_seconds = client_init_end - client_init_start
td_init = timedelta(seconds = init_seconds)
print (f"Client init took {td_init}")


### Configure a latency model for the agents.

# Get a new-style cubic LatencyModel from the networking literature.
pairwise = (len(agent_types),len(agent_types))

model_args = { 'connected'   : True,

               # All in NYC.
               # Only matters for evaluating "real world" protocol duration,
               # not for accuracy, collusion, or reconstruction.
               'min_latency' : np.random.uniform(low = 21000, high = 100000, size = pairwise),
               'jitter'      : 0.3,
               'jitter_clip' : 0.05,
               'jitter_unit' : 5,
               }

latency_model = LatencyModel ( latency_model = 'cubic',
                               random_state = latency_rstate,
                               kwargs = model_args )


# Start the kernel running.
results = kernel.runner(agents = agents,
                        startTime = kernelStartTime,
                        stopTime = kernelStopTime,
                        agentLatencyModel = latency_model,
                        defaultComputationDelay = defaultComputationDelay,
                        skip_log = skip_log,
                        log_dir = log_dir)



# Print parameter summary and elapsed times by category for this experimental trial.
print ()
print (f"######## Microbenchmarks ########")
print (f"Protocol Iterations: {num_iterations}, Clients: {num_clients}, ")

print ()
print ("Service Agent mean time per iteration (except setup)...")
print (f"    Place step:         {results['srv_place']}")
print (f"    Match step:     {results['srv_match']}")
print ()
print ("Client Agent mean time per iteration (except setup)...")
print (f"    Place step:         {results['clt_place'] / num_clients}")
print (f"    Match step:     {results['clt_match'] / num_clients}")
print ()


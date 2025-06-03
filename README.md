# Indifferentially Private Dark Pool Auctions

[![AAMAS 2025](https://img.shields.io/badge/AAMAS-2025-blue)](https://aamas2025.com)


This repository accompanies the paper ***Indifferential Privacy: A New Paradigm and Its Applications to Optimal Matching in Dark Pool Auctions*** ([ArXiv](https://arxiv.org/abs/2502.13415)), as presented at **AAMAS 2025**. 
This implementations includes two protocols for dark pool auctions: Non-Private and Indifferentially Private. We introduce a new system based on 
Indifferential privacy (where a user is indifferent to whether certain information is revealed after some special event) combined with lightweight encryption, 
offering an efficient and practical solution that mitigates the risks of an untrustworthy auctioneer. 



WARNING: This is an academic proof-of-concept prototype and is not production-ready.

## Overview
We integrate our code into [ABIDES](https://github.com/jpmorganchase/abides-jpmc-public), an open-source highfidelity simulator designed for AI research in financial markets (e.g., stock exchanges). 
The simulator supports tens of thousands of clients interacting with a server to facilitate transactions (and in our case to compute sums). 
It also supports configurable pairwise network latencies.

Our protocol works by steps (i.e., round trips). 
A step includes waiting and processing messages. 
The waiting time is set according to the network latency distribution and a target dropout rate.

## Installation Instructions
We recommend using [Miniconda](https://docs.conda.io/en/latest/miniconda.html) to set up environment.
You can download Miniconda by the following command:
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```
To install Miniconda, run
```
bash Miniconda3-latest-Linux-x86_64.sh
```
If you use bash, then run
```
source ~/.bashrc
```
Now create an environment with python 3.9.12 and then activate it.
```
conda create --name idp-darkpool python=3.9.12
conda activate idp-darkpool
```

Use pip to install required packages.
```
pip install -r requirements.txt
```

## Auction Simulation 
The code is in branch `main`.

First enter into folder `pki_files`, and run
```
python setup_pki.py
```

Our program has multiple configs.
```
-c [protocol name] 
-n [number of clients (power of 2)]
-i [number of iterations] 
-p [parallel or not] 
-d [debug mode, if True then output info for every agent]
```
The protocol supports batches of clients with size power of 2, starting from 128,
e.g., 128, 256, 512.

Example command for non-private auction:
```
python -O abides.py -c non_private_auction -n 1024 -i 1 -d 0
```
Example command for IDP auction:
```
python -O abides.py -c idp_auction -n 1024 -i 1 -d 0
```

## Acknowledgement
We thank authors of [Flamingo](https://eprint.iacr.org/2023/486) for providing an example template of ABIDES framework.

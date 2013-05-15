## Overview

unisencoder is a script that imports perfSONAR and RSpec topologies and convert then to UNIS topologies.
unisencoder does only encode the topologies and convert then to UNIS, it does NOT send the output UNIS topology
to a UNIS instance, this is left to the user to do!

The unisencoder is designed in a modular way that enables it to be imported in any python project without the need to
invoke a command line.


## INSTALL

For system-wide install:
```
  sudo python setup.py install
```

For development install:
```
  sudo python setup.py develop
```
For user install:
```
  sudo python setup.py --user
```

Note that for user install `unisencoder` might not be in your default `$PATH` environmnet variable.

## Dependencies

Install process will pull required packages.

### GENI specific dependencies

Using --slice_cred flag requires additional external import
(sfa.trust.credential), available from:  

http://trac.gpolab.bbn.com/gcf/wiki/GettingGcf

This import will also require dateutil, OpenSSL, M2Crypto and a few other python
dependencies.

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

### RDF decoder
UnisEncoder can read Network Topology information from NDL based RDF file and
convert it into UNIS schema and push it into UNIS instance directly.

To use RDF decoder:
```
    unisencoder -t rdf -u <unis-instance-ip> -p <unis-port> --filename <rdf-file-location>
```


### Open Daylight Decoder:
UnisEncoder can read Network Topology information from an OpenDaylight Instance with Yang Rest Interface installed and
convert it into UNIS schema and push it into UNIS instance directly.

To use ODL decoder:
```
    unisencoder -t odl -u <unis-instance-ip> -p <unis-port> --odl_ip <odl-instance-ip> --odl_port <odl-port>
```

odl_port will be Yang UI port which is usually 8181
#!/usr/bin/env python
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from setuptools import setup

version = "0.1.dev"

setup(
    name="unisencoder",
    version=version,
    packages=["unisencoder", "unisencoder.test"],
    package_data={},
    author="Ahmed El-Hassany",
    author_email="ahassany@indiana.edu",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    url="https://github.com/periscope-ps/periscope",
    description="Encodes GENI RSpec and Perfsonar Topology to UNIS",
    include_package_data = True,
    
    install_requires=[
        "argparse",
        "lxml",
        "unittest2",
        "netlogger>=4.3.0",
        "mock==0.8.0",
	"python-dateutil<2.0",
        "rdflib",
        "coreapi",
        "requests"
    ],
    entry_points = {
        'console_scripts': [
            'unisencoder = unisencoder.decoder:main',
        ]
    },
)

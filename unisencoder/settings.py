'''
Created on Apr 2, 2012

@author: fernandes
'''

import os


UNISENCODER_ROOT = os.path.dirname(os.path.abspath(__file__)) + os.sep + os.pardir + os.sep

SCHEMA_DIR = UNISENCODER_ROOT + 'schema' + os.sep
RSPEC3_SCHEMA_DIR = SCHEMA_DIR + 'rspec' + os.sep + '3' + os.sep

DEFAULT_EXNODE_DURATION = 3 # extent lifetime in HOURS
ROOT_NAME = "Landsat"

#XND_FILE_PATH = "/home/jemusser/exnodes" 
XND_FILE_PATH = "/data/jemusser"
DISPATCH_LOG_PATH = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'dispatched_files.log'
UNIS_HOST = "http://dev.incntre.iu.edu"
#UNIS_HOST = "http://localhost"
UNIS_PORT = "8888"

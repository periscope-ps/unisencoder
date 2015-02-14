'''
Created on Apr 2, 2012

@author: fernandes
'''

import os


UNISENCODER_ROOT = os.path.dirname(os.path.abspath(__file__)) + os.sep + os.pardir + os.sep

SCHEMA_DIR = UNISENCODER_ROOT + 'schema' + os.sep
RSPEC3_SCHEMA_DIR = SCHEMA_DIR + 'rspec' + os.sep + '3' + os.sep

EXNODE_LIFETIME = 10 # extent lifetime in HOURS

XND_FILE_PATH = "/home/jemusser/exnodes" 
DISPATCH_LOG_PATH = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'dispatched_files.log'
UNIS_URL = "http://dev.incntre.iu.edu:8888/exnodes"

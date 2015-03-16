import json
import urllib2
import urllib
import os, sys, getopt
import settings
import logging
import uuid
import time
from lxml import etree
from subprocess import call


from decoder import ExnodeDecoder

class Dispatcher(object):
    def __init__(self, **kwargs):
        if "duration" in kwargs:
            self._duration = kwargs["duration"]
        else:
            self._duration = settings.DEFAULT_EXNODE_DURATION

        if "host" in kwargs:
            self._host = kwargs["host"]
        else:
            self._host = settings.UNIS_HOST

        if "port" in kwargs:
            self._port = kwargs["port"]
        else:
            self._port = settings.UNIS_PORT

    def _parseFile(self):
        in_file = open(self._path, 'r')
        info = os.stat(self._path)
        creation_time = int(info.st_ctime)
        modified_time = int(info.st_mtime)
        
        topology = etree.parse(in_file)
        in_file.close()
        encoder = ExnodeDecoder()
        kwargs = dict(creation_time = creation_time, modified_time = modified_time, duration = self._duration)
        
        return encoder.encode(topology, **kwargs)
    
    def SetDuration(duration):
        self._duration = duration

    def DispatchFile(self, filename, parent, metadata = None):
        self._path = filename
        topology_out = self._parseFile()
        topology_out["parent"] = parent
        topology_out["properties"] = {}
        topology_out["properties"]["metadata"] = metadata
        
        data = json.dumps(topology_out)
        request = urllib2.Request("{host}:{port}/exnodes".format(host = self._host, port = self._port), data = data, headers = {'Content-Type': 'application/perfsonar+json'})
        
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            self.log.error("Failed to connect to UNIS", value = e.code, guid = self._guid)
        except urllib2.URLError as e:
            self.log.error("Failed to connect to UNIS", value = e.args, guid = self._guid)

    def CreateRemoteDirectory(self, name, parent):
        data = {}
        data["created"]  = int(time.time())
        data["modified"] = int(time.time())
        data["name"]     = name
        data["size"]     = 0
        data["parent"]   = parent
        data["mode"]     = "directory"
        data = json.dumps(data)
        print "Sending: {0}".format(data)
        request = urllib2.Request("{host}:{port}/exnodes".format(host = self._host, port = self._port), data = data, headers = {'Content-Type': 'application/perfsonar+json'})
        response = ""
        
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print "Failed to contact UNIS - {err}".format(err = e)
        except urllib2.URLError as e:
            print "Error in URL - {err}".format(err = e)
            
        response =  response.read()
        print response
        response = json.loads(response)
        return response["id"]
        



#  Temporary function that creates a list of upload candidates
def create_file_list():
    tmpResult = []

    for dirName, subdirList, fileList in os.walk(settings.XND_FILE_PATH):
        for filename in fileList:
            if filename.endswith(".xnd"):
        	tmpPath = "%s/%s" % (dirName, filename)
	      	tmpResult.append(tmpPath)
            else:
		continue
        
    return tmpResult


def create_directories(dispatch, filename, root):
    directories = filename.split("/")
    ids = []
    ids.append(root)
    
    for index in range(0, len(directories) - 1):
        ids.append(dispatch.CreateRemoteDirectory(directories[index], ids[index]))

    return ids[len(ids) - 1]

def build_dispatch_list(file_list):
    entries = []
    tmpResult = []
    
    if not os.path.exists(settings.DISPATCH_LOG_PATH):
        with open(settings.DISPATCH_LOG_PATH, 'w') as dispatch_log:
            pass

    with open(settings.DISPATCH_LOG_PATH, 'r+') as dispatch_log:
        for line in dispatch_log:
            entries.append(line.split('\t'))
    
    with open(settings.DISPATCH_LOG_PATH, 'w') as dispatch_log:
        for filename in file_list:
            info = os.stat(filename)
            modified_time = int(info.st_mtime)
            tmpDoUpload = True
            
            for entry in entries:
                if filename == entry[0]:
                    if int(modified_time) > int(entry[1]):
                        tmpDoUpload = True
                    else:
                        tmpDoUpload = False
                    break
                
            if tmpDoUpload:
                tmpResult.append(filename)
            else:
                dispatch_log.write("%s\t%s\n" % (filename, modified_time))
            
    return tmpResult

def parse_filename(filename):
    sensor = filename[:3]
    path   = filename[3:6]
    row    = filename[6:9]
    year   = filename[9:13]

    return "%s/%s/%s/%s/%s" % (sensor, path, row, year, filename)

def build_metadata(filepath):
    path_parts = filepath.split('/')
    metadata = {}
    metadata["sensor"] = path_parts[0]
    metadata["path"]   = path_parts[1]
    metadata["row"]    = path_parts[2]
    metadata["year"]   = path_parts[3]
    
    return metadata

def main(argv):
    do_expand = False

    try:
        opts, args = getopt.getopt(argv, "x", ["--expand-folders"])
        for opt, arg in opts:
            if opt in ('-x', "--expand-folders"):
                do_expand = True
    except:
        pass
    
    dispatch_list = build_dispatch_list(create_file_list())
    dispatch = Dispatcher()
    
    root_id = dispatch.CreateRemoteDirectory(settings.ROOT_NAME, None)
    for filename in dispatch_list:
        metadata = {}
        expanded_dir = os.path.relpath(filename, settings.XND_FILE_PATH)
        if do_expand:
            print "Expanding filename"
            expanded_dir = parse_filename(expanded_dir)
            metadata = build_metadata(expanded_dir)

        parent = create_directories(dispatch, expanded_dir, root_id)
        dispatch.DispatchFile(filename, parent, metadata)
        
if __name__ == "__main__":
    main(sys.argv[1:])

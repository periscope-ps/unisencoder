import json
import urllib2
import urllib
import os, sys, getopt
import settings
import logging
import uuid
import time
from netlogger import nllog
from lxml import etree
from subprocess import call


from decoder import ExnodeDecoder

class Dispatcher(object, nllog.DoesLogging):
    def __init__(self):
        nllog.DoesLogging.__init__(self)
        self._guid = uuid.uuid1()

    def _parseFile(self):
        self.log.debug("parse.start", guid = self._guid)
        in_file = open(self._path, 'r')
        info = os.stat(self._path)
        creation_time = int(info.st_ctime)
        modified_time = int(info.st_mtime)
        
        topology = etree.parse(in_file)
        in_file.close()        
        encoder = ExnodeDecoder()
        kwargs = dict(creation_time = creation_time,
                      modified_time = modified_time)
        
        self.log.debug("parse.end", guid = self._guid)
        return encoder.encode(topology, **kwargs)
    
    def DispatchFile(self, filename, parent, metadata = None):
        self.log.debug("dispatch.start", guid = self._guid)
        self._path = filename
        topology_out = self._parseFile()
        topology_out["parent"] = parent
        topology_out["properties"] = {}
        topology_out["properites"]["metadata"] = metadata
        
        data = json.dumps(topology_out)
        request = urllib2.Request("%s" % settings.UNIS_URL, data = data, headers = {'Content-Type': 'application/perfsonar+json'})
        
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            self.log.error("Failed to connect to UNIS", value = e.code, guid = self._guid)
        except urllib2.URLError as e:
            self.log.error("Failed to connect to UNIS", value = e.args, guid = self._guid)

        self.log.debug("dispatch.end", guid = self._guid)        

def setup_logger(filename = "dispatcher.log"):
    logging.setLoggerClass(nllog.BPLogger)
    log = logging.getLogger(nllog.PROJECT_NAMESPACE)
    handler = logging.FileHandler(filename)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)


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

def create_remote_directory(_name, _parent):
    data = {}
    data["created"]  = int(time.time())
    data["modified"] = int(time.time())
    data["name"]     = _name
    data["size"]     = 0
    data["parent"]   = _parent
    data["mode"]     = "directory"
    data = json.dumps(data)
    request = urllib2.Request("%s" % settings.UNIS_URL, data = data, headers = {'Content-Type': 'application/perfsonar+json'})
    response = ""

    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        print "Failed to contact UNIS"
    except urllib2.URLError as e:
        print "Error in URL"

    response =  response.read()
    print response
    response = json.loads(response)
    return response["id"]

def create_directories(filename, root):
    directories = filename.split("/")
    ids = []
    ids.append(root)
    
    for index in range(0, len(directories) - 1):
        ids.append(create_remote_directory(directories[index], ids[index]))

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

def log_dispatch(filename):
    info = os.stat(filename)
    modified_time = int(info.st_mtime)
    
    with open(settings.DISPATCH_LOG_PATH, 'a') as dispatch_log:
        dispatch_log.write("%s\t%s\n" % (filename, modified_time))

def main(argv):
    do_expand = False
    setup_logger()
    try:
        opts, args = getopt.getopt(argv, "x", ["--expand-folders"])
        for opt, arg in opts:
            if opt in ('-x', "--expand-folders"):
                do_expand = True
    except:
        pass
    
    dispatch_list = build_dispatch_list(create_file_list())
    dispatch = Dispatcher()
    
    root_id = create_remote_directory("root", None)
    for filename in dispatch_list:
        metadata = {}
        expanded_dir = os.path.relpath(filename, settings.XND_FILE_PATH)
        if do_expand:
            print "Expanding filename"
            expanded_dir = parse_filename(expanded_dir)
            metadata = build_metadata(expanded_dir)

        parent = create_directories(expanded_dir, root_id)
        dispatch.DispatchFile(filename, parent, metadata)
        log_dispatch(filename)
        
if __name__ == "__main__":
    main(sys.argv[1:])

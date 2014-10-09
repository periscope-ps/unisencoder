import json
import urllib2
import urllib
import os
import settings
import logging
import uuid
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
    
    def DispatchFile(self, path):
        self.log.debug("dispatch.start", guid = self._guid)
        self._path = path
        topology_out = self._parseFile()
        data = json.dumps(topology_out)
        request = urllib2.Request("%s/files" % settings.UNIS_URL, data = data, headers = {'Content-Type': 'application/perfsonar+json'})
        
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
    
    for filename in os.listdir(settings.XND_FILE_PATH):
        if filename.endswith(".xnd"):
            tmpPath = "%s/%s" % (settings.XND_FILE_PATH, filename)
            tmpResult.append(tmpPath)
        else:
            continue
        
    return tmpResult


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
            creation_time = int(info.st_ctime)
            tmpDoUpload = True
            
            for entry in entries:
                if filename == entry[0]:
                    if int(modified_time) > int(entry[1]):
                        tmpDoUpload = True
                    else:
                        tmpDoUpload = False
                    break
                
            dispatch_log.write("%s\t%s\n" % (filename, modified_time))
            if tmpDoUpload:
                tmpResult.append(filename)
            
    return tmpResult

def main():
    setup_logger()
    dispatch_list = build_dispatch_list(create_file_list())
    dispatch = Dispatcher()
    
    for filename in dispatch_list:
        dispatch.DispatchFile(filename)
    
if __name__ == "__main__":
    main()

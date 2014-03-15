#!/usr/bin/env python
"""
Decodes different topologies to UNIS representation.

@author: Ahmed El-Hassany
@author: fernandes
"""

import argparse
import json
import logging
import re
import sys
import uuid
import pdb #python debugger use, pdb.set_trace(), to start trace
from lxml import etree
from netlogger import nllog
from urllib import unquote
from urllib import quote
import urllib2 

nllog.PROJECT_NAMESPACE = "unisencoder"


class UNISDecoderException(Exception):
    """The default exception raise by UNIS decoders"""
    pass

class UNISDecoder(object, nllog.DoesLogging):
    """Abstract class for UNIS decoders."""
    
    SCHEMAS = {
        'networkresource': 'http://unis.incntre.iu.edu/schema/20120709/networkresource#',
        'node': 'http://unis.incntre.iu.edu/schema/20120709/node#',
        'domain': 'http://unis.incntre.iu.edu/schema/20120709/domain#',
        'topology': 'http://unis.incntre.iu.edu/schema/20120709/topology#',
        'port': 'http://unis.incntre.iu.edu/schema/20120709/port#',
        'link': 'http://unis.incntre.iu.edu/schema/20120709/link#',
        'network': 'http://unis.incntre.iu.edu/schema/20120709/network#',
        'blipp': 'http://unis.incntre.iu.edu/schema/20120709/blipp#',
        'metadata': 'http://unis.incntre.iu.edu/schema/20120709/metadata#',
    }
    
    def __init__(self):
        nllog.DoesLogging.__init__(self)
        self._guid = uuid.uuid1()
    
    def encode(self, tree, **kwargs):
        """Abstract method."""
        raise NotImplementedError
    
    def _encode_ignore(self, doc, out, **kwargs):
        """Just log Ignore an element."""
        self.log.info("ignore", tag=doc.tag, guid=self._guid)
    
    def _parse_xml_bool(self, xml_bool):
        clean = xml_bool.strip().lower()
        map_bool = {"true": True, "false": False, "1": True, "0": False}
        if clean not in map_bool:
            self.log.error("not_valid_xml_boolean", value=xml_bool, guid=self._guid)
            return xml_bool
        else:
            return map_bool[clean]
    
    @staticmethod
    def is_valid_ipv4(ip):
        """Validates IPv4 addresses."""
        
        pattern = re.compile(r"""
            ^
            (?:
              # Dotted variants:
              (?:
                # Decimal 1-255 (no leading 0's)
                [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
              |
                0x0*[0-9a-f]{1,2}  # Hexadecimal 0x0 - 0xFF (possible leading 0's)
              |
                0+[1-3]?[0-7]{0,2} # Octal 0 - 0377 (possible leading 0's)
              )
              (?:                  # Repeat 0-3 times, separated by a dot
                \.
                (?:
                  [3-9]\d?|2(?:5[0-5]|[0-4]?\d)?|1\d{0,2}
                |
                  0x0*[0-9a-f]{1,2}
                |
                  0+[1-3]?[0-7]{0,2}
                )
              ){0,3}
            |
              0x0*[0-9a-f]{1,8}    # Hexadecimal notation, 0x0 - 0xffffffff
            |
              0+[0-3]?[0-7]{0,10}  # Octal notation, 0 - 037777777777
            |
              # Decimal notation, 1-4294967295:
              429496729[0-5]|42949672[0-8]\d|4294967[01]\d\d|429496[0-6]\d{3}|
              42949[0-5]\d{4}|4294[0-8]\d{5}|429[0-3]\d{6}|42[0-8]\d{7}|
              4[01]\d{8}|[1-3]\d{0,9}|[4-9]\d{0,8}
            )
            $
        """, re.VERBOSE | re.IGNORECASE)
        return pattern.match(ip) is not None

    @staticmethod
    def is_valid_ipv6(ip):
        """Validates IPv6 addresses."""
        
        pattern = re.compile(r"""
            ^
            \s*                         # Leading whitespace
            (?!.*::.*::)                # Only a single whildcard allowed
            (?:(?!:)|:(?=:))            # Colon iff it would be part of a wildcard
            (?:                         # Repeat 6 times:
                [0-9a-f]{0,4}           #  A group of at most four hexadecimal digits
                (?:(?<=::)|(?<!::):)    #  Colon unless preceeded by wildcard
            ){6}                        #
            (?:                         # Either
                [0-9a-f]{0,4}           #   Another group
                (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
                [0-9a-f]{0,4}           #   Last group
                (?: (?<=::)             #   Colon iff preceeded by exacly one colon
                 |  (?<!:)              #
                 |  (?<=:) (?<!::) :    #
                 )                      # OR
             |                          #   A v4 address with NO leading zeros
                (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
                (?: \.
                    (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
                ){3}
            )
            \s*                         # Trailing whitespace
            $
        """, re.VERBOSE | re.IGNORECASE | re.DOTALL)
        return pattern.match(ip) is not None

    
class RSpec3Decoder(UNISDecoder):
    """Decodes RSpecV3 to UNIS format."""
    
    rspec3 = ["http://www.protogeni.net/resources/rspec/3",
              "http://www.protogeni.net/resources/rspec/2",
              "http://www.geni.net/resources/rspec/3"]
    sharedvlan = ["http://www.protogeni.net/resources/rspec/ext/shared-vlan/1",
                  "http://www.geni.net/resources/rspec/ext/shared-vlan/1"]
    gemini = ["http://geni.net/resources/rspec/ext/gemini/1"]
    openflow = ["http://www.geni.net/resources/rspec/ext/openflow/3"]
    topo = ["http://geni.bssoftworks.com/rspec/ext/topo/1"]
    opstate = ["http://www.geni.net/resources/rspec/ext/opstate/1"]

    ns_default = None

    RSpecADV = "advertisement"
    RSpecRequest = "request"
    RSpecManifest = "manifest"

    def __init__(self):
        super(RSpec3Decoder, self).__init__()
        self._parent_collection = {}
        self._tree = None
        self._root = None
        self._jsonpointer_path = "#/"
        self._jsonpath_cache = {}
        self._urn_cache = {}
        self._component_id_cache = {}
        self._sliver_id_cache = {}
        self.geni_ns = "geni"
        self._ignored_namespaces = [
            "http://hpn.east.isi.edu/rspec/ext/stitch/0.1/",
            "http://www.protogeni.net/resources/rspec/ext/emulab/1",
            "http://www.protogeni.net/resources/rspec/ext/flack/1",
            "http://www.protogeni.net/resources/rspec/ext/client/1",
        ]
        # Resolving jsonpath is expensive operation
        # This cache keeps track of jsonpath used to replaced in the end
        # with jsonpointers
        self._subsitution_cache = {}

        self._handlers = {}
        for ns in RSpec3Decoder.rspec3:
            self._handlers.update({
            "{%s}%s" % (ns, "rspec") : self._encode_rspec,
            "{%s}%s" % (ns, "node") : self._encode_rspec_node,
            "{%s}%s" % (ns, "location") : self._encode_rspec_location,
            "{%s}%s" % (ns, "hardware_type") : self._encode_rspec_hardware_type,
            "{%s}%s" % (ns, "interface") : self._encode_rspec_interface,
            "{%s}%s" % (ns, "available") : self._encode_rspec_available,
            "{%s}%s" % (ns, "cloud") : self._encode_rspec_cloud,           ### new tag, cloud
            "{%s}%s" % (ns, "sliver_type") : self._encode_rspec_sliver_type,
            "{%s}%s" % (ns, "disk_image") : self._encode_rspec_disk_image,
            "{%s}%s" % (ns, "relation") : self._encode_rspec_relation,
            "{%s}%s" % (ns, "link") : self._encode_rspec_link,
            "{%s}%s" % (ns, "link_type") : self._encode_rspec_link_type,
            "{%s}%s" % (ns, "component_manager") : self._encode_rspec_component_manager,
            "{%s}%s" % (ns, "interface_ref") : self._encode_rspec_interface_ref,
            "{%s}%s" % (ns, "property") : self._encode_rspec_property,
            "{%s}%s" % (ns, "host") : self._encode_rspec_host,
            "{%s}%s" % (ns, "ip") : self._encode_rspec_ip,
            "{%s}%s" % (ns, "services") : self._encode_rspec_services,
            "{%s}%s" % (ns, "login") : self._encode_rspec_login,
            "{%s}%s" % (ns, "external_ref") : self._encode_rspec_external_ref,
            })
        for ns in RSpec3Decoder.sharedvlan:
            self._handlers.update({
            "{%s}%s" % (ns, "link_shared_vlan") : self._encode_sharedvlan_link_shared_vlan,
            "{%s}%s" % (ns, "link_shared_vlan") : self._encode_sharedvlan_link_shared_vlan,
            })
        for ns in RSpec3Decoder.gemini:
            self._handlers.update({
            "{%s}%s" % (ns, "node") : self._encode_gemini_node,
            "{%s}%s" % (ns, "monitor_urn") : self._encode_gemini_monitor_urn,
            })
        for ns in RSpec3Decoder.openflow:
            self._handlers.update({
            "{%s}%s" % (ns, "datapath") : self._encode_foam_datapath,
            "{%s}%s" % (ns, "port") : self._encode_foam_port,
            "{%s}%s" % (ns, "location") : self._encode_foam_location,
            "{%s}%s" % (ns, "sliver") : self._encode_foam_sliver,
            "{%s}%s" % (ns, "controller") : self._encode_foam_controller,
            "{%s}%s" % (ns, "group") : self._encode_foam_group,
            "{%s}%s" % (ns, "match") : self._encode_foam_match,
            })
        for ns in RSpec3Decoder.topo:
            self._handlers.update({
            "{%s}%s" % (ns, "geni-of") : self._encode_foam_topo,
            "{%s}%s" % (ns, "geni-host") : self._encode_foam_topo,
            "{%s}%s" % (ns, "other") : self._encode_foam_topo,
            "{%s}%s" % (ns, "pg-host") : self._encode_foam_topo,
            })
        for ns in RSpec3Decoder.opstate:
            self._handlers.update({
            "{%s}%s" % (ns, "rspec_opstate") : self._encode_rspec_opstate,
            })

    def _encode_children(self, doc, out, **kwargs):
        """Iterates over the all child nodes and process and call the approperiate
        handler for each one."""
        for child in doc.iterchildren():
            if child.tag is etree.Comment:
                continue
            if child.nsmap.get(child.prefix, None) in self._ignored_namespaces:
                continue
            self.log.debug("_encode_children.start", child=child.tag, guid=self._guid)
            if child.tag in self._handlers:
                self._handlers[child.tag](child, out, **kwargs)
            else:
                #pdb.set_trace()
                sys.stderr.write("No handler for: %s\n" % child.tag)
                self.log.error("no handler for '%s'" % child.tag,
                    child=child.tag , guid=self._guid)
            self.log.debug("_encode_children.end",
                child=child.tag, guid=self._guid)
    @staticmethod
    def rspec_create_urn(component_id):
        return unquote(component_id).strip()
    
    def _refactor_default_xmlns(self, tree):
        """
        Change the RSpec from the default namespace to an explicit namespace.
        This will make xpath works!
        """
        exclude_ns = ""
        exclude_prefixes = ""
        for x in range(len(self._ignored_namespaces)):
            exclude_ns += 'xmlns:ns%d="%s"\n' % (x, self._ignored_namespaces[x])
            exclude_prefixes +="ns%d " % x
        if exclude_ns != "":
            exclude_prefixes = 'exclude-result-prefixes="%s"\n' % exclude_prefixes 

        XSLT = """
        <xsl:stylesheet version="1.0" 
           xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
           xmlns="http://sample.com/s" 
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
           xmlns:xs="http://www.w3.org/2001/XMLSchema"
           %s
           %s
           xmlns:rspec="%s"
           >

           <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
           
           <xsl:template match="/">
             <xsl:copy>
                <xsl:apply-templates select="@* | node()"/>
             </xsl:copy>              
           </xsl:template>
           
           <xsl:template match="*">
              <xsl:copy>
                <xsl:apply-templates select="@* | node()"/>
              </xsl:copy>
           </xsl:template>
           

           <xsl:template match="rspec:*">
              <xsl:element name="rspec:{local-name()}">
                 <xsl:apply-templates select="@* | node()"/>
              </xsl:element>
           </xsl:template>
           
           <xsl:template match="@*">
              <xsl:attribute name="{local-name()}">
                 <xsl:value-of select="."/>
              </xsl:attribute>
           </xsl:template>
        </xsl:stylesheet>
        """ % (exclude_ns, exclude_prefixes, RSpec3Decoder.ns_default)
        
        xslt_root = etree.XML(XSLT)
        transform = etree.XSLT(xslt_root)
        tree = transform(tree)
            
        return tree

    def encode(self, tree, slice_urn=None, **kwargs):
        self.log.debug("encode.start", guid=self._guid)
        out = {}
        
        # set the default document namespace
        root = tree.getroot()
        RSpec3Decoder.ns_default = root.nsmap[None]

        tree = self._refactor_default_xmlns(tree)
        root = tree.getroot()
        self._tree = tree
        self._root = root
        self._parent_collection = out            

        if root.tag in self._handlers:
            self._handlers[root.tag](root, out, collection=out,
                parent=out, slice_urn=slice_urn, **kwargs)
        else:
            #pdb.set_trace()
            sys.stderr.write("No handler for: %s\n" % root.tag)
        
        sout = json.dumps(out)
        # This is an optimization hack to make every jsonpath a jsonpointer
        for urn, jpath in self._subsitution_cache.iteritems():
            if urn in self._jsonpath_cache:
                sout = sout.replace(jpath, self._jsonpath_cache[urn])
        out = json.loads(sout)
        
        self.log.debug("encode.end", guid=self._guid)
        return out
    
    def _encode_rspec(self, doc, out, **kwargs):
        self.log.debug("_encode_rspec.start", guid=self._guid)
        assert isinstance(out, dict)
        assert doc.nsmap['rspec'] in RSpec3Decoder.rspec3, \
            "Not valid element '%s'" % doc.tag
        
        if not self._parent_collection:
            self._parent_collection = out
            self._jsonpointer_path =  "#"
        # Parse GENI specific properties
        out["$schema"] = UNISDecoder.SCHEMAS["domain"]
        if "properties" not in out:
            out["properties"] = {}
        if self.geni_ns not in out["properties"]:
            out["properties"][self.geni_ns] = {}
        geni_props = out["properties"][self.geni_ns]
        attrib = dict(doc.attrib)
        # From XML schema
        attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)
        # From common.rnc
        generated = attrib.pop('generated', None)
        generated_by = attrib.pop('generated_by', None)
        expires = attrib.pop('expires', None)
        # From ad.rnc and request.rnc
        rspec_type = attrib.pop('type', "")
        rspec_type = rspec_type.strip()
        
        # Some validation of Input
        if rspec_type not in [RSpec3Decoder.RSpecADV, RSpec3Decoder.RSpecManifest]:
            self.log.debug("_encode_rspec.end", guid=self._guid)
            raise UNISDecoderException("Unsupported rspec type '%s'" % rspec_type)
        
        if rspec_type == RSpec3Decoder.RSpecManifest and kwargs.get("slice_urn", None) is None:
            self.log.debug("_encode_rspec.end", guid=self._guid)
            self.log.error("no_slice_urn", guid=self._guid)
            self.log.debug("_encode_rspec.end", guid=self._guid)
            raise UNISDecoderException("slice_urn must be provided "
                "when decoding manifest.")
         
        if rspec_type == RSpec3Decoder.RSpecADV and kwargs.get("component_manager_id", None) is None:
            self.log.debug("_encode_rspec.end", guid=self._guid)
            self.log.error("no_component_manager_id", guid=self._guid)
            self.log.debug("_encode_rspec.end", guid=self._guid)
            raise UNISDecoderException("component_manager_id must be "
                "provided when decoding advertisment rspec.")
        
        # Building GENI properties
        if generated is not None:
            geni_props['generated'] = generated.strip()
        if generated_by is not None:
            geni_props['generated_by'] = generated_by.strip()
        if expires is not None:
            geni_props['expires'] = expires.strip()
        if rspec_type is not None:
            geni_props['type'] = rspec_type.strip()
        kwargs.pop("parent", None)
        collection = kwargs.pop("collection", out)
        
         # Generating URN
        if rspec_type == RSpec3Decoder.RSpecManifest:
            slice_urn = kwargs.get("slice_urn", None)
            geni_props['slice_urn'] = slice_urn            
            out["urn"] = slice_urn
            slice_uuid = kwargs.get("slice_uuid")
            if slice_uuid is not None:
                geni_props['slice_uuid'] = slice_uuid
            out["id"] = self.geni_urn_to_id(slice_urn)
            slice_uuid = kwargs.get("slice_uuid")
            if slice_uuid is not None:
                geni_props['slice_uuid'] = slice_uuid
        elif rspec_type == RSpec3Decoder.RSpecADV:
            component_manager_id = kwargs.get("component_manager_id", None)            
            out["id"] = self.geni_urn_to_id(component_manager_id)
            out["urn"] = component_manager_id
        
        # Iterate children
        self._encode_children(doc, out, rspec_type=rspec_type,
            collection=collection, parent=out, **kwargs)
        
        if len(attrib) > 0:
            self.log.warn("unpares_attribute.warn", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
            
        self.log.debug("_encode_rspec.end", guid=self._guid)
        return out
    
    def geni_urn_to_id(self, geni_id):
        return geni_id.replace('urn:publicid:IDN+', '').replace('+', '_')
    
    def _encode_rspec_node(self, doc, out, collection, **kwargs):
        self.log.debug("_encode_rspec_node.start",
            component_id=doc.attrib.get("component_id", None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.nsmap['rspec'] in RSpec3Decoder.rspec3, \
            "Not valid element '%s'" % doc.tag
        node = {}
        node["$schema"] = UNISDecoder.SCHEMAS["node"]
        if "nodes" not in collection:
            collection["nodes"] = []
        
        # Parse GENI specific properties
        if "properties" not in node:
            node["properties"] = {}
        if self.geni_ns not in node["properties"]:
            node["properties"][self.geni_ns] = {}
        geni_props = node["properties"][self.geni_ns]
        attrib = dict(doc.attrib)
        # From common.rnc
        # From ad.rnc & request.rnc
        component_id = attrib.pop('component_id', None)
        component_manager_id = attrib.pop('component_manager_id', None)
        component_name = attrib.pop('component_name', None)
        # From request.rnc
        client_id = attrib.pop('client_id', None)
        exclusive = attrib.pop('exclusive', None)
        colocate = attrib.pop('colocate', None)
        # From manifest.rnc
        sliver_id = attrib.pop('sliver_id', None)
        
        if component_id is not None:
            geni_props['component_id'] = unquote(component_id.strip())
        if client_id is not None:
            geni_props['client_id'] = client_id.strip()
        if component_name is not None:
            geni_props['component_name'] = component_name.strip()        
        if sliver_id is not None:
            geni_props['sliver_id'] = sliver_id.strip()
        if component_manager_id is not None:
            geni_props['component_manager_id'] = component_manager_id.strip()
        if exclusive is not None:
            geni_props['exclusive'] = self._parse_xml_bool(exclusive)
        if colocate is not None:
            geni_props['colocate'] = colocate.strip()

        slice_uuid = kwargs.get("slice_uuid")
        if slice_uuid is not None:
            geni_props['slice_uuid'] = slice_uuid
    
        # Set URN, ID, and name
        rspec_type = kwargs.get("rspec_type", None)
        if rspec_type == RSpec3Decoder.RSpecADV:
            node["urn"] = RSpec3Decoder.rspec_create_urn(geni_props['component_id'])
            node["id"] = self.geni_urn_to_id(geni_props['component_id'])
            self._component_id_cache[component_id.strip()] = doc
            if component_name:
                node["name"] = geni_props['component_name']
        elif rspec_type == RSpec3Decoder.RSpecManifest:
            slice_urn = kwargs.get("slice_urn")
            geni_props['slice_urn'] = slice_urn
            node["urn"] = RSpec3Decoder.rspec_create_urn(slice_urn+"+node+"+geni_props['client_id'])
            node["id"] = self.geni_urn_to_id(slice_urn+"_node_"+geni_props['client_id'])
            node["name"] = geni_props['client_id']
            if component_id is not None:
                if 'relations' not in node:
                    node['relations'] = {}
                if 'over' not in node['relations']:
                    node['relations']['over'] = []
                node['relations']['over'].append({"href": component_id, "rel": "full"})
        
        kwargs.pop("parent", None)
        self._encode_children(doc, node, collection=collection,
            parent=node, **kwargs)
        
        collection["nodes"].append(node)
        if node.get("urn", None) is not None:
            pointer = self._jsonpointer_path + "/nodes/%d" % (len(collection["nodes"]) - 1)
            self._urn_cache[node["urn"]] = pointer 
            
        if len(attrib) > 0:
            self.log.warn("unparesd_attributes", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self.log.debug("_encode_rspec_node.end",
            component_id=doc.attrib.get("component_id", None), guid=self._guid)
        return node
        
    def _encode_rspec_interface(self, doc, out, collection, **kwargs):
        self.log.debug("_encode_rspec_interface.start",
            component_id=doc.attrib.get("component_id", None),
            guid=self._guid)
        assert isinstance(out, dict)
        port = {}
        port["$schema"] = UNISDecoder.SCHEMAS["port"]
        
        # Parse GENI specific properties
        if "properties" not in port:
            port["properties"] = {}
        if self.geni_ns not in port["properties"]:
            port["properties"][self.geni_ns] = {}
        
        geni_props = port["properties"][self.geni_ns]
        attrib = dict(doc.attrib)
        # From common.rnc
        # From request.rnc & ad.rnc
        component_id = attrib.pop('component_id', None)
        component_name = attrib.pop('component_name', None)
        role = attrib.pop('role', None)
        public_ipv4 = attrib.pop('public_ipv4', None)
        # From request.rnc
        client_id = attrib.pop('client_id', None)
        # From manifest
        sliver_id = attrib.pop('sliver_id', None)
        mac_address = attrib.pop('mac_address', None)
        
        if component_id is not None:
            geni_props['component_id'] = unquote(component_id.strip())
        if client_id is not None:
            geni_props['client_id'] = client_id.strip()
        if component_name is not None:
            geni_props['component_name'] = component_name.strip()
        if sliver_id is not None:
            geni_props['sliver_id'] = sliver_id.strip()
        if role is not None:
            geni_props['role'] = role.strip()
        if public_ipv4 is not None:
            geni_props['public_ipv4'] = public_ipv4.strip()
            port["address"] = {
                "type": "ipv4",
                "address": geni_props['public_ipv4']
            }
        if mac_address is not None:
            geni_props['mac_address'] = mac_address.strip()
            port["address"] = {
                "type": "mac",
                "address": geni_props['mac_address']
            }

        slice_uuid = kwargs.get("slice_uuid")
        if slice_uuid is not None:
            geni_props['slice_uuid'] = slice_uuid
        
        # Set URN, ID, and name
        rspec_type = kwargs.get("rspec_type", None)
        if rspec_type == RSpec3Decoder.RSpecADV:
            port["urn"] = RSpec3Decoder.rspec_create_urn(geni_props['component_id'])
            port["id"] = self.geni_urn_to_id(geni_props['component_id'])
            self._component_id_cache[component_id.strip()] = doc
            if component_name:
                port["name"] = geni_props['component_name']
        elif rspec_type == RSpec3Decoder.RSpecManifest:
            slice_urn = kwargs.get("slice_urn")
            geni_props['slice_urn'] = slice_urn
            port["urn"] = RSpec3Decoder.rspec_create_urn(slice_urn+"+interface+"+geni_props['client_id'])
            port["id"] = self.geni_urn_to_id(slice_urn+"_interface_"+geni_props['client_id'])
            port["name"] = geni_props['client_id']
            if component_id is not None:
                if 'relations' not in port:
                    port['relations'] = {}
                if 'over' not in port['relations']:
                    port['relations']['over'] = []
                port['relations']['over'].append({"href": component_id, "rel": "full"})
            
        kwargs.pop("parent", None)
        self._encode_children(doc, port, collection=collection,
            parent=port, **kwargs)
        
        if out == self._parent_collection:
            if "ports" not in out:
                out["ports"] = []
            out["ports"].append(port)
            pointer = self._jsonpointer_path + \
                "/ports/%d" % (len(out["ports"]) - 1)
        else:
            if "ports" not in collection:
                collection["ports"] = []
            collection["ports"].append(port)
            if "ports" not in out:
                out["ports"] = []
            pointer = self._jsonpointer_path + \
                "/ports/%d" % (len(collection["ports"]) - 1)
            out["ports"].append({"href": pointer, "rel": "full"})
        
        if port.get("urn", None) is not None:
            self._urn_cache[port["urn"]] = pointer 
        
        if len(attrib) > 0:
            self.log.warn("unpares_attribute.warn", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self.log.debug("_encode_rspec_interface.end", guid=self._guid)
        return port
    
    def _encode_rspec_link(self, doc, out, collection, **kwargs):
        self.log.debug("_encode_rspec_link.start",
            component_id=doc.attrib.get("component_id", None),
            guid=self._guid)
        assert isinstance(out, dict)
        link = {}
        link["$schema"] = UNISDecoder.SCHEMAS["link"]
        
        # Parse GENI specific properties
        if "properties" not in link:
            link["properties"] = {}
        if self.geni_ns not in link["properties"]:
            link["properties"][self.geni_ns] = {}
        
        geni_props = link["properties"][self.geni_ns]
        attrib = dict(doc.attrib)
        
        # From ad.rnc
        component_id = attrib.pop('component_id', None)
        component_name = attrib.pop('component_name', None)
        # From request.rnc
        client_id = attrib.pop('client_id', None)
        # From mainfest.rnc
        vlantag = attrib.pop('vlantag', None)
        sliver_id = attrib.pop('sliver_id', None)
        
        if component_id is not None:
            geni_props['component_id'] = unquote(component_id.strip())
        if component_name is not None:
            geni_props['component_name'] = component_name.strip()
        if client_id is not None:
            geni_props['client_id'] = client_id.strip()
        if vlantag is not None:
            geni_props['vlantag'] = vlantag.strip()
        if sliver_id is not None:
            geni_props['sliver_id'] = sliver_id.strip()

        slice_uuid = kwargs.get("slice_uuid")
        if slice_uuid is not None:
            geni_props['slice_uuid'] = slice_uuid
            
        # Set URN, ID, and name
        rspec_type = kwargs.get("rspec_type", None)
        if rspec_type == RSpec3Decoder.RSpecADV:
            link["urn"] = RSpec3Decoder.rspec_create_urn(geni_props['component_id'])
            link["id"] = self.geni_urn_to_id(geni_props['component_id'])
            self._component_id_cache[component_id.strip()] = doc
            if component_name:
                link["name"] = geni_props['component_name']
        elif rspec_type == RSpec3Decoder.RSpecManifest:
            slice_urn = kwargs.get("slice_urn")
            geni_props['slice_urn'] = slice_urn
            link["urn"] = RSpec3Decoder.rspec_create_urn(slice_urn+"+link+"+geni_props['client_id'])
            link["id"] = self.geni_urn_to_id(slice_urn+"_link_"+geni_props['client_id'])
            link["name"] = geni_props['client_id']
            if component_id is not None:
                if 'relations' not in link:
                    link['relations'] = {}
                if 'over' not in link['relations']:
                    link['relations']['over'] = []
                link['relations']['over'].append({"href": component_id, "rel": "full"})
        
        if len(attrib) > 0:
            self.log.warn("unpares_attribute.warn", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        kwargs.pop("parent", None)
        self._encode_children(doc, link, collection=collection,
            parent=link, **kwargs)
        
        # First try to establish links by interface_ref
        interface_refs = geni_props.get("interface_refs", [])
        link_shared_vlans = geni_props.get("link_shared_vlans", [])
        # XXX (EK): allow links with more than 2 interface_refs
        # first two endpoints are used
        if len(interface_refs) >= 2:
            hrefs = []
            for interface in interface_refs:
                sliver_id = None
                client_id = None
                
                if rspec_type == RSpec3Decoder.RSpecManifest:
                    sliver_id = interface.get("sliver_id", None)
                    client_id = interface.get("client_id", None)
                    element = None
                    if not sliver_id and not client_id:
                        raise UNISDecoderException("Not valid Link" + etree.tostring(doc, pretty_print=True))
                    interface_id = interface.get("client_id", None)
                    if sliver_id:
                        element = self._find_sliver_id(interface_id, "interface")
                    if client_id and not element:
                        element = self._find_client_id(client_id, "interface")
                else:
                    interface_id = interface.get("component_id", None)
                    if not interface_id:
                        raise UNISDecoderException("Not valid Link" + etree.tostring(doc, pretty_print=True))
                    element = self._find_component_id(interface_id, "interface")
                    if element is None:
                        self.log.warn("ref_doesnot_exist", interface=interface,
                            guid=self._guid)
                        return
                use_client_id = not not client_id
                hrefs.append(self._make_self_link(element, rspec_type=rspec_type, use_client_id=use_client_id))
            link["directed"] = False
            link["endpoints"] = [
                {
                    "href": hrefs[0],
                    "rel": "full"
                },
                {
                    "href": hrefs[1],
                    "rel": "full"
                }
            ]
        # ProtoGENI lets you add "LAN" nodes
        # links with client_id "lanX" are basically switches
        elif len(interface_refs) > 2:
            lan_node = {}
            lan_node["$schema"] = UNISDecoder.SCHEMAS["node"]
            lan_node["name"] = link["name"]
            lan_node["urn"] = RSpec3Decoder.rspec_create_urn(slice_urn+"+node+"+link["name"])
            lan_node["id"] = self.geni_urn_to_id(slice_urn+"_node_"+link["name"])            

            # Make a node
            # Make fake ports on this node
            # Create links for each interface_ref to these ports for each client_id
            
            # XXX (EK): For now we just make one end point so parsing continues
            # hacked conditional above
        # shared vlans, or in exogeni case, you get just one interface_ref *sigh*
        elif len(link_shared_vlans) or (len(interface_refs) == 1):
            hrefs = []
            if len(interface_refs):
                for interface in interface_refs:
                    interface_id = interface.get("sliver_id", None)
                    client_id = interface.get("client_id", None)
                    element = None
                    if not interface_id and not client_id:
                        raise UNISDecoderException("Not valid Link" + etree.tostring(doc, pretty_print=True))
                    interface_id = interface.get("client_id", None)
                    if sliver_id:
                        element = self._find_sliver_id(interface_id, "interface")
                    if client_id and not element:
                        element = self._find_client_id(client_id, "interface")                
                    if element is None:
                        self.log.warn("ref_doesnot_exist", interface=interface,
                                      guid=self._guid)
                        return
                    use_client_id = not not client_id
                    hrefs.append(self._make_self_link(element, rspec_type=rspec_type, use_client_id=use_client_id))

            for shared_vlan in link_shared_vlans:
                if "name" in shared_vlan:
                    hrefs.append("link to %s endpoint" % shared_vlan["name"])
                else:
                    hrefs.append("unresolveable sharedvlan endpoint")
            
            if not link_shared_vlans:
                hrefs.append("unresolveable sharedvlan endpoint")

            link["directed"] = False
            link["endpoints"] = [
                {
                    "href": hrefs[0],
                    "rel": "full"
                },
                {
                    "href": hrefs[1],
                    "rel": "full"
                }
            ]
        else:
            # Try to find the link's endpoints in the properties
            link_props = geni_props.get('properties', None)
            if link_props is not None:
                # Assume default endpoints at first
                ends_id = [
                    {"source_id": None, "dest_id": None, "props": {}},
                    {"source_id": None, "dest_id": None, "props": {}},
                ]
                # Then make sure that all for all properties there is at most two endpoints
                for prop in link_props:
                    source_id = prop.get("source_id", None) 
                    dest_id = prop.get("dest_id", None) 
                    if ends_id[0]["source_id"] is None and source_id is not None and dest_id is not None:
                        ends_id[0]["source_id"] = source_id
                        ends_id[0]["dest_id"] = dest_id
                        ends_id[0]["props"].update(prop)
                    elif ends_id[1]["source_id"] is None and source_id is not None and dest_id is not None:
                        ends_id[1]["source_id"] = source_id
                        ends_id[1]["dest_id"] = dest_id
                        ends_id[1]["props"].update(prop)
                    elif source_id is None or dest_id is None:
                        raise UNISDecoderException("Incomplete link property")
                    else:
                        if {"source_id": source_id, "dest_id": dest_id} not in ends_id:
                            raise UNISDecoderException("end matching source and dest")
                # Check if the link is unidirectional or bidirectional
                unidirectional = {"source_id": None, "dest_id": None} in ends_id
                
                if unidirectional is True:
                    ends_id.remove({"source_id": None, "dest_id": None})
                    link["directed"] = True
                    src_port = self._find_component_id(ends_id[0]["source_id"], "interface")
                    dst_port = self._find_component_id(ends_id[0]["dest_id"], "interface")
                    
                    if src_port is None:
                        src_port = ends_id[0]["source_id"]
                    else:
                        src_port = self._make_self_link(src_port)
                        
                    if dst_port is None:
                        dst_port = ends_id[0]["dest_id"]
                    else:
                        dst_port = self._make_self_link(dst_port)
                    
                    
                    link["endpoints"] = {
                        "source": {
                            "href": self._make_self_link(src_port),
                            "rel": "full"
                        },
                        "sink": {
                            "href": self._make_self_link(dst_port),
                            "rel": "full"
                        }
                    }
                    if "capacity" in ends_id[0]["props"]:
                        link["capacity"] = float(ends_id[0]["props"]["capacity"])
                else:
                    link["directed"] = False
                    src_port = self._find_component_id(ends_id[0]["source_id"], "interface")
                    dst_port = self._find_component_id(ends_id[0]["dest_id"], "interface")
                    if src_port is None:
                        src_port = ends_id[0]["source_id"]
                    else:
                        src_port = self._make_self_link(src_port)
                        
                    if dst_port is None:
                        dst_port = ends_id[0]["dest_id"]
                    else:
                        dst_port = self._make_self_link(dst_port)
                    
                    link["endpoints"] = [
                        {
                            "href": src_port,
                            "rel": "full"
                        },
                        {
                            "href": dst_port,
                            "rel": "full"
                        }
                    ]
                    # Check if the links has symmetric capacity
                    if ends_id[0]["props"].get("capacity", None) == \
                        ends_id[1]["props"].get("capacity", None) and \
                        ends_id[1]["props"].get("capacity", None) is not None:
                        link["capacity"] = float(ends_id[0]["props"]["capacity"])
        
        if link.get("endpoints", None) is None:
            raise UNISDecoderException(
                "Cannot accept link with no endpoints in %s " % \
                etree.tostring(doc, pretty_print=True)
            )
        
        if out == self._parent_collection:
            if "links" not in out:
                out["links"] = []
            out["links"].append(link)
            pointer = self._jsonpointer_path + \
                "/links/%d" % (len(out["links"]) - 1)
        else:
            if "links" not in collection:
                collection["links"] = []
            collection["links"].append(link)
            if "links" not in out:
                out["links"] = []
            pointer = self._jsonpointer_path + \
                "/links/%d" % (len(collection["links"]) - 1)
            out["links"].append({"href": pointer, "rel": "full"})
        
        if len(attrib) > 0:
            self.log.warn("unpares_attribute.warn", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self.log.debug("_encode_rspec_link.end",
            component_id=doc.attrib.get("component_id", None), guid=self._guid)
        return link
    
    def _encode_rspec_available(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_available.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        if "available" not in geni_props:
            geni_props["available"] = {}
        available = geni_props["available"]
        attrib = dict(doc.attrib)
        # From ad.rnc
        now = attrib.pop('now', None)
        
        if now is not None:
            available["now"] = self._parse_xml_bool(now)
            if available["now"]:
                parent["status"] = "AVAILABLE"
        if len(attrib) > 0:
            self.log.warn("unparesd_attributes",
                attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, available, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_available.end", guid=self._guid)
        return {"available": available}

    ### working function for new rspec tag, cloud
    def _encode_rspec_cloud(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_cloud.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        if "cloud" not in geni_props:
            geni_props["cloud"] = {}
        cloud = geni_props["cloud"]
        attrib = dict(doc.attrib)
        # From ad.rnc
        #now = attrib.pop('now', None)
        
        #if now is not None:
        #    available["now"] = self._parse_xml_bool(now)
        #    if available["now"]:
        #        parent["status"] = "AVAILABLE"
        if len(attrib) > 0:
            self.log.warn("unparesd_attributes",
                attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, cloud, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_cloud.end", guid=self._guid)
        return {"cloud": cloud}

    def _make_self_link(self, element, rspec_type=None, use_client_id=False):
        if element is None:
            raise UNISDecoderException("Cannot make self link to NONE")
        if rspec_type == RSpec3Decoder.RSpecManifest:
            urn = element.get("sliver_id", None) or element.get("client_id", None)
        else:
            urn = element.get("component_id", None)
        
        if not urn:
            raise UNISDecoderException("Cannot link to an element without URN or sliver_id or client_id")
        
        # First try cache
        urn = unquote(urn.strip())
        if urn in self._urn_cache:
            return self._urn_cache[urn]
       
        # TODO (AH) : Improve generating json paths
        #if rspec_type == RSpec3Decoder.RSpecManifest:
        #    jpath = "[?(@.properties.geni.sliver_id==\"%s\")]" % urn
        #else:
        #    jpath = "[?(@.urn==\"%s\")]" % urn
                
        #self._urn_cache[urn] = jpath
        #self._subsitution_cache[urn] = jpath
        #return
        
        # Try to construct xpath to make the lookup easier
        xpath = self._tree.getpath(element)
        
        peices = xpath.split("/")[2:]
        names_map = {
            "topology": "topolgies",
            "domain": "domains",
            "rspec": "domains",
            "network": "networks",
            "node": "nodes",
            "port": "ports",
            "interface": "ports",
            "link": "links",
            "path": "paths",
            "service": "services",
            "metadata": "metadata",
        }
        jpath = []
        add_urn = False
        collections = ["topolgies", "domains"]
        for p in peices:
            p = p[p.find(":") + 1:]
            if "[" in p:
                name, index = p.split("[")
                index = "[" + str(int(index.rstrip("]")) - 1) + "]"
            else:
                name = p
                index = ""
            if name not in names_map:
                raise UNISDecoderException("Unrecongized type '%s' in '%s'" % (name, xpath))
            if name not in collections:
                add_urn = True
                if len(jpath) > 0:
                    lastname = jpath[-1].split("[")[0]
                    if lastname not in collections:
                        jpath = jpath[:-1]
            if names_map[name] in collections and index == "":
                index = "[0]"
            jpath.append(names_map[name] + index)
        jpath =  "$." + ".".join(jpath)
        if add_urn:
            if jpath.endswith("]"):
                jpath = jpath[:jpath.rindex("[")]
            if rspec_type == RSpec3Decoder.RSpecManifest:
                if use_client_id:
                    jpath += "[?(@.properties.geni.client_id==\"%s\")]" % urn
                else:
                    jpath += "[?(@.properties.geni.sliver_id==\"%s\")]" % urn
            else:
                jpath += "[?(@.urn==\"%s\")]" % urn
        self._urn_cache[urn] = jpath
        self._subsitution_cache[urn] = jpath
        return jpath
    
    def _find_sliver_id(self, urn, component_type, try_hard=False):
        """
        Looks for the any element with sliver_id == urn and of type
        component_type. component_type examples: interface and node.
        This method trys all special cases I've seen and issues a
        warning log if the URN found but was not in the right format.
        """
        def escape_urn(u):
            return u.replace("/", "%2F").replace("#", "%23")
        
        if urn in self._sliver_id_cache:
            self.log.debug("_find_sliver_id.end", guid=self._guid, urn=urn)
            return self._sliver_id_cache[urn]
        self.log.debug("_find_sliver_id.start", guid=self._guid, urn=urn)
        if self._root is None:
            self.log.debug("_find_sliver_id.end", guid=self._guid, urn=urn)
            return None
        xpath = ".//rspec:%s[@sliver_id='%s']" % (component_type, urn)
        if try_hard == True:
            escaped_urn = escape_urn(urn)
            xpath = ".//rspec:%s[@sliver_id='%s' or @sliver_id='%s']" \
                % (component_type, urn, escaped_urn)
        result = self._root.xpath(xpath, namespaces={"rspec": RSpec3Decoder.ns_default})
        
        if len(result) > 1:
            self.log.debug("_find_sliver_id.end", guid=self._guid, urn=urn)
            raise UNISDecoderException("Found more than one node with the URN '%s'" % urn)
        elif len(result) == 1:
            result = result[0]
        else:
            result = None
        self._sliver_id_cache[urn] = result
        self.log.debug("_find_sliver_id.end", guid=self._guid, urn=urn)
        return result
    
    def _find_client_id(self, urn, component_type, try_hard=False):
        """
        Looks for the any element with client_id == urn and of type
        component_type. component_type examples: interface and node.
        This method trys all special cases I've seen and issues a
        warning log if the URN found but was not in the right format.
        """
        def escape_urn(u):
            return u.replace("/", "%2F").replace("#", "%23")
        
        self.log.debug("_find_client_id.start", guid=self._guid, urn=urn)
        if self._root is None:
            self.log.debug("_find_client_id.end", guid=self._guid, urn=urn)
            return None
        xpath = ".//rspec:%s[@client_id='%s']" % (component_type, urn)
        if try_hard == True:
            escaped_urn = escape_urn(urn)
            xpath = ".//rspec:%s[@client_id='%s' or @client_id='%s']" \
                % (component_type, urn, escaped_urn)
        result = self._root.xpath(xpath, namespaces={"rspec": RSpec3Decoder.ns_default})
        if len(result) > 1:
            self.log.debug("_find_client_id.end", guid=self._guid, urn=urn)
            raise UNISDecoderException("Found more than one node with the URN '%s'" % urn)
        elif len(result) == 1:
            result = result[0]
        else:
            result = None
        self.log.debug("_find_client_id.end", guid=self._guid, urn=urn)
        return result
    
    
    def _find_component_id(self, urn, component_type, try_hard=False):
        """
        Looks for the any element with component_id == urn and of type
        component_type. component_type examples: interface and node.
        This method trys all special cases I've seen and issues a
        warning log if the URN found but was not in the right format.
        """
        def escape_urn(u):
            return u.replace("/", "%2F").replace("#", "%23")
        
        if urn in self._component_id_cache:
            self.log.debug("_find_component_id.end", guid=self._guid, urn=urn)
            return self._component_id_cache[urn]
        self.log.debug("_find_component_id.start", guid=self._guid, urn=urn)
        if self._root is None:
            self.log.debug("_find_component_id.end", guid=self._guid, urn=urn)
            return None
        xpath = ".//rspec:%s[@component_id='%s']" % (component_type, urn)
        if try_hard == True:
            escaped_urn = escape_urn(urn)
            xpath = ".//rspec:%s[@component_id='%s' or @component_id='%s']" \
                % (component_type, urn, escaped_urn)
        result = self._root.xpath(xpath, namespaces={"rspec": RSpec3Decoder.ns_default})
        
        if len(result) > 1:
            self.log.debug("_find_component_id.end", guid=self._guid, urn=urn)
            raise UNISDecoderException("Found more than one node with the URN '%s'" % urn)
        elif len(result) == 1:
            result = result[0]
        else:
            result = None
        self._component_id_cache[urn] = result
        self.log.debug("_find_component_id.end", guid=self._guid, urn=urn)
        return result
    
    def _encode_rspec_sliver_type(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_sliver_type.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if 'sliver_type' not in geni_props:
            geni_props['sliver_type'] = {}
        sliver_type = geni_props['sliver_type']
        
        attrib = dict(doc.attrib)
        # From common.rnc
        name = attrib.pop('name', None)
        # From ad.rnc
        default = attrib.pop('default', None)
        
        if name is not None:
            sliver_type["name"] = name.strip()
        if default is not None:
            sliver_type["default"] = default.strip()
        
        if len(attrib) > 0:
            self.log.warn("unparesd_attributes", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, sliver_type, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_sliver_type.end", guid=self._guid)
        return {"sliver_type": sliver_type}
    
    def _encode_rspec_location(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_location.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "location" not in parent:
            parent["location"] = {}
        location = parent["location"]
       
        xml_attribs = dict(doc.attrib)
        schema_attribs = [
            # From common.rnc
            "country", "longitude", "latitude"
        ]
        location.update(dict(
                [
                    (name, xml_attribs.pop(name).strip()) \
                    for name in xml_attribs.keys() \
                    if name in schema_attribs
                ]
            )
        )
        # Convert values
        if location['longitude'] is not None:
            location['longitude'] = float(location['longitude'])
        if location['latitude'] is not None:
            location['latitude'] = float(location['latitude'])
        
        if len(xml_attribs) != 0:
            self.log.warn("unparesd_attributes",
                attribs=xml_attribs, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % xml_attribs)
        
        self._encode_children(doc, location, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_location.end", guid=self._guid)
        return {"location": location}
    
    def _encode_rspec_hardware_type(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_hardware_type.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "hardware_types" not in geni_props:
            geni_props["hardware_types"] = []
        hardware_types = geni_props["hardware_types"]
        hardware_type = {}
        
        attrib = dict(doc.attrib)
        # From common.rnc
        ## Exogeni Aggregates have an unknown node, which does not specify a hardware type 
        name = attrib.pop('name', None)
        
        if name:
            hardware_type['name'] = name.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, hardware_type, collection=collection, parent=parent, **kwargs)
        hardware_types.append(hardware_type)
        self.log.debug("_encode_rspec_hardware_type.end", guid=self._guid)
        return {"hardware_types": hardware_types}
    
    def _encode_rspec_disk_image(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_disk_type.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "disk_images" not in out:
            out["disk_images"] = []
        disk_images = out["disk_images"]
        disk_image = {}        
        
        xml_attribs = dict(doc.attrib)
        schema_attribs = [
            # From common.rnc
            "name", "os", "version", "description",
            # From ad.rnc
            "default",
            # somehow url is also allowed now
            "url",
        ]
        disk_image = dict(
            [
                (name, xml_attribs.pop(name).strip()) \
                for name in xml_attribs.keys() \
                if name in schema_attribs
            ]
        )
        if len(xml_attribs) != 0:
            self.log.warn("unparesd_attributes", attribs=xml_attribs, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % xml_attribs)
        
        self._encode_children(doc, disk_image, collection=collection,
            parent=parent, **kwargs)
        disk_images.append(disk_image)
        self.log.debug("_encode_rspec_disk_type.end", guid=self._guid)
        return {"disk_images": disk_images}
    
    def _encode_rspec_relation(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_relation.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if 'relations' not in geni_props:
            geni_props['relations'] = []
        relations = geni_props['relations']
        relation = {}
        
        attrib = dict(doc.attrib)
        # From common.rnc
        rtype = attrib.pop('type')
        # From ad.rnc
        component_id = attrib.pop('component_id', None)
        # From request.rnc
        client_id = attrib.pop('client_id', None)
        
        relation["type"] = rtype.strip()
        if component_id is not None:
            relation["component_id"] = component_id.strip()
            if "relations" not in parent:
                parent["relations"] = {}
            if relation["type"] not in parent["relations"]:
                parent["relations"][relation["type"]] = []
            parent["relations"][relation["type"]].append(
                {"href": '$.nodes[?(@.urn=="%s")]' % component_id, "rel": "full"}
            )
        if client_id is not None:
            relation["client_id"] = client_id.strip()
        
        if len(attrib) > 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, relation, collection=collection,
            parent=parent, **kwargs)
        relations.append(relation)
        self.log.debug("_encode_rspec_relation.end", guid=self._guid)
        return {"relations": relations}
    
    
    def _encode_rspec_link_type(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_link_type.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["link"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "link_types" not in geni_props:
            geni_props["link_types"] = []
        link_types = geni_props["link_types"]
        link_type = {}
        
        attrib = dict(doc.attrib)
        # From common.rnc
        name = attrib.pop('name')
        klass = attrib.pop('class', None)
        
        if name:
            link_type['name'] = name.strip()
        if klass:
            link_type['class'] = klass.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, link_type, collection=collection, parent=parent, **kwargs)
        link_types.append(link_type)
        self.log.debug("_encode_rspec_link_type.end", guid=self._guid)
        return {"link_types": link_types}
    
    def _encode_rspec_component_manager(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_component_manager.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["link"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "component_managers" not in geni_props:
            geni_props["component_managers"] = []
        component_managers = geni_props["component_managers"]
        component_manager = {}
        
        attrib = dict(doc.attrib)
        # From ad.rnc
        name = attrib.pop('name')
        
        if name:
            component_manager['name'] = name.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, component_manager, collection=collection, parent=parent, **kwargs)
        component_managers.append(component_manager)
        self.log.debug("_encode_rspec_component_manager.end", guid=self._guid)
        return {"component_managers": component_managers}
    
    def _encode_rspec_interface_ref(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_interface_ref.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["link"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "interface_refs" not in geni_props:
            geni_props["interface_refs"] = []
        interface_refs = geni_props["interface_refs"]
        interface_ref = {}
        
        attrib = dict(doc.attrib)
        
        # From ad.rnc and manifest.rnc
        component_id = attrib.pop('component_id', None)
        # From request.rnc
        client_id = attrib.pop('client_id', None)
        # From manifest.rnc
        sliver_id = attrib.pop('sliver_id', None)
        
        if component_id:
            interface_ref['component_id'] = unquote(component_id.strip())
        if client_id:
            interface_ref['client_id'] = client_id.strip()
        if sliver_id:
            interface_ref['sliver_id'] = sliver_id.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, interface_ref, collection=collection, parent=parent, **kwargs)
        interface_refs.append(interface_ref)
        self.log.debug("_encode_rspec_interface_ref.end", guid=self._guid)
        return {"interface_refs": interface_refs}

    def _encode_sharedvlan_link_shared_vlan(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_sharedvlan_link_shared_vlan.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["link"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]

        if "link_shared_vlans" not in geni_props:
            geni_props["link_shared_vlans"] = []
        shared_vlans = geni_props["link_shared_vlans"]
        shared_vlan = {}
        
        attrib = dict(doc.attrib)

        name = attrib.pop('name', None)
        vlantag = attrib.pop('vlantag', None)

        if name:
            shared_vlan['name'] = name
        if vlantag:
            shared_vlan['vlantag'] = vlantag

        
        self._encode_children(doc, shared_vlan, collection=collection, parent=parent, **kwargs)
        shared_vlans.append(shared_vlan)
        return {"link_shared_vlans": shared_vlans}

    def _encode_rspec_property(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_property.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["link"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "properties" not in geni_props:
            geni_props["properties"] = []
        properties = geni_props["properties"]
        prop = {}
        
        attrib = dict(doc.attrib)
        # From common.rnc
        source_id = attrib.pop('source_id', None)
        dest_id = attrib.pop('dest_id', None)
        capacity = attrib.pop('capacity', None)
        latency = attrib.pop('latency', None)
        packet_loss = attrib.pop('packet_loss', None)
        
        if source_id:
            prop['source_id'] = source_id.strip()
        if dest_id:
            prop['dest_id'] = dest_id.strip()
        if capacity:
            prop['capacity'] = capacity.strip()
        if latency:
            prop['latency'] = latency.strip()
        if packet_loss:
            prop['packet_loss'] = packet_loss.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, prop, collection=collection, parent=parent, **kwargs)
        properties.append(prop)
        self.log.debug("_encode_rspec_property.end", guid=self._guid)
        return {"properties": prop}
        
    def _encode_rspec_host(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_host.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) in [UNISDecoder.SCHEMAS["node"], UNISDecoder.SCHEMAS["port"]], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "hosts" not in geni_props:
            geni_props["hosts"] = []
        hosts = geni_props["hosts"]
        host = {}        
        
        attrib = dict(doc.attrib)
        # From manifest.rnc
        hostname = attrib.pop('name', None)
        
        if hostname:
            host['hostname'] = hostname.strip()
            parent["id"] = hostname
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, host, collection=collection, parent=parent, **kwargs)
        hosts.append(host)
        self.log.debug("_encode_rspec_host.end", guid=self._guid)
        return {'hosts': hosts}
    
    def _encode_rspec_ip(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_ip.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["port"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "ip" not in geni_props:
            geni_props["ip"] = {}
        ip = geni_props["ip"]
        
        attrib = dict(doc.attrib)
        # From common.rnc
        address = attrib.pop('address')
        netmask = attrib.pop('netmask', None)
        ip_type = attrib.pop('type', None)
        
        if address:
            ip['address'] = address.strip()
        if netmask:
            ip['netmask'] = netmask.strip()
        if ip_type:
            ip['type'] = ip_type.strip().lower()
        else:
            ip['type'] = "ipv4"
        
        parent["address"] = {
            "address": ip['address'],
            "type": ip['type'],
        }
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, ip, collection=collection, parent=parent, **kwargs)
        self.log.debug("_encode_rspec_ip.end", guid=self._guid)
        return {'ip': ip}

    def _encode_rspec_services(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_services.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) in [UNISDecoder.SCHEMAS["node"], UNISDecoder.SCHEMAS["port"]], \
            "Found parent '%s'." % (parent.get("$schema", None))
        
        service = {}
        attrib = dict(doc.attrib)
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, service, collection=collection, parent=parent, **kwargs)
        self.log.debug("_encode_rspec_services.end", guid=self._guid)
        return service
    
    def _encode_rspec_login(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_login.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) in [UNISDecoder.SCHEMAS["node"], UNISDecoder.SCHEMAS["port"]], \
            "Found parent '%s'." % (parent.get("$schema", None))

        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "logins" not in geni_props:
            geni_props["logins"] = []
        logins = geni_props["logins"]
        
        login = {}
        attrib = dict(doc.attrib)
        
        # From common.rnc
        auth = attrib.pop('authentication', None)
        hostname = attrib.pop('hostname', None)
        port = attrib.pop('port', None)
        username = attrib.pop('username', None)
        if auth:
            login['authentication'] = auth.strip()
        if hostname:
            login['hostname'] = hostname.strip()
        if port:
            login['port'] = port.strip()
        if username:
            login['username'] = username.strip()

        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, login, collection=collection, parent=parent, **kwargs)
        logins.append(login)
        self.log.debug("_encode_rspec_login.end", guid=self._guid)
        return {"logins": logins}
    
    ##TODO : check if lambda can be used.
    def foam_urn_to_nodeid(self, urn):
        return urn[urn.rfind('foam'):].translate(None, ':').replace('+', '_')

    def foam_urn_to_portid(self, urn, name, num):
        return urn[urn.rfind('foam'):].translate(None, ':').replace('+', '_')+'_'+name+'_'+num

    ### function for new foam tag, location 
    def _encode_foam_datapath(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_datapath.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["domain"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        node = {}
        node["$schema"] = UNISDecoder.SCHEMAS["node"]
        node['status'] = "AVAILABLE"
        if "nodes" not in collection:
            collection["nodes"] = []
        if "properties" not in node:
            node["properties"] = {}
        if self.geni_ns not in node["properties"]:
            node["properties"][self.geni_ns] = {}

        geni_props = node["properties"][self.geni_ns]

        attrib = dict(doc.attrib)
        dpid = attrib.pop('dpid', None)
        component_id = attrib.pop('component_id', None)
        component_manager_id = attrib.pop('component_manager_id', None)
        if dpid is not None:
            node['dpid'] = dpid.translate(None, ':') 
        if component_id is not None:
            geni_props['component_id'] = unquote(component_id.strip())
        if component_manager_id is not None:
            geni_props['component_manager_id'] = component_manager_id.strip()

        # Set URN, ID, and name
        rspec_type = kwargs.get("rspec_type", None)

        #TODO Findout the reason for this check
        #if rspec_type == RSpec3Decoder.RSpecADV:
        node["id"] = self.foam_urn_to_nodeid(geni_props['component_id'])
        node["urn"] = geni_props['component_id']

        if len(attrib) > 0:
            self.log.warn("unparesd_attributes",
                attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        #pdb.set_trace()
        self._encode_children(doc, node, collection=collection,
            parent=parent, **kwargs)

        collection["nodes"].append(node)
        self.log.debug("_encode_rspec_foam.end", guid=self._guid)
        return node

    ### function for new foam tag, location 
    def _encode_foam_location(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_location.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        if "location" not in out:
            out["location"] = {}
        location = out["location"]
        xml_attribs = dict(doc.attrib)
        schema_attribs = [
            # From common.rnc
            "country", "longitude", "latitude"
        ]
        location.update(dict(
                [
                    (name, xml_attribs.pop(name).strip()) \
                    for name in xml_attribs.keys() \
                    if name in schema_attribs
                ]
            )
        )
        # Convert values
        if location['longitude'] is not None:
            location['longitude'] = float(location['longitude'])
        if location['latitude'] is not None:
            location['latitude'] = float(location['latitude'])
        
        if len(xml_attribs) != 0:
            self.log.warn("unparesd_attributes",
                attribs=xml_attribs, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % xml_attribs)
        
        self._encode_children(doc, location, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_location.end", guid=self._guid)
        return {"location": location}

    ### function for new openflow tag, sliver 
    def _encode_foam_sliver(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_sliver.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)

        rspec_type = kwargs.get("rspec_type", None)
        #TODO check for rspec type
        attribs = dict(doc.attrib)

        ref = attribs.pop('ref')
        desc = attribs.pop('description')
        email = attribs.pop('email')
        
        if ref is not None:
            out['properties']['ref'] = ref 
        if desc is not None:
            out['properties']['description'] = desc 
        if email is not None:
            out['properties']['email'] = ref 

        #pdb.set_trace()
        
        if len(attribs) != 0:
            self.log.warn("unparesd_attributes",
                attribs=xml_attribs, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % xml_attribs)
        
        self._encode_children(doc, out, collection=collection,
            parent=parent, **kwargs)
        self.log.debug("_encode_rspec_sliver.end", guid=self._guid)
        return 

    ### function for new openflow tag,controller 
    def _encode_foam_controller(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_controller_.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)

        attribs = dict(doc.attrib)

        url = attribs.pop('url')
        pri = attribs.pop('type')
        
        if url is not None and pri is not None:
            key = 'controller' + '_' + pri
            out['properties'][key] = url

        self._encode_children(doc, out, collection=collection,
            parent=parent, **kwargs)

        self.log.debug("_encode_controller_.end", guid=self._guid)
        return 

    ### function for new openflow tag, group
    def _encode_foam_group(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_group.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        
        #schema doesn't have enry for groups, needs to be taken care of
        self._encode_children(doc, out, collection=collection,
            parent=parent, **kwargs)

        self.log.debug("_encode_foam_group.end", guid=self._guid)
        return 

    #Stub for packet match, should be extended.
    def _encode_foam_match(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_match.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        self.log.debug("_encode_foam_match.end", guid=self._guid)
        return 

    ### function for new foam tag, topo 
    def _encode_foam_topo(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_topo.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        
        topo = {}
        attrib = dict(doc.attrib)
        comp_id = attrib.pop('remote-component-id', None)
        port_name = attrib.pop('remote-port-name', None)
        desc = attrib.pop('desc', None)
        remote_hostname = attrib.pop('remote-hostname', None)

        if desc is not None:
            topo['desc'] = desc 
        if doc.tag is not None:
            tag = doc.tag
            topo['type'] = tag[tag.rfind('}')+1:]

        if comp_id is not None:
            topo['remote-component-id'] = comp_id 
        if port_name is not None:
            topo['remote-port-name'] = port_name 
        if remote_hostname is not None:
            topo['remote-hostname'] = remote_hostname

        out['properties']['topo']= topo
        self._encode_children(doc, topo, collection=collection,
            parent=parent, **kwargs)

        if len(attrib) > 0:
            self.log.warn("unparesd_attributes",
                attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)

        self.log.debug("_encode_foam_topo.end", guid=self._guid)
        return {'topo': topo}

    ### function for new foam tag, port 
    def _encode_foam_port(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_foam_port.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)

        port = {}
        port["$schema"] = UNISDecoder.SCHEMAS["port"]
        if "ports" not in collection:
            collection["ports"] = []
        if "properties" not in port:
            port["properties"] = {}

        attrib = dict(doc.attrib)
        num = attrib.pop('num', None)
        name = attrib.pop('name', None)

        if num is not None:
            port['properties']['num'] = num 
        if name is not None:
            port['properties']['name'] = name

        port['id'] = self.foam_urn_to_portid(out['urn'], name, num)
        self._encode_children(doc, port, collection=collection,
            parent=parent, **kwargs)

        if len(attrib) > 0:
            self.log.warn("unparesd_attributes",
                attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)

        collection["ports"].append(port)
        self.log.debug("_encode_foam_port.end", guid=self._guid)
        return port

    #An empty handler for opstate to remove errors, we do not have
    #useful info for UNIS from this tag as of now.
    def _encode_rspec_opstate(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_opstate.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        self.log.debug("_encode_rspec_opstate.end", guid=self._guid)
        return

    #A scaled down node handler for external ref (elements of an external AM)
    def _encode_rspec_external_ref(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_rspec_external_ref.start",
            component_id=doc.attrib.get("component_id", None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.nsmap['rspec'] in RSpec3Decoder.rspec3, \
            "Not valid element '%s'" % doc.tag
        node = {}
        node['status'] = "EXTERNAL"
        node["$schema"] = UNISDecoder.SCHEMAS["node"]
        if "nodes" not in collection:
            collection["nodes"] = []
        
        # Parse GENI specific properties
        if "properties" not in node:
            node["properties"] = {}
        if self.geni_ns not in node["properties"]:
            node["properties"][self.geni_ns] = {}
        geni_props = node["properties"][self.geni_ns]
        attrib = dict(doc.attrib)
        # From common.rnc
        # From ad.rnc & request.rnc
        component_id = attrib.pop('component_id', None)
        component_manager_id = attrib.pop('component_manager_id', None)
        
        if component_id is not None:
            geni_props['component_id'] = unquote(component_id.strip())
        if component_manager_id is not None:
            geni_props['component_manager_id'] = component_manager_id.strip()

        kwargs.pop("parent", None)
        self._encode_children(doc, node, collection=collection,
            parent=node, **kwargs)
        
        collection["nodes"].append(node)

        if len(attrib) > 0:
            print "GG UNPARSED"
            self.log.warn("unparesd_attributes", attribs=attrib,
                guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self.log.debug("_encode_rspec_external_ref.end",
            component_id=doc.attrib.get("component_id", None), guid=self._guid)
        return node 

    def _encode_gemini_node(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_gemini_node.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "gemini" not in geni_props:
            geni_props["gemini"] = {}
        gemini_props = geni_props["gemini"]
        
        attrib = dict(doc.attrib)
        # From common.rnc
        node_type = attrib.pop('type')
        
        if node_type:
            gemini_props['type'] = node_type.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, gemini_props, collection=collection, parent=parent, **kwargs)
        self.log.debug("_encode_gemini_node.end", guid=self._guid)
        return {'gemini': gemini_props}
        
    def _encode_gemini_monitor_urn(self, doc, out, collection, parent, **kwargs):
        self.log.debug("_encode_gemini_node.start", guid=self._guid)
        assert isinstance(out, dict)
        assert isinstance(parent, dict)
        assert parent.get("$schema", None) == UNISDecoder.SCHEMAS["node"], \
            "Found parent '%s'." % (parent.get("$schema", None))
        # Parse GENI specific properties
        if "properties" not in parent:
            parent["properties"] = {}
        if self.geni_ns not in parent["properties"]:
            parent["properties"][self.geni_ns] = {}
        geni_props = parent["properties"][self.geni_ns]
        
        if "gemini" not in geni_props:
            geni_props["gemini"] = {}
        gemini_props = geni_props["gemini"]
        
        attrib = dict(doc.attrib)
        # From common.rnc
        name = attrib.pop('name')
        
        if name:
            gemini_props['monitor_urn'] = name.strip()
        
        if len(attrib) != 0:
            self.log.warn("unparesd_attributes", attribs=attrib, guid=self._guid)
            sys.stderr.write("Unparsed attributes: %s\n" % attrib)
        
        self._encode_children(doc, gemini_props, collection=collection, parent=parent, **kwargs)
        self.log.debug("_encode_gemini_node.end", guid=self._guid)
        return {'gemini': gemini_props}


class PSDecoder(UNISDecoder):
    """Decodes perfSONAR topologies to UNIS format."""
    
    ctrl = "http://ogf.org/schema/network/topology/ctrlPlane/20080828/"
    nmtb = "http://ogf.org/schema/network/topology/base/20070828/"
    nmtl2 = "http://ogf.org/schema/network/topology/l2/20070828/"
    nmtl3 = "http://ogf.org/schema/network/topology/l3/20070828/"
    nmtl4 = "http://ogf.org/schema/network/topology/l4/20070828/"
    nml = "http://schemas.ogf.org/nml/base/201103"
    
    def __init__(self):
        super(PSDecoder, self).__init__()
        self._parent_collection = {}
        self._tree = None
        self._root = None
        self._jsonpointer_path = "#/"
        self._jsonpath_cache = {}
        self._urn_cache = {}
        self._ignored_namespaces = [PSDecoder.nml]
        # Resolving jsonpath is expensive operation
        # This cache keeps track of jsonpath used to replaced in the end
        # with jsonpointers
        self._subsitution_cache = {}
        
        self._handlers = {
            "{%s}%s" % (PSDecoder.nmtb, "topology") : self._encode_topology,
            "{%s}%s" % (PSDecoder.nmtb, "domain") : self._encode_domain,
            "{%s}%s" % (PSDecoder.nmtb, "node") : self._encode_node,
            "{%s}%s" % (PSDecoder.nmtb, "name") : self._encode_name,
            "{%s}%s" % (PSDecoder.nmtb, "hostName") : self._encode_name,
            "{%s}%s" % (PSDecoder.nmtb, "description") : self._encode_description,
            "{%s}%s" % (PSDecoder.nmtb, "location") : self._encode_location,
            "{%s}%s" % (PSDecoder.nmtb, "latitude") : self._encode_latitude,
            "{%s}%s" % (PSDecoder.nmtb, "longitude") : self._encode_longitude,
            "{%s}%s" % (PSDecoder.nmtb, "relation") : self._encode_relation,
            "{%s}%s" % (PSDecoder.nmtb, "idRef") : self._encode_idRef,
            
            
            "{%s}%s" % (PSDecoder.nmtl2, "port") : self._encode_port,
            "{%s}%s" % (PSDecoder.nmtl2, "name") : self._encode_name,            
            "{%s}%s" % (PSDecoder.nmtl2, "ifName") : self._encode_name,
            "{%s}%s" % (PSDecoder.nmtl2, "ifDescription") : self._encode_description,
            "{%s}%s" % (PSDecoder.nmtl2, "description") : self._encode_description,
            "{%s}%s" % (PSDecoder.nmtl2, "capacity") : self._encode_capacity,
            "{%s}%s" % (PSDecoder.nmtl2, "link") : self._encode_l2_link,
            
            "{%s}%s" % (PSDecoder.nmtl3, "port") : self._encode_port,
            "{%s}%s" % (PSDecoder.nmtl3, "name") : self._encode_name,
            "{%s}%s" % (PSDecoder.nmtl3, "ifName") : self._encode_name,
            "{%s}%s" % (PSDecoder.nmtl3, "ifDescription") : self._encode_description,
            "{%s}%s" % (PSDecoder.nmtl3, "description") : self._encode_description,
            "{%s}%s" % (PSDecoder.nmtl3, "capacity") : self._encode_capacity,
            "{%s}%s" % (PSDecoder.nmtl3, "ipAddress") : self._encode_address,
            "{%s}%s" % (PSDecoder.nmtl3, "address") : self._encode_address,
            "{%s}%s" % (PSDecoder.nmtl3, "netmask") : self._encode_netmask,
            
            "{%s}%s" % (PSDecoder.ctrl, "domain") : self._encode_domain,
            "{%s}%s" % (PSDecoder.ctrl, "node") : self._encode_node,
            "{%s}%s" % (PSDecoder.ctrl, "port") : self._encode_port,
            "{%s}%s" % (PSDecoder.ctrl, "link") : self._encode_ctrl_link,
            "{%s}%s" % (PSDecoder.ctrl, "remoteLinkId") : self._encode_remoteLinkId,
            "{%s}%s" % (PSDecoder.ctrl, "address") : self._encode_address,
            "{%s}%s" % (PSDecoder.ctrl, "capacity") : self._encode_capacity,
            "{%s}%s" % (PSDecoder.ctrl, "granularity") : self._encode_granularity,
            "{%s}%s" % (PSDecoder.ctrl, "minimumReservableCapacity") : self._encode_minimumReservableCapacity,
            "{%s}%s" % (PSDecoder.ctrl, "maximumReservableCapacity") : self._encode_maximumReservableCapacity,
            "{%s}%s" % (PSDecoder.ctrl, "trafficEngineeringMetric") : self._encode_trafficEngineeringMetric,
            "{%s}%s" % (PSDecoder.ctrl, "switchingCapabilityDescriptors") : self._encode_switchingCapabilityDescriptors,
            "{%s}%s" % (PSDecoder.ctrl, "SwitchingCapabilityDescriptors") : self._encode_switchingCapabilityDescriptors,
            "{%s}%s" % (PSDecoder.ctrl, "switchingcapType") : self._encode_switchingcapType,
            "{%s}%s" % (PSDecoder.ctrl, "encodingType") : self._encode_encodingType,
            "{%s}%s" % (PSDecoder.ctrl, "switchingCapabilitySpecificInfo") : self._encode_switchingCapabilitySpecificInfo,
            "{%s}%s" % (PSDecoder.ctrl, "capability") : self._encode_capability,
            "{%s}%s" % (PSDecoder.ctrl, "interfaceMTU") : self._encode_interfaceMTU,
            "{%s}%s" % (PSDecoder.ctrl, "vlanRangeAvailability") : self._encode_vlanRangeAvailability,
            "{%s}%s" % (PSDecoder.ctrl, "vlanTranslation") : self._encode_vlanTranslation,
        }
    
    @staticmethod
    def create_id(urn):
        new_id = urn.replace("urn:ogf:network:", "").replace(":", "_").replace("=", "_")
        new_id = new_id.replace("/", "_").replace("*", "")
        return quote(new_id)
 
    def encode(self, tree, **kwargs):
        self.log.debug("encode.start", guid=self._guid)
        out = {}
        self._parent_collection = out
        root = tree.getroot()
        self._tree = tree
        self._root = root
        if root.tag in self._handlers:
            self._handlers[root.tag](root, out, **kwargs)
        else:
            #pdb.set_trace()
            sys.stderr.write("No handler for: %s\n" % root.tag)
        self.log.debug("encode.end", guid=self._guid)
        sout = json.dumps(out)
        
        # This is an optimization hack to make every jsonpath a jsonpointer
        for urn, jpath in self._subsitution_cache.iteritems():
            if urn in self._jsonpath_cache:
                sout = sout.replace(jpath, self._jsonpath_cache[urn])
        out = json.loads(sout)
        return out
    
    def _parse_xml_bool(self, xml_bool):
        clean = xml_bool.strip().lower()
        map_bool = {"true": True, "false": False, "1": True, "0": False}
        if clean not in map_bool:
            self.log.error("not_valid_xml_boolean", value=xml_bool, guid=self._guid)
            return xml_bool
        else:
            return map_bool[clean]
    
    def _encode_topology(self, doc, out, **kwargs):
        self.log.debug("_encode_topology.start", guid=self._guid)
        assert isinstance(out, dict)
        urn = doc.attrib.get('id', None)
        if urn:
            out["urn"] = self._parse_urn(urn)
            out["id"] = PSDecoder.create_id(out["urn"])
        out["$schema"] = UNISDecoder.SCHEMAS["topology"]
        self._encode_children(doc, out, **kwargs)
        self.log.debug("_encode_topology.end", guid=self._guid)
        return out
    
    def _encode_domain(self, doc, out, **kwargs):
        self.log.debug("_encode_domain.start", urn=doc.attrib.get('id', None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}domain" % PSDecoder.nmtb,
            "{%s}domain" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        domain = {}
        domain["$schema"] = UNISDecoder.SCHEMAS["domain"]
        urn = doc.attrib.get('id', None)
        if urn:
            domain["urn"] = self._parse_urn(urn)
            domain["id"] = PSDecoder.create_id(domain["urn"])
            self._urn_cache[domain["urn"]] = doc
        
        if "domains" not in out:
            out["domains"] = []
        out["domains"].append(domain)
        domain_path = "domains/%d" % (len(out["domains"]) -1)
        self._jsonpointer_path += domain_path
        kwargs.pop("parent", None)
        self._encode_children(doc, domain, collection=domain, parent=domain, **kwargs)
        self._jsonpointer_path = self._jsonpointer_path[:self._jsonpointer_path.rindex(domain_path)]
        # Cache JSONPointer
        if urn:
            self._jsonpath_cache[domain["urn"]] = domain_path
        
        self.log.debug("_encode_domain.end", urn=doc.attrib.get('id', None), guid=self._guid)
        return domain

    def _encode_node(self, doc, out, collection=None, parent=None, **kwargs):
        self.log.debug("_encode_node.start",
            urn=doc.attrib.get('id', None), guid=self._guid)
        assert isinstance(out, dict)
        #node = Node(auto_id=False, auto_ts=False)
        node = {}
        node["$schema"] = UNISDecoder.SCHEMAS["node"]
        urn = doc.attrib.get('id', None)
        if urn:
            node["urn"] = self._parse_urn(urn)
            node["id"] = PSDecoder.create_id(node["urn"])
            self._urn_cache[node["urn"]] = doc
            
        kwargs.pop("parent", None)
        self._encode_children(doc, node, collection=collection, parent=node, **kwargs)    
        if "nodes" not in out:
            out["nodes"] = []
        out["nodes"].append(node)
        self.log.debug("_encode_node.end", urn=doc.attrib.get('id', None), guid=self._guid)
        return node

    def _encode_port(self, doc, out, collection=None, parent=None, **kwargs):
        self.log.debug("_encode_port.start",
            urn=doc.attrib.get('id', None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}port" % PSDecoder.nmtl2,
            "{%s}port" % PSDecoder.nmtl3,
            "{%s}port" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        if not collection:
            collection = self._parent_collection
        #port = Port(auto_id=False, auto_ts=False)
        port = {}
        port["$schema"] = UNISDecoder.SCHEMAS["port"]
        urn = doc.attrib.get('id', None)
        
        if urn:
            port["urn"] = self._parse_urn(urn)
            port["id"] = PSDecoder.create_id(port["urn"])
            self._urn_cache[port["urn"]] = doc
        
        if out == self._parent_collection:
            if "ports" not in out:
                out["ports"] = []
            out["ports"].append(port)
            pointer = self._jsonpointer_path + "/ports/%d" % (len(out["ports"]) - 1)
        else:
            if "ports" not in collection:
                collection["ports"] = []
            collection["ports"].append(port)
            if "ports" not in out:
                out["ports"] = []
            pointer = self._jsonpointer_path + "/ports/%d" % (len(collection["ports"]) - 1)
            out["ports"].append({"href": pointer, "rel": "full"})
        self._jsonpath_cache[port["urn"]] = pointer
        kwargs.pop("parent", None)
        self._encode_children(doc, port, collection=collection,
            parent=port, parent_port=pointer, **kwargs)
        self.log.debug("_encode_port.end",
            urn=doc.attrib.get('id', None), guid=self._guid)
        return port
    
    def _encode_name(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        name = doc.text.strip()
        out["name"] = name
        return name
    
    def _encode_description(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}description" % PSDecoder.nmtb,
            "{%s}description" % PSDecoder.nmtl2,
            "{%s}description" % PSDecoder.nmtl3,
            "{%s}ifDescription" % PSDecoder.nmtl2,
            "{%s}ifDescription" % PSDecoder.nmtl3,
        ], "Not valid element '%s'" % doc.tag
        if doc.text is None:
            return None
        description = doc.text.strip()
        out["description"] = description
        return description
    
    def _encode_location(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        location = {}
        out["location"] = location
        self._encode_children(doc, out, **kwargs)
        return location
    
    def _encode_latitude(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        latitude = doc.text.strip()
        if "location" not in out:
            out["location"] = {}
        out["location"]["latitude"] = float(latitude)
        return out["location"]["latitude"]
    
    def _encode_longitude(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        longitude = doc.text.strip()
        if "location" not in out:
            out["location"] = {}
        out["location"]["longitude"] = float(longitude)
        return out["location"]["longitude"]

    def _encode_capacity(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}capacity" % PSDecoder.ctrl,
            "{%s}capacity" % PSDecoder.nmtl2,
            "{%s}capacity" % PSDecoder.nmtl3,
        ], "Not valid element '%s'" % doc.tag
        capacity = doc.text.strip()
        out["capacity"] = self._parse_capacity(capacity)
        return out["capacity"]

    def _parse_urn(self, urn):
        new_urn = unquote(urn.strip())
        if new_urn != urn:
            self.log.warn("urn_escaped.", urn=urn, guid=self._guid)
        if "urn:ogf:network" in new_urn and ":domain=" not in new_urn:
            parts = new_urn.split(":")
            new_urn = ":".join(parts[0:3])
            if len(parts) >= 4:
                new_urn += ":domain=" + parts[3]
            if len(parts) >= 5:
                new_urn += ":node=" + parts[4]
            if len(parts) >= 6:
                new_urn += ":port=" + parts[5]
            if len(parts) >= 7:
                new_urn += ":link=" + parts[6]
            if len(parts) >= 8:
                new_urn += ":".join(parts[7:])
            if new_urn != urn:
                self.log.warn("urn_incomplete.", urn=urn, guid=self._guid)
        return new_urn

    def _parse_capacity(self, capacity):
        """Parse strings like 1Gpbs, 100Mpbs to floating number of bps"""
        capacity = str(capacity).lower()
        val = None
        try:
            val = float(capacity)
        except:
            if capacity.endswith("gbps"):
                val = float(capacity.strip("gbps")) * 1000000000
            elif capacity.endswith("mbps"):
                val = float(capacity.strip("mbps")) * 1000000
            elif capacity.endswith("kbps"):
                val = float(capacity.strip("kbps")) * 1000
            elif capacity.endswith("bps"):
                val = float(capacity.strip("kbps"))
            else:
                raise UNISDecoderException("Cannot parse capacity '%s'" \
                    % capacity)
        return int(val)
    
    def _encode_l2_link(self, doc, out, collection=None, parent_port=None, **kwargs):
        self.log.debug("_encode_l2_link.start", urn=doc.attrib.get('id', None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}link" % PSDecoder.nmtl2,
        ], "Not valid element '%s'" % doc.tag
        #link = Link(auto_id=False, auto_ts=False)
        link = {}
        link["$schema"] = UNISDecoder.SCHEMAS["link"]
        urn = doc.attrib.get('id', None)
        dir_type = doc.attrib.get('type', None)
        
        #parent_port = doc.parentNode.getAttribute('id')
        if urn:
            link["urn"] = self._parse_urn(urn)
            link["id"] = PSDecoder.create_id(link["urn"])
            self._urn_cache[link["urn"]] = doc
        
        if dir_type == "unidirectional":
            link['directed'] = True
        elif dir_type == "bidirectional":
            link['directed'] = False
            return # TODO handler bidirectional links
        else:
            link['directed'] = True
        if parent_port is None:
            self.log.warn("no_parent_port_for_link", urn=doc.attrib.get('id', None), guid=self._guid)
            if ":link" not in urn:
                self.log.fatal("no_parent_port_for_link_and_no_link_in_urn",
                    urn=doc.attrib.get('id', None), guid=self._guid)
                raise UNISDecoderException(
                    "no_parent_port_for_link_and_no_link_in_urn %s" + \
                    doc.attrib.get('id', None)
                )
            parent_port = urn.split(":link")[0]
        link['endpoints'] = [{"href": parent_port, "rel": "full"}]
        
        relation = doc.xpath("./nmtb:relation[@type='sibling']",
                    namespaces = {"nmtb": PSDecoder.nmtb})
        if not relation:
            raise UNISDecoderException(
                "Unable to find relation in L2 link: " + \
                doc.attrib.get('id', None)
            )
        relation = relation[0]
        idref = relation.find("{%s}%s" % (PSDecoder.nmtb, "idRef"))
        if idref is None:
            self.log.fatal("no_idRef", urn=doc.attrib.get('id', None), guid=self._guid)
            raise UNISDecoderException(
                "Unable to find relation idRef in L2 Link: " + \
                doc.attrib.get('id', None)
            )
        
        remote_port = self._parse_urn(idref.text).split(":link")[0]        
        # Make sure that the link is in the current doc
        # I don't why ESnet escapes some of the characters
        found_element = self._find_urn(remote_port, try_hard=True)
        if found_element is not None:
            remote_port = self._make_self_link(found_element)
        
        link['endpoints'].append({"href": remote_port, "rel": "full"})
        if link['directed'] == True:
            link['endpoints'] = {
                "source": link['endpoints'][0],
                "sink": link['endpoints'][1]
            }
        if collection is None:
            collection = out
        kwargs.pop("parent", None)
        self._encode_children(doc, link, collection=collection, parent=link,
            ref_type="port", **kwargs)
        
        if "links" not in collection:
            collection["links"] = []
        collection["links"].append(link)
        
        # Cache JSONPointer
        if urn:
            pointer = self._jsonpointer_path + "/links/%d" % (len(collection["links"]) -1)
            self._jsonpath_cache[link["urn"]] = pointer
        
        self.log.debug("_encode_l2_link.end", urn=doc.attrib.get('id', None), guid=self._guid)
        return link
    
    def _encode_ctrl_link(self, doc, out, collection=None, parent_port=None, **kwargs):
        self.log.debug("_encode_ctrl_link.start", urn=doc.attrib.get('id', None), guid=self._guid)
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}link" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        #link = Link(auto_id=False, auto_ts=False)
        link = {}
        link["$schema"] = UNISDecoder.SCHEMAS["link"]
        urn = doc.attrib.get('id', None)
        dir_type = doc.attrib.get('type', None)
        #parent_port = doc.parentNode.getAttribute('id')
        if urn:
            link["urn"] = self._parse_urn(urn)
            link["id"] = PSDecoder.create_id(link["urn"])
            self._urn_cache[link["urn"]] = doc
            
        if dir_type == "unidirectional":
            link['directed'] = True
        elif dir_type == "bidirectional":
            link['directed'] = False
        else:
            link['directed'] = True
        if parent_port is None:
            self.log.warn("no_parent_port_for_link", urn=doc.attrib.get('id', None), guid=self._guid)
            if ":link" not in urn:
                self.log.fatal("no_parent_port_for_link_and_no_link_in_urn",
                    urn=doc.attrib.get('id', None), guid=self._guid)
                raise UNISDecoderException("no_parent_port_for_link_and_no_link_in_urn %s" + doc.attrib.get('id', None))
            parent_port = urn.split(":link")[0]
        link['endpoints'] = [{"href": parent_port, "rel": "full"}]
        
        remote_link = doc.find("{%s}remoteLinkId" % PSDecoder.ctrl)
        if remote_link is None:
            self.log.fatal("no_idRef", urn=doc.attrib.get('id', None), guid=self._guid)
            raise UNISDecoderException("Unable to find remoteLinkId in CtrlPlane link: %s" % doc.attrib.get('id', None))
        
        # Make sure that the link is in the current doc
        remote_link = remote_link.text.strip()
        link_parts = remote_link.split(":")
        remote_port = ":".join(link_parts[:-1])
        
        if remote_link.endswith(':site') or remote_link.endswith(':link=site'):
            link['endpoints'].append({"href": remote_link, "rel": "full"})
        else:
            found_element = self._find_urn(remote_port, try_hard=True)
            if found_element is not None:
                # Convert xpath to json pointer to make it faster for eval
                selfRef = self._make_self_link(found_element)
                remote_port = '%s' % (selfRef)
            else:
                self.log.warn("remoteLinkID_not_found", urn=remote_link,
                    link=doc.attrib.get('id', None), guid=self._guid)
            link['endpoints'].append({"href": remote_port, "rel": "full"})
        if link['directed'] == True:
            link['endpoints'] = {
                "source": link['endpoints'][0],
                "sink": link['endpoints'][1]
            }
        if collection is None:
            collection = out
        kwargs.pop("parent", None)
        self._encode_children(doc, link, collection=collection, parent=link, ref_type="port", **kwargs)
        if "links" not in collection:
            collection["links"] = []
        collection["links"].append(link)
        
        # Cache JSONPointer
        if urn:
            pointer = self._jsonpointer_path + "/links/%d" % (len(collection["links"]) -1)
            self._jsonpath_cache[link["urn"]] = pointer
        
        self.log.debug("_encode_ctrl_link.end", urn=doc.attrib.get('id', None), guid=self._guid)
        return link
    
    def _make_self_link(self, element):
        urn = element.get("id", None)
        if not urn:
            raise UNISDecoderException("Cannot link to an element without URN")
        
        # First try cache
        urn = self._parse_urn(urn)
        if urn in self._jsonpath_cache:
            return self._jsonpath_cache[urn]
        
        # Try to construct xpath to make the lookup easier
        xpath = self._tree.getpath(element)
        peices = xpath.split("/")[2:]
        names_map = {
            "topology": "topolgies",
            "domain": "domains",
            "network": "networks",
            "node": "nodes",
            "port": "ports",
            "link": "links",
            "path": "paths",
            "service": "services",
            "metadata": "metadata",
        }
        jpath = []
        add_urn = False
        collections = ["topolgies", "domains"]
        for p in peices:
            p = p[p.find(":") + 1:]
            if "[" in p:
                name, index = p.split("[")
                index = "[" + str(int(index.rstrip("]")) - 1) + "]"
            else:
                name = p
                index = ""
            if name not in names_map:
                raise UNISDecoderException("Unrecongized type '%s' in '%s'" % (name, xpath))
            if name not in collections:
                add_urn = True
                if len(jpath) > 0:
                    lastname = jpath[-1].split("[")[0]
                    if lastname not in collections:
                        jpath = jpath[:-1]
            if names_map[name] in collections and index == "":
                index = "[0]"
            jpath.append(names_map[name] + index)
        jpath =  "$." + ".".join(jpath)
        if add_urn:
            if jpath.endswith("]"):
                jpath = jpath[:jpath.rindex("[")]
            jpath += "[?(@.urn=='%s')]" % urn        
        self._jsonpath_cache[urn] = jpath
        self._subsitution_cache[urn] = jpath
        return jpath
            
    def _find_urn(self, urn, try_hard=False):
        """
        Looks for the any element with id == urn.
        This method trys all special cases I've seen and issues a
        warning log if the URN found but was not in the right format.
        """
        def escape_urn(u):
            return u.replace("/", "%2F").replace("#", "%23")
        self.log.debug("_find_urn.start", guid=self._guid, urn=urn)
        if self._root is None:
            self.log.debug("_find_urn.end", guid=self._guid, urn=urn)
            return None
        parsed_urn = self._parse_urn(urn)
        if parsed_urn in self._urn_cache:
            self.log.debug("_find_urn.end", guid=self._guid, urn=urn)
            return self._urn_cache[parsed_urn]
        
        xpath = ".//*[@id='%s']" % urn
        if try_hard == True:
            escaped_urn = escape_urn(urn)
            xpath = ".//*[@id='%s' or @id='%s' or @id='%s']" % (urn, escaped_urn, parsed_urn)
        result = self._root.xpath(xpath)
        
        if len(result) > 1:
            self.log.warn("_duplicate_urns", guid=self._guid, urn=urn)
            result = result[0]
        elif len(result) == 1:
            result = result[0]
        else:
            result = None
        self._urn_cache[parsed_urn] = result
        self.log.debug("_find_urn.end", guid=self._guid, urn=urn)
        return result
    
    def _is_urn_in_doc(self, urn, try_hard=False):
        """Returns True if any element with id == urn.
        This method trys all special cases I've seen and issues a
        warning log if the URN found but was not in the right format.
        """
        ret = self._find_urn(urn, try_hard) is not None
        if not ret:
            self.log.warn("urn_not_found.", urn=urn, guid=self._guid)
        return ret 

    def _encode_relation(self, doc, out, collection=None, parent=None, **kwargs):
        assert isinstance(out, dict)
        rel_type = doc.attrib.get('type')
        if "relations" not in parent:
            parent["relations"] = {}
        if rel_type not in out["relations"]:
            parent["relations"][rel_type] = []
        self._encode_children(doc, out["relations"][rel_type], collection=collection, parent=parent, **kwargs)
        return out["relations"][rel_type]
    
    def _encode_idRef(self, doc, out, **kwargs):
        assert isinstance(out, list)
        assert doc.tag in [
            "{%s}idRef" % PSDecoder.nmtb,
        ], "Not valid element '%s'" % doc.tag
        idRef = doc.text.strip()
        # Make sure that the link is in the current doc
        found_element = self._find_urn(idRef, try_hard=True)
        if found_element is not None:
            # Convert xpath to json pointer to make it faster for eval
            selfRef = self._make_self_link(found_element)
            idRef = '%s' % (selfRef)
        out.append({"href": idRef, "rel": "full"})
        return idRef
        
    def _encode_address(self, doc, out, parent, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}address" % PSDecoder.ctrl,
            "{%s}address" % PSDecoder.nmtl3,
            "{%s}ipAddress" % PSDecoder.nmtl3,
        ], "Not valid element '%s'" % doc.tag
        # In UNIS only ports has addresses
        if parent.get("$schema", "") != UNISDecoder.SCHEMAS["port"]:
            self.log.warn("ignore_address_not_port", address=doc.text, guid=self._guid)
            return
        if "address" not in parent:
            parent["address"] = {}
        address = doc.text.strip()
        address_type = doc.attrib.get("type", "").lower()
        if address_type == "":
            if UNISDecoder.is_valid_ipv4(address):
                address_type = "ipv4"
            elif UNISDecoder.is_valid_ipv6(address):
                address_type = "ipv6"
            else:
                address_type = "hostname"
        parent["address"] = {"type": address_type, "address": address}
        return parent["address"]
    
    def _encode_netmask(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if "properties" not in out:
            out["properties"] = {}
        if "ip" not in out["properties"]:
            out["properties"]["ip"] = {}
        netmask = doc.text.strip()
        out["properties"]["ip"]["netmask"] = netmask
        return netmask
    
    def _encode_granularity(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}granularity" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        if doc.text is None:
            return
        if "properties" not in out:
            out["properties"] = {}
        if "ctrlPlane" not in out["properties"]:
            out["properties"]["ctrlPlane"] = {}
        granularity = doc.text.strip()
        out["properties"]["ctrlPlane"]["granularity"] = self._parse_capacity(granularity)
        return out["properties"]["ctrlPlane"]["granularity"]
    
    def _encode_minimumReservableCapacity(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return
        if "properties" not in out:
            out["properties"] = {}
        if "ctrlPlane" not in out["properties"]:
            out["properties"]["ctrlPlane"] = {}
        minimumReservableCapacity = doc.text.strip()
        out["properties"]["ctrlPlane"]["minimumReservableCapacity"] = self._parse_capacity(minimumReservableCapacity)
        return out["properties"]["ctrlPlane"]["minimumReservableCapacity"]
    
    def _encode_maximumReservableCapacity(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return
        if "properties" not in out:
            out["properties"] = {}
        if "ctrlPlane" not in out["properties"]:
            out["properties"]["ctrlPlane"] = {}
        maximumReservableCapacity = doc.text.strip()
        out["properties"]["ctrlPlane"]["maximumReservableCapacity"] = self._parse_capacity(maximumReservableCapacity)
        return out["properties"]["ctrlPlane"]["maximumReservableCapacity"]
    
    def _encode_trafficEngineeringMetric(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return
        if "properties" not in out:
            out["properties"] = {}
        if "ctrlPlane" not in out["properties"]:
            out["properties"]["ctrlPlane"] = {}
        trafficEngineeringMetric = doc.text.strip()
        out["properties"]["ctrlPlane"]["trafficEngineeringMetric"] = self._parse_capacity(trafficEngineeringMetric)
        return out["properties"]["ctrlPlane"]["trafficEngineeringMetric"]
    
    def _encode_switchingCapabilityDescriptors(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if "properties" not in out:
            out["properties"] = {}
        if "ctrlPlane" not in out["properties"]:
            out["properties"]["ctrlPlane"] = {}
        descriptors = {}
        out["properties"]["ctrlPlane"]["switchingCapabilityDescriptors"] = descriptors
        self._encode_children(doc, descriptors, **kwargs)
        return descriptors
    
    def _encode_switchingcapType(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return None
        switchingcapType = doc.text.strip()
        out["switchingcapType"] = switchingcapType
        return switchingcapType
    
    def _encode_encodingType(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}encodingType" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        if doc.text is None:
            return None
        encodingType = doc.text.strip()
        out["encodingType"] = encodingType
        return encodingType
    
    def _encode_switchingCapabilitySpecificInfo(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        info = {}
        out["switchingCapabilitySpecificInfo"] = info
        self._encode_children(doc, info, **kwargs)
        return info
    
    def _encode_capability(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}capability" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        if doc.text is None:
            return None
        capability = doc.text.strip()
        out["capability"] = capability
        return capability
    
    def _encode_interfaceMTU(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        assert doc.tag in [
            "{%s}interfaceMTU" % PSDecoder.ctrl,
        ], "Not valid element '%s'" % doc.tag
        if doc.text is None:
            return None
        interfaceMTU = doc.text.strip()
        out["interfaceMTU"] = int(interfaceMTU)
        return out["interfaceMTU"]
    
    def _encode_vlanRangeAvailability(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return None
        vlanRangeAvailability = doc.text.strip()
        out["vlanRangeAvailability"] = vlanRangeAvailability
        return out["vlanRangeAvailability"]
    
    def _encode_vlanTranslation(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        if doc.text is None:
            return None
        vlanTranslation = doc.text.strip()
        map_bool = {"true": True, "false": False, "1": True, "0": False}
        if vlanTranslation.lower() not in map_bool:
            raise UNISDecoderException("Not valid boolean value '%s' of map_bool vlanTranslation" % vlanTranslation)
        out["vlanTranslation"] = map_bool[vlanTranslation]
        return out["vlanTranslation"]
    
    def _encode_remoteLinkId(self, doc, out, **kwargs):
        assert isinstance(out, dict)
        remote_link = doc.text.strip()
        urn = self._parse_urn(remote_link)
        # Make sure that the link is in the current doc
        # I don't why ESnet escapes some of the characters
        found_element = self._find_urn(urn, try_hard=True)
        if found_element is not None:
            # Convert xpath to json pointer to make it faster for eval
            selfRef = self._make_self_link(found_element)
            href = '%s' % (selfRef)
        else:
            href = urn
        relation = {"href": href, "rel": "full"}
        if "relations" not in out:
            out["relations"] = {}
        if "sibling" not in out["relations"]:
            out["relations"]["sibling"] = []
        out["relations"]["sibling"].append(relation)
        return relation
    
    def _encode_children(self, doc, out, **kwargs):
        """Iterates over the all child nodes and process and call the approperiate
        handler for each one."""
        for child in doc.iterchildren():
            if child.tag is etree.Comment:
                continue
            if child.nsmap.get(child.prefix, None) in self._ignored_namespaces:
                continue
            self.log.debug("_encode_children.start", child=child.tag, guid=self._guid)
            if child.tag in self._handlers:
                self._handlers[child.tag](child, out, **kwargs)
            else:
                #pdb.set_trace()
                sys.stderr.write("No handler for: %s\n" % child.tag)
                self.log.error("no handler for '%s'" % child.tag, child=child.tag , guid=self._guid)
            self.log.debug("_encode_children.end", child=child.tag, guid=self._guid)                


def setup_logger(filename="unisencoder.log"):
    logging.setLoggerClass(nllog.BPLogger)
    log = logging.getLogger(nllog.PROJECT_NAMESPACE)
    handler = logging.FileHandler(filename)
    log.addHandler(handler)
    #log.addHandler(logging.StreamHandler())
    log.setLevel(logging.DEBUG)
    
def make_envelope(content):
    envelope = """
    <SOAP-ENV:Envelope xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
    <SOAP-ENV:Header/>
    <SOAP-ENV:Body>
        %s
    </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """ % content
    return envelope

def send_receive(url, envelope):
    req = urllib2.Request(url=url, data=envelope,
        headers={
            'Content-type': 'text/xml; charset="UTF-8"',
            'SOAPAction': 'http://ggf.org/ns/nmwg/base/2.0/message/'
        }
    )
    f = urllib2.urlopen(req)
    return f.read()
    
    
def pull_topology(url):
    query = """
    <nmwg:message type="TSQueryRequest" id="msg1" xmlns:nmwg="http://ggf.org/ns/nmwg/base/2.0/" xmlns:xquery="http://ggf.org/ns/nmwg/tools/org/perfsonar/service/lookup/xquery/1.0/">
        <nmwg:metadata id="meta1">
        <nmwg:eventType>http://ggf.org/ns/nmwg/topology/20070809</nmwg:eventType>
    </nmwg:metadata>
    <nmwg:data metadataIdRef="meta1" id="d1" />
    </nmwg:message>
    """
    envelope = make_envelope(query)
    return send_receive(url, envelope)

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

def main():
    parser = argparse.ArgumentParser(
        description="Encodes RSpec V3 and the different perfSONAR's topologies to UNIS"
    )
    parser.add_argument('-t', '--type', required=True, type=str,
        choices=["rspec3", "ps"], help='Input type (rspec3 or ps)')
    parser.add_argument('-o', '--output', type=str, default=None,
        help='Output file')
    parser.add_argument('-l', '--log', type=str, default="unisencoder.log",
        help='Log file.')
    parser.add_argument('--slice_urn', type=str, default=None,
        help='Slice URN.')
    parser.add_argument('--slice_cred', type=str, default=None,
        help='Slice credential file (XML)')
    parser.add_argument('-m', '--component_manager_id', type=str, default=None,
        help='The URN of the component manager of the advertisment RSpec.')
    parser.add_argument('--indent', type=int, default=2,
        help='JSON output indent.')
    parser.add_argument('filename', type=str, help='Input file.')    
    args = parser.parse_args()
    
    setup_logger(args.log)
    
    if args.filename is None:
        in_file = sys.stdin
    else:
        in_file = open(args.filename, 'r')

    try:
        if args.slice_cred and args.slice_urn:
            raise Usage("Must specify only one of '--slice_urn' or '--slice_cred'")
        elif args.slice_cred:
            from sfa.trust.credential import Credential as GENICredential
            import hashlib
            try:
                cred = GENICredential(filename=args.slice_cred)
                slice_urn = cred.get_gid_object().get_urn()
                slice_uuid = cred.get_gid_object().get_uuid()
                if not slice_uuid:
                    slice_uuid = hashlib.md5(cred.get_gid_object().get_urn()).hexdigest()
                    slice_uuid = str(uuid.UUID(slice_uuid))
                else:
                    slice_uuid = str(uuid.UUID(int=slice_uuid))
            except Exception, msg:
                raise Usage(msg)
        else:
            slice_urn = args.slice_urn
            slice_uuid = None
    except Usage, err:
        print >>sys.stderr, err.msg
        return

    topology = etree.parse(in_file)
    in_file.close()
    
    if args.type == "rspec3":
        encoder = RSpec3Decoder()
        kwargs = dict(slice_urn=slice_urn,
                      slice_uuid=slice_uuid,
                      component_manager_id=args.component_manager_id)
    elif args.type == "ps":
        encoder = PSDecoder()
        kwargs = dict()
    
    topology_out = encoder.encode(topology, **kwargs)

    if args.output is None:
        out_file = sys.stdout
    else:
        out_file = open(args.output, 'w')
    
    json.dump(topology_out, fp=out_file, indent=args.indent)
    #print json.dump(topology_out, fp=sys.stdout, indent=args.indent)
    out_file.close()
    
if __name__ == '__main__':
    main()

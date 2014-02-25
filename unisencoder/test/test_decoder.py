#!/usr/bin/env python

import unittest2
from lxml import etree
from mock import Mock
from mock import patch
from unisencoder.decoder import UNISDecoder
from unisencoder.decoder import PSDecoder
from unisencoder.decoder import RSpec3Decoder


class UNISDecoderTest(unittest2.TestCase):
    def setUp(self):
        self.encoder = UNISDecoder()
    
    def test_encode(self):
        encode = lambda : self.encoder.encode("X")
        self.assertRaises(NotImplementedError, encode)
    
    def test_is_valid_ipv4(self):
        # Arrange
        ip1 = "10.10.10.10"
        ip1_expected = True
        ip2 = "300.10.10.10"
        ip2_expected = False
        ip3 = "hello"
        ip3_expected = False
        ip4 = "2001:cdba::3257:9652"
        ip4_expected = False
        # Act
        ret1 = UNISDecoder.is_valid_ipv4(ip1)
        ret2 = UNISDecoder.is_valid_ipv4(ip2)
        ret3 = UNISDecoder.is_valid_ipv4(ip3)
        ret4 = UNISDecoder.is_valid_ipv4(ip4)
        # Assert
        self.assertEqual(ret1, ip1_expected)
        self.assertEqual(ret2, ip2_expected)
        self.assertEqual(ret3, ip3_expected)
        self.assertEqual(ret4, ip4_expected)
    
    def test_is_valid_ipv6(self):
        # Arrange
        ip1 = "2001:cdba:0000:0000:0000:0000:3257:9652"
        ip1_expected = True
        ip2 = "2001:cdba:0:0:0:0:3257:9652"
        ip2_expected = True
        ip3 = "2001:cdba::3257:9652"
        ip3_expected = True
        ip4 = "10.10.10.10"
        ip4_expected = False
        ip5 = "10.10.10.10"
        ip5_expected = False
        # Act
        ret1 = UNISDecoder.is_valid_ipv6(ip1)
        ret2 = UNISDecoder.is_valid_ipv6(ip2)
        ret3 = UNISDecoder.is_valid_ipv6(ip3)
        ret4 = UNISDecoder.is_valid_ipv6(ip4)
        ret5 = UNISDecoder.is_valid_ipv6(ip5)
        # Assert
        self.assertEqual(ret1, ip1_expected)
        self.assertEqual(ret2, ip2_expected)
        self.assertEqual(ret3, ip3_expected)
        self.assertEqual(ret4, ip4_expected)

class PSDecoderTest(unittest2.TestCase):
    def setUp(self):
        self.encoder = PSDecoder()
        self.nmtb = "http://ogf.org/schema/network/topology/base/20070828/"        
        self.nmtl2 = "http://ogf.org/schema/network/topology/l2/20070828/"
        self.nmtl3 = "http://ogf.org/schema/network/topology/l3/20070828/"
        self.nmtl4 = "http://ogf.org/schema/network/topology/l4/20070828/"
        self.ctrl = "http://ogf.org/schema/network/topology/ctrlPlane/20080828/"
        self.rspec3 = "http://www.geni.net/resources/rspec/3"
        
        self.schemas = {
            'networkresource': 'http://unis.incntre.iu.edu/schema/20140214/networkresource#',
            'node': 'http://unis.incntre.iu.edu/schema/20140214/node#',
            'domain': 'http://unis.incntre.iu.edu/schema/20140214/domain#',
            'topology': 'http://unis.incntre.iu.edu/schema/20140214/topology#',
            'port': 'http://unis.incntre.iu.edu/schema/20140214/port#',
            'link': 'http://unis.incntre.iu.edu/schema/20140214/link#',
            'network': 'http://unis.incntre.iu.edu/schema/20140214/network#',
            'blipp': 'http://unis.incntre.iu.edu/schema/20140214/blipp#',
            'metadata': 'http://unis.incntre.iu.edu/schema/20140214/metadata#',
        }
    
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_topology(self, encode_children_mock):
        # Arrang
        nmtb_topology = etree.Element("{%s}topology" % self.nmtb)
        nmtb_topology.attrib["id"] = "nmtb_topo1"
        nmtb_out = {}
        # Act
        nmtb_out = self.encoder._encode_topology(nmtb_topology, nmtb_out)
        # Assert
        self.assertEqual(nmtb_out["urn"], "nmtb_topo1")
        self.assertEqual(nmtb_out["$schema"], self.schemas["topology"])
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_domain(self, encode_children_mock):
        # Arrang
        nmtb_domain = etree.Element("{%s}domain" % self.nmtb)
        nmtb_domain.attrib["id"] = "nmtb_domain"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_domain(nmtb_domain, nmtb_out)
        # Assert
        self.assertEqual(ret["id"], "nmtb_domain")
        self.assertEqual(ret["urn"], "nmtb_domain")
        self.assertEqual(ret["$schema"], self.schemas["domain"])
        self.assertEqual(nmtb_out, {"domains": [ret]})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_node(self, encode_children_mock):
        # Arrang
        nmtb_node = etree.Element("{%s}node" % self.nmtb)
        nmtb_node.attrib["id"] = "nmtb_node"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_node(nmtb_node, nmtb_out)
        # Assert
        self.assertEqual(ret["id"], "nmtb_node")
        self.assertEqual(ret["urn"], "nmtb_node")
        self.assertEqual(ret["$schema"], self.schemas["node"])
        self.assertEqual(nmtb_out, {"nodes": [ret]})
    
    def test_encode_name(self):
        # Arrang
        nmtb_name = etree.Element("{%s}name" % self.nmtb)
        nmtb_name.text = "nmtb_name"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_name(nmtb_name, nmtb_out)
        # Assert
        self.assertEqual(ret, "nmtb_name")
        self.assertEqual(nmtb_out, {"name": ret})
    
    def test_encode_description(self):
        # Arrang
        nmtb_description = etree.Element("{%s}description" % self.nmtb)
        nmtb_description.text = "nmtb_description"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_description(nmtb_description, nmtb_out)
        # Assert
        self.assertEqual(ret, "nmtb_description")
        self.assertEqual(nmtb_out, {"description": ret})
    
    def test_encode_latitude(self):
        # Arrang
        nmtb_latitude = etree.Element("{%s}latitude" % self.nmtb)
        nmtb_latitude.text = "111"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_latitude(nmtb_latitude, nmtb_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(nmtb_out, {"location": {"latitude": ret}})
    
    def test_encode_longitude(self):
        # Arrang
        nmtb_longitude = etree.Element("{%s}longitude" % self.nmtb)
        nmtb_longitude.text = "111"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_longitude(nmtb_longitude, nmtb_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(nmtb_out, {"location": {"longitude": ret}})

    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_port(self, encode_children_mock):
        # Arrang
        nmtl2_port = etree.Element("{%s}port" % self.nmtl2)
        nmtl2_port.attrib["id"] = "nmtb_port"
        nmtl2_out = {}
        # Act
        ret = self.encoder._encode_port(nmtl2_port, nmtl2_out)
        # Assert
        self.assertEqual(ret["urn"], "nmtb_port")
        self.assertEqual(ret["$schema"], self.schemas["port"])
        self.assertEqual(nmtl2_out, {"ports": [ret]})
    
    @patch.object(PSDecoder, '_parse_capacity', mocksignature=True)
    def test_encode_capacity(self, mock_parse_capacity):
        # Arrang
        nmtl2_capacity = etree.Element("{%s}capacity" % self.nmtl2)
        nmtl2_capacity.text = "111"
        mock_parse_capacity.return_value = 111
        nmtl2_out = {}
        # Act
        ret = self.encoder._encode_capacity(nmtl2_capacity, nmtl2_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(nmtl2_out, {"capacity": ret})
    
    def test_parse_capacity(self):
        # Arrang
        c1 = "111"
        c2 = "111bps"
        c3 = "111kbps"
        c4 = "111mbps"
        c5 = "111gbps"
        # Act
        ret1 = self.encoder._parse_capacity(c1)
        ret2 = self.encoder._parse_capacity(c2)
        ret3 = self.encoder._parse_capacity(c3)
        ret4 = self.encoder._parse_capacity(c4)
        ret5 = self.encoder._parse_capacity(c5)
        # Assert
        self.assertEqual(ret1, 111)
        self.assertEqual(ret2, 111)
        self.assertEqual(ret3, 111000)
        self.assertEqual(ret4, 111000000)
        self.assertEqual(ret5, 111000000000)

    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_l2_link(self, encode_children_mock):
        # Arrang
        urn1 = "urn:ogf:network:domain=d:node=n:port=p1:link=link1"
        urn2 = "urn:ogf:network:domain=d:node=n:port=p2:link=link2"
        nmtl2_link = etree.Element("{%s}link" % self.nmtl2)
        nmtl2_link.attrib["id"] = urn1
        nmtb_relation = etree.SubElement(nmtl2_link, "{%s}relation" % self.nmtb)
        nmtb_relation.attrib["type"] = "sibling"
        nmtb_idRef = etree.SubElement(nmtb_relation, "{%s}idRef" % self.nmtb)
        nmtb_idRef.text = urn2
        parent_port = "#/ports/0"
        collection = {}
        nmtl2_out = {}
        # Act
        ret = self.encoder._encode_l2_link(nmtl2_link, nmtl2_out, collection, parent_port)
        # Assert
        self.assertEqual(ret["urn"], urn1)        
        self.assertEqual(ret["$schema"], self.schemas["link"])
        self.assertEqual(ret["directed"], True)
        self.assertEqual(ret["endpoints"], {
                "source": {"href": parent_port, "rel": "full"},
                "sink": {"href": "urn:ogf:network:domain=d:node=n:port=p2", "rel": "full"},
            }
        )
        self.assertEqual(collection, {"links": [ret]})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_l2_link_no_parent(self, encode_children_mock):
        # Arrang
        urn1 = "urn:ogf:network:domain=d:node=n:port=p1:link=link1"
        urn2 = "urn:ogf:network:domain=d:node=n:port=p2:link=link2"
        nmtl2_link = etree.Element("{%s}link" % self.nmtl2)
        nmtl2_link.attrib["id"] = urn1
        nmtb_relation = etree.SubElement(nmtl2_link, "{%s}relation" % self.nmtb)
        nmtb_relation.attrib["type"] = "sibling"
        nmtb_idRef = etree.SubElement(nmtb_relation, "{%s}idRef" % self.nmtb)
        nmtb_idRef.text = urn2
        parent_port = None
        collection = None
        nmtl2_out = {}
        # Act
        ret = self.encoder._encode_l2_link(nmtl2_link, nmtl2_out, parent_port)
        # Assert
        self.assertEqual(ret["urn"], urn1)        
        self.assertEqual(ret["$schema"], self.schemas["link"])
        self.assertEqual(ret["directed"], True)
        self.assertEqual(ret["endpoints"], {
                "source": {"href": "urn:ogf:network:domain=d:node=n:port=p1", "rel": "full"},
                "sink": {"href": "urn:ogf:network:domain=d:node=n:port=p2", "rel": "full"},
            }
        )
        self.assertEqual(nmtl2_out, {"links": [ret]})
        self.assertEqual(collection, None)
        
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_relation(self, encode_children_mock):
        # Arrang
        nmtb_relation = etree.Element("{%s}relation" % self.nmtb)
        nmtb_relation.attrib["type"] = "sibling"
        nmtb_idRef = etree.SubElement(nmtb_relation, "{%s}idRef" % self.nmtb)
        nmtb_idRef.text = "nmtb_link2"
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_relation(nmtb_relation, nmtb_out, parent=nmtb_out)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, [])
        self.assertEqual(nmtb_out, {"relations": {"sibling": ret}})
    
    @patch.object(PSDecoder, '_find_urn', mocksignature=True)
    def test_encode_idRef(self, find_urn):
        # Arrange
        find_urn.return_value = None
        nmtb_idRef = etree.Element("{%s}idRef" % self.nmtb)
        nmtb_idRef.text = "nmtb_link2"
        nmtb_out = []
        # Act
        ret = self.encoder._encode_idRef(nmtb_idRef, nmtb_out)
        # Assert
        self.assertEqual(ret, 'nmtb_link2')
        self.assertEqual(nmtb_out, [{'href': ret, 'rel': 'full'}])
    
    def test_encode_address(self):
        # Arrang
        address1 = etree.Element("{%s}ipAddress" % self.nmtl3)
        address1.attrib["type"] = "ipv4"
        address1.text = "10.10.10.10"
        out1 = {"$schema": self.schemas["port"]}
        address2 = etree.Element("{%s}ipAddress" % self.nmtl3)
        address2.attrib["type"] = "ipv6"
        address2.text = "2607:f0d0:1002:51::4"
        out2 = {"$schema": self.schemas["port"]}
        address3 = etree.Element("{%s}address" % self.nmtl3)
        address3.text = "10.10.10.10"
        out3 = {"$schema": self.schemas["port"]}
        address4 = etree.Element("{%s}address" % self.nmtl3)
        address4.text = "2607:f0d0:1002:51::4"
        out4 = {"$schema": self.schemas["port"]}
        out5 = {"$schema": self.schemas["node"]}
        # Act
        ret1 = self.encoder._encode_address(address1, out1, parent=out1)
        ret2 = self.encoder._encode_address(address2, out2, parent=out2)
        ret3 = self.encoder._encode_address(address3, out3, parent=out3)
        ret4 = self.encoder._encode_address(address4, out4, parent=out4)
        ret5 = self.encoder._encode_address(address4, out5, parent=out5)
        # Assert
        self.assertEqual(ret1, {"type": "ipv4", "address": "10.10.10.10"})
        self.assertEqual(ret2, {"type": "ipv6", "address": "2607:f0d0:1002:51::4"})
        self.assertEqual(ret3, {"type": "ipv4", "address": "10.10.10.10"})
        self.assertEqual(ret4, {"type": "ipv6", "address": "2607:f0d0:1002:51::4"})
        self.assertEqual(ret5, None)
        self.assertEqual(out1, {"$schema": self.schemas["port"], "address": ret1})
        self.assertEqual(out2, {"$schema": self.schemas["port"], "address": ret2})
        self.assertEqual(out3, {"$schema": self.schemas["port"], "address": ret3})
        self.assertEqual(out4, {"$schema": self.schemas["port"], "address": ret4})
        self.assertEqual(out5, {"$schema": self.schemas["node"]})
    
    def test_encode_netmask(self):
        # Arrang
        nmtl3_netmask = etree.Element("{%s}netmask" % self.nmtl3)
        nmtl3_netmask.text = "255.255.255.252"
        nmtl3_out = {}
        # Act
        ret = self.encoder._encode_netmask(nmtl3_netmask, nmtl3_out)
        # Assert
        self.assertEqual(ret, "255.255.255.252")
        self.assertEqual(nmtl3_out, {"properties": {"ip": {"netmask": ret}}})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_ctrl_link(self, encode_children_mock):
        # Arrang
        urn1 = "urn:ogf:network:domain=d:node=n:port=p:link=link1"
        urn2 = "urn:ogf:network:domain=d:node=n:port=p:link=link2"
        ctrl_link = etree.Element("{%s}link" % self.ctrl)
        ctrl_link.attrib["id"] = urn1
        ctrl_remoteLink = etree.SubElement(ctrl_link, "{%s}remoteLinkId" % self.ctrl)
        ctrl_remoteLink.text = urn2
        parent_port = "#/ports/0"
        collection = {}
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_ctrl_link(ctrl_link, ctrl_out, collection, parent_port)
        # Assert
        self.assertEqual(ret["id"], "domain_d_node_n_port_p_link_link1")        
        self.assertEqual(ret["urn"], urn1)        
        self.assertEqual(ret["$schema"], self.schemas["link"])
        self.assertEqual(ret["directed"], True)
        self.assertEqual(ret["endpoints"], {
            "source": {"href": parent_port, "rel": "full"},
            "sink": {"href": urn2.split(":link")[0], "rel": "full"},
            }
        )
        self.assertEqual(collection, {"links": [ret]})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_ctrl_link_not_inside_port(self, encode_children_mock):
        # Arrang
        urn1 = "urn:ogf:network:domain=d:node=n:port=p:link=link1"
        urn2 = "urn:ogf:network:domain=d:node=n:port=p2:link=link2"
        ctrl_link = etree.Element("{%s}link" % self.ctrl)
        ctrl_link.attrib["id"] = urn1
        ctrl_remoteLink = etree.SubElement(ctrl_link, "{%s}remoteLinkId" % self.ctrl)
        ctrl_remoteLink.text = urn2
        parent_port = None
        collection = None
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_ctrl_link(ctrl_link, ctrl_out, collection, parent_port)
        # Assert
        self.assertEqual(ret["urn"], urn1)        
        self.assertEqual(ret["$schema"], self.schemas["link"])
        self.assertEqual(ret["directed"], True)
        self.assertEqual(ret["endpoints"], {
            "source": {"href": "urn:ogf:network:domain=d:node=n:port=p", "rel": "full"},
            "sink": {"href": urn2.split(":link")[0], "rel": "full"},
            }
        )
        self.assertEqual(ctrl_out, {"links": [ret]})
        self.assertEqual(collection, None)
    
    @patch.object(PSDecoder, '_parse_capacity', mocksignature=True)
    def test_encode_granularity(self, mock_parse_capacity):
        # Arrang
        ctrl_granularity = etree.Element("{%s}granularity" % self.ctrl)
        ctrl_granularity.text = "111"
        mock_parse_capacity.return_value = 111
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_granularity(ctrl_granularity, ctrl_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(ctrl_out, {'properties': {'ctrlPlane': {'granularity': ret}}})
    
    @patch.object(PSDecoder, '_parse_capacity', mocksignature=True)
    def test_encode_minimumReservableCapacity(self, mock_parse_capacity):
        # Arrang
        ctrl_minimumReservableCapacity = etree.Element("{%s}minimumReservableCapacity" % self.ctrl)
        ctrl_minimumReservableCapacity.text = "111"
        mock_parse_capacity.return_value = 111
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_minimumReservableCapacity(ctrl_minimumReservableCapacity, ctrl_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(ctrl_out, {'properties': {'ctrlPlane': {'minimumReservableCapacity': ret}}})
    
    @patch.object(PSDecoder, '_parse_capacity', mocksignature=True)
    def test_encode_maximumReservableCapacity(self, mock_parse_capacity):
        # Arrang
        ctrl_maximumReservableCapacity = etree.Element("{%s}maximumReservableCapacity" % self.ctrl)
        ctrl_maximumReservableCapacity.text = "111"
        mock_parse_capacity.return_value = 111
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_maximumReservableCapacity(ctrl_maximumReservableCapacity, ctrl_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(ctrl_out, {'properties': {'ctrlPlane': {'maximumReservableCapacity': ret}}})
    
    @patch.object(PSDecoder, '_parse_capacity', mocksignature=True)
    def test_encode_trafficEngineeringMetric(self, mock_parse_capacity):
        # Arrang
        ctrl_trafficEngineeringMetric = etree.Element("{%s}trafficEngineeringMetric" % self.ctrl)
        ctrl_trafficEngineeringMetric.text = "111"
        mock_parse_capacity.return_value = 111
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_trafficEngineeringMetric(ctrl_trafficEngineeringMetric, ctrl_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(ctrl_out, {'properties': {'ctrlPlane': {'trafficEngineeringMetric': ret}}})
        
    def test_encode_switchingcapType(self):
        # Arrang
        ctrl_switchingcapType = etree.Element("{%s}switchingcapType" % self.ctrl)
        ctrl_switchingcapType.text = "psc-4"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_switchingcapType(ctrl_switchingcapType, ctrl_out)
        # Assert
        self.assertEqual(ret, "psc-4")
        self.assertEqual(ctrl_out, {"switchingcapType": ret})
    
    def test_encode_encodingType(self):
        # Arrang
        ctrl_encodingType = etree.Element("{%s}encodingType" % self.ctrl)
        ctrl_encodingType.text = "packet"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_encodingType(ctrl_encodingType, ctrl_out)
        # Assert
        self.assertEqual(ret, "packet")
        self.assertEqual(ctrl_out, {"encodingType": ret})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_switchingCapabilityDescriptors(self, encode_children_mock):
        # Arrang
        ctrl_descriptors = etree.Element("{%s}switchingCapabilityDescriptors" % self.ctrl)
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_switchingCapabilityDescriptors(ctrl_descriptors, ctrl_out)
        # Assert
        self.assertEqual(ret, {})
        self.assertEqual(ctrl_out, {"properties": {"ctrlPlane": {"switchingCapabilityDescriptors": ret}}})
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_switchingCapabilitySpecificInfo(self, encode_children_mock):
        # Arrang
        ctrl_info = etree.Element("{%s}switchingCapabilitySpecificInfo" % self.ctrl)
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_switchingCapabilitySpecificInfo(ctrl_info, ctrl_out)
        # Assert
        self.assertEqual(ret, {})
        self.assertEqual(ctrl_out, {"switchingCapabilitySpecificInfo": ret})

    def test_encode_capability(self):
        # Arrang
        ctrl_capability = etree.Element("{%s}capability" % self.ctrl)
        ctrl_capability.text = "unimplemented"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_capability(ctrl_capability, ctrl_out)
        # Assert
        self.assertEqual(ret, "unimplemented")
        self.assertEqual(ctrl_out, {"capability": ret})

    def test_encode_interfaceMTU(self):
        # Arrang
        ctrl_interfaceMTU = etree.Element("{%s}interfaceMTU" % self.ctrl)
        ctrl_interfaceMTU.text = "111"
        ctrl_out = {}
        # Act encodingType
        ret = self.encoder._encode_interfaceMTU(ctrl_interfaceMTU, ctrl_out)
        # Assert
        self.assertEqual(ret, 111)
        self.assertEqual(ctrl_out, {"interfaceMTU": ret})
    
    def test_encode_vlanRangeAvailability(self):
        # Arrang
        ctrl_vlan = etree.Element("{%s}vlanRangeAvailability" % self.ctrl)
        ctrl_vlan.text = "2-908,910-918,920-4094"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_vlanRangeAvailability(ctrl_vlan, ctrl_out)
        # Assert
        self.assertEqual(ret, "2-908,910-918,920-4094")
        self.assertEqual(ctrl_out, {"vlanRangeAvailability": ret})
    
    def test_encode_vlanTranslation(self):
        # Arrang
        ctrl_vlan = etree.Element("{%s}vlanTranslation" % self.ctrl)
        ctrl_vlan.text = "true"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_vlanTranslation(ctrl_vlan, ctrl_out)
        # Assert
        self.assertEqual(ret, True)
        self.assertEqual(ctrl_out, {"vlanTranslation": ret})
        
    def test_parse_urn(self):
        # Arrang
        urn0 = "urn:ogf:network:domain=a.net:node=a:port=b:link=c"
        urn0_expected = "urn:ogf:network:domain=a.net:node=a:port=b:link=c"
        urn1 = "urn:ogf:network:a.net:a:b:c"
        urn1_expected = "urn:ogf:network:domain=a.net:node=a:port=b:link=c"
        urn2 = "urn:ogf:network:domain=a.net:node=a:port=c%2F1%2F0:link=xe-1%2F1%2F0.0%23%231"
        urn2_expected = "urn:ogf:network:domain=a.net:node=a:port=c/1/0:link=xe-1/1/0.0##1"
        # Act
        urn0_ret = self.encoder._parse_urn(urn0)
        urn1_ret = self.encoder._parse_urn(urn1)
        urn2_ret = self.encoder._parse_urn(urn2)
        # Assert
        self.assertEqual(urn0_ret, urn0_expected)
        self.assertEqual(urn1_ret, urn1_expected)
        self.assertEqual(urn2_ret, urn2_expected)
    
    @patch.object(PSDecoder, '_encode_children', mocksignature=True)
    def test_encode_location(self, encode_children_mock):
        # Arrang
        nmtb_location = etree.Element("{%s}location" % self.nmtb)
        nmtb_out = {}
        # Act
        ret = self.encoder._encode_location(nmtb_location, nmtb_out)
        # Assert
        self.assertEqual(ret, {})
        self.assertEqual(nmtb_out, {"location": ret})
    
    def test_find_urn(self):
        urn1 = "urn:ogf:network:domain=d:node=n:port=p"
        urn2 = "urn:ogf:network:domain=d:node=n:port=ge-1/2/0"
        urn3 = "urn:ogf:network:domain=d:node=n:port=ge-1/2/0:link=ge-2/0/0.0##134.55.218.125"
        urn4 = "urn:ogf:network:d:n:p"
        urn5 = "urn:ogf:network:domain=d:node=n:port=ge-1%2F2%2F0"
        urn6 = "urn:ogf:network:domain=d:node=n:port=ge-1%2F2%2F0:link=ge-2/0/0.0%23%23134.55.218.125"
        urn7 = "urn:ogf:network:d:n:ge-1%2F2%2F0"
        urn8 = "urn:ogf:network:domain=d:node=n:port=NotInThere"
        urn9 = "urn:ogf:network:d:n:NotInThere"
        urn10 = "urn:ogf:network:d:n:NotThere-1%2F2%2F0"
        root = etree.Element("{%s}topology" % self.nmtb)
        node1 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node1.attrib['id'] = urn1
        node2 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node2.attrib['id'] = urn2
        node3 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node3.attrib['id'] = urn3
        self.encoder._root = root
        # Act
        ret1 = self.encoder._find_urn(urn1, try_hard=True)
        self.encoder._urn_cache = {}
        ret2 = self.encoder._find_urn(urn2, try_hard=True)
        self.encoder._urn_cache = {}
        ret3 = self.encoder._find_urn(urn3, try_hard=True)
        self.encoder._urn_cache = {}
        ret4 = self.encoder._find_urn(urn4, try_hard=True)
        self.encoder._urn_cache = {}
        ret5 = self.encoder._find_urn(urn5, try_hard=True)
        self.encoder._urn_cache = {}
        ret6 = self.encoder._find_urn(urn6, try_hard=True)
        self.encoder._urn_cache = {}
        ret7 = self.encoder._find_urn(urn7, try_hard=True)
        self.encoder._urn_cache = {}
        ret8 = self.encoder._find_urn(urn8, try_hard=True)
        self.encoder._urn_cache = {}
        ret9 = self.encoder._find_urn(urn9, try_hard=True)
        self.encoder._urn_cache = {}
        ret10 = self.encoder._find_urn(urn10, try_hard=True)
        self.encoder._urn_cache = {}
        ret11 = self.encoder._find_urn(urn4, try_hard=False)
        self.encoder._urn_cache = {}
        ret12 = self.encoder._find_urn(urn5, try_hard=False)
        self.encoder._urn_cache = {}
        ret13 = self.encoder._find_urn(urn6, try_hard=False)
        self.encoder._urn_cache = {}
        ret14 = self.encoder._find_urn(urn7, try_hard=False)
        self.encoder._urn_cache = {}
        # Assert
        self.assertEqual(ret1, node1)
        self.assertEqual(ret2, node2)
        self.assertEqual(ret3, node3)
        self.assertEqual(ret4, node1)
        self.assertEqual(ret5, node2)
        self.assertEqual(ret6, node3)
        self.assertEqual(ret7, node2)
        self.assertEqual(ret8, None)
        self.assertEqual(ret9, None)
        self.assertEqual(ret10, None)
        self.assertEqual(ret11, None)
        self.assertEqual(ret12, None)
        self.assertEqual(ret13, None)
        self.assertEqual(ret14, None)
    
    def test_is_urn_in_doc(self):
        # Arrang
        urn1 = "urn:ogf:network:domain=d:node=n:port=p"
        urn2 = "urn:ogf:network:domain=d:node=n:port=ge-1/2/0"
        urn3 = "urn:ogf:network:domain=d:node=n:port=ge-1/2/0:link=ge-2/0/0.0##134.55.218.125"
        urn4 = "urn:ogf:network:d:n:p"
        urn5 = "urn:ogf:network:domain=d:node=n:port=ge-1%2F2%2F0"
        urn6 = "urn:ogf:network:domain=d:node=n:port=ge-1%2F2%2F0:link=ge-2/0/0.0%23%23134.55.218.125"
        urn7 = "urn:ogf:network:d:n:ge-1%2F2%2F0"
        urn8 = "urn:ogf:network:domain=d:node=n:port=NotInThere"
        urn9 = "urn:ogf:network:d:n:NotInThere"
        urn10 = "urn:ogf:network:d:n:NotThere-1%2F2%2F0"
        root = etree.Element("{%s}topology" % self.nmtb)
        node1 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node1.attrib['id'] = urn1
        node2 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node2.attrib['id'] = urn2
        node3 = etree.SubElement(root, "{%s}node" % self.nmtb)
        node3.attrib['id'] = urn3
        self.encoder._root = root
        # Act
        ret1 = self.encoder._is_urn_in_doc(urn1, try_hard=True)
        ret2 = self.encoder._is_urn_in_doc(urn2, try_hard=True)
        ret3 = self.encoder._is_urn_in_doc(urn3, try_hard=True)
        ret4 = self.encoder._is_urn_in_doc(urn4, try_hard=True)
        ret5 = self.encoder._is_urn_in_doc(urn5, try_hard=True)
        ret6 = self.encoder._is_urn_in_doc(urn6, try_hard=True)
        ret7 = self.encoder._is_urn_in_doc(urn7, try_hard=True)
        ret8 = self.encoder._is_urn_in_doc(urn8, try_hard=True)
        ret9 = self.encoder._is_urn_in_doc(urn9, try_hard=True)
        ret10 = self.encoder._is_urn_in_doc(urn10, try_hard=True)
        # Assert
        self.assertEqual(ret1, True)
        self.assertEqual(ret2, True)
        self.assertEqual(ret3, True)
        self.assertEqual(ret4, True)
        self.assertEqual(ret5, True)
        self.assertEqual(ret6, True)
        self.assertEqual(ret7, True)
        self.assertEqual(ret8, False)
        self.assertEqual(ret9, False)
        self.assertEqual(ret10, False)
        
    @patch.object(PSDecoder, '_find_urn', mocksignature=True)
    def test_encode_remoteLinkId(self, find_urn):
        # Arrang
        find_urn.return_value = None
        ctrl_rlink = etree.Element("{%s}remoteLinkId" % self.ctrl)
        ctrl_rlink.text = "nmtb_link2"
        ctrl_out = {}
        # Act
        ret = self.encoder._encode_remoteLinkId(ctrl_rlink, ctrl_out)
        # Assert
        self.assertEqual(find_urn.called, True)
        self.assertEqual(ret, {"href": 'nmtb_link2', "rel": "full"})
        self.assertEqual(ctrl_out, {"relations": {"sibling": [ret]}})


class RSpec3DecoderTest(unittest2.TestCase):
    def setUp(self):
        self.encoder = RSpec3Decoder()
        self.rspec3 = "http://www.geni.net/resources/rspec/3"
        
        self.schemas = {
            'networkresource': 'http://unis.incntre.iu.edu/schema/20140214/networkresource#',
            'node': 'http://unis.incntre.iu.edu/schema/20140214/node#',
            'domain': 'http://unis.incntre.iu.edu/schema/20140214/domain#',
            'topology': 'http://unis.incntre.iu.edu/schema/20140214/topology#',
            'port': 'http://unis.incntre.iu.edu/schema/20140214/port#',
            'link': 'http://unis.incntre.iu.edu/schema/20140214/link#',
            'network': 'http://unis.incntre.iu.edu/schema/20140214/network#',
            'blipp': 'http://unis.incntre.iu.edu/schema/20140214/blipp#',
            'metadata': 'http://unis.incntre.iu.edu/schema/20140214/metadata#',
        }
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec(self, encode_children_mock):
        # Arrange
        rspec_common = etree.Element("{%s}rspec" % self.rspec3)
        rspec_ad = etree.Element("{%s}rspec" % self.rspec3)
        rspec_request = etree.Element("{%s}rspec" % self.rspec3)
        rspec_manifest = etree.Element("{%s}rspec" % self.rspec3)
        attrib_common = {
            "generated": "2012-06-07T04:05:52Z",
            "expires": "2012-06-07T04:05:52Z",
            "generated_by": "test_encode_rspec",
        }
        attrib_ad = {
            "generated": "2012-06-07T04:05:52Z",
            "expires": "2012-06-07T04:05:52Z",
            "generated_by": "test_encode_rspec",
            "type": "advertisement",
        }
        attrib_request = {
            "generated": "2012-06-07T04:05:52Z",
            "expires": "2012-06-07T04:05:52Z",
            "generated_by": "test_encode_rspec",
            "type": "request",
        }
        attrib_manifest = {
            "generated": "2012-06-07T04:05:52Z",
            "expires": "2012-06-07T04:05:52Z",
            "generated_by": "test_encode_rspec",
            "type": "manifest",
        }
        rspec_common.attrib.update(attrib_common)
        rspec_ad.attrib.update(attrib_ad)
        rspec_request.attrib.update(attrib_request)
        rspec_manifest.attrib.update(attrib_manifest)
        out_common = {}
        out_ad = {}
        out_request = {}
        out_manifest = {}
        manifest_expected = {
            "$schema": self.schemas["domain"],
            "urn": "urn",
            "id": "urn",
            "properties":
                {"geni": attrib_manifest}
        }
        manifest_expected["properties"]["geni"]["slice_urn"] = "urn"
        # Act
        ret_common = lambda : self.encoder._encode_rspec(rspec_common, out_common)
        ret_ad = self.encoder._encode_rspec(rspec_ad, out_ad, component_manager_id="urn")
        ret_request = lambda : self.encoder._encode_rspec(rspec_request, out_request)
        ret_manifest = self.encoder._encode_rspec(rspec_manifest, out_manifest, slice_urn="urn")
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(out_ad, {"$schema": self.schemas["domain"],
            "urn": "urn", "id": "urn", "properties": {"geni": attrib_ad}})
        self.assertEqual(out_manifest, manifest_expected)
        self.assertEqual(ret_ad, out_ad)
        self.assertEqual(ret_manifest, out_manifest)
    
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_node_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}node" % self.rspec3)
        attrib = {}
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "$schema": self.schemas["node"],
            "properties": {"geni": attrib}
        }
        # Act
        ret = self.encoder._encode_rspec_node(rspec, out, collection=collection)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(collection, {"nodes": [expected]})
        self.assertEqual(out, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_node_ad(self, encode_children_mock):
        # Arrange
        out = {}
        collection = {}
        rspec = etree.Element("{%s}node" % self.rspec3)
        attrib = {
            "component_id": "urn:publicid:IDN+test.net+node+node1",
            "component_manager_id": "urn:publicid:IDN+test.net+authority+cm",
            "component_name": "node1",
            "exclusive": "true",
        }
        rspec.attrib.update(attrib)
        attrib["exclusive"] = True
        expected = {
            "urn": "urn:publicid:IDN+test.net+node+node1",
            "name": "node1",
            "id": "test.net_node_node1",
            "$schema": self.schemas["node"],
            "properties": {"geni": attrib}
        }
        # Act
        ret = self.encoder._encode_rspec_node(rspec, out,
            collection=collection, rspec_type="advertisement")
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(collection, {"nodes": [expected]})
        self.assertEqual(out, {})

    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_node_manifest(self, encode_children_mock):
        # Arrange
        slice_urn = "urn:publicid:IDN+test.net+slice+test"
        out = {}
        collection = {}
        rspec = etree.Element("{%s}node" % self.rspec3)
        attrib = {
            "sliver_id": "urn:publicid:IDN+test.net+node+node1", # TODO (AH): check sliver_id id
            "client_id": "node1",
            "component_id": "urn:publicid:IDN+test.net+node+node1",
            "component_manager_id": "urn:publicid:IDN+test.net+authority+cm",
            "component_name": "node1",
            "exclusive": "true",
            "colocate": "colocated",
        }
        rspec.attrib.update(attrib)
        attrib["exclusive"] = True
        expected = {
            "urn": "urn:publicid:IDN+test.net+slice+test+node+node1",
            "name": "node1",
            "id": "test.net_slice_test_node_node1",
            "$schema": self.schemas["node"],
            "properties": {"geni": attrib}
        }
        expected["properties"]["geni"]["slice_urn"] = slice_urn
        # Act
        ret = self.encoder._encode_rspec_node(rspec, out,
            collection=collection, rspec_type="manifest", slice_urn=slice_urn)
        # Assert
        ret.pop("relations", None) # TODO (AH): add unit test for relations
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(collection, {"nodes": [expected]})
        self.assertEqual(out, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_interface_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}interface" % self.rspec3)
        attrib = {}
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "$schema": self.schemas["port"],
            "properties": {
                "geni": {}
            }
        }
        # Act
        ret = self.encoder._encode_rspec_interface(rspec, out, collection=collection)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(out, {"ports": [expected]})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_interface_ad(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}interface" % self.rspec3)
        attrib = {
            "component_id": "urn:publicid:IDN+test.net+interface+node1:eth1",
            "component_name": "eth1",
            "role": "mixed",
            "public_ipv4": "129.129.129.129",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "$schema": self.schemas["port"],
            "name": "eth1",
            "id": "test.net_interface_node1:eth1",
            "urn": "urn:publicid:IDN+test.net+interface+node1:eth1",
            "address": {
                "type": "ipv4",
                "address": attrib["public_ipv4"]
            },
            "properties": {
                "geni": attrib
            }
        }
        # Act
        ret = self.encoder._encode_rspec_interface(rspec, out,
            collection=collection, rspec_type="advertisement")
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(out, {"ports": [expected]})
        self.assertEqual(collection, {})

    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_interface_manifest(self, encode_children_mock):
        # Arrange
        slice_urn = "urn:publicid:IDN+test.net+slice+test"
        out = {}
        collection = {}
        rspec = etree.Element("{%s}interface" % self.rspec3)
        attrib = {
            "component_id": "urn:publicid:IDN+test.net+interface+node1:eth1",
            "client_id": "eth1",
            "sliver_id": "urn:publicid:IDN+test.net+interface+node1:eth1",
            "mac_address": "00:13:72:09:7d:95",
        }
        rspec.attrib.update(attrib)
        expected = {
            "$schema": self.schemas["port"],
            "id": "test.net_slice_test_interface_eth1",
            "urn": "urn:publicid:IDN+test.net+slice+test+interface+eth1",
            "name": "eth1",
            "address": {
                "type": "mac",
                "address": attrib["mac_address"]
            },
            "properties": {"geni": attrib}
        }
        expected["properties"]["geni"]["slice_urn"] = slice_urn
        # Act
        ret = self.encoder._encode_rspec_interface(rspec, out,
            collection=collection, rspec_type="manifest", slice_urn=slice_urn)
        # Assert
        ret.pop("relations", None) # TODO (AH): add unit test for relations
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(out, {"ports": [expected]})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_available(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}available" % self.rspec3)
        attrib = {
            "now": "false"
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "available": {"now": False}
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_available(rspec, out, collection, parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(out, {})
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_host(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}host" % self.rspec3)
        hostname = "test.test.com"
        attrib = {
            "name": hostname
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "hosts": [
                {"hostname": hostname}
            ]
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_host(rspec, out, collection, parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(out, {})
        self.assertEqual(ret, expected)
        self.assertEqual(parent,
            {
                "$schema": self.schemas["node"],
                "id": hostname,
                "properties": {"geni": expected}
            }
        )
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_ip(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}ip" % self.rspec3)
        attrib = {
            "address": "127.0.0.1",
            "netmask": "255.0.0.0",
            "type": "ipv4",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "ip": {
                "address": "127.0.0.1",
                "netmask": "255.0.0.0",
                "type": "ipv4",
            }
        }
        parent = {"$schema": self.schemas["port"]}
        expected_parent = {
            "$schema": self.schemas["port"],
            "address": {
                "address": "127.0.0.1",
                "type": "ipv4"
            },
            "properties": {"geni": expected}
        }
        # Act
        ret = self.encoder._encode_rspec_ip(rspec, out, collection, parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(out, {})
        self.assertEqual(ret, expected)
        self.assertEqual(parent, expected_parent)
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_sliver_type_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}sliver_type" % self.rspec3)
        attrib = {
            "name": "openvz"
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "sliver_type": attrib
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_sliver_type(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_sliver_type_ad(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}sliver_type" % self.rspec3)
        attrib = {
            "name": "openvz",
            "default": "openvz"
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "sliver_type": attrib
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_sliver_type(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})
    
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_hardware_type_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}hardware_type" % self.rspec3)
        attrib = {
            "name": "openvz"
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "hardware_types": [attrib]
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_hardware_type(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_disk_image_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}disk_image" % self.rspec3)
        attrib = {
            "version": "10", 
            "os": "Fedora", 
            "name": "urn:publicid:IDN+emulab.net+image+emulab-ops:FEDORA10-STD", 
            "description": "Standard 32-bit Fedora 10 image",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "disk_images": [attrib]
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_disk_image(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"]})
        self.assertEqual(collection, {})
        self.assertEqual(out, expected)
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_disk_image_ad(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}disk_image" % self.rspec3)
        attrib = {
            "version": "10", 
            "os": "Fedora", 
            "name": "urn:publicid:IDN+emulab.net+image+emulab-ops:FEDORA10-STD", 
            "description": "Standard 32-bit Fedora 10 image",
            "default": "true",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "disk_images": [attrib]
        }
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_disk_image(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["node"]})
        self.assertEqual(collection, {})
        self.assertEqual(out, expected)
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_location(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}location" % self.rspec3)
        attrib = {
            "country": "US",
            "longitude": "-111.84581",
            "latitude": "40.768652",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        attrib["longitude"] = float(attrib["longitude"])
        attrib["latitude"] = float(attrib["latitude"])
        expected = attrib
        parent = {"$schema": self.schemas["node"]}
        # Act
        ret = self.encoder._encode_rspec_location(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, {"location": expected})
        self.assertEqual(parent, {"$schema": self.schemas["node"], "location": expected})
        self.assertEqual(collection, {})
        
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_link_type_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}link_type" % self.rspec3)
        attrib = {
            "name": "ipv4",
            "class": "ipv4",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "link_types": [attrib]
        }
        parent = {"$schema": self.schemas["link"]}
        # Act
        ret = self.encoder._encode_rspec_link_type(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["link"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})
    
    @patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_component_manager_common(self, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}component_manager" % self.rspec3)
        attrib = {
            "name": "urn:publicid:IDN+test.net+authority+cm",
        }
        rspec.attrib.update(attrib)
        out = {}
        collection = {}
        expected = {
            "component_managers": [attrib]
        }
        parent = {"$schema": self.schemas["link"]}
        # Act
        ret = self.encoder._encode_rspec_component_manager(rspec, out, collection=collection, parent=parent)
        # Assert
        self.assertEqual(encode_children_mock.called, True)
        self.assertEqual(ret, expected)
        self.assertEqual(parent, {"$schema": self.schemas["link"], "properties": {"geni": expected}})
        self.assertEqual(collection, {})

    #@patch.object(RSpec3Decoder, '_encode_children', mocksignature=True)
    def test_encode_rspec_link_common(self): #, encode_children_mock):
        # Arrange
        rspec = etree.Element("{%s}link" % self.rspec3)
        prop1 = etree.SubElement(rspec, "{%s}property" % self.rspec3)
        prop2 = etree.SubElement(rspec, "{%s}property" % self.rspec3)
        attrib = {}
        attrib_prop1 = {
            'capacity': '100000',
            'source_id': 'urn:publicid:IDN+emulab.net+interface+pc102:eth2',
            'dest_id': 'urn:publicid:IDN+emulab.net+interface+pc102:eth3',
            'latency': '0',
            'packet_loss': '0',
        }
        attrib_prop2 = {
            'capacity': '100000',
            'source_id': 'urn:publicid:IDN+emulab.net+interface+pc102:eth3',
            'dest_id': 'urn:publicid:IDN+emulab.net+interface+pc102:eth2',
            'latency': '0',
            'packet_loss': '0',
        }
        rspec.attrib.update(attrib)
        prop1.attrib.update(attrib_prop1)
        prop2.attrib.update(attrib_prop2)
        out = {}
        collection = {}
        expected = {
            "$schema": self.schemas["link"],
            "directed": False,
            "capacity": 100000.0,
            "endpoints": [
                {
                    "href": "urn:publicid:IDN+emulab.net+interface+pc102:eth2", 
                    "rel": "full"
                }, 
                {
                    "href": "urn:publicid:IDN+emulab.net+interface+pc102:eth3", 
                    "rel": "full"
                }
            ],
            "properties": {
                "geni": {
                    "properties": [attrib_prop1, attrib_prop2]
                }
            }
        }
        # Act
        ret = self.encoder._encode_rspec_link(rspec, out, collection=collection)
        # Assert
        self.assertEqual(ret, expected)
        self.assertEqual(out, {"links": [expected]})
        self.assertEqual(collection, {})


if __name__ == '__main__':
    unittest2.main()

import json
import requests
from requests.auth import HTTPBasicAuth
import coreapi
from topology import Topology, Node, Port, IntermediateNode


class OdlDecoder:

    SCHEMAS = {
        'networkresources': 'http://unis.crest.iu.edu/schema/20151104/networkresource#',
        'nodes': 'http://unis.crest.iu.edu/schema/20151104/node#',
        'domains': 'http://unis.crest.iu.edu/schema/20151104/domain#',
        'ports': 'http://unis.crest.iu.edu/schema/20151104/port#',
        'links': 'http://unis.crest.iu.edu/schema/20151104/link#',
        'paths': 'http://unis.crest.iu.edu/schema/20151104/path#',
        'networks': 'http://unis.crest.iu.edu/schema/20151104/network#',
        'topologies': 'http://unis.crest.iu.edu/schema/20151104/topology#',
        'services': 'http://unis.crest.iu.edu/schema/20151104/service#',
        'blipp': 'http://unis.crest.iu.edu/schema/20151104/blipp#',
        'metadata': 'http://unis.crest.iu.edu/schema/20151104/metadata#',
        'datum': 'http://unis.crest.iu.edu/schema/20151104/datum#',
        'data': 'http://unis.crest.iu.edu/schema/20151104/data#',
        'ipports': 'http://unis.crest.iu.edu/schema/ext/ipport/1/ipport#'
    }

    def __init__(self, host_name_unis, port_number_unis, host_name_odl, port_number_odl='8181', auth_username='admin', auth_password='admin'):

        self.topology_url = "http://"+host_name_odl+":"+port_number_odl+"/restconf/operational/network-topology:network-topology"
        headers = {'accept': 'application/json'}
        r = requests.get(self.topology_url,
                         auth=HTTPBasicAuth(auth_username, auth_password), headers=headers)
        self.resp_dict = r.json()
        self.topology_object = Topology()
        self.unis_uri="http://"+host_name_unis+":"+port_number_unis+"/"
        self.clean_all()
        self.decode()

    def clean_all(self):
        print("Starting the initial CLEANUP PROCESS")
        self.clean_nodes()
        self.delete_ports()
        self.delete_links()

    def clean_nodes(self):
        print("Deleting the nodes")
        nodes_uri = self.unis_uri+"nodes"
        nodes_list = coreapi.get(nodes_uri)
        for node_dict in nodes_list:
            print node_dict['selfRef']
            # requests.delete(node_dict['selfRef'])
            del_uri = nodes_uri+"/"+node_dict['selfRef'].split("/")[4]
            requests.delete(del_uri)

    def delete_ports(self):
        print("Deleting the ports")
        ports_uri=self.unis_uri+"ports"
        ports_list = coreapi.get(ports_uri)
        for port_dict in ports_list:
            print port_dict['selfRef']
            # requests.delete(port_dict['selfRef'])
            del_uri=ports_uri+"/"+port_dict['selfRef'].split("/")[4]
            print("Delete:"+del_uri)
            requests.delete(del_uri)

    def delete_links(self):
        print("Deleting the links")
        links_uri=self.unis_uri+"links"
        links_list = coreapi.get(links_uri)
        for link_dict in links_list:
            print link_dict['selfRef']
            # requests.delete(port_dict['selfRef'])
            del_uri = links_uri+"/"+link_dict['selfRef'].split("/")[4]
            print("Delete:"+del_uri)
            requests.delete(del_uri)

    def getId(self, ref_url):
        """
            http://10.10.0.135:8888/nodes/56f88569e1382308b0b6a2ea will return 56f88569e1382308b0b6a2ea
        :param ref_url:
        :return:
        """
        print("getId::"+ref_url)
        return ref_url.split("/")[4]

    def create_ref_url(self, type, id=None):
        """
            It will build the url from type and id
        :param type: ports or nodes
        :param id:
        :return:
        """
        if id is None:
            return self.unis_uri+type
        return self.unis_uri+type+"/"+id

    def decode(self):
        print("Starting the DECODE PROCESS")
        self.create_nodes_from_odl()
        self.update_node_refs()
        self.create_ports_from_odl()
        self.update_port_refs()
        self.create_links_from_odl()
        self.build_links()

    def create_nodes_from_odl(self):
        nodes_uri = self.unis_uri+"nodes"
        nodes = []
        for topology in self.resp_dict['network-topology']['topology']:
            if 'node' in topology:
                for node_dict in topology['node']:
                    print(node_dict['node-id'])
                    node = dict()
                    node["$schema"] = self.SCHEMAS['nodes']
                    node["name"] = node_dict['node-id']
                    print "Node::"
                    print node_dict['node-id']
                    nodes.append(node)
                print "::FINAL JSON::"
                json_data = json.dumps(nodes)


                print("NODE URI::"+nodes_uri)
                print("JSON DATA:"+json_data)
                requests.post(nodes_uri, data = json_data)

    def update_node_refs(self):
        nodes_uri = self.unis_uri+"nodes"
        nodes_list = coreapi.get(nodes_uri)
        for check_node in nodes_list:
            print check_node['name']
            print check_node['selfRef']
            node_object = Node(check_node['name'])
            self.topology_object.add_node(self.getId(check_node['selfRef']), node_object)
            print "\n"
        self.topology_object.display_topology()

    def create_ports_from_odl(self):
        print("PORTSSSSS!!!!")
        ports_uri = self.unis_uri+"ports"
        ports = []
        for topology in self.resp_dict['network-topology']['topology']:
            if 'node' in topology:
                for node in topology['node']:
                    print(node['node-id'])
                    if 'termination-point' in node:
                        for tp in node['termination-point']:
                            print(tp['tp-id'])
                            port_node_name = node['node-id']
                            port_name = tp['tp-id']
                            port = dict()
                            port["$schema"]=self.SCHEMAS['ports']
                            port["name"]=port_name
                            port["nodeRef"]=self.topology_object.get_node_id_by_name(port_node_name)
                            ipv4_addr = dict()
                            ipv4_addr["type"]="ipv4"
                            ipv4_addr["address"]="1.1.1.1"
                            port["properties"]={"ipv4":ipv4_addr}
                            ports.append(port)
            print "::FINAL PORTS JSON::"
            ports_json_data = json.dumps(ports)
            print(ports_json_data)
            print("PORTS URI::"+ports_uri)
            requests.post(ports_uri, data = ports_json_data)

    def update_port_refs(self):
        ports_uri = self.unis_uri+"ports"
        ports_list = coreapi.get(ports_uri)

        for check_port in ports_list:
            port_name = check_port['name']
            port_ref = self.getId(check_port['selfRef'])
            node_ref = check_port['nodeRef']
            port_object = Port(port_name, "2.2.2.2")
            self.topology_object.nodes[node_ref].add_port(port_ref, port_object)
            print "\n"

        print("PRINIIIIIII TOPO FINAL")
        self.topology_object.display_topology()

    def create_links_from_odl(self):

        for topology in self.resp_dict['network-topology']['topology']:

            print("Links:::")
            if 'link' in topology:
                for item in topology['link']:
                    link_id = item['link-id']
                    print(item['link-id'])
                    src_node_name = item['source']['source-node']
                    src_port_name = item['source']['source-tp']
                    print(item['source']['source-node'])
                    print(item['source']['source-tp'])
                    dst_node_name = item['destination']['dest-node']
                    dst_port_name = item['destination']['dest-tp']
                    print(item['destination']['dest-node'])
                    print(item['destination']['dest-tp'])
                    src_node_id = self.topology_object.get_node_id_by_name(src_node_name)
                    dst_node_id = self.topology_object.get_node_id_by_name(dst_node_name)
                    src_port_id = self.topology_object.nodes[src_node_id].get_port_id_by_name(src_port_name)
                    dst_port_id = self.topology_object.nodes[dst_node_id].get_port_id_by_name(dst_port_name)
                    self.topology_object.nodes[src_node_id].ports[src_port_id].add_link(link_id,dst_node_id,dst_port_id)

    def build_links(self):
        print("build_links::")
        link = dict()
        link["directed"] = False
        link["$schema"] = self.SCHEMAS['links']
        link["name"] = "linkk"
        for node_id in self.topology_object.nodes.keys():
            for src_port_id in self.topology_object.nodes[node_id].ports:
                src_port_obj = self.topology_object.nodes[node_id].ports[src_port_id]
                # check if a link exists
                if src_port_obj.link_id is not None:
                    port_obj = self.topology_object.nodes[node_id].ports[src_port_id]
                    endpoints = []
                    port_obj.display_port()
                    endpoint = {"href": "abcref", "rel": "full"}
                    endpoint["href"] = self.create_ref_url("ports", src_port_id)
                    endpoints.append(endpoint)
                    endpoint = {"href": "abcref", "rel": "full"}
                    dst_port_id = src_port_obj.connected_to_port_id
                    endpoint["href"] = self.create_ref_url("ports", dst_port_id)
                    endpoints.append(endpoint)
                    link["endpoints"] = endpoints
                    json_data = json.dumps(link)
                    print(json_data)
                    print(self.create_ref_url("links"))
                    r = requests.post(self.create_ref_url("links"), data=json_data)


# odlDecoder = OdlDecoder('10.10.0.135', '8888', '10.10.0.136', '8181')






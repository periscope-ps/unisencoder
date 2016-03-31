import rdflib
import requests
import json
import coreapi
from topology import Topology, Node, Port

class RdfDecoder():

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

	def __init__(self, rdf_file_name, host_name, port_number='8888'):
		self.g=rdflib.Graph()
		self.g.load(rdf_file_name)
		self.prefix = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
			PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> 
			PREFIX ndl: <http://www.science.uva.nl/research/sne/ndl#> """;
		self.uri="http://"+host_name+":"+port_number+"/"
		print("URI:"+self.uri)
		self.topology_object = Topology()
		self.clean_all()
		self.decode()

	def clean_all(self):
		print("Starting the initial CLEANUP PROCESS")
		self.clean_nodes()
		self.delete_ports()

	def clean_nodes(self):
		print("Deleting the nodes")
		nodes_uri=self.uri+"nodes"
		nodes_list = coreapi.get(nodes_uri)
		for node_dict in nodes_list:
			print node_dict['selfRef']
			requests.delete(node_dict['selfRef'])

	def delete_ports(self):
		print("Deleting the ports")
		ports_uri=self.uri+"ports"
		ports_list = coreapi.get(ports_uri)
		for port_dict in ports_list:
			print port_dict['selfRef']
			requests.delete(port_dict['selfRef'])

	def decode(self):
		print("Starting the DECODE PROCESS")
		self.create_nodes_from_rdf()
		self.update_node_refs()
		self.create_ports_from_rdf()
		self.update_port_refs()
		self.build_port_ref_in_nodes()

	def create_nodes_from_rdf(self):
		node_only_query=self.prefix+"""
		SELECT ?name 
		WHERE {
		        ?x rdf:type ndl:Device . ?x ndl:name ?name.
			OPTIONAL {
				?y ndl:connectedTo ?z .
				?z rdf:type ndl:Interface .
				?z ndl:name ?neighbour
			} . OPTIONAL {
				?y ndl:capacity ?capacity .
				?y ndl:encapsulation ?type
			} .
			
		}"""
		
		nodes_uri=self.uri+"nodes"
		nodes = []
		for row in self.g.query(node_only_query):
			node = dict()
			node["$schema"]=self.SCHEMAS['nodes']
			node["name"]=row.name
			# ports = []
			# port={'href':'instageni.illinois.edu_authority_cm_slice_idms','rel': 'full'}
			# ports.append(port)
			# node["ports"]=ports
			print "Node::"
			print row.name
			nodes.append(node)

		print "::FINAL JSON::"
		json_data = json.dumps(nodes)


		print("NODE URI::"+nodes_uri)
		print("JSON DATA:"+json_data)
		requests.post(nodes_uri, data = json_data)


	def update_node_refs(self):
		nodes_uri=self.uri+"nodes"
		nodes_list = coreapi.get(nodes_uri)

		for check_node in nodes_list:
			print check_node['name']
			print check_node['selfRef']
			node_object = Node(check_node['name'])
			self.topology_object.add_node(check_node['selfRef'], node_object)
			print "\n"

		print("PRINIIIIIII")
		self.topology_object.display_topology()

	############# PORTS


	def create_ports_from_rdf(self):
		interface_query=self.prefix+"""
		SELECT ?name ?interface
			WHERE {
			        ?x rdf:type ndl:Device . ?x ndl:name ?name .
				?x ndl:hasInterface ?interface 
				OPTIONAL {
					?y ndl:connectedTo ?z .
					?z rdf:type ndl:Interface .
					?z ndl:name ?neighbour
				} . OPTIONAL {
					?y ndl:capacity ?capacity .
					?y ndl:encapsulation ?type
				} .
				
			}"""

		ports_uri=self.uri+"ports"
		ports = []
		print("PORTSSSSS!!!!")
		for row in self.g.query(interface_query):
			print(row.name+" :::"+row.interface)
			temp_intf_name=row.interface
			intf_name=temp_intf_name.split("#")
			port_name_split=intf_name[1].split(":")
			port_node_name=port_name_split[0]
			port_name=port_name_split[1]
			port = dict()
			port["$schema"]=self.SCHEMAS['ports']
			port["name"]=port_name
			port["nodeRef"]=self.topology_object.get_node_id_by_name(port_node_name)
			ipv4_addr = dict()
			ipv4_addr["type"]="ipv4"
			## TODO: Fill the actual IPv4 address probably from the interface table using Router Proxy
			ipv4_addr["address"]="1.1.1.1"
			port["properties"]={"ipv4":ipv4_addr}
			ports.append(port)

		print "::FINAL PORTS JSON::"
		ports_json_data = json.dumps(ports)
		print(ports_json_data)
		print("PORTS URI::"+ports_uri)
		requests.post(ports_uri, data = ports_json_data)

	###### GET PORT REFS

	def update_port_refs(self):
		ports_uri=self.uri+"ports"
		ports_list = coreapi.get(ports_uri)

		for check_port in ports_list:
			port_name = check_port['name']
			port_ref = check_port['selfRef']
			node_ref = check_port['nodeRef']
			port_object = Port(node_ref, "2.2.2.2")
			self.topology_object.nodes[node_ref].add_port(port_ref, port_object)
			print "\n"

		print("PRINIIIIIII TOPO FINAL")
		self.topology_object.display_topology()


	######### BUILD PORT REF in NODES


	def build_port_ref_in_nodes(self):
		for node_id in self.topology_object.nodes.keys():
			self.topology_object.nodes[node_id].ports
			node = dict()
			ports = []
			for port_id in self.topology_object.nodes[node_id].ports.keys():
				port={'href': port_id,'rel': 'full'}
				ports.append(port)
			node["ports"]=ports	
			print "::FINAL JSON::"
			json_data = json.dumps(node)
			print(json_data)

			r=requests.put(node_id, data=json_data)


rdf = RdfDecoder('mini-topo.rdf', '10.0.0.135', '8888')




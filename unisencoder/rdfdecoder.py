import rdflib
import requests
import json
import coreapi
from topology import Topology, Node, Port, IntermediateNode
from permutation import Permutation

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
		self.inode_object = IntermediateNode()
		self.topology_object = Topology()
		self.clean_all()
		self.decode()


	def clean_all(self):
		print("Starting the initial CLEANUP PROCESS")
		self.clean_nodes()
		self.delete_ports()
		self.delete_links()

	def clean_nodes(self):
		print("Deleting the nodes")
		nodes_uri=self.uri+"nodes"
		nodes_list = coreapi.get(nodes_uri)
		for node_dict in nodes_list:
			print node_dict['selfRef']
			# requests.delete(node_dict['selfRef'])
			del_uri=nodes_uri+"/"+node_dict['selfRef'].split("/")[4]
			requests.delete(del_uri)

	def delete_ports(self):
		print("Deleting the ports")
		ports_uri=self.uri+"ports"
		ports_list = coreapi.get(ports_uri)
		for port_dict in ports_list:
			print port_dict['selfRef']
			# requests.delete(port_dict['selfRef'])
			del_uri=ports_uri+"/"+port_dict['selfRef'].split("/")[4]
			print("Delete:"+del_uri)
			requests.delete(del_uri)

	def delete_links(self):
		print("Deleting the links")
		links_uri=self.uri+"links"
		links_list = coreapi.get(links_uri)
		for link_dict in links_list:
			print link_dict['selfRef']
			# requests.delete(port_dict['selfRef'])
			del_uri=links_uri+"/"+link_dict['selfRef'].split("/")[4]
			print("Delete:"+del_uri)
			requests.delete(del_uri)

	def decode(self):
		print("Starting the DECODE PROCESS")
		self.create_nodes_from_rdf()
		self.update_node_refs()
		self.create_ports_from_rdf()
		self.update_port_refs()
		self.build_port_ref_in_nodes()
		print("Starting Links creation")
		self.create_links_from_rdf()
		print("Printing Inodes")
		self.inode_object.print_inodes()
		self.check_for_links()

	def create_nodes_from_rdf(self):
		node_only_query=self.prefix+"""
		SELECT ?name
		WHERE {
		        ?x rdf:type ndl:Device . ?x ndl:name ?name
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
			self.topology_object.add_node(self.getId(check_node['selfRef']), node_object)
			print "\n"

		print("PRINIIIIIII")
		self.topology_object.display_topology()

	############# PORTS

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
			return self.uri+type
		return self.uri+type+"/"+id

	def create_ports_from_rdf(self):
		interface_query=self.prefix+"""
		SELECT ?name ?interface
			WHERE {
			        ?x rdf:type ndl:Device . ?x ndl:name ?name .
				?x ndl:hasInterface ?interface
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
			port_ref = self.getId(check_port['selfRef'])
			node_ref = check_port['nodeRef']
			port_object = Port(port_name, "2.2.2.2")
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
				port={'href': self.create_ref_url("ports", port_id),'rel': 'full'}
				ports.append(port)
			node["ports"]=ports
			print "::FINAL JSON::"
			json_data = json.dumps(node)
			print(json_data)

			r=requests.put(self.create_ref_url("nodes",node_id), data=json_data)

	def create_links_from_rdf(self):
		links_query = self.prefix+"""
		SELECT ?name ?interface ?connectedTo
		WHERE {
				?x rdf:type ndl:Device . ?x ndl:name ?name .
			?x ndl:hasInterface ?y . ?y rdf:type ndl:Interface .
			?y ndl:name ?interface . ?y ndl:connectedTo ?connectedTo .
		}"""
		for row in self.g.query(links_query):
			print(row['name'], row['interface'], row['connectedTo'])
			dest_node_name  = row['connectedTo'].split("#")[1]
			print("ref::"+row['connectedTo'].split("#")[1])
			print("router...name::"+row['interface'].split(":")[0])
			node_name = row['interface'].split(":")[0]
			print("interface...name::"+row['interface'].split(":")[1])
			intf_name = row['interface'].split(":")[1]
			self.inode_object.add_link_to_inode(dest_node_name, intf_name, node_name)

	def check_for_links(self):
		is_valid = True
		for inode in self.inode_object.inodes:
			for link_dict in self.inode_object.inodes[inode]:
				if self.topology_object.get_node_id_by_name(link_dict['node_name']) is None:
					is_valid = False
			if is_valid:
				self.build_links(inode)


	def build_links(self, inode_name):
		print("build_links::"+inode_name)
		link = dict()
		link["directed"] = False
		link["$schema"] = self.SCHEMAS['links']
		link["name"] = "linkk"
		if len(self.inode_object.inodes[inode_name]) < 2:
			print("LESS THAN 2 ENDPOINTS TO HANDLE")
		else:
			num_endpoints = len(self.inode_object.inodes[inode_name])
			permutation_list = Permutation.permutation(num_endpoints, 2)
			for link_permutation in permutation_list:
				endpoints = []
				if len(link_permutation) != 2:
					print("Permutation lenngth not 2...Error")
					return
				for index in range(2):
					endpoint = {"href" : "abcref", "rel" : "full"}
					link_dict = self.inode_object.inodes[inode_name][link_permutation[index]]
					node_name = link_dict['node_name']
					intf_name = link_dict['intf_name']
					node_ref = self.topology_object.get_node_id_by_name(node_name)
					node_obj = self.topology_object.nodes[node_ref]
					port_ref = node_obj.get_port_id_by_name(intf_name)
					endpoint["href"] = self.create_ref_url("ports", port_ref)
					endpoints.append(endpoint)
				link["endpoints"] = endpoints
				json_data = json.dumps(link)
				print("A link::"+json_data)
				print(self.create_ref_url("links"))
				r=requests.post(self.create_ref_url("links"), data=json_data)
		print("END build_links::"+inode_name)



# rdf = RdfDecoder('mini-topo.rdf', '10.10.0.135', '8888')

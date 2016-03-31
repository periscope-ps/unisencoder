

class Topology():
	def __init__(self):
		self.nodes = dict()
	def add_node(self, node_id, node_object):
		if node_id in self.nodes:
			print("Node Id already exists")
			return
		#Check if node_object is of type Node
		self.nodes[node_id]=node_object

	def display_topology(self):
		print("Printing the topology")
		if len(self.nodes) > 0:
			for node_id in self.nodes.keys():
				print("Node_id::"+node_id)
				self.nodes[node_id].display_node()

	def get_node_id_by_name(self, node_name):
		if len(self.nodes) > 0:
			for node_id in self.nodes.keys():
				if self.nodes[node_id].name == node_name:
					return node_id
		return None

class Node:

	def __init__(self, node_name):
		self.name = node_name
		self.ports = dict()

	def add_port(self, port_id, port_object):
		if port_id in self.ports:
			print("Port Id already exists")
			return

		#Check if port_object is of type Port
		self.ports[port_id]=port_object

	def display_node(self):
		print("Node::Name:"+self.name)
		if len(self.ports) > 0:
			for port_id in self.ports.keys():
				print("Port_id::"+port_id)
				self.ports[port_id].display_port()


class Port:

	def __init__(self, port_name, ip_address):
		self.name = port_name
		self.ip_address = ip_address
		self.link_id = None
		self.connected_to_node_id = None
		self.connected_to_port_id = None

	def add_link(self, link_id, node_id, port_id):
		self.link_id = link_id
		self.connected_to_node_id = node_id
		self.connected_to_port_id = port_id

	def display_port(self):
		print("Port::Name:"+self.name)
		print("Port::ip_address:"+self.ip_address)
		if self.link_id is not None:
			print("Port::link_id:"+self.link_id)
			print("Port::connected_to_node_id:"+self.connected_to_node_id)
			print("Port::connected_to_port_id:"+self.connected_to_port_id)

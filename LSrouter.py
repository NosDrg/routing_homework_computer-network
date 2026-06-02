####################################################
# LSrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class LSrouter(Router):
    """Link state routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
    
        self.neighbor_links = {}
        self.topology = {}
        self.sequence_numbers = {}
        self.my_seq = 0
        self.forwarding_table = {}

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        
        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                next_port = self.forwarding_table[packet.dst_addr]
                if next_port is not None:
                    self.send(next_port, packet)
        else:
            payload = json.loads(packet.content)
            origin_addr = payload["origin"]
            seq_num = payload["seq"]
            received_ls = payload["link_state"] 

            if origin_addr not in self.sequence_numbers or seq_num > self.sequence_numbers[origin_addr]:
                self.sequence_numbers[origin_addr] = seq_num
                self.topology[origin_addr] = received_ls
                
                self.dijkstra()
                
                for p in self.neighbor_links.keys():
                    if p != port:
                        self.send(p, packet)

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""

        self.neighbor_links[port] = (endpoint, cost)
        
        self.my_seq += 1
        self.update_local_topology()
        
        self.dijkstra()
        self.broadcast_link_state()

    def handle_remove_link(self, port):
        """Handle removed link."""

        if port in self.neighbor_links:
            del self.neighbor_links[port]
            
        self.my_seq += 1
        self.update_local_topology()
        
        self.dijkstra()
        self.broadcast_link_state()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_link_state()

    def update_local_topology(self):
        """Update local topology."""

        local_ls = {}
        for port, (endpoint, cost) in self.neighbor_links.items():
            local_ls[endpoint] = cost
        self.topology[self.addr] = local_ls
        self.sequence_numbers[self.addr] = self.my_seq

    def broadcast_link_state(self):
        """Send link state to neighbors."""

        self.update_local_topology()
        
        payload = {
            "origin": self.addr,
            "seq": self.my_seq,
            "link_state": self.topology[self.addr]
        }
        serialized_content = json.dumps(payload)
        
        for port, (endpoint, _) in self.neighbor_links.items():
            routing_packet = Packet(
                kind=Packet.ROUTING,
                src_addr=self.addr,
                dst_addr=endpoint,
                content=serialized_content
            )
            self.send(port, routing_packet)

    def dijkstra(self):
        """Compute shortest paths using Dijkstra's algorithm and update forwarding table."""

        distances = {}     # Khoảng cách ngắn nhất từ nguồn đến các nút: {node: cost}
        first_hop = {}     # Cổng đầu tiên (port) tương ứng trên đường đi đến nút đó: {node: port}
        visited = set()    # Tập các nút đã tối ưu
        
        distances[self.addr] = 0
        
        all_nodes = set(self.topology.keys())
        for links in self.topology.values():
            all_nodes.update(links.keys())
            
        for node in all_nodes:
            if node != self.addr:
                distances[node] = float('inf')

        while len(visited) < len(all_nodes):
            u = None
            min_dist = float('inf')
            for node in all_nodes:
                if node not in visited and distances[node] < min_dist:
                    min_dist = distances[node]
                    u = node
            
            if u is None or min_dist == float('inf'):
                break
                
            visited.add(u)
            
            if u not in self.topology:
                continue
                
            for v, cost in self.topology[u].items():
                if v not in visited:
                    new_dist = distances[u] + cost
                    if new_dist < distances[v]:
                        distances[v] = new_dist
                        
                        if u == self.addr:
                            for port, (endpoint, _) in self.neighbor_links.items():
                                if endpoint == v:
                                    first_hop[v] = port
                                    break
                        else:
                            first_hop[v] = first_hop.get(u)

        new_forwarding_table = {}
        for node, port in first_hop.items():
            if port is not None:
                new_forwarding_table[node] = port
                
        self.forwarding_table = new_forwarding_table

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"LSrouter(addr={self.addr}, FwdTable={self.forwarding_table})"
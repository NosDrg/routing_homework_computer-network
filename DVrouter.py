####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        
        self.neighbor_links = {} 
        self.distance_vector = {self.addr: 0}
        self.forwarding_table = {}
        self.neighbor_vectors = {}

    def handle_packet(self, port, packet):
        """Process incoming packet."""

        if packet.is_traceroute:
            if packet.dst_addr in self.forwarding_table:
                next_port = self.forwarding_table[packet.dst_addr]
                if next_port is not None:
                    self.send(next_port, packet)
        else:
            neighbor_dv = json.loads(packet.content)

            self.neighbor_vectors[port] = neighbor_dv
            
            if self.recompute_routes():
                self.broadcast_distance_vector()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""

        self.neighbor_links[port] = (endpoint, cost)
        self.recompute_routes()
        self.broadcast_distance_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""

        if port in self.neighbor_links:
            del self.neighbor_links[port]
        
        if port in self.neighbor_vectors:
            del self.neighbor_vectors[port]
            
        self.recompute_routes()
        self.broadcast_distance_vector()

    def handle_time(self, time_ms):
        """Handle current time."""

        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_distance_vector()

    def recompute_routes(self):
        """Recompute distance vector and forwarding table based on neighbor information."""

        new_dv = {self.addr: 0}
        new_forwarding = {}
        
        all_destinations = set()
        for neighbor_dv in self.neighbor_vectors.values():
            all_destinations.update(neighbor_dv.keys())
        for endpoint, _ in self.neighbor_links.values():
            all_destinations.add(endpoint)
            
        if self.addr in all_destinations:
            all_destinations.remove(self.addr)

        for dst in all_destinations:
            min_cost = float('inf')
            best_port = None
            
            for port, (endpoint, link_cost) in self.neighbor_links.items():
                if endpoint == dst:
                    current_cost = link_cost
                    if current_cost < min_cost:
                        min_cost = current_cost
                        best_port = port
                        
                if port in self.neighbor_vectors and dst in self.neighbor_vectors[port]:
                    current_cost = link_cost + self.neighbor_vectors[port][dst]
                    if current_cost < min_cost:
                        min_cost = current_cost
                        best_port = port
            
            if min_cost < float('inf'):
                new_dv[dst] = min_cost
                new_forwarding[dst] = best_port

        changed = (new_dv != self.distance_vector)
        self.distance_vector = new_dv
        self.forwarding_table = new_forwarding

        return changed

    def broadcast_distance_vector(self):
        """Send distance vector to all neighbors."""

        for port, (endpoint, _) in self.neighbor_links.items():
            custom_dv = self.distance_vector.copy()
            
            for dst, next_port in self.forwarding_table.items():
                if next_port == port:
                    custom_dv[dst] = float('inf')
            
            serialized_content = json.dumps(custom_dv)
            
            routing_packet = Packet(
                kind=Packet.ROUTING, 
                src_addr=self.addr, 
                dst_addr=endpoint, 
                content=serialized_content
            )
            
            self.send(port, routing_packet)

    def __repr__(self):
        """Representation for debugging in the network visualizer."""

        return f"DVrouter(addr={self.addr}, DV={self.distance_vector})"
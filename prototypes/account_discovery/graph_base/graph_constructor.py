import json
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np

from tier_assignment import AccountTier


@dataclass
class GraphNode:
    """Represents a node (account) in the following graph"""
    account_id: str
    handle: str
    display_name: str
    follower_count: int
    verified: bool
    is_seed: bool = False
    seed_tier: Optional[AccountTier] = None
    
    # Graph metrics (calculated later)
    in_degree: int = 0
    out_degree: int = 0
    weighted_in_degree: float = 0.0
    pagerank_score: float = 0.0
    betweenness_centrality: float = 0.0


@dataclass  
class GraphEdge:
    """Represents an edge (following relationship) in the graph"""
    follower_id: str
    followed_id: str
    weight: float
    source_tier: AccountTier
    discovered_at: datetime


@dataclass
class GraphStats:
    """Statistics about the constructed graph"""
    total_nodes: int
    total_edges: int
    seed_nodes: int
    discovered_nodes: int
    average_degree: float
    graph_density: float
    connected_components: int
    tier_distribution: Dict[str, int]
    verification_rate: float


class FollowingGraphConstructor:
    """Constructs and analyzes weighted following graphs"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.tier_weights = {
            AccountTier.TIER_1: 3.0,
            AccountTier.TIER_2: 2.0, 
            AccountTier.TIER_3: 1.0
        }
        
    def load_relationships_from_json(self, json_file: str) -> None:
        """Load following relationships from JSON file"""
        print(f"Loading relationships from {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        relationships = data.get('relationships', [])
        print(f"Found {len(relationships)} relationships")
        
        # Process each relationship
        for rel_data in relationships:
            self._add_relationship(rel_data)
        
        print(f"Graph constructed with {len(self.nodes)} nodes and {len(self.edges)} edges")
    
    def _add_relationship(self, rel_data: Dict) -> None:
        """Add a single relationship to the graph"""
        follower_id = rel_data['follower_id']
        followed_id = rel_data['followed_id']
        source_tier = AccountTier[rel_data['source_tier']]
        
        # Create nodes if they don't exist
        if follower_id not in self.nodes:
            # This is a seed account (since it's doing the following)
            self.nodes[follower_id] = GraphNode(
                account_id=follower_id,
                handle="seed_" + follower_id,  # Will be updated if we have actual data
                display_name="Seed Account",
                follower_count=0,  # Unknown for seed in this data
                verified=False,
                is_seed=True,
                seed_tier=source_tier
            )
        
        if followed_id not in self.nodes:
            # This is a discovered account
            self.nodes[followed_id] = GraphNode(
                account_id=followed_id,
                handle=rel_data['followed_handle'],
                display_name=rel_data['followed_name'],
                follower_count=rel_data['followed_followers'],
                verified=rel_data['followed_verified'],
                is_seed=False
            )
        
        # Create weighted edge
        weight = self.tier_weights[source_tier]
        edge = GraphEdge(
            follower_id=follower_id,
            followed_id=followed_id,
            weight=weight,
            source_tier=source_tier,
            discovered_at=datetime.fromisoformat(rel_data['discovered_at'])
        )
        
        self.edges.append(edge)
        
        # Add edge to NetworkX graph
        if self.graph.has_edge(follower_id, followed_id):
            # If edge already exists, add to the weight (multiple seeds following same account)
            current_weight = self.graph[follower_id][followed_id]['weight']
            self.graph[follower_id][followed_id]['weight'] = current_weight + weight
        else:
            self.graph.add_edge(follower_id, followed_id, weight=weight, source_tier=source_tier.name)
    
    def calculate_basic_metrics(self) -> None:
        """Calculate basic graph metrics for all nodes"""
        print("Calculating basic graph metrics...")
        
        # Calculate degree centralities
        in_degree = dict(self.graph.in_degree())
        out_degree = dict(self.graph.out_degree())
        
        # Calculate weighted degrees
        weighted_in_degree = {}
        for node in self.graph.nodes():
            weighted_in = sum(self.graph[pred][node]['weight'] 
                            for pred in self.graph.predecessors(node))
            weighted_in_degree[node] = weighted_in
        
        # Update node objects with metrics
        for node_id, node in self.nodes.items():
            node.in_degree = in_degree.get(node_id, 0)
            node.out_degree = out_degree.get(node_id, 0)
            node.weighted_in_degree = weighted_in_degree.get(node_id, 0.0)
    
    def calculate_advanced_metrics(self) -> None:
        """Calculate advanced network metrics (PageRank, centrality)"""
        print("Calculating advanced network metrics...")
        
        # PageRank with edge weights
        try:
            pagerank = nx.pagerank(self.graph, weight='weight', max_iter=100)
            for node_id, score in pagerank.items():
                if node_id in self.nodes:
                    self.nodes[node_id].pagerank_score = score
        except Exception as e:
            print(f"Warning: PageRank calculation failed: {e}")
        
        # Betweenness centrality (computational intensive for large graphs)
        if len(self.graph.nodes()) < 1000:  # Only for smaller graphs
            try:
                betweenness = nx.betweenness_centrality(self.graph, weight='weight')
                for node_id, score in betweenness.items():
                    if node_id in self.nodes:
                        self.nodes[node_id].betweenness_centrality = score
            except Exception as e:
                print(f"Warning: Betweenness centrality calculation failed: {e}")
        else:
            print("Skipping betweenness centrality for large graph")
    
    def get_graph_statistics(self) -> GraphStats:
        """Calculate overall graph statistics"""
        seed_nodes = sum(1 for node in self.nodes.values() if node.is_seed)
        discovered_nodes = len(self.nodes) - seed_nodes
        
        # Calculate verification rate for discovered accounts
        discovered_accounts = [node for node in self.nodes.values() if not node.is_seed]
        verified_discovered = sum(1 for node in discovered_accounts if node.verified)
        verification_rate = verified_discovered / len(discovered_accounts) if discovered_accounts else 0
        
        # Tier distribution
        tier_counts = defaultdict(int)
        for node in self.nodes.values():
            if node.is_seed and node.seed_tier:
                tier_counts[node.seed_tier.name] += 1
        
        return GraphStats(
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            seed_nodes=seed_nodes,
            discovered_nodes=discovered_nodes,
            average_degree=2 * len(self.edges) / len(self.nodes) if self.nodes else 0,
            graph_density=nx.density(self.graph),
            connected_components=nx.number_weakly_connected_components(self.graph),
            tier_distribution=dict(tier_counts),
            verification_rate=verification_rate
        )
    
    def get_top_accounts_by_metric(self, metric: str, limit: int = 20) -> List[Tuple[GraphNode, float]]:
        """Get top accounts ranked by a specific metric"""
        discovered_accounts = [node for node in self.nodes.values() if not node.is_seed]
        
        if metric == "weighted_in_degree":
            sorted_accounts = sorted(discovered_accounts, 
                                   key=lambda x: x.weighted_in_degree, reverse=True)
            return [(acc, acc.weighted_in_degree) for acc in sorted_accounts[:limit]]
        elif metric == "pagerank":
            sorted_accounts = sorted(discovered_accounts,
                                   key=lambda x: x.pagerank_score, reverse=True)
            return [(acc, acc.pagerank_score) for acc in sorted_accounts[:limit]]
        elif metric == "follower_count":
            sorted_accounts = sorted(discovered_accounts,
                                   key=lambda x: x.follower_count, reverse=True)
            return [(acc, acc.follower_count) for acc in sorted_accounts[:limit]]
        elif metric == "in_degree":
            sorted_accounts = sorted(discovered_accounts,
                                   key=lambda x: x.in_degree, reverse=True)
            return [(acc, acc.in_degree) for acc in sorted_accounts[:limit]]
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    def find_highly_connected_accounts(self, min_connections: int = 2) -> List[Tuple[GraphNode, int]]:
        """Find accounts that are followed by multiple seed accounts"""
        discovered_accounts = [node for node in self.nodes.values() if not node.is_seed]
        highly_connected = []
        
        for account in discovered_accounts:
            connection_count = account.in_degree
            if connection_count >= min_connections:
                highly_connected.append((account, connection_count))
        
        # Sort by number of connections
        highly_connected.sort(key=lambda x: x[1], reverse=True)
        return highly_connected
    
    def analyze_tier_overlap(self) -> Dict[str, List[Tuple[str, int]]]:
        """Analyze which accounts are followed by multiple tiers"""
        tier_followers = defaultdict(lambda: defaultdict(list))
        
        # Group followers by tier for each followed account
        for edge in self.edges:
            followed_id = edge.followed_id
            follower_tier = edge.source_tier.name
            tier_followers[followed_id][follower_tier].append(edge.follower_id)
        
        # Find accounts followed by multiple tiers
        multi_tier_accounts = {}
        for followed_id, tier_data in tier_followers.items():
            if len(tier_data) > 1:  # Followed by multiple tiers
                tier_summary = []
                for tier, followers in tier_data.items():
                    tier_summary.append((tier, len(followers)))
                tier_summary.sort(key=lambda x: x[1], reverse=True)
                
                if followed_id in self.nodes:
                    account_name = f"{self.nodes[followed_id].handle} ({self.nodes[followed_id].display_name})"
                    multi_tier_accounts[account_name] = tier_summary
        
        return multi_tier_accounts
    
    def save_graph_data(self, output_prefix: str) -> None:
        """Save graph data in multiple formats"""
        # Save as GraphML (preserves all attributes)
        graphml_file = f"{output_prefix}_graph.graphml"
        nx.write_graphml(self.graph, graphml_file)
        print(f"Saved graph structure to {graphml_file}")
        
        # Save node data as JSON
        node_data = []
        for node in self.nodes.values():
            node_data.append({
                'account_id': node.account_id,
                'handle': node.handle,
                'display_name': node.display_name,
                'follower_count': node.follower_count,
                'verified': node.verified,
                'is_seed': node.is_seed,
                'seed_tier': node.seed_tier.name if node.seed_tier else None,
                'in_degree': node.in_degree,
                'weighted_in_degree': node.weighted_in_degree,
                'pagerank_score': node.pagerank_score,
                'betweenness_centrality': node.betweenness_centrality
            })
        
        nodes_file = f"{output_prefix}_nodes.json"
        with open(nodes_file, 'w', encoding='utf-8') as f:
            json.dump(node_data, f, indent=2, ensure_ascii=False)
        print(f"Saved node data to {nodes_file}")
    
    def create_summary_report(self) -> str:
        """Create a comprehensive summary report"""
        stats = self.get_graph_statistics()
        
        report = []
        report.append("=" * 60)
        report.append("GRAPH CONSTRUCTION SUMMARY")
        report.append("=" * 60)
        report.append("")
        
        # Basic Statistics
        report.append("📊 Graph Statistics:")
        report.append(f"  Total Nodes: {stats.total_nodes:,}")
        report.append(f"  Total Edges: {stats.total_edges:,}")
        report.append(f"  Seed Accounts: {stats.seed_nodes}")
        report.append(f"  Discovered Accounts: {stats.discovered_nodes:,}")
        report.append(f"  Average Degree: {stats.average_degree:.2f}")
        report.append(f"  Graph Density: {stats.graph_density:.4f}")
        report.append(f"  Connected Components: {stats.connected_components}")
        report.append(f"  Verification Rate: {stats.verification_rate:.1%}")
        report.append("")
        
        # Tier Distribution
        report.append("🏆 Seed Tier Distribution:")
        for tier, count in stats.tier_distribution.items():
            report.append(f"  {tier}: {count} accounts")
        report.append("")
        
        # Top accounts by different metrics
        report.append("🌟 Top Accounts by Weighted In-Degree:")
        top_weighted = self.get_top_accounts_by_metric("weighted_in_degree", 10)
        for i, (account, score) in enumerate(top_weighted, 1):
            verified_mark = "✓" if account.verified else " "
            report.append(f"  {i:2d}. {verified_mark} @{account.handle} ({account.display_name}) - Score: {score:.1f}")
        report.append("")
        
        # Highly connected accounts
        report.append("🔗 Accounts Followed by Multiple Seeds:")
        highly_connected = self.find_highly_connected_accounts(2)
        for account, connections in highly_connected[:10]:
            verified_mark = "✓" if account.verified else " "
            report.append(f"  {verified_mark} @{account.handle} ({account.display_name}) - {connections} seeds")
        report.append("")
        
        # Multi-tier accounts
        report.append("🎯 Accounts Followed Across Tiers:")
        multi_tier = self.analyze_tier_overlap()
        for account_name, tier_data in list(multi_tier.items())[:10]:
            tier_summary = ", ".join([f"{tier}({count})" for tier, count in tier_data])
            report.append(f"  {account_name} - {tier_summary}")
        
        return "\n".join(report)


# Example usage and testing
if __name__ == "__main__":
    # Initialize graph constructor
    constructor = FollowingGraphConstructor()
    
    # Load relationships from our previous step
    try:
        constructor.load_relationships_from_json("following_relationships.json")
        
        # Calculate metrics
        constructor.calculate_basic_metrics()
        constructor.calculate_advanced_metrics()
        
        # Generate and print report
        report = constructor.create_summary_report()
        print(report)
        
        # Save graph data
        constructor.save_graph_data("genai_following")
        
        print("\n" + "="*60)
        print("Graph construction completed successfully!")
        print("Files created:")
        print("  - genai_following_graph.graphml (graph structure)")
        print("  - genai_following_nodes.json (node data with metrics)")
        
    except FileNotFoundError:
        print("Error: following_relationships.json not found")
        print("Please run following_extractor.py first to generate the data") 
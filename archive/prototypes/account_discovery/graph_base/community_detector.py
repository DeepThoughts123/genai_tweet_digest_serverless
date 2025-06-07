import json
import networkx as nx
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, Counter
from datetime import datetime
import math

from graph_constructor import FollowingGraphConstructor, GraphNode


@dataclass
class Community:
    """Represents a detected community within the graph"""
    community_id: int
    accounts: List[str]  # Account IDs in this community
    size: int
    
    # Community characteristics
    verification_rate: float = 0.0
    avg_follower_count: float = 0.0
    seed_accounts: List[str] = field(default_factory=list)
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Network properties
    internal_edges: int = 0
    external_edges: int = 0
    modularity_contribution: float = 0.0
    
    # Community labels/topics (inferred)
    suggested_topics: List[str] = field(default_factory=list)
    representative_accounts: List[str] = field(default_factory=list)


@dataclass
class BridgeAccount:
    """Represents an account that bridges multiple communities"""
    account_id: str
    handle: str
    display_name: str
    follower_count: int
    verified: bool
    
    # Bridge characteristics
    community_connections: Dict[int, int]  # community_id -> number of connections
    bridge_score: float = 0.0
    betweenness_centrality: float = 0.0
    
    # Bridge type
    is_global_bridge: bool = False  # Connects to many communities
    is_local_bridge: bool = False   # Connects specific communities


@dataclass
class CommunityDetectionResult:
    """Results of community detection analysis"""
    algorithm_used: str
    total_communities: int
    modularity_score: float
    communities: List[Community]
    bridge_accounts: List[BridgeAccount]
    
    # Overall network characteristics
    largest_community_size: int
    smallest_community_size: int
    avg_community_size: float
    community_size_distribution: Dict[str, int]


class CommunityDetector:
    """Detects and analyzes communities in the following graph"""
    
    def __init__(self, graph_constructor: FollowingGraphConstructor):
        self.graph_constructor = graph_constructor
        self.graph = graph_constructor.graph
        self.nodes = graph_constructor.nodes
        self.communities: Dict[str, int] = {}  # account_id -> community_id
        self.community_data: List[Community] = []
        self.bridge_accounts: List[BridgeAccount] = []
        
    def detect_communities_louvain(self, resolution: float = 1.0) -> CommunityDetectionResult:
        """
        Detect communities using the Louvain algorithm.
        
        Args:
            resolution: Resolution parameter for community detection
                       Higher values = more communities, Lower values = fewer communities
        """
        print(f"Detecting communities using Louvain algorithm (resolution={resolution})")
        
        try:
            import networkx.algorithms.community as nx_comm
            
            # Apply Louvain algorithm
            communities_generator = nx_comm.louvain_communities(
                self.graph, 
                weight='weight', 
                resolution=resolution,
                seed=42  # For reproducible results
            )
            
            # Convert to list and assign community IDs
            communities_list = list(communities_generator)
            
            # Assign community IDs to accounts
            for comm_id, community_nodes in enumerate(communities_list):
                for node_id in community_nodes:
                    self.communities[node_id] = comm_id
            
            # Calculate modularity
            modularity = nx_comm.modularity(self.graph, communities_list, weight='weight')
            
            print(f"Found {len(communities_list)} communities with modularity {modularity:.3f}")
            
            # Analyze communities
            self._analyze_communities(communities_list)
            self._identify_bridge_accounts()
            
            return self._create_detection_result("Louvain", modularity)
            
        except ImportError:
            print("Warning: Advanced community detection not available. Using simple clustering.")
            return self._simple_community_detection()
    
    def detect_communities_label_propagation(self) -> CommunityDetectionResult:
        """
        Detect communities using Label Propagation algorithm.
        Faster but potentially less stable than Louvain.
        """
        print("Detecting communities using Label Propagation algorithm")
        
        try:
            import networkx.algorithms.community as nx_comm
            
            # Apply Label Propagation
            communities_generator = nx_comm.label_propagation_communities(self.graph)
            communities_list = list(communities_generator)
            
            # Assign community IDs
            for comm_id, community_nodes in enumerate(communities_list):
                for node_id in community_nodes:
                    self.communities[node_id] = comm_id
            
            # Calculate modularity
            modularity = nx_comm.modularity(self.graph, communities_list, weight='weight')
            
            print(f"Found {len(communities_list)} communities with modularity {modularity:.3f}")
            
            # Analyze communities
            self._analyze_communities(communities_list)
            self._identify_bridge_accounts()
            
            return self._create_detection_result("Label Propagation", modularity)
            
        except ImportError:
            print("Warning: Advanced community detection not available. Using simple clustering.")
            return self._simple_community_detection()
    
    def _simple_community_detection(self) -> CommunityDetectionResult:
        """
        Simple community detection based on connected components.
        Fallback when advanced algorithms are not available.
        """
        print("Using simple connected components for community detection")
        
        # Find weakly connected components
        components = list(nx.weakly_connected_components(self.graph))
        
        # Assign community IDs
        for comm_id, component in enumerate(components):
            for node_id in component:
                self.communities[node_id] = comm_id
        
        # Analyze communities
        self._analyze_communities(components)
        self._identify_bridge_accounts()
        
        # Simple modularity calculation (basic version)
        modularity = 0.0  # Would need proper calculation
        
        return self._create_detection_result("Connected Components", modularity)
    
    def _analyze_communities(self, communities_list: List[Set[str]]) -> None:
        """Analyze characteristics of detected communities"""
        self.community_data = []
        
        for comm_id, community_nodes in enumerate(communities_list):
            community_accounts = list(community_nodes)
            
            # Get node data for this community
            community_node_data = [
                self.nodes[node_id] for node_id in community_accounts 
                if node_id in self.nodes
            ]
            
            if not community_node_data:
                continue
            
            # Calculate community characteristics
            verification_rate = sum(1 for node in community_node_data if node.verified) / len(community_node_data)
            avg_follower_count = sum(node.follower_count for node in community_node_data) / len(community_node_data)
            
            # Identify seed accounts in this community
            seed_accounts = [node.account_id for node in community_node_data if node.is_seed]
            
            # Tier distribution
            tier_counts = defaultdict(int)
            for node in community_node_data:
                if node.is_seed and node.seed_tier:
                    tier_counts[node.seed_tier.name] += 1
            
            # Count internal vs external edges
            internal_edges = 0
            external_edges = 0
            
            for node_id in community_accounts:
                if node_id in self.graph:
                    for neighbor in self.graph.neighbors(node_id):
                        if neighbor in community_accounts:
                            internal_edges += 1
                        else:
                            external_edges += 1
            
            # Identify representative accounts (highest weighted in-degree in community)
            community_discovered = [node for node in community_node_data if not node.is_seed]
            community_discovered.sort(key=lambda x: x.weighted_in_degree, reverse=True)
            representative_accounts = [node.account_id for node in community_discovered[:3]]
            
            # Suggest topics based on account names/handles
            suggested_topics = self._infer_community_topics(community_node_data)
            
            community = Community(
                community_id=comm_id,
                accounts=community_accounts,
                size=len(community_accounts),
                verification_rate=verification_rate,
                avg_follower_count=avg_follower_count,
                seed_accounts=seed_accounts,
                tier_distribution=dict(tier_counts),
                internal_edges=internal_edges,
                external_edges=external_edges,
                suggested_topics=suggested_topics,
                representative_accounts=representative_accounts
            )
            
            self.community_data.append(community)
    
    def _infer_community_topics(self, community_nodes: List[GraphNode]) -> List[str]:
        """Infer likely topics for a community based on account characteristics"""
        topics = []
        
        # Count keywords in handles and names
        keyword_counts = defaultdict(int)
        
        for node in community_nodes:
            text = f"{node.handle} {node.display_name}".lower()
            
            # Research indicators
            if any(term in text for term in ["research", "lab", "university", "professor", "phd"]):
                keyword_counts["research"] += 1
            
            # Industry indicators
            if any(term in text for term in ["ceo", "founder", "company", "corp", "inc"]):
                keyword_counts["industry"] += 1
            
            # Safety indicators
            if any(term in text for term in ["safety", "alignment", "ethics", "responsible"]):
                keyword_counts["ai_safety"] += 1
            
            # Technical indicators
            if any(term in text for term in ["ml", "ai", "neural", "deep", "learning"]):
                keyword_counts["technical"] += 1
            
            # Application indicators  
            if any(term in text for term in ["product", "app", "tool", "platform"]):
                keyword_counts["applications"] += 1
        
        # Select top topics
        sorted_topics = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, count in sorted_topics[:3] if count >= 2]
        
        return topics
    
    def _identify_bridge_accounts(self) -> None:
        """Identify accounts that bridge multiple communities"""
        self.bridge_accounts = []
        
        # Analyze each discovered account (non-seeds)
        discovered_accounts = [node for node in self.nodes.values() if not node.is_seed]
        
        for account in discovered_accounts:
            # Count connections to different communities
            community_connections = defaultdict(int)
            
            # Check incoming edges (who follows this account)
            if account.account_id in self.graph:
                for predecessor in self.graph.predecessors(account.account_id):
                    if predecessor in self.communities:
                        pred_community = self.communities[predecessor]
                        community_connections[pred_community] += 1
            
            # Only consider accounts connected to multiple communities
            if len(community_connections) >= 2:
                # Calculate bridge score
                total_connections = sum(community_connections.values())
                bridge_score = len(community_connections) / total_connections if total_connections > 0 else 0
                
                # Determine bridge type
                is_global_bridge = len(community_connections) >= 3
                is_local_bridge = len(community_connections) == 2
                
                bridge_account = BridgeAccount(
                    account_id=account.account_id,
                    handle=account.handle,
                    display_name=account.display_name,
                    follower_count=account.follower_count,
                    verified=account.verified,
                    community_connections=dict(community_connections),
                    bridge_score=bridge_score,
                    betweenness_centrality=account.betweenness_centrality,
                    is_global_bridge=is_global_bridge,
                    is_local_bridge=is_local_bridge
                )
                
                self.bridge_accounts.append(bridge_account)
        
        # Sort by bridge score
        self.bridge_accounts.sort(key=lambda x: x.bridge_score, reverse=True)
    
    def _create_detection_result(self, algorithm: str, modularity: float) -> CommunityDetectionResult:
        """Create comprehensive detection result"""
        
        # Community size distribution
        sizes = [comm.size for comm in self.community_data]
        size_distribution = {
            "small (1-3)": sum(1 for s in sizes if 1 <= s <= 3),
            "medium (4-10)": sum(1 for s in sizes if 4 <= s <= 10),
            "large (11+)": sum(1 for s in sizes if s >= 11)
        }
        
        return CommunityDetectionResult(
            algorithm_used=algorithm,
            total_communities=len(self.community_data),
            modularity_score=modularity,
            communities=self.community_data,
            bridge_accounts=self.bridge_accounts,
            largest_community_size=max(sizes) if sizes else 0,
            smallest_community_size=min(sizes) if sizes else 0,
            avg_community_size=sum(sizes) / len(sizes) if sizes else 0,
            community_size_distribution=size_distribution
        )
    
    def create_community_report(self, result: CommunityDetectionResult) -> str:
        """Create comprehensive community analysis report"""
        report = []
        report.append("=" * 60)
        report.append("COMMUNITY DETECTION SUMMARY")
        report.append("=" * 60)
        report.append("")
        
        # Overall statistics
        report.append(f"🔍 Algorithm Used: {result.algorithm_used}")
        report.append(f"📊 Communities Found: {result.total_communities}")
        report.append(f"📈 Modularity Score: {result.modularity_score:.3f}")
        report.append(f"📏 Community Sizes: {result.smallest_community_size} - {result.largest_community_size} (avg: {result.avg_community_size:.1f})")
        report.append("")
        
        # Size distribution
        report.append("📊 Community Size Distribution:")
        for size_range, count in result.community_size_distribution.items():
            report.append(f"  {size_range}: {count} communities")
        report.append("")
        
        # Detailed community analysis
        report.append("🏘️ Community Analysis:")
        for i, community in enumerate(result.communities, 1):
            report.append(f"\n  Community {community.community_id} ({community.size} accounts):")
            report.append(f"    Verification Rate: {community.verification_rate:.1%}")
            report.append(f"    Avg Followers: {community.avg_follower_count:,.0f}")
            report.append(f"    Seed Accounts: {len(community.seed_accounts)}")
            
            if community.tier_distribution:
                tier_summary = ", ".join([f"{tier}({count})" for tier, count in community.tier_distribution.items()])
                report.append(f"    Tier Distribution: {tier_summary}")
            
            if community.suggested_topics:
                report.append(f"    Suggested Topics: {', '.join(community.suggested_topics)}")
            
            if community.representative_accounts:
                rep_names = []
                for acc_id in community.representative_accounts[:3]:
                    if acc_id in self.nodes:
                        rep_names.append(f"@{self.nodes[acc_id].handle}")
                if rep_names:
                    report.append(f"    Top Accounts: {', '.join(rep_names)}")
        
        # Bridge accounts analysis
        if result.bridge_accounts:
            report.append(f"\n🌉 Bridge Accounts ({len(result.bridge_accounts)} found):")
            for bridge in result.bridge_accounts[:10]:  # Top 10
                verified_mark = "✓" if bridge.verified else " "
                communities_str = ", ".join([f"C{comm_id}({count})" for comm_id, count in bridge.community_connections.items()])
                bridge_type = "Global" if bridge.is_global_bridge else "Local"
                report.append(f"  {verified_mark} @{bridge.handle} ({bridge.display_name})")
                report.append(f"    Type: {bridge_type} Bridge | Score: {bridge.bridge_score:.2f}")
                report.append(f"    Connections: {communities_str}")
        else:
            report.append("\n🌉 Bridge Accounts: None found (all accounts in single communities)")
        
        return "\n".join(report)
    
    def save_community_data(self, output_prefix: str) -> None:
        """Save community detection results to files"""
        
        # Save community assignments
        community_assignments = {}
        for account_id, community_id in self.communities.items():
            if account_id in self.nodes:
                node = self.nodes[account_id]
                community_assignments[account_id] = {
                    "handle": node.handle,
                    "display_name": node.display_name,
                    "community_id": community_id,
                    "is_seed": node.is_seed,
                    "verified": node.verified,
                    "follower_count": node.follower_count
                }
        
        assignments_file = f"{output_prefix}_community_assignments.json"
        with open(assignments_file, 'w', encoding='utf-8') as f:
            json.dump(community_assignments, f, indent=2, ensure_ascii=False)
        print(f"Saved community assignments to {assignments_file}")
        
        # Save detailed community data
        community_details = []
        for community in self.community_data:
            community_details.append({
                "community_id": community.community_id,
                "size": community.size,
                "verification_rate": community.verification_rate,
                "avg_follower_count": community.avg_follower_count,
                "seed_accounts": community.seed_accounts,
                "tier_distribution": community.tier_distribution,
                "internal_edges": community.internal_edges,
                "external_edges": community.external_edges,
                "suggested_topics": community.suggested_topics,
                "representative_accounts": community.representative_accounts
            })
        
        details_file = f"{output_prefix}_community_details.json"
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(community_details, f, indent=2, ensure_ascii=False)
        print(f"Saved community details to {details_file}")
        
        # Save bridge accounts
        if self.bridge_accounts:
            bridge_data = []
            for bridge in self.bridge_accounts:
                bridge_data.append({
                    "account_id": bridge.account_id,
                    "handle": bridge.handle,
                    "display_name": bridge.display_name,
                    "follower_count": bridge.follower_count,
                    "verified": bridge.verified,
                    "community_connections": bridge.community_connections,
                    "bridge_score": bridge.bridge_score,
                    "is_global_bridge": bridge.is_global_bridge,
                    "is_local_bridge": bridge.is_local_bridge
                })
            
            bridge_file = f"{output_prefix}_bridge_accounts.json"
            with open(bridge_file, 'w', encoding='utf-8') as f:
                json.dump(bridge_data, f, indent=2, ensure_ascii=False)
            print(f"Saved bridge accounts to {bridge_file}")


# Example usage and testing
if __name__ == "__main__":
    # Load existing graph from Step 2.1
    try:
        print("Loading graph from Step 2.1...")
        constructor = FollowingGraphConstructor()
        constructor.load_relationships_from_json("following_relationships.json")
        constructor.calculate_basic_metrics()
        constructor.calculate_advanced_metrics()
        
        print("Detecting communities...")
        detector = CommunityDetector(constructor)
        
        # Try Louvain algorithm first
        try:
            result = detector.detect_communities_louvain(resolution=1.0)
        except:
            print("Louvain not available, trying Label Propagation...")
            try:
                result = detector.detect_communities_label_propagation()
            except:
                print("Advanced algorithms not available, using simple detection...")
                result = detector.detect_communities_louvain()  # Will fall back to simple
        
        # Generate and print report
        report = detector.create_community_report(result)
        print(report)
        
        # Save results
        detector.save_community_data("genai_communities")
        
        print("\n" + "="*60)
        print("Community detection completed successfully!")
        print("Files created:")
        print("  - genai_communities_community_assignments.json")
        print("  - genai_communities_community_details.json")
        if result.bridge_accounts:
            print("  - genai_communities_bridge_accounts.json")
        
    except FileNotFoundError:
        print("Error: Required files not found")
        print("Please run the previous steps first:")
        print("1. following_extractor.py (generates following_relationships.json)")
        print("2. graph_constructor.py (builds the graph)") 
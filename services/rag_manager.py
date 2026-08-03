"""
RAG Manager - ChromaDB Vector Store for Salesforce Data
Provides semantic search and retrieval-augmented generation
"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime


class SalesforceRAGManager:
    """Manages vector store for Salesforce data with semantic search"""
    
    def __init__(self, openai_api_key: str, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB with OpenAI embeddings
        
        Args:
            openai_api_key: OpenAI API key for embeddings
            persist_directory: Local directory to persist vector store
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-small"  # Cheaper, faster
        )
        
        # Collections for different data types
        self.collections = {}
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Create or get collections for different Salesforce objects"""
        collection_names = ["leads", "opportunities", "conversations"]
        
        for name in collection_names:
            try:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"Error initializing collection {name}: {str(e)}")
    
    def index_leads(self, leads: List[Dict[str, Any]]) -> int:
        """
        Index leads into vector store
        
        Args:
            leads: List of lead dictionaries from Salesforce
            
        Returns:
            Number of leads indexed
        """
        if not leads:
            return 0
        
        collection = self.collections["leads"]
        
        documents = []
        metadatas = []
        ids = []
        
        for lead in leads:
            # Create rich text representation for embedding
            doc_text = self._lead_to_text(lead)
            documents.append(doc_text)
            
            # Store metadata for filtering
            metadatas.append({
                "name": lead.get("Name", ""),
                "company": lead.get("Company", ""),
                "status": lead.get("Status", ""),
                "rating": lead.get("Rating", ""),
                "source": lead.get("LeadSource", ""),
                "created_date": lead.get("CreatedDate", ""),
                "type": "lead"
            })
            
            # Use Salesforce ID or generate one
            lead_id = lead.get("Id", f"lead_{len(ids)}")
            ids.append(lead_id)
        
        # Add to collection
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(documents)
    
    def index_opportunities(self, opportunities: List[Dict[str, Any]]) -> int:
        """
        Index opportunities into vector store
        
        Args:
            opportunities: List of opportunity dictionaries from Salesforce
            
        Returns:
            Number of opportunities indexed
        """
        if not opportunities:
            return 0
        
        collection = self.collections["opportunities"]
        
        documents = []
        metadatas = []
        ids = []
        
        for opp in opportunities:
            # Create rich text representation
            doc_text = self._opportunity_to_text(opp)
            documents.append(doc_text)
            
            # Store metadata
            metadatas.append({
                "name": opp.get("Name", ""),
                "account": opp.get("AccountName", ""),
                "stage": opp.get("StageName", ""),
                "amount": str(opp.get("Amount", 0)),
                "probability": str(opp.get("Probability", 0)),
                "close_date": opp.get("CloseDate", ""),
                "type": "opportunity"
            })
            
            opp_id = opp.get("Id", f"opp_{len(ids)}")
            ids.append(opp_id)
        
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(documents)
    
    def index_conversation(self, user_message: str, assistant_response: str, 
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        Index conversation history for context retrieval
        
        Args:
            user_message: User's query
            assistant_response: Agent's response
            context: Additional context metadata
            
        Returns:
            Conversation ID
        """
        collection = self.collections["conversations"]
        
        # Create conversation document
        doc_text = f"User: {user_message}\nAssistant: {assistant_response}"
        
        # Metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message[:200],  # Truncate for metadata
            "type": "conversation"
        }
        
        if context:
            metadata.update({k: str(v)[:200] for k, v in context.items()})
        
        # Generate ID
        conv_id = f"conv_{datetime.now().timestamp()}"
        
        collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[conv_id]
        )
        
        return conv_id
    
    def semantic_search_leads(self, query: str, n_results: int = 5, 
                             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Semantic search for leads
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            filters: Metadata filters (e.g., {"status": "Open"})
            
        Returns:
            List of relevant leads with similarity scores
        """
        collection = self.collections["leads"]
        
        where_filter = filters if filters else None
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
        
        return self._format_results(results)
    
    def semantic_search_opportunities(self, query: str, n_results: int = 5,
                                     filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Semantic search for opportunities
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            filters: Metadata filters (e.g., {"stage": "Negotiation/Review"})
            
        Returns:
            List of relevant opportunities with similarity scores
        """
        collection = self.collections["opportunities"]
        
        where_filter = filters if filters else None
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter
        )
        
        return self._format_results(results)
    
    def search_conversation_history(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search past conversations for context
        
        Args:
            query: Query to find relevant past conversations
            n_results: Number of conversations to retrieve
            
        Returns:
            List of relevant past conversations
        """
        collection = self.collections["conversations"]
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        return self._format_results(results)
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about indexed data"""
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = collection.count()
        return stats
    
    def clear_collection(self, collection_name: str):
        """Clear all data from a collection"""
        if collection_name in self.collections:
            self.client.delete_collection(collection_name)
            self._initialize_collections()
    
    def clear_all(self):
        """Clear all collections"""
        for name in list(self.collections.keys()):
            self.clear_collection(name)
    
    def _lead_to_text(self, lead: Dict[str, Any]) -> str:
        """Convert lead to rich text for embedding"""
        parts = [
            f"Lead: {lead.get('Name', 'Unknown')}",
            f"Company: {lead.get('Company', 'N/A')}",
            f"Title: {lead.get('Title', 'N/A')}",
            f"Status: {lead.get('Status', 'N/A')}",
            f"Rating: {lead.get('Rating', 'N/A')}",
            f"Source: {lead.get('LeadSource', 'N/A')}",
            f"Industry: {lead.get('Industry', 'N/A')}",
            f"Email: {lead.get('Email', 'N/A')}",
            f"Phone: {lead.get('Phone', 'N/A')}"
        ]
        
        if lead.get('Description'):
            parts.append(f"Description: {lead['Description']}")
        
        return " | ".join(parts)
    
    def _opportunity_to_text(self, opp: Dict[str, Any]) -> str:
        """Convert opportunity to rich text for embedding"""
        parts = [
            f"Opportunity: {opp.get('Name', 'Unknown')}",
            f"Account: {opp.get('AccountName', 'N/A')}",
            f"Stage: {opp.get('StageName', 'N/A')}",
            f"Amount: ${opp.get('Amount', 0):,.0f}",
            f"Probability: {opp.get('Probability', 0)}%",
            f"Close Date: {opp.get('CloseDate', 'N/A')}",
            f"Type: {opp.get('Type', 'N/A')}",
            f"Lead Source: {opp.get('LeadSource', 'N/A')}"
        ]
        
        if opp.get('Description'):
            parts.append(f"Description: {opp['Description']}")
        
        if opp.get('NextStep'):
            parts.append(f"Next Step: {opp['NextStep']}")
        
        return " | ".join(parts)
    
    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB results into clean list"""
        formatted = []
        
        if not results['ids'] or not results['ids'][0]:
            return formatted
        
        for i, doc_id in enumerate(results['ids'][0]):
            formatted.append({
                'id': doc_id,
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted

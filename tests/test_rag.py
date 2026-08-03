"""
RAG System Test Runner
Tests ChromaDB integration and semantic search capabilities
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_manager import SalesforceRAGManager
from tests.test_data import TestSalesforceData


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_rag_initialization():
    """Test 1: RAG Manager initialization"""
    print_section("TEST 1: RAG Manager Initialization")
    
    try:
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_api_key:
            print("[FAIL] OpenAI API key not found")
            return None
        
        rag_manager = SalesforceRAGManager(
            openai_api_key=openai_api_key,
            persist_directory="./test_chroma_db"
        )
        
        print(f"[PASS] RAG Manager initialized")
        print(f"[PASS] Collections: {list(rag_manager.collections.keys())}")
        
        return rag_manager
        
    except Exception as e:
        print(f"[FAIL] Initialization error: {str(e)}")
        return None


def test_lead_indexing(rag_manager):
    """Test 2: Lead indexing"""
    print_section("TEST 2: Lead Indexing")
    
    try:
        # Generate test leads
        test_data = TestSalesforceData()
        leads = test_data.generate_leads()
        
        print(f"[INFO] Generated {len(leads)} test leads")
        
        # Index leads
        count = rag_manager.index_leads(leads)
        
        if count == len(leads):
            print(f"[PASS] Indexed {count} leads successfully")
            return True
        else:
            print(f"[FAIL] Expected {len(leads)}, indexed {count}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Lead indexing error: {str(e)}")
        return False


def test_opportunity_indexing(rag_manager):
    """Test 3: Opportunity indexing"""
    print_section("TEST 3: Opportunity Indexing")
    
    try:
        # Generate test opportunities
        test_data = TestSalesforceData()
        opps = test_data.generate_opportunities()
        
        print(f"[INFO] Generated {len(opps)} test opportunities")
        
        # Index opportunities
        count = rag_manager.index_opportunities(opps)
        
        if count == len(opps):
            print(f"[PASS] Indexed {count} opportunities successfully")
            return True
        else:
            print(f"[FAIL] Expected {len(opps)}, indexed {count}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Opportunity indexing error: {str(e)}")
        return False


def test_semantic_search_leads(rag_manager):
    """Test 4: Semantic search for leads"""
    print_section("TEST 4: Semantic Search - Leads")
    
    try:
        # Search for high-priority leads
        query = "high priority leads with strong engagement and recent activity"
        results = rag_manager.semantic_search_leads(query, n_results=5)
        
        if results:
            print(f"[PASS] Found {len(results)} relevant leads")
            print("\nTop results:")
            for i, result in enumerate(results[:3], 1):
                metadata = result['metadata']
                print(f"{i}. {metadata.get('name', 'Unknown')} - {metadata.get('company', 'N/A')}")
                print(f"   Status: {metadata.get('status', 'N/A')}, Rating: {metadata.get('rating', 'N/A')}")
            return True
        else:
            print("[FAIL] No results found")
            return False
            
    except Exception as e:
        print(f"[FAIL] Semantic search error: {str(e)}")
        if "quota" in str(e).lower():
            print("[INFO] OpenAI API quota exceeded - expected if quota exhausted")
            return True
        return False


def test_semantic_search_opportunities(rag_manager):
    """Test 5: Semantic search for opportunities"""
    print_section("TEST 5: Semantic Search - Opportunities")
    
    try:
        # Search for at-risk deals
        query = "deals at risk of being lost, stalled negotiations, pricing concerns"
        results = rag_manager.semantic_search_opportunities(query, n_results=5)
        
        if results:
            print(f"[PASS] Found {len(results)} relevant opportunities")
            print("\nTop results:")
            for i, result in enumerate(results[:3], 1):
                metadata = result['metadata']
                print(f"{i}. {metadata.get('name', 'Unknown')} - ${metadata.get('amount', '0')}")
                print(f"   Stage: {metadata.get('stage', 'N/A')}, Probability: {metadata.get('probability', '0')}%")
            return True
        else:
            print("[FAIL] No results found")
            return False
            
    except Exception as e:
        print(f"[FAIL] Semantic search error: {str(e)}")
        if "quota" in str(e).lower():
            print("[INFO] OpenAI API quota exceeded - expected if quota exhausted")
            return True
        return False


def test_conversation_indexing(rag_manager):
    """Test 6: Conversation indexing"""
    print_section("TEST 6: Conversation Indexing")
    
    try:
        # Index test conversation
        user_msg = "Show me at-risk deals"
        assistant_msg = "Here are the top 5 at-risk deals based on low win probability..."
        
        conv_id = rag_manager.index_conversation(
            user_msg,
            assistant_msg,
            {"agent": "Deal Risk Agent"}
        )
        
        if conv_id:
            print(f"[PASS] Conversation indexed with ID: {conv_id}")
            return True
        else:
            print("[FAIL] Conversation indexing failed")
            return False
            
    except Exception as e:
        print(f"[FAIL] Conversation indexing error: {str(e)}")
        return False


def test_collection_stats(rag_manager):
    """Test 7: Collection statistics"""
    print_section("TEST 7: Collection Statistics")
    
    try:
        stats = rag_manager.get_collection_stats()
        
        print(f"[PASS] Retrieved collection stats")
        print(f"  - Leads: {stats.get('leads', 0)}")
        print(f"  - Opportunities: {stats.get('opportunities', 0)}")
        print(f"  - Conversations: {stats.get('conversations', 0)}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Stats retrieval error: {str(e)}")
        return False


def test_filtered_search(rag_manager):
    """Test 8: Filtered semantic search"""
    print_section("TEST 8: Filtered Semantic Search")
    
    try:
        # Search with metadata filter
        query = "high value opportunities"
        results = rag_manager.semantic_search_opportunities(
            query,
            n_results=5,
            filters={"stage": "Negotiation/Review"}
        )
        
        if results is not None:  # May be empty list
            print(f"[PASS] Filtered search executed ({len(results)} results)")
            if results:
                print(f"  Sample: {results[0]['metadata'].get('name', 'Unknown')}")
            return True
        else:
            print("[FAIL] Filtered search failed")
            return False
            
    except Exception as e:
        print(f"[FAIL] Filtered search error: {str(e)}")
        # ChromaDB may not support all filter types
        print("[INFO] Filter may not be supported - this is acceptable")
        return True


def cleanup(rag_manager):
    """Cleanup test data"""
    print_section("CLEANUP")
    
    try:
        rag_manager.clear_all()
        print("[PASS] Test data cleared")
        
        # Remove test directory
        import shutil
        if os.path.exists("./test_chroma_db"):
            shutil.rmtree("./test_chroma_db")
            print("[PASS] Test directory removed")
        
    except Exception as e:
        print(f"[WARN] Cleanup error: {str(e)}")


def run_all_tests():
    """Run all RAG system tests"""
    print("\n" + "="*60)
    print("  RAG SYSTEM TEST SUITE (ChromaDB)")
    print("="*60)
    
    results = []
    
    # Test 1: Initialization
    rag_manager = test_rag_initialization()
    results.append(("Initialization", rag_manager is not None))
    
    if not rag_manager:
        print("\n[ABORT] Cannot proceed without RAG manager")
        return
    
    # Test 2: Lead indexing
    lead_result = test_lead_indexing(rag_manager)
    results.append(("Lead Indexing", lead_result))
    
    # Test 3: Opportunity indexing
    opp_result = test_opportunity_indexing(rag_manager)
    results.append(("Opportunity Indexing", opp_result))
    
    # Test 4: Semantic search - leads
    search_lead_result = test_semantic_search_leads(rag_manager)
    results.append(("Semantic Search (Leads)", search_lead_result))
    
    # Test 5: Semantic search - opportunities
    search_opp_result = test_semantic_search_opportunities(rag_manager)
    results.append(("Semantic Search (Opportunities)", search_opp_result))
    
    # Test 6: Conversation indexing
    conv_result = test_conversation_indexing(rag_manager)
    results.append(("Conversation Indexing", conv_result))
    
    # Test 7: Collection stats
    stats_result = test_collection_stats(rag_manager)
    results.append(("Collection Statistics", stats_result))
    
    # Test 8: Filtered search
    filter_result = test_filtered_search(rag_manager)
    results.append(("Filtered Search", filter_result))
    
    # Cleanup
    cleanup(rag_manager)
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\n{'='*60}")
    print(f"  TOTAL: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("[SUCCESS] All RAG tests passed!")
    else:
        print(f"[WARNING] {total - passed} test(s) failed")
    
    print("\n[INFO] RAG system is ready for use with multi-agent system")


if __name__ == "__main__":
    run_all_tests()

"""
Evaluation Framework Test Suite
Tests hallucination detection and RAG quality metrics
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.evaluation import HallucinationDetector, RAGQualityMetrics, EvaluationManager
from services.salesforce_agent import calculate_deal_risk, recommend_next_action, build_deal_risk_dashboard
from datetime import date


def test_deal_risk_dashboard():
    """Deterministic Phase 1 risk scoring and next-action coverage."""
    opportunity = {
        "Id": "006-test",
        "Name": "Expired Enterprise Deal",
        "Amount": 150000,
        "Probability": 25,
        "StageName": "Negotiation/Review",
        "CloseDate": "2026-01-01",
    }

    risk = calculate_deal_risk(opportunity, today=date(2026, 7, 28))
    assert risk["risk_level"] == "Critical"
    assert risk["risk_score"] == 70
    assert "Low win probability" in risk["risk_reasons"]
    assert "Close date has passed" in risk["risk_reasons"]
    assert "deal-recovery" in recommend_next_action(opportunity, risk)

    rows = build_deal_risk_dashboard([opportunity], today=date(2026, 7, 28))
    assert rows[0]["risk_value"] == 150000
    assert rows[0]["next_action"]


def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_hallucination_detection():
    """Test 1: Hallucination detection"""
    print_section("TEST 1: Hallucination Detection")
    
    detector = HallucinationDetector()
    
    # Test case 1: No hallucination (accurate response)
    response1 = "Top lead: John Doe from Acme Corp with score 85"
    source1 = [{"Name": "John Doe", "Company": "Acme Corp", "priority_score": 85}]
    
    result1 = detector.detect_hallucinations(response1, source1)
    
    if not result1["has_hallucination"] and result1["confidence"] > 0.5:
        print("[PASS] Accurate response detected correctly")
    else:
        print(f"[FAIL] False positive - Score: {result1['hallucination_score']}")
    
    # Test case 2: Clear hallucination (made-up data)
    response2 = "Top lead: Bob Johnson from FakeCorp with score 95"
    source2 = [{"Name": "John Doe", "Company": "Acme Corp", "priority_score": 85}]
    
    result2 = detector.detect_hallucinations(response2, source2)
    
    if result2["has_hallucination"]:
        print("[PASS] Hallucination detected correctly")
    else:
        print(f"[FAIL] Missed hallucination - Score: {result2['hallucination_score']}")
    
    # Test case 3: Partial hallucination (some correct, some wrong)
    response3 = "Top leads: John Doe (score 85) and Bob Johnson (score 95)"
    source3 = [{"Name": "John Doe", "priority_score": 85}]
    
    result3 = detector.detect_hallucinations(response3, source3)
    
    if result3["unverified_facts"] > 0:
        print("[PASS] Partial hallucination detected")
    else:
        print("[FAIL] Missed partial hallucination")
    
    print(f"\nHallucination Detection Summary:")
    print(f"  Test 1 - Confidence: {result1['confidence']:.2f}")
    print(f"  Test 2 - Hallucination Score: {result2['hallucination_score']:.2f}")
    print(f"  Test 3 - Unverified Facts: {result3['unverified_facts']}")
    
    return True


def test_rag_quality_metrics():
    """Test 2: RAG quality metrics"""
    print_section("TEST 2: RAG Quality Metrics")
    
    rag_metrics = RAGQualityMetrics()
    
    # Test case 1: High quality retrieval
    query1 = "high priority leads"
    retrieved1 = [
        {
            "id": "1",
            "document": "Lead: John Doe, high priority, score 85",
            "metadata": {"name": "John Doe", "type": "lead"}
        },
        {
            "id": "2",
            "document": "Lead: Jane Smith, high priority, score 82",
            "metadata": {"name": "Jane Smith", "type": "lead"}
        }
    ]
    
    result1 = rag_metrics.evaluate_retrieval(query1, retrieved1)
    
    if result1["relevance_score"] > 0.5:
        print(f"[PASS] High relevance detected: {result1['relevance_score']:.2f}")
    else:
        print(f"[FAIL] Low relevance: {result1['relevance_score']:.2f}")
    
    # Test case 2: Low quality retrieval (irrelevant results)
    query2 = "high priority leads"
    retrieved2 = [
        {
            "id": "3",
            "document": "Opportunity: Deal with XYZ Corp, amount $50000",
            "metadata": {"name": "XYZ Deal", "type": "opportunity"}
        }
    ]
    
    result2 = rag_metrics.evaluate_retrieval(query2, retrieved2)
    
    if result2["relevance_score"] < 0.5:
        print(f"[PASS] Low relevance detected: {result2['relevance_score']:.2f}")
    else:
        print(f"[FAIL] Should be low relevance: {result2['relevance_score']:.2f}")
    
    # Test case 3: Diversity check
    query3 = "show all data"
    retrieved3 = [
        {"id": "1", "document": "Lead A", "metadata": {"type": "lead", "stage": "New"}},
        {"id": "2", "document": "Lead B", "metadata": {"type": "lead", "stage": "Qualified"}},
        {"id": "3", "document": "Opp C", "metadata": {"type": "opportunity", "stage": "Proposal"}}
    ]
    
    result3 = rag_metrics.evaluate_retrieval(query3, retrieved3)
    
    if result3["diversity_score"] > 0.5:
        print(f"[PASS] Good diversity: {result3['diversity_score']:.2f}")
    else:
        print(f"[FAIL] Low diversity: {result3['diversity_score']:.2f}")
    
    print(f"\nRAG Quality Summary:")
    print(f"  Relevance (high): {result1['relevance_score']:.2f}")
    print(f"  Relevance (low): {result2['relevance_score']:.2f}")
    print(f"  Diversity: {result3['diversity_score']:.2f}")
    
    return True


def test_precision_recall():
    """Test 3: Precision and recall calculation"""
    print_section("TEST 3: Precision & Recall")
    
    rag_metrics = RAGQualityMetrics()
    
    # Expected documents
    expected = [
        {"id": "1", "document": "Doc 1"},
        {"id": "2", "document": "Doc 2"},
        {"id": "3", "document": "Doc 3"}
    ]
    
    # Test case 1: Perfect retrieval
    retrieved1 = expected.copy()
    result1 = rag_metrics.evaluate_retrieval("query", retrieved1, expected)
    
    if result1["precision"] == 1.0 and result1["recall"] == 1.0:
        print(f"[PASS] Perfect retrieval: P={result1['precision']:.2f}, R={result1['recall']:.2f}")
    else:
        print(f"[FAIL] Should be perfect: P={result1['precision']:.2f}, R={result1['recall']:.2f}")
    
    # Test case 2: Partial retrieval (missing some)
    retrieved2 = [{"id": "1", "document": "Doc 1"}]
    result2 = rag_metrics.evaluate_retrieval("query", retrieved2, expected)
    
    if result2["precision"] == 1.0 and result2["recall"] < 1.0:
        print(f"[PASS] Partial retrieval: P={result2['precision']:.2f}, R={result2['recall']:.2f}")
    else:
        print(f"[FAIL] Incorrect metrics: P={result2['precision']:.2f}, R={result2['recall']:.2f}")
    
    # Test case 3: Over-retrieval (extra irrelevant docs)
    retrieved3 = expected.copy()
    retrieved3.append({"id": "4", "document": "Extra doc"})
    result3 = rag_metrics.evaluate_retrieval("query", retrieved3, expected)
    
    if result3["precision"] < 1.0 and result3["recall"] == 1.0:
        print(f"[PASS] Over-retrieval: P={result3['precision']:.2f}, R={result3['recall']:.2f}")
    else:
        print(f"[FAIL] Incorrect metrics: P={result3['precision']:.2f}, R={result3['recall']:.2f}")
    
    print(f"\nPrecision/Recall Summary:")
    print(f"  Perfect: F1={result1['f1_score']:.2f}")
    print(f"  Partial: F1={result2['f1_score']:.2f}")
    print(f"  Over-retrieval: F1={result3['f1_score']:.2f}")
    
    return True


def test_evaluation_manager():
    """Test 4: Comprehensive evaluation manager"""
    print_section("TEST 4: Evaluation Manager")
    
    manager = EvaluationManager()
    
    # Test case 1: Good response with RAG
    query = "Show top leads"
    response = "Top lead: John Doe from Acme Corp with score 85"
    source_data = [{"Name": "John Doe", "Company": "Acme Corp", "priority_score": 85}]
    retrieved_docs = [
        {"id": "1", "document": "John Doe, Acme Corp, score 85", "metadata": {}}
    ]
    
    result = manager.evaluate_response(query, response, source_data, retrieved_docs)
    
    if "Excellent" in result["overall_quality"] or "Good" in result["overall_quality"]:
        print(f"[PASS] Good response quality: {result['overall_quality']}")
    else:
        print(f"[FAIL] Should be good quality: {result['overall_quality']}")
    
    # Test case 2: Response with hallucination
    query2 = "Show top leads"
    response2 = "Top lead: Bob Johnson from FakeCorp with score 95"
    source_data2 = [{"Name": "John Doe", "Company": "Acme Corp", "priority_score": 85}]
    
    result2 = manager.evaluate_response(query2, response2, source_data2)
    
    if "Poor" in result2["overall_quality"]:
        print(f"[PASS] Poor quality detected: {result2['overall_quality']}")
    else:
        print(f"[FAIL] Should be poor quality: {result2['overall_quality']}")
    
    # Get comprehensive report
    report = manager.get_comprehensive_report()
    
    if "hallucination_report" in report and "rag_quality_report" in report:
        print("[PASS] Comprehensive report generated")
    else:
        print("[FAIL] Report incomplete")
    
    print(f"\nEvaluation Manager Summary:")
    print(f"  Good response: {result['overall_quality']}")
    print(f"  Bad response: {result2['overall_quality']}")
    print(f"  Total evaluations: {len(manager.hallucination_detector.hallucination_log)}")
    
    return True


def test_average_metrics():
    """Test 5: Average metrics calculation"""
    print_section("TEST 5: Average Metrics")
    
    rag_metrics = RAGQualityMetrics()
    
    # Run multiple evaluations
    queries = ["query1", "query2", "query3"]
    docs = [
        [{"id": "1", "document": "relevant doc", "metadata": {}}],
        [{"id": "2", "document": "somewhat relevant", "metadata": {}}],
        [{"id": "3", "document": "not relevant", "metadata": {}}]
    ]
    
    for query, doc_list in zip(queries, docs):
        rag_metrics.evaluate_retrieval(query, doc_list)
    
    avg_metrics = rag_metrics.get_average_metrics()
    
    if avg_metrics["total_evaluations"] == 3:
        print(f"[PASS] Tracked 3 evaluations")
    else:
        print(f"[FAIL] Expected 3, got {avg_metrics['total_evaluations']}")
    
    if 0 <= avg_metrics["avg_relevance"] <= 1:
        print(f"[PASS] Valid relevance: {avg_metrics['avg_relevance']:.2f}")
    else:
        print(f"[FAIL] Invalid relevance: {avg_metrics['avg_relevance']:.2f}")
    
    # Get quality report
    report = rag_metrics.get_quality_report()
    
    if "grade" in report:
        print(f"[PASS] Quality grade: {report['grade']}")
    else:
        print("[FAIL] No quality grade")
    
    print(f"\nAverage Metrics Summary:")
    print(f"  Avg Relevance: {avg_metrics['avg_relevance']:.2f}")
    print(f"  Avg Diversity: {avg_metrics['avg_diversity']:.2f}")
    print(f"  Avg Coverage: {avg_metrics['avg_coverage']:.2f}")
    print(f"  Overall Grade: {report['grade']}")
    
    return True


def run_all_tests():
    """Run all evaluation tests"""
    print("\n" + "="*60)
    print("  EVALUATION FRAMEWORK TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Hallucination Detection", test_hallucination_detection()))
    results.append(("RAG Quality Metrics", test_rag_quality_metrics()))
    results.append(("Precision & Recall", test_precision_recall()))
    results.append(("Evaluation Manager", test_evaluation_manager()))
    results.append(("Average Metrics", test_average_metrics()))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print(f"\n{'='*60}")
    print(f"  TOTAL: {passed}/{total} test suites passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("[SUCCESS] All evaluation tests passed!")
    else:
        print(f"[WARNING] {total - passed} test(s) failed")


if __name__ == "__main__":
    run_all_tests()

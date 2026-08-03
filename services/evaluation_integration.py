"""
Evaluation Integration Examples
Shows how to integrate hallucination detection and RAG quality metrics into apps
"""

from services.evaluation import EvaluationManager
import streamlit as st
from typing import Dict, Any, List


# ==================== INTEGRATION WITH SINGLE AGENT ====================

def integrate_evaluation_single_agent():
    """
    Example: Add evaluation to app_single_agent.py (single agent)
    
    Add this code after getting AI response in Tab 4
    """
    
    # After getting response from agent
    # response = st.session_state.chat_agent.chat(user_input)
    
    # Initialize evaluator
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = EvaluationManager()
    
    # Get source data (leads/opportunities used)
    source_data = []
    # Add leads if query mentions leads
    if 'lead' in user_input.lower():
        source_data.extend(st.session_state.chat_agent._get_leads_cached())
    # Add opportunities if query mentions opportunities
    if 'opportunit' in user_input.lower() or 'deal' in user_input.lower():
        source_data.extend(st.session_state.chat_agent._get_opportunities_cached())
    
    # Evaluate response
    evaluation = st.session_state.evaluator.evaluate_response(
        query=user_input,
        response=response,
        source_data=source_data
    )
    
    # Display quality indicator
    quality = evaluation["overall_quality"]
    
    if "Excellent" in quality:
        st.success(f"✅ Response Quality: {quality}")
    elif "Good" in quality:
        st.info(f"ℹ️ Response Quality: {quality}")
    elif "Fair" in quality:
        st.warning(f"⚠️ Response Quality: {quality}")
    else:
        st.error(f"❌ Response Quality: {quality}")
    
    # Show hallucination warning if detected
    if evaluation["hallucination_check"]["has_hallucination"]:
        st.warning("⚠️ Potential hallucination detected. Please verify information.")
        with st.expander("View Issues"):
            for issue in evaluation["hallucination_check"]["issues"]:
                st.write(f"- {issue}")


# ==================== INTEGRATION WITH MULTI-AGENT ====================

def integrate_evaluation_multi_agent():
    """
    Example: Add evaluation to app_multi_agent.py
    
    Add this code in process_message() function
    """
    
    # Initialize evaluator
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = EvaluationManager()
    
    # After getting response from orchestrator
    # response = await orchestrator.chat_async(message)
    
    # Get source data from Salesforce
    source_data = []
    try:
        leads = st.session_state.orchestrator.salesforce_agent.get_leads()
        opps = st.session_state.orchestrator.salesforce_agent.get_opportunities()
        source_data.extend(leads)
        source_data.extend(opps)
    except:
        pass
    
    # Get RAG retrieved docs if RAG enabled
    retrieved_docs = None
    if st.session_state.rag_enabled and st.session_state.rag_manager:
        try:
            # Get recent RAG searches
            retrieved_docs = []  # Would come from RAG manager
        except:
            pass
    
    # Evaluate
    evaluation = st.session_state.evaluator.evaluate_response(
        query=message,
        response=response,
        source_data=source_data,
        retrieved_docs=retrieved_docs
    )
    
    # Return evaluation with response
    return response, evaluation


# ==================== EVALUATION DASHBOARD ====================

def create_evaluation_dashboard():
    """Create Streamlit dashboard for evaluation metrics"""
    
    st.title("📊 Evaluation Dashboard")
    
    if 'evaluator' not in st.session_state:
        st.warning("No evaluation data available. Start chatting to generate metrics.")
        return
    
    evaluator = st.session_state.evaluator
    
    # Get comprehensive report
    report = evaluator.get_comprehensive_report()
    
    # Hallucination metrics
    st.header("🎯 Hallucination Detection")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_evals = report["hallucination_report"]["total_evaluations"]
        st.metric("Total Evaluations", total_evals)
    
    with col2:
        hallucinations = report["hallucination_report"]["hallucinations_detected"]
        st.metric("Hallucinations Detected", hallucinations)
    
    with col3:
        rate = report["hallucination_report"]["hallucination_rate"]
        st.metric("Hallucination Rate", f"{rate:.1%}")
    
    # Recent issues
    if report["hallucination_report"]["recent_issues"]:
        st.subheader("Recent Issues")
        for issue in report["hallucination_report"]["recent_issues"]:
            with st.expander(f"Issue at {issue['timestamp'][:19]}"):
                st.write(f"**Query:** {issue['query']}")
                st.write(f"**Score:** {issue['hallucination_score']:.2f}")
                st.write("**Issues:**")
                for i in issue['issues']:
                    st.write(f"- {i}")
    
    st.markdown("---")
    
    # RAG quality metrics
    st.header("🔍 RAG Quality Metrics")
    
    rag_report = report["rag_quality_report"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Overall Score", f"{rag_report['overall_score']:.2f}")
        st.metric("Quality Grade", rag_report['grade'])
    
    with col2:
        metrics = rag_report['metrics']
        st.metric("Avg Relevance", f"{metrics['avg_relevance']:.2f}")
        st.metric("Avg Diversity", f"{metrics['avg_diversity']:.2f}")
        st.metric("Avg Coverage", f"{metrics['avg_coverage']:.2f}")
    
    # Export button
    st.markdown("---")
    if st.button("Export Metrics"):
        filepath = evaluator.export_metrics("evaluation_report.json")
        st.success(f"Metrics exported to {filepath}")


# ==================== REAL-TIME QUALITY INDICATOR ====================

def show_quality_indicator(evaluation: Dict[str, Any]):
    """Display real-time quality indicator in chat"""
    
    quality = evaluation["overall_quality"]
    confidence = evaluation["hallucination_check"]["confidence"]
    
    # Color-coded quality badge
    if "Excellent" in quality:
        color = "green"
        icon = "✅"
    elif "Good" in quality:
        color = "blue"
        icon = "ℹ️"
    elif "Fair" in quality:
        color = "orange"
        icon = "⚠️"
    else:
        color = "red"
        icon = "❌"
    
    st.markdown(f"""
    <div style="background-color: {color}; padding: 0.5rem; border-radius: 5px; color: white; text-align: center;">
        {icon} Quality: {quality} | Confidence: {confidence:.0%}
    </div>
    """, unsafe_allow_html=True)


# ==================== BATCH EVALUATION ====================

def batch_evaluate_responses(queries_and_responses: List[Dict[str, Any]], 
                            source_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Batch evaluate multiple responses
    
    Args:
        queries_and_responses: List of {"query": str, "response": str}
        source_data: Salesforce data
        
    Returns:
        Aggregated evaluation results
    """
    evaluator = EvaluationManager()
    
    results = []
    for item in queries_and_responses:
        result = evaluator.evaluate_response(
            query=item["query"],
            response=item["response"],
            source_data=source_data
        )
        results.append(result)
    
    # Aggregate results
    total = len(results)
    hallucinations = sum(1 for r in results if r["hallucination_check"]["has_hallucination"])
    avg_confidence = sum(r["hallucination_check"]["confidence"] for r in results) / total
    
    excellent = sum(1 for r in results if "Excellent" in r["overall_quality"])
    good = sum(1 for r in results if "Good" in r["overall_quality"])
    fair = sum(1 for r in results if "Fair" in r["overall_quality"])
    poor = sum(1 for r in results if "Poor" in r["overall_quality"])
    
    return {
        "total_evaluated": total,
        "hallucinations_detected": hallucinations,
        "hallucination_rate": hallucinations / total,
        "avg_confidence": avg_confidence,
        "quality_distribution": {
            "excellent": excellent,
            "good": good,
            "fair": fair,
            "poor": poor
        }
    }


# ==================== USAGE IN app_single_agent.py ====================

def app_single_agent_integration_example():
    """
    Complete example for app_single_agent.py integration
    """
    
    # In Tab 4 (AI Chat), after getting response:
    
    # 1. Initialize evaluator
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = EvaluationManager()
    
    # 2. Get response
    full_response = st.session_state.chat_agent.chat(user_input)
    
    # 3. Get source data
    source_data = []
    if 'lead' in user_input.lower():
        source_data.extend(st.session_state.chat_agent._get_leads_cached())
    if 'opportunit' in user_input.lower():
        source_data.extend(st.session_state.chat_agent._get_opportunities_cached())
    
    # 4. Evaluate
    evaluation = st.session_state.evaluator.evaluate_response(
        query=user_input,
        response=full_response,
        source_data=source_data
    )
    
    # 5. Display response with quality indicator
    message_placeholder.markdown(full_response)
    show_quality_indicator(evaluation)
    
    # 6. Add to history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": full_response,
        "evaluation": evaluation
    })


# ==================== USAGE IN APP_MULTI_AGENT.PY ====================

def app_multi_agent_integration_example():
    """
    Complete example for app_multi_agent.py integration
    """
    
    # In process_message() function:
    
    # 1. Initialize evaluator
    if 'evaluator' not in st.session_state:
        st.session_state.evaluator = EvaluationManager()
    
    # 2. Get response
    response = process_message(prompt)
    
    # 3. Get source data
    source_data = []
    try:
        leads = st.session_state.orchestrator.salesforce_agent.get_leads()
        opps = st.session_state.orchestrator.salesforce_agent.get_opportunities()
        source_data.extend(leads)
        source_data.extend(opps)
    except:
        pass
    
    # 4. Get RAG docs if enabled
    retrieved_docs = None
    if st.session_state.rag_enabled:
        # Would get from RAG manager
        pass
    
    # 5. Evaluate
    evaluation = st.session_state.evaluator.evaluate_response(
        query=prompt,
        response=response,
        source_data=source_data,
        retrieved_docs=retrieved_docs
    )
    
    # 6. Display with quality
    st.markdown(response)
    show_quality_indicator(evaluation)
    
    # 7. Show RAG metrics if available
    if evaluation.get("rag_quality"):
        rag = evaluation["rag_quality"]
        st.caption(f"RAG: Relevance {rag['relevance_score']:.2f} | Diversity {rag['diversity_score']:.2f}")


# ==================== SIDEBAR METRICS ====================

def add_evaluation_metrics_to_sidebar():
    """Add evaluation metrics to sidebar"""
    
    if 'evaluator' not in st.session_state:
        return
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Quality Metrics")
    
    report = st.session_state.evaluator.get_comprehensive_report()
    
    # Hallucination rate
    rate = report["hallucination_report"]["hallucination_rate"]
    if rate == 0:
        st.sidebar.success(f"✅ No hallucinations")
    elif rate < 0.1:
        st.sidebar.info(f"ℹ️ {rate:.1%} hallucination rate")
    else:
        st.sidebar.warning(f"⚠️ {rate:.1%} hallucination rate")
    
    # RAG quality
    if report["rag_quality_report"]["metrics"]["total_evaluations"] > 0:
        grade = report["rag_quality_report"]["grade"]
        st.sidebar.write(f"RAG Quality: {grade}")


if __name__ == "__main__":
    print("Evaluation Integration Examples")
    print("=" * 50)
    print("\nTo integrate evaluation:")
    print("1. Import: from services.evaluation import EvaluationManager")
    print("2. Initialize: evaluator = EvaluationManager()")
    print("3. Evaluate: evaluation = evaluator.evaluate_response(...)")
    print("4. Display: show_quality_indicator(evaluation)")


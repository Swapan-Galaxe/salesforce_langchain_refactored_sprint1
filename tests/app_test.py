import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.test_config import get_test_agent  # Use test configuration
from skills.prioritization_simple import LeadPrioritizer, OpportunityScorer, FollowUpGenerator
from agents.conversational_agent_enhanced import ConversationalSalesAgentEnhanced
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

load_dotenv()

st.set_page_config(page_title="Salesforce AI Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# Custom CSS (same as original)
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3rem;
        font-weight: bold;
    }
    .lead-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .opp-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .test-mode-banner {
        background: linear-gradient(90deg, #ff6b6b 0%, #ffa500 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Check if we're in test mode
use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

# Test mode banner
if use_mock_data:
    st.markdown("""
    <div class="test-mode-banner">
        🧪 TEST MODE ACTIVE - Using Mock Data (No Salesforce API Calls)
        <br><small>Set USE_MOCK_DATA=false in .env to use real Salesforce data</small>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚀 Salesforce AI Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-powered lead prioritization and opportunity scoring with real-time analytics</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.salesforce.com/content/dam/sfdc-docs/www/logos/logo-salesforce.svg", width=200)
    st.markdown("---")
    st.header("⚙️ Configuration")
    
    # Test mode indicator
    if use_mock_data:
        st.info("🧪 **TEST MODE**\nUsing mock data")
    else:
        st.success("🔗 **LIVE MODE**\nUsing Salesforce API")
    
    limit = st.slider("📊 Records to Analyze", 5, 50, 20, help="Number of leads and opportunities to fetch")
    cache_ttl = st.slider("⏱️ Cache Duration (seconds)", 60, 600, 300, help="How long to cache Salesforce data")
    
    st.markdown("---")
    
    if st.button("🚀 Run AI Analysis", type="primary", use_container_width=True):
        st.session_state.run_analysis = True
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        if 'chat_agent' in st.session_state:
            st.session_state.chat_agent.refresh_cache()
            st.success("Cache refreshed!")
    
    # Test data controls (only show in test mode)
    if use_mock_data:
        st.markdown("---")
        st.markdown("### 🧪 Test Controls")
        if st.button("📊 Show Test Data Summary", use_container_width=True):
            st.session_state.show_test_summary = True
        
        if st.button("💾 Export Test Data", use_container_width=True):
            from tests.test_data import TestSalesforceData
            test_data = TestSalesforceData()
            test_data.export_to_json()
            st.success("Test data exported to JSON files!")
    
    st.markdown("---")
    st.markdown("### 📋 Features")
    st.markdown("✅ AI Lead Scoring")
    st.markdown("✅ Opportunity Analysis")
    st.markdown("✅ Follow-up Generation")
    st.markdown("✅ Real-time Dashboards")
    st.markdown("✅ Conversational AI")
    
    st.markdown("---")
    st.caption("Powered by OpenAI GPT-4 + LangChain")

# Show test data summary if requested
if use_mock_data and st.session_state.get('show_test_summary', False):
    st.markdown("## 🧪 Test Data Summary")
    
    # Create a test agent to get summary
    test_agent = get_test_agent(limit=100)
    if hasattr(test_agent, 'get_test_data_summary'):
        summary = test_agent.get_test_data_summary()
        st.code(summary)
    
    if st.button("❌ Hide Summary"):
        st.session_state.show_test_summary = False
        st.rerun()

# Main content
if 'run_analysis' in st.session_state and st.session_state.run_analysis:
    
    with st.spinner("Connecting to data source..."):
        # Use test configuration to get appropriate agent
        agent = get_test_agent(limit=limit)
        
        leads = agent.get_leads()
        opportunities = agent.get_opportunities()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if use_mock_data:
            st.success(f"✅ Connected to Test Data")
        else:
            st.success(f"✅ Connected to Salesforce")
    with col2:
        st.info(f"📊 {len(leads)} Leads Retrieved")
    with col3:
        st.info(f"💰 {len(opportunities)} Opportunities Retrieved")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Leads", "💰 Opportunities", "📈 Dashboard", "💬 AI Chat"])
    
    # TAB 1: LEADS (same logic as original, but with test data)
    with tab1:
        st.header("Lead Prioritization")
        
        with st.spinner("AI scoring leads..."):
            prioritizer = LeadPrioritizer()
            scored_leads = prioritizer.prioritize_leads(leads)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🏆 Top Leads")
            
            # Create dataframe
            df_leads = pd.DataFrame(scored_leads[:10])
            df_display = df_leads[['Name', 'Company', 'Status', 'priority_score']].copy()
            df_display.columns = ['Name', 'Company', 'Status', 'Score']
            
            # Add color coding
            def color_score(val):
                if val >= 80:
                    return 'background-color: #d4edda'
                elif val >= 60:
                    return 'background-color: #fff3cd'
                else:
                    return 'background-color: #f8d7da'
            
            styled_df = df_display.style.applymap(color_score, subset=['Score'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Gradient bar chart
            colors = ['#667eea' if score >= 70 else '#ffa500' if score >= 50 else '#ff6b6b' 
                     for score in df_leads['priority_score'][:10]]
            
            fig_leads = go.Figure(data=[
                go.Bar(
                    x=df_leads['Name'][:10],
                    y=df_leads['priority_score'][:10],
                    marker_color=colors,
                    text=df_leads['priority_score'][:10],
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>Score: %{y}<extra></extra>'
                )
            ])
            fig_leads.update_layout(
                title="<b>Lead Priority Scores</b>",
                xaxis_title="Lead Name",
                yaxis_title="Score (0-100)",
                xaxis=dict(tickangle=-45),
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(size=12)
            )
            st.plotly_chart(fig_leads, use_container_width=True)
        
        with col2:
            st.subheader("⭐ Top Lead Details")
            
            if scored_leads:
                top_lead = scored_leads[0]
                
                st.markdown(f"""
                <div class="lead-card">
                    <h3>👤 {top_lead['Name']}</h3>
                    <p><b>🏢 Company:</b> {top_lead['Company']}</p>
                    <p><b>📊 Status:</b> {top_lead.get('Status', 'N/A')}</p>
                    <p><b>📧 Email:</b> {top_lead.get('Email', 'N/A')}</p>
                    <p><b>⭐ Rating:</b> {top_lead.get('Rating', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                score = top_lead['priority_score']
                st.metric("🎯 Priority Score", score, delta=f"{score-50} vs avg")
                
                if st.button("Generate Follow-Up Actions"):
                    with st.spinner("Generating..."):
                        generator = FollowUpGenerator()
                        followup = generator.generate_actions(top_lead, "lead")
                        st.markdown("### 📝 Follow-Up Actions")
                        st.write(followup)
    
    # TAB 2: OPPORTUNITIES (same logic as original, but with test data)
    with tab2:
        st.header("Opportunity Scoring")
        
        with st.spinner("AI scoring opportunities..."):
            scorer = OpportunityScorer()
            scored_opps = scorer.score_opportunities(opportunities)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("💎 Top Opportunities")
            
            # Create dataframe
            df_opps = pd.DataFrame(scored_opps[:10])
            df_display = df_opps[['Name', 'Amount', 'StageName', 'conversion_score']].copy()
            df_display['Amount'] = df_display['Amount'].apply(lambda x: f"${x:,.0f}")
            df_display.columns = ['Name', 'Amount', 'Stage', 'Score']
            
            # Add color coding
            def color_score(val):
                if isinstance(val, (int, float)):
                    if val >= 80:
                        return 'background-color: #d4edda'
                    elif val >= 60:
                        return 'background-color: #fff3cd'
                    else:
                        return 'background-color: #f8d7da'
                return ''
            
            styled_df = df_display.style.applymap(color_score, subset=['Score'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Bubble chart
            fig_opps = go.Figure(data=[
                go.Scatter(
                    x=df_opps['Amount'][:10],
                    y=df_opps['conversion_score'][:10],
                    mode='markers',
                    marker=dict(
                        size=df_opps['conversion_score'][:10]/3,
                        color=df_opps['conversion_score'][:10],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Score"),
                        line=dict(width=2, color='white')
                    ),
                    text=df_opps['Name'][:10],
                    hovertemplate='<b>%{text}</b><br>Amount: $%{x:,.0f}<br>Score: %{y}<extra></extra>'
                )
            ])
            fig_opps.update_layout(
                title="<b>Opportunity Value vs Conversion Score</b>",
                xaxis_title="Amount ($)",
                yaxis_title="Conversion Score (0-100)",
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_opps, use_container_width=True)
        
        with col2:
            st.subheader("💰 Top Opportunity Details")
            
            if scored_opps:
                top_opp = scored_opps[0]
                
                st.markdown(f"""
                <div class="opp-card">
                    <h3>💼 {top_opp['Name']}</h3>
                    <p><b>💵 Amount:</b> ${top_opp['Amount']:,.0f}</p>
                    <p><b>📈 Stage:</b> {top_opp.get('StageName', 'N/A')}</p>
                    <p><b>📅 Close Date:</b> {top_opp.get('CloseDate', 'N/A')}</p>
                    <p><b>🎯 Probability:</b> {top_opp.get('Probability', 'N/A')}%</p>
                </div>
                """, unsafe_allow_html=True)
                
                score = top_opp['conversion_score']
                st.metric("🎯 Conversion Score", score, delta=f"{score-50} vs avg")
                
                if st.button("Generate Follow-Up Actions", key="opp_followup"):
                    with st.spinner("Generating..."):
                        generator = FollowUpGenerator()
                        followup = generator.generate_actions(top_opp, "opportunity")
                        st.markdown("### 📝 Follow-Up Actions")
                        st.write(followup)
    
    # TAB 3: DASHBOARD (same as original)
    with tab3:
        st.header("Analytics Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center;">
                <h2 style="margin: 0; font-size: 2.5rem;">{len(scored_leads)}</h2>
                <p style="margin: 0;">📊 Total Leads</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_lead_score = sum(l['priority_score'] for l in scored_leads) / len(scored_leads)
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center;">
                <h2 style="margin: 0; font-size: 2.5rem;">{avg_lead_score:.1f}</h2>
                <p style="margin: 0;">⭐ Avg Lead Score</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center;">
                <h2 style="margin: 0; font-size: 2.5rem;">{len(scored_opps)}</h2>
                <p style="margin: 0;">💼 Total Opportunities</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_value = sum(o['Amount'] for o in scored_opps if o['Amount'])
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center;">
                <h2 style="margin: 0; font-size: 2.5rem;">${total_value:,.0f}</h2>
                <p style="margin: 0;">💰 Total Pipeline</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Lead score distribution
            fig_dist = go.Figure(data=[
                go.Histogram(
                    x=[l['priority_score'] for l in scored_leads],
                    nbinsx=10,
                    marker=dict(
                        color=[l['priority_score'] for l in scored_leads],
                        colorscale='Viridis',
                        showscale=False
                    )
                )
            ])
            fig_dist.update_layout(
                title="<b>Lead Score Distribution</b>",
                xaxis_title="Score Range",
                yaxis_title="Number of Leads",
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            # Opportunity stage breakdown
            stage_counts = {}
            for opp in scored_opps:
                stage = opp.get('StageName', 'Unknown')
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            fig_pie = go.Figure(data=[
                go.Pie(
                    labels=list(stage_counts.keys()),
                    values=list(stage_counts.values()),
                    hole=0.4,
                    marker=dict(
                        colors=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'],
                        line=dict(color='white', width=2)
                    ),
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )
            ])
            fig_pie.update_layout(
                title="<b>Opportunities by Stage</b>",
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # TAB 4: AI CHAT (modified to use test configuration)
    with tab4:
        st.header("🤖 Conversational AI Assistant")
        
        if use_mock_data:
            st.info("🧪 **Test Mode**: Chat agent is using mock data for demonstration")
        
        st.markdown("Ask questions about your leads and opportunities in natural language!")
        
        # Initialize chat agent with test configuration
        if 'chat_agent' not in st.session_state:
            with st.spinner("Initializing AI assistant with memory & streaming..."):
                # Create chat agent that uses the same test configuration
                if use_mock_data:
                    from tests.mock_salesforce_agent import MockSalesforceAgent
                    sf_agent = MockSalesforceAgent(
                        sf_username=os.getenv("SF_USERNAME"),
                        sf_password=os.getenv("SF_PASSWORD"),
                        sf_token=os.getenv("SF_TOKEN"),
                        limit=50
                    )
                else:
                    from services.salesforce_agent import SalesforceAgent
                    sf_agent = SalesforceAgent(
                        sf_username=os.getenv("SF_USERNAME"),
                        sf_password=os.getenv("SF_PASSWORD"),
                        sf_token=os.getenv("SF_TOKEN"),
                        limit=50
                    )
                
                # Create conversational agent with the appropriate SF agent
                from agents.conversational_agent_enhanced import ConversationalSalesAgentEnhanced
                # Inject the pre-configured test/mock Salesforce agent to avoid live API calls
                st.session_state.chat_agent = ConversationalSalesAgentEnhanced(
                    sf_username=os.getenv("SF_USERNAME"),
                    sf_password=os.getenv("SF_PASSWORD"),
                    sf_token=os.getenv("SF_TOKEN"),
                    cache_ttl=300,
                    sf_agent=sf_agent
                )
        
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Example queries (same as original)
        st.markdown("### 💡 Try asking:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📊 Basic Queries:**")
            if st.button("🏆 Show me top 5 leads"):
                st.session_state.current_query = "Show me top 5 leads"
            if st.button("💰 Top 3 opportunities"):
                st.session_state.current_query = "Show me top 3 opportunities"
            if st.button("📊 Quick pipeline summary"):
                st.session_state.current_query = "Give me quick pipeline summary"
        with col2:
            st.markdown("**🔍 Advanced Analysis:**")
            if st.button("🚨 Critical actions today"):
                st.session_state.current_query = "What are the critical actions I need to take today?"
            if st.button("⚠️ High-value deals at risk"):
                st.session_state.current_query = "Show me high-value deals at risk"
            if st.button("🐌 Stale leads (30+ days)"):
                st.session_state.current_query = "Find stale leads that haven't been contacted in 30 days"
        with col3:
            st.markdown("**💡 Smart Actions:**")
            if st.button("💰 Discount strategy"):
                st.session_state.current_query = "Suggest discount strategy for the top opportunity"
            if st.button("⚖️ Compare opportunities"):
                st.session_state.current_query = "Compare top 2 opportunities"
            if st.button("🔄 Reset conversation"):
                st.session_state.chat_agent.reset_conversation()
                st.session_state.chat_history = []
                st.success("Conversation reset!")
        
        st.markdown("---")
        
        # Chat interface (same as original)
        user_input = st.chat_input("💬 Ask me anything about your leads and opportunities...")
        
        # Handle button clicks
        if 'current_query' in st.session_state:
            user_input = st.session_state.current_query
            del st.session_state.current_query
        
        if user_input:
            # Display user message immediately
            with st.chat_message("user"):
                st.write(user_input)
            
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Get AI response
            try:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    message_placeholder.markdown("Thinking...")
                    
                    # Use non-streaming chat for reliability
                    full_response = st.session_state.chat_agent.chat(user_input)
                    
                    message_placeholder.markdown(full_response)
                    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                import traceback
                st.code(traceback.format_exc())
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        
        # Display chat history (excluding the last 2 messages which are already shown)
        if len(st.session_state.chat_history) > 2:
            for message in st.session_state.chat_history[:-2]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

else:
    # Hero section (same as original)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 0;">
            <h2>👈 Click 'Run AI Analysis' to get started</h2>
            <p style="font-size: 1.1rem; color: #666;">Transform your Salesforce data with AI-powered insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature cards (same as original)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 3rem;">🎯</div>
            <h3>AI Lead Scoring</h3>
            <p>GPT-4 powered prioritization with 0-100 scoring system</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 3rem;">💎</div>
            <h3>Opportunity Analysis</h3>
            <p>Conversion likelihood prediction and pipeline insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 3rem;">📝</div>
            <h3>Smart Follow-ups</h3>
            <p>AI-generated personalized action plans for each prospect</p>
        </div>
        """, unsafe_allow_html=True)
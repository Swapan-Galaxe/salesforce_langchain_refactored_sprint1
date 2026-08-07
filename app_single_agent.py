import streamlit as st
import os
import json
from dotenv import load_dotenv
from services.salesforce_agent import SalesforceAgent, build_deal_risk_dashboard
from skills.prioritization_simple import LeadPrioritizer, OpportunityScorer, FollowUpGenerator
from agents.conversational_agent_enhanced import ConversationalSalesAgentEnhanced
from security.guardrails import GuardrailsManager
from services.evaluation import EvaluationManager
from tests.test_config import get_test_agent
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

load_dotenv()

use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

st.set_page_config(page_title="Salesforce AI Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# Initialize guardrails in session state
if 'guardrails' not in st.session_state:
    guardrails_config = {
        "max_input_length": 1000,
        "rate_limit_requests_per_minute": 20,
        "rate_limit_requests_per_hour": 200,
        "block_pii": True,
        "block_profanity": True,
        "block_sql_injection": True,
        "block_prompt_injection": True,
        "enable_audit_log": True
    }
    st.session_state.guardrails = GuardrailsManager(guardrails_config)

if 'evaluator' not in st.session_state:
    st.session_state.evaluator = EvaluationManager()

if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_" + str(hash(st.session_state.get('session_id', 'default')))

if 'history_file' not in st.session_state:
    st.session_state.history_file = os.path.join(os.getcwd(), "session_history.json")

if 'chat_history' not in st.session_state:
    history_file = st.session_state.history_file
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                st.session_state.chat_history = json.load(f)
        except Exception:
            st.session_state.chat_history = []
    else:
        st.session_state.chat_history = []


def save_chat_history():
    """Persist single-agent chat history to disk."""
    try:
        with open(st.session_state.history_file, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not save chat history: {e}")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #2d6cdf 0%, #5f2fc7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: left;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        text-align: left;
        color: #4d4d4d;
        font-size: 1rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        line-height: 1.55;
        max-width: 860px;
    }
    .hero-block {
        position: relative;
        background: #ffffff;
        border-radius: 28px;
        padding: 1.75rem;
        box-shadow: 0 20px 60px rgba(57, 91, 215, 0.08);
        margin-bottom: 1.5rem;
        text-align: left;
    }
    .mode-badge {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        border: 1px solid rgba(59, 130, 246, 0.2);
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.1);
        font-size: 0.88rem;
        margin-bottom: 0.85rem;
    }
    .sidebar-logo {
        width: 140px;
        display: block;
        margin: 0 auto 1rem auto;
    }
    .sidebar .mode-badge {
        margin-left: 0;
        margin-right: 0;
    }
    .hero-subtext {
        color: #5f5f6d;
        margin-top: 0.75rem;
    }
    .stat-card {
        background: #f4f6fb;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 10px 28px rgba(29, 53, 102, 0.06);
        transition: transform 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
    }
    .stat-card h4,
    .section-card h4 {
        font-size: 1.05rem;
        margin-bottom: 0.65rem;
    }
    .stat-card p,
    .section-card p,
    .lead-card p,
    .opp-card p {
        font-size: 0.95rem;
        margin: 0.35rem 0;
        line-height: 1.5;
    }
    .lead-card h3,
    .opp-card h3 {
        font-size: 1.15rem;
        margin-bottom: 0.75rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3rem;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .lead-card, .opp-card {
        background: #ffffff;
        padding: 1.2rem;
        border-radius: 16px;
        border-left: 5px solid #3f72af;
        box-shadow: 0 10px 24px rgba(81, 111, 176, 0.08);
        margin-bottom: 1rem;
    }
    .opp-card { border-left-color: #2a9d8f; }
    .sidebar .stButton>button {
        border-radius: 12px;
    }
    .section-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 1.5rem;
        border: 1px solid #e8ebf2;
        box-shadow: 0 14px 36px rgba(67, 84, 114, 0.06);
        margin-bottom: 1rem;
    }
    body .stApp h1 {
        font-size: 2.2rem !important;
        text-align: left !important;
    }
    body .stApp h2 {
        font-size: 1.45rem !important;
        text-align: left !important;
    }
    body .stApp h3 {
        font-size: 1.05rem !important;
        text-align: left !important;
    }
    body .stApp h4 {
        font-size: 0.98rem !important;
        text-align: left !important;
    }
    body .stApp p {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        text-align: left !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-block"><h1 class="main-header">🚀 Salesforce AI Assistant</h1><p class="sub-header">A polished sales intelligence workspace for leads, opportunities, pipeline risk, and follow-up actions.</p></div>', unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.image("https://www.salesforce.com/content/dam/sfdc-docs/www/logos/logo-salesforce.svg", width=140, caption="Salesforce AI")
    st.markdown("---")
    st.header("Configuration")
    
    limit = st.slider("Records to Analyze", 5, 50, 20, help="Number of leads and opportunities to fetch")
    cache_ttl = st.slider("Cache Duration (seconds)", 60, 600, 300, help="How long to cache Salesforce data")
    
    st.markdown("---")
    
    if st.button("Run AI Analysis", type="primary", use_container_width=True):
        st.session_state.run_analysis = True
    
    if st.button("Refresh Salesforce Data", use_container_width=True):
        if 'chat_agent' in st.session_state:
            st.session_state.chat_agent.refresh_cache()
            st.success("Cache refreshed!")
    
    st.markdown("---")
    st.markdown("### 📋 Features")
    st.markdown("✅ AI Lead Scoring")
    st.markdown("✅ Opportunity Analysis")
    st.markdown("✅ Follow-up Generation")
    st.markdown("✅ Real-time Dashboards")
    
    st.markdown("---")
    st.markdown(f'<div class="mode-badge">{"TEST MODE: Mock Data" if use_mock_data else "Live Salesforce"}</div>', unsafe_allow_html=True)
    if use_mock_data:
        st.info("🧪 Using mock Salesforce data. No API calls will be made.")

    st.markdown("---")
    st.caption("Powered by OpenAI GPT-4")

# Main content
if 'run_analysis' in st.session_state and st.session_state.run_analysis:
    
    with st.spinner("Connecting to data source..."):
        sf_username = os.getenv("SALESFORCE_USERNAME") or os.getenv("SF_USERNAME")
        sf_password = os.getenv("SALESFORCE_PASSWORD") or os.getenv("SF_PASSWORD")
        sf_token = os.getenv("SALESFORCE_SECURITY_TOKEN") or os.getenv("SF_TOKEN")

        if use_mock_data or not all([sf_username, sf_password, sf_token]):
            if not use_mock_data:
                st.warning("Salesforce credentials not found. Using mock data mode.")
            else:
                st.info("USE_MOCK_DATA=true detected. Using mock data mode.")
            agent = get_test_agent(limit=limit)
        else:
            agent = SalesforceAgent(
                sf_username=sf_username,
                sf_password=sf_password,
                sf_token=sf_token,
                limit=limit
            )
        
        leads = agent.get_leads()
        opportunities = agent.get_opportunities()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Leads", "Opportunities", "Dashboard", "AI Chat"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if use_mock_data:
            st.success("Connected to Mock Data")
        else:
            st.success("Connected to Salesforce")
    with col2:
        st.info(f"{len(leads)} Leads Retrieved")
    with col3:
        st.info(f"{len(opportunities)} Opportunities Retrieved")
    
    # TAB 1: LEADS
    with tab1:
        st.header("Lead Prioritization")
        
        with st.spinner("AI scoring leads..."):
            prioritizer = LeadPrioritizer()
            scored_leads = prioritizer.prioritize_leads(leads)
        
        col1, col2 = st.columns([2, 1])
        
        selected_lead = None

        with col1:
            st.subheader("Top Leads")
            
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
            st.subheader("Selected Lead Details")

            if scored_leads:
                lead_names = [lead['Name'] for lead in scored_leads]
                selected_lead_name = st.session_state.get('selected_lead_name', lead_names[0])
                selected_lead_name = st.selectbox(
                    "Select a lead to inspect",
                    lead_names,
                    index=lead_names.index(selected_lead_name) if selected_lead_name in lead_names else 0,
                    key="selected_lead_name"
                )
                selected_lead = next((lead for lead in scored_leads if lead['Name'] == selected_lead_name), scored_leads[0])

            if selected_lead:
                st.markdown(f"""
                <div class="lead-card">
                    <h3>{selected_lead['Name']}</h3>
                    <p><b>Company:</b> {selected_lead['Company']}</p>
                    <p><b>Status:</b> {selected_lead.get('Status', 'N/A')}</p>
                    <p><b>Email:</b> {selected_lead.get('Email', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                score = selected_lead['priority_score']
                st.metric("Priority Score", score, delta=f"{score-50} vs avg")
                
                if st.button("Generate Follow-Up Actions", key="lead_followup"):
                    with st.spinner("Generating..."):
                        generator = FollowUpGenerator()
                        followup = generator.generate_actions(selected_lead, "lead")
                        st.markdown("### 📝 Follow-Up Actions")
                        st.write(followup)
            else:
                st.info("No lead selected or no leads available.")
    
    # TAB 2: OPPORTUNITIES
    with tab2:
        st.header("Opportunity Scoring")
        
        with st.spinner("AI scoring opportunities..."):
            scorer = OpportunityScorer()
            scored_opps = scorer.score_opportunities(opportunities)
        
        col1, col2 = st.columns([2, 1])
        
        selected_opp = None

        with col1:
            st.subheader("Top Opportunities")

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
            st.subheader("Selected Opportunity Details")
            
            if scored_opps:
                opp_names = [opp['Name'] for opp in scored_opps]
                selected_opp_name = st.session_state.get('selected_opp_name', opp_names[0])
                selected_opp_name = st.selectbox(
                    "Select an opportunity to inspect",
                    opp_names,
                    index=opp_names.index(selected_opp_name) if selected_opp_name in opp_names else 0,
                    key="selected_opp_name"
                )
                selected_opp = next((opp for opp in scored_opps if opp['Name'] == selected_opp_name), scored_opps[0])

            if selected_opp:
                st.markdown(f"""
                <div class="opp-card">
                    <h3>{selected_opp['Name']}</h3>
                    <p><b>Amount:</b> ${selected_opp['Amount']:,.0f}</p>
                    <p><b>Stage:</b> {selected_opp.get('StageName', 'N/A')}</p>
                    <p><b>Close Date:</b> {selected_opp.get('CloseDate', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                score = selected_opp['conversion_score']
                st.metric("Conversion Score", score, delta=f"{score-50} vs avg")
                
                if st.button("Generate Follow-Up Actions", key="opp_followup"):
                    with st.spinner("Generating..."):
                        generator = FollowUpGenerator()
                        followup = generator.generate_actions(selected_opp, "opportunity")
                        st.markdown("### 📝 Follow-Up Actions")
                        st.write(followup)
            else:
                st.info("No opportunity selected or no opportunities available.")
    
    # TAB 3: DASHBOARD
    with tab3:
        st.header("Analytics Dashboard")
        st.markdown("Create a concise view of sales performance, risk, and runway in one place.")
        
        total_leads = len(scored_leads)
        avg_lead_score = sum(l['priority_score'] for l in scored_leads) / len(scored_leads) if scored_leads else 0
        total_opps = len(scored_opps)
        total_value = sum(o['Amount'] for o in scored_opps if o.get('Amount'))

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.markdown(f"""
            <div class="stat-card">
                <h4>Total Leads</h4>
                <p style="font-size: 2.4rem; font-weight: 800; margin: 0;">{total_leads}</p>
                <p style="color: #64748b; margin-top: 0.4rem;">Lead coverage across Salesforce.</p>
            </div>
        """, unsafe_allow_html=True)
        metric_col2.markdown(f"""
            <div class="stat-card">
                <h4>Avg Lead Score</h4>
                <p style="font-size: 2.4rem; font-weight: 800; margin: 0;">{avg_lead_score:.1f}</p>
                <p style="color: #64748b; margin-top: 0.4rem;">Quality signal across active leads.</p>
            </div>
        """, unsafe_allow_html=True)
        metric_col3.markdown(f"""
            <div class="stat-card">
                <h4>Total Opportunities</h4>
                <p style="font-size: 2.4rem; font-weight: 800; margin: 0;">{total_opps}</p>
                <p style="color: #64748b; margin-top: 0.4rem;">Pipeline opportunities in scope.</p>
            </div>
        """, unsafe_allow_html=True)
        metric_col4.markdown(f"""
            <div class="stat-card">
                <h4>Total Pipeline</h4>
                <p style="font-size: 2.4rem; font-weight: 800; margin: 0;">${total_value:,.0f}</p>
                <p style="color: #64748b; margin-top: 0.4rem;">Estimated revenue across opportunities.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Deal Risk and Recommended Next Actions")
        risk_rows = build_deal_risk_dashboard(opportunities)

        if risk_rows:
            risk_df = pd.DataFrame(risk_rows)
            critical_count = int((risk_df["risk_level"] == "Critical").sum())
            at_risk_count = int((risk_df["risk_score"] >= 40).sum())
            at_risk_value = risk_df.loc[risk_df["risk_score"] >= 40, "risk_value"].sum()

            risk_col1, risk_col2, risk_col3 = st.columns(3)
            risk_col1.markdown(f"""
                <div class="section-card">
                    <h4>Critical Deals</h4>
                    <p style="font-size: 2rem; font-weight: 700; margin: 0;">{critical_count}</p>
                    <p style="color: #64748b; margin-top: 0.35rem;">Deals requiring immediate attention.</p>
                </div>
            """, unsafe_allow_html=True)
            risk_col2.markdown(f"""
                <div class="section-card">
                    <h4>Deals Needing Attention</h4>
                    <p style="font-size: 2rem; font-weight: 700; margin: 0;">{at_risk_count}</p>
                    <p style="color: #64748b; margin-top: 0.35rem;">Potential at-risk opportunities.</p>
                </div>
            """, unsafe_allow_html=True)
            risk_col3.markdown(f"""
                <div class="section-card">
                    <h4>At-Risk Pipeline</h4>
                    <p style="font-size: 2rem; font-weight: 700; margin: 0;">${at_risk_value:,.0f}</p>
                    <p style="color: #64748b; margin-top: 0.35rem;">Potential exposure if deals slip.</p>
                </div>
            """, unsafe_allow_html=True)

            display_columns = [
                "Name", "Amount", "StageName", "Probability", "CloseDate",
                "risk_level", "risk_score", "next_action"
            ]
            available_columns = [column for column in display_columns if column in risk_df.columns]
            display_df = risk_df[available_columns].copy()
            if "Amount" in display_df:
                display_df["Amount"] = display_df["Amount"].fillna(0).map(lambda value: f"${value:,.0f}")
            display_df.columns = [
                {
                    "StageName": "Stage", "Probability": "Probability %",
                    "CloseDate": "Close Date", "risk_level": "Risk Level",
                    "risk_score": "Risk Score", "next_action": "Recommended Next Action"
                }.get(column, column)
                for column in display_df.columns
            ]

            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)

            selected_name = st.selectbox(
                "Inspect risk evidence",
                [row.get("Name", "Unnamed opportunity") for row in risk_rows],
                key="deal_risk_selection"
            )
            selected_row = next(row for row in risk_rows if row.get("Name") == selected_name)
            st.markdown(f"""
                <div class='section-card'>
                    <h4>Risk Details for {selected_row.get('Name')}</h4>
                    <p><strong>Risk Level:</strong> {selected_row.get('risk_level')} ({selected_row.get('risk_score')}/100)</p>
                    <p><strong>Recommended Action:</strong> {selected_row.get('next_action')}</p>
                    <p style='color: #475569;'>{' ; '.join(selected_row.get('risk_reasons', []))}</p>
                </div>
            """, unsafe_allow_html=True)
            st.caption("Recommendations are advisory. Review before acting.")
        else:
            st.info("No open opportunities are available for risk analysis.")

        st.markdown("---")
        st.subheader("Performance Charts")

        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
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
                title="Lead Score Distribution",
                xaxis_title="Score Range",
                yaxis_title="Number of Leads",
                height=380,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=50, b=40, l=30, r=20)
            )
            st.plotly_chart(fig_dist, use_container_width=True)
        
        with chart_col2:
            # Opportunity stage breakdown with custom colors
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
    
    # TAB 4: AI CHAT
    with tab4:
        st.header("Conversational AI Assistant")
        st.markdown("Ask questions about your leads and opportunities in natural language!")
        
        # Initialize chat agent
        if 'chat_agent' not in st.session_state:
            with st.spinner("Initializing AI assistant with memory & streaming..."):
                sf_username = os.getenv('SALESFORCE_USERNAME') or os.getenv('SF_USERNAME')
                sf_password = os.getenv('SALESFORCE_PASSWORD') or os.getenv('SF_PASSWORD')
                sf_token = os.getenv('SALESFORCE_SECURITY_TOKEN') or os.getenv('SF_TOKEN')

                if use_mock_data or not all([sf_username, sf_password, sf_token]):
                    if not use_mock_data:
                        st.warning("Salesforce credentials were not found, so chat is using mock data mode.")
                    from tests.mock_salesforce_agent import MockSalesforceAgent
                    sf_agent = MockSalesforceAgent(limit=50)
                    st.session_state.chat_agent = ConversationalSalesAgentEnhanced(
                        cache_ttl=300,
                        sf_agent=sf_agent
                    )
                else:
                    st.session_state.chat_agent = ConversationalSalesAgentEnhanced(
                        sf_username=sf_username,
                        sf_password=sf_password,
                        sf_token=sf_token,
                        cache_ttl=300
                    )
        
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Example queries
        st.markdown("### Try asking:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Basic Queries:**")
            if st.button("Show me top 5 leads"):
                st.session_state.current_query = "Show me top 5 leads"
            if st.button("Top 3 opportunities"):
                st.session_state.current_query = "Show me top 3 opportunities"
            if st.button("Quick pipeline summary"):
                st.session_state.current_query = "Give me quick pipeline summary"
            if st.button("Complete opportunity analysis"):
                st.session_state.current_query = "Give me complete opportunity summary"
        with col2:
            st.markdown("**Advanced Analysis:**")
            if st.button("Critical actions today"):
                st.session_state.current_query = "What are the critical actions I need to take today?"
            if st.button("High-value deals at risk"):
                st.session_state.current_query = "Show me high-value deals at risk"
            if st.button("Stale leads (30+ days)"):
                st.session_state.current_query = "Find stale leads that haven't been contacted in 30 days"
            if st.button("Deal velocity analysis"):
                st.session_state.current_query = "Analyze deal velocity"
        with col3:
            st.markdown("**Smart Actions:**")
            if st.button("Discount strategy"):
                st.session_state.current_query = "Suggest discount strategy for United Oil opportunity"
            if st.button("Compare opportunities"):
                st.session_state.current_query = "Compare top 2 opportunities"
            if st.button("Search lead"):
                st.session_state.current_query = "Search for lead named Bertha Boxer"
            if st.button("Reset conversation"):
                st.session_state.chat_agent.reset_conversation()
                st.session_state.chat_history = []
                save_chat_history()
                st.success("Conversation reset!")
        
        st.markdown("---")
        
        # Chat interface
        user_input = st.chat_input("Ask me anything about your leads and opportunities...")
        
        # Handle button clicks
        if 'current_query' in st.session_state:
            user_input = st.session_state.current_query
            del st.session_state.current_query
        
        if user_input:
            # Validate with guardrails
            guardrails = st.session_state.guardrails
            user_id = st.session_state.user_id
            
            is_valid, error = guardrails.validate_input(user_input, user_id)
            if not is_valid:
                st.error(f"⚠️ {error}")
                st.stop()
            
            is_allowed, error = guardrails.check_rate_limit(user_id)
            if not is_allowed:
                st.warning(f"⚠️ {error}")
                st.stop()
            
            # Display user message immediately
            with st.chat_message("user"):
                st.write(user_input)
            
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            save_chat_history()
            # Get AI response
            try:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    message_placeholder.markdown("Thinking...")
                    
                    # Use non-streaming chat for reliability
                    full_response = st.session_state.chat_agent.chat(user_input)
                    
                    # Get source data for evaluation
                    source_data = []
                    if 'lead' in user_input.lower():
                        source_data.extend(st.session_state.chat_agent._get_leads_cached())
                    if 'opportunit' in user_input.lower() or 'deal' in user_input.lower():
                        source_data.extend(st.session_state.chat_agent._get_opportunities_cached())
                    
                    # Evaluate response
                    evaluation = st.session_state.evaluator.evaluate_response(
                        query=user_input,
                        response=full_response,
                        source_data=source_data
                    )
                    
                    # Validate output with guardrails
                    is_valid, sanitized, error = guardrails.validate_output(full_response)
                    
                    message_placeholder.markdown(sanitized)
                    
                    # Show quality indicator
                    quality = evaluation["overall_quality"]
                    confidence = evaluation["hallucination_check"]["confidence"]
                    
                    if "Excellent" in quality:
                        st.success(f"✅ Quality: {quality} | Confidence: {confidence:.0%}")
                    elif "Good" in quality:
                        st.info(f"ℹ️ Quality: {quality} | Confidence: {confidence:.0%}")
                    elif "Fair" in quality:
                        st.warning(f"⚠️ Quality: {quality} | Confidence: {confidence:.0%}")
                    else:
                        st.error(f"❌ Quality: {quality} | Confidence: {confidence:.0%}")
                    
                    # Show hallucination warning if detected
                    if evaluation["hallucination_check"]["has_hallucination"]:
                        st.warning("⚠️ Potential hallucination detected. Please verify information.")
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": sanitized, "evaluation": evaluation})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                import traceback
                st.code(traceback.format_exc())
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                save_chat_history()

else:
    # Hero section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 0;">
            <h2>Click 'Run AI Analysis' to get started</h2>
            <p style="font-size: 1.1rem; color: #666;">Transform your Salesforce data with AI-powered insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">🎯</div>
            <h3>AI Lead Scoring</h3>
            <p>GPT-4 powered prioritization with 0-100 scoring system</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">💎</div>
            <h3>Opportunity Analysis</h3>
            <p>Conversion likelihood prediction and pipeline insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">📝</div>
            <h3>Smart Follow-ups</h3>
            <p>AI-generated personalized action plans for each prospect</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">📊</div>
            <h3>Visual Dashboards</h3>
            <p>Interactive charts and real-time analytics</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">🔄</div>
            <h3>Real-time Sync</h3>
            <p>Direct Salesforce API integration for live data</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 2rem; border-radius: 10px; text-align: center; height: 250px;">
            <div style="font-size: 2rem;">⚡</div>
            <h3>Lightning Fast</h3>
            <p>Optimized performance with intelligent caching</p>
        </div>
        """, unsafe_allow_html=True)

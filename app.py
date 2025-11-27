import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import risk_engine 
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io
import altair as alt
import textwrap
import datetime

load_dotenv()

st.set_page_config(page_title="Cloudflare-Is-Not-Available AI", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    /* 1. MAIN PAGE PADDING */
    .block-container { 
        padding-top: 3.5rem; 
        padding-bottom: 1rem; 
        padding-left: 2rem; 
        padding-right: 2rem; 
    }
    div[data-testid="column"] { gap: 0.5rem; }

    /* 2. SIDEBAR: FLEXBOX MAGIC */
    [data-testid="stSidebarUserContent"] > div:first-child {
        height: calc(100vh - 100px); 
        display: flex;
        flex-direction: column;
    }

    /* TOP CONTAINER: Fixed */
    [data-testid="stSidebarUserContent"] > div:first-child > div:nth-child(1) {
        flex: 0 0 auto; padding-bottom: 1rem;
    }

    /* MIDDLE CONTAINER: Scrolls */
    [data-testid="stSidebarUserContent"] > div:first-child > div:nth-child(2) {
        flex: 1 1 auto; overflow-y: auto; min-height: 0; margin-bottom: 10px;
    }

    /* BOTTOM CONTAINER: Fixed */
    [data-testid="stSidebarUserContent"] > div:first-child > div:nth-child(3) {
        flex: 0 0 auto; padding-top: 1rem; border-top: 1px solid #e6e6e6;
    }

    /* 3. BUTTON STYLING */
    section[data-testid="stSidebar"] .stButton button { 
        width: 100%; text-align: left; border: none; background: transparent; 
        padding: 6px 10px; color: #444; font-size: 14px;
    }
    section[data-testid="stSidebar"] .stButton button:hover { background: #eef0f2; }
    
    /* New Assessment Button */
    div[data-testid="stSidebar"] div:nth-child(1) .stButton button { 
        background: #f0f4f8; border: 1px solid #dbe0e6; font-weight: 600; color: #333;
        border-radius: 20px; text-align: center;
    }
    
    /* 4. Download Buttons Height */
    div.stButton > button:first-child { height: 3em; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HELPER 1: IMAGE GENERATOR
# ---------------------------------------------------------
def create_summary_image(data, result, label):
    W, H = 800, 600
    img = Image.new('RGB', (W, H), color='white'); d = ImageDraw.Draw(img)
    score = result['Final_Risk']
    if score > 60: header="#ffcdd2"; text="#b71c1c"; status="REJECT"
    elif score > 40: header="#ffe0b2"; text="#e65100"; status="REVIEW"
    else: header="#c8e6c9"; text="#1b5e20"; status="APPROVE"
    try: fXL=ImageFont.truetype("arial.ttf",50); fL=ImageFont.truetype("arial.ttf",30); fM=ImageFont.truetype("arial.ttf",20)
    except: fXL=ImageFont.load_default(); fL=ImageFont.load_default(); fM=ImageFont.load_default()
    d.rectangle([(0,0),(W,100)], fill=header); d.text((30,25), f"Decision: {status}", fill=text, font=fXL)
    d.text((30,130), f"Risk: {score}/100", fill="black", font=fL); d.text((400,130), f"Conf: {result.get('Text_Analysis',{}).get('confidence','N/A')}%", fill="gray", font=fL)
    d.line([(30,180),(W-30,180)], fill="gray", width=2)
    d.text((30,200),"Applicant:",fill="black",font=fL); d.text((30,240),f"Income: ${data['income']} | Loan: ${data['loan_amount']}",fill="black",font=fM)
    d.text((30,290),"AI Summary:",fill="black",font=fL)
    exp=result.get('Text_Analysis',{}).get('explanation','-'); wrap=textwrap.fill(exp,70)
    d.text((30,330),wrap,fill="black",font=fM)
    
    # Footer
    d.text((30,550),f"Cloudflare-Is-Not-Available AI | Case: {label}",fill="lightgray",font=fM)
    buf=io.BytesIO(); img.save(buf,format='PNG'); return buf.getvalue()

# ---------------------------------------------------------
# HELPER 2: PDF GENERATOR 
# ---------------------------------------------------------

def clean_text(text):
    """Sanitize text to remove unsupported characters for PDF."""
    if not isinstance(text, str):
        return str(text)
    # Replace smart quotes and dashes with standard ASCII
    replacements = {
        '\u2018': "'", '\u2019': "'", # Smart single quotes
        '\u201c': '"', '\u201d': '"', # Smart double quotes
        '\u2013': '-', '\u2014': '-', # Dashes
        '\u2026': '...',              # Ellipsis
        '–': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # Force Latin-1 compatible, replacing unknowns with '?'
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf_report(data, result, label, fin_text):
    pdf = FPDF()
    pdf.add_page()
    
    # HEADER
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "Credit Risk Assessment Report", ln=True, align='L')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Generated via Cloudflare-Is-Not-Available AI | Date: {datetime.date.today()}", ln=True, align='L')
    pdf.ln(5)

    # 1. APPLICANT DATA
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "  1. Applicant Data", ln=True, fill=True)
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    
    labels = {
        "income": "Monthly Income", "loan_amount": "Loan Amount", "dti": "Debt-to-Income Ratio",
        "age": "Applicant Age", "dependents": "Number of Dependents", "loan_term": "Loan Term (Months)",
        "credit_history": "Credit History (Years)", "user_story": "Loan Purpose"
    }
    
    for key, value in data.items():
        label_text = labels.get(key, key.title())
        
        # --- FIX APPLIED HERE: Clean the value before printing ---
        safe_value = clean_text(value) 
        
        pdf.cell(60, 7, f"{label_text}", border=0)
        if key == "user_story":
            pdf.multi_cell(0, 7, f": {safe_value}", border=0)
        else:
            pdf.cell(0, 7, f": {safe_value}", border=0, ln=True)
    pdf.ln(10)

    # 2. DETAILED ANALYSIS
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "  2. Detailed Risk Analysis", ln=True, fill=True)
    pdf.ln(5)

    # A. Financial
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"A. Financial Metrics (Math Model: {result['Math_Score']}/100)", ln=True)
    pdf.set_font("Arial", '', 10)
    
    # --- FIX APPLIED HERE: Clean fin_text ---
    pdf.multi_cell(0, 6, clean_text(fin_text))
    pdf.ln(5)

    # B. Behavioral
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"B. Behavioral/Story Analysis (LLM Model: {result['Text_Score']}/100)", ln=True)
    pdf.set_font("Arial", '', 10)
    
    explanation = result.get('Text_Analysis', {}).get('explanation', 'N/A')
    
    # --- FIX APPLIED HERE: Use clean_text instead of manual replace ---
    # Your previous code was: safe_explanation = explanation.encode('latin-1', 'replace').decode('latin-1')
    # clean_text does that PLUS the smart quote fix.
    pdf.multi_cell(0, 6, clean_text(explanation))
    pdf.ln(5)
    
    # Flags Table
    analysis = result.get('Text_Analysis', {})
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(95, 8, f"- Purpose Legitimacy: {analysis.get('purpose_legitimacy', '-')}/100", border=1)
    pdf.cell(95, 8, f"- Financial Responsibility: {analysis.get('financial_responsibility', '-')}/100", border=1, ln=True)
    pdf.cell(95, 8, f"- Urgency/Desperation: {analysis.get('urgency_desperation', '-')}/100", border=1)
    pdf.cell(95, 8, f"- Clarity of Plan: {analysis.get('clarity', '-')}/100", border=1, ln=True)
    pdf.ln(10)

    # 3. EXECUTIVE SUMMARY (ALIGNED COLONS)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "  3. Executive Summary", ln=True, fill=True)
    pdf.ln(5)
    
    final_score = result['Final_Risk']
    if final_score > 60: 
        decision = "REJECT"; color_text = "(High Risk)"
        r, g, b = 200, 0, 0 # RED
    elif final_score > 40: 
        decision = "MANUAL REVIEW"; color_text = "(Medium Risk)"
        r, g, b = 220, 120, 0 # ORANGE
    else: 
        decision = "APPROVE"; color_text = "(Low Risk)"
        r, g, b = 0, 150, 0 # GREEN
    
    # Row 1: Recommendation (Red Text)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 8, "Recommendation", border=0) # Fixed width label
    pdf.set_text_color(r, g, b)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, f": {decision} {color_text}", ln=True)
    
    # Row 2: Final Score (Black Text)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(50, 8, "Final Risk Score", border=0)
    pdf.cell(0, 8, f": {final_score}/100", ln=True)
    
    # Row 3: Confidence
    pdf.cell(50, 8, "AI Confidence", border=0)
    pdf.cell(0, 8, f": {result.get('Text_Analysis', {}).get('confidence', 'N/A')}%", ln=True)

    return pdf.output(dest="S").encode("latin-1")

def generate_financial_insight(inputs, math_score):
    flags = []
    if inputs['income'] < 3000: flags.append("Low income.")
    elif inputs['income'] > 8000: flags.append("Strong income.")
    if inputs['dti'] > 0.45: flags.append("High DTI.")
    summary = "Math model predicts HIGH risk." if math_score > 70 else "Math model predicts LOW risk."
    return f"{summary} {' '.join(flags)}"

# ---------------------------------------------------------
# STATE
# ---------------------------------------------------------
if 'history' not in st.session_state: st.session_state.history = []
if 'active_index' not in st.session_state: st.session_state.active_index = -1 
defaults = { "income": 5000, "loan_amount": 10000, "dti": 0.3, "age": 30, "dependents": 0, "loan_term": 36, "credit_history": 5, "user_story": "I need this loan to expand my small bakery business." }
for k, v in defaults.items(): 
    if k not in st.session_state: st.session_state[k] = v

@st.cache_resource
def get_engine(): return risk_engine.get_total_risk

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    # 1. Fixed Top
    with st.container():
        if st.button("➕ New Assessment", type="secondary"):
            st.session_state.active_index = -1
            for k, v in defaults.items(): st.session_state[k] = v
            st.rerun()
        
    # 2. Scrollable History
    with st.container():
        st.caption("Recent")
        for i, record in enumerate(reversed(st.session_state.history)):
            real_index = len(st.session_state.history) - 1 - i
            display_name = record.get('custom_name', f"Case #{real_index + 1}")
            icon = "🟢" if record['risk_label'] == "Low Risk" else "🔴" if record['risk_label'] == "High Risk" else "🟡"
            if st.button(f"{icon}  {display_name}", key=f"hist_{real_index}"):
                st.session_state.active_index = real_index
                for k, v in record['inputs'].items(): st.session_state[k] = v
                st.rerun()

    # 3. Fixed Bottom
    with st.container():
        # HELP EXPANDER
        with st.expander("❓ Help"):
            st.markdown("""
            **How to use:**
            1. Enter Applicant Details on the left.
            2. Type the Loan Purpose description.
            3. Click **Predict Risk**.
            4. Review the AI Decision, Confidence, and Reasoning.
            5. Download PDF Report if needed.
            """)
        
        if st.session_state.active_index != -1:
            
            st.caption("Current")
            current_idx = st.session_state.active_index
            current_name = st.session_state.history[current_idx].get('custom_name', f"Case #{current_idx + 1}")
            new_name = st.text_input("Rename Case", value=current_name, label_visibility="collapsed")
            if new_name != current_name:
                st.session_state.history[current_idx]['custom_name'] = new_name
                st.rerun()

# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------


left_col, right_col = st.columns([1, 1.2], gap="large") 

# --- LEFT COLUMN ---
with left_col:
    st.markdown("### 🏦 DeepCheck Credit Assessment")
    st.caption("by Cloudflare-Is-Not-Available AI")
    c1, c2, c3, c4 = st.columns(4)
    with c1: income = st.number_input("Income", 0, key="income", help="Monthly income in USD")
    with c2: loan_amount = st.number_input("Loan", 0, key="loan_amount", help="Principal Amount")
    with c3: dti = st.number_input("DTI", 0.0, 1.0, key="dti", help="Debt-to-Income Ratio")
    with c4: loan_term = st.number_input("Term", 12, key="loan_term", help="Months")
    c5, c6, c7, c8 = st.columns(4)
    with c5: age = st.number_input("Age", 18, 100, key="age")
    with c6: dependents = st.number_input("Dep.", 0, key="dependents", help="Number of Dependents")
    with c7: credit_history = st.number_input("Hist.", 0, key="credit_history", help="Years of Credit History")
    with c8: st.empty() 

    user_story = st.text_area("Reason for Loan", height=190, key="user_story", placeholder="Enter applicant explanation...")
    
    if st.button("Predict Risk", type="primary", use_container_width=True):
        with st.spinner("Analysing..."):
            try:
                result = risk_engine.get_total_risk(age=age, income=income, loan_amount=loan_amount, loan_term=loan_term, dti=dti, credit_history=credit_history, dependents=dependents, user_story=user_story)
                fin_commentary = generate_financial_insight({"income": income, "dti": dti, "credit_history": credit_history}, result['Math_Score'])
                f_risk = result['Final_Risk']
                if f_risk > 60: r_label = "High Risk"
                elif f_risk > 40: r_label = "Medium Risk"
                else: r_label = "Low Risk"

                new_record = {
                    "inputs": { "income": income, "loan_amount": loan_amount, "dti": dti, "age": age, "dependents": dependents, "loan_term": loan_term, "credit_history": credit_history, "user_story": user_story },
                    "full_result": result, "financial_commentary": fin_commentary, "risk_label": r_label, "custom_name": f"Case #{len(st.session_state.history) + 1}"
                }
                st.session_state.history.append(new_record)
                st.session_state.active_index = len(st.session_state.history) - 1
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

# --- RIGHT COLUMN ---
if st.session_state.active_index != -1:
    record = st.session_state.history[st.session_state.active_index]
    result = record['full_result']
    fin_commentary = record.get('financial_commentary', "Analysis not available.")

    with right_col:
        st.write("")
        c_card, c_btns = st.columns([3.5, 0.8])
        with c_btns:
            pdf_bytes = create_pdf_report(record['inputs'], result, record['custom_name'], fin_commentary)
            img_bytes = create_summary_image(record['inputs'], result, record['custom_name'])
            st.download_button(" PDF ", pdf_bytes, f"{record['custom_name']}.pdf", "application/pdf", use_container_width=True)
            st.download_button(" IMG ", img_bytes, f"{record['custom_name']}.png", "image/png", use_container_width=True)

        with c_card:
            final_risk = result['Final_Risk']
            text_analysis = result.get('Text_Analysis', {})
            conf_val = text_analysis.get('confidence', '85')
            if final_risk > 60: bg="#ffebee"; border="#ef5350"; text="#c62828"; action="REJECT LOAN"; arrow="↑"; level="High Risk"
            elif final_risk > 40: bg="#fff3e0"; border="#ffb74d"; text="#ef6c00"; action="REVIEW LOAN"; arrow="↗"; level="Med Risk"
            else: bg="#e8f5e9"; border="#66bb6a"; text="#2e7d32"; action="APPROVE LOAN"; arrow="↓"; level="Low Risk"
            html_code = f"""<div style="background-color:{bg};border:2px solid {border};border-radius:10px;padding:10px 15px;height:120px;display:flex;align-items:center;"><div style="flex:1.5;border-right:1px solid {border};padding-right:10px;"><div style="font-size:11px;color:#555;">Total Risk Score</div><div style="font-size:36px;font-weight:900;color:{text};line-height:1;">{final_risk}/100</div><div style="display:inline-block;background-color:rgba(255,255,255,0.6);border:1px solid {text};color:{text};border-radius:12px;padding:2px 8px;font-size:10px;font-weight:bold;margin-top:4px;">{arrow} {action} : {level}</div></div><div style="flex:1;padding-left:15px;"><div style="font-size:11px;color:#555;">Confidence</div><div style="font-size:36px;font-weight:900;color:#333;line-height:1;">{conf_val}%</div><div style="font-size:9px;color:#777;margin-top:2px;">Math + Story Model</div></div></div>"""
            st.markdown(html_code, unsafe_allow_html=True)

        st.write("")

        tab1, tab2 = st.tabs(["Analysis", "Data"])
        with tab1:
            st.caption("AI Summary")
            st.info(text_analysis.get('explanation', '-'))
            st.caption("Financial Flags")
            st.write(fin_commentary)
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.caption("Legitimacy"); st.progress(int(text_analysis.get('purpose_legitimacy', 0)))
            with k2: st.caption("Responsibility"); st.progress(int(text_analysis.get('financial_responsibility', 0)))
            with k3: st.caption("Urgency"); st.progress(int(text_analysis.get('urgency_desperation', 0)))
            with k4: st.caption("Clarity"); st.progress(int(text_analysis.get('clarity', 0)))

        with tab2:
            chart_data = pd.DataFrame({ "Source": ["Financial", "Story"], "Risk": [result['Math_Score'], result['Text_Score']] })
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Source', axis=alt.Axis(labelAngle=0, title=None, labelFontWeight='bold')), 
                y=alt.Y('Risk', scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(title=None)), 
                color=alt.Color('Source', scale=alt.Scale(range=['#FF4B4B', '#FF4B4B']), legend=None),
                tooltip=['Source', 'Risk']
            ).properties(height=340) 
            st.altair_chart(chart, use_container_width=True)
else:
    with right_col:
        st.markdown("### ")
        st.info("👈 Enter applicant details to start.")
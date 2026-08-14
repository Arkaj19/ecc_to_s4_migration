# frontend/app.py

import streamlit as st
import pandas as pd
import requests
import json
import io
import os
import sys

# Add parent directory to path so we can import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend import mappings

# Set up page configurations
st.set_page_config(
    page_title="ECC to S/4 HANA FICO Data Migrator",
    page_icon="📊",
    layout="wide"
)

# Custom Styling (CSS)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
        text-align: center;
    }
    .preview-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1F2937;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #4B5563;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 0.375rem;
        padding: 0.5rem 2rem;
        width: 100%;
        border: None;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">SAP ECC to S/4 HANA FICO Migrator</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Extract registry records, map configuration variables, and generate ready-to-load SAP migration spreadsheets on the fly.</div>', unsafe_allow_html=True)

# ----------------- SESSION STATE MAPPINGS INITIALIZATION -----------------
# Load defaults from backend.mappings if not present in session state
if 'mapping_cocd' not in st.session_state:
    st.session_state.mapping_cocd = pd.DataFrame([
        {"ecc_cocd": k, "s4_cocd": v}
        for k, v in mappings.COMPANY_CODE_MAPPING.items()
    ])

if 'mapping_plant_loc' not in st.session_state:
    st.session_state.mapping_plant_loc = pd.DataFrame([
        {
            "ecc_plant": int(k[0]) if isinstance(k[0], (int, float)) else k[0],
            "ecc_location": k[1],
            "s4_plant": v["s4_plant"],
            "s4_location": v["s4_location"]
        }
        for k, v in mappings.PLANT_LOCATION_MAPPING.items()
    ])

if 'mapping_cost_center' not in st.session_state:
    st.session_state.mapping_cost_center = pd.DataFrame([
        {"ecc_cost_center": int(k) if isinstance(k, (int, float)) else k, "s4_cost_center": v}
        for k, v in mappings.COST_CENTER_OVERRIDES.items()
    ])

# ----------------- SIDEBAR CONFIG -----------------
with st.sidebar:
    st.header("⚙️ Migration Settings")
    
    # 4 Radio buttons requested
    module = st.radio(
        "Select Migration Sub-Module",
        ["AP (Accounts Payable)", "AR (Accounts Receivable)", "Credit Management", "Asset Management (Selected)"],
        index=3 # Asset Management selected by default
    )
    
    st.info("💡 AP, AR, and Credit mapping routines are currently under construction. Please use **Asset Management** for active conversions.")
    
    # Backend URL Configuration
    backend_url = st.text_input("FastAPI Backend URL", value="http://127.0.0.1:8000")
    
    st.markdown("---")
    st.markdown("**Local Data Seeding Option**")
    st.write("Excel Master template seeded locally at: `templates/assets_load_template.xlsx`")

# ----------------- MAIN LAYOUT -----------------
col_upload, col_preview = st.columns([2, 3])

uploaded_df = None
uploaded_file_bytes = None

with col_upload:
    st.subheader("1. Upload Source Registry Excel")
    uploaded_file = st.file_uploader(
        "Drag and drop or browse for `sample_registry.xlsx`",
        type=["xlsx", "xls"],
        help="Upload the primary registry truth data source."
    )
    
    if uploaded_file is not None:
        try:
            # Read file bytes for posting to backend later
            uploaded_file_bytes = uploaded_file.getvalue()
            
            # Read excel structure using pandas to preview
            uploaded_df = pd.read_excel(io.BytesIO(uploaded_file_bytes))
            
            st.success("✅ Registry uploaded successfully!")
            
            # Filter active rows count
            # Active records are those whose Deact.Date is empty, None, NaT or '00/00/0000'
            def check_active(val):
                v_str = str(val).strip()
                return v_str in ('', 'nan', 'NaT', '00/00/0000', '00.00.0000')
                
            active_mask = uploaded_df['Deact.Date'].apply(check_active)
            active_count = active_mask.sum()
            inactive_count = len(uploaded_df) - active_count
            
            # Show summary metrics in modern cards
            st.markdown("### Upload Summary")
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{active_count}</div>
                        <div class="metric-label">Active Records</div>
                    </div>
                """, unsafe_allow_html=True)
            with mc2:
                st.markdown(f"""
                    <div class="metric-card" style="border-left-color: #EF4444;">
                        <div class="metric-value">{inactive_count}</div>
                        <div class="metric-label">Deactivated</div>
                    </div>
                """, unsafe_allow_html=True)
                
            st.warning(f"ℹ️ {active_count} active records (Deact.Date == 00/00/0000) will be mapped to the S/4 Hana template.")
            
        except Exception as e:
            st.error(f"Error reading file structure: {str(e)}")

with col_preview:
    st.subheader("2. Source Registry Preview")
    if uploaded_df is not None:
        st.markdown('<div class="preview-header">First 5 records of registry source:</div>', unsafe_allow_html=True)
        # Show first few records
        st.dataframe(uploaded_df.head(5), use_container_width=True)
        
        # Expand details
        with st.expander("🔍 View column catalog of uploaded registry"):
            st.write(list(uploaded_df.columns))
    else:
        st.info("Upload an Excel registry file on the left to see a preview of its rows here.")

st.markdown("---")

# ----------------- EDITABLE MAPPING CONFIGURATION -----------------
st.subheader("3. S/4 HANA FICO Migration Mappings (Interactive)")
st.markdown("Verify or modify these values before generating the template. The S/4 Hana loader will map the incoming ECC columns using these exact translation codes.")

tab_cocd, tab_plant_loc, tab_cc = st.tabs([
    "🏢 Company Code Mapping", 
    "🏭 Plant & Location Mapping", 
    "💰 Cost Center Mapping Overrides"
])

with tab_cocd:
    st.markdown("**ECC Company Code to S/4 Company Code:**")
    edited_cocd = st.data_editor(
        st.session_state.mapping_cocd, 
        num_rows="dynamic",
        key="editor_cocd",
        use_container_width=True
    )

with tab_plant_loc:
    st.markdown("**ECC (Plant, Location) to S/4 (Plant, Location) mappings:**")
    edited_plant_loc = st.data_editor(
        st.session_state.mapping_plant_loc,
        num_rows="dynamic",
        key="editor_plant_loc",
        use_container_width=True
    )

with tab_cc:
    st.markdown("**ECC Cost Center to S/4 proposed Cost Center overrides:**")
    st.caption("Any cost center not explicitly listed here will follow the automatic generation pattern: `S4_Plant` + `AM` + `last 2 digits of ECC Cost Center`.")
    edited_cc = st.data_editor(
        st.session_state.mapping_cost_center,
        num_rows="dynamic",
        key="editor_cc",
        use_container_width=True
    )

st.markdown("---")

# ----------------- MIGRATION PROCESSING TRIGGER -----------------
st.subheader("4. Process Assets Migration Template")

# Check if correct module selected
if module != "Asset Management (Selected)":
    st.error("❌ Process asset template is only supported when Asset Management is selected.")
else:
    # Trigger processing button
    process_btn = st.button("🚀 Process Asset Template & Generate Excel Load Sheet")
    
    if process_btn:
        if uploaded_file_bytes is None:
            st.error("❌ Please upload a sample registry Excel file first.")
        else:
            with st.spinner("Connecting to FastAPI backend, filtering registry, and populating S/4 HANA sheets..."):
                # Compile mappings into JSON payload
                mappings_dict = {
                    "cocd": edited_cocd.to_dict('records') if edited_cocd is not None else [],
                    "plant_loc": edited_plant_loc.to_dict('records') if edited_plant_loc is not None else [],
                    "cost_center": edited_cc.to_dict('records') if edited_cc is not None else []
                }
                
                payload = {
                    "mappings_json": json.dumps(mappings_dict)
                }
                
                files = {
                    "file": (uploaded_file.name, uploaded_file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                }
                
                try:
                    # Make API call to FastAPI backend
                    response = requests.post(
                        f"{backend_url}/process-asset",
                        data=payload,
                        files=files,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        st.success("🎉 Asset migration template processed and populated successfully!")
                        
                        # Offer file download
                        st.download_button(
                            label="📥 Download final S/4 HANA Assets Load Template Excel",
                            data=response.content,
                            file_name="assets_load_template_filled.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        
                        st.balloons()
                    else:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"❌ Backend processing failed: {error_detail}")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Failed to communicate with FastAPI backend at {backend_url}. Make sure your backend server is running.")
                    st.exception(e)

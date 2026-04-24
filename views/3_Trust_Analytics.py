import streamlit as st
import pandas as pd
from utils import db_client

st.set_page_config(page_title="TrustLens | Analytics", page_icon="ðŸ“Š", layout="wide")

if 'user' not in st.session_state or st.session_state.user is None:
    st.warning("Please login from the Home page first.")
    st.stop()

st.title("ðŸ“Š Trust Analytics Dashboard")
st.markdown("Monitor your secured documents and immutable audit trail.")

with st.spinner("Loading Ledger..."):
    docs = db_client.get_user_documents(st.session_state.user.id)
    
if docs:
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Secured Documents", len(docs))
    col2.metric("Cryptographic Proofs Generated", len(docs) * 2) # Hash + Signature
    col3.metric("Immutable Ledger Uptime", "100%")
    
    st.divider()
    st.markdown("### ðŸ“œ Document Audit Log")
    
    # Prepare Data for Table
    table_data = []
    for doc in docs:
        extracted = doc.get('extracted_fields', {})
        table_data.append({
            "Document ID": doc['id'],
            "Secured On": doc['created_at'][:10],
            "Extracted Name": extracted.get('name', 'N/A'),
            "Extracted Amount": extracted.get('amount', 'N/A'),
            "SHA-256 Hash": doc['content_hash'][:15] + "..."
        })
        
    df = pd.DataFrame(table_data)
    
    # Search and Filter
    search_query = st.text_input("ðŸ” Search Audit Log", placeholder="Enter Name or ID...")
    if search_query:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)]
        
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Export Data
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="ðŸ“¥ Export Audit Log (CSV)",
        data=csv,
        file_name='TrustLens_Audit_Log.csv',
        mime='text/csv',
    )
    
else:
    st.info("No documents found in your Trust Ledger. Upload a document to get started!")

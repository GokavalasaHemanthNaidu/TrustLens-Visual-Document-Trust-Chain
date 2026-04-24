import altair as alt
import pandas as pd
import streamlit as st

def render_provenance_chart():
    """
    Renders an interactive Altair chart showing the stages of the Document Trust Chain.
    Simulates the blockchain/provenance lifecycle.
    """
    stages = [
        {"Stage": "1. Document Upload", "Status": "Complete", "Order": 1, "Detail": "Image secured in local memory"},
        {"Stage": "2. AI OCR Extraction", "Status": "Complete", "Order": 2, "Detail": "Tesseract/Detectron2 processing"},
        {"Stage": "3. Deterministic Hashing", "Status": "Complete", "Order": 3, "Detail": "SHA-256 Checksum generated"},
        {"Stage": "4. Cryptographic Sign", "Status": "Complete", "Order": 4, "Detail": "ECDSA SECP256R1 Digital Signature"},
        {"Stage": "5. Decentralized Auth", "Status": "Complete", "Order": 5, "Detail": "Anchored to Supabase / Web3"}
    ]
    
    df = pd.DataFrame(stages)
    
    # Create an interactive timeline
    base = alt.Chart(df).encode(
        x=alt.X("Order:O", title="Trust Chain Timeline", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Stage:N", sort=alt.EncodingSortField(field="Order", order="ascending"), title=""),
        tooltip=["Stage", "Detail"]
    )
    
    points = base.mark_circle(size=500, color="#10B981", opacity=1).encode(
        color=alt.condition(alt.datum.Status == 'Complete', alt.value('#10B981'), alt.value('#D1D5DB'))
    )
    
    text = base.mark_text(
        align='left',
        baseline='middle',
        dx=20,
        dy=0,
        fontSize=14,
        fontWeight='bold'
    ).encode(
        text='Stage'
    )
    
    chart = (points + text).properties(
        width=700,
        height=300,
        title="Immutable Provenance Lifecycle"
    ).configure_view(strokeWidth=0).configure_axis(grid=False).interactive()
    
    st.altair_chart(chart, use_container_width=True)


import streamlit as st

# Configure the browser page
st.set_page_config(
    page_title="GeneScope AI",
    page_icon="🧬",
    layout="wide"
)

# Application heading
st.title("🧬 GeneScope AI")
st.subheader("Multi-Agent Genetic Research Assistant")

st.write(
    "Explore relationships between genes, genetic variants, "
    "diseases, and supporting scientific evidence."
)

st.divider()

# Research input
st.header("Start Your Research")

gene_name = st.text_input(
    "Enter a gene name",
    placeholder="Example: BRCA1"
)

# User action
if st.button("Analyze Gene"):
    if gene_name.strip():
        st.info(
            f"Research request received for: {gene_name.strip()}"
        )
        st.write(
            "Our AI agents will eventually retrieve research, "
            "analyze relationships, validate evidence, "
            "and build a knowledge graph."
        )
    else:
        st.warning("Please enter a gene name.")

st.divider()

# Future agent architecture
st.header("Our AI Research Agents")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Research Agent")
    st.write("Retrieves scientific information from trusted sources.")

    st.subheader("2. Relationship Analysis Agent")
    st.write("Identifies connections between genes and diseases.")

with col2:
    st.subheader("3. Evidence Validation Agent")
    st.write("Checks supporting evidence and flags uncertainty.")

    st.subheader("4. Knowledge Graph Agent")
    st.write("Prepares relationships for interactive visualization.")

st.caption(
    "GeneScope AI | Educational research prototype | "
    "Not for clinical diagnosis"
)

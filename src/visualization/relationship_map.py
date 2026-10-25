
import streamlit.components.v1 as components
from pyvis.network import Network


GENE_COLOR = {"background": "#dbeafe", "border": "#6795cf"}
VARIANT_COLORS = {
    "APOE ε4": {"background": "#ede9fe", "border": "#a394d1"},
    "APOE ε2": {"background": "#dcf2e8", "border": "#7bb89e"},
}
DISEASE_COLOR = {"background": "#fce7ec", "border": "#d69aa9"}


def show_relationship_map(relationships, review_status=None):
    """Display candidates with their batch review decision, without mutating them."""

    if not relationships:
        return False

    if review_status == "rejected":
        status_label = "Rejected candidate"
        status_title = "Rejected by researcher"
        edge_color, dashed = "#b84b55", True
    elif review_status == "approved":
        status_label = "Researcher-approved"
        status_title = "Approved by researcher"
        edge_color, dashed = "#23805a", False
    else:
        status_label = "Unreviewed candidate"
        status_title = "Candidate awaiting researcher review"
        edge_color, dashed = "#94a3b8", False

    network = Network(
        height="420px",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#14264d",
    )

    network.add_node(
        "APOE",
        label="APOE",
        title="Gene: APOE",
        color=GENE_COLOR,
        shape="box",
        size=28,
        level=0,
    )

    added_nodes = {"APOE"}
    added_edges = set()

    for relationship in relationships:
        allele = relationship.get("allele")
        disease = relationship.get("disease")
        relationship_type = relationship.get("relationship_type", "associated")

        if not allele or not disease:
            continue

        if allele not in added_nodes:
            network.add_node(
                allele,
                label=allele,
                title=f"Genetic variant: {allele}",
                color=VARIANT_COLORS.get(allele, {"background": "#fff3d6", "border": "#d0ae65"}),
                shape="box",
                size=24,
                level=1,
            )
            added_nodes.add(allele)

        if disease not in added_nodes:
            network.add_node(
                disease,
                label=disease,
                title=f"Disease: {disease}",
                color=DISEASE_COLOR,
                shape="box",
                size=28,
                level=2,
            )
            added_nodes.add(disease)

        if ("APOE", allele) not in added_edges:
            network.add_edge("APOE", allele, title="Gene variant")
            added_edges.add(("APOE", allele))

        label = relationship_type.replace("_", " ")
        edge_key = (allele, disease, relationship_type)
        if edge_key in added_edges:
            continue
        added_edges.add(edge_key)

        network.add_edge(
            allele,
            disease,
            label=f"{label}\n{status_label}",
            title=(
                f"Relationship: {label}\n"
                f"Review status: {status_title}\n"
                "AI-extracted candidate. Human review is not independent scientific verification."
            ),
            arrows="to",
            color=edge_color,
            dashes=dashed,
        )

    network.set_options(
        """
        {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "LR",
              "sortMethod": "directed",
              "levelSeparation": 240,
              "nodeSpacing": 160,
              "treeSpacing": 180
            }
          },
          "physics": {
            "enabled": false
          },
          "nodes": {
            "font": {
              "size": 17
            },
            "borderWidth": 1.5,
            "margin": 12,
            "shapeProperties": {
              "borderRadius": 10
            }
          },
          "edges": {
            "smooth": false,
            "width": 1.5,
            "color": {
              "color": "#94a3b8",
              "highlight": "#64748b",
              "hover": "#64748b",
              "inherit": false
            },
            "arrows": {
              "to": {
                "enabled": true,
                "scaleFactor": 0.7
              }
            },
            "font": {
              "size": 12,
              "align": "horizontal",
              "color": "#425570",
              "background": "#ffffff",
              "strokeWidth": 4,
              "strokeColor": "#ffffff"
            }
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true
          }
        }
        """
    )

    components.html(
        network.generate_html(),
        height=440,
        scrolling=False,
    )

    return True

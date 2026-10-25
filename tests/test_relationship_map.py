"""Review status must be visible without altering scientific candidates."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from src.visualization import relationship_map


@pytest.mark.parametrize("status, label, color, dashed", [
    (None, "Unreviewed candidate", "#94a3b8", False),
    ("approved", "Researcher-approved", "#23805a", False),
    ("rejected", "Rejected candidate", "#b84b55", True),
])
def test_graph_edges_distinguish_review_decisions_without_changing_candidates(
    monkeypatch, status, label, color, dashed
):
    candidates = [{
        "gene": "APOE", "allele": "APOE ε4", "disease": "Alzheimer's disease",
        "relationship_type": "increased_risk",
        "relationship_status": "rule_extracted_candidate",
        "evidence_status": "model_assessed_supported",
        "citations": ["pubmed_00000000"],
    }]
    original = deepcopy(candidates)
    network = relationship_map.Network(directed=True)
    monkeypatch.setattr(relationship_map, "Network", Mock(return_value=network))
    render_html = Mock()
    monkeypatch.setattr(relationship_map.components, "html", render_html)
    assert relationship_map.show_relationship_map(candidates, review_status=status)
    risk_edge = next(edge for edge in network.edges if edge["from"] == "APOE ε4")
    assert risk_edge["label"] == "increased risk\n" + label
    assert risk_edge["color"] == color
    assert risk_edge["dashes"] is dashed
    assert "not independent scientific verification" in risk_edge["title"]
    assert candidates == original
    render_html.assert_called_once()
    assert label in render_html.call_args.args[0]

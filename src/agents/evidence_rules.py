"""Application source parsing and conservative evidence presentation rules.

These rules are not an evaluator or a scientific truth classifier. Precision
claims must preserve the indexed wording; unsupported paraphrases are withheld,
not declared biologically false. The independent evaluation code stays separate.
"""

import re
import unicodedata

SOURCE_ID = re.compile(r"\b(?:pubmed_\d+|ncbi_gene_\d+)\b", re.I)
ALLELE_LABEL = re.compile(r"\b(?:epsilon\s*[234]|apoe\s*[234]|e[234])\b|[εϵɛ]\s*[234]\b", re.I)
PRECISION = re.compile(
    r"\d|\b(?:half|percent(?:age)?|prevalence|frequency|proportion|fraction|"
    r"fold|nucleotide|substitution|haplotype)\b|\b[ACGT]\s*(?:→|->|>|/)\s*[ACGT]\b", re.I
)


def source_ids(text):
    return sorted({s.casefold() for s in SOURCE_ID.findall(text or "")})


def evidence_wording(text):
    text = re.sub(r"\[[^\]]*(?:pubmed_|ncbi_gene_)[^\]]*\]", "", text, flags=re.I)
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.translate(str.maketrans({"’": "'", "“": '"', "”": '"'}))
    return " ".join(text.strip(" \t\n\"'*>#").split()).rstrip(" .!?\t\n\"'")


def requires_exact_precision(text):
    return bool(PRECISION.search(ALLELE_LABEL.sub("", SOURCE_ID.sub("", text or ""))))


def precision_is_grounded(text, passages):
    """Require an intact evidence span, not a matching number in another context.

For example, a gene-level half-of-cases quote cannot justify an allele-prevalence
paraphrase. Allele labels alone are not quantitative assertions. This contract
can withhold valid precision paraphrases; the indexed passage remains available.
"""
    if not requires_exact_precision(text):
        return True
    claim = evidence_wording(text)
    return bool(claim) and any(claim in evidence_wording(p) for p in passages)


def checked_evidence_quote(value, evidence_by_id, citations):
    """Accept only an intact sentence/span boundary from the cited source.

The quote is displayed as source text, never as validation of the original
paraphrase. In particular, do not extract a quantity fragment without its subject.
"""
    if not isinstance(value, dict):
        return None
    source, quote = value.get("document_id"), value.get("text")
    if source not in citations or not isinstance(quote, str) or len(quote.split()) < 6:
        return None
    quote = quote.strip()
    for passage in evidence_by_id.get(source, []):
        start = passage.find(quote)
        if start < 0:
            continue
        before, after = passage[:start].rstrip(), passage[start + len(quote):].lstrip()
        if (not before or before[-1] in ".!?\n:") and (not after or quote[-1] in ".!?" or after[0] in ".!?"):
            return {"document_id": source, "text": quote}
    return None

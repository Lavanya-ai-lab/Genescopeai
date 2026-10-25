
"""
Normalize all locally downloaded PubMed XML articles.

Input:
    data/raw/pubmed_*.xml

Output:
    data/processed/pubmed_*_normalized.json
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data/raw"
OUTPUT_DIR = PROJECT_ROOT / "data/processed"


def element_text(element):
    """Extract text, including nested XML formatting."""
    if element is None:
        return ""

    return " ".join("".join(element.itertext()).split())


def normalize_pubmed_record(root):
    """Convert one PubMed XML record to standard JSON."""

    article = root.find(".//PubmedArticle")

    if article is None:
        raise ValueError("No PubMed article found in XML.")

    pmid = article.findtext("./MedlineCitation/PMID")

    if not pmid:
        raise ValueError("PubMed record has no PMID.")

    title = element_text(
        article.find("./MedlineCitation/Article/ArticleTitle")
    )

    abstract_parts = []

    for section in article.findall(
        "./MedlineCitation/Article/Abstract/AbstractText"
    ):
        text = element_text(section)
        label = section.get("Label")

        if text:
            abstract_parts.append(
                f"{label}: {text}" if label else text
            )

    abstract = "\n".join(abstract_parts)

    if not abstract:
        raise ValueError(
            f"PMID {pmid} has no abstract."
        )

    authors = []

    for author in article.findall(
        "./MedlineCitation/Article/AuthorList/Author"
    ):
        last = author.findtext("LastName")
        first = author.findtext("ForeName")

        if last:
            authors.append(
                f"{first or ''} {last}".strip()
            )

    doi = None

    for identifier in article.findall(
        "./PubmedData/ArticleIdList/ArticleId"
    ):
        if identifier.get("IdType") == "doi":
            doi = identifier.text
            break

    journal = article.findtext(
        "./MedlineCitation/Article/Journal/Title"
    )

    year = article.findtext(
        "./MedlineCitation/Article/Journal/"
        "JournalIssue/PubDate/Year"
    )

    if not year:
        year = article.findtext(
            "./MedlineCitation/Article/ArticleDate/Year"
        )

    return {
        "document_id": f"pubmed_{pmid}",
        "document_type": "research_article",
        "title": title,
        "content": (
            f"Title: {title}\n"
            f"Abstract: {abstract}"
        ),
        "metadata": {
            "source": "PubMed",
            "pmid": pmid,
            "doi": doi,
            "authors": authors,
            "publication_year": year,
            "journal": journal,
            "source_url": (
                f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            ),
        },
    }


def main():
    """Normalize all downloaded PubMed XML files."""

    files = sorted(RAW_DIR.glob("pubmed_*.xml"))

    if not files:
        print("No PubMed XML files found.")
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    successful = 0
    failed = 0

    for xml_file in files:
        try:
            root = ET.parse(xml_file).getroot()
            document = normalize_pubmed_record(root)

            pmid = document["metadata"]["pmid"]

            # Check that filename and article identity agree.
            expected_name = f"pubmed_{pmid}.xml"

            if xml_file.name != expected_name:
                raise ValueError(
                    "Filename does not match article PMID."
                )

            output_file = (
                OUTPUT_DIR
                / f"pubmed_{pmid}_normalized.json"
            )

            with output_file.open(
                "w", encoding="utf-8"
            ) as file:
                json.dump(
                    document,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            print(f"SUCCESS: PMID {pmid}")
            print(f"  {document['title']}")
            print(f"  Saved: {output_file.name}")

            successful += 1

        except (ET.ParseError, OSError, ValueError, KeyError) as error:
            print(f"FAILED: {xml_file.name}")
            print(f"  Reason: {error}")
            failed += 1

    print("\nProcessing summary")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()

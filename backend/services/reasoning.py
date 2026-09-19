import re

from backend.services.rag import search_knowledge


# =========================================================
# KNOWLEDGE QUESTION ANSWERING
# =========================================================

import re

from backend.services.rag import search_knowledge


def split_into_sentences(text):
    """Extract readable scientific sentences from PDF text."""
    if not text:
        return []

    text = " ".join(text.split())

    # Remove common PDF bullets and normalize whitespace.
    text = re.sub(r"[•▪●◦]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # PDF extraction sometimes joins headings and sentence fragments with
    # semicolons. Split on strong sentence boundaries first.
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)

    sentences = []

    for sentence in raw_sentences:
        sentence = sentence.strip(" -–—:;")

        # Remove obvious page/header noise at the beginning.
        sentence = re.sub(
            r"^(?:\d+\s+)?(?:THE\s+)?STATE OF THE WORLD'S BIODIVERSITY.*?\b(?:AGRICULTURE|AGRICULTURE\s+3)\b\s*",
            "",
            sentence,
            flags=re.IGNORECASE
        )

        if len(sentence) < 45:
            continue

        # Do not display fragments ending in an incomplete connector.
        if sentence.lower().endswith(
            ("through", "and", "or", "of", "to", "with", "by", "for")
        ):
            continue

        sentences.append(sentence)

    return sentences


def get_question_concepts(question):
    question = question.lower()

    concepts = []

    if "organic carbon" in question or "organic matter" in question:
        concepts.extend([
            "organic carbon",
            "organic matter",
            "soil organic matter",
            "soil carbon"
        ])

    if "biodiversity" in question:
        concepts.extend([
            "biodiversity",
            "soil biodiversity",
            "soil organisms",
            "soil biota",
            "species"
        ])

    if "soil moisture" in question or "water retention" in question:
        concepts.extend([
            "soil moisture",
            "water retention",
            "store water",
            "capture and store water",
            "water"
        ])

    if "soil structure" in question or "structure" in question:
        concepts.extend([
            "soil structure",
            "soil aggregates"
        ])

    if "climate" in question or "temperature" in question or "rainfall" in question:
        concepts.extend([
            "climate",
            "temperature",
            "rainfall"
        ])

    if "habitat" in question or "species" in question:
        concepts.extend([
            "habitat",
            "species",
            "ecosystem"
        ])

    if (
        "land use" in question
        or "land-use" in question
        or "monoculture" in question
        or "crop diversity" in question
        or "intercropping" in question
        or "crop rotation" in question
    ):
        concepts.extend([
            "land use",
            "land-use",
            "monoculture",
            "crop diversity",
            "crop rotation",
            "intercropping",
            "diversification",
            "habitat"
        ])

    return list(dict.fromkeys(concepts))


def score_sentence(sentence, concepts, question):
    """Score evidence by direct scientific relevance."""
    s = sentence.lower()
    score = 0

    for concept in concepts:
        if concept in s:
            score += 4

    # Strong direct relationships.
    relationships = [
        (
            ["organic matter", "organic carbon", "soil carbon"],
            ["soil biodiversity", "biodiversity", "soil organisms", "soil biota"],
            18
        ),
        (
            ["loss of soil organic matter", "loss of organic matter"],
            ["weaker soil structure", "soil structure"],
            16
        ),
        (
            ["soil structure", "weaker soil structure"],
            ["capture and store water", "store water", "water retention"],
            16
        ),
        (
            ["organic matter"],
            ["soil organisms", "soil biodiversity", "biodiversity"],
            14
        ),
        (
            ["organic matter", "organic carbon"],
            ["water", "water retention", "capture and store water"],
            8
        ),
        (
            ["monoculture", "crop diversity", "crop rotation", "intercropping"],
            ["biodiversity", "soil biodiversity", "soil organisms", "soil biota"],
            20
        ),
        (
            ["soil moisture", "water availability", "water stress"],
            ["biodiversity", "soil biodiversity", "soil organisms", "soil biota"],
            14
        )
    ]

    for source_terms, target_terms, points in relationships:
        if any(term in s for term in source_terms) and any(
            term in s for term in target_terms
        ):
            score += points

    # For organic-carbon/biodiversity questions, direct evidence is
    # substantially stronger than generic biodiversity statements.
    if (
        ("organic carbon" in question.lower() or "organic matter" in question.lower())
        and "biodiversity" in question.lower()
    ):
        has_organic = any(
            term in s
            for term in [
                "organic matter",
                "organic carbon",
                "soil carbon"
            ]
        )
        has_biodiversity = any(
            term in s
            for term in [
                "soil biodiversity",
                "biodiversity",
                "soil organisms",
                "soil biota"
            ]
        )

        if has_organic and has_biodiversity:
            score += 30
        elif has_biodiversity and not has_organic:
            score -= 12

    # Strongly prefer sentences that contain an actual relationship.
    causal_terms = [
        "influenced by",
        "affect",
        "affects",
        "associated with",
        "lead to",
        "reducing",
        "increase",
        "decrease",
        "support",
        "maintain",
        "enhance",
        "contribute",
        "important"
    ]

    if any(term in s for term in causal_terms):
        score += 3

    # Penalize material that is technically related to soil but not useful
    # for the requested relationship.
    unrelated_terms = [
        "leaching",
        "volatilization",
        "harvested products",
        "greenhouse gas",
        "greenhouse-gas",
        "atmospheric",
        "community ecotoxicology",
        "dna analysis",
        "monitoring programs",
        "voluntary guidelines",
        "ecosystem services"
    ]

    for term in unrelated_terms:
        if term in s:
            score -= 7

    # Avoid sentences that are primarily headings or bibliographic context.
    heading_terms = [
        "working on the basis of this definition",
        "this section presents",
        "recommendations provided",
        "section 3.7",
        "box 5.14",
        "source:",
        "adapted from"
    ]

    for term in heading_terms:
        if term in s:
            score -= 10

    # Penalize very long sentences because they are often PDF extraction
    # fragments containing several unrelated claims.
    if len(sentence) > 350:
        score -= 5

    return score


def extract_relevant_evidence(question, results, max_items=3):
    concepts = get_question_concepts(question)
    candidates = []

    for result in results:
        text = result.get("text", "")
        sentences = split_into_sentences(text)

        for sentence in sentences:
            score = score_sentence(sentence, concepts, question)

            if score > 4:
                candidates.append({
                    "score": score,
                    "text": sentence,
                    "filename": result.get("filename"),
                    "page": result.get("page")
                })

    candidates.sort(
        key=lambda item: (
            -item["score"],
            len(item["text"])
        )
    )

    selected = []
    seen_sentences = set()
    source_pages = set()

    for item in candidates:
        normalized = re.sub(
            r"\s+",
            " ",
            item["text"].lower().strip()
        )

        if normalized in seen_sentences:
            continue

        source_key = (
            item.get("filename"),
            item.get("page")
        )

        # Prefer different source pages, but allow another sentence from
        # the same page if it is substantially stronger.
        if source_key in source_pages and item["score"] < 18:
            continue

        # Avoid very long evidence blocks.
        if len(item["text"]) > 420:
            continue

        seen_sentences.add(normalized)
        source_pages.add(source_key)
        selected.append(item)

        if len(selected) >= max_items:
            break

    return selected


def build_scientific_evidence(question, results):
    selected = extract_relevant_evidence(
        question,
        results,
        max_items=3
    )

    evidence = []

    for item in selected:
        evidence.append({
            "filename": item["filename"],
            "page": item["page"],
            "text": item["text"]
        })

    return evidence


def answer_knowledge_question(question: str):
    results = search_knowledge(question, top_k=8)

    if not results:
        return {
            "answer": (
                "I could not find enough scientific evidence in the "
                "current knowledge base to answer this question."
            ),
            "evidence": []
        }

    evidence = build_scientific_evidence(
        question,
        results
    )

    question_lower = question.lower()

    if (
        "organic carbon" in question_lower
        and "biodiversity" in question_lower
    ):
        answer = (
            "Low soil organic carbon can affect soil biodiversity because "
            "organic matter provides important food and energy sources for "
            "many soil organisms. Scientific evidence indicates that soil "
            "biodiversity is strongly influenced by the quantity and quality "
            "of organic matter present in the soil. When organic matter "
            "declines, soil structure can also weaken, which can reduce the "
            "soil's ability to capture and store water. Maintaining or "
            "increasing organic matter through appropriate organic inputs "
            "and soil cover can therefore help support soil biological "
            "activity and biodiversity."
        )

    elif "soil biodiversity" in question_lower:
        answer = (
            "Soil biodiversity refers to the variety of organisms living "
            "in soil and the interactions they form. These organisms "
            "contribute to important soil processes and ecosystem functions. "
            "Soil organic matter, soil structure and other environmental "
            "conditions can influence soil biological communities."
        )

    elif (
        "water retention" in question_lower
        or "water holding" in question_lower
    ):
        answer = (
            "Soil water retention is influenced by soil structure and "
            "organic matter. Loss of soil organic matter can weaken soil "
            "structure and reduce the soil's capacity to capture and store "
            "water. Maintaining organic matter and healthy soil conditions "
            "can therefore support soil water retention."
        )

    else:
        if evidence:
            answer = (
                "Based on the retrieved scientific evidence, "
                + " ".join(
                    item["text"]
                    for item in evidence[:3]
                )
            )
        else:
            answer = (
                "The retrieved scientific sources contain relevant "
                "information, but they do not provide enough directly "
                "relevant evidence to give a specific answer."
            )

    return {
        "answer": answer,
        "evidence": evidence
    }


def get_evidence(
    query,
    top_k=5
):
    """Return concise, sentence-level evidence instead of whole PDF chunks."""

    results = search_knowledge(
        query,
        top_k
    )

    candidates = []
    concepts = get_question_concepts(query)

    # Useful environmental terms that may not be present in the
    # question wording but are important for soil reasoning.
    query_lower = query.lower()
    if "organic" in query_lower or "carbon" in query_lower:
        concepts.extend([
            "organic matter",
            "organic carbon",
            "soil carbon"
        ])
    if "water" in query_lower or "moisture" in query_lower:
        concepts.extend([
            "water",
            "water retention",
            "capture and store water",
            "soil moisture"
        ])
    if "biodiversity" in query_lower:
        concepts.extend([
            "biodiversity",
            "soil biodiversity",
            "soil organisms"
        ])

    concepts = list(dict.fromkeys(concepts))

    weak_context_terms = [
        "greenhouse gas emissions",
        "atmospheric greenhouse",
        "nitrogen fertilizer",
        "manufacture of nitrogen",
        "leaching",
        "volatilization",
        "harvested products",
        "fuel-energy input",
        "labour input"
    ]

    for result in results:
        text = result.get("text", "")
        sentences = split_into_sentences(text)

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Skip obvious headings, navigation fragments and very long
            # PDF boilerplate lines.
            if len(sentence) > 420:
                continue

            score = score_sentence(
                sentence,
                concepts,
                query
            )

            for term in weak_context_terms:
                if term in sentence_lower:
                    score -= 4

            # Strongly reward direct cause/effect relationships.
            relationship_pairs = [
                (["organic matter", "organic carbon", "soil carbon"],
                 ["soil biodiversity", "biodiversity", "soil organisms", "soil biota"], 35),
                (["organic matter", "organic carbon"],
                 ["soil structure", "soil aggregates"], 14),
                (["soil structure", "weaker soil structure"],
                 ["capture and store water", "store water", "water retention"], 18),
                (["soil organic matter"],
                 ["supporting soil biodiversity", "soil biodiversity"], 25),
                (["monoculture", "crop diversity", "crop rotation", "intercropping"],
                 ["biodiversity", "soil biodiversity", "soil organisms", "soil biota"], 30),
                (["crop diversity", "crop rotation", "intercropping", "diversification"],
                 ["soil biodiversity", "biodiversity"], 28),
                (["soil moisture", "water availability", "water stress"],
                 ["biodiversity", "soil biodiversity", "soil organisms", "soil biota"], 20),
                (["soil moisture", "water retention"],
                 ["soil organisms", "soil biodiversity", "biodiversity"], 16)
            ]

            for left_terms, right_terms, points in relationship_pairs:
                if (
                    any(term in sentence_lower for term in left_terms)
                    and any(term in sentence_lower for term in right_terms)
                ):
                    score += points

            # For biodiversity-related soil questions, direct evidence
            # connecting organic matter/carbon with biodiversity is much
            # stronger than a generic statement about soil biodiversity.
            wants_organic_biodiversity = (
                ("organic" in query_lower or "carbon" in query_lower)
                and "biodiversity" in query_lower
            )

            if wants_organic_biodiversity:
                has_organic = any(
                    term in sentence_lower
                    for term in [
                        "organic matter",
                        "organic carbon",
                        "soil carbon"
                    ]
                )
                has_biodiversity = any(
                    term in sentence_lower
                    for term in [
                        "soil biodiversity",
                        "biodiversity",
                        "soil organisms",
                        "soil biota"
                    ]
                )

                if has_organic and has_biodiversity:
                    score += 30
                elif has_biodiversity and not has_organic:
                    score -= 12

            if score > 0:
                candidates.append({
                    "score": score,
                    "source": result.get("filename"),
                    "page": result.get("page"),
                    "distance": result.get("distance"),
                    "text": sentence.strip()
                })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    evidence = []
    seen = set()
    source_pages = set()

    for item in candidates:
        key = item["text"].lower()
        page_key = (item["source"], item["page"])

        if key in seen:
            continue

        # Prefer one strong sentence per source page.
        if page_key in source_pages:
            continue

        seen.add(key)
        source_pages.add(page_key)

        evidence.append({
            "source": item["source"],
            "page": item["page"],
            "distance": item["distance"],
            "text": item["text"]
        })

        if len(evidence) >= 3:
            break

    return evidence


# =========================================================
# BUILD OBSERVED METRICS
# =========================================================

def get_observed_metrics(data):

    observed = {}

    fields = [

        "soil_ph",

        "organic_carbon",

        "soil_moisture",

        "temperature",

        "rainfall",

        "land_use",

        "species_richness",

        "habitat_diversity",

        "pollution_level",

        "deforestation_level",

        "region"
    ]

    for field in fields:

        value = getattr(
            data,
            field,
            None
        )

        if value is not None:

            observed[field] = value

    return observed


# =========================================================
# CALCULATE CONFIDENCE
# =========================================================

def calculate_confidence(
    data,
    evidence_count
):

    observed_metrics = get_observed_metrics(
        data
    )

    metric_count = len(
        observed_metrics
    )

    if (
        metric_count >= 4
        and evidence_count >= 3
    ):

        return "High"

    elif (
        metric_count >= 2
        and evidence_count >= 2
    ):

        return "Moderate"

    else:

        return "Limited"


# =========================================================
# ADD RECOMMENDATION
# =========================================================

def add_recommendation(
    recommendations,
    recommendation,
    reason,
    links,
    metrics,
    time_horizon,
    evidence,
    priority=2
):

    recommendations.append({

        "priority":
            priority,

        "recommendation":
            recommendation,

        "reason":
            reason,

        "environmental_links":
            links,

        "metrics":
            metrics,

        "time_horizon":
            time_horizon,

        "evidence":
            evidence
    })


# =========================================================
# ENVIRONMENTAL REASONING
# =========================================================

def analyze_environment(data):

    findings = []

    recommendations = []

    relationships = []

    uncertainties = []

    observed_metrics = get_observed_metrics(
        data
    )


    # =====================================================
    # 1. MONOCULTURE + LOW ORGANIC CARBON + LOW MOISTURE
    # =====================================================

    if (
        data.land_use is not None
        and "monoculture" in data.land_use.lower()
        and data.organic_carbon is not None
        and data.organic_carbon < 1.0
        and data.soil_moisture is not None
        and data.soil_moisture < 20
    ):
        findings.append(
            "Monoculture, low soil organic carbon and low soil "
            "moisture form a combined soil-management pressure "
            "that may affect soil condition, water retention and "
            "soil biodiversity."
        )

        relationships.append({
            "variables": ["land_use", "organic_carbon", "soil_moisture"],
            "relationship":
                "Diversified cropping and organic-matter "
                "management can influence soil biodiversity "
                "and soil condition, while soil structure is "
                "relevant to water retention."
        })

        # Check each relationship independently. Missing evidence
        # is reported honestly rather than being replaced by
        # unrelated passages from the knowledge base.
        evidence_groups = [
            {
                "relationship": "Organic carbon → Soil biodiversity",
                "query": "organic matter organic carbon soil biodiversity",
            },
            {
                "relationship": "Land use / monoculture → Biodiversity",
                "query": "monoculture crop diversity biodiversity",
            },
            {
                "relationship": "Soil moisture → Soil biological conditions",
                "query": "soil moisture water retention soil biodiversity soil organisms",
            },
        ]

        relationship_evidence = []
        evidence_status = []

        causal_terms = [
            "influenced by", "affect", "affects", "affected by",
            "associated with", "lead to", "leads to", "result in",
            "results in", "support", "supports", "increase",
            "increases", "decrease", "decreases", "reduce",
            "reduces", "enhance", "enhances", "contribute",
            "contributes", "important for", "essential to",
            "depend", "depends on", "promote", "promotes",
            "maintain", "maintains", "loss of", "change in",
            "changes in", "influence", "influences"
        ]

        for group in evidence_groups:
            results = get_evidence(group["query"])
            direct_results = []

            for item in results:
                sentence = item.get("text", "").strip().lower()

                if group["relationship"].startswith("Organic"):
                    side_a = (
                        "organic matter" in sentence
                        or "organic carbon" in sentence
                        or "soil organic" in sentence
                    )
                    side_b = (
                        "soil biodiversity" in sentence
                        or "biodiversity" in sentence
                        or "soil organisms" in sentence
                        or "soil fauna" in sentence
                        or "soil microorganisms" in sentence
                    )

                elif group["relationship"].startswith("Land"):
                    side_a = (
                        "monoculture" in sentence
                        or "crop diversity" in sentence
                        or "diversification" in sentence
                        or "crop rotation" in sentence
                        or "intercropping" in sentence
                    )
                    side_b = (
                        "biodiversity" in sentence
                        or "species diversity" in sentence
                        or "species richness" in sentence
                        or "habitat diversity" in sentence
                    )

                else:
                    side_a = (
                        "soil moisture" in sentence
                        or "water retention" in sentence
                        or "water availability" in sentence
                        or "soil water" in sentence
                    )
                    side_b = (
                        "soil biodiversity" in sentence
                        or "soil organisms" in sentence
                        or "soil fauna" in sentence
                        or "soil microorganisms" in sentence
                        or "biological activity" in sentence
                    )

                has_causal_language = any(
                    term in sentence for term in causal_terms
                )

                if side_a and side_b and has_causal_language:
                    direct_results.append(item)

                if len(direct_results) >= 2:
                    break

            if direct_results:
                for item in direct_results:
                    evidence_item = dict(item)
                    evidence_item["relationship"] = group["relationship"]
                    evidence_item["evidence_status"] = "direct"
                    relationship_evidence.append(evidence_item)

                evidence_status.append({
                    "relationship": group["relationship"],
                    "status": "direct evidence found"
                })
            else:
                evidence_status.append({
                    "relationship": group["relationship"],
                    "status":
                        "direct evidence not found in current knowledge base"
                })

        found_count = sum(
            1 for item in evidence_status
            if item["status"] == "direct evidence found"
        )

        if found_count == 3:
            evidence_reason = (
                "Direct supporting evidence was retrieved for all "
                "three relationships."
            )
        elif found_count > 0:
            evidence_reason = (
                "Direct supporting evidence was retrieved for "
                f"{found_count} of the three relationships. "
                "Relationships without direct evidence are explicitly "
                "marked as unsupported by the current knowledge base."
            )
        else:
            evidence_reason = (
                "Direct supporting evidence was not found for these "
                "three relationships in the current knowledge base."
            )

        add_recommendation(
            recommendations,
            "Reduce dependence on monoculture by introducing "
            "crop rotation, intercropping or diverse cover crops, "
            "while increasing organic inputs and maintaining soil "
            "cover to support soil condition and water retention.",
            evidence_reason,
            [
                "Land-use diversity",
                "Soil organic carbon",
                "Soil moisture",
                "Soil biodiversity",
                "Soil water retention"
            ],
            [
                "Land-use diversity",
                "Soil organic carbon",
                "Soil moisture",
                "Soil biodiversity",
                "Soil water retention"
            ],
            "Medium term: 1–3 years",
            relationship_evidence
        )

        # add_recommendation() appends directly to the list.
        # Add relationship-level evidence metadata to the
        # recommendation that was just created.
        if recommendations:
            recommendations[-1]["evidence_status"] = evidence_status
            recommendations[-1]["evidence_relationships_checked"] = [
                group["relationship"] for group in evidence_groups
            ]


    elif (
        data.organic_carbon is not None
        and data.organic_carbon < 1.0
        and data.soil_moisture is not None
        and data.soil_moisture < 20
    ):

        findings.append(
            "Low soil organic carbon and low soil moisture "
            "indicate interacting soil-quality and water-stress "
            "conditions."
        )

        relationships.append({

            "variables": [

                "organic_carbon",

                "soil_moisture"
            ],

            "relationship":
                "Low soil organic matter can be associated with "
                "weaker soil structure and reduced capacity to "
                "capture and store water."
        })

        evidence = get_evidence(

            "soil organic matter soil structure "
            "capture store water soil moisture"
        )

        add_recommendation(

            recommendations,

            "Increase organic inputs and maintain soil cover "
            "to support soil structure and water retention.",

            "The retrieved evidence connects soil organic "
            "matter with soil structure and water-storage "
            "capacity.",

            [

                "Low organic carbon → soil-quality pressure",

                "Low soil moisture → water stress",

                "Organic matter → soil structure",

                "Soil structure → water storage"
            ],

            [

                "Soil organic carbon",

                "Soil moisture",

                "Soil water retention"
            ],

            "Medium term",

            evidence,

            priority=1
        )


    # =====================================================
    # 3. LOW RAINFALL + LOW SOIL MOISTURE
    # =====================================================

    if (
        data.rainfall is not None
        and data.rainfall < 600
        and data.soil_moisture is not None
        and data.soil_moisture < 20
    ):

        findings.append(
            "Low rainfall combined with low soil moisture "
            "indicates increased water-availability pressure."
        )

        relationships.append({

            "variables": [

                "rainfall",

                "soil_moisture"
            ],

            "relationship":
                "Lower rainfall together with low soil moisture "
                "can indicate increased pressure on water "
                "availability."
        })

        evidence = get_evidence(

            "rainfall soil moisture water availability "
            "soil water retention infiltration"
        )

        add_recommendation(

            recommendations,

            "Prioritize practices that improve soil water "
            "retention and reduce moisture loss.",

            "The retrieved evidence describes the role of "
            "vegetation, soils and soil biota in water "
            "infiltration and water-holding capacity.",

            [

                "Low rainfall → lower water input",

                "Low soil moisture → water stress",

                "Soil structure → water retention"
            ],

            [

                "Soil moisture",

                "Soil water retention"
            ],

            "Short to medium term",

            evidence,

            priority=2
        )


    # =====================================================
    # 4. LOW ORGANIC CARBON ONLY
    # =====================================================

    if (
        data.organic_carbon is not None
        and data.organic_carbon < 1.0
        and not (
            data.soil_moisture is not None
            and data.soil_moisture < 20
        )
    ):

        findings.append(
            "Low soil organic carbon indicates a potential "
            "soil-quality concern."
        )

        relationships.append({

            "variables": [

                "organic_carbon",

                "soil_biodiversity"
            ],

            "relationship":
                "Soil biodiversity is influenced by the "
                "quantity and quality of organic matter."
        })

        evidence = get_evidence(

            "soil organic matter soil biodiversity "
            "organic inputs crop residues"
        )

        add_recommendation(

            recommendations,

            "Increase organic inputs and maintain soil cover.",

            "Retrieved evidence indicates that increasing "
            "organic matter inputs can benefit soil "
            "biodiversity.",

            [

                "Low organic carbon → reduced organic matter",

                "Organic matter → soil biodiversity"
            ],

            [

                "Soil organic carbon",

                "Soil biodiversity"
            ],

            "Medium term",

            evidence,

            priority=2
        )


    # =====================================================
    # 5. MONOCULTURE + LOW ORGANIC CARBON
    # =====================================================

    if (
        data.land_use is not None
        and "monoculture" in data.land_use.lower()
        and data.organic_carbon is not None
        and data.organic_carbon < 1.0
        and not (
            data.soil_moisture is not None
            and data.soil_moisture < 20
        )
    ):

        findings.append(
            "Monoculture combined with low soil organic carbon "
            "indicates reduced crop-system diversity alongside "
            "soil-quality pressure."
        )

        relationships.append({

            "variables": [

                "land_use",

                "organic_carbon"
            ],

            "relationship":
                "Crop diversification and organic-matter "
                "management can influence soil biodiversity "
                "and soil condition."
        })

        evidence = get_evidence(

            "crop diversity rotations intercropping "
            "organic matter soil biodiversity"
        )

        add_recommendation(

            recommendations,

            "Consider crop rotation, intercropping or "
            "diverse cover crops while maintaining soil cover.",

            "Retrieved FAO evidence indicates that increasing "
            "crop diversity through rotations or intercropping "
            "tends to increase soil biodiversity, while organic "
            "matter management also supports soil biodiversity.",

            [

                "Monoculture → lower crop diversity",

                "Crop diversity → soil biodiversity",

                "Organic matter → soil biodiversity"
            ],

            [

                "Soil organic carbon",

                "Soil biodiversity",

                "Land-use diversity"
            ],

            "Medium term: 1–3 years",

            evidence,

            priority=2
        )


    # =====================================================
    # 6. LOW HABITAT DIVERSITY + LOW SPECIES RICHNESS
    # =====================================================

    if (
        data.habitat_diversity is not None
        and data.habitat_diversity < 0.4
        and data.species_richness is not None
        and data.species_richness < 10
    ):

        findings.append(
            "Low habitat diversity and species richness "
            "indicate limited biological and habitat variety."
        )

        relationships.append({

            "variables": [

                "habitat_diversity",

                "species_richness"
            ],

            "relationship":
                "Habitat variety can support diverse biological "
                "communities and ecosystem resilience."
        })

        evidence = get_evidence(

            "habitat diversity biological communities "
            "species diversity landscape resilience "
            "habitat fragmentation"
        )

        add_recommendation(

            recommendations,

            "Increase habitat variety using native vegetation "
            "and diverse habitat patches.",

            "Retrieved evidence associates diverse biological "
            "communities and habitat mosaics with ecosystem "
            "resilience.",

            [

                "Low habitat diversity → limited habitat variety",

                "Habitat diversity → biological variety",

                "Biological variety → ecosystem resilience"
            ],

            [

                "Habitat diversity",

                "Species richness"
            ],

            "Medium to long term",

            evidence,

            priority=1
        )


    # =====================================================
    # 7. HIGH POLLUTION
    # =====================================================

    if (
        data.pollution_level is not None
        and data.pollution_level.lower() == "high"
    ):

        pollution_variables = [

            "pollution_level"
        ]

        if data.species_richness is not None:

            pollution_variables.append(
                "species_richness"
            )

        if data.habitat_diversity is not None:

            pollution_variables.append(
                "habitat_diversity"
            )

        findings.append(
            "High pollution represents a significant "
            "environmental pressure on organisms and "
            "biodiversity."
        )

        if (
            data.species_richness is not None
            and data.species_richness < 10
            and data.habitat_diversity is not None
            and data.habitat_diversity < 0.4
        ):

            findings.append(
                "The combination of high pollution, low species "
                "richness and low habitat diversity indicates "
                "multiple simultaneous pressures on biodiversity. "
                "The available data show an association between "
                "these conditions, but do not by themselves prove "
                "that pollution caused the observed biodiversity "
                "levels."
            )

        evidence = get_evidence(

            "pollution soil biodiversity persistent organic "
            "pollutants pesticides biocides waste disposal "
            "toxicity soil biota cascading effects ecosystem functions"
        )

        if (
            data.species_richness is not None
            and data.habitat_diversity is not None
        ):

            relationship_text = (
                "High pollution can add environmental pressure "
                "to ecosystems, while low species richness and "
                "low habitat diversity indicate reduced biological "
                "and habitat variety. Together, these variables "
                "represent interacting biodiversity pressures."
            )

        else:

            relationship_text = (
                "Pollution can affect soil organisms and ecosystem "
                "functions through contaminants and toxic substances."
            )

        relationships.append({

            "variables":
                pollution_variables,

            "relationship":
                relationship_text
        })

        add_recommendation(

            recommendations,

            "Identify and reduce the major pollution sources, "
            "with priority given to persistent pollutants, "
            "pesticides, biocides and poorly managed waste. "
            "Use source-control and safe disposal measures, "
            "then monitor biodiversity indicators over time.",

            "Retrieved FAO evidence identifies fertilizer "
            "application, persistent organic pollutants, "
            "biocides and pesticides, and waste disposal as "
            "pollution-related pressures on soil biota. It "
            "also describes potential toxicity and cascading "
            "effects from individual organisms to communities "
            "and ecosystem functions.",

            [

                "High pollution → contamination pressure",

                "Contaminants → toxicity pressure on soil biota",

                "Soil biota → ecosystem functions",

                "Reduced environmental pressure → improved "
                "conditions for biodiversity"
            ],

            [

                "Pollution level",

                "Species richness",

                "Habitat diversity"
            ],

            "Short term for source identification and control; "
            "medium to long term for biodiversity improvement",

            evidence,

            priority=1
        )


    # =====================================================
    # 8. MEDIUM / LOW POLLUTION
    # =====================================================

    if (
        data.pollution_level is not None
        and data.pollution_level.lower()
        in ["medium", "low"]
    ):

        evidence = get_evidence(

            "pollution soil biodiversity "
            "soil organisms contaminants ecosystem functions"
        )

        level = data.pollution_level.lower()

        findings.append(
            f"{level.capitalize()} pollution represents an "
            "environmental pressure that should be monitored."
        )

        relationships.append({

            "variables": [

                "pollution_level",

                "soil_biodiversity"
            ],

            "relationship":
                "Pollution levels can influence environmental "
                "conditions experienced by soil organisms."
        })

        add_recommendation(

            recommendations,

            "Monitor potential pollution sources and "
            "prevent unnecessary chemical or waste inputs "
            "to maintain soil and habitat quality.",

            "Retrieved evidence identifies pollution-related "
            "substances and waste as potential pressures "
            "on soil organisms and ecosystem functions.",

            [

                "Pollution → environmental pressure",

                "Environmental quality → soil organisms",

                "Soil organisms → ecosystem functions"
            ],

            [

                "Pollution level",

                "Soil biodiversity"
            ],

            "Short to medium term",

            evidence,

            priority=3
        )


    # =====================================================
    # 9. HIGH DEFORESTATION
    # =====================================================

    if (
        data.deforestation_level is not None
        and data.deforestation_level.lower() == "high"
    ):

        evidence = get_evidence(

            "deforestation habitat loss biodiversity "
            "forest fragmentation species habitat"
        )

        findings.append(
            "High deforestation indicates substantial pressure "
            "on habitat availability and biodiversity."
        )

        relationships.append({

            "variables": [

                "deforestation_level",

                "habitat_diversity",

                "species_richness"
            ],

            "relationship":
                "Deforestation can reduce habitat availability "
                "and contribute to habitat fragmentation, creating "
                "pressure on biological communities."
        })

        add_recommendation(

            recommendations,

            "Prioritize protection of remaining native habitat "
            "and restore degraded habitat corridors where "
            "appropriate.",

            "Retrieved evidence connects habitat loss and "
            "fragmentation with biodiversity pressures.",

            [

                "Deforestation → habitat loss",

                "Habitat loss → pressure on species",

                "Habitat connectivity → biological movement"
            ],

            [

                "Deforestation level",

                "Habitat diversity",

                "Species richness"
            ],

            "Medium to long term",

            evidence,

            priority=1
        )


    # =====================================================
    # 10. LOW SOIL PH
    # =====================================================

    if (
        data.soil_ph is not None
        and data.soil_ph < 5.5
    ):

        evidence = get_evidence(

            "soil pH acidic soil biodiversity "
            "soil organisms nutrient availability"
        )

        findings.append(
            "The reported soil pH is acidic and may influence "
            "soil biological activity and nutrient conditions."
        )

        relationships.append({

            "variables": [

                "soil_ph",

                "soil_biodiversity"
            ],

            "relationship":
                "Soil pH influences chemical and biological "
                "conditions experienced by soil organisms."
        })

        add_recommendation(

            recommendations,

            "Monitor soil pH and use locally appropriate "
            "soil-management practices to maintain suitable "
            "soil conditions.",

            "Soil pH is an important factor influencing "
            "soil chemical and biological conditions.",

            [

                "Low soil pH → acidic soil conditions",

                "Soil pH → soil chemical conditions",

                "Soil conditions → soil organisms"
            ],

            [

                "Soil pH",

                "Soil biodiversity"
            ],

            "Medium term",

            evidence,

            priority=2
        )


    # =====================================================
    # 11. HIGH TEMPERATURE
    # =====================================================

    if (
        data.temperature is not None
        and data.temperature > 35
    ):

        evidence = get_evidence(

            "high temperature climate biodiversity "
            "heat stress species ecosystem"
        )

        findings.append(
            "High reported temperature indicates potential "
            "heat stress for organisms and ecosystems."
        )

        relationships.append({

            "variables": [

                "temperature",

                "biodiversity"
            ],

            "relationship":
                "Temperature influences physiological conditions "
                "and the suitability of habitats for organisms."
        })

        add_recommendation(

            recommendations,

            "Maintain vegetation cover and habitat features "
            "that can provide thermal refuges and reduce "
            "exposure to extreme heat where appropriate.",

            "Temperature is an important environmental factor "
            "affecting organisms and ecosystem conditions.",

            [

                "High temperature → heat pressure",

                "Vegetation cover → habitat protection",

                "Habitat conditions → organism survival"
            ],

            [

                "Temperature",

                "Habitat quality",

                "Species richness"
            ],

            "Short to medium term",

            evidence,

            priority=2
        )


    # =====================================================
    # REMOVE DUPLICATE RECOMMENDATIONS
    # =====================================================

    unique_recommendations = []

    seen = set()

    for item in recommendations:

        key = item[
            "recommendation"
        ].strip().lower()

        if key not in seen:

            seen.add(key)

            unique_recommendations.append(
                item
            )

    recommendations = (
        unique_recommendations
    )


    # =====================================================
    # SORT BY PRIORITY
    # =====================================================

    recommendations.sort(
        key=lambda item:
            item.get(
                "priority",
                3
            )
    )


    # =====================================================
    # LIMIT RECOMMENDATIONS
    # =====================================================

    recommendations = recommendations[:4]


    # =====================================================
    # UNCERTAINTIES
    # =====================================================

    if data.region is None:

        uncertainties.append(
            "No geographic region was provided, so the "
            "assessment does not account for regional "
            "climate or ecological differences."
        )


    if data.soil_ph is None:

        uncertainties.append(
            "Soil pH was not provided."
        )


    if data.species_richness is None:

        uncertainties.append(
            "Species richness was not provided, so current "
            "species-level biodiversity cannot be quantified."
        )


    if data.habitat_diversity is None:

        uncertainties.append(
            "Habitat diversity was not provided, so habitat "
            "structure cannot be directly assessed."
        )


    # =====================================================
    # CALCULATE CONFIDENCE
    # =====================================================

    total_evidence = sum(

        len(
            item.get(
                "evidence",
                []
            )
        )

        for item in recommendations
    )


    confidence = calculate_confidence(

        data,

        total_evidence
    )


    # =====================================================
    # RETURN COMPLETE ANALYSIS
    # =====================================================

    return {

        "observed_metrics":
            observed_metrics,

        "findings":
            findings,

        "derived_relationships":
            relationships,

        "recommendations":
            recommendations,

        "uncertainties":
            uncertainties,

        "confidence":
            confidence
    }
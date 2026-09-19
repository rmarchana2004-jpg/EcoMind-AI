from backend.services.rag import search_knowledge

queries = [
    "How can cover crops and intercropping improve soil health and biodiversity?",
    "How does organic matter improve soil moisture and water retention?",
    "How does habitat diversity support species richness and biodiversity?",
    "How does monoculture affect biodiversity?",
    "How does soil biodiversity contribute to healthy soils?"
]

for query in queries:
    print("\n" + "=" * 80)
    print("QUERY:", query)
    print("=" * 80)

    results = search_knowledge(query, top_k=3)

    for i, result in enumerate(results, start=1):
        print(f"\nResult {i}")
        print("Source:", result["filename"])
        print("Page:", result["page"])
        print("Distance:", result["distance"])
        print("Text:", result["text"])
        print("-" * 80)
import re


def extract_environment_from_text(message: str, context_field=None):
    data = {}
    text = message.lower().strip()

    # -------------------------------------------------
    # Contextual follow-up answers
    # Example:
    # Bot: "Could you provide annual rainfall (mm)?"
    # User: "500 mm"
    # -------------------------------------------------

    if context_field:

        number_match = re.search(
            r"(-?\d+(?:\.\d+)?)",
            text
        )

        if number_match:
            value = float(number_match.group(1))

            if context_field == "rainfall":
                data["rainfall"] = value

            elif context_field == "soil_moisture":
                data["soil_moisture"] = value

            elif context_field == "organic_carbon":
                data["organic_carbon"] = value

            elif context_field == "temperature":
                data["temperature"] = value

            elif context_field == "soil_ph":
                data["soil_ph"] = value

            elif context_field == "species_richness":
                data["species_richness"] = int(value)

            elif context_field == "habitat_diversity":
                data["habitat_diversity"] = value

            if data:
                return data

    # -------------------------------------------------
    # Soil moisture
    # -------------------------------------------------

    match = re.search(
        r"soil moisture(?: is| of| around| approximately)?\s*"
        r"(\d+(?:\.\d+)?)\s*%?",
        text
    )

    if match:
        data["soil_moisture"] = float(match.group(1))

    # -------------------------------------------------
    # Soil pH
    # -------------------------------------------------

    match = re.search(
        r"(?:soil\s*)?ph(?: is| of| around| approximately)?\s*"
        r"(\d+(?:\.\d+)?)",
        text
    )

    if match:
        data["soil_ph"] = float(match.group(1))

    # -------------------------------------------------
    # Organic carbon
    # -------------------------------------------------

    match = re.search(
        r"(?:organic carbon|soil organic carbon)"
        r"(?: is| of| around| approximately)?\s*"
        r"(\d+(?:\.\d+)?)\s*%?",
        text
    )

    if match:
        data["organic_carbon"] = float(match.group(1))

    # -------------------------------------------------
    # Rainfall
    # -------------------------------------------------

    match = re.search(
        r"rainfall(?: is| of| around| approximately)?\s*"
        r"(\d+(?:\.\d+)?)\s*(?:mm)?",
        text
    )

    if match:
        data["rainfall"] = float(match.group(1))

    # -------------------------------------------------
    # Temperature
    # -------------------------------------------------

    match = re.search(
        r"temperature(?: is| of| around| approximately)?\s*"
        r"(-?\d+(?:\.\d+)?)\s*(?:°c|c)?",
        text
    )

    if match:
        data["temperature"] = float(match.group(1))

    # -------------------------------------------------
    # Species richness
    # -------------------------------------------------

    match = re.search(
        r"species richness(?: is| of| around| approximately)?\s*"
        r"(\d+)",
        text
    )

    if match:
        data["species_richness"] = int(match.group(1))

    # -------------------------------------------------
    # Habitat diversity
    # -------------------------------------------------

    match = re.search(
        r"habitat diversity(?: is| of| around| approximately)?\s*"
        r"(\d+(?:\.\d+)?)",
        text
    )

    if match:
        data["habitat_diversity"] = float(match.group(1))

    # -------------------------------------------------
    # Land use
    # -------------------------------------------------

    if "monoculture" in text:
        data["land_use"] = "monoculture"

    elif "mixed cropping" in text:
        data["land_use"] = "mixed cropping"

    elif "intercropping" in text:
        data["land_use"] = "intercropping"

    elif "agroforestry" in text:
        data["land_use"] = "agroforestry"

    # -------------------------------------------------
    # Pollution
    # -------------------------------------------------

    if "high pollution" in text:
        data["pollution_level"] = "high"

    elif "medium pollution" in text:
        data["pollution_level"] = "medium"

    elif "low pollution" in text:
        data["pollution_level"] = "low"

    # -------------------------------------------------
    # Deforestation
    # -------------------------------------------------

    if "high deforestation" in text:
        data["deforestation_level"] = "high"

    elif "medium deforestation" in text:
        data["deforestation_level"] = "medium"

    elif "low deforestation" in text:
        data["deforestation_level"] = "low"

    # -------------------------------------------------
    # Region
    # -------------------------------------------------

    regions = [
        "karnataka",
        "kerala",
        "tamil nadu",
        "andhra pradesh",
        "telangana",
        "maharashtra",
        "india"
    ]

    for region in regions:
        if region in text:
            data["region"] = region.title()
            break

    return data
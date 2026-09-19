from fastapi import FastAPI
import re
from fastapi.middleware.cors import CORSMiddleware

from backend.models import EnvironmentalData, ChatRequest

from backend.services.reasoning import (
    analyze_environment,
    answer_knowledge_question
)

from backend.services.parser import (
    extract_environment_from_text
)

from backend.services.memory import (
    get_conversation,
    update_conversation,
    clear_conversation,
    set_pending_field,
    get_pending_field,
    clear_pending_field
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="EcoMind AI",
    description="AI-powered Biodiversity Intelligence System",
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Welcome to EcoMind AI",
        "status": "running"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# =========================================================
# ENVIRONMENT DATA
# =========================================================

@app.post("/environment")
def receive_environmental_data(
    data: EnvironmentalData
):

    return {
        "message":
            "Environmental data received successfully",

        "data":
            data.model_dump()
    }


# =========================================================
# DIRECT ENVIRONMENT ANALYSIS
# =========================================================

@app.post("/analyze")
def analyze(
    data: EnvironmentalData
):

    analysis = analyze_environment(data)

    return {
        "environment":
            data.model_dump(),

        "analysis":
            analysis
    }


# =========================================================
# DETECT KNOWLEDGE QUESTIONS
# =========================================================

def is_knowledge_question(message: str):

    text = message.lower().strip()

    knowledge_patterns = [

        "why ",

        "how does ",

        "how do ",

        "what is ",

        "what are ",

        "explain ",

        "why does ",

        "why do ",

        "how can ",

        "what happens ",

        "what factors ",
        "factors affecting ",
        "factors that affect ",
        "factors that influence ",

        "impact of ",

        "effect of ",

        "effects of ",

        "relationship between ",

        "importance of ",

        "role of "
    ]

    return any(
        text.startswith(pattern)
        for pattern in knowledge_patterns
    )



# =========================================================
# DETECT CONTEXTUAL ENVIRONMENT QUESTIONS
# =========================================================

def is_contextual_environment_question(message: str):
    text = message.lower().strip()

    contextual_phrases = [
        "these conditions",
        "these values",
        "these measurements",
        "these parameters",
        "this condition",
        "this soil",
        "current conditions",
        "given conditions",
        "given values",
        "how does this affect",
        "how do these affect",
        "how do these conditions affect",
        "what is the impact of these",
        "what effect do these have"
    ]

    return any(
        phrase in text
        for phrase in contextual_phrases
    )


def detect_metric_question(message: str):
    text = message.lower().strip()

    metric_patterns = [
        (["soil moisture", "moisture of soil"], "soil_moisture",
         "soil moisture (%)"),
        (["organic carbon", "soil organic carbon"], "organic_carbon",
         "soil organic carbon (%)"),
        (["soil ph", "soil pH"], "soil_ph",
         "soil pH"),
        (["rainfall", "annual rainfall"], "rainfall",
         "annual rainfall (mm)"),
        (["temperature"], "temperature",
         "temperature (°C)"),
        (["land use", "land-use"], "land_use",
         "land-use type"),
        (["habitat diversity"], "habitat_diversity",
         "habitat diversity"),
        (["species richness"], "species_richness",
         "species richness"),
        (["pollution level", "pollution"], "pollution_level",
         "pollution level"),
        (["deforestation level", "deforestation"], "deforestation_level",
         "deforestation level"),
        (["region", "location"], "region",
         "region")
    ]

    question_starters = (
        "what is",
        "what are",
        "tell me",
        "give me",
        "provide",
        "what's"
    )

    if not text.startswith(question_starters):
        return None

    for terms, field, display_name in metric_patterns:
        if any(term in text for term in terms):
            return {
                "field": field,
                "display_name": display_name
            }

    return None


def is_follow_up_value(message: str):
    text = message.lower().strip()

    # A short numeric reply such as "15%" or "500 mm"
    # should be handled by the pending-field memory flow.
    return bool(
        re.fullmatch(
            r"-?\d+(?:\.\d+)?\s*(?:%|mm|°?c)?",
            text
        )
    )

# =========================================================
# CHAT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):

    session_id = request.session_id

    # =====================================================
    # 1. GET PREVIOUS CONVERSATION DATA
    # =====================================================

    previous_data = get_conversation(
        session_id
    )


    # =====================================================
    # 2. GET PENDING FIELD
    # =====================================================

    pending_field = get_pending_field(
        session_id
    )

    # =====================================================
    # GENERAL KNOWLEDGE ROUTING
    # =====================================================
    # Handle general scientific questions before metric parsing.
    # This prevents a stale pending field from incorrectly sending
    # a knowledge question into the environmental-data flow.
    early_contextual_question = is_contextual_environment_question(
        request.message
    )

    early_knowledge_question = is_knowledge_question(
        request.message
    )

    early_context_terms = [
        "my ",
        "these conditions",
        "these values",
        "these measurements",
        "these parameters",
        "this condition",
        "this soil",
        "current conditions",
        "given conditions",
        "given values",
        "my environment",
        "my land"
    ]

    early_has_context_reference = (
        early_contextual_question
        or any(
            term in request.message.lower()
            for term in early_context_terms
        )
    )

    if (
        early_knowledge_question
        and not early_has_context_reference
    ):
        knowledge_result = answer_knowledge_question(
            request.message
        )

        return {
            "session_id": session_id,
            "message": request.message,
            "status": "knowledge_answer",
            "response": knowledge_result["answer"],
            "scientific_evidence": knowledge_result["evidence"]
        }

    # Detect direct questions about environmental metrics such as
    # "What is the soil moisture?" before generic RAG routing.
    metric_question = detect_metric_question(
        request.message
    )

    if metric_question and not pending_field:
        set_pending_field(
            session_id,
            metric_question["field"]
        )

        return {
            "session_id": session_id,
            "message": request.message,
            "status": "needs_more_information",
            "response": (
                f"Could you provide the value for "
                f"{metric_question['display_name']}?"
            ),
            "clarifying_questions": [
                f"Could you provide {metric_question['display_name']}?"
            ],
            "missing_information": [
                metric_question["display_name"]
            ]
        }


    # =====================================================
    # 3. EXTRACT ENVIRONMENTAL DATA
    # =====================================================

    detected_data = extract_environment_from_text(
        request.message,
        pending_field
    )

    # If EcoMind asked specifically for soil moisture and the user
    # replies with a bare value such as "15%", preserve that value.
    if pending_field == "soil_moisture" and not detected_data:
        value_match = re.search(
            r"(-?\d+(?:\.\d+)?)",
            request.message
        )

        if value_match:
            detected_data["soil_moisture"] = float(
                value_match.group(1)
            )


    # =====================================================
    # 4. GENERAL KNOWLEDGE QUESTION
    # =====================================================
    # Knowledge questions are handled only when they are NOT
    # contextual follow-ups and NOT replies to a pending field.

    contextual_question = is_contextual_environment_question(
        request.message
    )

    value_follow_up = is_follow_up_value(
        request.message
    )

    # =====================================================
    # GENERAL KNOWLEDGE VS CONTEXTUAL ENVIRONMENT QUESTIONS
    # =====================================================
    # General questions such as "What factors affect biodiversity?"
    # should use the scientific RAG knowledge base.
    #
    # Questions that explicitly refer to the user's stored
    # measurements/conditions should continue to environmental
    # reasoning instead.
    general_knowledge_question = is_knowledge_question(
        request.message
    )

    context_reference_terms = [
        "my ",
        "these conditions",
        "these values",
        "these measurements",
        "these parameters",
        "this condition",
        "this soil",
        "current conditions",
        "given conditions",
        "given values",
        "my soil",
        "my land",
        "my environment",
        "these environmental"
    ]

    explicitly_refers_to_context = (
        contextual_question
        or any(
            term in request.message.lower()
            for term in context_reference_terms
        )
    )

    if (
        general_knowledge_question
        and not explicitly_refers_to_context
        and not pending_field
        and not value_follow_up
    ):

        knowledge_result = answer_knowledge_question(
            request.message
        )

        return {

            "session_id":
                session_id,

            "message":
                request.message,

            "status":
                "knowledge_answer",

            "response":
                knowledge_result["answer"],

            "scientific_evidence":
                knowledge_result["evidence"]
        }


    # =====================================================
    # 5. STRUCTURED ENVIRONMENT DATA
    # =====================================================

    if request.environment is not None:

        structured_data = (
            request.environment.model_dump(
                exclude_none=True
            )
        )

        detected_data.update(
            structured_data
        )


    # =====================================================
    # 6. COMBINE PREVIOUS + NEW DATA
    # =====================================================

    # Support both the older flat memory format and the newer
    # {"environment": {...}, "pending_field": ...} format.
    if isinstance(previous_data.get("environment"), dict):
        combined_data = previous_data.get("environment", {}).copy()
    else:
        combined_data = previous_data.copy()

    # Remove internal memory fields if an older flat format is used.
    combined_data.pop(
        "pending_field",
        None
    )

    combined_data.update(
        detected_data
    )


    # =====================================================
    # 7. SAVE NEW ENVIRONMENT DATA
    # =====================================================

    if detected_data:

        update_conversation(
            session_id,
            detected_data
        )


    # =====================================================
    # 8. CLEAR PENDING FIELD
    # =====================================================

    if detected_data and pending_field:

        clear_pending_field(
            session_id
        )


    # =====================================================
    # 9. CREATE ENVIRONMENT OBJECT
    # =====================================================

    environment = EnvironmentalData(
        **combined_data
    )


    # =====================================================
    # 10. FIND MISSING INFORMATION
    # =====================================================

    missing_information = []


    # -----------------------------------------------------
    # Soil moisture related information
    # -----------------------------------------------------

    if environment.soil_moisture is not None:

        if environment.organic_carbon is None:

            missing_information.append(
                "soil organic carbon (%)"
            )


        if environment.rainfall is None:

            missing_information.append(
                "annual rainfall (mm)"
            )


        if environment.land_use is None:

            missing_information.append(
                "land-use type"
            )


    # -----------------------------------------------------
    # Biodiversity related information
    # -----------------------------------------------------

    if (
        environment.habitat_diversity is not None
        or
        environment.species_richness is not None
    ):

        if environment.habitat_diversity is None:

            missing_information.append(
                "habitat diversity"
            )


        if environment.species_richness is None:

            missing_information.append(
                "species richness"
            )


    # Remove duplicates

    missing_information = list(
        dict.fromkeys(
            missing_information
        )
    )

    # =====================================================
    # 10B. DETERMINE WHETHER ENOUGH DATA EXISTS FOR A
    #      PRELIMINARY MULTI-METRIC ASSESSMENT
    # =====================================================
    # Two or more environmental metrics are enough for a
    # preliminary assessment. Optional metrics such as rainfall
    # should improve the assessment, not block it.
    #
    # Example:
    #   organic_carbon + soil_moisture + land_use
    # should be analyzed immediately instead of asking for rainfall.

    environmental_fields = [
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

    available_metric_count = sum(
        1
        for field in environmental_fields
        if getattr(environment, field, None) is not None
    )

    enough_for_preliminary_analysis = (
        available_metric_count >= 2
    )

    # =====================================================
    # 11. ASK CLARIFYING QUESTIONS
    # =====================================================
    # Ask for more information only when there is not enough
    # environmental data for a useful preliminary assessment.
    # Contextual questions can always proceed with stored data.

    if (
        missing_information
        and not contextual_question
        and not enough_for_preliminary_analysis
    ):

        questions = []


        for item in missing_information[:3]:

            questions.append(
                f"Could you provide {item}?"
            )


        # -------------------------------------------------
        # Map question to environmental field
        # -------------------------------------------------

        field_mapping = {

            "soil organic carbon (%)":
                "organic_carbon",

            "soil moisture (%)":
                "soil_moisture",

            "annual rainfall (mm)":
                "rainfall",

            "land-use type":
                "land_use",

            "habitat diversity":
                "habitat_diversity",

            "species richness":
                "species_richness"
        }


        # -------------------------------------------------
        # Store first missing field
        # -------------------------------------------------

        first_missing = (
            missing_information[0]
        )


        pending_field = field_mapping.get(
            first_missing
        )


        if pending_field:

            set_pending_field(
                session_id,
                pending_field
            )


        return {

            "session_id":
                session_id,

            "message":
                request.message,

            "detected_environment":
                environment.model_dump(),

            "status":
                "needs_more_information",

            "response": (
                "I detected some environmental "
                "conditions, but I need a little "
                "more information to perform a "
                "stronger multi-metric assessment."
            ),

            "clarifying_questions":
                questions,

            "missing_information":
                missing_information
        }


    # =====================================================
    # 12. ENVIRONMENTAL ANALYSIS
    # =====================================================
    # Contextual follow-ups such as "How do these conditions affect
    # biodiversity?" are analyzed using the environmental values
    # already stored in this session, even when optional metrics
    # such as rainfall or land use are still missing.

    if combined_data:

        analysis = analyze_environment(
            environment
        )


        return {

            "session_id":
                session_id,

            "message":
                request.message,

            "detected_environment":
                environment.model_dump(),

            "status":
                "analysis_complete",

            "available_metric_count":
                available_metric_count,

            "response": (
                "I combined the environmental "
                "information from this conversation "
                "and analyzed the conditions using "
                "the environmental reasoning and "
                "scientific evidence system."
            ),

            "analysis":
                analysis
        }


    # =====================================================
    # 13. NO ENVIRONMENTAL DATA
    # =====================================================

    if contextual_question:
        return {
            "session_id": session_id,
            "message": request.message,
            "status": "needs_environmental_data",
            "response": (
                "I don't have environmental conditions stored "
                "for this conversation yet. Please provide at "
                "least two values such as soil moisture, organic "
                "carbon, soil pH, rainfall, temperature or land use."
            ),
            "required_information": [
                "Soil moisture (%)",
                "Soil organic carbon (%)",
                "Soil pH",
                "Land use"
            ]
        }

    return {

        "session_id":
            session_id,

        "message":
            request.message,

        "status":
            "needs_environmental_data",

        "response": (
            "I need some environmental information "
            "before I can provide a grounded "
            "recommendation."
        ),

        "required_information": [

            "Soil moisture (%)",

            "Soil organic carbon (%)",

            "Soil pH",

            "Rainfall (mm)",

            "Temperature (°C)",

            "Land use",

            "Habitat diversity",

            "Species richness",

            "Pollution level",

            "Deforestation level",

            "Region"
        ]
    }


# =========================================================
# CLEAR CHAT MEMORY
# =========================================================

@app.delete("/chat/{session_id}")
def clear_chat(
    session_id: str
):

    clear_conversation(
        session_id
    )


    return {

        "message":
            "Conversation memory cleared",

        "session_id":
            session_id
    }
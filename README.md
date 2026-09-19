# 🌿 EcoMind AI

### AI-Powered Biodiversity & Environmental Intelligence System

EcoMind AI is an AI-powered environmental intelligence platform designed to analyze biodiversity and environmental conditions using scientific knowledge, semantic retrieval, multi-metric reasoning, and conversational memory.

The system combines structured environmental data with scientific documents to provide evidence-grounded biodiversity assessments and actionable recommendations.

---

## 🎯 Problem Statement

Environmental conditions are interconnected. Changes in soil, climate, land use, and human activities can influence biodiversity and ecosystem health.

Traditional chatbot systems may provide generic environmental advice without considering multiple environmental variables or scientific evidence.

EcoMind AI addresses this problem by combining:

- Scientific knowledge retrieval
- Environmental metric extraction
- Multi-metric reasoning
- Conversational context
- Evidence-backed recommendations
- Uncertainty and missing-data reporting

The goal is to provide an AI environmental scientist rather than a generic chatbot.

---

## 🚀 Key Features

### 1. Scientific Knowledge Retrieval

EcoMind AI uses a Retrieval-Augmented Generation (RAG) approach to retrieve relevant information from scientific biodiversity and environmental documents.

The current knowledge base includes:

- FAO Biodiversity and Agriculture
- FAO Soil Biodiversity
- IPCC Climate and Land

---

### 2. Environmental Data Understanding

The system can extract and reason about:

#### Soil
- Soil pH
- Organic carbon
- Soil moisture

#### Climate
- Temperature
- Rainfall

#### Land
- Land use

#### Biodiversity
- Species richness
- Habitat diversity

#### Human Impact
- Pollution
- Deforestation

#### Location
- Region

---

### 3. Multi-Metric Reasoning

A key feature of EcoMind AI is reasoning across multiple environmental variables.

For example:

```text
Organic Carbon = 0.6%
Soil Moisture = 15%
Land Use = Monoculture
## 🗄️ Data Schema

EcoMind AI uses structured environmental data to represent the conditions provided by the user.

### Environmental Data

| Field | Type | Description |
|---|---|---|
| `soil_ph` | float | Soil pH value |
| `organic_carbon` | float | Soil organic carbon percentage |
| `soil_moisture` | float | Soil moisture percentage |
| `temperature` | float | Environmental temperature |
| `rainfall` | float | Rainfall amount |
| `land_use` | string | Land-use type such as monoculture, intercropping or agroforestry |
| `species_richness` | integer | Number/measure of species richness |
| `habitat_diversity` | float | Habitat diversity measure |
| `pollution_level` | string | Pollution level |
| `deforestation_level` | string | Deforestation level |
| `region` | string | Geographic region |

### Conversation Memory

For each conversation session, EcoMind AI maintains:

- Session ID
- Environmental metrics provided by the user
- Pending clarification field
- Previous environmental context

### Knowledge Base Metadata

Each retrieved scientific chunk contains:

- `text`
- `page`
- `filename`
- Vector embedding used for semantic retrieval
## 🔄 CI/CD

The current version of EcoMind AI is maintained through GitHub and is configured for local development and manual deployment.

- Source code is maintained in the GitHub repository.
- The `main` branch contains the submitted version.
- Python dependencies are defined in `backend/requirements.txt`.
- The FastAPI backend is run using Uvicorn.
- The frontend is served as HTML/CSS/JavaScript.
- The current submission does not use an automated CI/CD deployment pipeline.
- Future versions can add GitHub Actions for automated testing, validation and deployment.
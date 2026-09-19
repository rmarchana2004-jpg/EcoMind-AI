const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const newChatButton = document.getElementById("newChatButton");

const sessionId = "demo-session";


// ==================================================
// EVENT LISTENERS
// ==================================================

sendButton.addEventListener("click", sendMessage);

newChatButton.addEventListener(
    "click",
    startNewChat
);

messageInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter" && !event.shiftKey) {

        event.preventDefault();

        sendMessage();
    }
});


// ==================================================
// SEND MESSAGE
// ==================================================

async function sendMessage() {

    const message = messageInput.value.trim();

    if (message === "") {
        return;
    }

    addMessage(
        "You",
        message,
        "user"
    );

    messageInput.value = "";

    sendButton.disabled = true;
    sendButton.textContent = "Analyzing...";


    try {

        const response = await fetch(
            "http://127.0.0.1:8000/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message,
                    session_id: sessionId
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail || "Server error"
            );
        }


        displayResponse(data);


    } catch (error) {

        console.error(error);

        addMessage(
            "EcoMind AI",
            `
            <div class="error-message">

                ❌ Unable to connect to the EcoMind AI backend.

                <br><br>

                Please make sure FastAPI is running.

            </div>
            `,
            "bot"
        );

    } finally {

        sendButton.disabled = false;

        sendButton.textContent = "Send";
    }
}


// ==================================================
// DISPLAY RESPONSE
// ==================================================

function displayResponse(data) {

    let html = "";


    // ==================================================
    // MAIN RESPONSE
    // ==================================================

    html += `
        <div class="ai-response">
            ${formatText(data.response || "")}
        </div>
    `;


    // ==================================================
    // KNOWLEDGE QUESTION
    // ==================================================

    if (data.status === "knowledge_answer") {

        html += createKnowledgeEvidenceSection(
            data.scientific_evidence
        );

        addMessage(
            "EcoMind AI",
            html,
            "bot"
        );

        return;
    }


    // ==================================================
    // ENVIRONMENTAL DATA
    // ==================================================

    if (data.detected_environment) {

        const environment =
            data.detected_environment;

        html += `

            <div class="section">

                <h3>🌍 Environmental Conditions</h3>

                <div class="metrics-grid">

                    ${createMetric(
                        "Soil Moisture",
                        environment.soil_moisture,
                        "%"
                    )}

                    ${createMetric(
                        "Organic Carbon",
                        environment.organic_carbon,
                        "%"
                    )}

                    ${createMetric(
                        "Rainfall",
                        environment.rainfall,
                        " mm"
                    )}

                    ${createMetric(
                        "Temperature",
                        environment.temperature,
                        " °C"
                    )}

                    ${createMetric(
                        "Soil pH",
                        environment.soil_ph,
                        ""
                    )}

                    ${createMetric(
                        "Species Richness",
                        environment.species_richness,
                        ""
                    )}

                    ${createMetric(
                        "Habitat Diversity",
                        environment.habitat_diversity,
                        ""
                    )}

                    ${createMetric(
                        "Land Use",
                        environment.land_use,
                        ""
                    )}

                    ${createMetric(
                        "Pollution",
                        environment.pollution_level,
                        ""
                    )}

                    ${createMetric(
                        "Deforestation",
                        environment.deforestation_level,
                        ""
                    )}

                    ${createMetric(
                        "Region",
                        environment.region,
                        ""
                    )}

                </div>

            </div>
        `;
    }


    // ==================================================
    // CLARIFYING QUESTIONS
    // ==================================================

    if (
        data.status === "needs_more_information" &&
        data.clarifying_questions
    ) {

        html += `

            <div class="section clarification">

                <h3>❓ More Information Needed</h3>

                <ul>
        `;


        data.clarifying_questions.forEach(
            question => {

                html += `
                    <li>
                        ${formatText(question)}
                    </li>
                `;
            }
        );


        html += `

                </ul>

            </div>
        `;
    }


    // ==================================================
    // COMPLETE ANALYSIS
    // ==================================================

    if (
        data.status === "analysis_complete" &&
        data.analysis
    ) {

        const analysis = data.analysis;


        // ==================================================
        // CONFIDENCE
        // ==================================================

        if (analysis.confidence) {

            html += `

                <div class="section confidence-section">

                    <h3>📊 Assessment Confidence</h3>

                    <div class="confidence-card">

                        <div class="confidence-value">
                            ${formatText(
                                analysis.confidence
                            )}
                        </div>

                        <p>
                            Confidence reflects the amount of
                            environmental data and supporting
                            scientific evidence available for
                            this assessment.
                        </p>

                    </div>

                </div>
            `;
        }


        // ==================================================
        // FINDINGS
        // ==================================================

        if (
            analysis.findings &&
            analysis.findings.length > 0
        ) {

            html += `

                <div class="section">

                    <h3>🔎 Environmental Findings</h3>

                    <ul class="findings-list">
            `;


            analysis.findings.forEach(
                finding => {

                    html += `
                        <li>
                            ${formatText(finding)}
                        </li>
                    `;
                }
            );


            html += `

                    </ul>

                </div>
            `;
        }


        // ==================================================
        // MULTI-METRIC RELATIONSHIPS
        // ==================================================

        if (
            analysis.derived_relationships &&
            analysis.derived_relationships.length > 0
        ) {

            html += `

                <div class="section">

                    <h3>🔗 Multi-Metric Relationships</h3>
            `;


            analysis.derived_relationships.forEach(
                relationship => {

                    html += `

                        <div class="relationship-card">

                            <strong>
                                ${formatArray(
                                    relationship.variables
                                )}
                            </strong>

                            <p>
                                ${formatText(
                                    relationship.relationship
                                )}
                            </p>

                        </div>
                    `;
                }
            );


            html += `

                </div>
            `;
        }


        // ==================================================
        // RECOMMENDATIONS
        // ==================================================

        if (
            analysis.recommendations &&
            analysis.recommendations.length > 0
        ) {

            html += `

                <div class="section">

                    <h3>🌱 Recommended Actions</h3>
            `;


            analysis.recommendations.forEach(
                (recommendation, index) => {

                    html += `

                        <div class="recommendation-card">

                            <div class="recommendation-number">
                                ${index + 1}
                            </div>

                            <div class="recommendation-content">

                                <h4>
                                    ${formatText(
                                        recommendation.recommendation
                                    )}
                                </h4>

                                <p>
                                    <strong>
                                        Why it works:
                                    </strong>

                                    ${formatText(
                                        recommendation.reason
                                    )}
                                </p>

                                <p>
                                    <strong>
                                        Impacted metrics:
                                    </strong>

                                    ${formatArray(
                                        recommendation.metrics
                                    )}
                                </p>

                                <p>
                                    <strong>
                                        Time horizon:
                                    </strong>

                                    ${formatText(
                                        recommendation.time_horizon
                                    )}
                                </p>

                                ${createRecommendationEvidence(
                                    recommendation
                                )}

                            </div>

                        </div>
                    `;
                }
            );


            html += `

                </div>
            `;
        }


        // ==================================================
        // SCIENTIFIC EVIDENCE
        // ==================================================

        html += createEvidenceSection(
            analysis.recommendations
        );


        // ==================================================
        // UNCERTAINTIES
        // ==================================================

        if (
            analysis.uncertainties &&
            analysis.uncertainties.length > 0
        ) {

            html += `

                <div class="section uncertainty">

                    <h3>
                        ⚠️ Uncertainties & Missing Data
                    </h3>

                    <ul>
            `;


            analysis.uncertainties.forEach(
                uncertainty => {

                    html += `
                        <li>
                            ${formatText(uncertainty)}
                        </li>
                    `;
                }
            );


            html += `

                    </ul>

                </div>
            `;
        }
    }


    // ==================================================
    // ADD BOT MESSAGE
    // ==================================================

    addMessage(
        "EcoMind AI",
        html,
        "bot"
    );
}


// ==================================================
// CREATE METRIC CARD
// ==================================================

function createMetric(
    name,
    value,
    unit
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "";
    }


    return `

        <div class="metric-card">

            <span class="metric-name">
                ${formatText(name)}
            </span>

            <strong class="metric-value">
                ${formatText(String(value))}${unit}
            </strong>

        </div>
    `;
}


// ==================================================
// FORMAT ARRAY
// ==================================================

function formatArray(items) {

    if (
        !items ||
        items.length === 0
    ) {

        return "Not specified";
    }


    return items
        .map(item => formatText(String(item)))
        .join(", ");
}


// ==================================================
// RECOMMENDATION EVIDENCE
// ==================================================

function createRecommendationEvidence(
    recommendation
) {

    if (
        !recommendation.evidence ||
        recommendation.evidence.length === 0
    ) {

        return "";
    }


    let html = `

        <div class="recommendation-evidence">

            <strong>
                📚 Supporting Evidence
            </strong>
    `;


    recommendation.evidence.forEach(
        evidence => {

            html += `

                <div class="recommendation-evidence-item">

                    <div class="evidence-source">

                        📄 ${formatText(
                            evidence.source ||
                            evidence.filename ||
                            "Scientific source"
                        )}

                        <span>
                            Page ${
                                evidence.page ||
                                "N/A"
                            }
                        </span>

                    </div>

                    <p>
                        ${formatText(
                            evidence.text || ""
                        )}
                    </p>

                </div>
            `;
        }
    );


    html += `

        </div>
    `;


    return html;
}


// ==================================================
// SCIENTIFIC EVIDENCE SECTION
// ==================================================

function createEvidenceSection(
    recommendations
) {

    if (
        !recommendations ||
        recommendations.length === 0
    ) {

        return "";
    }


    let evidenceItems = [];


    recommendations.forEach(
        recommendation => {

            if (recommendation.evidence) {

                recommendation.evidence.forEach(
                    evidence => {

                        evidenceItems.push(
                            evidence
                        );

                    }
                );
            }
        }
    );


    if (evidenceItems.length === 0) {
        return "";
    }


    // ==================================================
    // REMOVE DUPLICATE SOURCE + PAGE
    // ==================================================

    const uniqueEvidence = [];

    const seen = new Set();


    evidenceItems.forEach(
        evidence => {

            const source =
                evidence.source ||
                evidence.filename ||
                "Unknown source";

            const page =
                evidence.page ||
                "N/A";

            const key =
                `${source}-${page}`;


            if (!seen.has(key)) {

                seen.add(key);

                uniqueEvidence.push(
                    evidence
                );
            }
        }
    );


    // ==================================================
    // BUILD SECTION
    // ==================================================

    let html = `

        <div class="section evidence-section">

            <h3>
                📚 Scientific Evidence
            </h3>

            <p class="evidence-intro">
                Recommendations are grounded in the
                retrieved scientific knowledge base.
            </p>
    `;


    uniqueEvidence.forEach(
        evidence => {

            html += `

                <div class="evidence-card">

                    <div class="evidence-source">

                        📄 ${formatText(
                            evidence.source ||
                            evidence.filename ||
                            "Scientific source"
                        )}

                        <span>
                            Page ${
                                evidence.page ||
                                "N/A"
                            }
                        </span>

                    </div>

                    <p>
                        ${formatText(
                            evidence.text || ""
                        )}
                    </p>

                </div>
            `;
        }
    );


    html += `

        </div>
    `;


    return html;
}


// ==================================================
// KNOWLEDGE QUESTION EVIDENCE
// ==================================================

function createKnowledgeEvidenceSection(
    evidenceItems
) {

    if (
        !evidenceItems ||
        evidenceItems.length === 0
    ) {

        return `
            <div class="section evidence-section">

                <h3>
                    📚 Scientific Evidence
                </h3>

                <p class="evidence-intro">
                    No supporting evidence was returned
                    from the scientific knowledge base.
                </p>

            </div>
        `;
    }


    // ==================================================
    // REMOVE DUPLICATES
    // ==================================================

    const uniqueEvidence = [];

    const seen = new Set();


    evidenceItems.forEach(
        evidence => {

            const source =
                evidence.filename ||
                evidence.source ||
                "Unknown source";

            const page =
                evidence.page ||
                "N/A";

            const key =
                `${source}-${page}`;


            if (!seen.has(key)) {

                seen.add(key);

                uniqueEvidence.push(
                    evidence
                );
            }
        }
    );


    // ==================================================
    // BUILD KNOWLEDGE EVIDENCE SECTION
    // ==================================================

    let html = `

        <div class="section evidence-section">

            <h3>
                📚 Scientific Evidence
            </h3>

            <p class="evidence-intro">
                This answer was generated using evidence
                retrieved from the EcoMind AI scientific
                knowledge base.
            </p>
    `;


    uniqueEvidence.forEach(
        (evidence, index) => {

            const source =
                evidence.filename ||
                evidence.source ||
                "Scientific source";

            const page =
                evidence.page ||
                "N/A";

            const text =
                evidence.text ||
                "";


            html += `

                <div class="knowledge-evidence-card">

                    <div class="evidence-header">

                        <strong>
                            📄 ${formatText(source)}
                        </strong>

                        <span>
                            Page ${formatText(
                                String(page)
                            )}
                        </span>

                    </div>

                    <div class="evidence-text">

                        ${formatText(text)}

                    </div>

                </div>
            `;
        }
    );


    html += `

        </div>
    `;


    return html;
}


// ==================================================
// FORMAT TEXT
// ==================================================

function formatText(text) {

    if (
        text === null ||
        text === undefined
    ) {

        return "";
    }


    return String(text)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        )
        .replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        )
        .replace(
            /\n/g,
            "<br>"
        );
}


// ==================================================
// ADD MESSAGE
// ==================================================

function addMessage(
    sender,
    text,
    type
) {

    const messageDiv =
        document.createElement("div");


    messageDiv.className =
        `message ${type}`;


    messageDiv.innerHTML = `

        <div class="message-content">

            <strong>
                ${formatText(sender)}
            </strong>

            <div class="message-text">
                ${text}
            </div>

        </div>

    `;


    chatBox.appendChild(
        messageDiv
    );


    chatBox.scrollTop =
        chatBox.scrollHeight;
}


// ==================================================
// START NEW CHAT
// ==================================================

async function startNewChat() {

    try {

        await fetch(
            `http://127.0.0.1:8000/chat/${sessionId}`,
            {
                method: "DELETE"
            }
        );

    } catch (error) {

        console.error(
            "Unable to clear server memory:",
            error
        );
    }


    chatBox.innerHTML = `

        <div class="message bot">

            <div class="message-content">

                <strong>
                    EcoMind AI
                </strong>

                <div class="message-text">

                    <p>
                        Hello! I'm ready to analyze a new
                        environmental scenario.
                    </p>

                    <p>
                        Tell me about your soil, climate,
                        land use or biodiversity conditions.
                    </p>

                </div>

            </div>

        </div>

    `;


    messageInput.value = "";

    messageInput.focus();
}
/**
 * Le Petit Prince RAG Frontend
 * Pure vanilla JavaScript - no dependencies
 */

// ===== Configuration =====
const CONFIG = {
    DEFAULT_API_URL: 'http://localhost:8000',
    STORAGE_KEYS: {
        API_URL: 'petitprince_api_url',
        CONVERSATION: 'petitprince_conversation',
        STREAMING: 'petitprince_streaming',
        DEBUG_MODE: 'petitprince_debug',
        METRICS_MODE: 'petitprince_metrics'
    },
    ENDPOINTS: {
        HEALTH: '/health',
        INIT: '/api/init',
        CHAT: '/api/v1/chat/completions'
    }
};

// ===== State Management =====
const state = {
    apiUrl: localStorage.getItem(CONFIG.STORAGE_KEYS.API_URL) || CONFIG.DEFAULT_API_URL,
    conversation: JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.CONVERSATION) || '[]'),
    streaming: localStorage.getItem(CONFIG.STORAGE_KEYS.STREAMING) !== 'false',
    debugMode: localStorage.getItem(CONFIG.STORAGE_KEYS.DEBUG_MODE) === 'true',
    metricsMode: localStorage.getItem(CONFIG.STORAGE_KEYS.METRICS_MODE) === 'true',
    isLoading: false
};

// ===== DOM Elements =====
const elements = {
    chatContainer: document.getElementById('chat-messages'),
    messageInput: document.getElementById('message-input'),
    sendButton: document.getElementById('send-button'),
    clearButton: document.getElementById('btn-clear'),
    initButton: document.getElementById('btn-init'),
    apiUrlInput: document.getElementById('api-url'),
    streamingToggle: document.getElementById('streaming-toggle'),
    debugToggle: document.getElementById('debug-toggle'),
    metricsToggle: document.getElementById('metrics-toggle'),
    apiStatus: document.getElementById('api-status'),
    statusText: document.getElementById('status-text')
};

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    setupEventListeners();
    checkAPIHealth();
    restoreConversation();
});

function initializeUI() {
    elements.apiUrlInput.value = state.apiUrl;
    elements.streamingToggle.checked = state.streaming;
    elements.debugToggle.checked = state.debugMode;
    elements.metricsToggle.checked = state.metricsMode;
}

function setupEventListeners() {
    // Send message
    elements.sendButton.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Clear conversation
    elements.clearButton.addEventListener('click', clearConversation);

    // Initialize index
    elements.initButton.addEventListener('click', initializeIndex);

    // Settings
    elements.apiUrlInput.addEventListener('change', (e) => {
        state.apiUrl = e.target.value;
        localStorage.setItem(CONFIG.STORAGE_KEYS.API_URL, state.apiUrl);
        checkAPIHealth();
    });

    elements.streamingToggle.addEventListener('change', (e) => {
        state.streaming = e.target.checked;
        localStorage.setItem(CONFIG.STORAGE_KEYS.STREAMING, state.streaming);
    });

    elements.debugToggle.addEventListener('change', (e) => {
        state.debugMode = e.target.checked;
        localStorage.setItem(CONFIG.STORAGE_KEYS.DEBUG_MODE, state.debugMode);
    });

    elements.metricsToggle.addEventListener('change', (e) => {
        state.metricsMode = e.target.checked;
        localStorage.setItem(CONFIG.STORAGE_KEYS.METRICS_MODE, state.metricsMode);
    });
}

// ===== API Communication =====
async function checkAPIHealth() {
    try {
        const response = await fetch(`${state.apiUrl}${CONFIG.ENDPOINTS.HEALTH}`);
        if (response.ok) {
            showStatus('Connecté', 'success');
        } else {
            showStatus('Erreur de connexion', 'error');
        }
    } catch (error) {
        showStatus('API non disponible', 'error');
        console.error('Health check failed:', error);
    }
}

async function initializeIndex() {
    if (!confirm('Voulez-vous réindexer le livre ? Cela peut prendre quelques minutes.')) {
        return;
    }

    showToast('Initialisation en cours...', 'info');
    setInputState(false);

    try {
        const response = await fetch(`${state.apiUrl}${CONFIG.ENDPOINTS.INIT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            showToast(`Initialisation réussie : ${data.statistics.paragraphs} paragraphes indexés`, 'success');
        } else {
            const error = await response.json();
            showToast(`Erreur: ${error.error?.message || 'Initialisation échouée'}`, 'error');
        }
    } catch (error) {
        showToast('Erreur de connexion', 'error');
        console.error('Init error:', error);
    } finally {
        setInputState(true);
    }
}

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isLoading) return;

    // Add user message to conversation
    const userMessage = { role: 'user', content: message };
    state.conversation.push(userMessage);
    appendMessage(userMessage);
    saveConversation();

    // Clear input
    elements.messageInput.value = '';
    setInputState(false);
    state.isLoading = true;

    try {
        if (state.streaming) {
            await sendStreamingMessage();
        } else {
            await sendBlockingMessage();
        }
    } catch (error) {
        console.error('Message error:', error);
        showToast('Erreur lors de l\'envoi', 'error');

        // Remove failed message attempt
        const lastAssistantIndex = state.conversation.findLastIndex(m => m.role === 'assistant');
        if (lastAssistantIndex !== -1) {
            state.conversation.splice(lastAssistantIndex, 1);
            saveConversation();
        }
    } finally {
        setInputState(true);
        state.isLoading = false;
    }
}

async function sendBlockingMessage() {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (state.metricsMode) {
        headers['X-Include-Metrics'] = 'true';
    }

    const response = await fetch(`${state.apiUrl}${CONFIG.ENDPOINTS.CHAT}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
            messages: state.conversation,
            stream: false
        })
    });

    if (!response.ok) {
        handleAPIError(response.status);
        throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const assistantMessage = data.choices[0].message;

    // Add metadata
    assistantMessage.metadata = {
        usage: data.usage,
        x_metrics: data.x_metrics
    };

    state.conversation.push(assistantMessage);
    appendMessage(assistantMessage);
    saveConversation();
}

async function sendStreamingMessage() {
    const headers = {
        'Content-Type': 'application/json'
    };

    if (state.metricsMode) {
        headers['X-Include-Metrics'] = 'true';
    }

    const response = await fetch(`${state.apiUrl}${CONFIG.ENDPOINTS.CHAT}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
            messages: state.conversation,
            stream: true
        })
    });

    if (!response.ok) {
        handleAPIError(response.status);
        throw new Error(`HTTP ${response.status}`);
    }

    // Create assistant message placeholder
    const messageElement = appendMessage({ role: 'assistant', content: '' });
    const contentElement = messageElement.querySelector('.message-text');
    let fullContent = '';
    let lastMetadata = null;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.substring(6).trim();

                    if (data === '[DONE]') {
                        break;
                    }

                    try {
                        const parsed = JSON.parse(data);
                        const delta = parsed.choices?.[0]?.delta;

                        if (delta?.content) {
                            fullContent += delta.content;
                            contentElement.textContent = fullContent;
                            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                        }

                        // Capture final metadata
                        if (parsed.usage) {
                            lastMetadata = {
                                usage: parsed.usage,
                                x_metrics: parsed.x_metrics
                            };
                        }
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', e);
                    }
                }
            }
        }

        // Save complete message
        const assistantMessage = {
            role: 'assistant',
            content: fullContent,
            metadata: lastMetadata
        };
        state.conversation.push(assistantMessage);

        // Update with metadata if in debug mode
        if (state.debugMode && lastMetadata) {
            appendDebugInfo(messageElement, lastMetadata);
        }

        saveConversation();

    } catch (streamError) {
        console.error('Stream error:', streamError);
        showToast('Connexion interrompue', 'error');
        contentElement.innerHTML += '<br><span style="color: var(--error);">⚠️ Connexion interrompue</span>';
    }
}

function handleAPIError(status) {
    const messages = {
        400: 'Requête invalide',
        404: 'Endpoint non trouvé',
        422: 'Données invalides',
        429: 'Trop de requêtes',
        500: 'Erreur serveur',
        503: 'Service indisponible'
    };

    const message = messages[status] || `Erreur ${status}`;
    showToast(message, 'error');
}

// ===== UI Functions =====
function appendMessage(message) {
    // Remove empty state if present
    const emptyState = elements.chatContainer.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${message.role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = message.content;
    contentDiv.appendChild(textDiv);

    // Add debug info if enabled
    if (state.debugMode && message.metadata) {
        appendDebugInfo(contentDiv, message.metadata);
    }

    messageDiv.appendChild(contentDiv);
    elements.chatContainer.appendChild(messageDiv);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

    return messageDiv;
}

function appendDebugInfo(container, metadata) {
    const debugDiv = document.createElement('div');
    debugDiv.className = 'debug-info';

    // Usage metrics
    if (metadata.usage) {
        const usageSection = createDebugSection('📊 Tokens', formatUsage(metadata.usage), true);
        debugDiv.appendChild(usageSection);
    }

    // Extended metrics
    if (metadata.x_metrics) {
        const timingsSection = createDebugSection('⏱️ Performances', formatTimings(metadata.x_metrics.timings), false);
        debugDiv.appendChild(timingsSection);

        const retrievalSection = createDebugSection('🔍 Récupération', formatRetrieval(metadata.x_metrics.retrieval), false);
        debugDiv.appendChild(retrievalSection);

        // Sources
        if (metadata.x_metrics.retrieval?.documents) {
            const sourcesSection = createDebugSection('📚 Sources', formatSources(metadata.x_metrics.retrieval.documents), false);
            debugDiv.appendChild(sourcesSection);
        }
    }

    container.appendChild(debugDiv);
}

function createDebugSection(title, content, defaultOpen = false) {
    const section = document.createElement('div');
    section.className = 'debug-section';

    const titleDiv = document.createElement('div');
    titleDiv.className = 'debug-section-title';
    titleDiv.innerHTML = `<span class="collapsible-icon ${defaultOpen ? 'open' : ''}">▶</span> ${title}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = `debug-section-content collapsible-content ${defaultOpen ? 'open' : ''}`;
    contentDiv.innerHTML = content;

    titleDiv.addEventListener('click', () => {
        const icon = titleDiv.querySelector('.collapsible-icon');
        icon.classList.toggle('open');
        contentDiv.classList.toggle('open');
    });

    section.appendChild(titleDiv);
    section.appendChild(contentDiv);
    return section;
}

function formatUsage(usage) {
    return `
        <div class="metric-row">
            <span class="metric-label">Tokens prompt:</span>
            <span class="metric-value">${usage.prompt_tokens}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Tokens réponse:</span>
            <span class="metric-value">${usage.completion_tokens}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Total:</span>
            <span class="metric-value">${usage.total_tokens}</span>
        </div>
    `;
}

function formatTimings(timings) {
    return `
        <div class="metric-row">
            <span class="metric-label">Embedding:</span>
            <span class="metric-value">${timings.embedding_ms?.toFixed(0) || 0}ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Recherche:</span>
            <span class="metric-value">${timings.search_ms?.toFixed(0) || 0}ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Reranking:</span>
            <span class="metric-value">${timings.rerank_ms?.toFixed(0) || 0}ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Génération:</span>
            <span class="metric-value">${timings.generation_ms?.toFixed(0) || 0}ms</span>
        </div>
        <div class="metric-row">
            <span class="metric-label"><strong>Total:</strong></span>
            <span class="metric-value"><strong>${timings.total_ms?.toFixed(0) || 0}ms</strong></span>
        </div>
    `;
}

function formatRetrieval(retrieval) {
    return `
        <div class="metric-row">
            <span class="metric-label">Documents récupérés:</span>
            <span class="metric-value">${retrieval.documents_retrieved}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Après reranking:</span>
            <span class="metric-value">${retrieval.documents_after_rerank}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Au-dessus du seuil:</span>
            <span class="metric-value">${retrieval.documents_above_threshold}/${retrieval.documents_after_rerank}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Seuil de pertinence:</span>
            <span class="metric-value">${retrieval.threshold_used}</span>
        </div>
    `;
}

function formatSources(documents) {
    return documents.map((doc, index) => {
        const isHigh = doc.score >= 0.7;
        const tag = `<span class="source-tag ${isHigh ? 'high' : 'moderate'}">${isHigh ? 'HAUTE' : 'MODÉRÉE'} - ${doc.score.toFixed(2)}</span>`;

        return `
            <div class="source-item">
                <strong>Extrait ${index + 1}</strong> ${tag}
                <p style="margin-top: 0.5rem; color: var(--text-dark); font-size: 0.8rem;">
                    ${doc.text.substring(0, 200)}${doc.text.length > 200 ? '...' : ''}
                </p>
            </div>
        `;
    }).join('');
}

function showStatus(text, type) {
    elements.apiStatus.className = `status-indicator ${type}`;
    elements.statusText.textContent = text;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✓',
        error: '✗',
        warning: '⚠',
        info: 'ℹ'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setInputState(enabled) {
    elements.messageInput.disabled = !enabled;
    elements.sendButton.disabled = !enabled;

    if (!enabled) {
        // Show loading indicator
        const loading = document.createElement('div');
        loading.className = 'loading-indicator';
        loading.id = 'loading-indicator';
        loading.innerHTML = `
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        `;
        elements.chatContainer.appendChild(loading);
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    } else {
        // Remove loading indicator
        const loading = document.getElementById('loading-indicator');
        if (loading) loading.remove();
    }
}

function clearConversation() {
    if (!confirm('Effacer toute la conversation ?')) return;

    state.conversation = [];
    elements.chatContainer.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">🌟</div>
            <h2 class="empty-state-title">Bienvenue dans l'univers du Petit Prince</h2>
            <p class="empty-state-text">Posez-moi des questions sur cette œuvre magnifique</p>
        </div>
    `;
    saveConversation();
    showToast('Conversation effacée', 'success');
}

function saveConversation() {
    // Save without metadata to reduce storage size
    const toSave = state.conversation.map(msg => ({
        role: msg.role,
        content: msg.content
    }));
    localStorage.setItem(CONFIG.STORAGE_KEYS.CONVERSATION, JSON.stringify(toSave));
}

function restoreConversation() {
    if (state.conversation.length === 0) return;

    elements.chatContainer.innerHTML = '';
    state.conversation.forEach(message => {
        appendMessage(message);
    });
}

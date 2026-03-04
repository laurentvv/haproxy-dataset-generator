"""CSS styles for HAProxy Chatbot UI."""

CUSTOM_CSS = """
/* Variables de thème */
:root {
    --haproxy-orange: #ff6b35;
    --haproxy-red: #e74c3c;
    --bg-dark: #0f0f0f;
    --bg-card: #1a1a1a;
    --bg-input: #252525;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
    --border-color: #333333;
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
}

/* Container principal */
.gradio-container {
    max-width: 1800px !important;
    margin: 0 auto !important;
    background: var(--bg-dark) !important;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%);
    border-radius: 12px;
    padding: 16px 24px;
    margin: 16px auto;
    text-align: center;
    color: white;
}

/* Chatbot */
.chatbot-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
}

.chatbot-container .chatbot {
    height: 70vh !important;
    max-height: 70vh !important;
}

/* Messages utilisateur */
.message-user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 12px 16px !important;
}

/* Messages assistant */
.message-assistant {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 12px 16px !important;
    border: 1px solid var(--border-color) !important;
}

/* Input area */
.input-area {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
}

.input-area textarea {
    background: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    font-size: 1em !important;
}

.input-area textarea:focus {
    border-color: var(--haproxy-orange) !important;
    box-shadow: 0 0 0 2px rgba(255,107,53,0.2) !important;
}

/* Boutons principaux */
.btn-primary {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

.btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(255,107,53,0.4) !important;
}

/* Exemples */
.examples-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 16px;
}

.example-card {
    background: var(--bg-input);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.85em;
    color: var(--text-primary);
    text-align: left;
    white-space: normal;
    height: auto;
    min-height: 50px;
    display: flex;
    align-items: center;
}

.example-card:hover {
    background: linear-gradient(135deg, var(--haproxy-orange) 0%, var(--haproxy-red) 100%);
    border-color: var(--haproxy-orange);
    color: white;
    transform: translateX(4px);
}

/* Sources */
.sources-box {
    background: var(--bg-input);
    border-left: 4px solid var(--haproxy-orange);
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 12px;
    font-size: 0.85em;
}

.sources-box a {
    color: var(--haproxy-orange);
}

/* Footer */
.app-footer {
    text-align: center;
    padding: 12px;
    color: var(--text-secondary);
    font-size: 0.8em;
    border-top: 1px solid var(--border-color);
    margin-top: 16px;
}

.app-footer a {
    color: var(--haproxy-orange);
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-dark);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--haproxy-orange);
}
"""

// EASY-CHATGPT Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    
    const promptTokensSpan = document.getElementById("prompt-tokens");
    const completionTokensSpan = document.getElementById("completion-tokens");
    const totalTokensSpan = document.getElementById("total-tokens");
    const jsonViewer = document.getElementById("json-viewer");

    // Initialize Conversation Context
    let messages = [
        { role: "system", content: "You are a helpful assistant. Keep your responses concise and well-formatted." }
    ];

    // Helper to format JSON nicely
    function updateContextViewer() {
        jsonViewer.textContent = JSON.stringify(messages, null, 2);
        // Apply syntax highlighting
        if (window.hljs) {
            window.hljs.highlightElement(jsonViewer);
        }
    }

    // Helper to update token usage on UI
    function updateTokenUsage(usage) {
        if (!usage) return;
        promptTokensSpan.textContent = usage.prompt_tokens || 0;
        completionTokensSpan.textContent = usage.completion_tokens || 0;
        totalTokensSpan.textContent = usage.total_tokens || 0;
    }

    // Helper to append a message to the Chat Area
    function appendMessageToChat(role, content) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}-message`;

        const tagDiv = document.createElement("div");
        tagDiv.className = "system-tag";
        tagDiv.textContent = role === "user" ? "You" : "Assistant";
        msgDiv.appendChild(tagDiv);

        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";

        // If assistant, parse Markdown using marked.js
        if (role === "assistant" && window.marked) {
            contentDiv.innerHTML = window.marked.parse(content);
        } else {
            // For user messages or if marked is not loaded, escape HTML and render as text
            contentDiv.textContent = content;
        }

        msgDiv.appendChild(contentDiv);
        chatMessages.appendChild(msgDiv);
        
        // Auto-scroll to bottom of the chat container
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Display typing indicator
    function showTypingIndicator() {
        const indicatorDiv = document.createElement("div");
        indicatorDiv.className = "message assistant-message typing-indicator-msg";
        indicatorDiv.id = "typing-indicator";

        const tagDiv = document.createElement("div");
        tagDiv.className = "system-tag";
        tagDiv.textContent = "Assistant";
        indicatorDiv.appendChild(tagDiv);

        const indicatorContent = document.createElement("div");
        indicatorContent.className = "typing-indicator";
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement("div");
            dot.className = "typing-dot";
            indicatorContent.appendChild(dot);
        }

        indicatorDiv.appendChild(indicatorContent);
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById("typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    // Auto-resize textarea to fit text
    userInput.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight - 4) + "px";
    });

    // Handle Enter to Submit (and Shift+Enter for newline)
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // Form Submission Handler
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Add user message to UI and state
        appendMessageToChat("user", text);
        messages.push({ role: "user", content: text });
        
        // 2. Update Context Panel to show current state being sent
        updateContextViewer();

        // 3. Reset input field
        userInput.value = "";
        userInput.style.height = "auto";
        
        // 4. Disable input & button and show typing indicator
        userInput.disabled = true;
        sendBtn.disabled = true;
        showTypingIndicator();

        try {
            // 5. Send POST request to FastAPI backend proxy
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ messages })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error (${response.status})`);
            }

            const data = await response.json();

            // 6. Remove typing indicator
            removeTypingIndicator();

            // 7. Add Assistant response to UI and state
            const assistantMsg = data.message;
            appendMessageToChat("assistant", assistantMsg.content);
            messages.push(assistantMsg);

            // 8. Update Context Viewer and Token Usage stats
            updateContextViewer();
            updateTokenUsage(data.usage);

        } catch (error) {
            removeTypingIndicator();
            console.error("Chat error:", error);
            
            // Render error message in assistant style
            appendMessageToChat("assistant", `❌ **Error:** Failed to get response. ${error.message}`);
        } finally {
            // Re-enable input & button
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });

    // Clear Conversation Context
    clearBtn.addEventListener("click", () => {
        if (confirm("Are you sure you want to clear the conversation context? This resets token counts and history.")) {
            // Reset state
            messages = [
                { role: "system", content: "You are a helpful assistant. Keep your responses concise and well-formatted." }
            ];
            
            // Clear UI
            chatMessages.innerHTML = `
                <div class="message assistant-message">
                    <div class="message-content">
                        Hello! Welcome to <strong>EASY-CHATGPT</strong>. Ask me anything, and watch the context array and token counts grow in the panel on the right!
                    </div>
                </div>
            `;
            
            // Reset tokens
            updateTokenUsage({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 });
            
            // Reset Context view
            updateContextViewer();
        }
    });

    // Initialize display on startup
    updateContextViewer();
});

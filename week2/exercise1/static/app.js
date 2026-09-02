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
    const assistantSelector = document.getElementById("assistant-selector");
    const newName = document.getElementById("new-name");
    const newSystem = document.getElementById("new-system");
    const newTemplate = document.getElementById("new-template");
    const saveAssistantBtn = document.getElementById("save-assistant-btn");
    const deleteAssistantBtn = document.getElementById("delete-assistant-btn");
    const contextFile = document.getElementById("context-file");
    const uploadContextBtn = document.getElementById("upload-context-btn");
    const jsonViewer = document.getElementById("json-viewer");

    async function refreshAssistants() {
        const res = await fetch("/api/assistants");
        const data = await res.json();
        assistantSelector.innerHTML = '<option value="">Default (No Assistant)</option>';
        data.forEach(a => {
            const opt = document.createElement("option");
            opt.value = a.id;
            opt.textContent = a.name;
            opt.dataset.prompt = a.system_prompt;
            opt.dataset.template = a.prompt_template;
            opt.dataset.knowledge = a.knowledge;
            assistantSelector.appendChild(opt);
        });
    }

    saveAssistantBtn.onclick = async () => {
        await fetch("/api/assistants", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                name: newName.value, 
                system_prompt: newSystem.value, 
                prompt_template: newTemplate.value 
            })
        });
        refreshAssistants();
    };

    deleteAssistantBtn.onclick = async () => {
        if (!assistantSelector.value) return;
        await fetch(`/api/assistants/${assistantSelector.value}`, { method: "DELETE" });
        refreshAssistants();
    };

    uploadContextBtn.onclick = async () => {
        if (!assistantSelector.value || !contextFile.files[0]) return;
        const text = await contextFile.files[0].text();
        await fetch(`/api/assistants/${assistantSelector.value}/context?context=${encodeURIComponent(text)}`, { method: "POST" });
        refreshAssistants();
    };


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
    function appendMessageToChat(role, content) { // Removed isStreaming parameter, as it's not strictly necessary for the initial append
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}-message`;

        const tagDiv = document.createElement("div");
        tagDiv.className = "system-tag";
        tagDiv.textContent = role === "user" ? "You" : "Assistant";
        msgDiv.appendChild(tagDiv);

        const contentDiv = document.createElement("div");
        contentDiv.className = "message-content";
        contentDiv.textContent = content; // Set initial content as text

        msgDiv.appendChild(contentDiv); // Append contentDiv here
        chatMessages.appendChild(msgDiv);
        
        // Auto-scroll to bottom of the chat container
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return contentDiv; // Return contentDiv for direct manipulation
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

    // Remove typing indicator
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

    // Handle sending message
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // 1. Add user message to UI and state (bare user question)
        appendMessageToChat("user", text);
        messages.push({ role: "user", content: text });
        
        // 2. Prepare body (let backend handle templating)
        const body = { messages: messages };
        const selectedOpt = assistantSelector.options[assistantSelector.selectedIndex];
        if (selectedOpt && selectedOpt.value) {
            body.assistant_id = selectedOpt.value;
        }

        // 4. Reset input field
        userInput.value = "";
        userInput.style.height = "auto";
        
        // 5. Disable input & button and show typing indicator
        userInput.disabled = true;
        sendBtn.disabled = true;
        showTypingIndicator();

        let assistantMessageContent = "";
        let fullMessageElement = appendMessageToChat("assistant", "");
        let promptShown = false;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });

            if (!response.ok) throw new Error("Server error");
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6);
                        if (jsonStr === '[DONE]') continue;
                        const data = JSON.parse(jsonStr);
                        if (data.text) {
                            assistantMessageContent += data.text;
                            fullMessageElement.textContent = assistantMessageContent;
                        } else if (data.sent_prompt) {
                            jsonViewer.textContent = JSON.stringify(data.sent_prompt, null, 2);
                            promptShown = true;
                        } else if (data.usage) {
                            updateTokenUsage(data.usage);
                        }
                    }
                }
            }
            messages.push({ role: "assistant", content: assistantMessageContent });
            if (!promptShown) updateContextViewer();
        } catch (error) {
            console.error("Chat error:", error);
            fullMessageElement.textContent = `❌ Error: ${error.message}`;
        } finally {
            removeTypingIndicator();
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    // Handle Enter to Submit (and Shift+Enter for newline)
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Form Submission Handler
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        sendMessage();
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
    refreshAssistants();
});
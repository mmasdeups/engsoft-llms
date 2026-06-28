// EASY-CHATGPT Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    const imageInput = document.getElementById("image-input");
    const attachedImagePreview = document.getElementById("attached-image-preview");
    let attachedImage = null;
    // Handle image attachment
    imageInput.addEventListener("change", function(event) {
        const file = event.target.files[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                alert("Please select an image file.");
                return;
            }
            const reader = new FileReader();
            reader.onload = function(e) {
                attachedImage = e.target.result;
                attachedImagePreview.innerHTML = `
                    <div class="attached-image-item">
                        <span>${file.name}</span>
                        <button class="remove-image-btn" aria-label="Remove image">&times;</button>
                    </div>
                `;
                // Add event listener to the remove button
                attachedImagePreview.querySelector('.remove-image-btn').addEventListener('click', () => {
                    attachedImage = null;
                    imageInput.value = ''; // Clear the file input
                    attachedImagePreview.innerHTML = '';
                });
            }
            reader.readAsDataURL(file);
        }
    });
    
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
        // Deep clone messages to avoid modifying the original array during rendering
        const messagesForDisplay = JSON.parse(JSON.stringify(messages));

        // Truncate image data URIs for display
        messagesForDisplay.forEach(message => {
            if (message.content && Array.isArray(message.content)) {
                message.content = message.content.map(part => {
                    if (part.type === 'image_url' && part.image_url && part.image_url.url && part.image_url.url.startsWith('data:image')) {
                        // Truncate the data URI, showing only the prefix and a snippet
                        const url = part.image_url.url;
                        const prefixEnd = url.indexOf(',') + 1;
                        const snippet = url.substring(prefixEnd, prefixEnd + 50);
                        return { ...part, image_url: { url: `data:image/...;base64,${snippet}...` } };
                    }
                    return part;
                });
            }
        });

        jsonViewer.textContent = JSON.stringify(messagesForDisplay, null, 2);
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
        if (!text && !attachedImage) return; // Prevent sending if both are empty

        let messageContent;
        if (attachedImage) {
            messageContent = [
                { type: "text", text: text },
                { type: "image_url", image_url: { url: attachedImage } }
            ];
        } else {
            messageContent = text;
        }

        // Add user message to UI and state
        appendMessageToChat("user", text); // Still display the text part of the message
        messages.push({ role: "user", content: messageContent });
        
        // Clear attached image and preview after sending
        attachedImage = null;
        imageInput.value = ''; // Clear the file input
        attachedImagePreview.innerHTML = '';

        // Update Context Panel to show current state being sent
        updateContextViewer();

        // Reset input field
        userInput.value = "";
        userInput.style.height = "auto";
        
        // Disable input & button and show typing indicator
        userInput.disabled = true;
        sendBtn.disabled = true;
        showTypingIndicator();

        let assistantMessageContent = "";
        let fullMessageElement = null; // Reference to the message content div to apply markdown to later

        try {
            // 5. Send POST request to FastAPI backend proxy
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ messages: messages })
            });

            if (!response.ok) {
                // If the response is not ok, attempt to read error data as JSON
                const errorText = await response.text();
                try {
                    const errorData = JSON.parse(errorText);
                    throw new Error(errorData.detail || `Server error (${response.status})`);
                } catch (jsonError) {
                    // If parsing as JSON fails, just use the raw text
                    throw new Error(`Server error (${response.status}): ${errorText}`);
                }
            }

            // Create an empty message bubble for the assistant to stream into
            fullMessageElement = appendMessageToChat("assistant", "");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete SSE data lines
                let lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete last line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6);
                        try {
                            if (jsonStr === '[DONE]') {
                                // Stream finished, markdown render the full content
                                if (window.marked) {
                                    fullMessageElement.innerHTML = window.marked.parse(assistantMessageContent);
                                }
                                continue; // Skip to next line, or break if this is indeed the last expected line
                            }
                            const data = JSON.parse(jsonStr);
                            if (data.text) {
                                assistantMessageContent += data.text;
                                fullMessageElement.textContent = assistantMessageContent; // Update live
                                chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
                            } else if (data.usage) {
                                updateTokenUsage(data.usage);
                            }
                        } catch (e) {
                            console.error("Error parsing SSE JSON:", e, "JSON string:", jsonStr);
                        }
                    }
                }
            }
            
            // 6. Remove typing indicator
            removeTypingIndicator();

            // 7. Add Assistant response to state (full message)
            messages.push({ role: "assistant", content: assistantMessageContent });

            // 8. Update Context Viewer
            updateContextViewer();

        } catch (error) {
            removeTypingIndicator();
            console.error("Chat error:", error);
            
            // Render error message in assistant style
            if (fullMessageElement) {
                fullMessageElement.innerHTML = `❌ **Error:** Failed to get response. ${error.message}`;
            } else {
                appendMessageToChat("assistant", `❌ **Error:** Failed to get response. ${error.message}`);
            }
        } finally {
            // Re-enable input & button
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
});

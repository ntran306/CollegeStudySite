class ChatWidgetManager {
    constructor() {
        // Read config from data attributes
        const configEl = document.getElementById('chatWidgetConfig');
        if (!configEl) {
            console.error('Chat widget config not found');
            return;
        }

        this.twilioClient = null;
        this.activeConversations = new Map();
        this.openChats = new Map();
        this.conversationListeners = new Set();
        this.friends = [];
        this.conversations = [];
        this.currentUserId = parseInt(configEl.dataset.userId);
        this.defaultAvatar = configEl.dataset.defaultAvatar;
        this.urls = {
            getToken: configEl.dataset.getTokenUrl,
            listConversations: configEl.dataset.listConversationsUrl,
            getMessages: configEl.dataset.getMessagesUrl,
            getOtherUser: configEl.dataset.getOtherUserUrl,
            getFriends: configEl.dataset.getFriendsUrl
        };
        
        // Debug log
        console.log('Chat widget URLs loaded:', this.urls);
        this.unreadCounts = new Map();
        
        this.init();
    }

     // --- Helpers for friend list state ---
    updateFriendLastMessage(conversationSid, message) {
        if (!this.mergedFriendsList) return;

        const sidStr = String(conversationSid);
        const idx = this.mergedFriendsList.findIndex(
            f => f.conversation_sid && String(f.conversation_sid) === sidStr
        );
        if (idx === -1) return;

        const friend = this.mergedFriendsList[idx];
        friend.last_message_body = message.body || '';
        friend.last_message_author = message.author || null;

        const rawDate = message.dateCreated || message.date_created || message.date || new Date().toISOString();
        friend.last_message_date = rawDate;
    }

    sortMergedFriendsList() {
        if (!this.mergedFriendsList) return;

        this.mergedFriendsList.sort((a, b) => {
            const da = a.last_message_date ? new Date(a.last_message_date) : null;
            const db = b.last_message_date ? new Date(b.last_message_date) : null;

            if (da && db) return db - da;          // newest first
            if (db) return 1;
            if (da) return -1;

            // fallback: alphabetical by username so it’s stable
            return (a.username || '').localeCompare(b.username || '');
        });
    }

    async init() {
        console.log('ChatWidgetManager init started');
        
        // Get DOM elements
        this.toggleBtn = document.getElementById('chatToggleBtn');
        this.friendsPanel = document.getElementById('chatFriendsPanel');
        this.closePanelBtn = document.getElementById('closeFriendsPanel');
        this.friendsList = document.getElementById('chatFriendsList');
        this.friendSearch = document.getElementById('friendSearch');
        this.notificationBadge = document.getElementById('chatNotificationBadge');
        this.widgetContainer = document.getElementById('chatWindowsContainer');

        console.log('DOM elements loaded:', {
            toggleBtn: !!this.toggleBtn,
            friendsPanel: !!this.friendsPanel,
            friendsList: !!this.friendsList,
            widgetContainer: !!this.widgetContainer
        });

        if (!this.toggleBtn) {
            console.error('Toggle button not found!');
            return;
        }

        // Attach event listeners FIRST - don't wait for Twilio
        this.toggleBtn.addEventListener('click', () => {
            console.log('Toggle button clicked');
            this.toggleFriendsPanel();
        });
        
        if (this.closePanelBtn) {
            this.closePanelBtn.addEventListener('click', () => this.closeFriendsPanel());
        }
        
        if (this.friendSearch) {
            this.friendSearch.addEventListener('input', (e) => this.filterFriends(e.target.value));
        }

        console.log('Event listeners attached');

        // Load friends and conversations first (don't wait for Twilio)
        this.loadFriendsAndConversations().catch(err => {
            console.error('Error loading friends:', err);
        });
        
        // Initialize Twilio in background (don't await)
        this.initializeTwilio().catch(err => {
            console.error('Error initializing Twilio:', err);
        });
    }

    toggleFriendsPanel() {
        console.log('toggleFriendsPanel called');
        const isActive = this.friendsPanel.classList.contains('active');
        console.log('Current state - isActive:', isActive);
        
        if (isActive) {
            this.friendsPanel.classList.remove('active');
            this.toggleBtn.classList.remove('active');
            console.log('Panel closed');
        } else {
            this.friendsPanel.classList.add('active');
            this.toggleBtn.classList.add('active');
            console.log('Panel opened');
        }
    }

    closeFriendsPanel() {
        this.friendsPanel.classList.remove('active');
        this.toggleBtn.classList.remove('active');
    }

    async initializeTwilio() {
        try {
            const response = await fetch(this.urls.getToken);
            const data = await response.json();
            
            if (data.error) {
                console.error('Failed to get Twilio token:', data.error);
                return;
            }

            // Create Twilio Client with new Client() constructor
            this.twilioClient = new Twilio.Conversations.Client(data.token);
            
            // Wait for client initialization
            this.twilioClient.on('stateChanged', (state) => {
                console.log('Twilio client state:', state);
                if (state === 'initialized') {
                    console.log('Twilio client fully initialized');
                    this.setupClientListeners();
                }
            });

            this.twilioClient.on('connectionStateChanged', (state) => {
                console.log('Connection state changed:', state);
            });

        } catch (error) {
            console.error('Error initializing Twilio:', error);
        }
    }

    setupClientListeners() {
        // FIXED: Set up listeners at client level for better performance
        this.twilioClient.on('conversationJoined', (conversation) => {
            console.log('Joined conversation:', conversation.sid);
            this.setupConversationListeners(conversation);
        });

        this.twilioClient.on('conversationAdded', (conversation) => {
            console.log('Conversation added:', conversation.sid);
            this.setupConversationListeners(conversation);
        });

        this.twilioClient.on('messageAdded', (message) => {
            console.log('Message added via client listener:', message);
            this.handleNewMessage(message);
        });
    }

    async setupConversationListeners(conversation) {
    const sid = conversation.sid;

    // avoid wiring the same conversation multiple times
    if (this.conversationListeners.has(sid)) {
        return;
    }
    this.conversationListeners.add(sid);

    this.activeConversations.set(sid, conversation);

    conversation.on('typingStarted', (participant) => {
        this.showTypingIndicator(sid, participant);
    });

    conversation.on('typingEnded', (participant) => {
        this.hideTypingIndicator(sid);
    });
}

    async loadFriendsAndConversations() {
        try {
            const [friendsResponse, conversationsResponse] = await Promise.all([
                fetch(this.urls.getFriends),
                fetch(this.urls.listConversations)
            ]);
            
            const friendsData = await friendsResponse.json();
            const conversationsData = await conversationsResponse.json();
            
            this.friends = friendsData.friends || [];
            this.conversations = conversationsData.conversations || [];
            
            this.mergedFriendsList = this.friends.map(friend => {
                const conversation = this.conversations.find(conv => {
                    const convOtherId = conv.other_user_id;
                    const convOtherUsername = conv.other_username;

                    const matchById =
                        convOtherId !== null &&
                        convOtherId !== undefined &&
                        Number(convOtherId) === Number(friend.id);

                    const matchByUsername =
                        !!convOtherUsername && convOtherUsername === friend.username;

                    return matchById || matchByUsername;
                });

                return {
                    ...friend,
                    conversation_sid: conversation ? conversation.sid : null,
                    has_conversation: !!conversation,
                    last_message_body: conversation ? (conversation.last_message_body || "") : "",
                    last_message_author: conversation ? conversation.last_message_author : null,
                    last_message_date: conversation ? conversation.last_message_date_created : null,
                };
            });

            // sort by most recent message
            this.sortMergedFriendsList();

            this.renderFriendsList();
        } catch (error) {
            console.error('Error loading friends and conversations:', error);
            if (this.friendsList) {
                this.friendsList.innerHTML = '<div class="chat-empty-state"><i class="fas fa-user-friends"></i><p>No friends to message yet</p></div>';
            }
        }
    }

    renderFriendsList() {
        if (!this.friendsList) return;

        if (!this.mergedFriendsList || this.mergedFriendsList.length === 0) {
            this.friendsList.innerHTML =
                '<div class="chat-empty-state"><i class="fas fa-user-friends"></i><p>No friends to message yet</p></div>';
            return;
        }

        this.friendsList.innerHTML = this.mergedFriendsList.map(friend => {
            const avatarUrl = friend.avatar_url || this.defaultAvatar;
            const username = friend.username;

            // Treat hasConversation as "we know a conversation SID OR we explicitly marked it"
            const hasConversation =
                (friend.conversation_sid && friend.conversation_sid !== '') ||
                !!friend.has_conversation;

            const unreadCount = hasConversation && friend.conversation_sid
                ? (this.unreadCounts.get(friend.conversation_sid) || 0)
                : 0;

            const unreadBadge = unreadCount > 0
                ? '<span class="chat-friend-unread">' + unreadCount + '</span>'
                : '';

            // ----- Last message preview logic -----
            const rawLastBody = friend.last_message_body || '';
            let lastMessageText = '';

            if (rawLastBody) {
                // We have a real last message – show it
                if (friend.last_message_author === 'user_' + this.currentUserId) {
                    lastMessageText = 'You: ' + rawLastBody;
                } else {
                    lastMessageText = rawLastBody;
                }
            } else {
                // No messages yet (whether or not a Twilio conversation SID exists)
                lastMessageText = 'Start a conversation';
            }

            const maxLen = 40;
            if (lastMessageText.length > maxLen) {
                lastMessageText = lastMessageText.slice(0, maxLen) + '…';
            }

            return ''
                + '<div class="chat-friend-item"'
                + ' data-user-id="' + friend.id + '"'
                + ' data-conversation-sid="' + (friend.conversation_sid || '') + '"'
                + ' data-has-conversation="' + hasConversation + '">'
                    + '<img src="' + avatarUrl + '" alt="' + username + '" class="chat-friend-avatar">'
                    + '<div class="chat-friend-info">'
                        + '<p class="chat-friend-name">' + username + '</p>'
                        + '<p class="chat-friend-last-message">' + this.escapeHtml(lastMessageText) + '</p>'
                    + '</div>'
                    + unreadBadge
                + '</div>';
        }).join('');

        // Click handlers
        this.friendsList.querySelectorAll('.chat-friend-item').forEach(item => {
            item.addEventListener('click', async () => {
                const userId = parseInt(item.dataset.userId);
                const conversationSid = item.dataset.conversationSid;
                const hasConversation = item.dataset.hasConversation === 'true';

                if (hasConversation && conversationSid) {
                    await this.openChatWindow(conversationSid, userId);
                } else {
                    await this.createAndOpenConversation(userId);
                }
            });
        });
    }

    filterFriends(searchTerm) {
        if (!this.friendsList) return; // ADDED: Check if element exists
        
        const items = this.friendsList.querySelectorAll('.chat-friend-item');
        const term = searchTerm.toLowerCase();

        items.forEach(item => {
            const name = item.querySelector('.chat-friend-name').textContent.toLowerCase();
            item.style.display = name.includes(term) ? 'flex' : 'none';
        });
    }

    async createAndOpenConversation(userId) {
        try {
            // Show loading state
            const friendItem = this.friendsList.querySelector(`[data-user-id="${userId}"]`);
            if (friendItem) {
                friendItem.style.opacity = '0.5';
                friendItem.style.pointerEvents = 'none';
            }

            // Use existing start_conversation endpoint
            const url = `/communication/messaging/start/${userId}/`;
            console.log('Creating conversation with URL:', url);
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // The response has "conversation_sid" field
            const conversationSid = data.conversation_sid || data.sid;
            
            // Update the friend's conversation data
            const friendIndex = this.mergedFriendsList.findIndex(f => f.id === userId);
            if (friendIndex !== -1) {
                this.mergedFriendsList[friendIndex].conversation_sid = conversationSid;
                this.mergedFriendsList[friendIndex].has_conversation = true;
            }

            // Re-render list to update UI
            this.renderFriendsList();

            // Get the conversation from Twilio and set up listeners
            if (this.twilioClient) {
                try {
                    const conversation = await this.twilioClient.getConversationBySid(conversationSid);
                    await this.setupConversationListeners(conversation);
                } catch (error) {
                    console.log('Conversation will be available via conversationAdded event');
                }
            }

            // Open the new conversation
            await this.openChatWindow(conversationSid, userId);

        } catch (error) {
            console.error('Error creating conversation:', error);
            alert('Failed to start conversation. Please try again.');
            
            // Reset loading state
            const friendItem = this.friendsList.querySelector(`[data-user-id="${userId}"]`);
            if (friendItem) {
                friendItem.style.opacity = '1';
                friendItem.style.pointerEvents = 'auto';
            }
        }
    }

    async openChatWindow(conversationSid, userId) {
        // Check if chat is already open
        if (this.openChats.has(conversationSid)) {
            const existingWindow = this.openChats.get(conversationSid);
            existingWindow.classList.remove('minimized');
            return;
        }

        // Limit to 3 open chats
        if (this.openChats.size >= 3) {
            alert('Maximum 3 chat windows allowed. Please close one first.');
            return;
        }

        try {
            // Get conversation details
            const url = this.urls.getOtherUser.replace('CONVERSATION_SID', conversationSid);
            const response = await fetch(url);
            const userData = await response.json();

            // Create chat window
            const chatWindow = this.createChatWindow(conversationSid, userData);
            this.widgetContainer.appendChild(chatWindow);
            
            this.openChats.set(conversationSid, chatWindow);
            
            // ⭐ Load messages and also update last-message preview for this friend
            await this.loadMessages(conversationSid, userId);
            
            // Clear unread count
            this.unreadCounts.delete(conversationSid);
            this.updateNotificationBadge();
            this.renderFriendsList();
        } catch (error) {
            console.error('Error opening chat window:', error);
            alert('Failed to open chat. Please try again.');
        }
    }

    createChatWindow(conversationSid, userData) {
        const div = document.createElement('div');
        div.className = 'chat-window active';
        div.dataset.conversationSid = conversationSid;
        
        const avatarUrl = userData.avatar_url || this.defaultAvatar;
        const username = userData.username || 'User';
        
        div.innerHTML = '<div class="chat-window-header" data-conversation-sid="' + conversationSid + '">' +
            '<img src="' + avatarUrl + '" alt="' + username + '" class="chat-window-avatar">' +
            '<div class="chat-window-info">' +
                '<h4 class="chat-window-name">' + username + '</h4>' +
            '</div>' +
            '<div class="chat-window-controls">' +
                '<button class="chat-window-control-btn minimize-btn" title="Minimize">' +
                    '<i class="fas fa-minus"></i>' +
                '</button>' +
                '<button class="chat-window-control-btn close-btn" title="Close">' +
                    '<i class="fas fa-times"></i>' +
                '</button>' +
            '</div>' +
        '</div>' +
        '<div class="chat-messages" id="messages-' + conversationSid + '">' +
            '<div class="chat-loading">' +
                '<i class="fas fa-spinner"></i>' +
            '</div>' +
        '</div>' +
        '<div class="chat-input-container">' +
            '<textarea class="chat-input" placeholder="Type a message..." rows="1" data-conversation-sid="' + conversationSid + '"></textarea>' +
            '<button class="chat-send-btn" data-conversation-sid="' + conversationSid + '">' +
                '<i class="fas fa-paper-plane"></i>' +
            '</button>' +
        '</div>';

        // Attach event handlers
        const header = div.querySelector('.chat-window-header');
        const minimizeBtn = div.querySelector('.minimize-btn');
        const closeBtn = div.querySelector('.close-btn');
        const input = div.querySelector('.chat-input');
        const sendBtn = div.querySelector('.chat-send-btn');

        header.addEventListener('click', (e) => {
            if (!e.target.closest('.chat-window-controls')) {
                div.classList.toggle('minimized');
            }
        });

        minimizeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            div.classList.toggle('minimized');
        });

        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.closeChatWindow(conversationSid);
        });

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage(conversationSid, input.value.trim());
            }
        });

        input.addEventListener('input', () => {
            this.handleTyping(conversationSid);
        });

        sendBtn.addEventListener('click', () => {
            this.sendMessage(conversationSid, input.value.trim());
        });

        return div;
    }

    async loadMessages(conversationSid) {
        const messagesContainer = document.getElementById('messages-' + conversationSid);
        if (!messagesContainer) return;

        try {
            const url = this.urls.getMessages.replace('CONVERSATION_SID', conversationSid);
            const response = await fetch(url);
            const data = await response.json();

            const messages = data.messages || [];

            if (messages.length > 0) {
                // Render messages in the order they come from backend
                messagesContainer.innerHTML = messages.map(msg =>
                    this.createMessageHTML({
                        author: msg.author,
                        body: msg.body,
                        date_created: msg.date_created
                    })
                ).join('');

                // Scroll to bottom so the latest one (in that order) is visible
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } else {
                messagesContainer.innerHTML =
                    '<div class="chat-empty-state"><i class="fas fa-comments"></i><p>No messages yet. Start the conversation!</p></div>';
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            messagesContainer.innerHTML =
                '<div class="chat-empty-state"><i class="fas fa-exclamation-circle"></i><p>Failed to load messages</p></div>';
        }
    }

    createMessageHTML(message) {
        // A message is "sent" if its author is this user's Twilio identity
        const isSent = message.author === 'user_' + this.currentUserId;

        // Support both dateCreated (Twilio events) and date_created (Django API)
        const rawDate = message.dateCreated || message.date_created || message.date;
        let time = '';

        if (rawDate) {
            const d = new Date(rawDate);
            if (!isNaN(d.getTime())) {
                time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
        }

        return ''
            + '<div class="chat-message ' + (isSent ? 'sent' : 'received') + '">'
                + '<img src="' + this.defaultAvatar + '" alt="Avatar" class="chat-message-avatar">'
                + '<div class="chat-message-content">'
                    + '<div class="chat-message-bubble">' + this.escapeHtml(message.body || '') + '</div>'
                    + '<div class="chat-message-time">' + (time || '') + '</div>'
                + '</div>'
            + '</div>';
    }

    async sendMessage(conversationSid, text) {
        if (!text) return;

        const input = document.querySelector('.chat-input[data-conversation-sid="' + conversationSid + '"]');
        const sendBtn = document.querySelector('.chat-send-btn[data-conversation-sid="' + conversationSid + '"]');
        
        if (!input || !sendBtn) return; // ADDED: Safety check
        
        input.disabled = true;
        sendBtn.disabled = true;

        try {
            const conversation = this.activeConversations.get(conversationSid);
            if (conversation) {
                await conversation.sendMessage(text);
                input.value = '';
                input.style.height = 'auto';
            } else {
                console.error('Conversation not found in activeConversations');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Failed to send message. Please try again.');
        } finally {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    handleNewMessage(message) {
        const conversationSid = message.conversation.sid;
        const messagesContainer = document.getElementById('messages-' + conversationSid);
        
        if (messagesContainer) {
            // Remove empty state if exists
            const emptyState = messagesContainer.querySelector('.chat-empty-state');
            if (emptyState) {
                emptyState.remove();
            }
            
            const messageHTML = this.createMessageHTML({
                author: message.author,
                body: message.body,
                dateCreated: message.dateCreated
            });
            
            messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else {
            // Chat window not open - increment unread count
            if (message.author !== 'user_' + this.currentUserId) {
                const currentCount = this.unreadCounts.get(conversationSid) || 0;
                this.unreadCounts.set(conversationSid, currentCount + 1);
                this.updateNotificationBadge();
            }
        }

        // ALWAYS update friend preview + ordering for this conversation
        this.updateFriendLastMessage(conversationSid, message);
        this.sortMergedFriendsList();
        this.renderFriendsList();
    }

    handleTyping(conversationSid) {
        const conversation = this.activeConversations.get(conversationSid);
        if (conversation) {
            conversation.typing();
        }
    }

    showTypingIndicator(conversationSid, participant) {
        if (participant.identity === 'user_' + this.currentUserId) return;
        
        const messagesContainer = document.getElementById('messages-' + conversationSid);
        if (messagesContainer) {
            const existingIndicator = messagesContainer.querySelector('.chat-typing-indicator');
            if (!existingIndicator) {
                messagesContainer.insertAdjacentHTML('beforeend', 
                    '<div class="chat-typing-indicator">' +
                        '<div class="chat-typing-dot"></div>' +
                        '<div class="chat-typing-dot"></div>' +
                        '<div class="chat-typing-dot"></div>' +
                    '</div>'
                );
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    }

    hideTypingIndicator(conversationSid) {
        const messagesContainer = document.getElementById('messages-' + conversationSid);
        if (messagesContainer) {
            const indicator = messagesContainer.querySelector('.chat-typing-indicator');
            if (indicator) indicator.remove();
        }
    }

    closeChatWindow(conversationSid) {
        const chatWindow = this.openChats.get(conversationSid);
        if (chatWindow) {
            chatWindow.remove();
            this.openChats.delete(conversationSid);
        }
    }

    updateNotificationBadge() {
        if (!this.notificationBadge) return; // ADDED: Safety check
        
        const totalUnread = Array.from(this.unreadCounts.values()).reduce((sum, count) => sum + count, 0);
        
        if (totalUnread > 0) {
            this.notificationBadge.textContent = totalUnread > 99 ? '99+' : totalUnread;
            this.notificationBadge.style.display = 'flex';
        } else {
            this.notificationBadge.style.display = 'none';
        }
    }

    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (document.getElementById('chatWidgetConfig')) {
            new ChatWidgetManager();
        }
    });
} else {
    if (document.getElementById('chatWidgetConfig')) {
        new ChatWidgetManager();
    }
}
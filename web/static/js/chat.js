let rooms = [];
let currentRoomId = null;
let currentRoomType = null;
let roomDrafts = {};
let roomReplyStates = {};
let roomScrollPositions = {};
let pageTracker = {};
let hasMoreTracker = {};
let isLoading = false;

function loadRooms() {
    return fetch('/chat/api/rooms')
        .then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(data => {
            rooms = data.rooms;
            renderRoomList();
        })
        .catch(err => {
            console.error('loadRooms error:', err);
            document.getElementById('roomList').innerHTML = '<div class="text-center text-muted py-4">加载失败: ' + err.message + '</div>';
        });
}

function renderRoomList() {
    const container = document.getElementById('roomList');
    const search = (document.getElementById('roomSearch').value || '').toLowerCase();
    let html = '';
    rooms.forEach(room => {
        if (search && !room.name.toLowerCase().includes(search)) return;
        const isActive = room.id === currentRoomId;
        const avatarHtml = room.type === 'group'
            ? `<div class="room-avatar-placeholder"><i class="fas fa-home"></i></div>`
            : (room.other_members.length > 0 && room.other_members[0].avatar
                ? `<img src="/static/${room.other_members[0].avatar}" class="room-avatar">`
                : `<div class="room-avatar-placeholder">${(room.name || '?')[0].toUpperCase()}</div>`);
        const onlineHtml = room.type === 'private' && room.online
            ? `<span class="online-dot"></span>` : '';
        const pinHtml = room.is_pinned ? `<i class="fas fa-thumbtack pin-icon"></i>` : '';
        const statusHtml = room.type === 'private'
            ? `<span class="room-status ${room.online ? 'online' : 'offline'}">${room.online ? '在线' : '离线'}</span>`
            : '';
        html += `
        <div class="room-item ${isActive ? 'active' : ''}" onclick="openRoom(${room.id}, '${room.type}')">
            ${avatarHtml}
            <div class="room-info">
                <div class="room-name">${room.name} ${pinHtml} ${statusHtml}</div>
                <div class="room-last-msg">${room.last_message || '暂无消息'}</div>
            </div>
            <div class="room-meta">
                <div class="room-time">${room.last_time || ''}</div>
            </div>
        </div>`;
    });
    container.innerHTML = html || '<div class="text-center text-muted py-4">暂无聊天</div>';
}

function filterRooms() {
    renderRoomList();
}

function openRoom(roomId, roomType) {
    if (currentRoomId) {
        roomDrafts[currentRoomId] = document.getElementById('msgInput').value;
        roomScrollPositions[currentRoomId] = document.getElementById('chatMessages').scrollTop;
    }

    currentRoomId = roomId;
    currentRoomType = roomType;
    
    localStorage.setItem('lastRoomId', roomId);
    localStorage.setItem('lastRoomType', roomType);

    pageTracker[roomId] = 1;
    hasMoreTracker[roomId] = true;

    console.log('[SocketIO] Emitting leave_room:', roomId);
    socket.emit('leave_room', {room_id: roomId});
    console.log('[SocketIO] Emitting join_room:', roomId);
    socket.emit('join_room', {room_id: roomId});
    document.getElementById('chatEmpty').style.display = 'none';
    document.getElementById('chatActive').style.display = 'flex';
    renderRoomList();
    
    loadMessages(roomId, 1, false, roomScrollPositions[roomId]);
    
    document.getElementById('msgInput').value = roomDrafts[roomId] || '';
    cancelReply(); 
    
    const section = document.getElementById('groupMembersSection');
    if (roomType === 'group') {
        section.style.display = 'block';
        loadGroupMembers(roomId);
    } else {
        section.style.display = 'none';
    }
    
    const room = rooms.find(r => r.id === roomId);
    if (room) {
        document.getElementById('chatName').textContent = room.name;
        if (roomType === 'private') {
            document.getElementById('chatStatus').innerHTML = room.online
                ? '<span style="color:#10b981;">在线</span>' : '<span style="color:#ef4444;">离线</span>';
        } else {
            document.getElementById('chatStatus').textContent = '群聊';
        }
    }
    
    if (window.innerWidth <= 768) {
        document.getElementById('chatSidebar').classList.add('hidden');
    }
}

function loadGroupMembers(roomId) {
    fetch(`/chat/api/rooms/${roomId}/members`)
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('groupMembersList');
            const count = document.getElementById('memberCount');
            count.textContent = `(${data.members.length})`;
            let html = '';
            data.members.forEach((m, index) => {
                const avatar = m.avatar ? `/static/${m.avatar}` : '/static/img/default-avatar.png';
                html += `
                    <div class="member-item">
                        <img src="${avatar}" class="member-avatar" title="${m.nickname}">
                        <div class="member-nickname">${m.nickname}</div>
                    </div>`;
            });
            list.innerHTML = html;
        });
}


function toggleGroupMembers() {
    const list = document.getElementById('groupMembersList');
    const chevron = document.getElementById('memberChevron');
    const isHidden = list.style.display === 'none';
    list.style.display = isHidden ? 'flex' : 'none';
    chevron.className = isHidden ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
}

function loadMessages(roomId, page = 1, prepend = false, scrollPos = null) {
    if (isLoading) return;
    isLoading = true;
    fetch(`/chat/api/rooms/${roomId}/messages?page=${page}`)
        .then(r => r.json())
        .then(data => {
            isLoading = false;
            hasMoreTracker[roomId] = data.has_more;
            pageTracker[roomId] = page;
            renderMessages(data.messages, prepend, scrollPos);
        })
        .catch(err => {
            isLoading = false;
            console.error('loadMessages error:', err);
        });
}

function loadMoreMessages() {
    console.log("[DEBUG] loadMoreMessages called, hasMore:", hasMoreTracker[currentRoomId], "isLoading:", isLoading);
    if (!hasMoreTracker[currentRoomId] || isLoading) return;
    loadMessages(currentRoomId, (pageTracker[currentRoomId] || 1) + 1, true);
}

function renderMessages(messages, prepend = false, scrollPos = null) {
    const container = document.getElementById('chatMessages');
    
    if (!prepend) {
        container.innerHTML = '';
    }

    const oldScrollHeight = container.scrollHeight;
    
    let html = '';
    messages.forEach(msg => {
        const isMine = msg.is_mine;
        const avatarHtml = msg.sender_avatar
            ? `<img src="/static/${msg.sender_avatar}" class="msg-avatar">`
            : `<div class="msg-avatar-placeholder">${(msg.sender_name || '?')[0].toUpperCase()}</div>`;
        let senderHtml = '';
        if (!isMine && currentRoomType === 'group') {
            senderHtml = `<div class="msg-sender-name">${msg.sender_name}</div>`;
        }
        if (msg.is_recalled) {
            html += `
            <div style="text-align:center;padding:8px 0;">
                <span class="msg-recalled" style="font-style:italic; color:#9ca3af !important; font-size: 0.75rem;">${isMine ? '你' : msg.sender_name}撤回了一条消息</span>
            </div>`;
            return;
        }
        let contentHtml = '';
        if (msg.message_type === 'image') {
            contentHtml = `<img src="/${msg.image_url}" class="msg-image" onclick="viewImage(this.src)">`;
            if (msg.content) {
                contentHtml += `<div style="margin-top:4px;">${escapeHtml(msg.content)}</div>`;
            }
        } else {
            contentHtml = escapeHtml(msg.content);
        }
        
        let quoteHtml = '';
        if (msg.reply_to_id) {
            quoteHtml = `<div class="msg-quote" style="align-self: ${isMine ? 'flex-end' : 'flex-start'}">${escapeHtml(msg.reply_sender_name || '...')}: ${escapeHtml(msg.reply_content || '...')}</div>`;
        }

        const canRecall = isMine && msg.created_at ? (Date.now() - new Date(msg.created_at).getTime() < 120000) : false;
        html += `
        <div class="msg-row ${isMine ? 'mine' : ''}" data-msg-id="${msg.id}" data-msg-time="${msg.created_at || ''}" oncontextmenu="showMsgMenu(event, ${msg.id}, ${isMine})">
            ${avatarHtml}
            <div class="msg-content-wrapper">
                ${senderHtml}
                <div class="msg-bubble">${contentHtml}</div>
                ${quoteHtml}
                <div class="msg-time">${msg.time}${canRecall ? ' · <span class="msg-recall-hint" onclick="recallMessage(' + msg.id + ')" style="cursor:pointer;color:#07c160;">撤回</span>' : ''}</div>
            </div>
        </div>`;
    });
    
    if (prepend) {
        container.insertAdjacentHTML('afterbegin', html);
        container.scrollTop = container.scrollHeight - oldScrollHeight;
    } else {
        container.innerHTML = html;
        if (scrollPos !== null) {
            container.scrollTop = scrollPos;
        } else {
            setTimeout(() => container.scrollTop = container.scrollHeight, 100);
        }
    }
}


let pendingImageFile = null;
let pendingImageName = '';

function handlePastedImage(file) {
    if (file.size > 10 * 1024 * 1024) {
        showToast('图片大小不能超过 10MB', 'error');
        return;
    }
    pendingImageFile = file;
    pendingImageName = 'pasted_image.png';
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('imagePreviewThumb').src = e.target.result;
        document.getElementById('imagePreviewName').textContent = pendingImageName;
        document.getElementById('imagePreviewBar').style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

function updateSendButtonState() {
    const inputArea = document.getElementById('msgInput');
    const content = inputArea.innerText.trim();
    const hasImage = inputArea.querySelector('img') !== null;
    document.getElementById('btnSend').disabled = !(content.length > 0 || hasImage);
}

function handleImageSelect(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    if (file.size > 10 * 1024 * 1024) {
        showToast('图片大小不能超过 10MB', 'error');
        return;
    }
    pendingImageFile = file;
    pendingImageName = file.name;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('imagePreviewThumb').src = e.target.result;
        document.getElementById('imagePreviewName').textContent = file.name;
        document.getElementById('imagePreviewBar').style.display = 'flex';
        updateSendButtonState();
    };
    reader.readAsDataURL(file);
    input.value = '';
}

function cancelImagePreview() {
    pendingImageFile = null;
    pendingImageName = '';
    document.getElementById('imagePreviewBar').style.display = 'none';
    document.getElementById('imagePreviewThumb').src = '';
    document.getElementById('imagePreviewName').textContent = '';
    updateSendButtonState();
}

function viewImage(src) {
    document.getElementById('imageViewerImg').src = src;
    document.getElementById('imageViewer').style.display = 'flex';
}

function sendMessage() {
    const inputArea = document.getElementById('msgInput');
    const nodes = inputArea.childNodes;
    let textContent = '';
    let images = [];
    
    nodes.forEach(node => {
        if (node.nodeType === Node.TEXT_NODE) {
            textContent += node.textContent;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'IMG') {
                images.push(node.src);
            } else if (node.tagName === 'A') {
                textContent += node.href || node.textContent;
            } else {
                textContent += node.textContent;
            }
        }
    });

    const content = textContent.trim();
    console.log('[DEBUG] sendMessage content:', content, 'replyingToId:', replyingToId);
    if (!currentRoomId) return;
    if (!content && images.length === 0) return;

    if (images.length > 0) {
        if (inputArea.dataset.isSending) return;
        inputArea.dataset.isSending = 'true';
        
        fetch(images[0]).then(r => r.blob()).then(blob => {
            const formData = new FormData();
            formData.append('image', blob, 'pasted.png');
            return fetch('/chat/api/upload-image', { method: 'POST', body: formData });
        })
        .then(res => res.json())
        .then(data => {
            if (data.url) {
                socket.emit('send_message', {
                    room_id: currentRoomId,
                    content: content,
                    image_url: data.url,
                    message_type: 'image',
                    reply_to_id: replyingToId
                });
                inputArea.innerHTML = '';
                cancelReply();
            }
        })
        .finally(() => {
            delete inputArea.dataset.isSending;
        });
    } else {
        socket.emit('send_message', {room_id: currentRoomId, content: content, reply_to_id: replyingToId});
        inputArea.innerHTML = '';
        cancelReply();
    }
}

function handleInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

let allUsers = [];

function showNewChatModal() {
    const modal = new bootstrap.Modal(document.getElementById('newChatModal'));
    document.getElementById('userListBody').innerHTML = '<div class="text-center text-muted py-4">加载中...</div>';
    modal.show();
    
    const modalBody = document.getElementById('userListBody');
    modalBody.innerHTML = `
        <div class="p-2 border-bottom">
            <input type="text" id="userSearch" class="form-control form-control-sm" placeholder="搜索家庭成员..." oninput="filterUsers()">
        </div>
        <div id="userListItems"></div>
    `;

    fetch('/chat/api/users')
        .then(r => r.json())
        .then(data => {
            allUsers = data.users;
            renderUserList(allUsers);
        });
}

function renderUserList(users) {
    const container = document.getElementById('userListItems');
    const search = (document.getElementById('userSearch')?.value || '').toLowerCase();
    
    let html = '';
    users.forEach(u => {
        if (search && !(u.nickname || u.username).toLowerCase().includes(search)) return;
        
        const avatarHtml = u.avatar
            ? `<img src="/static/${u.avatar}" style="width:36px;height:36px;border-radius:4px;margin-right:12px;object-fit:cover;flex-shrink:0;">`
            : `<div class="room-avatar-placeholder" style="width:36px;height:36px;font-size:0.8rem;margin-right:12px;">${(u.nickname || '?')[0].toUpperCase()}</div>`;
        const roleText = u.role === 'admin' ? '管理员' : u.role === 'assistant' ? '辅助管理员' : '家人';
        html += `
        <div class="user-list-item" onclick="startPrivateChat(${u.id})">
            ${avatarHtml}
            <div style="flex:1;">
                <div class="user-name">${u.nickname || u.username} ${u.online ? '<span class="online-dot"></span>' : ''}</div>
                <div class="user-role">${roleText}</div>
            </div>
        </div>`;
    });
    container.innerHTML = html || '<div class="text-center text-muted py-4">暂无可聊天的用户</div>';
}

function filterUsers() {
    renderUserList(allUsers);
}

function startPrivateChat(userId) {
    fetch('/chat/api/rooms/create-private', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
    })
    .then(r => r.json())
    .then(data => {
        bootstrap.Modal.getInstance(document.getElementById('newChatModal')).hide();
        loadRooms();
        setTimeout(() => {
            const room = rooms.find(r => r.id === data.room_id);
            if (room) openRoom(room.id, room.type);
        }, 300);
    });
}

function showSidebar() {
    document.getElementById('chatSidebar').classList.remove('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showMsgMenu(e, msgId, isMine) {
    e.preventDefault();
    const existing = document.getElementById('msgContextMenu');
    if (existing) existing.remove();

    const menu = document.createElement('div');
    menu.id = 'msgContextMenu';
    menu.className = 'msg-context-menu';
    
    const copyItem = document.createElement('div');
    copyItem.className = 'msg-context-menu-item';
    copyItem.innerHTML = '<i class="fas fa-copy"></i>复制';
    copyItem.onclick = () => copyMessage(msgId);
    menu.appendChild(copyItem);

    const replyItem = document.createElement('div');
    replyItem.className = 'msg-context-menu-item';
    replyItem.innerHTML = '<i class="fas fa-reply"></i>引用';
    replyItem.onclick = () => replyMessage(msgId);
    menu.appendChild(replyItem);

    const msgElement = document.querySelector(`[data-msg-id="${msgId}"]`);
    const msgTimeStr = msgElement.getAttribute('data-msg-time');
    const msgTime = new Date(msgTimeStr).getTime();
    const isWithinTime = (Date.now() - msgTime) < 120000;

    if (isMine && isWithinTime) {
        const recallItem = document.createElement('div');
        recallItem.className = 'msg-context-menu-item danger';
        recallItem.innerHTML = '<i class="fas fa-undo"></i>撤回';
        recallItem.onclick = () => recallMessage(msgId);
        menu.appendChild(recallItem);
    }
    
    menu.style.left = e.clientX + 'px';
    menu.style.top = e.clientY + 'px';
    document.body.appendChild(menu);
}

let replyingToId = null;

function copyMessage(msgId) {
    const el = document.querySelector(`[data-msg-id="${msgId}"] .msg-bubble`);
    if (el) {
        const text = el.innerText;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(() => showToast('已复制'))
                .catch(err => {
                    console.error('复制失败: ', err);
                    showToast('复制失败', 'error');
                });
        } else {
            const textArea = document.createElement("textarea");
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                showToast('已复制');
            } catch (err) {
                console.error('复制失败: ', err);
                showToast('复制失败', 'error');
            }
            document.body.removeChild(textArea);
        }
    }
    document.getElementById('msgContextMenu')?.remove();
}

function replyMessage(msgId) {
    replyingToId = msgId;
    const bubble = document.querySelector(`[data-msg-id="${msgId}"] .msg-bubble`);
    const sender = document.querySelector(`[data-msg-id="${msgId}"] .msg-sender-name`)?.innerText || '对方';
    const content = bubble ? bubble.innerText : '...';
    
    const container = document.getElementById('chatInputArea');
    let quoteBar = document.getElementById('replyQuoteBar');
    if(!quoteBar){
            quoteBar = document.createElement('div');
            quoteBar.id = 'replyQuoteBar';
            quoteBar.className = 'msg-quote-bar';
            container.insertBefore(quoteBar, container.firstChild);
    }
    quoteBar.innerHTML = `<span>引用 ${sender}: ${content.substring(0, 20)}...</span> <i class="fas fa-times" onclick="cancelReply()"></i>`;
    document.getElementById('msgInput').focus();
    document.getElementById('msgContextMenu')?.remove();
}

function cancelReply() {
    replyingToId = null;
    const quoteBar = document.getElementById('replyQuoteBar');
    if(quoteBar) quoteBar.remove();
}

function recallMessage(msgId) {
    const el = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!el) return;
    fetch(`/chat/api/messages/${msgId}/recall`, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        if (!data.message) {
            showToast(data.error || '撤回失败', 'error');
        }
    })
    .catch(() => showToast('撤回失败', 'error'));
}

socket.on('message_recalled', (data) => {
    console.log('[SocketIO] message_recalled event received:', data);
    const el = document.querySelector(`[data-msg-id="${data.msg_id}"]`);
    if (el) {
        const isMine = data.sender_id === currentUserId;
        el.outerHTML = `
        <div style="text-align:center;padding:8px 0;">
            <span class="msg-recalled" style="font-style:italic; color:#9ca3af !important; font-size: 0.75rem;">${isMine ? '你' : '对方'}撤回了一条消息</span>
        </div>`;
    } else if (data.room_id === currentRoomId) {
        loadMessages(currentRoomId);
    }
    
    const room = rooms.find(r => r.id === data.room_id);
    if (room) {
        room.last_message = '撤回了一条消息';
        room.last_sender = '';
        renderRoomList();
    }
});

document.addEventListener('click', () => {
    const menu = document.getElementById('msgContextMenu');
    if (menu) menu.remove();
});

socket.on('new_message', (data) => {
    const isMine = data.sender_id === currentUserId;
    if (data.room_id === currentRoomId) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        const avatarHtml = data.sender_avatar
            ? `<img src="/static/${data.sender_avatar}" class="msg-avatar">`
            : `<div class="msg-avatar-placeholder">${(data.sender_name || '?')[0].toUpperCase()}</div>`;
        let senderHtml = '';
        if (!isMine && currentRoomType === 'group') {
            senderHtml = `<div class="msg-sender-name">${data.sender_name}</div>`;
        }
        let contentHtml = '';
        if (data.message_type === 'image') {
            contentHtml = `<img src="/${data.image_url}" class="msg-image" onclick="viewImage(this.src)">`;
            if (data.content) {
                contentHtml += `<div style="margin-top:4px;">${escapeHtml(data.content)}</div>`;
            }
        } else {
            contentHtml = escapeHtml(data.content);
        }
        
        let quoteHtml = '';
        if (data.reply_to_id) {
            quoteHtml = `<div class="msg-quote" style="align-self: ${isMine ? 'flex-end' : 'flex-start'}">${escapeHtml(data.reply_sender_name || '...')}: ${escapeHtml(data.reply_content || '...')}</div>`;
        }

        const html = `
        <div class="msg-row ${isMine ? 'mine' : ''}" data-msg-id="${data.id}" data-msg-time="${data.created_at || ''}" oncontextmenu="showMsgMenu(event, ${data.id}, ${isMine})">
            ${avatarHtml}
            <div class="msg-content-wrapper">
                ${senderHtml}
                <div class="msg-bubble">${contentHtml}</div>
                ${quoteHtml}
                <div class="msg-time">${data.time}</div>
            </div>
        </div>`;

        container.insertAdjacentHTML('beforeend', html);
        container.scrollTop = container.scrollHeight;
    }
    const room = rooms.find(r => r.id === data.room_id);
    if (room) {
        room.last_message = data.message_type === 'image' ? '[图片]' : data.content;
        room.last_time = data.time;
        room.last_sender = data.sender_name;
        renderRoomList();
    }
});

socket.on('online_status', (data) => {
    rooms.forEach(r => {
        if (r.type === 'private' && r.other_members.length > 0) {
            r.other_members.forEach(m => {
                if (m.id === data.user_id) {
                    m.online = data.online;
                    r.online = data.online;
                }
            });
        }
    });
    if (currentRoomType === 'private') {
        const room = rooms.find(r => r.id === currentRoomId);
        if (room) {
            document.getElementById('chatStatus').innerHTML = room.online
                ? '<span style="color:#10b981;">在线</span>' : '<span style="color:#ef4444;">离线</span>';
        }
    }
    renderRoomList();
});

document.addEventListener('DOMContentLoaded', () => {
    const lastRoomId = parseInt(localStorage.getItem('lastRoomId'));
    const lastRoomType = localStorage.getItem('lastRoomType');
    
    if (lastRoomId) {
        document.getElementById('chatEmpty').style.display = 'none';
        document.getElementById('chatActive').style.display = 'flex';
        window.isRestoringRoom = true;
    }

    document.getElementById('msgInput').addEventListener('input', updateSendButtonState);
    document.getElementById('msgInput').addEventListener('keydown', handleInputKey);
    document.getElementById('btnSend').addEventListener('click', sendMessage);

    let scrollTimeout;

    document.getElementById('chatMessages').addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            if (document.getElementById('chatMessages').scrollTop === 0) {
                loadMoreMessages();
            }
        }, 150);
    });

    document.getElementById('msgInput').addEventListener('paste', (e) => {
        const items = e.clipboardData.items;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                
                const img = document.createElement('img');
                img.src = URL.createObjectURL(blob);
                img.style.maxWidth = '100px';
                img.style.maxHeight = '100px';
                img.className = 'pasted-image';
                
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    selection.getRangeAt(0).insertNode(img);
                    selection.collapseToEnd();
                } else {
                    document.getElementById('msgInput').appendChild(img);
                }
                
                e.preventDefault();
                break;
            }
        }
        updateSendButtonState();
    });

    loadRooms().then(() => {
        const room = rooms.find(r => r.id === lastRoomId);
        if (room) {
            openRoom(room.id, room.type);
        } else {
            const familyRoom = rooms.find(r => r.is_pinned);
            if (familyRoom) openRoom(familyRoom.id, familyRoom.type);
        }
        window.isRestoringRoom = false;
    });

    const resizer = document.getElementById('chatResizer');
    const sidebar = document.getElementById('chatSidebar');
    const resizerY = document.getElementById('chatResizerY');
    const inputArea = document.getElementById('chatInputArea');
    
    let isResizing = false;
    let startX = 0;
    let startWidth = 0;
    
    let isResizingY = false;
    let startY = 0;
    let startHeight = 0;

    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = sidebar.offsetWidth;
        resizer.classList.add('active');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    resizerY.addEventListener('mousedown', (e) => {
        isResizingY = true;
        startY = e.clientY;
        startHeight = inputArea.offsetHeight;
        resizerY.classList.add('active');
        document.body.style.cursor = 'row-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (isResizing) {
            const delta = e.clientX - startX;
            const newWidth = Math.min(Math.max(startWidth + delta, 220), 500);
            sidebar.style.width = newWidth + 'px';
        } else if (isResizingY) {
            const delta = startY - e.clientY;
            const newHeight = Math.min(Math.max(startHeight + delta, 100), 400);
            inputArea.style.height = newHeight + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('active');
            localStorage.setItem('chatSidebarWidth', sidebar.style.width);
        }
        if (isResizingY) {
            isResizingY = false;
            resizerY.classList.remove('active');
            localStorage.setItem('chatInputHeight', inputArea.style.height);
        }
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    });
});

window.addEventListener('load', () => {
    const savedWidth = localStorage.getItem('chatSidebarWidth');
    const savedHeight = localStorage.getItem('chatInputHeight');
    if (savedWidth) {
        document.getElementById('chatSidebar').style.width = savedWidth;
    }
    if (savedHeight) {
        document.getElementById('chatInputArea').style.height = savedHeight;
    }
});

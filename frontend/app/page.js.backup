// src/app/page.js
"use client";
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import MessageInput from "@/components/MessageInput";
import HistoryViewer from "@/components/HistoryViewer";

export default function Home() {
    const BASE_URL = "http://192.168.0.104:8000";

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [search, setSearch] = useState("");
    const [editingIndex, setEditingIndex] = useState(null);
    const [newName, setNewName] = useState("");
    const [chats, setChats] = useState([]);
    const [activeChatId, setActiveChatId] = useState(null);
    const [input, setInput] = useState("");
    const [isThinking, setIsThinking] = useState(false);
    
    const [isExecuting, setIsExecuting] = useState(false); 
    
    const [pendingConfig, setPendingConfig] = useState(null);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    const [showGraph, setShowGraph] = useState(false);
    const [configHistory, setConfigHistory] = useState([]);
    const [showHistory, setShowHistory] = useState(false);
    const [selectedImage, setSelectedImage] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);
    const fileInputRef = useRef(null);
    const [currentTopology, setCurrentTopology] = useState(null);
    const [networkUsers, setNetworkUsers] = useState([]);


    const activeChat = chats.find((c) => c.id === activeChatId);

    const safeFetchJson = async (url, options = {}) => {
        try {
            const res = await fetch(url, options);
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Server Error (${res.status}): ${errText.substring(0, 100)}...`);
            }
            const text = await res.text();
            if (!text) return null;
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error("Gagal parse JSON:", text);
                throw new Error("Respon server bukan JSON valid");
            }
        } catch (err) {
            console.error("Fetch Error:", err);
            throw err;
        }
    };

    // Mengambil Data Chat & History
    useEffect(() => {
        const fetchChats = async () => {
            try {
                const data = await safeFetchJson(`${BASE_URL}/api/chats/`);
                if (Array.isArray(data)) {
                    const formatted = data.map((c) => ({
                        id: String(c.id),
                        title: c.title,
                        messages: [],
                    }));
                    setChats(formatted);
                    if (formatted.length > 0 && !activeChatId) {
                        setActiveChatId(formatted[0].id);
                    }
                }
            } catch (e) {
                console.error("Gagal load chat list:", e);
            }
        };
        const fetchNetworkUsers = async () => {
            try {
                // Pastikan endpoint ini sesuai dengan URL backend-mu
                const data = await safeFetchJson(`${BASE_URL}/api/network-devices/`); 
                if (Array.isArray(data)) {
                    setNetworkUsers(data);
                }
            } catch (e) {
                console.error("Gagal load daftar user network:", e);
            }
        };
        fetchChats();
        fetchNetworkUsers();
        fetchConfigHistory(); 
    }, []);

    useEffect(() => {
        if (!activeChatId) return;
        const loadMessages = async () => {
            try {
                const data = await safeFetchJson(`${BASE_URL}/api/chats/${activeChatId}/messages/`);
                if (!data) return;
                if (data.messages) {
                    setChats((prev) =>
                        prev.map((c) =>
                            c.id === activeChatId ? { ...c, messages: data.messages } : c
                        )
                    );
                }
                if (data.topology) setCurrentTopology(data.topology);
                else setCurrentTopology(null);
            } catch (err) {
                console.error("Gagal load pesan:", err);
            }
        };
        loadMessages();
    }, [activeChatId]);

    const fetchConfigHistory = async () => {
        try {
            const data = await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/`);
            if (Array.isArray(data)) setConfigHistory(data);
        } catch (error) {
            console.error("Error fetching history:", error);
        }
    };

    const handleOpenHistory = () => {
        fetchConfigHistory();
        setShowHistory(true);
    };

    // Chat Management 
    const handleNewChat = useCallback(async () => {
        try {
            const data = await safeFetchJson(`${BASE_URL}/api/chats/create/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
            if (data) {
                const newChat = { id: String(data.id), title: data.title, messages: [] };
                setChats((prev) => [...prev, newChat]);
                setActiveChatId(String(data.id));
            }
        } catch (err) {
            console.error("Gagal membuat chat:", err);
        }
    }, [setChats, setActiveChatId, BASE_URL]);

    const handleRename = (index) => {
        if (newName.trim() === "") return;
        const updated = [...chats];
        updated[index].title = newName;
        setChats(updated);
        setEditingIndex(null);
    };

    const handleDelete = async (index) => {
        const chatIdToDelete = chats[index].id;
        try {
            await fetch(`${BASE_URL}/api/chats/${chatIdToDelete}/delete/`, { method: "DELETE" });
            const updated = chats.filter((_, i) => i !== index);
            setChats(updated);
            if (updated.length > 0) setActiveChatId(updated[0].id);
            else setActiveChatId(null);
        } catch (err) {
            console.error("Gagal hapus chat:", err);
        }
    };


    const executeConfig = async (finalConfig) => {
        try {
            const result = await safeFetchJson(`${BASE_URL}/api/execute_config/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chat_id: activeChatId,
                    config_cli: finalConfig,
                }),
            });
            return result;
        } catch (e) {
            console.error("EXEC ERROR:", e);
            throw e;
        }
    };

    const handleApproveConfig = async (editedConfig) => {
        if (!editedConfig) return;
        
        setIsExecuting(true);
        
        let executionSuccess = false;
        let outputMessage = "";
        let errorDetail = "";

        try {
            const execResult = await executeConfig(editedConfig);
            const isConfigChanged = pendingConfig && (pendingConfig.trim() !== editedConfig.trim());
            const editNotice = isConfigChanged 
                ? `\n\nKonfigurasi diedit oleh pengguna:\n\n${editedConfig}\n` 
                : "";
            if (execResult && execResult.results && execResult.results.length > 0) {
                const firstResult = execResult.results[0];
                if (firstResult.status === 'success') {
                    executionSuccess = true;
                    outputMessage = `✅ Konfigurasi berhasil diproses di perangkat ${firstResult.target}${editNotice}`;
                } else {
                    executionSuccess = false;
                    errorDetail = firstResult.stderr || firstResult.error || "Unknown Error";
                    outputMessage = `❌ Konfigurasi gagal diterapkan pada ${firstResult.target}\nError: ${editNotice}`;
                }
                
            } else {
                executionSuccess = false;
                outputMessage = "⚠️ Eksekusi selesai tapi tidak ada respons detail.";
            }

            await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/add/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    config: editedConfig,
                    status: executionSuccess ? "Berhasil" : "Gagal",
                }),
            });

            await safeFetchJson(`${BASE_URL}/api/chats/messages/save/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chat_id: activeChatId,
                    role: "assistant",
                    content: outputMessage,
                }),
            });

            const newMessage = { role: "bot", text: outputMessage };
            setChats((prev) =>
                prev.map((c) =>
                    c.id === activeChatId
                        ? { ...c, messages: [...(c.messages || []), newMessage] }
                        : c
                )
            );

        } catch (error) {
            console.error("Error approve:", error);
            const errorMsg = `❌ Terjadi kesalahan sistem saat memproses: ${error.message}`;
            setChats((prev) =>
                prev.map((c) =>
                    c.id === activeChatId
                        ? { ...c, messages: [...(c.messages || []), { role: "bot", text: errorMsg }] }
                        : c
                )
            );
        } finally {
            // 6. Cleanup
            setPendingConfig(null);
            fetchConfigHistory();
            setIsExecuting(false);
            setShowConfirmPopup(false);
        }
    };

    const handleRejectConfig = async () => {
        setShowConfirmPopup(false);
        if (!pendingConfig) return;
        
        const rejectMsg = "❌ Konfigurasi dibatalkan oleh pengguna.";

        try {
            await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/add/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    config: pendingConfig,
                    status: "Ditolak",
                }),
            });
            await safeFetchJson(`${BASE_URL}/api/chats/messages/save/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chat_id: activeChatId,
                    role: "assistant",
                    content: rejectMsg,
                }),
            });
            
             setChats((prev) =>
                prev.map((c) =>
                    c.id === activeChatId
                        ? { ...c, title: data.title ? data.title : c.title, messages: [...(c.messages || []), { role: "bot", text: rejectMsg }] }
                        : c
                )
            );

        } catch (error) {
            console.error("Error reject:", error);
        } finally {
            setPendingConfig(null);
            fetchConfigHistory();
        }
    };

    const handleSend = async () => {
        if (!input.trim() && !selectedImage) return;
        
        const currentInput = input;
        const currentSelectedImage = selectedImage;
        const currentPreviewUrl = previewUrl;

        let userMessage;
        if (currentInput.trim() && currentSelectedImage) {
            userMessage = { role: "user", text: currentInput.trim(), image: currentPreviewUrl };
        } else if (currentInput.trim()) {
            userMessage = { role: "user", text: currentInput.trim() };
        } else if (currentSelectedImage) {
            userMessage = { role: "user", image: currentPreviewUrl };
        }

        if (userMessage) {
            setChats((prev) =>
                prev.map((c) =>
                    c.id === activeChatId ? { ...c, messages: [...(c.messages || []), userMessage] } : c
                )
            );
        }

        setInput("");
        setSelectedImage(null);
        setPreviewUrl(null);
        setIsThinking(true);

        try {
            let res;
            if (currentSelectedImage) {
                const formData = new FormData();
                formData.append("image", currentSelectedImage);
                formData.append("chat_id", activeChatId || "");
                formData.append("prompt", currentInput.trim());
                res = await fetch(`${BASE_URL}/api/chat/`, { method: "POST", body: formData });
            } else {
                res = await fetch(`${BASE_URL}/api/chat/`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt: currentInput, chat_id: activeChatId || null }),
                });
            }

            if (!res.ok) throw new Error(`Server Error ${res.status}`);
            const data = await res.json();

            if (data.error) throw new Error(data.error);
            if (data.topology) setCurrentTopology(data.topology);

            const botReply = data.cli || data.reply || "⚠️ Tidak ada balasan.";

            setChats((prev) =>
                prev.map((c) =>
                    c.id === String(data.chat_id || activeChatId)
                        ? { ...c, messages: [...(c.messages || []), { role: "bot", text: botReply }] }
                        : c
                )
            );

            if (/ip address|interface|system-view|vlan|set|add|undo|enable|cli/i.test(botReply)) {
                setPendingConfig(botReply);
                setShowConfirmPopup(true);
            }

        } catch (error) {
            console.error("Error handleSend:", error);
            setChats((prev) =>
                prev.map((c) =>
                    c.id === activeChatId
                        ? { ...c, messages: [...(c.messages || []), { role: "bot", text: `❌ Error: ${error.message}` }] }
                        : c
                )
            );
        } finally {
            setIsThinking(false);
        }
    };

    const filteredChats = chats.filter((chat) =>
        chat.title.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="flex h-screen bg-gray-50 text-gray-800 overflow-hidden relative">
            <Sidebar
                isSidebarOpen={isSidebarOpen}
                setIsSidebarOpen={setIsSidebarOpen}
                chats={filteredChats}
                activeChatId={activeChatId}
                setActiveChatId={setActiveChatId}
                handleNewChat={handleNewChat}
                search={search}
                setSearch={setSearch}
                editingIndex={editingIndex}
                setEditingIndex={setEditingIndex}
                newName={newName}
                setNewName={setNewName}
                handleRename={handleRename}
                handleDelete={handleDelete}
                setShowGraph={setShowGraph}
                onOpenHistory={handleOpenHistory}
                networkUsers={networkUsers}
            />

            <main className={`flex flex-col flex-1 transition-all duration-300 ${isSidebarOpen ? "ml-72" : "ml-0"}`}>
                <ChatWindow
                    activeChat={activeChat}
                    isThinking={isThinking}
                    BASE_URL={BASE_URL}
                    handleNewChat={handleNewChat}
                    showConfirmPopup={showConfirmPopup}
                    pendingConfig={pendingConfig}
                    handleApproveConfig={handleApproveConfig} 
                    handleRejectConfig={handleRejectConfig}
                    showGraph={showGraph}
                    setShowGraph={setShowGraph}
                    showHistory={showHistory}
                    setShowHistory={setShowHistory}
                    configHistory={configHistory}
                    currentTopology={currentTopology}
                    isExecuting={isExecuting} 
                >
                    <MessageInput
                        input={input}
                        setInput={setInput}
                        handleSend={handleSend}
                        fileInputRef={fileInputRef}
                        setSelectedImage={setSelectedImage}
                        setPreviewUrl={setPreviewUrl}
                        previewUrl={previewUrl}
                    />
                </ChatWindow>
                {showHistory && <HistoryViewer configHistory={configHistory} setShowHistory={setShowHistory} />}
            </main>
        </div>
    );
}

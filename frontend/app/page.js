"use client";
/* eslint-disable react-hooks/exhaustive-deps */
import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import ChatWindow from "@/components/ChatWindow";
import MessageInput from "@/components/MessageInput";
import HistoryViewer from "@/components/HistoryViewer";

export default function Home() {
    const BASE_URL = "http://192.168.1.2:8000"; // Sesuaikan IP 

    // =========================================================================
    // SECTION 1: STATE MANAGEMENT
    // =========================================================================
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [search, setSearch] = useState("");
    const [editingIndex, setEditingIndex] = useState(null);
    const [newName, setNewName] = useState("");
    const [chats, setChats] = useState([]);
    const [selectedImage, setSelectedImage] = useState(null);
    const [activeChatId, setActiveChatId] = useState(null);
    const [input, setInput] = useState("");
    const [isThinking, setIsThinking] = useState(false);
    
    const [isExecuting, setIsExecuting] = useState(false); 
    const [pendingConfig, setPendingConfig] = useState(null);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    
    const [configHistory, setConfigHistory] = useState([]);
    const [showHistory, setShowHistory] = useState(false);
    const [previewUrl, setPreviewUrl] = useState(null);
    const fileInputRef = useRef(null);
    const [networkUsers, setNetworkUsers] = useState([]);

    const activeChat = chats.find((c) => c.id === activeChatId);

    // Fungsi Pembantu Fetch API
    const safeFetchJson = async (url, options = {}) => {
        try {
            const res = await fetch(url, options);
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`Server Error (${res.status}): ${errText.substring(0, 100)}...`);
            }
            const text = await res.text();
            if (!text) return null;
            return JSON.parse(text);
        } catch (err) {
            console.error("Fetch Error:", err);
            throw err;
        }
    };

    // Data Fetching
    const fetchNetworkUsers = async () => {
        try {
            const data = await safeFetchJson(`${BASE_URL}/api/network-devices/`); 
            if (Array.isArray(data)) setNetworkUsers(data);
        } catch (e) { console.error("Gagal load daftar user:", e); }
    };

    // Lifecycle untuk setiap kali sistem dimulai
    useEffect(() => {
        const fetchChats = async () => {
            try {
                const data = await safeFetchJson(`${BASE_URL}/api/chats/`);
                if (Array.isArray(data)) {
                    const formatted = data.map((c) => ({ id: String(c.id), title: c.title, messages: [] }));
                    setChats(formatted);
                    const savedChatId = localStorage.getItem("activeChatId");
                    if (savedChatId && formatted.some(c => c.id === savedChatId)) {
                        setActiveChatId(savedChatId);
                    } else if (formatted.length > 0 && !activeChatId) {
                        setActiveChatId(formatted[0].id);
                    }                
                }
            } catch (e) { console.error("Gagal load chat list:", e); }
        };
        fetchChats();
        fetchNetworkUsers();
        fetchConfigHistory(); 
    }, []);

    // Lifecycle setiap  user berpindah ruang chat
    useEffect(() => {
        if (!activeChatId) return;
        localStorage.setItem("activeChatId", activeChatId);
        const loadMessages = async () => {
            try {
                const data = await safeFetchJson(`${BASE_URL}/api/chats/${activeChatId}/messages/`);
                if (data && data.messages) {
                    setChats((prev) => prev.map((c) => c.id === activeChatId ? { ...c, messages: data.messages } : c));
                }
            } catch (err) { console.error("Gagal load pesan:", err); }
        };
        loadMessages();
    }, [activeChatId]);

    const fetchConfigHistory = async () => {
        try {
            const data = await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/`);
            if (Array.isArray(data)) setConfigHistory(data);
        } catch (error) { console.error("Error fetching history:", error); }
    };

    const handleOpenHistory = () => {
        fetchConfigHistory();
        setShowHistory(true);
    };

    // =========================================================================
    // MANAJEMEN CHAT 
    // =========================================================================
    
    // Membuat sesi chat baru
    const handleNewChat = useCallback(async () => {
        try {
            const data = await safeFetchJson(`${BASE_URL}/api/chats/create/`, { method: "POST" });
            if (data) {
                const newChat = { id: String(data.id), title: data.title, messages: [] };
                setChats((prev) => [...prev, newChat]);
                setActiveChatId(String(data.id));
            }
        } catch (err) { console.error("Gagal membuat chat:", err); }
    }, [setChats, setActiveChatId, BASE_URL]);

    // Mengganti nama judul chat
    const handleRename = (index) => {
        if (newName.trim() === "") return;
        const updated = [...chats];
        updated[index].title = newName;
        setChats(updated);
        setEditingIndex(null);
    };

    // Menghapus sesi chat
    const handleDelete = async (index) => {
        const chatIdToDelete = chats[index].id;
        try {
            await fetch(`${BASE_URL}/api/chats/${chatIdToDelete}/delete/`, { method: "DELETE" });
            const updated = chats.filter((_, i) => i !== index);
            setChats(updated);
            if (chatIdToDelete === activeChatId) {
                setActiveChatId(null); 
                localStorage.removeItem("activeChatId");
            }
        } catch (err) { console.error("Gagal hapus chat:", err); }
    };

    // =========================================================================
    // NETWORK AUTOMATION (Eksekusi Ansible)
    // =========================================================================
    
    // Fungsi untuk mengirim instruksi CLI ke endpoint eksekutor Ansible di Django
    const executeConfig = async (finalConfig) => {
        try {
            return await safeFetchJson(`${BASE_URL}/api/execute_config/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ chat_id: activeChatId, config_cli: finalConfig }),
            });
        } catch (e) { throw e; }
    };

    // Fungsi yang dijalankan ketika user menekan tombol "Setuju" pada Pop-up Konfigurasi
    const handleApproveConfig = async (editedConfig) => {
        if (!editedConfig) return;
        setIsExecuting(true);
        let executionSuccess = false;
        let outputMessage = "";

        try {
            const execResult = await executeConfig(editedConfig);

            if (execResult && execResult.results && execResult.results.length > 0) {
                const successList = execResult.results.filter(r => r.status === 'success');
                const failedList = execResult.results.filter(r => r.status !== 'success');

                const formatNames = (names) => {
                    if (names.length === 0) return "";
                    if (names.length === 1) return names[0];
                    if (names.length === 2) return `${names[0]} dan ${names[1]}`;
                    return `${names.slice(0, -1).join(", ")}, dan ${names[names.length - 1]}`;
                };

                const successNames = formatNames(successList.map(r => r.target));
                const failedNames = formatNames(failedList.map(r => r.target));
                const failedDetails = failedList.map(r => r.feedback).join('\n\n---\n\n');

                // Skenario 1: Semua Berhasil
                if (failedList.length === 0) {
                    outputMessage = `Konfigurasi berhasil diterapkan di perangkat **${successNames}**.`;
                    executionSuccess = true;
                } 
                // Skenario 2: Semua Gagal
                else if (successList.length === 0) {
                    outputMessage = `Konfigurasi gagal diterapkan pada semua perangkat (**${failedNames}**).\n\n${failedDetails}`;
                } 
                // Skenario 3: Sebagian Berhasil, Sebagian Gagal
                else {
                    outputMessage = `Konfigurasi berhasil diterapkan di perangkat **${successNames}**, sedangkan perangkat **${failedNames}** mengalami kegagalan.\n\n${failedDetails}`;
                }
            } else {
                outputMessage = "Eksekusi selesai tapi tidak ada respons detail dari server.";
            }

            // Menyimpan ke database
            await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/add/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                // Menyimpan pesan feedback lengkap ke riwayat
                body: JSON.stringify({ 
                    config: editedConfig, 
                    status: outputMessage 
                }),
            });

            // Simpan ke riwayat chat agar muncul di ChatWindow
            await safeFetchJson(`${BASE_URL}/api/chats/messages/save/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    chat_id: activeChatId, 
                    role: "assistant", 
                    content: outputMessage 
                }),
            });

            setChats((prev) => prev.map((c) => 
                c.id === activeChatId 
                ? { ...c, messages: [...(c.messages || []), { role: "bot", text: outputMessage }] } 
                : c
            ));

        } catch (error) {
            const errorMsg = `Terjadi kesalahan sistem saat memproses: ${error.message}`;
            setChats((prev) => prev.map((c) => 
                c.id === activeChatId 
                ? { ...c, messages: [...(c.messages || []), { role: "bot", text: errorMsg }] } 
                : c
            ));
        } finally {
            setPendingConfig(null);
            fetchConfigHistory();
            setIsExecuting(false);
            setShowConfirmPopup(false);
        }
    };

    // Fungsi yang dijalankan ketika user menekan tombol "Tolak" pada Pop-up Konfigurasi
    const handleRejectConfig = async () => {
        setShowConfirmPopup(false);
        if (!pendingConfig) return;
        const rejectMsg = " Konfigurasi dibatalkan oleh pengguna.";
        try {
            await safeFetchJson(`${BASE_URL}/api/riwayat-konfigurasi/add/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ config: pendingConfig, status: "Ditolak" }),
            });
            await safeFetchJson(`${BASE_URL}/api/chats/messages/save/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ chat_id: activeChatId, role: "assistant", content: rejectMsg }),
            });
            setChats((prev) => prev.map((c) => c.id === activeChatId ? { ...c, messages: [...(c.messages || []), { role: "bot", text: rejectMsg }] } : c));
        } catch (error) { console.error("Error reject:", error); } 
        finally {
            setPendingConfig(null);
            fetchConfigHistory();
        }
    };


    // =========================================================================
    // HANDLING PENGIRIMAN PESAN & LLM
    // =========================================================================
    
    const handleSend = async () => {
        if (!input.trim() && !selectedImage) return;
        
        const currentInput = input;
        const currentSelectedImage = selectedImage;
        const currentPreviewUrl = previewUrl;

        let userMessage;
        if (currentInput.trim() && currentSelectedImage) userMessage = { role: "user", text: currentInput.trim(), image: currentPreviewUrl };
        else if (currentInput.trim()) userMessage = { role: "user", text: currentInput.trim() };
        else if (currentSelectedImage) userMessage = { role: "user", image: currentPreviewUrl };

        if (userMessage) {
            setChats((prev) => prev.map((c) => c.id === activeChatId ? { ...c, messages: [...(c.messages || []), userMessage] } : c));
        }

        setInput("");
        setSelectedImage(null);
        setPreviewUrl(null);
        setIsThinking(true);

        try {
            let res;

            // Mengirim request ke Backend: Mode Gambar atau Teks
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

            // Mendapatkan balasan bot
            const botReply = data.cli || data.reply || "Tidak ada balasan.";

            // Memperbarui chat dengan balasan asisten LLM
            setChats((prev) => prev.map((c) => 
                c.id === String(data.chat_id || activeChatId) 
                    ? { 
                        ...c, 
                        title: data.title || c.title, 
                        messages: [...(c.messages || []), { role: "bot", text: botReply }] 
                      } 
                    : c
            ));

            // Jika bot berhasil menambah/menghapus perangkat dari database, refresh Sidebar
            if (botReply.includes("database") || botReply.includes("Berhasil") || botReply.includes("dihapus")) {
                fetchNetworkUsers(); 
            }


            // Jika sistem mendeteksi niat eksekusi akan muncul pop-up konfirmasi
            if (botReply.includes("Target:") && botReply.includes("Konfigurasi:")) {
                const cleanedConfigForPopup = botReply
                    .replace(/Execute this now\?/gi, "")
                    .trim();

                setPendingConfig(cleanedConfigForPopup);
                setShowConfirmPopup(true);
            }


        } catch (error) {
            setChats((prev) => prev.map((c) => c.id === activeChatId ? { ...c, messages: [...(c.messages || []), { role: "bot", text: `❌ Error: ${error.message}` }] } : c));
        } finally {
            setIsThinking(false);
        }
    };

    const filteredChats = chats.filter((chat) => chat.title.toLowerCase().includes(search.toLowerCase()));

    // =========================================================================
    // RENDER / UI
    // =========================================================================
    return (
        <div className="flex h-screen bg-gray-50 text-gray-800 overflow-x-auto relative">
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
                {showHistory && (
                    <HistoryViewer 
                        configHistory={configHistory} 
                        setShowHistory={setShowHistory} 
                        BASE_URL={BASE_URL}
                        refreshHistory={fetchConfigHistory}
                    />
                )}
            </main>
        </div>
    );
}

// src/components/ChatWindow.js
import React from "react";
import { FiPlus } from "react-icons/fi";
import ConfirmPopup from "@/components/ConfirmPopup";
import GraphViewer from "@/components/GraphViewer";
import HistoryViewer from "@/components/HistoryViewer";

// src/components/ChatWindow.js

// src/components/ChatWindow.js

const MessageBubble = ({ message, BASE_URL }) => {
    const isUser = message.role === "user";
    
    let imageUrl = null;

    if (message.image) {
        if (message.image.startsWith("data:") || message.image.startsWith("blob:")) {
            imageUrl = message.image;
        } 
        else if (message.image.startsWith("http")) {
            imageUrl = message.image;
        } 
        else {
            const cleanPath = message.image.startsWith("/") ? message.image : `/${message.image}`;

            imageUrl = `${BASE_URL}${cleanPath}`;
        }
    }

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`mx-4 my-2 p-3 rounded-2xl max-w-[75%] ${
                    isUser ? "bg-blue-500 text-white" : "bg-gray-200 text-gray-800"
                }`}
            >
                {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
                
                {imageUrl && (
                    <img
                        src={imageUrl}
                        alt="attachment"
                        className="rounded-xl mt-2 max-w-full border border-gray-300 bg-white"
                        onError={(e) => {
                            console.log("Gagal load gambar:", imageUrl); // Cek console kalau masih error
                            e.target.style.display = 'none';
                        }}
                    />
                )}
            </div>
        </div>
    );
};


export default function ChatWindow({
    activeChat,
    isThinking,
    BASE_URL,
    handleNewChat,
    showConfirmPopup,
    isExecuting,
    pendingConfig,
    handleApproveConfig,
    handleRejectConfig,
    showGraph,
    setShowGraph,
    showHistory,
    setShowHistory,
    configHistory,
    children,
    currentTopology,

}) {

    if (!activeChat) {
        return (
            <div className="flex flex-col justify-center items-center flex-1">
                <p className="text-gray-500 mb-6 text-lg">
                    Belum ada chat. Mulai obrolan baru dulu.
                </p>
                <button
                    onClick={handleNewChat}
                    className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-full transition"
                >
                    <FiPlus /> New Chat
                </button>
            </div>
        );
    }

    if (activeChat.messages.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center flex-1 text-center px-4">
                <h1 className="text-2xl font-bold mb-6 text-gray-800">
                    Asisten Jaringan
                </h1>
                <div className="w-full max-w-xl">
                    {children}
                </div>
            </div>
        );
    }


    return (
        <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {activeChat.messages.map((m, i) => (
                    <MessageBubble key={m.id || i} message={m} BASE_URL={BASE_URL} />
                ))}

                {isThinking && (
                    <div className="flex justify-start">
                        <div className="mx-15 my-4 px-4 py-2 bg-gray-200 text-gray-500 rounded-2xl animate-pulse">
                            Asisten mengetik...
                        </div>
                    </div>
                )}
            </div>

            <div className="pb-5 px-5 w-full max-w-3xl mx-auto">
                 {children}
            </div>
           
            {showConfirmPopup && (
                <ConfirmPopup
                    pendingConfig={pendingConfig}
                    handleApproveConfig={handleApproveConfig}
                    handleRejectConfig={handleRejectConfig}
                    isExecuting={isExecuting}
                />
            )}
            {showGraph && <GraphViewer setShowGraph={setShowGraph} topologyData={currentTopology} />}
            {showHistory && <HistoryViewer configHistory={configHistory} setShowHistory={setShowHistory} />}
        </>
    );
}

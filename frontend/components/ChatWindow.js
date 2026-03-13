import React, { useEffect, useRef } from "react";
import { FiPlus } from "react-icons/fi";
import ConfirmPopup from "@/components/ConfirmPopup";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";

// Mermaid Graph
const MermaidGraph = ({ chart }) => {
    const graphRef = useRef(null);

    useEffect(() => {
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
        if (graphRef.current) {
            const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
            mermaid.render(id, chart).then(({ svg }) => {
                if (graphRef.current) {
                    graphRef.current.innerHTML = svg;
                }
            }).catch(e => console.error("Mermaid Render Error:", e));
        }
    }, [chart]);

    return (
        <div 
            ref={graphRef} 
            className="flex justify-center bg-white p-4 rounded-xl my-3 border shadow-sm text-black w-full overflow-x-auto"
        />
    );
};

const MessageBubble = ({ message, BASE_URL }) => {
    const isUser = message.role === "user";
    let imageUrl = null;

    if (message.image) {
        if (message.image.startsWith("data:") || message.image.startsWith("blob:") || message.image.startsWith("http")) {
            imageUrl = message.image;
        } else {
            const cleanPath = message.image.startsWith("/") ? message.image : `/${message.image}`;
            imageUrl = `${BASE_URL}${cleanPath}`;
        }
    }

    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`mx-4 my-2 p-4 rounded-2xl max-w-[85%] ${
                    isUser ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-800 border border-gray-200"
                }`}
            >
                {/* Render Markdown, Tabel, dan Grafis Mermaid */}
                {message.text && (
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        className="prose prose-sm max-w-none text-current"
                        components={{
                            code({ node, inline, className, children, ...props }) {
                                const match = /language-(\w+)/.exec(className || "");
                                // Jika LLM memberikan tag mermaid, render sebagai grafis
                                if (!inline && match && match[1] === "mermaid") {
                                    return <MermaidGraph chart={String(children).replace(/\n$/, "")} />;
                                }
                                // Jika blok kode biasa (seperti CLI config)
                                return !inline ? (
                                    <pre className="bg-gray-900 text-green-400 p-3 rounded-xl overflow-x-auto mt-2">
                                        <code className={className} {...props}>
                                            {children}
                                        </code>
                                    </pre>
                                ) : (
                                    <code className="bg-gray-300 text-red-600 px-1 rounded font-mono text-xs" {...props}>
                                        {children}
                                    </code>
                                );
                            },
                        }}
                    >
                        {message.text}
                    </ReactMarkdown>
                )}
                
                {imageUrl && (
                    <img
                        src={imageUrl}
                        alt="attachment"
                        className="rounded-xl mt-3 max-w-full border border-gray-300 bg-white"
                        onError={(e) => { e.target.style.display = 'none'; }}
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
    children,
}) {

    if (!activeChat) {
        return (
            <div className="flex flex-col justify-center items-center flex-1">
                <p className="text-gray-500 mb-6 text-lg">Belum ada chat. Mulai obrolan baru dulu.</p>
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
                <h1 className="text-2xl font-bold mb-6 text-gray-800">Asisten Jaringan</h1>
                <div className="w-full max-w-xl">{children}</div>
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
                        <div className="mx-4 my-2 px-4 py-2 bg-gray-200 text-gray-500 rounded-2xl animate-pulse">
                            Memproses...
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
        </>
    );
}

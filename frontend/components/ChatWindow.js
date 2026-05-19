import React from "react";
import { FiPlus } from "react-icons/fi";
import ConfirmPopup from "@/components/ConfirmPopup";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";

// IMPORT DINAMIS: Ini adalah "Pelindung RAM" Anda
// Next.js akan mengabaikan komponen ini saat kompilasi awal
const MermaidGraph = dynamic(() => import("./MermaidGraph"), {
    ssr: false,
    loading: () => (
        <div className="flex justify-center bg-gray-50 p-4 rounded-xl my-3 border shadow-sm text-gray-400 text-sm animate-pulse">
            Menyiapkan modul visualisasi topologi...
        </div>
    )
});

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
                className={`mx-4 my-2 p-4 rounded-2xl max-w-[90%] sm:max-w-[85%] min-w-0 overflow-hidden ${
                    isUser ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-800 border border-gray-200"
                }`}
            >
                {message.text && (
                    <div className="prose prose-sm max-w-none text-current break-words whitespace-pre-wrap min-w-0 w-full">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                pre({ node, children, ...props }) {
                                    const hasMermaid = node.children?.[0]?.properties?.className?.includes("language-mermaid");
                                    
                                    if (hasMermaid) {
                                        return <div className="my-4">{children}</div>;
                                    }
                                    
                                    return (
                                        <pre className="bg-gray-900 text-green-400 p-3 rounded-xl overflow-x-auto max-w-full mt-2" {...props}>
                                            {children}
                                        </pre>
                                    );
                                },

                                code({ node, className, children, ...props }) {
                                    const match = /language-(\w+)/.exec(className || "");

                                    if (match && match[1] === "mermaid") {
                                        // Memanggil komponen MermaidGraph yang aman dari SSR
                                        return <MermaidGraph chart={String(children).replace(/\n$/, "")} />;
                                    }

                                    const isInline = !match; 
                                    if (isInline) {
                                        return (
                                            <code className="bg-gray-300 text-red-600 px-1 rounded font-mono text-xs" {...props}>
                                                {children}
                                            </code>
                                        );
                                    }

                                    return (
                                        <code className={className} {...props}>
                                            {children}
                                        </code>
                                    );
                                },
                            }}
                        >
                            {message.text}
                        </ReactMarkdown>
                    </div>
                )}
                
                {imageUrl && (
                    <img
                        src={imageUrl}
                        alt="attachment"
                        className="rounded-xl mt-3 max-w-[400px] w-auto h-auto border border-gray-300 bg-white object-contain"
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
            <div className="flex-1 overflow-y-auto overflow-x-hidden p-6">
                <div className="max-w-3xl mx-auto w-full flex flex-col space-y-4">
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

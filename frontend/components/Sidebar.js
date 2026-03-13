import React, { useState } from "react";
import { FiPlus, FiEdit2, FiTrash2, FiMenu, FiUser, FiChevronDown, FiChevronUp } from "react-icons/fi";

export default function Sidebar({
    isSidebarOpen,
    setIsSidebarOpen,
    chats,
    activeChatId,
    setActiveChatId,
    handleNewChat,
    search,
    setSearch,
    editingIndex,
    setEditingIndex,
    newName,
    setNewName,
    handleRename,
    handleDelete,
    onOpenHistory,
    networkUsers
}) {
    // State untuk mengontrol buka-tutup dropdown Perangkat Terdaftar
    const [isDeviceListOpen, setIsDeviceListOpen] = useState(false);

    if (!isSidebarOpen) {
        return (
            <div className="fixed top-4 left-4 flex flex-col items-center gap-3 z-30">
                <button onClick={() => setIsSidebarOpen(true)} className="p-2 bg-gray-200 hover:bg-gray-300 rounded-md shadow" title="Open sidebar">
                    <FiMenu size={18} />
                </button>
                <button onClick={handleNewChat} className="p-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md shadow" title="New chat">
                    <FiPlus size={18} />
                </button>
            </div>
        );
    }

    return (
        <>
            <button
                onClick={() => setIsSidebarOpen(false)}
                className="fixed top-4 left-72 p-2 rounded-md shadow-md bg-gray-200 hover:bg-gray-300 transition-all duration-300 z-30"
                title="Close sidebar"
            >
                <FiMenu size={18} />
            </button>

            <aside className="fixed top-0 left-0 h-full bg-white border-r border-gray-300 flex flex-col w-72 p-4 transition-all duration-300 ease-in-out z-20">
                <button
                    onClick={handleNewChat}
                    className="mb-4 flex items-center gap-2 hover:bg-gray-200 py-2 px-2 rounded text-sm font-medium transition"
                >
                    <FiPlus /> Obrolan Baru
                </button>

                <div className="mb-4">
                    <label htmlFor="search-chats" className="block mb-1 text-xs font-semibold text-gray-600">Cari Obrolan</label>
                    <input
                        id="search-chats"
                        type="text"
                        placeholder="Search..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                </div>

                <div className="mb-1 flex items-center gap-2 text-gray-600 text-sm font-semibold">
                    Riwayat
                </div>

                <nav className="overflow-y-auto flex-1 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 mb-4">
                    {chats.length > 0 ? (
                        chats.map((chat, i) => (
                            <div
                                key={chat.id}
                                onClick={() => setActiveChatId(String(chat.id))}
                                className={`group flex items-center justify-between px-3 py-2 mb-1 rounded text-sm cursor-pointer ${
                                    chat.id === activeChatId ? "bg-gray-200 font-semibold" : "hover:bg-gray-100"
                                }`}
                            >
                                {editingIndex === i ? (
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        onBlur={() => handleRename(i)}
                                        onKeyDown={(e) => e.key === "Enter" && handleRename(i)}
                                        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                                        autoFocus
                                    />
                                ) : (
                                    <>
                                        <span className="truncate flex-1">{chat.title}</span>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setEditingIndex(i);
                                                    setNewName(chat.title);
                                                }}
                                                className="p-1 text-gray-500 hover:text-blue-600"
                                            >
                                                <FiEdit2 size={14} />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDelete(i);
                                                }}
                                                className="p-1 text-gray-500 hover:text-red-600"
                                            >
                                                <FiTrash2 size={14} />
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        ))
                    ) : (
                        <p className="text-xs text-gray-400">Belum ada obrolan.</p>
                    )}
                </nav>

                <div className="mt-auto border-t border-gray-300 pt-3">
                    <button
                        onClick={onOpenHistory}
                        className="mb-3 w-full flex items-center gap-2 hover:bg-gray-200 px-3 py-2 rounded text-sm font-medium transition"
                    >
                        Riwayat Konfigurasi
                    </button>
                    
                    {/* Header Dropdown Interaktif */}
                    <div 
                        onClick={() => setIsDeviceListOpen(!isDeviceListOpen)}
                        className="mb-2 flex items-center justify-between text-gray-600 text-sm font-semibold cursor-pointer hover:text-blue-600 transition-colors p-1 rounded"
                    >
                        <div className="flex items-center gap-2">
                            <FiUser /> Perangkat Terdaftar
                        </div>
                        {isDeviceListOpen ? <FiChevronUp /> : <FiChevronDown />}
                    </div>

                    {/* Daftar Perangkat (Hanya Tampil Jika isDeviceListOpen === true) */}
                    {isDeviceListOpen && (
                        <div className="overflow-y-auto max-h-40 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 transition-all duration-300">
                            {networkUsers && networkUsers.length > 0 ? (
                                networkUsers.map((user, index) => (
                                    <div key={index} className="flex flex-col p-2 mb-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded text-xs transition-colors">
                                        <span className="font-bold text-gray-700">{user.name}</span>
                                        <div className="flex justify-between items-center mt-1">
                                            <span className="text-gray-500 uppercase text-[10px] font-bold tracking-wider">{user.device_category}</span>
                                            <span className="text-blue-600 font-mono">{user.ip_address}</span>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p className="text-xs text-gray-400 px-2 pb-2">Memuat / Tidak ada perangkat...</p>
                            )}
                        </div>
                    )}
                </div>
            </aside>
        </>
    );
}

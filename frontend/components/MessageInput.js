// src/components/MessageInput.js
import React from "react";
import { ArrowUpIcon, PlusIcon } from "lucide-react";

export default function MessageInput({
    input,
    setInput,
    handleSend,
    fileInputRef,
    setSelectedImage,
    setPreviewUrl,
    previewUrl,
}) {
    // Fungsi untuk menangani perubahan file input
    const handleFileInputChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setSelectedImage(file);
        setPreviewUrl(URL.createObjectURL(file));
    };

    // Fungsi menghapus gambar
    const handleRemoveImage = () => {
        setSelectedImage(null);
        setPreviewUrl(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = ""; 
        }
    };

    return (
        <div className="w-full">
            {previewUrl && (
                <div className="px-1 pb-2 flex items-center gap-3">
                    <div className="relative w-24 h-24">
                        <img
                            src={previewUrl}
                            alt="preview"
                            className="w-full h-full object-cover rounded-xl border"
                        />
                        <button
                            className="absolute top-0 right-0 transform translate-x-1/2 -translate-y-1/2 
                                        bg-red-600 text-white rounded-full w-5 h-5 
                                        flex items-center justify-center text-xs font-bold shadow-md 
                                        hover:bg-red-700 transition duration-150"
                            onClick={handleRemoveImage}
                            aria-label="Hapus Gambar"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}

            {/* Input Utama */}
            <div className="w-full rounded-full flex justify-between gap-2 border border-gray-300 bg-white shadow-sm focus-within:ring-2 focus-within:ring-blue-500 px-3 py-2">
                {/* Upload Button */}
                <button
                    type="button"
                    onClick={() => fileInputRef.current.click()}
                    className="p-2 rounded-full hover:bg-gray-100 flex justify-center items-center"
                >
                    <PlusIcon />
                </button>
        
                {/* Hidden file input */}
                <input
                    type="file"
                    accept="image/*"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileInputChange}
                    onClick={(e) => e.target.value = null}
                />

                <textarea
                    placeholder="Mau konfig apa hari ini?"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onInput={(e) => {
                        e.target.style.height = "auto";
                        e.target.style.height = `${e.target.scrollHeight}px`;
                    }}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                    rows={1}
                    style={{ maxHeight: "72px", overflowY: "auto" }}
                    className="flex-1 resize-none overflow-hidden bg-transparent outline-none px-1 py-2 text-gray-700"
                ></textarea>

                {/* Send Icon*/}
                <button
                    onClick={handleSend}
                    type="button"
                    disabled={!input.trim() && !previewUrl}
                    className="p-2 rounded-full hover:bg-gray-100 flex items-center gap-1 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Send <ArrowUpIcon className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}

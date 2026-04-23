// src/components/ConfirmPopup.js
import React, { useState, useEffect } from "react";
import { FiLoader, FiCheck, FiX } from "react-icons/fi";

export default function ConfirmPopup({ 
    pendingConfig, 
    handleApproveConfig, 
    handleRejectConfig, 
    isExecuting 
}) {
    const [editedConfig, setEditedConfig] = useState(pendingConfig);

    useEffect(() => {
        setEditedConfig(pendingConfig);
    }, [pendingConfig]);

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* Header */}
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                    <h3 className="text-lg font-bold text-gray-800">
                        Konfirmasi Konfigurasi
                    </h3>
                    <div className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-md font-medium">
                        Dapat Diedit
                    </div>
                </div>

                {/* Body (Textarea) */}
                <div className="p-6 flex-1 overflow-y-auto">
                    <p className="text-sm text-gray-500 mb-3">
                        Silakan periksa dan koreksi konfigurasi sebelum dijalankan ke perangkat.
                    </p>
                    <textarea
                        value={editedConfig}
                        onChange={(e) => setEditedConfig(e.target.value)}
                        disabled={isExecuting}
                        className={`w-full h-64 p-4 font-mono text-sm bg-gray-900 text-green-400 rounded-xl border-2 focus:outline-none resize-none transition-all ${
                            isExecuting ? "opacity-50 cursor-not-allowed border-gray-300" : "border-gray-200 focus:border-blue-500 shadow-inner"
                        }`}
                        spellCheck="false"
                    />
                </div>

                {/* Footer Buttons */}
                <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
                    <button
                        onClick={handleRejectConfig}
                        disabled={isExecuting}
                        className="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-200 hover:text-red-600 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        <FiX className="w-4 h-4" /> Batal
                    </button>
                    
                    <button
                        onClick={() => handleApproveConfig(editedConfig)}
                        disabled={isExecuting}
                        className={`px-5 py-2.5 rounded-xl text-sm font-medium text-white shadow-lg transition flex items-center gap-2 ${
                            isExecuting 
                            ? "bg-blue-400 cursor-wait" 
                            : "bg-blue-600 hover:bg-blue-700 hover:shadow-blue-500/30 transform hover:-translate-y-0.5"
                        }`}
                    >
                        {isExecuting ? (
                            <>
                                <FiLoader className="animate-spin w-4 h-4" /> Memproses...
                            </>
                        ) : (
                            <>
                                <FiCheck className="w-4 h-4" /> Jalankan Konfigurasi
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

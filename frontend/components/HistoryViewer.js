import React, { useState } from "react";
import { FiTrash2, FiX } from "react-icons/fi";

export default function HistoryViewer({ configHistory, setShowHistory, BASE_URL, refreshHistory }) {
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [confirmText, setConfirmText] = useState("");
    const [isDeleting, setIsDeleting] = useState(false);

    const requiredText = "hapus riwayat konfigurasi";
    const isMatch = confirmText === requiredText;

    const executeDelete = async () => {
        if (!isMatch) return;
        setIsDeleting(true);
        try {
            const endpoint = deleteTarget === "all" 
                ? `${BASE_URL}/api/riwayat-konfigurasi/delete-all/`
                : `${BASE_URL}/api/riwayat-konfigurasi/${deleteTarget}/delete/`;

            await fetch(endpoint, { method: "DELETE" });
            
            refreshHistory(); 
            setDeleteTarget(null); 
            setConfirmText(""); 
        } catch (error) {
            console.error("Gagal menghapus riwayat:", error);
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex justify-center items-center z-50 p-4">
            <div className="bg-white w-full max-w-4xl max-h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden relative">
                
                <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center shrink-0">
                    <h2 className="text-lg font-bold text-gray-800">Riwayat Konfigurasi</h2>
                    <div className="flex items-center gap-3">
                        {configHistory.length > 0 && (
                            <button
                                onClick={() => setDeleteTarget("all")}
                                className="bg-red-100 text-red-600 hover:bg-red-200 px-3 py-1.5 rounded-lg text-sm font-medium transition flex items-center gap-1"
                            >
                                <FiTrash2 /> Hapus Semua
                            </button>
                        )}
                        <button
                            onClick={() => setShowHistory(false)}
                            className="bg-gray-200 text-gray-600 hover:bg-gray-300 hover:text-red-500 p-1.5 rounded-lg transition"
                        >
                            <FiX className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                <div className="p-6 flex-1 overflow-y-auto bg-white">
                    {configHistory.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400">
                            <p>Belum ada riwayat konfigurasi.</p>
                        </div>
                    ) : (
                        <table className="w-full text-sm border-collapse">
                            <thead>
                                <tr className="bg-gray-100 text-left text-gray-600">
                                    <th className="border-b-2 border-gray-200 p-3 font-semibold">Waktu</th>
                                    <th className="border-b-2 border-gray-200 p-3 font-semibold w-1/2">Konfigurasi</th>
                                    <th className="border-b-2 border-gray-200 p-3 font-semibold">Status</th>
                                    <th className="border-b-2 border-gray-200 p-3 font-semibold text-center">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                {configHistory.map((item, i) => (
                                    <tr key={item.id || i} className="hover:bg-gray-50 border-b border-gray-100 transition">
                                        <td className="p-3 align-top whitespace-nowrap text-gray-600">
                                            {new Date(item.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}
                                        </td>
                                        <td className="p-3 align-top text-xs font-mono bg-gray-50 whitespace-pre-wrap text-gray-700">
                                            {item.config}
                                        </td>
                                        <td className="p-3 align-top font-medium">
                                            {item.status === "Berhasil" || item.status === "Disetujui" ? (
                                                <span className="bg-green-100 text-green-700 px-2 py-1 rounded-md text-xs">{item.status}</span>
                                            ) : (
                                                <span className="bg-red-100 text-red-700 px-2 py-1 rounded-md text-xs">{item.status}</span>
                                            )}
                                        </td>
                                        <td className="p-3 align-top text-center">
                                            <button
                                                onClick={() => setDeleteTarget(item.id)}
                                                className="text-gray-400 hover:text-red-500 transition"
                                                title="Hapus riwayat ini"
                                            >
                                                <FiTrash2 className="w-4 h-4 mx-auto" />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>

            {/* ========================================================= */}
            {/* POP-UP KONFIRMASI HAPUS  */}
            {/* ========================================================= */}
            {deleteTarget && (
                <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
                        <h3 className="text-xl font-bold text-red-600 mb-2 flex items-center gap-2">
                            <FiTrash2 /> Konfirmasi Penghapusan
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Tindakan ini permanen. Untuk melanjutkan, silakan ketik kalimat di bawah ini:
                            <br/>
                            <span className="font-mono bg-gray-100 px-2 py-1 rounded font-bold text-gray-800 inline-block mt-2">
                                {requiredText}
                            </span>
                        </p>
                        
                        <input
                            type="text"
                            value={confirmText}
                            onChange={(e) => setConfirmText(e.target.value)}
                            placeholder={requiredText}
                            className="w-full border-2 border-gray-300 rounded-lg p-2.5 mb-5 focus:outline-none focus:border-red-500 transition font-mono text-sm"
                            autoComplete="off"
                        />

                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => { setDeleteTarget(null); setConfirmText(""); }}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg font-medium transition"
                            >
                                Batal
                            </button>
                            <button
                                onClick={executeDelete}
                                disabled={!isMatch || isDeleting}
                                className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                                    isMatch && !isDeleting
                                    ? "bg-red-600 text-white hover:bg-red-700" 
                                    : "bg-red-200 text-red-400 cursor-not-allowed"
                                }`}
                            >
                                {isDeleting ? "Menghapus..." : "Hapus Permanen"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

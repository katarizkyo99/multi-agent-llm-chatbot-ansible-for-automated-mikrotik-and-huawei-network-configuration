// src/components/HistoryViewer.js
import React from "react";

export default function HistoryViewer({ configHistory, setShowHistory }) {
    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50">
            <div className="bg-white w-[600px] h-[500px] rounded-xl shadow-xl relative p-4 overflow-y-auto">
                {/* CLOSE BUTTON */}
                <button
                    onClick={() => setShowHistory(false)}
                    className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded"
                >
                    X
                </button>

                <h2 className="text-lg font-semibold mb-4">Riwayat Konfigurasi</h2>

                {configHistory.length === 0 ? (
                    <p className="text-gray-500 text-sm">Belum ada riwayat konfigurasi.</p>
                ) : (
                    <table className="w-full text-sm border-collapse">
                        <thead>
                            <tr className="bg-gray-100">
                                <th className="border p-2">Konfigurasi</th>
                                <th className="border p-2">Status</th>
                                <th className="border p-2">Waktu</th>
                            </tr>
                        </thead>
                        <tbody>
                            {configHistory.map((item, i) => (
                                <tr key={i} className="hover:bg-gray-50">
                                    <td className="border p-2 whitespace-pre-wrap">{item.config}</td>
                                    <td className="border p-2 font-semibold">
                                        {item.status === "Disetujui" ? (
                                            <span className="text-green-600">{item.status}</span>
                                        ) : (
                                            <span className="text-red-600">{item.status}</span>
                                        )}
                                    </td>
                                    <td className="border p-2">
                                        {new Date(item.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}

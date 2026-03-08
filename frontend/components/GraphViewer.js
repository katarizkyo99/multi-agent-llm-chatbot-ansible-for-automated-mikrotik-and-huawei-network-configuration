// frontend/components/GraphViewer.js
import React from "react";
import NodeGraph from "@/components/NodeGraph"; 

export default function GraphViewer({ setShowGraph, topologyData }) {
    return (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50">
            <div className="bg-white w-[800px] h-[600px] rounded-xl shadow-xl relative p-2">
                <button
                    onClick={() => setShowGraph(false)}
                    className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded z-50 hover:bg-red-600"
                >
                    Close
                </button>

                <NodeGraph topologyData={topologyData} />
            </div>
        </div>
    );
}

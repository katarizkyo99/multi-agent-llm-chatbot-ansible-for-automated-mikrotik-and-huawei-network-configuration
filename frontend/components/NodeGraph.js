"use client";

import React, { useEffect, useCallback } from "react";
import ReactFlow, { 
  Background, 
  Controls, 
  useNodesState, 
  useEdgesState,
  MarkerType
} from "reactflow";
import "reactflow/dist/style.css";

const cleanId = (id) => String(id).replace(/\s+/g, '_').toLowerCase();

export default function NodeGraph({ topologyData }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const processTopology = useCallback(() => {
    if (!topologyData) return;

    console.log("🛠️ NodeGraph menerima data:", topologyData);

    // Mengambil Data
    const devices = topologyData.devices || topologyData.nodes || [];
    const connections = topologyData.connections || topologyData.links || [];

    // Membuat Nodes
    const newNodes = devices.map((dev, index) => {
      const x = 100 + (index * 250); 
      const y = 200 + (index % 2 === 0 ? 0 : 100); // Zigzag dikit biar ga lurus kaku

      const safeId = cleanId(dev.id);

      return {
        id: safeId, 
        position: { x, y },
        data: { label: dev.label || dev.id },
        style: {
          background: dev.type?.toLowerCase().includes("router") ? "#E3F2FD" : "#F3E5F5",
          border: dev.type?.toLowerCase().includes("router") ? "2px solid #2196F3" : "2px solid #9C27B0",
          borderRadius: "8px",
          padding: "10px",
          fontWeight: "bold",
          fontSize: "12px",
          width: 150,
          textAlign: "center",
          color: "#333"
        },
      };
    });

    // Membuat Koneksi Nodes
    const newEdges = connections.map((conn, i) => {
      const sourceId = cleanId(conn.source);
      const targetId = cleanId(conn.target);

      return {
        id: `edge-${i}`,
        source: sourceId,
        target: targetId,
        label: conn.label || "", 
        type: 'smoothstep', 
        animated: true,
        style: { stroke: "#555", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed },
      };
    });

    setNodes(newNodes);
    setEdges(newEdges);
    
    console.log("Nodes created:", newNodes);
    console.log("Edges created:", newEdges);

  }, [topologyData, setNodes, setEdges]);

  useEffect(() => {
    processTopology();
  }, [topologyData, processTopology]);

  if (!topologyData) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <p>Data topologi kosong.</p>
        <small>Silakan chat bot untuk generate topologi.</small>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", minHeight: "400px", background: "#fff" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView 
      >
        <Background gap={20} color="#e0e0e0" />
        <Controls />
      </ReactFlow>
    </div>
  );
}

import React, { useEffect, useRef, useState } from "react";

const MermaidGraph = ({ chart }) => {
    const graphRef = useRef(null);
    const [hasError, setHasError] = useState(false); 
    useEffect(() => {
        const renderGraph = async () => {
            try {
                const mermaid = (await import("mermaid")).default;                
                mermaid.initialize({ startOnLoad: false, theme: 'neutral' });                
                const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;               
                const { svg } = await mermaid.render(id, chart);
                if (graphRef.current) {
                    graphRef.current.innerHTML = svg;
                }
            } catch (error) {
                console.error("Mermaid Render Error:", error);
                setHasError(true); 
            }
        };
        if (chart) {
            setHasError(false); 
            renderGraph();
        }
    }, [chart]);

    if (hasError) {
        return (
            <div className="bg-red-50 text-red-600 p-4 rounded-xl my-3 border border-red-200 text-sm overflow-x-auto">
                <p className="font-bold mb-2"> Gagal menggambar topologi (Format Mermaid Tidak Valid):</p>
                <pre className="text-xs bg-red-100 p-2 rounded">{chart}</pre>
            </div>
        );
    }

    return (
        <div 
            ref={graphRef} 
            className="flex justify-center bg-white p-4 rounded-xl my-3 border shadow-sm text-black max-w-[600px] overflow-x-auto [&>svg]:max-w-full [&>svg]:h-auto"
        >
            <span className="text-gray-400 text-sm animate-pulse">Menggambar topologi...</span>
        </div>
    );
};

export default MermaidGraph;

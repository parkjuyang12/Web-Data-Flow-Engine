import React, { useState } from 'react';
import Cytoscape from 'cytoscape';
import './App.css';

function App() {
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [url, setUrl] = useState('');

  const handleFetch = () => {
    fetch(`http://localhost:5001/api/fetch-html?url=${encodeURIComponent(url)}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data) => {
        console.log('Received data:', data);

        if (!data.parsed_tree) {
          console.error('Invalid data structure:', data);
          return;
        }

        const { nodes, edges } = extractNodesAndEdges(data.parsed_tree);

        const elements = [
          ...nodes.map((node) => ({
            data: {
              id: node.id,
              label: node.label,
            },
          })),
          ...edges.map((edge) => ({
            data: {
              id: edge.id,
              source: edge.source,
              target: edge.target,
              label: edge.label,
            },
          })),
        ];

        setData({ nodes, edges });
        renderCytoscape(elements);
      })
      .catch((error) => console.error('Error:', error));
  };

  const extractNodesAndEdges = (tree) => {
    const nodes = [];
    const edges = [];
    const idMap = new Map();

    const traverse = (node, parentId = null) => {
      if (!node) return;

      const nodeId = `node-${Math.random().toString(36).substr(2, 9)}`;
      idMap.set(node, nodeId);

      nodes.push({
        id: nodeId,
        label: node.tag || 'Unknown',
      });

      if (parentId) {
        edges.push({
          id: `edge-${Math.random().toString(36).substr(2, 9)}`,
          source: parentId,
          target: nodeId,
          label: `Parent of ${node.tag || 'Unknown'}`,
        });
      }

      if (Array.isArray(node.children)) {
        node.children.forEach((child) => traverse(child, nodeId));
      }
    };

    traverse(tree);

    return { nodes, edges };
  };

  const renderCytoscape = (elements) => {
    Cytoscape({
      container: document.getElementById('cy'),
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#666',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'width': '50px',
            'height': '50px',
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'target-arrow-shape': 'triangle',
            'line-color': '#ddd',
            'target-arrow-color': '#ddd',
            'label': 'data(label)',
            'font-size': '8px',
          },
        },
      ],
      layout: {
        name: 'cose',
        nodeSpacing: 50,
        edgeLength: 100,
        animate: true,
      },
    });
  };
  

  return (
    <div className="App">
      <header className="App-header">
        <h1>Web Data Flow Engine</h1>
      </header>
      <main className="App-main">
        <div className="InputContainer">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter URL"
          />
          <button onClick={handleFetch}>Fetch Data</button>
        </div>
        <div id="cy"></div>
      </main>
    </div>
  );
}

export default App;

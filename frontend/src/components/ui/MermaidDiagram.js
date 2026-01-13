import React, { useEffect, useRef, useId } from 'react';
import mermaid from 'mermaid';

/**
 * MermaidDiagram - A reusable component for rendering Mermaid diagrams
 *
 * Features:
 * - Automatic theme switching (dark/light mode support)
 * - Unique IDs for multiple diagrams on one page
 * - Re-renders when chart definition or theme changes
 * - Custom theme variables that match the app's design system
 *
 * @param {string} chart - The Mermaid diagram definition
 * @param {boolean} isDarkTheme - Whether dark theme is active
 */
const MermaidDiagram = ({ chart, isDarkTheme }) => {
  const containerRef = useRef(null);
  const uniqueId = useId().replace(/:/g, '-');

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current || !chart) return;

      // Configure mermaid with theme-aware settings
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        themeVariables: isDarkTheme ? {
          // Dark theme - matches app's dark mode colors
          primaryColor: '#3b82f6',
          primaryTextColor: '#f8fafc',
          primaryBorderColor: '#3b4a63',
          lineColor: '#64748b',
          secondaryColor: '#2f3e4e',
          tertiaryColor: '#273444',
          background: '#273444',
          mainBkg: '#273444',
          secondBkg: '#2f3e4e',
          nodeTextColor: '#f8fafc',
          textColor: '#f8fafc',
          titleColor: '#f8fafc',
          edgeLabelBackground: '#273444',
          clusterBkg: '#2f3e4e',
          clusterBorder: '#3b4a63',
          // Flowchart specific
          nodeBorder: '#3b4a63',
          nodeBkg: '#273444',
        } : {
          // Light theme - matches app's light mode colors
          primaryColor: '#2563eb',
          primaryTextColor: '#1e293b',
          primaryBorderColor: '#e2e8f0',
          lineColor: '#64748b',
          secondaryColor: '#f1f5f9',
          tertiaryColor: '#ffffff',
          background: '#ffffff',
          mainBkg: '#ffffff',
          secondBkg: '#f8fafc',
          nodeTextColor: '#1e293b',
          textColor: '#1e293b',
          titleColor: '#1e293b',
          edgeLabelBackground: '#ffffff',
          clusterBkg: '#f8fafc',
          clusterBorder: '#e2e8f0',
          // Flowchart specific
          nodeBorder: '#e2e8f0',
          nodeBkg: '#ffffff',
        },
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: 'basis',
          nodeSpacing: 50,
          rankSpacing: 80,
        },
        securityLevel: 'loose', // Allow HTML in labels for richer formatting
        logLevel: 'error',
      });

      // Clear previous content
      containerRef.current.innerHTML = '';

      try {
        const { svg } = await mermaid.render(`mermaid-${uniqueId}`, chart);
        containerRef.current.innerHTML = svg;

        // Make SVG responsive
        const svgElement = containerRef.current.querySelector('svg');
        if (svgElement) {
          svgElement.style.maxWidth = '100%';
          svgElement.style.height = 'auto';

          // Add padding to cluster labels for better readability
          const clusterLabels = svgElement.querySelectorAll('.cluster-label foreignObject div');
          clusterLabels.forEach(label => {
            label.style.paddingTop = '6px';
            label.style.paddingBottom = '8px';
          });
        }
      } catch (error) {
        console.error('Mermaid rendering error:', error);
        containerRef.current.innerHTML = `
          <div style="
            padding: 1rem;
            background-color: var(--badge-red-bg);
            border: 1px solid var(--badge-red-border);
            border-radius: 0.5rem;
            color: var(--badge-red-text);
          ">
            <strong>Diagram Error:</strong> ${error.message}
          </div>
        `;
      }
    };

    renderDiagram();
  }, [chart, isDarkTheme, uniqueId]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'auto',
        padding: '1rem 0',
      }}
    />
  );
};

export default MermaidDiagram;

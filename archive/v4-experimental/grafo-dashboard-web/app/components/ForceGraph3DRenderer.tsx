"use client";

/**
 * ForceGraph3DRenderer — Internal multidimensional rendering component (2D/3D)
 *
 * This component is imported ONLY via next/dynamic with ssr: false.
 * Never import directly — use the GrafoUniverse wrapper.
 *
 * Slice Front-5: Enterprise UX & Multidimensional Navigation
 * - Dynamic switching between 3D (ForceGraph3D) and 2D (ForceGraph2D) engines
 * - Strict conditional rendering with inactive canvas discardal
 * - Data, colors, opacities, and D3 simulation sharing
 * - Click (Inspection) vs double click (Camera flight Fly-to-Node) logic
 */

import { useCallback, useRef, useMemo, useEffect, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphData, ForceGraphNode } from "@/lib/graph/types";
import { NODE_TYPE_COLORS } from "@/lib/graph/types";
import * as THREE from "three";

// ─── Constants ──────────────────────────────────────────────────────────────

const BG_COLOR = "#161b22"; // Elegant Graphite/Slate
const LINK_COLOR_DEFAULT = "rgba(156, 163, 175, 0.12)"; // Translucent pastel gray
const LINK_HOVER_COLOR = "#fdba74"; // Pastel Peach (desaturated from orange branding)

// ─── Pre-rendered Textures (GPU Cache - 3D) ───────────────────────────

const TEXTURE_CACHE: Record<string, THREE.CanvasTexture> = {};

function getCachedTexture(type: string, isHovered: boolean): THREE.CanvasTexture {
  const key = `${type}_${isHovered}`;
  if (!TEXTURE_CACHE[key]) {
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d")!;

    ctx.clearRect(0, 0, 64, 64);
    const color = NODE_TYPE_COLORS[type] ?? NODE_TYPE_COLORS.DEFAULT;

    const grad = ctx.createRadialGradient(32, 32, 2, 32, 32, 30);
    grad.addColorStop(0, isHovered ? color : `${color}38`);
    grad.addColorStop(0.4, isHovered ? `${color}22` : `${color}0c`);
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(32, 32, 30, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = isHovered ? "#ffffff" : color;
    ctx.beginPath();
    ctx.arc(32, 32, isHovered ? 12 : 8, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = isHovered ? color : "#161b22";
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    let glyph = "";
    if (type === "FACT") glyph = "🧠";
    else if (type === "MODULE") glyph = "📦";
    else if (type === "CLASS") glyph = "Ⓒ";
    else if (type === "METHOD") glyph = "Ⓜ";
    else if (type === "FUNCTION") glyph = "Ⓕ";
    else glyph = "•";

    ctx.fillText(glyph, 32, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    TEXTURE_CACHE[key] = texture;
  }
  return TEXTURE_CACHE[key];
}

// ─── Props ──────────────────────────────────────────────────────────────────

interface ForceGraph3DRendererProps {
  graphData: ForceGraphData;
  width: number;
  height: number;
  dimensionMode: "2D" | "3D";
  onNodeHover: (node: ForceGraphNode | null) => void;
  onNodeClick: (node: ForceGraphNode | null) => void;
}

// ─── Component ──────────────────────────────────────────────────────────────

type ZoomLevel = "near" | "medium" | "far";

export default function ForceGraph3DRenderer({
  graphData,
  width,
  height,
  dimensionMode,
  onNodeHover,
  onNodeClick,
}: ForceGraph3DRendererProps) {
  const fgRef = useRef<any>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  // Dynamic Optimization States
  const [isPointerEnabled, setIsPointerEnabled] = useState(true);
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>("medium");

  useEffect(() => {
    console.log("[ForceGraph Renderer] isPointerEnabled =", isPointerEnabled, "| zoomLevel =", zoomLevel, "| dimensionMode =", dimensionMode);
  }, [isPointerEnabled, zoomLevel, dimensionMode]);

  const cameraTimerRef = useRef<NodeJS.Timeout | null>(null);
  const zoomThrottleRef = useRef<NodeJS.Timeout | null>(null);
  const clickTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isUserInteractingRef = useRef(false);
  const hasMovedCameraRef = useRef(false);
  const lastClickedNodeIdRef = useRef<number | null>(null);

  // ─── Node appearance (3D) ──────────────────────────────────────────────

  const nodeThreeObject = useCallback(
    (node: ForceGraphNode) => {
      const isHovered = hoveredNodeId === node.id;
      const texture = getCachedTexture(node.node_type, isHovered);
      const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        depthWrite: false,
      });
      const sprite = new THREE.Sprite(material);

      const baseScale = node.val || 8;
      const scale = isHovered ? baseScale * 1.8 : baseScale;
      sprite.scale.set(scale, scale, 1);

      return sprite;
    },
    [hoveredNodeId]
  );

  // ─── Node appearance (2D Canvas) ───────────────────────────────────────

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isHovered = hoveredNodeId === node.id;
      const color = NODE_TYPE_COLORS[node.node_type] ?? NODE_TYPE_COLORS.DEFAULT;
      const radius = Math.cbrt(node.val || 8) * 1.6;

      // Guarantees a minimum physical size (3px radius / 6px screen diameter) so the node does not disappear
      const minVisibleRadius = 3.0;
      const renderRadius = Math.max(radius, minVisibleRadius / globalScale);

      ctx.save();

      // Advanced Canvas Semantic Zoom Optimization:
      // 1. Far zoom (globalScale < 0.6): simple points only
      // 2. Medium zoom (0.6 <= globalScale < 1.5): glyphs only for major nodes (val >= 12), simple points for the rest
      const isMajorNode = (node.val || 8) >= 12;
      const shouldDrawSimple = globalScale < 0.6 || (globalScale < 1.5 && !isMajorNode);

      if (shouldDrawSimple) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, isHovered ? renderRadius * 1.35 : renderRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        return;
      }

      ctx.shadowColor = color;
      ctx.shadowBlur = isHovered ? 12 : 4;
      ctx.fillStyle = isHovered ? "#ffffff" : color;

      ctx.beginPath();
      ctx.arc(node.x, node.y, isHovered ? radius * 1.35 : radius, 0, Math.PI * 2);
      ctx.fill();

      // Draw internal icon
      ctx.shadowBlur = 0;
      ctx.fillStyle = isHovered ? color : "#161b22";
      ctx.font = `bold ${radius * 1.0}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      let glyph = "";
      if (node.node_type === "FACT") glyph = "🧠";
      else if (node.node_type === "MODULE") glyph = "📦";
      else if (node.node_type === "CLASS") glyph = "Ⓒ";
      else if (node.node_type === "METHOD") glyph = "Ⓜ";
      else if (node.node_type === "FUNCTION") glyph = "Ⓕ";
      else glyph = "•";

      ctx.fillText(glyph, node.x, node.y);
      ctx.restore();
    },
    [hoveredNodeId]
  );

  // ─── Camera Movement & Zoom Interception ──────────────────────

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;

    const setupListeners = () => {
      const controls = dimensionMode === "3D" ? fg.controls() : null;
      const camera = dimensionMode === "3D" ? fg.camera() : null;

      // 1. Mouse zoom speed in 3D
      if (controls && camera) {
        controls.zoomSpeed = 0.35;

        const handleStart = () => {
          isUserInteractingRef.current = true;
          hasMovedCameraRef.current = false;
          if (cameraTimerRef.current) {
            clearTimeout(cameraTimerRef.current);
            cameraTimerRef.current = null;
          }
        };

        const handleEnd = () => {
          isUserInteractingRef.current = false;
          if (cameraTimerRef.current) {
            clearTimeout(cameraTimerRef.current);
          }
          if (hasMovedCameraRef.current) {
            cameraTimerRef.current = setTimeout(() => {
              setIsPointerEnabled(true);
            }, 250);
          }
          hasMovedCameraRef.current = false;
        };

        const handleCameraChange = () => {
          // Disable raycasting ONLY when the camera actually moves
          // during user interaction (drag/zoom/rotate), not on clicks or programmatic movements.
          if (isUserInteractingRef.current && !hasMovedCameraRef.current) {
            hasMovedCameraRef.current = true;
            setIsPointerEnabled(false);
          }

          if (zoomThrottleRef.current) return;

          zoomThrottleRef.current = setTimeout(() => {
            zoomThrottleRef.current = null;
            const target = controls.target;
            const dist = camera.position.distanceTo(target);

            let newLevel: ZoomLevel = "medium";
            if (dist > 450) {
              newLevel = "far";
            } else if (dist < 130) {
              newLevel = "near";
            }

            setZoomLevel((prev) => {
              if (prev !== newLevel) return newLevel;
              return prev;
            });
          }, 200);
        };

        controls.addEventListener("start", handleStart);
        controls.addEventListener("end", handleEnd);
        controls.addEventListener("change", handleCameraChange);

        return () => {
          controls.removeEventListener("start", handleStart);
          controls.removeEventListener("end", handleEnd);
          controls.removeEventListener("change", handleCameraChange);
        };
      } else if (dimensionMode === "2D") {
        // In 2D mode there are no OrbitControls, pointer is always active
        // The semantic zoom in 2D will be done via onZoom callback prop
      }
      return () => {};
    };

    const timer = setTimeout(setupListeners, 200);
    return () => clearTimeout(timer);
  }, [graphData.nodes.length, dimensionMode]);

  // Configure d3 forces when nodes are loaded or mode changes
  const configuredRef = useRef(false);

  // Reset states when changing dimensions
  useEffect(() => {
    configuredRef.current = false;
    setIsPointerEnabled(true); // Guarantees pointer doesn't get locked to false
    setZoomLevel("medium");
    setHoveredNodeId(null);
    // Clear pending timers
    if (cameraTimerRef.current) {
      clearTimeout(cameraTimerRef.current);
      cameraTimerRef.current = null;
    }
    if (clickTimeoutRef.current) {
      clearTimeout(clickTimeoutRef.current);
      clickTimeoutRef.current = null;
    }
    lastClickedNodeIdRef.current = null;
  }, [dimensionMode]);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || graphData.nodes.length === 0) return;

    const forceTimer = setTimeout(() => {
      const chargeForce = fg.d3Force("charge");
      if (chargeForce && typeof chargeForce.strength === "function") {
        chargeForce.strength(-35);
        if (typeof chargeForce.distanceMax === "function") {
          chargeForce.distanceMax(200);
        }
      }

      const linkForce = fg.d3Force("link");
      if (linkForce && typeof linkForce.distance === "function") {
        linkForce.distance(15);
      }

      if (dimensionMode === "3D") {
        fg.cameraPosition({ x: 0, y: 0, z: 250 });
      } else {
        // In 2D, wait for simulation to settle and use zoomToFit
        setTimeout(() => {
          const fg2 = fgRef.current;
          if (fg2 && typeof fg2.zoomToFit === "function") {
            fg2.zoomToFit(800, 40);
          }
        }, 1200);
      }
    }, 100);

    return () => {
      clearTimeout(forceTimer);
    };
  }, [graphData.nodes.length, dimensionMode]);

  // ─── Ghost Edges ───────────────────────────────────────────────────

  const linkColor = useCallback(
    (link: any) => {
      if (hoveredNodeId === null) return LINK_COLOR_DEFAULT;
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;

      if (sourceId === hoveredNodeId || targetId === hoveredNodeId) {
        return LINK_HOVER_COLOR;
      }
      return "rgba(156, 163, 175, 0.02)";
    },
    [hoveredNodeId]
  );

  const linkWidth = useCallback(
    (link: any) => {
      if (hoveredNodeId === null) return 0.5;
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;

      if (sourceId === hoveredNodeId || targetId === hoveredNodeId) {
        return 2.0;
      }
      return 0.15;
    },
    [hoveredNodeId]
  );

  const linkDirectionalParticles = useCallback(
    (link: any) => {
      if (hoveredNodeId === null) return 0;
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;

      if (sourceId === hoveredNodeId || targetId === hoveredNodeId) {
        return 2;
      }
      return 0;
    },
    [hoveredNodeId]
  );

  // ─── Single vs Double Click (Fly-to-Node) ──────────────────────────────

  const handleNodeHover = useCallback(
    (node: object | null) => {
      if (!isPointerEnabled) return;
      const graphNode = node as ForceGraphNode | null;
      const newId = graphNode?.id ?? null;
      console.log("[ForceGraph Renderer] Hover node:", newId, graphNode?.label);
      setHoveredNodeId(newId);
      onNodeHover(graphNode);
    },
    [isPointerEnabled, onNodeHover]
  );

  const handleNodeClick = useCallback(
    (node: object) => {
      const graphNode = node as ForceGraphNode;
      console.log("[ForceGraph Renderer] Click node initiated:", graphNode.id, graphNode.label);

      if (clickTimeoutRef.current && lastClickedNodeIdRef.current === graphNode.id) {
        console.log("[ForceGraph Renderer] Double click detected on same node:", graphNode.id);
        // Double Click -> fly to node
        clearTimeout(clickTimeoutRef.current);
        clickTimeoutRef.current = null;
        lastClickedNodeIdRef.current = null;

        const fg = fgRef.current;
        if (fg) {
          if (dimensionMode === "3D") {
            if (graphNode.x !== undefined && graphNode.y !== undefined && graphNode.z !== undefined) {
              fg.cameraPosition(
                { x: graphNode.x, y: graphNode.y, z: graphNode.z + 100 }, // Position camera in front of the node
                graphNode, // Look at the node
                1500 // 1.5s flight
              );
            }
          } else {
            if (graphNode.x !== undefined && graphNode.y !== undefined) {
              fg.centerAt(graphNode.x, graphNode.y, 1500); // Center on the node
              fg.zoom(8, 1500); // Focus with high zoom
            }
          }
        }
      } else {
        // If there was already a pending click on another node, clear it
        if (clickTimeoutRef.current) {
          clearTimeout(clickTimeoutRef.current);
        }
        
        lastClickedNodeIdRef.current = graphNode.id;
        console.log("[ForceGraph Renderer] Single click timeout started for node:", graphNode.id);
        
        // Single Click -> open panel after a small 280ms debounce
        clickTimeoutRef.current = setTimeout(() => {
          console.log("[ForceGraph Renderer] Single click timeout resolved, calling onNodeClick:", graphNode.id);
          clickTimeoutRef.current = null;
          lastClickedNodeIdRef.current = null;
          onNodeClick(graphNode);
        }, 280);
      }
    },
    [dimensionMode, onNodeClick]
  );
  // ─── Zoom & Pan 2D Camera Controller ────────────────────────────────────

  const handleZoom2D = useCallback(
    ({ k }: { k: number }) => {
      // 1. Semantic zoom for 2D based on scale (k)
      let newLevel: ZoomLevel = "medium";
      if (k < 0.6) {
        newLevel = "far";
      } else if (k > 4.5) {
        newLevel = "near";
      }
      setZoomLevel((prev) => {
        if (prev !== newLevel) return newLevel;
        return prev;
      });

      // 2. Temporary Interaction Freezing (Pointer/Raycast) during drag/zoom
      setIsPointerEnabled(false);
      if (cameraTimerRef.current) {
        clearTimeout(cameraTimerRef.current);
      }
      cameraTimerRef.current = setTimeout(() => {
        setIsPointerEnabled(true);
      }, 250);
    },
    []
  );
  // ─── Legend Data ──────────────────────────────────────────────────────

  const nodeTypesInGraph = useMemo(() => {
    const types = new Set<string>();
    graphData.nodes.forEach((n) => types.add(n.node_type));
    return Array.from(types).sort();
  }, [graphData.nodes]);

  return (
    <div className="relative" style={{ width, height }}>
      {/* Strict Conditional Rendering to preserve Canvas/WebGL memory */}
      {dimensionMode === "3D" ? (
        <ForceGraph3D
          ref={fgRef}
          graphData={graphData}
          nodeId="id"
          width={width}
          height={height}
          backgroundColor={BG_COLOR}
          rendererConfig={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
          }}
          enablePointerInteraction={isPointerEnabled}
          nodeThreeObject={nodeThreeObject as (node: object) => THREE.Object3D}
          nodeThreeObjectExtend={false}
          nodeVisibility={(node: any) => {
            if (zoomLevel === "far") return node.val >= 12;
            return true;
          }}
          linkVisibility={(link: any) => {
            if (zoomLevel === "far") {
              const sourceVal = typeof link.source === "object" ? link.source.val : 0;
              const targetVal = typeof link.target === "object" ? link.target.val : 0;
              return sourceVal >= 12 && targetVal >= 12;
            }
            return true;
          }}
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkOpacity={0.4}
          linkDirectionalParticles={linkDirectionalParticles}
          linkDirectionalParticleWidth={1.2}
          linkDirectionalParticleColor={() => LINK_HOVER_COLOR}
          linkDirectionalParticleSpeed={0.006}
          onNodeHover={handleNodeHover}
          onNodeClick={handleNodeClick}
          enableNodeDrag={true}
          enableNavigationControls={true}
          showNavInfo={false}
          warmupTicks={30}
          cooldownTicks={60}
          cooldownTime={1500}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      ) : (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          nodeId="id"
          width={width}
          height={height}
          backgroundColor={BG_COLOR}
          enablePointerInteraction={isPointerEnabled}
          nodeCanvasObject={nodeCanvasObject}
          onZoom={handleZoom2D}
          nodeVisibility={() => true}
          linkVisibility={(link: any) => {
            if (zoomLevel === "far") {
              // Completely hide edges in 2D for extreme performance (transparent spiderwebs)
              return false;
            }
            return true;
          }}
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkDirectionalParticles={linkDirectionalParticles}
          linkDirectionalParticleWidth={1.2}
          linkDirectionalParticleColor={() => LINK_HOVER_COLOR}
          linkDirectionalParticleSpeed={0.006}
          onNodeHover={handleNodeHover}
          onNodeClick={handleNodeClick}
          enableNodeDrag={true}
          warmupTicks={30}
          cooldownTicks={60}
          cooldownTime={1500}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      )}

      {/* Legend Overlay */}
      <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 pointer-events-none">
        {nodeTypesInGraph.map((type) => (
          <div
            key={type}
            className="flex items-center gap-1.5 px-2 py-1 rounded-full
                       bg-[#161b22]/80 backdrop-blur-sm border border-white/[0.08]
                       text-[10px] font-mono text-neutral-400"
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: NODE_TYPE_COLORS[type] ?? NODE_TYPE_COLORS.DEFAULT }}
            />
            {type}
          </div>
        ))}
        {zoomLevel === "far" && (
          <div
            className="flex items-center gap-1 px-2 py-1 rounded-full
                       bg-amber-500/10 border border-amber-500/20
                       text-[10px] font-mono text-amber-400"
          >
            🔭 Semantic Zoom Active
          </div>
        )}
      </div>
    </div>
  );
}

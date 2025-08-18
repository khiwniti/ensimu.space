import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Box, Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';

interface ThreeDViewerProps {
  type: 'geometry' | 'mesh' | 'results' | 'analysis';
  data?: any;
  className?: string;
  showControls?: boolean;
  showGrid?: boolean;
}

// Mesh visualization component
function MeshVisualization({ data }: { data?: any }) {
  const meshRef = useRef<THREE.Group>(null);
  const [wireframe, setWireframe] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002;
    }
  });

  // Generate a sample mesh structure
  const generateMeshElements = () => {
    const elements = [];
    const gridSize = 8;
    
    // Create a grid of mesh elements
    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        for (let k = 0; k < 2; k++) {
          const x = (i - gridSize/2) * 0.5;
          const y = (j - gridSize/2) * 0.5;
          const z = (k - 1) * 0.5;
          
          elements.push(
            <Box
              key={`${i}-${j}-${k}`}
              position={[x, y, z]}
              args={[0.4, 0.4, 0.4]}
            >
              <meshBasicMaterial 
                color="#3b82f6" 
                wireframe={wireframe}
                transparent={!wireframe}
                opacity={wireframe ? 1 : 0.6}
              />
            </Box>
          );
        }
      }
    }
    
    return elements;
  };

  return (
    <group ref={meshRef}>
      {generateMeshElements()}
      
      {/* Quality indicators */}
      {data?.qualityMetrics && (
        <Sphere position={[0, 3, 0]} args={[0.2]} >
          <meshBasicMaterial color={
            data.qualityMetrics.overallScore > 8 ? "#10b981" :
            data.qualityMetrics.overallScore > 6 ? "#f59e0b" : "#ef4444"
          } />
        </Sphere>
      )}
    </group>
  );
}

// Results visualization component
function ResultsVisualization({ data }: { data?: any }) {
  const resultsRef = useRef<THREE.Group>(null);
  const [animationPhase, setAnimationPhase] = useState(0);

  useFrame((state) => {
    setAnimationPhase(state.clock.elapsedTime);
  });

  // Simulate flow field or temperature distribution
  const generateResultField = () => {
    const field = [];
    const gridSize = 10;
    
    for (let i = 0; i < gridSize; i++) {
      for (let j = 0; j < gridSize; j++) {
        const x = (i - gridSize/2) * 0.3;
        const y = (j - gridSize/2) * 0.3;
        const intensity = Math.sin(x + animationPhase) * Math.cos(y + animationPhase);
        
        field.push(
          <Sphere
            key={`${i}-${j}`}
            position={[x, y, 0]}
            args={[0.05]}
          >
            <meshBasicMaterial color={
              intensity > 0.5 ? "#ef4444" :
              intensity > 0 ? "#f59e0b" :
              intensity > -0.5 ? "#3b82f6" : "#1e40af"
            } />
          </Sphere>
        );
      }
    }
    
    return field;
  };

  return (
    <group ref={resultsRef}>
      {generateResultField()}
      
      {/* Flow vectors */}
      <Line
        points={[[-2, 0, 0], [2, 0, 0]]}
        color="#10b981"
        lineWidth={2}
      />
      <Line
        points={[[0, -2, 0], [0, 2, 0]]}
        color="#10b981"
        lineWidth={2}
      />
    </group>
  );
}

// Analysis visualization component  
function AnalysisVisualization({ data }: { data?: any }) {
  const analysisRef = useRef<THREE.Group>(null);

  return (
    <group ref={analysisRef}>
      {/* Stress concentration points */}
      <Sphere position={[1, 1, 0]} args={[0.15]}>
        <meshBasicMaterial color="#ef4444" />
      </Sphere>
      <Sphere position={[-1, -1, 0]} args={[0.15]}>
        <meshBasicMaterial color="#ef4444" />
      </Sphere>
      
      {/* Material boundaries */}
      <Box position={[0, 0, 0]} args={[3, 3, 0.1]}>
        <meshBasicMaterial color="#3b82f6" transparent opacity={0.3} />
      </Box>
      
      {/* Analysis arrows */}
      <Line
        points={[[0, 0, 0], [1.5, 1.5, 0]]}
        color="#f59e0b"
        lineWidth={3}
      />
      <Line
        points={[[0, 0, 0], [-1.5, -1.5, 0]]}
        color="#f59e0b"
        lineWidth={3}
      />
    </group>
  );
}

export function ThreeDViewer({ type, data, className = "", showControls = true, showGrid = true }: ThreeDViewerProps) {
  const [viewMode, setViewMode] = useState<'3d' | 'top' | 'front' | 'side'>('3d');
  const [renderMode, setRenderMode] = useState<'solid' | 'wireframe' | 'points'>('solid');

  const getCameraPosition = (): [number, number, number] => {
    switch (viewMode) {
      case 'top': return [0, 8, 0];
      case 'front': return [0, 0, 8];
      case 'side': return [8, 0, 0];
      default: return [4, 4, 4];
    }
  };

  const renderVisualization = () => {
    switch (type) {
      case 'mesh':
        return <MeshVisualization data={data} />;
      case 'results':
        return <ResultsVisualization data={data} />;
      case 'analysis':
        return <AnalysisVisualization data={data} />;
      default:
        return (
          <Box args={[2, 2, 2]}>
            <meshStandardMaterial color="#3b82f6" />
          </Box>
        );
    }
  };

  return (
    <div className={`w-full h-96 bg-gray-100 rounded-lg overflow-hidden border ${className}`}>
      {/* Controls Header */}
      {showControls && (
        <div className="bg-white border-b p-3 flex items-center justify-between">
          <div className="flex space-x-2">
            <span className="text-sm font-medium text-gray-700">
              {type.charAt(0).toUpperCase() + type.slice(1)} View
            </span>
          </div>

          <div className="flex space-x-2">
            {/* View Mode */}
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="3d">3D View</option>
              <option value="top">Top View</option>
              <option value="front">Front View</option>
              <option value="side">Side View</option>
            </select>

            {/* Render Mode */}
            <select
              value={renderMode}
              onChange={(e) => setRenderMode(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
            >
              <option value="solid">Solid</option>
              <option value="wireframe">Wireframe</option>
              <option value="points">Points</option>
            </select>
          </div>

          {/* Info Display */}
          <div className="text-xs text-gray-500">
            {data && Object.keys(data).length > 0 ? (
              <span>Data loaded</span>
            ) : (
              <span>No data</span>
            )}
          </div>
        </div>
      )}

      {/* 3D Canvas */}
      <div className="h-full relative">
        <Canvas
          camera={{ 
            position: getCameraPosition(), 
            fov: 50 
          }}
          style={{ background: '#f8fafc' }}
        >
          {/* Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={0.7} />
          <pointLight position={[-10, -10, -5]} intensity={0.3} />

          {/* Grid */}
          {showGrid && (
            <Grid
              args={[10, 10]}
              cellSize={0.5}
              cellThickness={0.5}
              cellColor="#9ca3af"
              sectionSize={5}
              sectionThickness={1}
              sectionColor="#6b7280"
              fadeDistance={20}
              fadeStrength={1}
              followCamera={false}
              infiniteGrid={true}
            />
          )}

          {/* Main visualization */}
          {renderVisualization()}

          {/* Controls */}
          <OrbitControls
            enablePan={true}
            enableZoom={true}
            enableRotate={viewMode === '3d'}
            minDistance={1}
            maxDistance={20}
          />
        </Canvas>

        {/* Data overlay */}
        {data && (
          <div className="absolute top-4 left-4 bg-white bg-opacity-90 p-3 rounded shadow max-w-xs">
            <h4 className="font-medium text-sm mb-2">{type.charAt(0).toUpperCase() + type.slice(1)} Data</h4>
            
            {type === 'mesh' && data.qualityMetrics && (
              <div className="space-y-1 text-xs">
                <div>Aspect Ratio: {data.qualityMetrics.aspectRatio?.toFixed(2) || 'N/A'}</div>
                <div>Skewness: {data.qualityMetrics.skewness?.toFixed(2) || 'N/A'}</div>
                <div>Overall Score: {data.qualityMetrics.overallScore?.toFixed(1) || 'N/A'}/10</div>
              </div>
            )}
            
            {type === 'results' && data.simulation && (
              <div className="space-y-1 text-xs">
                <div>Max Velocity: {data.simulation.maxVelocity?.toFixed(2) || 'N/A'} m/s</div>
                <div>Max Pressure: {data.simulation.maxPressure?.toFixed(0) || 'N/A'} Pa</div>
                <div>Temperature Range: {data.simulation.tempRange || 'N/A'} K</div>
              </div>
            )}
            
            {type === 'analysis' && data.analysis && (
              <div className="space-y-1 text-xs">
                <div>Max Stress: {data.analysis.maxStress?.toFixed(1) || 'N/A'} MPa</div>
                <div>Safety Factor: {data.analysis.safetyFactor?.toFixed(1) || 'N/A'}</div>
                <div>Deformation: {data.analysis.maxDeformation?.toFixed(3) || 'N/A'} mm</div>
              </div>
            )}
          </div>
        )}

        {/* Legend */}
        {type === 'results' && (
          <div className="absolute bottom-4 right-4 bg-white bg-opacity-90 p-2 rounded shadow">
            <div className="text-xs font-medium mb-1">Scale</div>
            <div className="flex space-x-1">
              <div className="w-3 h-3 bg-blue-800"></div>
              <div className="w-3 h-3 bg-blue-500"></div>
              <div className="w-3 h-3 bg-yellow-500"></div>
              <div className="w-3 h-3 bg-red-500"></div>
            </div>
            <div className="text-xs text-gray-600 mt-1">Low → High</div>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="bg-gray-50 border-t p-2 text-xs text-gray-600">
        <div className="flex justify-between items-center">
          <span>View: {viewMode.toUpperCase()} | Render: {renderMode}</span>
          <span>Type: {type.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
}
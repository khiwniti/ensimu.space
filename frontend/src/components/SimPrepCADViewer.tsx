import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame, useLoader } from '@react-three/fiber';
import { OrbitControls, Grid, Box, Sphere } from '@react-three/drei';
import * as THREE from 'three';

interface CADFile {
  id: string;
  filename: string;
  fileType: string;
  uploadStatus: string;
  analysisResults?: any;
}

interface SimPrepCADViewerProps {
  cadFiles: CADFile[];
  onFileSelect?: (fileId: string) => void;
  showGrid?: boolean;
  showAxes?: boolean;
}

// Simple CAD model placeholder component
function CADModel({ file, position = [0, 0, 0] }: { file: CADFile; position?: [number, number, number] }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
    }
  });

  // For demo purposes, show different shapes based on file type
  const getModelByFileType = (fileType: string) => {
    if (fileType.includes('step') || fileType.includes('stp')) {
      return (
        <Box
          ref={meshRef}
          position={position}
          args={[2, 1, 0.5]}
          onPointerOver={() => setHovered(true)}
          onPointerOut={() => setHovered(false)}
        >
          <meshStandardMaterial color={hovered ? "#4ade80" : "#3b82f6"} />
        </Box>
      );
    } else if (fileType.includes('stl')) {
      return (
        <Sphere
          ref={meshRef}
          position={position}
          args={[1, 32, 32]}
          onPointerOver={() => setHovered(true)}
          onPointerOut={() => setHovered(false)}
        >
          <meshStandardMaterial color={hovered ? "#f59e0b" : "#8b5cf6"} />
        </Sphere>
      );
    } else {
      return (
        <mesh
          ref={meshRef}
          position={position}
          onPointerOver={() => setHovered(true)}
          onPointerOut={() => setHovered(false)}
        >
          <cylinderGeometry args={[1, 1, 2, 8]} />
          <meshStandardMaterial color={hovered ? "#ef4444" : "#10b981"} />
        </mesh>
      );
    }
  };

  return getModelByFileType(file.fileType);
}

export function SimPrepCADViewer({ cadFiles, onFileSelect, showGrid = true, showAxes = true }: SimPrepCADViewerProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'perspective' | 'top' | 'front' | 'side'>('perspective');

  const handleFileSelect = (fileId: string) => {
    setSelectedFile(fileId);
    onFileSelect?.(fileId);
  };

  const getCameraPosition = (): [number, number, number] => {
    switch (viewMode) {
      case 'top': return [0, 10, 0];
      case 'front': return [0, 0, 10];
      case 'side': return [10, 0, 0];
      default: return [5, 5, 5];
    }
  };

  return (
    <div className="w-full h-96 bg-gray-100 rounded-lg overflow-hidden border">
      {/* Viewer Controls */}
      <div className="bg-white border-b p-3 flex items-center justify-between">
        <div className="flex space-x-2">
          <select
            value={selectedFile || ''}
            onChange={(e) => handleFileSelect(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="">Select CAD File</option>
            {cadFiles.map((file) => (
              <option key={file.id} value={file.id}>
                {file.filename}
              </option>
            ))}
          </select>
        </div>

        <div className="flex space-x-2">
          {(['perspective', 'top', 'front', 'side'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1 text-xs rounded capitalize ${
                viewMode === mode
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2 text-sm">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={showGrid}
              readOnly
              className="mr-1"
            />
            Grid
          </label>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={showAxes}
              readOnly
              className="mr-1"
            />
            Axes
          </label>
        </div>
      </div>

      {/* 3D Viewer */}
      <div className="h-full relative">
        {cadFiles.length === 0 ? (
          <div className="flex items-center justify-center h-full bg-gray-50">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-2">📐</div>
              <p className="font-medium">No CAD files loaded</p>
              <p className="text-sm">Upload CAD files to view geometry</p>
            </div>
          </div>
        ) : (
          <Canvas
            camera={{ 
              position: getCameraPosition(), 
              fov: 50 
            }}
            style={{ background: '#f8fafc' }}
          >
            {/* Lighting */}
            <ambientLight intensity={0.4} />
            <directionalLight position={[10, 10, 5]} intensity={0.8} />
            <pointLight position={[-10, -10, -5]} intensity={0.3} />

            {/* Grid */}
            {showGrid && (
              <Grid
                args={[20, 20]}
                cellSize={1}
                cellThickness={0.5}
                cellColor="#6b7280"
                sectionSize={5}
                sectionThickness={1}
                sectionColor="#374151"
                fadeDistance={30}
                fadeStrength={1}
                followCamera={false}
                infiniteGrid={true}
              />
            )}

            {/* Axes Helper */}
            {showAxes && <axesHelper args={[5]} />}

            {/* CAD Models */}
            {cadFiles.map((file, index) => {
              if (selectedFile && file.id !== selectedFile) return null;
              
              return (
                <CADModel
                  key={file.id}
                  file={file}
                  position={[
                    (index % 3) * 3 - 3,
                    0,
                    Math.floor(index / 3) * 3 - 3
                  ]}
                />
              );
            })}

            {/* Controls */}
            <OrbitControls
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              minDistance={2}
              maxDistance={50}
            />
          </Canvas>
        )}

        {/* File Info Overlay */}
        {selectedFile && (
          <div className="absolute top-4 left-4 bg-white bg-opacity-90 p-3 rounded shadow">
            {(() => {
              const file = cadFiles.find(f => f.id === selectedFile);
              return file ? (
                <div className="text-sm">
                  <p className="font-medium">{file.filename}</p>
                  <p className="text-gray-600">{file.fileType}</p>
                  <p className="text-gray-600">Status: {file.uploadStatus}</p>
                </div>
              ) : null;
            })()}
          </div>
        )}

        {/* Loading Indicator */}
        {cadFiles.some(file => file.uploadStatus === 'uploading') && (
          <div className="absolute bottom-4 right-4 bg-blue-500 text-white px-3 py-2 rounded shadow">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">Processing...</span>
            </div>
          </div>
        )}
      </div>

      {/* File Status Bar */}
      {cadFiles.length > 0 && (
        <div className="bg-gray-50 border-t p-2">
          <div className="flex space-x-4 text-xs text-gray-600">
            <span>Files: {cadFiles.length}</span>
            <span>
              Completed: {cadFiles.filter(f => f.uploadStatus === 'completed').length}
            </span>
            <span>
              Processing: {cadFiles.filter(f => f.uploadStatus === 'uploading').length}
            </span>
            {cadFiles.filter(f => f.uploadStatus === 'failed').length > 0 && (
              <span className="text-red-600">
                Failed: {cadFiles.filter(f => f.uploadStatus === 'failed').length}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
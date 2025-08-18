import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MeshQualityVisualization } from '../../components/GenerativeUI/MeshQualityVisualization';

// Mock the useSimulationState hook
vi.mock('../../hooks/useSimulationState', () => ({
  useSimulationState: vi.fn(),
}));

import { useSimulationState } from '../../hooks/useSimulationState';

describe('MeshQualityVisualization', () => {
  const mockUseSimulationState = useSimulationState as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders placeholder when no mesh metrics available', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: null,
        meshRecommendations: null,
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    expect(screen.getByText('Mesh Quality Metrics')).toBeInTheDocument();
    expect(screen.getByText('📊')).toBeInTheDocument();
    expect(screen.getByText('Mesh quality metrics will appear here after mesh generation')).toBeInTheDocument();
  });

  it('displays mesh quality metrics correctly', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.85,
          skewness: 0.15,
          orthogonalQuality: 0.92,
          overallScore: 8.5,
        },
        meshRecommendations: {
          computational_cost_estimate: {
            element_count: 150000,
          },
          element_types: {
            primary: 'hexahedral',
          },
          performance_optimization: {
            memory_estimate: {
              mesh_memory_gb: 2.5,
            },
            runtime_estimate: {
              mesh_generation_minutes: 15,
            },
          },
        },
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    expect(screen.getByText('Mesh Quality Metrics')).toBeInTheDocument();
    expect(screen.getByText('Excellent')).toBeInTheDocument(); // Overall quality badge
    
    // Check individual metrics
    expect(screen.getByText('Aspect Ratio')).toBeInTheDocument();
    expect(screen.getByText('0.85')).toBeInTheDocument();
    
    expect(screen.getByText('Skewness')).toBeInTheDocument();
    expect(screen.getByText('0.150')).toBeInTheDocument();
    
    expect(screen.getByText('Orthogonal Quality')).toBeInTheDocument();
    expect(screen.getByText('0.92')).toBeInTheDocument();
    
    expect(screen.getByText('Overall Score')).toBeInTheDocument();
    expect(screen.getByText('8.5/10')).toBeInTheDocument();
  });

  it('shows quality recommendations based on metrics', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.45, // Poor
          skewness: 0.65,    // Poor
          orthogonalQuality: 0.55, // Poor
          overallScore: 4.2, // Poor
        },
        meshRecommendations: null,
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    expect(screen.getByText('Quality Recommendations')).toBeInTheDocument();
    expect(screen.getByText('Consider mesh refinement to improve quality before simulation')).toBeInTheDocument();
    expect(screen.getByText('High skewness detected - review element shapes in critical regions')).toBeInTheDocument();
    expect(screen.getByText('Poor aspect ratio - consider adjusting element sizing')).toBeInTheDocument();
  });

  it('displays excellent quality recommendations', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.95,
          skewness: 0.05,
          orthogonalQuality: 0.98,
          overallScore: 9.2,
        },
        meshRecommendations: null,
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    expect(screen.getByText('Excellent mesh quality - ready for high-accuracy simulation')).toBeInTheDocument();
  });

  it('shows mesh statistics when available', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.85,
          skewness: 0.15,
          orthogonalQuality: 0.92,
          overallScore: 8.5,
        },
        meshRecommendations: {
          computational_cost_estimate: {
            element_count: 250000,
          },
          element_types: {
            primary: 'tetrahedral',
          },
          performance_optimization: {
            memory_estimate: {
              mesh_memory_gb: 4.2,
            },
            runtime_estimate: {
              mesh_generation_minutes: 25,
            },
          },
        },
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    // Check mesh statistics
    expect(screen.getByText('250,000')).toBeInTheDocument(); // Element count
    expect(screen.getByText('Elements')).toBeInTheDocument();
    
    expect(screen.getByText('tetrahedral')).toBeInTheDocument(); // Element type
    expect(screen.getByText('Element Type')).toBeInTheDocument();
    
    expect(screen.getByText('4.2')).toBeInTheDocument(); // Memory
    expect(screen.getByText('Memory (GB)')).toBeInTheDocument();
    
    expect(screen.getByText('25')).toBeInTheDocument(); // Time estimate
    expect(screen.getByText('Est. Time (min)')).toBeInTheDocument();
  });

  it('handles missing mesh recommendation data gracefully', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.75,
          skewness: 0.25,
          orthogonalQuality: 0.80,
          overallScore: 7.0,
        },
        meshRecommendations: {
          computational_cost_estimate: {},
          element_types: {},
          performance_optimization: {
            memory_estimate: {},
            runtime_estimate: {},
          },
        },
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    // Should show N/A for missing data
    const naElements = screen.getAllByText('N/A');
    expect(naElements.length).toBeGreaterThan(0);
  });

  it('applies correct quality color coding', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.95, // Excellent - should be green
          skewness: 0.05,    // Excellent - should be green
          orthogonalQuality: 0.98, // Excellent - should be green
          overallScore: 9.2, // Excellent - should be green
        },
        meshRecommendations: null,
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    // Check that excellent quality badge is present
    const excellentBadge = screen.getByText('Excellent');
    expect(excellentBadge).toBeInTheDocument();
    expect(excellentBadge.closest('div')).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('shows good quality status correctly', () => {
    mockUseSimulationState.mockReturnValue({
      simulationState: {
        meshQualityMetrics: {
          aspectRatio: 0.75,
          skewness: 0.35,
          orthogonalQuality: 0.70,
          overallScore: 6.8,
        },
        meshRecommendations: null,
      },
    });

    render(<MeshQualityVisualization projectId="test-project" />);

    const goodBadge = screen.getByText('Good');
    expect(goodBadge).toBeInTheDocument();
    expect(goodBadge.closest('div')).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });
});

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    // Handle file imports for various formats
    config.module.rules.push({
      test: /\.(pdf|txt|csv)$/,
      type: 'asset/resource',
    });
    
    return config;
  },
  transpilePackages: [
    '@copilotkit/react-core',
    '@copilotkit/react-ui',
    '@copilotkit/react-textarea'
  ],
};

export default nextConfig;

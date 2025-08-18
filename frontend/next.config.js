/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    esmExternals: 'loose',
  },
  webpack: (config, { isServer }) => {
    // Handle canvas for react-pdf and other packages
    config.resolve.alias.canvas = false
    
    // Fix for packages that use process
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      crypto: false,
      stream: false,
      buffer: false,
      util: false,
      assert: false,
      http: false,
      https: false,
      os: false,
      url: false,
      zlib: false,
      path: false,
    }
    
    // Handle WebAssembly
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
      syncWebAssembly: true,
    }
    
    // Handle audio files
    config.module.rules.push({
      test: /\.(mp3|wav|ogg)$/,
      use: {
        loader: 'file-loader',
        options: {
          publicPath: '/_next/static/sounds/',
          outputPath: 'static/sounds/',
        },
      },
    })
    
    // Handle worker files
    config.module.rules.push({
      test: /\.worker\.js$/,
      use: { loader: 'worker-loader' },
    })
    
    // Handle WASM files
    config.module.rules.push({
      test: /\.wasm$/,
      type: 'webassembly/async',
    })
    
    return config
  },
  images: {
    domains: [
      'localhost',
      'example.com',
      'cdn.example.com',
      // Add more domains as needed for your images
    ],
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  // Support for Three.js and other libraries
  transpilePackages: [
    'three',
    '@react-three/fiber',
    '@react-three/drei',
    'rhino3dm',
    '@blocknote/core',
    '@blocknote/react',
    '@splinetool/react-spline',
  ],
}

module.exports = nextConfig
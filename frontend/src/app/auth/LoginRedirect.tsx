'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Mock user hook (replaces Stack Auth dependency)
const useUser = () => {
  return null; // Always return null for now (unauthenticated)
};

export const LoginRedirect: React.FC = () => {
  const router = useRouter();
  const user = useUser();

  useEffect(() => {
    if (user) {
      // Redirect authenticated users to the dashboard
      router.replace('/dashboard');
    } else {
      // Redirect unauthenticated users to home page
      router.replace('/');
    }
  }, [user, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Redirecting...</p>
      </div>
    </div>
  );
};
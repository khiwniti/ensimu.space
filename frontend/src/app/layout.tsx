import type { Metadata } from 'next'
import './globals.css'
import { AppProvider } from '@/components/AppProvider'

export const metadata: Metadata = {
  title: 'EnsumuSpace',
  description: 'AI-powered engineering simulations and workflows',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  )
}
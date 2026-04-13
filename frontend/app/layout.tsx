import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter'
})

export const metadata: Metadata = {
  title: 'AIVidio - Create Faceless YouTube Videos with AI',
  description: 'Generate professional faceless YouTube videos with AI-powered scripts, voiceovers, and visuals. No camera, no editing, just results.',
  generator: 'AIVidio',
  keywords: ['AI video', 'YouTube automation', 'faceless videos', 'AI content creation', 'video generation'],
  authors: [{ name: 'AIVidio' }],
  openGraph: {
    title: 'AIVidio - Create Faceless YouTube Videos with AI',
    description: 'Generate professional faceless YouTube videos with AI-powered scripts, voiceovers, and visuals.',
    type: 'website',
    siteName: 'AIVidio',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AIVidio - Create Faceless YouTube Videos with AI',
    description: 'Generate professional faceless YouTube videos with AI-powered scripts, voiceovers, and visuals.',
  },
}

export const viewport: Viewport = {
  themeColor: '#ffffff',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}

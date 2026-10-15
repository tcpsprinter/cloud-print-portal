import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Cloud Print Portal',
  description: 'Secure PDF printing portal',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
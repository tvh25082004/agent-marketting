import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Tinasoft-Agentic-Marketing | AI Music Video Studio',
  description: 'AI Agentic Marketing - Tự động crawl nhạc, tạo video ca sĩ AI với LangGraph',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="min-h-screen bg-[#0f141e] text-gray-100">
        {children}
      </body>
    </html>
  )
}

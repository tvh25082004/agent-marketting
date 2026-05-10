import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f5ff',
          100: '#e0eaff',
          200: '#c2d6ff',
          300: '#94b8ff',
          400: '#6090ff',
          500: '#3366ff',
          600: '#1a40e0',
          700: '#1a33b3',
          800: '#1a2d8a',
          900: '#1a2566',
        },
        dark: {
          50: '#f8f9fc',
          100: '#e8ecf4',
          200: '#c8d0e0',
          300: '#9ca8c0',
          400: '#6c7a9a',
          500: '#4a5568',
          600: '#374151',
          700: '#2d3748',
          800: '#1a202c',
          900: '#0f141e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'gradient': 'gradient 8s ease infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
    },
  },
  plugins: [],
}

export default config

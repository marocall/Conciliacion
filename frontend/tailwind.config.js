/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0a0f',
        'bg-card': '#12121a',
        'bg-elevated': '#1a1a26',
        'accent-gold': '#6B2D8B',
        'accent-gold-light': '#8B3DAB',
        'accent-blue': '#3b82f6',
        'text-primary': '#f8fafc',
        'text-secondary': '#94a3b8',
        success: '#10b981',
        error: '#ef4444',
        border: 'rgba(255,255,255,0.08)',
      },
      fontFamily: {
        display: ['Playfair Display', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['DM Sans', 'sans-serif'],
      },
      animation: {
        'pulse-gold': 'pulsePurple 2s ease-in-out infinite',
        'fade-up': 'fadeUp 0.5s ease-out forwards',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        pulsePurple: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(107,45,139,0.4)' },
          '50%': { boxShadow: '0 0 0 12px rgba(107,45,139,0)' },
        },
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}

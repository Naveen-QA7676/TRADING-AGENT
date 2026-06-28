/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0A0E1A',
        card: '#141824',
        border: '#1E2535',
        bull: '#00FF88',
        bear: '#FF3355',
        amber: '#FFB020',
        info: '#4488FF',
        muted: '#6B7280',
        text: '#E2E8F0',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}

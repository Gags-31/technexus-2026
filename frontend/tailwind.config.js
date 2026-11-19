/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#030711',
        navy: '#071126',
        panel: '#0a1730',
        cyan: '#22e6ff',
        electric: '#3b82f6',
        violet: '#9b6dff',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 32px rgba(34,230,255,.22)',
        violet: '0 0 40px rgba(155,109,255,.22)',
      },
    },
  },
  plugins: [],
}

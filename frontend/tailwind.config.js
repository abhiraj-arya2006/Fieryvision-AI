/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        fv: {
          bg: '#050914',
          bg2: '#08111e',
          panel: 'rgba(8, 15, 28, 0.78)',
          panel2: 'rgba(12, 21, 37, 0.88)',
          border: 'rgba(130, 180, 255, 0.16)',
          borderHover: 'rgba(130, 180, 255, 0.32)',
          cyan: '#38bdf8',
          cyanGlow: '#0284c7',
          violet: '#8768ff',
          purple: '#b46cff',
          red: '#ff4d4d',
          orange: '#ff9b3d',
          amber: '#f59e0b',
          green: '#53d88b',
          blue: '#4fa7ff',
          muted: '#8497ae',
          mutedDark: '#52657b'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.15)', opacity: '0.75' },
        },
        radarScan: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        }
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-scan': 'radarScan 4s linear infinite',
      }
    },
  },
  plugins: [],
}

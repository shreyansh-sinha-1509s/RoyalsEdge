/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        rr: {
          plum: '#24172C',
          surface: '#392940',
          'surface-deep': '#1B1022',
          pink: '#E83E80',
          gold: '#D8B45A',
          light: '#F5F1F5',
          lavender: '#B8A6C2',
          teal: '#4FD1A5',
          coral: '#F26A6A',
          blue: '#7C9EF2',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        rr: '0 10px 30px -10px rgba(10, 4, 15, 0.65)',
        'rr-pink': '0 0 28px -6px rgba(232, 62, 128, 0.45)',
      },
    },
  },
  plugins: [],
};


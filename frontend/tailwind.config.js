/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette for the file manager
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        // File permission colors
        readonly: {
          light: '#fef3c7',
          dark: '#d97706',
        },
        readwrite: {
          light: '#dcfce7',
          dark: '#16a34a',
        },
        agent: {
          light: '#e0e7ff',
          dark: '#4338ca',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'bounce-subtle': 'bounceSubtle 0.4s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
        },
      },
      boxShadow: {
        'file-item': '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'file-item-hover': '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
        'permission-card': '0 2px 8px rgba(0, 0, 0, 0.1)',
      },
      spacing: {
        'sidebar': '16rem',
        'file-item': '2.75rem',
      },
    },
  },
  plugins: [
    // Custom plugin for file permission styles
    function({ addUtilities }) {
      const newUtilities = {
        '.permission-readonly': {
          'border-left': '4px solid #d97706',
          'background-color': '#fef3c7',
        },
        '.permission-readwrite': {
          'border-left': '4px solid #16a34a',
          'background-color': '#dcfce7',
        },
        '.permission-agent': {
          'border-left': '4px solid #4338ca',
          'background-color': '#e0e7ff',
        },
        '.drag-over': {
          'border': '2px dashed #3b82f6',
          'background-color': '#eff6ff',
        },
        '.file-selected': {
          'background-color': '#dbeafe',
          'border-color': '#3b82f6',
        },
      }
      addUtilities(newUtilities)
    }
  ],
}
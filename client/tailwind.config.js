/** @type {import('tailwindcss').Config} */
// Dark is the default theme (:root); light is [data-theme="light"].
// Colors reference CSS custom properties defined in src/index.css so the
// same Tailwind utilities work across both themes.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        app: 'var(--bg-app)',
        surface: 'var(--bg-surface)',
        'surface-hover': 'var(--bg-surface-hover)',
        elevated: 'var(--bg-elevated)',
        input: 'var(--bg-input)',
        subtle: 'var(--border-subtle)',
        line: 'var(--border)',
        'line-strong': 'var(--border-strong)',
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        tertiary: 'var(--text-tertiary)',
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        'accent-soft': 'var(--accent-soft)',
        up: 'var(--color-up)',
        'up-soft': 'var(--color-up-soft)',
        down: 'var(--color-down)',
        'down-soft': 'var(--color-down-soft)',
        warn: 'var(--color-warn)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius)',
        lg: 'var(--radius-lg)',
      },
      fontFamily: {
        body: 'var(--font-body)',
        mono: 'var(--font-mono)',
      },
    },
  },
  plugins: [],
}

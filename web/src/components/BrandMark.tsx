interface BrandMarkProps {
  size?: number;
  className?: string;
}

export function BrandMark({ size = 38, className }: BrandMarkProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="7.5" y="5.5" width="25" height="29" rx="1.5" stroke="currentColor" />
      <path d="M13 6v28" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M17.5 15.5c2.2-2.4 4.1 2.4 6.3 0s4.1 2.4 6.3 0M17.5 20.5c2.2-2.4 4.1 2.4 6.3 0s4.1 2.4 6.3 0M17.5 25.5c2.2-2.4 4.1 2.4 6.3 0s4.1 2.4 6.3 0"
        stroke="var(--accent)"
        strokeLinecap="round"
        strokeWidth="1.3"
      />
    </svg>
  );
}

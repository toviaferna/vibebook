import clsx from "clsx";
import { type ButtonHTMLAttributes, forwardRef } from "react";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={clsx("icon-button", className)}
      aria-label={label}
      title={label}
      {...props}
    >
      {children}
    </button>
  );
});

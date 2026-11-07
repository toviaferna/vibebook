import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";

import { Button } from "../../components/Button";
import { Field } from "../../components/Field";

type Theme = "light" | "sepia" | "night";
type Font = "serif" | "sans" | "hyperlegible";

interface ReaderSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  theme: Theme;
  font: Font;
  size: number;
  follow: boolean;
  onTheme: (theme: Theme) => void;
  onFont: (font: Font) => void;
  onSize: (size: number) => void;
  onFollow: (follow: boolean) => void;
}

export function ReaderSettingsDialog({
  open,
  onOpenChange,
  theme,
  font,
  size,
  follow,
  onTheme,
  onFont,
  onSize,
  onFollow,
}: ReaderSettingsDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content reader-settings" aria-describedby={undefined}>
          <div className="reader-settings-head">
            <div>
              <p className="eyebrow">Lectura</p>
              <Dialog.Title asChild>
                <h2>Tu espacio</h2>
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="icon-button" aria-label="Cerrar ajustes">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          <div className="settings-section">
            <Field label="Tema">
              <div className="theme-options" role="radiogroup" aria-label="Tema de lectura">
                {[
                  { value: "light", label: "Claro" },
                  { value: "sepia", label: "Sepia" },
                  { value: "night", label: "Noche" },
                ].map((option) => (
                  <label
                    key={option.value}
                    className={`theme-option${theme === option.value ? " is-selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="reader-theme"
                      value={option.value}
                      checked={theme === option.value}
                      onChange={() => onTheme(option.value as Theme)}
                    />
                    <span className="theme-swatch" data-theme-swatch={option.value} />
                    {option.label}
                  </label>
                ))}
              </div>
            </Field>

            <Field label="Tipografía" htmlFor="reader-font">
              <select
                id="reader-font"
                className="select"
                value={font}
                onChange={(event) => onFont(event.target.value as Font)}
              >
                <option value="serif">Serif editorial</option>
                <option value="sans">Sans clara</option>
                <option value="hyperlegible">Atkinson Hyperlegible</option>
              </select>
            </Field>

            <Field label={`Tamaño de texto · ${size}px`}>
              <input
                className="range"
                type="range"
                min={16}
                max={28}
                step={1}
                value={size}
                onChange={(event) => onSize(Number(event.target.value))}
              />
            </Field>

            <label className="label" htmlFor="reader-follow-setting">
              <input
                id="reader-follow-setting"
                type="checkbox"
                checked={follow}
                onChange={(event) => onFollow(event.target.checked)}
              />{" "}
              Seguir el texto mientras suena
            </label>
          </div>

          <div className="dialog-actions">
            <Dialog.Close asChild>
              <Button variant="primary">Listo</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

import * as Dialog from "@radix-ui/react-dialog";

import { Button } from "../../components/Button";

const SHORTCUTS = [
  ["Espacio", "Reproducir o pausar"],
  ["← / →", "Retroceder o adelantar"],
  ["J / K", "Capítulo anterior o siguiente"],
  ["+ / -", "Cambiar velocidad"],
  ["T", "Abrir el índice"],
  ["F", "Pantalla completa"],
  ["?", "Esta ayuda"],
];

export function ShortcutsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content" aria-describedby={undefined}>
          <p className="eyebrow">Atajos</p>
          <Dialog.Title asChild>
            <h2>Leer sin soltar el teclado</h2>
          </Dialog.Title>
          <div className="shortcut-list">
            {SHORTCUTS.map(([keys, label]) => (
              <div className="shortcut-row" key={keys}>
                <kbd className="kbd">{keys}</kbd>
                <span>{label}</span>
              </div>
            ))}
          </div>
          <div className="dialog-actions">
            <Dialog.Close asChild>
              <Button variant="primary">Cerrar</Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

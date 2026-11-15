import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

import { errorMessage } from "../../api/client";
import { useDeleteBook } from "../../api/queries";
import type { Book } from "../../api/types";
import { Button } from "../../components/Button";

interface DeleteBookDialogProps {
  book: Book | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}

export function DeleteBookDialog({ book, open, onOpenChange, onDeleted }: DeleteBookDialogProps) {
  const deleteBook = useDeleteBook();
  const reset = deleteBook.reset;
  const error = deleteBook.isError ? errorMessage(deleteBook.error) : null;

  useEffect(() => {
    if (!open) {
      reset();
    }
  }, [open, reset]);

  if (!book) {
    return null;
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <Dialog.Title asChild>
            <h2>¿Eliminar “{book.title}”?</h2>
          </Dialog.Title>
          <Dialog.Description asChild>
            <p>
              Se borran el EPUB, el audio, los datos de sincronización y el estado de lectura. Esta
              acción no se puede deshacer.
            </p>
          </Dialog.Description>
          {error ? (
            <div className="alert" role="alert" style={{ marginTop: "var(--space-4)" }}>
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          ) : null}
          <div className="dialog-actions">
            <Dialog.Close asChild>
              <Button variant="ghost">Cancelar</Button>
            </Dialog.Close>
            <Button
              variant="danger"
              loading={deleteBook.isPending}
              onClick={() => {
                deleteBook.mutate(book.id, {
                  onSuccess: () => {
                    onOpenChange(false);
                    onDeleted();
                  },
                });
              }}
            >
              Eliminar definitivamente
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

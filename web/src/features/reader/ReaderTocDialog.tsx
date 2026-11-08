import * as Dialog from "@radix-ui/react-dialog";

import type { ManifestChapter, TocNode } from "../../api/types";
import { ReaderToc } from "./ReaderToc";

interface ReaderTocDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  chapters: ManifestChapter[];
  toc?: TocNode[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function ReaderTocDialog({
  open,
  onOpenChange,
  chapters,
  toc,
  currentIndex,
  onSelect,
}: ReaderTocDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content reader-toc-dialog" aria-describedby={undefined}>
          <Dialog.Title asChild>
            <h2>Índice</h2>
          </Dialog.Title>
          <ReaderToc
            chapters={chapters}
            toc={toc}
            currentIndex={currentIndex}
            onSelect={(index) => {
              onSelect(index);
              onOpenChange(false);
            }}
          />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export interface StoredBook {
  id: string;
  title: string;
  bytes: ArrayBuffer;
  cfi: string | null;
  updatedAt: string;
}

const DB_NAME = "vibebook-reader";
const STORE = "books";

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE)) {
        database.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("No se pudo abrir la biblioteca."));
  });
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Error de IndexedDB."));
  });
}

export async function listBooks(): Promise<StoredBook[]> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(STORE, "readonly");
    const books = await requestResult(transaction.objectStore(STORE).getAll());
    return (books as StoredBook[]).sort((left, right) =>
      right.updatedAt.localeCompare(left.updatedAt),
    );
  } finally {
    database.close();
  }
}

export async function saveBook(book: StoredBook): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).put(book);
    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error ?? new Error("No se pudo guardar."));
    });
  } finally {
    database.close();
  }
}

export async function updateBookCfi(id: string, cfi: string | null): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(STORE, "readwrite");
    const store = transaction.objectStore(STORE);
    const book = (await requestResult(store.get(id))) as StoredBook | undefined;
    if (book) {
      store.put({ ...book, cfi, updatedAt: new Date().toISOString() });
    }
    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error ?? new Error("No se pudo guardar."));
    });
  } finally {
    database.close();
  }
}

export async function deleteBook(id: string): Promise<void> {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).delete(id);
    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error ?? new Error("No se pudo borrar."));
    });
  } finally {
    database.close();
  }
}

"use client";

import { useRef, useState } from "react";

export default function FileDropzone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [isOver, setIsOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsOver(false);
        if (e.dataTransfer.files.length) onFiles(Array.from(e.dataTransfer.files));
      }}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-3xl p-8 text-center flex flex-col items-center gap-3 cursor-pointer ${
        isOver ? "border-[var(--brass)] bg-[#F1EADB]" : "border-[var(--line2)] bg-cream"
      }`}
    >
      <span className="serif text-2xl">Перетащите файлы сюда</span>
      <span className="text-sm text-[var(--stone)]">или нажмите, чтобы выбрать — письма, договоры, сканы, таблицы, .ics</span>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.length) onFiles(Array.from(e.target.files));
          e.target.value = "";
        }}
      />
    </div>
  );
}

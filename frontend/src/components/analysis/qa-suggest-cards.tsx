"use client";

type QaSuggestCardsProps = {
  onSelect: (question: string) => void;
};

const SUGGESTIONS = [
  "这些产品最常见的差评原因是什么？",
  "哪个产品在质量方面评价最好？",
  "买家最常提到的优点有哪些？",
  "不同产品之间有哪些共同的质量问题？",
];

export function QaSuggestCards({ onSelect }: QaSuggestCardsProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
        想了解什么？
      </h2>
      <p className="mt-2 text-sm leading-7 text-soft">
        选择产品后，可以围绕评论自由提问，支持多轮追问。
      </p>
      <div className="mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onSelect(text)}
            className="rounded-card border border-line bg-white px-4 py-4 text-left text-sm leading-6 text-ink transition hover:border-[#f36f8f] hover:shadow-card"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

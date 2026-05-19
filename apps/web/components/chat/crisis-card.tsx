export function CrisisCard({ content }: { content: string }) {
  return (
    <div className="mx-4 rounded-xl border-2 border-[var(--color-crisis)] bg-red-50 p-4">
      <p className="mb-2 text-sm font-medium text-[var(--color-crisis)]">
        You&apos;re not alone — support is available
      </p>
      <p className="text-sm text-[var(--color-text-primary)]">{content}</p>
      <a
        href="tel:800HOPE"
        className="mt-3 inline-flex min-h-[44px] items-center rounded-full bg-[var(--color-crisis)] px-4 py-2 text-sm font-medium text-white"
      >
        Talk to someone now
      </a>
    </div>
  )
}

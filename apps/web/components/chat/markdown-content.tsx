'use client'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'

// Safe element allowlist — no raw HTML (rehype-raw is intentionally absent), so the
// renderer cannot emit script/style/iframe. Headings are capped at h3/h4 so a stray
// model `#` cannot produce a page-dominating title; bold subheads come from <strong>.
// 'a' is DELIBERATELY EXCLUDED (see Global Constraints "Links"): with unwrapDisallowed,
// [text](url) renders as its plain-text label with NO clickable anchor. The backend does
// not strip link syntax (output_gate strips emphasis/emoji/em-dash only), so allowing 'a'
// would make clickable model-generated URLs live on day one. Clickable links are a
// Sub-project B decision (vetted-domain allowlist + clinical owner).
const ALLOWED = ['p', 'strong', 'em', 'ul', 'ol', 'li', 'br', 'h3', 'h4', 'blockquote', 'code']

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkBreaks]}
      allowedElements={ALLOWED}
      unwrapDisallowed
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 ps-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 ps-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        h3: ({ children }) => <h3 className="mb-2 mt-3 font-semibold first:mt-0">{children}</h3>,
        h4: ({ children }) => <h4 className="mb-2 mt-3 font-semibold first:mt-0">{children}</h4>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-s-2 border-[var(--color-border)] ps-3 text-[var(--color-text-secondary)]">
            {children}
          </blockquote>
        ),
        // No `a` mapping — 'a' is not in ALLOWED, so links render as plain-text labels.
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

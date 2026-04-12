import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Renders markdown content with GFM support (tables, strikethrough, tasklists)
 * and Tailwind-friendly prose styling.
 */
export default function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-invert max-w-none
      prose-headings:font-display prose-headings:text-white
      prose-h1:text-2xl prose-h1:border-b prose-h1:border-[var(--color-border)] prose-h1:pb-3 prose-h1:mb-6
      prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4
      prose-h3:text-lg prose-h3:mt-6 prose-h3:mb-3
      prose-p:text-[var(--color-text-secondary)] prose-p:leading-relaxed
      prose-a:text-primary-400 prose-a:no-underline hover:prose-a:underline
      prose-strong:text-white
      prose-code:text-primary-300 prose-code:bg-studio-obsidian/50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
      prose-pre:bg-studio-obsidian/80 prose-pre:border prose-pre:border-[var(--color-border)] prose-pre:rounded-xl
      prose-table:border-collapse
      prose-th:border prose-th:border-[var(--color-border)] prose-th:bg-studio-charcoal/30 prose-th:px-4 prose-th:py-2 prose-th:text-left prose-th:text-white prose-th:text-sm
      prose-td:border prose-td:border-[var(--color-border)] prose-td:px-4 prose-td:py-2 prose-td:text-sm prose-td:text-[var(--color-text-secondary)]
      prose-li:text-[var(--color-text-secondary)]
      prose-blockquote:border-primary-500/50 prose-blockquote:bg-primary-500/5 prose-blockquote:rounded-r-lg prose-blockquote:py-1
      prose-hr:border-[var(--color-border)]
      ${className}`}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

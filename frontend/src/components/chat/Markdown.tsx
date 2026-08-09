import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  p: (props) => <p className="mb-2.5 leading-relaxed last:mb-0" {...props} />,
  strong: (props) => <strong className="font-semibold text-foreground" {...props} />,
  em: (props) => <em className="italic" {...props} />,
  ul: (props) => <ul className="mb-2.5 list-disc space-y-1 pl-5" {...props} />,
  ol: (props) => <ol className="mb-2.5 list-decimal space-y-1 pl-5" {...props} />,
  li: (props) => <li className="leading-relaxed marker:text-muted/60" {...props} />,
  h1: (props) => <h1 className="mb-2 mt-4 text-lg font-semibold" {...props} />,
  h2: (props) => <h2 className="mb-2 mt-3.5 text-base font-semibold" {...props} />,
  h3: (props) => <h3 className="mb-1.5 mt-3 text-sm font-semibold" {...props} />,
  h4: (props) => <h4 className="mb-1.5 mt-2.5 text-sm font-semibold" {...props} />,
  hr: (props) => <hr className="my-3 border-white/8" {...props} />,
  blockquote: (props) => (
    <blockquote className="my-2.5 border-l-2 border-primary/50 bg-white/[0.03] py-1 pl-3 pr-2 text-muted" {...props} />
  ),
  a: (props) => (
    <a className="font-medium text-primary underline decoration-primary/40 underline-offset-2 hover:text-primary-hover" target="_blank" rel="noreferrer" {...props} />
  ),
  code: (props) => (
    <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.85em] text-primary" {...props} />
  ),
  pre: (props) => (
    <pre className="my-2.5 overflow-x-auto rounded-lg border border-white/8 bg-[#0a1120] p-3 font-mono text-xs leading-relaxed" {...props} />
  ),
  table: (props) => (
    <div className="my-2.5 overflow-x-auto rounded-lg border border-white/8">
      <table className="w-full text-xs" {...props} />
    </div>
  ),
  thead: (props) => <thead className="bg-white/5" {...props} />,
  th: (props) => <th className="px-3 py-2 text-left font-semibold text-muted" {...props} />,
  td: (props) => <td className="border-t border-white/8 px-3 py-2 text-muted" {...props} />,
};

export function Markdown({ content }: { content: string }) {
  return (
    <div className="text-[13.5px] text-foreground/90">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

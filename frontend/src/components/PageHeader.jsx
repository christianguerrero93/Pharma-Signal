export default function PageHeader({ kicker, title, description, actions }) {
  return (
    <div className="flex items-start justify-between gap-6 mb-8" data-testid="page-header">
      <div>
        {kicker && (
          <div className="text-[10px] uppercase tracking-[0.15em] font-semibold text-slate-500 mb-2">
            {kicker}
          </div>
        )}
        <h2 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight text-slate-900">
          {title}
        </h2>
        {description && (
          <p className="text-sm text-slate-600 mt-2 max-w-2xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/** A definition strip: reference detail, deliberately quieter than the content around it. */
export default function Spec({
  items,
  stacked = false,
}: {
  items: [string, string][];
  stacked?: boolean;
}) {
  return (
    <dl className={`grid gap-x-8 gap-y-2 ${stacked ? '' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
      {items.map(([term, value]) => (
        <div key={term} className="flex items-baseline justify-between gap-3 text-xs">
          <dt className="text-slate-400">{term}</dt>
          <dd className="truncate font-medium text-slate-600">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

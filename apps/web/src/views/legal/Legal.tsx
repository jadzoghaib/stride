/** One renderer for every legal document — the copy lives in lib/legal.ts so a
 *  schema change and its disclosure change in the same review. */

import { useParams } from 'react-router-dom'
import { PageHeader, Section } from '../../components/ui'
import { LEGAL_STATUS, POLICY_VERSION, legalDoc } from '../../lib/legal'
import NotFound from '../NotFound'

export default function Legal() {
  const { doc } = useParams()
  const d = legalDoc(doc)
  if (!d) return <NotFound />

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow={d.eyebrow}
        title={d.title}
        lede={d.lede}
        aside={<span className="meta">v{POLICY_VERSION}</span>}
      />

      <div className="rounded border border-warn/45 bg-warn/10 px-4 py-3 text-sm text-warn">
        <b className="font-display uppercase tracking-micro">Draft</b> — {LEGAL_STATUS}
      </div>

      {d.sections.map((s) => (
        <Section key={s.h} title={s.h}>
          {s.p?.map((para) => (
            <p key={para.slice(0, 40)} className="mb-3 text-body leading-relaxed text-ink-2 last:mb-0">
              {para}
            </p>
          ))}

          {s.list && (
            <ul className="space-y-1.5 text-body text-ink-2">
              {s.list.map((li) => (
                <li key={li} className="flex gap-2.5">
                  <span className="mt-2 h-px w-3 shrink-0 bg-accent" aria-hidden />
                  <span>{li}</span>
                </li>
              ))}
            </ul>
          )}

          {s.table && (
            <div className="panel overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    {s.table.head.map((h) => (
                      <th key={h} className="table-head">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {s.table.rows.map((row) => (
                    <tr key={row[0]}>
                      {row.map((cell, i) => (
                        <td key={i} className={`table-cell ${i === 0 ? 'text-ink' : 'text-ink-2'}`}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {s.note && <p className="meta mt-3 leading-relaxed">{s.note}</p>}
        </Section>
      ))}
    </div>
  )
}

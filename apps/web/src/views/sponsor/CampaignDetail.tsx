/** One campaign, and the three questions you ask about it.
 *
 *  These used to be scattered: matching lived at the campaign's own address,
 *  the pipeline was a single org-wide page listing every offer ever sent, and
 *  analytics was a button on a card. So "how is the spring line going" meant
 *  visiting three places and filtering one of them by eye.
 *
 *  A campaign is the unit a sponsor actually thinks in, so it gets the tabs:
 *  who should be on it, what has been offered, and what came back. The org-wide
 *  view still exists — it moved to Analytics, where a cross-campaign question
 *  is the point rather than an accident of where the deals happened to live.
 */
import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { LoadError, PageLoading, StatusChip, Tabs } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney } from '../../lib/format'
import type { Campaign, SponsorWorkspace } from '../../types'
import CampaignAnalytics from './CampaignAnalytics'
import CampaignMatches from './CampaignMatches'
import SponsorPipeline from './Pipeline'

type Tab = 'athletes' | 'pipeline' | 'analytics'
const TABS: { key: Tab; label: string }[] = [
  { key: 'athletes', label: 'Athletes' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'analytics', label: 'Analytics' },
]

export default function CampaignDetail() {
  const { id } = useParams()
  const campaignId = Number(id)
  //: In the URL, so a tab is linkable and the back button steps through them.
  const [params, setParams] = useSearchParams()
  const raw = params.get('tab')
  const tab: Tab = TABS.some((t) => t.key === raw) ? (raw as Tab) : 'athletes'

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<SponsorWorkspace>('/api/sponsor/workspace')
      .then((ws) => {
        const found = ws.campaigns.find((c) => c.id === campaignId)
        if (!found) setError('That campaign is not on this account.')
        else setCampaign(found)
      })
      .catch((e) => setError(errorText(e)))
  }, [campaignId])

  if (!campaign) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <Link to="/sponsor" className="meta mb-3 inline-flex items-center gap-1.5 hover:text-accent">
        <ArrowLeft size={13} /> Campaigns
      </Link>

      <div className="mb-5">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-[30px] font-bold leading-none tracking-board text-ink">
            {campaign.name}
          </h1>
          <span className="tag">{campaign.category}</span>
          <StatusChip status={campaign.status} />
          <span className="tnum ml-auto text-sm text-ink-2">
            {fmtMoney(campaign.budget_eur_min)} – {fmtMoney(campaign.budget_eur_max)}
          </span>
        </div>
        {campaign.objective && <p className="mt-1.5 text-sm text-ink-3">{campaign.objective}</p>}
      </div>

      <div className="mb-5 max-w-lg">
        <Tabs<Tab>
          tabs={TABS}
          active={tab}
          onChange={(k) => setParams(k === 'athletes' ? {} : { tab: k }, { replace: true })}
        />
      </div>

      {tab === 'athletes' && <CampaignMatches embedded />}
      {tab === 'pipeline' && <SponsorPipeline campaignId={campaignId} embedded />}
      {tab === 'analytics' && <CampaignAnalytics embedded />}
    </div>
  )
}

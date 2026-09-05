/** One directory, two kinds of thing in it.
 *
 *  Athletes and clubs used to be separate nav items pointing at separate pages
 *  with separate search boxes and the same three filters — so "look something
 *  up on Stride" had two answers and you had to know which one before you
 *  started typing. The fan side already worked this way (Discover has always
 *  covered both); this brings the other roles in line with it.
 *
 *  The tab lives in the URL rather than in component state. `/clubs` was a real
 *  address that people have bookmarked and that the product links to from a
 *  dozen places, and a tab you cannot link to is a tab that breaks the back
 *  button.
 */
import { useNavigate, useLocation } from 'react-router-dom'
import AthletesDirectory from './AthletesDirectory'
import ClubsDirectory from './ClubsDirectory'
import { PageHeader, Tabs } from '../components/ui'

type Which = 'athletes' | 'clubs'

export default function Directory() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const which: Which = pathname.startsWith('/clubs') ? 'clubs' : 'athletes'

  return (
    <div>
      <PageHeader
        eyebrow="Browse"
        title="Directory"
        lede={which === 'athletes'
          ? 'Every listed athlete on Stride, searchable by name, sport and country.'
          : 'Every listed club. Clubs manage rosters of Stride athletes and publish sponsorship packages — including player-direct packages that back one athlete through the club.'}
      />

      <div className="mb-4 max-w-sm">
        <Tabs<Which>
          tabs={[{ key: 'athletes', label: 'Athletes' }, { key: 'clubs', label: 'Clubs' }]}
          active={which}
          onChange={(k) => navigate(k === 'clubs' ? '/clubs' : '/athletes')}
        />
      </div>

      {which === 'athletes' ? <AthletesDirectory embedded /> : <ClubsDirectory embedded />}
    </div>
  )
}

/** Reference lists for the fields where free text was the wrong control.
 *
 *  Typed country and sport fields produced "UK" and "United Kingdom" and "Great
 *  Britain" as three different countries, which then split the directory
 *  filters three ways. These are the canonical spellings.
 *
 *  Deliberately the *whole* list rather than the values already in the
 *  database: the facets endpoint answers "what do we have", which is the right
 *  question for a filter and the wrong one for a form. An athlete from East
 *  Timor has to be able to say so before there is an athlete from East Timor.
 */

export const SPORTS = [
  'Archery', 'Athletics', 'Badminton', 'Baseball', 'Basketball', 'Biathlon', 'Bobsleigh',
  'Boxing', 'Canoeing', 'Climbing', 'Cricket', 'CrossFit', 'Curling', 'Cycling', 'Darts',
  'Diving', 'Equestrian', 'Fencing', 'Field hockey', 'Figure skating', 'Football', 'Formula racing',
  'Golf', 'Gymnastics', 'Handball', 'Ice hockey', 'Judo', 'Karate', 'Kitesurfing', 'Lacrosse',
  'MMA', 'Motocross', 'Netball', 'Padel', 'Pentathlon', 'Powerlifting', 'Rowing', 'Rugby',
  'Sailing', 'Skateboarding', 'Skiing', 'Snowboarding', 'Squash', 'Surfing', 'Swimming',
  'Table tennis', 'Taekwondo', 'Tennis', 'Track cycling', 'Trail running', 'Triathlon',
  'Volleyball', 'Water polo', 'Weightlifting', 'Wrestling',
] as const

export const COUNTRIES = [
  'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Argentina', 'Armenia', 'Australia',
  'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 'Belarus', 'Belgium',
  'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil',
  'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada',
  'Cape Verde', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica',
  'Croatia', 'Cuba', 'Cyprus', 'Czechia', 'Denmark', 'Djibouti', 'Dominica',
  'Dominican Republic', 'East Timor', 'Ecuador', 'Egypt', 'El Salvador', 'Estonia', 'Eswatini',
  'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana',
  'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guyana', 'Haiti', 'Honduras', 'Hungary',
  'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy', 'Ivory Coast',
  'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kosovo', 'Kuwait', 'Kyrgyzstan',
  'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania',
  'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 'Mali', 'Malta', 'Mauritania',
  'Mauritius', 'Mexico', 'Moldova', 'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique',
  'Myanmar', 'Namibia', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria',
  'North Macedonia', 'Norway', 'Oman', 'Pakistan', 'Palestine', 'Panama', 'Papua New Guinea',
  'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar', 'Romania', 'Rwanda',
  'Samoa', 'San Marino', 'Saudi Arabia', 'Senegal', 'Serbia', 'Seychelles', 'Sierra Leone',
  'Singapore', 'Slovakia', 'Slovenia', 'Somalia', 'South Africa', 'South Korea', 'South Sudan',
  'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan',
  'Tajikistan', 'Tanzania', 'Thailand', 'Togo', 'Trinidad and Tobago', 'Tunisia', 'Turkey',
  'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom',
  'United States', 'Uruguay', 'Uzbekistan', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia',
  'Zimbabwe',
] as const

export const GENDERS = ['Female', 'Male', 'Other', 'Prefer not to say'] as const

/** Options for a `<select>`, with `current` kept even when it is not on the
 *  list. A profile saved before a spelling was standardised must not silently
 *  lose its value the first time somebody opens the form. */
export function withCurrent(options: readonly string[], current: string): string[] {
  return current && !options.includes(current) ? [current, ...options] : [...options]
}

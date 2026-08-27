import { Link } from 'react-router-dom'
import {
  Store,
  Stethoscope,
  ShoppingCart,
  Package,
  ShoppingBasket,
  Shirt,
  Wrench,
  MoreHorizontal,
} from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { formatNumber } from '../lib/format'

const CATEGORY_META = {
  restoran: { label: 'Restoran', icon: Store },
  klinik: { label: 'Klinik', icon: Stethoscope },
  marketplace: { label: 'Marketplace', icon: ShoppingCart },
  retail: { label: 'Retail', icon: Package },
  warung: { label: 'Warung', icon: ShoppingBasket },
  laundry: { label: 'Laundry', icon: Shirt },
  bengkel: { label: 'Bengkel', icon: Wrench },
  lainnya: { label: 'Lainnya', icon: MoreHorizontal },
}

export default function Businesses() {
  const { data, loading, error } = useFetch(() => api.listBusinesses(), [])

  if (loading) return <LoadingState label="Memuat businesses" />
  if (error) return <ErrorState message={error} />

  const grouped = data.reduce((acc, b) => {
    ;(acc[b.category] ||= []).push(b)
    return acc
  }, {})

  const categoryOrder = [
    'restoran',
    'warung',
    'klinik',
    'marketplace',
    'retail',
    'laundry',
    'bengkel',
    'lainnya',
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-xl text-text-primary">Businesses</h1>
        <p className="text-text-muted text-sm mt-1">
          Klien/bisnis yang datanya dikelola lewat platform ini, dikelompokkan per kategori.
        </p>
      </div>

      {data.length === 0 ? (
        <EmptyState label="Belum ada business. Upload data untuk membuat business pertama." />
      ) : (
        categoryOrder
          .filter((cat) => grouped[cat]?.length)
          .map((cat) => {
            const { label, icon: Icon } = CATEGORY_META[cat]
            return (
              <div key={cat}>
                <div className="flex items-center gap-2 mb-3">
                  <Icon size={15} className="text-accent" strokeWidth={1.75} />
                  <h2 className="text-sm font-medium text-text-primary">{label}</h2>
                  <span className="text-text-muted text-xs">({grouped[cat].length})</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {grouped[cat].map((b) => (
                    <Link
                      key={b.id}
                      to={`/businesses/${b.id}`}
                      className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 hover:border-accent/50 transition-colors"
                    >
                      <div className="text-text-primary text-sm font-medium truncate">
                        {b.name}
                      </div>
                      <div className="flex items-center gap-4 mt-4 pt-3 border-t border-ink-border text-xs">
                        <div>
                          <div className="font-display text-text-primary tabular-nums">
                            {b.total_sources}
                          </div>
                          <div className="text-text-muted text-[11px]">sources</div>
                        </div>
                        <div>
                          <div className="font-display text-text-primary tabular-nums">
                            {b.total_datasets}
                          </div>
                          <div className="text-text-muted text-[11px]">datasets</div>
                        </div>
                        <div>
                          <div className="font-display text-text-primary tabular-nums">
                            {formatNumber(b.total_records)}
                          </div>
                          <div className="text-text-muted text-[11px]">records</div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )
          })
      )}
    </div>
  )
}

export { CATEGORY_META }

import { useEffect, useState } from 'react'

/**
 * true cuando el elemento referenciado entra al viewport (carga diferida de paneles).
 */
export function useInView(ref, { rootMargin = '120px', threshold = 0.01 } = {}) {
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || inView) return undefined

    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return undefined
    }

    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true)
          obs.disconnect()
        }
      },
      { rootMargin, threshold },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [ref, inView, rootMargin, threshold])

  return inView
}

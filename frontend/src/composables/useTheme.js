/**
 * useTheme — Dynamisch tenant-thema laden (ADR-047 B5).
 *
 * Laadt /themes/{tenantId}.css als stylesheet in document.head. De
 * tenant-identifier is het `tenant_id` uit de auth-store (`auth.tenantId`);
 * `/auth/me` levert geen slug. Retourneert een Promise die resolvet zodra het
 * thema geladen is, zodat de eerste render pas na thema-activering plaatsvindt.
 */

let currentThemeLink = null

export function useTheme(tenantId) {
  return new Promise((resolve, reject) => {
    // Verwijder eerder geladen tenant-thema (bij tenant-switch)
    if (currentThemeLink) {
      currentThemeLink.remove()
      currentThemeLink = null
    }

    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = `/themes/${tenantId}.css`
    link.onload = () => resolve()
    link.onerror = () => reject(new Error(`Thema '${tenantId}' kon niet geladen worden`))
    document.head.appendChild(link)
    currentThemeLink = link
  })
}

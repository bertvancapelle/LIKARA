/** Tests — sessieVangrail: de verlopen-sessie-handler wist de sessie en leidt netjes naar login. */
import { describe, expect, it, vi } from 'vitest'
import { sessieVerlopenHandler } from '@/sessieVangrail'

function _router(route) {
  return { currentRoute: { value: route }, push: vi.fn() }
}
const _auth = () => ({ user: { sub: 'x' }, sessionType: 'tenant' })

describe('sessieVerlopenHandler', () => {
  it('wist de sessie en redirect naar login met sessie_verlopen + next (huidig pad)', () => {
    const router = _router({ fullPath: '/partijen/p1', meta: {} })
    const auth = _auth()
    sessieVerlopenHandler(router, auth)()
    expect(auth.user).toBeNull()
    expect(auth.sessionType).toBeNull()
    expect(router.push).toHaveBeenCalledWith({
      name: 'login',
      query: { sessie_verlopen: '1', next: '/partijen/p1' },
    })
  })

  it('geen next bij de wortel "/" (schone login-URL)', () => {
    const router = _router({ fullPath: '/', meta: {} })
    sessieVerlopenHandler(router, _auth())()
    expect(router.push).toHaveBeenCalledWith({ name: 'login', query: { sessie_verlopen: '1' } })
  })

  it('redirect NIET op een publieke route (al op login/callback)', () => {
    const router = _router({ fullPath: '/login', meta: { public: true } })
    const auth = _auth()
    sessieVerlopenHandler(router, auth)()
    expect(auth.user).toBeNull() // sessie wél gewist
    expect(router.push).not.toHaveBeenCalled() // maar geen dubbele redirect
  })
})

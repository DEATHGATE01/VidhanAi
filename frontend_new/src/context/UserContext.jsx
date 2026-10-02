import { useContext } from 'react'
import UserContext from './userContextObject'

// The hook module. Importers keep using '../context/UserContext' unchanged.
//
// This file exports a HOOK ONLY (no component), which is what keeps Fast Refresh
// healthy: a module exporting both a component and a hook gets invalidated on
// edit, and the running page then throws "useUser must be used inside a
// <UserProvider>" until it is fully reloaded. The provider component lives in
// UserProvider.jsx and the context object in userContextObject.js.

export function useUser() {
  const ctx = useContext(UserContext)
  if (!ctx) throw new Error('useUser must be used inside a <UserProvider>')
  return ctx
}

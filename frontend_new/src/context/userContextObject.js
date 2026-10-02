import { createContext } from 'react'

// The context OBJECT lives in its own module, and that is deliberate.
//
// Vite's React plugin refuses to Fast Refresh a module that exports both a
// component and a hook ("Could not Fast Refresh (\"useUser\" export is
// incompatible)"), so it INVALIDATES the module instead. Invalidating a module
// that holds a context object creates a new context, while components already on
// screen still sit under the provider from the old one — they then read `null`
// and throw "useUser must be used inside a <UserProvider>" until a full reload.
//
// Keeping the object here means the two refresh boundaries are clean:
//   UserProvider.jsx  exports a component only  -> remounts on edit
//   UserContext.jsx   exports a hook only       -> propagates to importers
// Neither can invalidate the context identity, so editing the provider (or
// anything else) no longer crashes the running page mid-demo.
const UserContext = createContext(null)

export default UserContext

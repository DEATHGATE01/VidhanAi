import { useEffect, useState } from 'react'
import { loginUser, registerUser } from '../services/api'
import UserContext from './userContextObject'

const STORAGE_KEY = 'vidhanai-user'

// Portal profile: sign up / sign in against the VidhanAI backend and remember
// the session in localStorage (demo-grade — no tokens). The stored email is the
// single source of truth for alert subscriptions, so users never retype it.
//
// This module exports the COMPONENT ONLY, so it is a clean Fast Refresh boundary.
// The hook lives in UserContext.jsx and the context object in
// userContextObject.js — see that file for why the split matters.
export function UserProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let stored = null
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) stored = JSON.parse(raw)
    } catch {
      /* localStorage unavailable — start signed out */
    }
    setUser(stored)
    setReady(true)
  }, [])

  const persist = (next) => {
    setUser(next)
    try {
      if (next) localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      else localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* ignore storage errors */
    }
  }

  const signIn = async (email, password) => {
    const data = await loginUser({ email, password })
    const account = data?.user
    if (!data?.success || !account) throw new Error(data?.error || 'Sign in failed')
    persist(account)
    return account
  }

  const signUp = async ({ email, username, password }) => {
    const data = await registerUser({ email, username, password })
    const account = data?.user
    if (!data?.success || !account) throw new Error(data?.error || 'Sign up failed')
    persist(account)
    return account
  }

  const signOut = () => persist(null)

  return (
    <UserContext.Provider value={{ user, ready, signIn, signUp, signOut }}>
      {children}
    </UserContext.Provider>
  )
}

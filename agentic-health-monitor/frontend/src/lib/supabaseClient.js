// Local auth + local DB — replaces Supabase entirely.
// No external network calls. All data stored in localStorage.

const SESSION_KEY = 'ahm_session'
const USERS_KEY = 'ahm_users'

function getUsers() {
  try { return JSON.parse(localStorage.getItem(USERS_KEY) || '{}') } catch { return {} }
}
function saveUsers(u) { localStorage.setItem(USERS_KEY, JSON.stringify(u)) }
function getStoredSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null') } catch { return null }
}
function getTable(name) {
  try { return JSON.parse(localStorage.getItem(`ahm_table_${name}`) || '[]') } catch { return [] }
}
function saveTable(name, rows) { localStorage.setItem(`ahm_table_${name}`, JSON.stringify(rows)) }

const _listeners = []

// ---------- query builder ----------
class QueryBuilder {
  constructor(table) {
    this._table = table
    this._filters = []
    this._orderKey = null
    this._orderAsc = true
    this._selectAll = true
  }
  select(cols) { this._selectAll = cols; return this }
  eq(key, value) { this._filters.push({ key, value }); return this }
  order(key, { ascending = true } = {}) { this._orderKey = key; this._orderAsc = ascending; return this }

  then(resolve, reject) {
    return Promise.resolve().then(() => {
      try {
        let rows = getTable(this._table)
        for (const f of this._filters) {
          rows = rows.filter(r => r[f.key] === f.value)
        }
        if (this._orderKey) {
          const k = this._orderKey
          const asc = this._orderAsc
          rows = [...rows].sort((a, b) => {
            const va = a[k], vb = b[k]
            if (va < vb) return asc ? -1 : 1
            if (va > vb) return asc ? 1 : -1
            return 0
          })
        }
        return resolve({ data: rows, error: null })
      } catch (e) {
        return resolve({ data: [], error: { message: e.message } })
      }
    }, reject)
  }
}

// ---------- supabase mock ----------
export const supabase = {
  auth: {
    async getSession() {
      return { data: { session: getStoredSession() } }
    },

    async signUp({ email, password }) {
      const users = getUsers()
      if (users[email]) {
        return { data: {}, error: { message: 'User already registered. Please log in.' } }
      }
      const user = { id: crypto.randomUUID(), email, createdAt: new Date().toISOString() }
      users[email] = { ...user, password }
      saveUsers(users)
      return { data: { user }, error: null }
    },

    async signInWithPassword({ email, password }) {
      const users = getUsers()
      const record = users[email]
      if (!record || record.password !== password) {
        return { data: {}, error: { message: 'Invalid email or password.' } }
      }
      const session = {
        user: { id: record.id, email: record.email },
        access_token: 'local',
      }
      localStorage.setItem(SESSION_KEY, JSON.stringify(session))
      _listeners.forEach(fn => fn('SIGNED_IN', session))
      return { data: { session }, error: null }
    },

    async signOut() {
      localStorage.removeItem(SESSION_KEY)
      _listeners.forEach(fn => fn('SIGNED_OUT', null))
      return { error: null }
    },

    onAuthStateChange(callback) {
      _listeners.push(callback)
      return {
        data: {
          subscription: {
            unsubscribe: () => _listeners.splice(_listeners.indexOf(callback), 1),
          },
        },
      }
    },
  },

  from(table) {
    return {
      // chained query builder
      select(cols) { return new QueryBuilder(table).select(cols) },

      insert(rows) {
        try {
          const all = getTable(table)
          const newRows = Array.isArray(rows) ? rows : [rows]
          const timestamped = newRows.map(r => ({
            id: r.id || crypto.randomUUID(),
            created_at: r.created_at || new Date().toISOString(),
            ...r,
          }))
          all.push(...timestamped)
          saveTable(table, all)
          return Promise.resolve({ data: timestamped, error: null })
        } catch (e) {
          return Promise.resolve({ data: null, error: { message: e.message } })
        }
      },
    }
  },
}

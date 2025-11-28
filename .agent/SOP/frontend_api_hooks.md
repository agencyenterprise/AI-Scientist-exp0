# SOP: Frontend API Hooks

## Related Documentation
- [Frontend Architecture](../System/frontend_architecture.md)
- [Project Architecture](../System/project_architecture.md)

---

## Overview

This SOP covers creating custom React hooks for API calls in the frontend. Use this procedure when you need to:
- Fetch data from the backend API
- Handle loading and error states
- Implement caching and debouncing
- Create reusable data fetching logic

---

## Prerequisites

- Node.js environment set up
- Understanding of React hooks (useState, useCallback, useRef, useMemo)
- Knowledge of the API endpoints you're integrating

---

## Step-by-Step Procedure

### 1. Define Types

```typescript
// frontend/src/types/myFeature.ts
export interface MyFeatureItem {
  id: string
  name: string
  description: string
  createdAt: string
}

export interface MyFeatureListResponse {
  items: MyFeatureItem[]
  total: number
  page: number
  pageSize: number
}

export interface MyFeatureState {
  items: MyFeatureItem[]
  total: number
  loading: boolean
  error: string | null
}
```

### 2. Create the Hook

```typescript
// frontend/src/hooks/useMyFeature.ts
import { useState, useCallback, useRef, useMemo } from "react"
import { config } from "@/lib/config"
import type {
  MyFeatureItem,
  MyFeatureListResponse,
  MyFeatureState
} from "@/types/myFeature"

interface UseMyFeatureReturn {
  // State
  state: MyFeatureState

  // Actions
  fetchItems: (page?: number) => Promise<void>
  createItem: (data: Omit<MyFeatureItem, "id" | "createdAt">) => Promise<MyFeatureItem>
  updateItem: (id: string, data: Partial<MyFeatureItem>) => Promise<MyFeatureItem>
  deleteItem: (id: string) => Promise<void>
  refresh: () => Promise<void>

  // Utilities
  getItemById: (id: string) => MyFeatureItem | undefined
  clearError: () => void
}

export function useMyFeature(): UseMyFeatureReturn {
  // State
  const [state, setState] = useState<MyFeatureState>({
    items: [],
    total: 0,
    loading: false,
    error: null
  })

  // Cache for avoiding duplicate requests
  const cacheRef = useRef<Map<string, MyFeatureItem[]>>(new Map())
  const currentPageRef = useRef(1)

  // Fetch items with pagination
  const fetchItems = useCallback(async (page = 1) => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    currentPageRef.current = page

    try {
      const response = await fetch(
        `${config.apiUrl}/my-feature?page=${page}&pageSize=25`,
        { credentials: "include" }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.status}`)
      }

      const data: MyFeatureListResponse = await response.json()

      setState(prev => ({
        ...prev,
        items: data.items,
        total: data.total,
        loading: false
      }))

      // Cache the results
      cacheRef.current.set(`page-${page}`, data.items)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      setState(prev => ({
        ...prev,
        loading: false,
        error: message
      }))
    }
  }, [])

  // Create new item
  const createItem = useCallback(async (
    data: Omit<MyFeatureItem, "id" | "createdAt">
  ): Promise<MyFeatureItem> => {
    const response = await fetch(`${config.apiUrl}/my-feature`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`Failed to create: ${response.status}`)
    }

    const created: MyFeatureItem = await response.json()

    // Update state with new item
    setState(prev => ({
      ...prev,
      items: [created, ...prev.items],
      total: prev.total + 1
    }))

    // Clear cache
    cacheRef.current.clear()

    return created
  }, [])

  // Update existing item
  const updateItem = useCallback(async (
    id: string,
    data: Partial<MyFeatureItem>
  ): Promise<MyFeatureItem> => {
    const response = await fetch(`${config.apiUrl}/my-feature/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`Failed to update: ${response.status}`)
    }

    const updated: MyFeatureItem = await response.json()

    // Update state
    setState(prev => ({
      ...prev,
      items: prev.items.map(item =>
        item.id === id ? updated : item
      )
    }))

    // Clear cache
    cacheRef.current.clear()

    return updated
  }, [])

  // Delete item
  const deleteItem = useCallback(async (id: string): Promise<void> => {
    const response = await fetch(`${config.apiUrl}/my-feature/${id}`, {
      method: "DELETE",
      credentials: "include"
    })

    if (!response.ok) {
      throw new Error(`Failed to delete: ${response.status}`)
    }

    // Update state
    setState(prev => ({
      ...prev,
      items: prev.items.filter(item => item.id !== id),
      total: prev.total - 1
    }))

    // Clear cache
    cacheRef.current.clear()
  }, [])

  // Refresh current page
  const refresh = useCallback(async () => {
    cacheRef.current.clear()
    await fetchItems(currentPageRef.current)
  }, [fetchItems])

  // Get item by ID from current state
  const getItemById = useCallback((id: string): MyFeatureItem | undefined => {
    return state.items.find(item => item.id === id)
  }, [state.items])

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }))
  }, [])

  // Memoize return value
  return useMemo(() => ({
    state,
    fetchItems,
    createItem,
    updateItem,
    deleteItem,
    refresh,
    getItemById,
    clearError
  }), [
    state,
    fetchItems,
    createItem,
    updateItem,
    deleteItem,
    refresh,
    getItemById,
    clearError
  ])
}
```

### 3. Add Debouncing (for Search)

```typescript
// frontend/src/hooks/useMyFeatureSearch.ts
import { useState, useCallback, useRef, useMemo } from "react"
import { config } from "@/lib/config"

interface UseMyFeatureSearchReturn {
  query: string
  results: MyFeatureItem[]
  loading: boolean
  error: string | null
  search: (query: string) => void
  clearSearch: () => void
}

export function useMyFeatureSearch(): UseMyFeatureSearchReturn {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<MyFeatureItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounce timer ref
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Search with debouncing
  const search = useCallback((searchQuery: string) => {
    setQuery(searchQuery)

    // Clear previous timer
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    // Don't search for empty queries
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    // Debounce the API call
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch(
          `${config.apiUrl}/my-feature/search?q=${encodeURIComponent(searchQuery)}`,
          { credentials: "include" }
        )

        if (!response.ok) {
          throw new Error("Search failed")
        }

        const data = await response.json()
        setResults(data.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search error")
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300) // 300ms debounce
  }, [])

  // Clear search
  const clearSearch = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    setQuery("")
    setResults([])
    setError(null)
  }, [])

  return useMemo(() => ({
    query,
    results,
    loading,
    error,
    search,
    clearSearch
  }), [query, results, loading, error, search, clearSearch])
}
```

### 4. Use the Hook in a Component

```typescript
// frontend/src/components/MyFeatureList.tsx
"use client"

import { useEffect } from "react"
import { useMyFeature } from "@/hooks/useMyFeature"

export function MyFeatureList() {
  const {
    state: { items, loading, error },
    fetchItems,
    deleteItem,
    refresh
  } = useMyFeature()

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  if (loading) {
    return <div>Loading...</div>
  }

  if (error) {
    return (
      <div className="text-red-500">
        Error: {error}
        <button onClick={refresh}>Retry</button>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {items.map(item => (
        <li key={item.id} className="flex justify-between p-2 border rounded">
          <span>{item.name}</span>
          <button
            onClick={() => deleteItem(item.id)}
            className="text-red-500"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/hooks/useMyFeature.ts` | Main feature hook |
| `src/hooks/useSearch.ts` | Example search hook with debouncing |
| `src/hooks/useAuth.ts` | Authentication hook |
| `src/types/` | Type definitions |
| `src/lib/config.ts` | API configuration |

---

## Hook Return Pattern

```typescript
interface UseHookReturn {
  // State (read-only)
  state: StateType
  // or individual state values:
  items: Item[]
  loading: boolean
  error: string | null

  // Actions (mutations)
  fetch: () => Promise<void>
  create: (data: CreateData) => Promise<Item>
  update: (id: string, data: UpdateData) => Promise<Item>
  delete: (id: string) => Promise<void>

  // Utilities (helpers)
  getById: (id: string) => Item | undefined
  validate: (data: Data) => boolean
  clear: () => void
}
```

---

## Common Patterns

### API Call with Credentials

```typescript
const response = await fetch(`${config.apiUrl}/endpoint`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include", // Required for auth cookies
  body: JSON.stringify(data)
})
```

### Error Response Handling

```typescript
interface ErrorResponse {
  detail: string
}

function isErrorResponse(data: unknown): data is ErrorResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    "detail" in data
  )
}

// Usage
if (!response.ok) {
  const data = await response.json()
  if (isErrorResponse(data)) {
    throw new Error(data.detail)
  }
  throw new Error(`Request failed: ${response.status}`)
}
```

### Caching with useRef

```typescript
const cacheRef = useRef<Map<string, Data>>(new Map())

const fetchWithCache = useCallback(async (key: string) => {
  // Check cache first
  if (cacheRef.current.has(key)) {
    return cacheRef.current.get(key)
  }

  // Fetch from API
  const data = await fetchData(key)

  // Store in cache
  cacheRef.current.set(key, data)

  return data
}, [])
```

---

## Common Pitfalls

- **Always use `useCallback`**: Prevents unnecessary re-renders
- **Always use `useMemo` for return value**: Maintains referential equality
- **Include `credentials: "include"`**: Required for authentication
- **Handle all error states**: Check `response.ok` before parsing JSON
- **Clear cache on mutations**: Invalidate cache after create/update/delete
- **Use `useRef` for mutable values**: Timers, caches, previous values
- **Don't call hooks conditionally**: Follow Rules of Hooks

---

## Verification

1. Test the hook in isolation:
   ```typescript
   const { state, fetchItems } = useMyFeature()
   useEffect(() => { fetchItems() }, [fetchItems])
   console.log(state)
   ```

2. Verify loading states appear correctly

3. Test error handling by simulating API errors

4. Check caching works (no duplicate requests)

5. Verify debouncing for search hooks (network tab)

6. Test mutations update state correctly

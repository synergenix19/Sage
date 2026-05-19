import '@testing-library/jest-dom'

// pool:forks passes --localstorage-file without a valid path, so jsdom's storage
// object has no setItem. Provide a working in-memory implementation for all tests.
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (i: number) => Object.keys(store)[i] ?? null,
  } satisfies Storage
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true })

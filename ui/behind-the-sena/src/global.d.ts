/// <reference types="vite/client" />
declare module '*.css'
declare module 'react/jsx-runtime'
declare module 'electron'
declare module 'path'
declare var process: any
declare var __dirname: string

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any
  }
}

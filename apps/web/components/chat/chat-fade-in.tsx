'use client'
import { motion } from 'framer-motion'

export function ChatFadeIn({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      className="flex h-full flex-col"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}

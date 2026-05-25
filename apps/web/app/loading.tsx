import { Skeleton } from '@cdai/ui'

export default function Loading() {
  return (
    <div className="flex h-dvh items-center justify-center p-8">
      <div className="w-full max-w-sm space-y-3">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  )
}

import { Skeleton } from '@cdai/ui'

export default function AppLoading() {
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center gap-3 border-b border-[var(--color-border)] pb-3">
        <Skeleton className="h-8 w-8 rounded-full" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="flex flex-1 flex-col gap-3 pt-2">
        <Skeleton className="h-10 w-2/3 self-end rounded-2xl" />
        <Skeleton className="h-16 w-3/4 rounded-2xl" />
        <Skeleton className="h-10 w-1/2 self-end rounded-2xl" />
        <Skeleton className="h-20 w-4/5 rounded-2xl" />
      </div>
      <Skeleton className="h-12 w-full rounded-full" />
    </div>
  )
}

import { tenant } from '@cdai/tenant'
import { VoiceBiomarker } from '@/components/voice-biomarker/voice-biomarker'

export default function BiomarkerPage() {
  if (!tenant.capabilities.voiceBiomarker) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <p className="text-center text-sm text-[var(--color-text-secondary)]">
          Voice biomarker analysis is not enabled for this organisation.
        </p>
      </div>
    )
  }
  return <VoiceBiomarker />
}

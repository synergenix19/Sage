import { notFound } from 'next/navigation'
import { Welcome } from '@/components/onboarding/steps/welcome'
import { Language } from '@/components/onboarding/steps/language'
import { Name } from '@/components/onboarding/steps/name'
import { AboutYou } from '@/components/onboarding/steps/about-you'
import { WhatMatters } from '@/components/onboarding/steps/what-matters'
import { Personalising } from '@/components/onboarding/steps/personalising'

const STEPS = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5', 'step-6']
const STEP_COMPONENTS = [Welcome, Language, Name, AboutYou, WhatMatters, Personalising]

interface Props { params: Promise<{ step: string }> }

export default async function OnboardingStepPage({ params }: Props) {
  const { step } = await params
  const idx = STEPS.indexOf(step)
  if (idx === -1) notFound()
  const StepComponent = STEP_COMPONENTS[idx]
  return <StepComponent />
}

export function generateStaticParams() {
  return STEPS.map((step) => ({ step }))
}

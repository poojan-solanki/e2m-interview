"use client";

import { useCallback, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { RateOverride, SampleHouse, StudioState, WizardStep } from "@/types";
import StudioHeader from "./StudioHeader";
import Step1Upload from "./steps/Step1Upload";
import Step2Zones from "./steps/Step2Zones";
import Step4Comparison from "./steps/Step4Comparison";
import Step5BoQ from "./steps/Step5BoQ";

const initialState: StudioState = {
  step: 1,
  maxStepReached: 1,
  house: null,
  activeMaterialId: null,
  assignments: {},
  rateOverrides: {},
  activeMaterialTab: "instant",
  renderedImageSrc: null,
};

const STEP_VARIANTS = {
  enter: { opacity: 0, x: 32 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -32 },
};

export default function StudioApp() {
  const [state, setState] = useState<StudioState>(initialState);

  // Used by "Continue"/"Next" buttons — always allowed, and unlocks that step (and
  // its header pip) for the rest of the session.
  const advanceToStep = (step: WizardStep) =>
    setState((s) => ({ ...s, step, maxStepReached: (Math.max(s.maxStepReached, step) as WizardStep) }));

  // Used by "Back" buttons and clicking a header step pip — only allowed to jump to
  // a step already reached, and never changes what's unlocked.
  const goToStep = (step: WizardStep) => setState((s) => (step <= s.maxStepReached ? { ...s, step } : s));

  const loadHouse = (house: SampleHouse) => {
    setState((s) => ({ ...s, house, step: 2, maxStepReached: 2, activeMaterialId: null }));
  };

  const setActiveMaterial = (materialId: string | null) => setState((s) => ({ ...s, activeMaterialId: materialId }));

  const assignMaterial = (zoneIds: string[], materialId: string) =>
    setState((s) => ({
      ...s,
      assignments: {
        ...s.assignments,
        ...Object.fromEntries(zoneIds.map((id) => [id, materialId])),
      },
    }));

  const unassignZone = (zoneId: string) =>
    setState((s) => {
      const next = { ...s.assignments };
      delete next[zoneId];
      return { ...s, assignments: next };
    });

  const setRateOverride = (zoneIds: string[], override: RateOverride) =>
    setState((s) => ({
      ...s,
      rateOverrides: {
        ...s.rateOverrides,
        ...Object.fromEntries(zoneIds.map((id) => [id, { ...s.rateOverrides[id], ...override }])),
      },
    }));

  const setMaterialTab = (tab: "instant" | "ai") => setState((s) => ({ ...s, activeMaterialTab: tab }));

  const setRenderedImage = useCallback(
    (src: string | null) => setState((s) => (s.renderedImageSrc === src ? s : { ...s, renderedImageSrc: src })),
    []
  );

  return (
    <div className="min-h-screen bg-bg">
      <StudioHeader currentStep={state.step} maxStepReached={state.maxStepReached} onStepClick={goToStep} />
      <AnimatePresence mode="wait">
        <motion.div
          key={state.step}
          variants={STEP_VARIANTS}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        >
          {state.step === 1 && <Step1Upload onSelectHouse={loadHouse} />}
          {state.step === 2 && state.house && (
            <Step2Zones
              house={state.house}
              activeMaterialId={state.activeMaterialId}
              assignments={state.assignments}
              onSetActiveMaterial={setActiveMaterial}
              onAssignMaterial={assignMaterial}
              onUnassignZone={unassignZone}
              onBack={() => goToStep(1)}
              onNext={() => advanceToStep(3)}
            />
          )}
          {state.step === 3 && state.house && (
            <Step4Comparison
              house={state.house}
              assignments={state.assignments}
              activeTab={state.activeMaterialTab}
              onTabChange={setMaterialTab}
              onRenderedImageChange={setRenderedImage}
              onBack={() => goToStep(2)}
              onNext={() => advanceToStep(4)}
            />
          )}
          {state.step === 4 && state.house && (
            <Step5BoQ
              house={state.house}
              assignments={state.assignments}
              rateOverrides={state.rateOverrides}
              onRateOverride={setRateOverride}
              renderedImageSrc={state.renderedImageSrc}
              onBack={() => goToStep(3)}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

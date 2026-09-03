"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { RateOverride, SampleHouse, StudioState, WizardStep } from "@/types";
import StudioHeader from "./StudioHeader";
import Step1Upload from "./steps/Step1Upload";
import Step2Zones from "./steps/Step2Zones";
import Step3Materials from "./steps/Step3Materials";
import Step4Comparison from "./steps/Step4Comparison";
import Step5BoQ from "./steps/Step5BoQ";

const initialState: StudioState = {
  step: 1,
  house: null,
  selectedZoneId: null,
  assignments: {},
  rateOverrides: {},
  activeMaterialTab: "instant",
};

const STEP_VARIANTS = {
  enter: { opacity: 0, x: 32 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -32 },
};

export default function StudioApp() {
  const [state, setState] = useState<StudioState>(initialState);

  const goToStep = (step: WizardStep) => setState((s) => ({ ...s, step }));

  const loadHouse = (house: SampleHouse) => {
    // Start on the largest assignable surface (typically the main wall) rather than
    // whichever zone happens to be first in segmentation order.
    const heroZone = house.zones
      .filter((z) => !z.isProtected)
      .sort((a, b) => Math.max(b.netAreaSqft, b.runningFeet) - Math.max(a.netAreaSqft, a.runningFeet))[0];
    setState((s) => ({
      ...s,
      house,
      step: 2,
      selectedZoneId: heroZone?.id ?? null,
    }));
  };

  const selectZone = (zoneId: string | null) => setState((s) => ({ ...s, selectedZoneId: zoneId }));

  const assignMaterial = (zoneIds: string[], materialId: string) =>
    setState((s) => ({
      ...s,
      assignments: {
        ...s.assignments,
        ...Object.fromEntries(zoneIds.map((id) => [id, materialId])),
      },
    }));

  const setRateOverride = (zoneIds: string[], override: RateOverride) =>
    setState((s) => ({
      ...s,
      rateOverrides: {
        ...s.rateOverrides,
        ...Object.fromEntries(zoneIds.map((id) => [id, { ...s.rateOverrides[id], ...override }])),
      },
    }));

  const setMaterialTab = (tab: "instant" | "ai") => setState((s) => ({ ...s, activeMaterialTab: tab }));

  return (
    <div className="min-h-screen bg-bg">
      <StudioHeader currentStep={state.step} />
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
              selectedZoneId={state.selectedZoneId}
              assignments={state.assignments}
              onSelectZone={selectZone}
              onNext={() => goToStep(3)}
            />
          )}
          {state.step === 3 && state.house && (
            <Step3Materials
              house={state.house}
              selectedZoneId={state.selectedZoneId}
              assignments={state.assignments}
              onAssignMaterial={assignMaterial}
              onNext={() => goToStep(4)}
            />
          )}
          {state.step === 4 && state.house && (
            <Step4Comparison
              house={state.house}
              assignments={state.assignments}
              activeTab={state.activeMaterialTab}
              onTabChange={setMaterialTab}
              onNext={() => goToStep(5)}
            />
          )}
          {state.step === 5 && state.house && (
            <Step5BoQ
              house={state.house}
              assignments={state.assignments}
              rateOverrides={state.rateOverrides}
              onRateOverride={setRateOverride}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

import {
  Brain,
  Activity,
  Waves,
  Hourglass,
  Network,
  Video,
  Zap,
  type LucideIcon,
} from "lucide-react";

export type AxisInputType = "MRI" | "fMRI" | "Video" | "EEG / Signal";

export type AxisId =
  | "axis1-alzheimer-dementia"
  | "axis2-parkinson-atypical"
  | "axis3-cerebellar-dysfunction"
  | "axis4-brain-aging"
  | "axis5-functional-connectivity"
  | "axis6-neuromotor-video"
  | "axis7-epilepsy-network";

export interface AxisDef {
  id: AxisId;
  number: number;
  slug: string;
  title: string;
  shortTitle: string;
  purpose: string;
  description: string;
  input: AxisInputType;
  acceptedFormats: string;
  endpoint: string;
  icon: LucideIcon;
  accent: string; // tailwind color class fragment for tone
}

export const AXES: AxisDef[] = [
  {
    id: "axis1-alzheimer-dementia",
    number: 1,
    slug: "alzheimer-dementia",
    title: "Alzheimer MRI Pattern Analysis",
    shortTitle: "Alzheimer MRI",
    purpose: "Structural MRI decision-support analysis for Alzheimer-like patterns.",
    description:
      "Structural MRI decision-support analysis for Alzheimer-like patterns, supported by explainability and cognitive-score correlation.",
    input: "MRI",
    acceptedFormats: ".nii, .nii.gz, .dcm, .zip",
    endpoint: "/api/axis1-alzheimer-dementia/analyze/",
    icon: Brain,
    accent: "from-[oklch(0.55_0.12_250)] to-[oklch(0.72_0.10_200)]",
  },
  {
    id: "axis2-parkinson-atypical",
    number: 2,
    slug: "parkinson-atypical",
    title: "Parkinson's vs Atypical Syndromes",
    shortTitle: "Parkinson & Atypical",
    purpose: "Differentiate Parkinson's disease from MSA, PSP and other atypical syndromes.",
    description:
      "MRI-based motor-region analysis with attention maps highlighting structural cues suggestive of atypical parkinsonism.",
    input: "MRI",
    acceptedFormats: ".nii, .nii.gz, .dcm",
    endpoint: "/api/axis2-parkinson-atypical/analyze/",
    icon: Activity,
    accent: "from-[oklch(0.60_0.13_220)] to-[oklch(0.78_0.07_295)]",
  },
  {
    id: "axis3-cerebellar-dysfunction",
    number: 3,
    slug: "cerebellar-dysfunction",
    title: "Cerebellar Dysfunction",
    shortTitle: "Cerebellum",
    purpose: "Quantify cerebellar involvement in cognitive and motor dysfunction.",
    description:
      "Region-level cerebellar profiling to surface subtle structural changes that may contribute to dementia or ataxia.",
    input: "MRI",
    acceptedFormats: ".nii, .nii.gz, .dcm",
    endpoint: "/api/axis3-cerebellar-dysfunction/analyze/",
    icon: Waves,
    accent: "from-[oklch(0.65_0.13_165)] to-[oklch(0.72_0.10_200)]",
  },
  {
    id: "axis4-brain-aging",
    number: 4,
    slug: "brain-aging",
    title: "Uneven Brain Aging",
    shortTitle: "Brain Aging",
    purpose: "Detect regional brain-age gaps versus chronological age.",
    description:
      "Voxel-wise brain age estimation that highlights regions aging faster than expected for the patient profile.",
    input: "MRI",
    acceptedFormats: ".nii/.gz, .zip (hdr+img), .hdr+.img pair, .png/.jpg",
    endpoint: "/api/axis4-brain-aging/analyze/",
    icon: Hourglass,
    accent: "from-[oklch(0.65_0.13_220)] to-[oklch(0.78_0.07_295)]",
  },
  {
    id: "axis5-functional-connectivity",
    number: 5,
    slug: "functional-connectivity",
    title: "Hidden Cognitive Effort",
    shortTitle: "Functional Connectivity",
    purpose: "Reveal altered functional connectivity and hidden cognitive effort.",
    description:
      "fMRI-based network analysis surfaces compensatory or high-effort connectivity patterns invisible to standard reads.",
    input: "fMRI",
    acceptedFormats: ".nii, .nii.gz",
    endpoint: "/api/axis5-functional-connectivity/analyze/",
    icon: Network,
    accent: "from-[oklch(0.55_0.12_250)] to-[oklch(0.78_0.07_295)]",
  },
  {
    id: "axis6-neuromotor-video",
    number: 6,
    slug: "neuromotor-video",
    title: "Neuromotor Video Analysis",
    shortTitle: "Neuromotor Video",
    purpose: "Detect gait, posture and tremor anomalies from clinical video.",
    description:
      "Pose-aware video analysis flags movement anomalies with timestamped markers and key-frame interpretation.",
    input: "Video",
    acceptedFormats: ".mp4, .mov, .webm",
    endpoint: "/api/axis6-neuromotor-video/analyze/",
    icon: Video,
    accent: "from-[oklch(0.70_0.11_195)] to-[oklch(0.65_0.14_165)]",
  },
  {
    id: "axis7-epilepsy-network",
    number: 7,
    slug: "epilepsy-network",
    title: "Epilepsy Vulnerability",
    shortTitle: "Epilepsy Network",
    purpose: "Surface network instability patterns linked to epilepsy vulnerability.",
    description:
      "Multimodal seizure-signal analysis highlights instability windows and informative channels suggestive of heightened epilepsy vulnerability.",
    input: "EEG / Signal",
    acceptedFormats: "patient run folder (.edf/.bdf)",
    endpoint: "/api/axis7-epilepsy-network/analyze/",
    icon: Zap,
    accent: "from-[oklch(0.68_0.18_60)] to-[oklch(0.78_0.07_295)]",
  },
];

export const getAxisBySlug = (slug: string) => AXES.find((a) => a.slug === slug);
export const getAxisById = (id: AxisId) => AXES.find((a) => a.id === id)!;

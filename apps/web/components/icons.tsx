import type { SVGProps } from "react";

import type { Label } from "../lib/contract";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      width={18}
      height={18}
      {...props}
    >
      {children}
    </svg>
  );
}

export function PencilIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 20l4-1 10.5-10.5a2.12 2.12 0 0 0-3-3L5 16l-1 4Z" />
      <path d="M14 7l3 3" />
    </Icon>
  );
}

export function EraserIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M8.5 19H20" />
      <path d="M5.4 15.6l8.5-8.5a2 2 0 0 1 2.8 0l2.2 2.2a2 2 0 0 1 0 2.8L12.2 19H8.8l-3.4-3.4Z" />
      <path d="M9.6 11.4l5 5" />
    </Icon>
  );
}

export function UndoIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 14L4 9l5-5" />
      <path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" />
    </Icon>
  );
}

export function TrashIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M10 11v6M14 11v6" />
      <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" />
    </Icon>
  );
}

export function PauseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 5v14M15 5v14" />
    </Icon>
  );
}

export function PlayIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M7 5l12 7-12 7V5Z" />
    </Icon>
  );
}

export function ResetIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 12a8 8 0 1 0 2.4-5.7" />
      <path d="M4 4v4h4" />
    </Icon>
  );
}

export function ArrowDownIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </Icon>
  );
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </Icon>
  );
}

export function ArrowUpRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M7 17L17 7M8 7h9v9" />
    </Icon>
  );
}

export function SparkIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.5 2.5M15.2 15.2l2.5 2.5M6.3 17.7l2.5-2.5M15.2 8.8l2.5-2.5" />
    </Icon>
  );
}

export function GitHubIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden width={18} height={18} {...props}>
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z" />
    </svg>
  );
}

/** A small hand-drawn picture of each class, for chips and the result card. */
export function LabelIcon({ label, ...props }: IconProps & { label: Label }) {
  switch (label) {
    case "sun":
      return (
        <Icon {...props}>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" />
        </Icon>
      );
    case "cloud":
      return (
        <Icon {...props}>
          <path d="M7 18.5h10.2a4 4 0 0 0 .4-7.98A5.6 5.6 0 0 0 6.9 9.7 4.4 4.4 0 0 0 7 18.5Z" />
        </Icon>
      );
    case "tree":
      return (
        <Icon {...props}>
          <circle cx="12" cy="9" r="5.5" />
          <path d="M12 14.5V21M9 21h6M12 17l-2-1.6M12 16l2-1.4" />
        </Icon>
      );
    case "flower":
      return (
        <Icon {...props}>
          <circle cx="12" cy="8" r="1.8" />
          <path d="M12 4.2a2 2 0 1 1 3.3 2.4 2 2 0 1 1-1.2 3.7A2 2 0 1 1 10 10.3a2 2 0 1 1-1.3-3.7A2 2 0 1 1 12 4.2Z" />
          <path d="M12 12v9M12 17c-1.8 0-3.2-.9-3.8-2.5 1.8 0 3.2.8 3.8 2.5Z" />
        </Icon>
      );
    case "car":
      return (
        <Icon {...props}>
          <path d="M3 16v-3.2l2.2-4.3h8.4l3.2 4.3H20a1 1 0 0 1 1 1V16" />
          <path d="M5.5 12.8h11" />
          <circle cx="7.5" cy="16.5" r="2" />
          <circle cx="16.5" cy="16.5" r="2" />
          <path d="M9.5 16.5h5" />
        </Icon>
      );
    case "cat":
      return (
        <Icon {...props}>
          <path d="M6.5 9.5L5.5 4l4 2.6h5L18.5 4l-1 5.5" />
          <path d="M6.5 9.5a6 6 0 1 0 11 0" />
          <path d="M9.5 12.5h.01M14.5 12.5h.01M12 14.5v1M3.5 15l4-.5M3.5 17.5l4-1M20.5 15l-4-.5M20.5 17.5l-4-1" />
        </Icon>
      );
  }
}

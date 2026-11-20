export type StaffDeployment = {
  origin: string;
  pin: string;
} & (
  | { rpId: string; version: 'staff-deployment-v2'; paperPilot: false }
  | { rpId: null; version: 'staff-paper-pilot-origin-v1'; paperPilot: true }
);

// Vite injects only a verified profile. Server authorization is independent.
declare const __STAFF_DEPLOYMENT__: StaffDeployment | null;

export function activeStaffDeployment(): StaffDeployment | undefined {
  const deployment = __STAFF_DEPLOYMENT__;
  return deployment && window.isSecureContext && window.location.origin === deployment.origin
    ? deployment : undefined;
}

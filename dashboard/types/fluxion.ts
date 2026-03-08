// FLUXION — TypeScript type definitions v2

export type UserRole = 'super_admin' | 'fleet_manager' | 'driver';

export type PointType =
  | 'trash_bin' | 'hotel' | 'restaurant' | 'pharmacy' | 'hospital'
  | 'industrial' | 'commercial' | 'school' | 'office' | 'market'
  | 'generic' | 'depot' | 'refuel' | 'wash';

export const POINT_TYPE_ICONS: Record<PointType | string, string> = {
  trash_bin: '🗑️',
  hotel: '🏨',
  restaurant: '🍽️',
  pharmacy: '💊',
  hospital: '🏥',
  industrial: '🏭',
  commercial: '🏪',
  school: '🏫',
  office: '🏢',
  market: '🛒',
  generic: '📍',
  depot: '📦',
  refuel: '⛽',
  wash: '🚿',
};

export interface Zone {
  id: number;
  x: number;
  y: number;
  lat: number;
  lon: number;
  volume_estime: number;
  fill_level: number;
  type: PointType | string;
  name: string;
  city?: string;
  collected?: boolean;
  collected_by?: number | null;
}

export interface Camion {
  id: number;
  capacite: number;
  charge_actuelle: number;
  lat: number;
  lon: number;
  on_duty: boolean;
  type?: string;
  city?: string;
}

export interface RoutePoint {
  x: number;
  y: number;
  lat?: number;
  lon?: number;
  id: number;
  type?: string;
}

export interface Route {
  camion_id: number;
  points: RoutePoint[];
  distance_km?: number;
}

export interface DepotPoint {
  id: number | string;
  lat: number;
  lon: number;
  name: string;
  type: 'depot' | 'refuel' | 'wash';
}

export interface SimulationMetrics {
  naive_distance_km: number;
  optimized_distance_km: number;
  distance_saved_km: number;
  fuel_saved_l: number;
  co2_reduced_kg: number;
  money_saved: number;
  fuel_consumed_l: number;
  money_consumed: number;
  time_elapsed_min: number;
}

export interface SimulationEvent {
  type: string;
  timestamp?: string;
  details?: Record<string, unknown>;
  message?: string;
  zone_id?: number;
  camion_id?: number;
}

export interface SimulationState {
  status: 'running' | 'paused';
  zones: Zone[];
  camions: Camion[];
  recent_events: SimulationEvent[];
  routes: Route[];
  depot?: DepotPoint;
  refuel_points?: DepotPoint[];
  metrics?: SimulationMetrics;
}

export interface SavingsMetrics {
  money_saved: number;
  fuel_saved_l: number;
  co2_reduced_kg: number;
  distance_saved_km: number;
  fuel_consumed_l?: number;
  money_consumed?: number;
  time_elapsed_min?: number;
}

export interface NSGAWeights {
  distance: number;
  co2: number;
  satisfaction: number;
  equite: number;
}

export type FillStatus = 'ok' | 'warning' | 'urgent' | 'critical' | 'collected';

export function getFillStatus(level: number, collected?: boolean): FillStatus {
  if (collected) return 'collected';
  if (level >= 95) return 'critical';
  if (level >= 90) return 'urgent';
  if (level >= 70) return 'warning';
  return 'ok';
}

export const FILL_COLORS: Record<FillStatus, string> = {
  ok: '#22c55e',   // green-500
  warning: '#f59e0b',   // amber-500
  urgent: '#ef4444',   // red-500
  critical: '#7c3aed',   // violet-600
  collected: '#6b7280',   // gray-500
};

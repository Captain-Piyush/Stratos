import { ProvenanceValue } from '../types/backend';

export function getCalibratedValue(val: ProvenanceValue | undefined | null, fallback: number): number {
    if (!val || typeof val.value !== 'number') return fallback;
    return val.value;
}

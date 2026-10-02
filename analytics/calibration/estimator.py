import pandas as pd
import numpy as np
from scipy import stats
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

def run_empirical_calibration(df: pd.DataFrame) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Runs empirical parameter estimation on the calibration dataset.
    Returns:
        calibrated_params: Dictionary of parameters ready for CalibrationProfile.
        report_data: Dictionary of statistics and metadata for the report.
    """
    report_data = {}
    calibrated_params = {
        'degradation_slopes': {},
        'compound_deltas': {},
        'circuit_pit_loss': {},
        'fallback_degradation': {
            'value': 0.08,
            'source': 'PRIOR',
            'sample_size': 0,
            'uncertainty': 0.0,
            'quality_status': 'ACCEPTED'
        },
        'fallback_compound_delta': {
            'value': 0.6,
            'source': 'PRIOR',
            'sample_size': 0,
            'uncertainty': 0.0,
            'quality_status': 'ACCEPTED'
        }
    }

    # 1. Pit Loss Estimation
    # Fetch directly from DB since pit_time_loss is not in Phase 2 features
    from database.connection import db
    if db.client is None:
        db.connect()
    
    session_keys = [int(k) for k in df['session_key'].unique()]
    pit_stops_cursor = db.get_collection('pit_stops').find({"session_key": {"$in": session_keys}})
    pits_df = pd.DataFrame(list(pit_stops_cursor))
    
    if not pits_df.empty:
        # Exclude malformed data (pit stops < 15s are physically impossible without drive-throughs or errors)
        valid_pits = pits_df[pits_df['pit_duration'] >= 15].copy()
        
        # Identify extreme outliers (e.g. > 45s) which represent red-flags, front-wing repairs, or penalties
        extreme_mask = valid_pits['pit_duration'] > 45
        extreme_count = extreme_mask.sum()
        clean_pits = valid_pits[~extreme_mask].copy()
        
        if not clean_pits.empty:
            median_loss = float(clean_pits['pit_duration'].median())
            mad = float((clean_pits['pit_duration'] - median_loss).abs().median() * 1.4826)
            
            calibrated_params['pit_loss'] = {
                'value': median_loss,
                'source': 'CALIBRATED',
                'sample_size': len(clean_pits),
                'uncertainty': mad,
                'quality_status': 'ACCEPTED'
            }
            
            report_data['pit_loss'] = {
                'robust_central': median_loss,
                'dispersion': mad,
                'p10': float(clean_pits['pit_duration'].quantile(0.1)),
                'p50': median_loss,
                'p90': float(clean_pits['pit_duration'].quantile(0.9)),
                'sample_size': len(clean_pits),
                'excluded_direct': int(extreme_count),
                'inferred_kept_separate': 0,
                'direct_vs_inferred': "DIRECT (from pit_stops collection)",
                'exclusion_rationale': "Excluded pit durations > 45s as nonstandard events (red-flags, repairs, drive-through penalties)."
            }
            
            # Circuit specific pit loss
            for session_key, group in valid_pits.groupby('session_key'):
                grp_clean = group[group['pit_duration'] <= 45]
                grp_extreme = group[group['pit_duration'] > 45]
                if len(grp_clean) >= 5:
                    c_median = float(grp_clean['pit_duration'].median())
                    c_mad = float((grp_clean['pit_duration'] - c_median).abs().median() * 1.4826)
                    # Quality gate for circuit: mad must be < 3.0s, outlier rate < 10%, and no red-flag scale outliers
                    outlier_rate = len(grp_extreme) / len(group)
                    if c_mad < 3.0 and outlier_rate < 0.1 and group['pit_duration'].max() < 120:
                        calibrated_params['circuit_pit_loss'][int(session_key)] = {
                            'value': c_median,
                            'source': 'CALIBRATED',
                            'sample_size': len(grp_clean),
                            'uncertainty': c_mad,
                            'quality_status': 'ACCEPTED'
                        }
                    else:
                        calibrated_params['circuit_pit_loss'][int(session_key)] = {
                            'value': median_loss,
                            'source': 'FALLBACK',
                            'sample_size': len(grp_clean),
                            'uncertainty': c_mad,
                            'quality_status': 'REJECTED'
                        }
                else:
                    calibrated_params['circuit_pit_loss'][int(session_key)] = {
                        'value': median_loss,
                        'source': 'FALLBACK',
                        'sample_size': len(grp_clean),
                        'uncertainty': 0.0,
                        'quality_status': 'REJECTED'
                    }
        else:
            # Fallback
            calibrated_params['pit_loss'] = {
                'value': 24.0,
                'source': 'FALLBACK',
                'sample_size': 0,
                'uncertainty': 1.0,
                'quality_status': 'REJECTED'
            }
            report_data['pit_loss'] = {
                'robust_central': 24.0, 'dispersion': 1.0, 'p10': 22.0, 'p50': 24.0, 'p90': 26.0,
                'sample_size': 0, 'excluded_direct': 0, 'inferred_kept_separate': 0,
                'direct_vs_inferred': "DEFAULT (No valid clean pits found)", 'exclusion_rationale': "N/A"
            }
    else:
        calibrated_params['pit_loss'] = {
            'value': 24.0,
            'source': 'FALLBACK',
            'sample_size': 0,
            'uncertainty': 1.0,
            'quality_status': 'REJECTED'
        }
        report_data['pit_loss'] = {
            'robust_central': 24.0, 'dispersion': 1.0, 'p10': 22.0, 'p50': 24.0, 'p90': 26.0,
            'sample_size': 0, 'excluded_direct': 0, 'inferred_kept_separate': 0,
            'direct_vs_inferred': "DEFAULT (No pit data)", 'exclusion_rationale': "N/A"
        }

    # 2. Setup Multiple Regression for Pace (Fuel, Compound Deltas, Degradation)
    # Exclude laps where pit_out == True for clean pace.
    pace_df = df[~df['pit_out'] & (df['lap_number'] > 1)].copy()
    
    if 'lap_time' in pace_df.columns:
        pace_df['lap_duration'] = pace_df['lap_time']
        
    # Robust Filtering: exclude lap times > 105% of the driver's session median
    # This removes traffic, mistakes, and VSC ends not properly flagged.
    driver_medians = pace_df.groupby(['session_key', 'driver_number'])['lap_duration'].transform('median')
    pace_df = pace_df[pace_df['lap_duration'] < (driver_medians * 1.05)]
    
    # Isolate "Clean Air" pace by removing laps heavily affected by traffic (DRS / dirty air)
    if 'cars_within_1s' in pace_df.columns:
        pace_df = pace_df[pace_df['cars_within_1s'] == 0]
    
    pace_df['session_driver'] = pace_df['session_key'].astype(str) + "_" + pace_df['driver_number'].astype(str)
    
    compounds = ['SOFT', 'MEDIUM', 'HARD']
    pace_df = pace_df[pace_df['tyre_compound'].isin(compounds)]
    
    # Fuel effect is unidentifiable due to collinearity with tyre age
    # Apply a fixed prior to isolate degradation
    prior_fuel_effect = 0.06
    y_adjusted = pace_df['lap_duration'].values + (pace_df['lap_number'].values * prior_fuel_effect)
    
    # Compounds (Base = SOFT)
    X_med = (pace_df['tyre_compound'] == 'MEDIUM').astype(float).values
    X_hard = (pace_df['tyre_compound'] == 'HARD').astype(float).values
    
    # Degradation (Age)
    X_deg_soft = ((pace_df['tyre_compound'] == 'SOFT') * pace_df['tyre_age']).values
    X_deg_med = ((pace_df['tyre_compound'] == 'MEDIUM') * pace_df['tyre_age']).values
    X_deg_hard = ((pace_df['tyre_compound'] == 'HARD') * pace_df['tyre_age']).values
    
    session_drivers = pace_df['session_driver'].unique()
    X_dummies = pd.get_dummies(pace_df['session_driver']).values
    
    # Drop X_fuel from design matrix
    X = np.column_stack([X_med, X_hard, X_deg_soft, X_deg_med, X_deg_hard, X_dummies])
    
    # Solve using ordinary least squares since collinearity is removed
    beta, residuals, rank, s = np.linalg.lstsq(X, y_adjusted, rcond=None)
    
    y_pred = X @ beta
    resids = y_adjusted - y_pred
    mse = np.sum(resids**2) / (len(y_adjusted) - X.shape[1])
    
    # Variance of coefficients
    XtX = X.T @ X
    XtX += np.eye(XtX.shape[0]) * 1e-6 # small eps for numerical stability
    var_beta = mse * np.linalg.inv(XtX).diagonal()
    se_beta = np.sqrt(np.abs(var_beta))
    
    calibrated_params['fuel_burn_effect'] = {
        'value': prior_fuel_effect,
        'source': 'PRIOR',
        'sample_size': 0,
        'uncertainty': 0.0,
        'quality_status': 'ACCEPTED'
    }
    
    n_soft = int(np.sum(pace_df['tyre_compound'] == 'SOFT'))
    n_med = int(np.sum(pace_df['tyre_compound'] == 'MEDIUM'))
    n_hard = int(np.sum(pace_df['tyre_compound'] == 'HARD'))
    
    calibrated_params['compound_deltas']['SOFT'] = {
        'value': 0.0,
        'source': 'CALIBRATED',
        'sample_size': n_soft,
        'uncertainty': 0.0,
        'quality_status': 'ACCEPTED'
    }
    calibrated_params['compound_deltas']['MEDIUM'] = {
        'value': float(beta[0]),
        'source': 'CALIBRATED',
        'sample_size': n_med,
        'uncertainty': float(se_beta[0]),
        'quality_status': 'ACCEPTED'
    }
    calibrated_params['compound_deltas']['HARD'] = {
        'value': float(beta[1]),
        'source': 'CALIBRATED',
        'sample_size': n_hard,
        'uncertainty': float(se_beta[1]),
        'quality_status': 'ACCEPTED'
    }
    
    calibrated_params['degradation_slopes']['SOFT'] = {
        'value': float(beta[2]),
        'source': 'CALIBRATED',
        'sample_size': n_soft,
        'uncertainty': float(se_beta[2]),
        'quality_status': 'ACCEPTED'
    }
    calibrated_params['degradation_slopes']['MEDIUM'] = {
        'value': float(beta[3]),
        'source': 'CALIBRATED',
        'sample_size': n_med,
        'uncertainty': float(se_beta[3]),
        'quality_status': 'ACCEPTED'
    }
    calibrated_params['degradation_slopes']['HARD'] = {
        'value': float(beta[4]),
        'source': 'CALIBRATED',
        'sample_size': n_hard,
        'uncertainty': float(se_beta[4]),
        'quality_status': 'ACCEPTED'
    }
    
    report_data['tyre_model'] = {
        'SOFT': {'estimate': float(beta[2]), 'se': float(se_beta[2]), 'n': n_soft},
        'MEDIUM': {'estimate': float(beta[3]), 'se': float(se_beta[3]), 'n': n_med},
        'HARD': {'estimate': float(beta[4]), 'se': float(se_beta[4]), 'n': n_hard},
    }
    
    report_data['compound_model'] = {
        'MEDIUM_vs_SOFT': {'estimate': float(beta[0]), 'se': float(se_beta[0])},
        'HARD_vs_SOFT': {'estimate': float(beta[1]), 'se': float(se_beta[1])},
    }
    
    report_data['fuel_model'] = {
        'effect': calibrated_params['fuel_burn_effect']['value'],
        'se': 0.0,
        'method': "FUEL_EFFECT_UNIDENTIFIABLE (Fixed prior applied to avoid collinearity)"
    }
    
    # 3. Test Linearity
    X_deg_soft_sq = X_deg_soft ** 2
    X_sq = np.column_stack([X, X_deg_soft_sq])
    beta_sq, _, _, _ = np.linalg.lstsq(X_sq, y_adjusted, rcond=None)
    y_pred_sq = X_sq @ beta_sq
    mse_sq = np.sum((y_adjusted - y_pred_sq)**2) / (len(y_adjusted) - X_sq.shape[1])
    
    report_data['linearity_test'] = {
        'linear_mse': float(mse),
        'quadratic_mse': float(mse_sq),
        'conclusion': 'Linear remains appropriate for simplicity' if mse_sq > mse * 0.95 else 'Quadratic fits significantly better, but linear kept for Phase 3 compatibility'
    }
    
    # 4. Residual Model & Strategy Uncertainty
    calibrated_params['residuals'] = {
        'mean': {
            'value': float(np.mean(resids)),
            'source': 'CALIBRATED',
            'sample_size': len(resids),
            'uncertainty': 0.0,
            'quality_status': 'ACCEPTED'
        },
        'std': {
            'value': float(np.std(resids)),
            'source': 'CALIBRATED',
            'sample_size': len(resids),
            'uncertainty': 0.0,
            'quality_status': 'ACCEPTED'
        }
    }
    calibrated_params['degradation_uncertainty'] = {
        'value': float(np.std(resids)) * 0.1, # Empirical proxy for growth
        'source': 'CALIBRATED',
        'sample_size': len(resids),
        'uncertainty': 0.0,
        'quality_status': 'ACCEPTED'
    }
    
    report_data['residuals'] = {
        'mean': calibrated_params['residuals']['mean']['value'],
        'std': calibrated_params['residuals']['std']['value'],
        'p10': float(np.percentile(resids, 10)),
        'p25': float(np.percentile(resids, 25)),
        'p50': float(np.percentile(resids, 50)),
        'p75': float(np.percentile(resids, 75)),
        'p90': float(np.percentile(resids, 90)),
        'is_gaussian': bool(stats.normaltest(resids)[1] > 0.05) if len(resids) >= 8 else True
    }
    
    # Fallback rules
    report_data['fallback_hierarchy'] = (
        "1. Pit Loss: Circuit-specific Pit Loss -> Global Pit Loss -> 24.0s\n"
        "2. Tyre Degradation: Calibrated Profile -> GLOBAL_FALLBACK_TYRE_DEGRADATION (0.08s/lap)\n"
        "3. Compound Pace Delta: Calibrated Profile -> GLOBAL_FALLBACK_COMPOUND_PACE (0.6s/lap)\n"
        "Legacy hardcoded values will NOT silently override the calibration profile."
    )
    
    return calibrated_params, report_data

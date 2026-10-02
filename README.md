# STRATOS

**F1 Strategy Intelligence Engine**

*Real-time race strategy simulation and decision intelligence.*

---

## Overview

Motorsport strategy decisions are historically reliant on rigid pre-race heuristics, manually parameterized lap-time models, and reactionary intuition. 
STRATOS solves this by replacing manual priors with empirical calibration and evaluating thousands of probabilistic branches via Monte Carlo simulation in real-time.

This project is a complete end-to-end strategy intelligence platform consisting of a historical data ingestion pipeline, a statistical calibration engine, a high-performance forward simulator, and a React-based Race Engineer Console.

## Problem

Modern race strategy requires balancing upside potential against asymmetric downside risks (traffic, tyre cliff, safety cars). Rigid algebraic models fail because they don't capture the interacting probabilities of a 20-car grid.

## Architecture

```text
OpenF1 API
  ↓ (Ingestion)
MongoDB (Raw Events)
  ↓ (Feature Engine)
Calibrated Model
  ↓ (Simulation Engine + Monte Carlo)
Decision Engine
  ↓ (FastAPI WebSocket)
React / Plotly Console
```

## How STRATOS Works

### Simulation
The physics-informed forward simulation models lap-by-lap progression. It tracks compound degradation, fuel burn, pit-loss, and traffic intervals using a robust state machine (`CanonicalRaceState`).

### Monte Carlo
Uncertainty is injected probabilistically. The engine samples from traffic density distributions, pit-stop variance models, and driver pacing variances to build a robust `P10–P90 simulated range`.

### Decision Engine
Candidates are scored against a defined Decision Objective (e.g., *Minimize Total Race Time*) and filtered by Constraints (e.g., mandatory compound usage, maximum pit windows). The system assigns a categorical **Decision Confidence** (HIGH / MEDIUM / LOW) based on statistical robustness vs baseline.

### Historical Replay
Powered by a deterministic `ReplayStreamAdapter`, the platform can chronologically query MongoDB and strictly emit `CanonicalRaceState` blocks exactly as they would have occurred live, with **zero look-ahead bias** (hindsight protected).

### Calibration
Pace offsets, compound deltas, and tyre degradation slopes are empirically calibrated using robust regression over the historical trace (Phase 5B).

### Validation
STRATOS models are validated retrospectively on deterministic holdout datasets.

**Phase 5C Validation Set Metrics:**
- **Holdout Races:** Bahrain 2023, Spa 2023, Austin 2023
- **Corrected MAE:** 68.89s
- **Corrected Median Absolute Error:** 12.05s
- **P10–P90 empirical coverage:** 30.6%

*Note: V2 reproduced the predictive performance of the hardcoded baseline on the current holdout set while replacing manually specified race-model parameters with empirically calibrated parameters. Validation results are historical retrospective evaluation and not evidence of guaranteed real-world race performance.*

### Live Architecture
The engine is driven by a `Live OpenF1 Adapter` connecting directly to WebSockets. Currently marked as `LIVE_ADAPTER_IMPLEMENTED` but `CREDENTIALS_NOT_AVAILABLE` for real-time race sessions outside of the testing lab.

## Tech Stack
- **Backend:** Python 3.12, FastAPI, Pandas, Pytest
- **Database:** MongoDB
- **Frontend:** React, TypeScript, Vite, Plotly.js, Vanilla CSS

## Project Structure
- `/analytics/` - Core simulation, calibration, and replay math.
- `/backend/` - FastAPI service mapping internal engine logic to REST/WS APIs.
- `/database/` - MongoDB connection handling.
- `/frontend/` - React UI, Race Console, and Visualizations.

## Local Setup

### Requirements
- Docker & Docker Compose (or local MongoDB running on 27017)
- Python 3.12+
- Node.js 18+

### 1. Database
```bash
docker run -d -p 27017:27017 --name stratos-mongo mongo:latest
```
*Ensure historical race telemetry is loaded into the `stratos` database.*

### 2. Backend
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173`.

## Replay Demo
The default demonstration is Bahrain 2023. Launch the Race Console via the frontend to step through the historical timeline. The timeline strictly blocks future data leakage until the cursor passes the decision boundary.

## Testing
The repository enforces architectural contracts through extensive `pytest` coverage.
```bash
pytest tests/
```

## Limitations
- Fuel burn remains a hardcoded prior (`0.0600 s/lap`) because it is not reliably identifiable from open timing telemetry.
- Traffic plot visualizes immediate adjacent cars rather than the full grid interval gap matrix due to UI density constraints.
- Real-time live execution requires authenticated OpenF1 credentials.

## Future Work
- Empirical calibration of pit-loss distributions per-circuit.
- Migration to a Rust-based Monte Carlo kernel for 10x simulation depth.

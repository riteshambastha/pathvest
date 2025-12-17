# LEAN Configuration Files

This directory contains configuration files for the LEAN backtesting engine.

## Files

### `config.json`
- Simple configuration for local Python backtesting
- Used when running LEAN from Python code directly
- Points to local file paths

### `lean-config.json`
- Full LEAN Docker configuration
- Used when running LEAN in Docker containers
- Uses Docker volume paths (`/Lean/Data`, `/Results`, etc.)

## Key Settings

### Fractional Shares
```json
"algorithm-settings": {
  "allow-fractional-holdings": true
}
```
This enables fractional share trading as required by FR-3.1.D.4.

### Transaction Costs
Transaction fees and slippage are configured in the PathVestBaseStrategy class:
- Commission: $0.005 per share (FR-3.1.C.7)
- Slippage: 25 basis points (FR-3.1.C.7)

### Data Paths
- **Local**: `../data` (relative to this config directory)
- **Docker**: `/Lean/Data` (mounted volume)

## Usage

### Local Testing (Python)
```python
from lean_engine import LEANBacktestEngine

engine = LEANBacktestEngine(config_path="config.json")
results = engine.run_backtest(strategy_config)
```

### Docker (Full LEAN)
```bash
docker run --rm -v $(pwd):/Lean \
  quantconnect/lean:latest \
  --config /Lean/config/lean-config.json
```

## Environment Variables

You can override settings using environment variables:
- `LEAN_DATA_FOLDER`: Override data directory
- `LEAN_RESULTS_FOLDER`: Override results directory
- `LEAN_LOG_LEVEL`: Set logging level (trace, debug, information, warning, error)

## References

- [LEAN Documentation](https://www.quantconnect.com/docs)
- [LEAN Configuration Reference](https://github.com/QuantConnect/Lean/blob/master/Launcher/config.json)
- PathVest SRS Section 6.1: LEAN Integration


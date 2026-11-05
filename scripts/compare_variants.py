"""Compare day-ahead feature variants on identical evaluation timelines."""
import argparse, tempfile
from pathlib import Path
import numpy as np, pandas as pd, yaml
from sklearn.metrics import r2_score
from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.backtesting.backtest_runner import run_configured_backtest

def run(experiment, paths, start, end, retraining, workspace, tag):
    config = load_config(experiment, local_paths_config_path=paths,
                         model_params_config_path="configs/model_params.yaml")
    config["backtest"]["evaluation_start_date"] = start
    config["backtest"]["evaluation_end_date"] = end
    config["retraining"] = retraining
    config["paths"]["models_dir"] = workspace / "models" / tag
    config["paths"]["logs_dir"] = workspace / "logs" / tag
    cfg = workspace / f"{tag}.yaml"
    cfg.write_text(yaml.safe_dump({k: v for k, v in config.items() if k != "paths"}))
    meta = run_configured_backtest(config, config_file_path=cfg)
    frame = pd.read_parquet(meta["artifact_paths"]["forecasts"]).sort_values("timestamp")
    actual, predicted = frame.actual.to_numpy(float), frame.prediction.to_numpy(float)
    error = predicted - actual
    return {"rmse": float(np.sqrt((error**2).mean())), "mae": float(np.abs(error).mean()),
            "r2": float(r2_score(actual, predicted)), "refits": meta["retraining_event_count"]}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-12-31")
    args = parser.parse_args()
    variants = {
        "both forecasts (5097+122)": ("configs/experiment_day_ahead_published.yaml",
                                      "configs/local_paths_day_ahead_published.yaml"),
        "PV+wind only (5097)": ("configs/experiment_day_ahead_pvwind.yaml",
                                "configs/local_paths_day_ahead_pvwind.yaml"),
    }
    strategies = {"no_retraining": {"strategy": "no_retraining"},
                  "fixed_schedule": {"strategy": "fixed_schedule", "fixed_schedule_interval_days": 7}}
    workspace = Path(tempfile.mkdtemp(prefix="etp_variant_"))
    rows = []
    for label, (experiment, paths) in variants.items():
        for name, retraining in strategies.items():
            tag = f"{abs(hash(label+name)) % 10000}"
            rows.append({"features": label, "strategy": name,
                         **run(experiment, paths, args.start, args.end, retraining, workspace, tag)})
            print(f"  {label} / {name}: RMSE {rows[-1]['rmse']:.3f}", flush=True)
    table = pd.DataFrame(rows)
    print(f"\n{args.start} .. {args.end}")
    print(table.to_string(index=False))
    for name in strategies:
        subset = table[table.strategy == name].set_index("features")
        both = subset.loc["both forecasts (5097+122)", "rmse"]
        only = subset.loc["PV+wind only (5097)", "rmse"]
        print(f"  {name:16s} dropping filter 122: RMSE {both:.3f} -> {only:.3f} ({100*(only-both)/both:+.2f}%)")

if __name__ == "__main__":
    main()

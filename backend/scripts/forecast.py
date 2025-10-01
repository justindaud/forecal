import pandas as pd
import numpy as np
import json
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor

# ==============================================================================
# ML-BASED PIPELINE (aligned with backend/data/testfixed.ipynb)
# ==============================================================================

def _build_enrich_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate notebook-style feature engineering at daily granularity.

    Expects columns: Date, Occupancy Rate, Is_Holiday, Is_Weekend, Is_Event, Is_SchoolHoliday
    Returns daily DataFrame with features used for ML models.
    """
    enrich = df.copy()
    # Keep one row per date with the target occupancy rate
    enrich = (enrich.groupby(['Date', 'Occupancy Rate', 'Is_Holiday', 'Is_Weekend', 'Is_Event', 'Is_SchoolHoliday'])
                    .size().reset_index().drop(columns=0))
    enrich = enrich.rename(columns={'Is_Holiday': 'Is_NationalHoliday'})
    enrich = enrich.sort_values('Date').reset_index(drop=True)

    # Bridge day between holidays/weekends
    seed_hol = (enrich['Is_NationalHoliday'].astype(bool) | enrich['Is_Weekend'].astype(bool)).to_numpy()
    n = len(seed_hol)

    left_seed  = np.r_[False, seed_hol[:-1]]
    right_seed = np.r_[seed_hol[1:], False]
    is_bridge = (~seed_hol) & left_seed & right_seed
    enrich['Is_Bridge'] = is_bridge

    is_nat = enrich['Is_NationalHoliday'].to_numpy(dtype=bool)
    is_we  = enrich['Is_Weekend'].to_numpy(dtype=bool)
    is_br  = enrich['Is_Bridge'].to_numpy(dtype=bool)

    base = is_nat | is_br

    left_base  = np.r_[False, base[:-1]]
    right_base = np.r_[base[1:], False]
    wk1 = is_we & (left_base | right_base)

    left_wk1  = np.r_[False, wk1[:-1]]
    right_wk1 = np.r_[wk1[1:], False]
    wk2 = is_we & (left_wk1 | right_wk1)

    is_holiday_final = base | wk1 | wk2
    enrich['Is_Holiday'] = is_holiday_final

    # Block sizing for holiday spans
    block_id = (~is_holiday_final).cumsum()
    enrich['Holiday_Duration'] = 0
    enrich['Days_of_Holiday'] = 0

    mask = is_holiday_final
    grp = pd.Series(block_id[mask]).groupby(block_id[mask])
    sizes = grp.transform('size').to_numpy() if len(grp) else np.array([])
    
    order_in_block = grp.cumcount() + 1 if len(grp) else pd.Series([], dtype=int)
    if len(sizes):
        enrich.loc[mask, 'Holiday_Duration'] = sizes
        enrich.loc[mask, 'Days_of_Holiday'] = order_in_block.to_numpy()

    # Distance to nearest holiday
    is_hol = enrich['Is_Holiday'].to_numpy(dtype=bool)
    n = len(enrich)
    INF = 10**9
    dist_fwd = np.full(n, INF, dtype=int)
    last = -INF
    for i in range(n):
        if is_hol[i]:
            last = i
        dist_fwd[i] = i - last
    dist_bwd = np.full(n, INF, dtype=int)
    last = INF
    for i in range(n - 1, -1, -1):
        if is_hol[i]:
            last = i
        dist_bwd[i] = last - i
    dist = np.minimum(dist_fwd, dist_bwd)
    dist[is_hol] = 0
    enrich['Distance_to_Holiday'] = dist

    # Date parts
    enrich['Day_of_Week']  = pd.to_datetime(enrich['Date']).dt.dayofweek
    enrich['Day_of_Month'] = pd.to_datetime(enrich['Date']).dt.day
    enrich['Month']        = pd.to_datetime(enrich['Date']).dt.month
    enrich['Year']         = pd.to_datetime(enrich['Date']).dt.year

    return enrich

def _future_calendar_2026(holidays_df: pd.DataFrame, start_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """Create 2026 future calendar with the same engineered calendar features.

    If start_date is provided, the calendar starts from that date; otherwise defaults to 2026-01-01.
    """
    holidays = holidays_df.copy()
    holidays['Date'] = pd.to_datetime(holidays['Date'])
    start_2026 = pd.Timestamp('2026-01-01') if start_date is None else pd.Timestamp(start_date)
    end_2026 = pd.Timestamp('2026-12-31')
    future_cal = pd.date_range(start=start_2026, end=end_2026, freq='D')

    rows = []
    for date in future_cal:
        is_weekend = date.weekday() >= 5
        info = holidays[holidays['Date'] == date]
        is_nat = False; is_school = False; is_event = False
        if not info.empty:
            kind = str(info.iloc[0]['Kind']).lower()
            is_nat = kind in ['national', 'joint', 'national holiday', 'joint holiday']
            is_school = kind in ['school', 'school holiday']
            is_event = kind in ['event']
        rows.append({
            'Date': date,
            'Is_NationalHoliday': is_nat,
            'Is_Weekend': is_weekend,
            'Is_Event': is_event,
            'Is_SchoolHoliday': is_school,
        })
    future = pd.DataFrame(rows)

    # Apply same bridge/holiday logic and derived features
    seed_hol = (future['Is_NationalHoliday'].astype(bool) | future['Is_Weekend'].astype(bool)).to_numpy()
    n = len(seed_hol)
    
    left_seed  = np.r_[False, seed_hol[:-1]]
    right_seed = np.r_[seed_hol[1:], False]
    is_bridge = (~seed_hol) & left_seed & right_seed
    future['Is_Bridge'] = is_bridge

    is_nat = future['Is_NationalHoliday'].to_numpy(dtype=bool)
    is_we  = future['Is_Weekend'].to_numpy(dtype=bool)
    is_br  = future['Is_Bridge'].to_numpy(dtype=bool)

    base = is_nat | is_br

    left_base  = np.r_[False, base[:-1]]
    right_base = np.r_[base[1:], False]
    wk1 = is_we & (left_base | right_base)

    left_wk1  = np.r_[False, wk1[:-1]]
    right_wk1 = np.r_[wk1[1:], False]
    wk2 = is_we & (left_wk1 | right_wk1)

    is_holiday_final = base | wk1 | wk2
    future['Is_Holiday'] = is_holiday_final

    block_id = (~is_holiday_final).cumsum()
    future['Holiday_Duration'] = 0
    future['Days_of_Holiday'] = 0

    mask = is_holiday_final
    grp = pd.Series(block_id[mask]).groupby(block_id[mask])
    sizes = grp.transform('size').to_numpy() if len(grp) else np.array([])

    order_in_block = grp.cumcount() + 1 if len(grp) else pd.Series([], dtype=int)
    if len(sizes):
        future.loc[mask, 'Holiday_Duration'] = sizes
        future.loc[mask, 'Days_of_Holiday'] = order_in_block.to_numpy()

    # Distance to nearest holiday
    is_hol = future['Is_Holiday'].to_numpy(dtype=bool)
    n = len(future)
    INF = 10**9
    dist_fwd = np.full(n, INF, dtype=int)
    last = -INF
    for i in range(n):
        if is_hol[i]:
            last = i
        dist_fwd[i] = i - last
    dist_bwd = np.full(n, INF, dtype=int)
    last = INF
    for i in range(n - 1, -1, -1):
        if is_hol[i]:
            last = i
        dist_bwd[i] = last - i
    dist = np.minimum(dist_fwd, dist_bwd)
    dist[is_hol] = 0
    future['Distance_to_Holiday'] = dist

    # Date parts
    future['Day_of_Week']  = pd.to_datetime(future['Date']).dt.dayofweek
    future['Day_of_Month'] = pd.to_datetime(future['Date']).dt.day
    future['Month']        = pd.to_datetime(future['Date']).dt.month
    future['Year']         = pd.to_datetime(future['Date']).dt.year

    return future

def _clean_boolean_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if df[c].dtype == bool:
            df[c] = df[c].astype(int)
        elif df[c].dtype == object:
            uniq = set(pd.unique(df[c].dropna()))
            if uniq <= {"True", "False"}:
                df[c] = df[c].map({"False": 0, "True": 1}).astype('Int64').fillna(0).astype(int)
    return df

def ml_predict_occupancy_and_arr(hist_df: pd.DataFrame, holidays_df: pd.DataFrame):
    """Train RF for occupancy and ARR, then predict for 2026. Returns (occ_df, arr_df)."""
    # Occupancy RF
    daily_df = hist_df[['Date', 'Occupancy Rate', 'Is_Holiday', 'Is_Weekend', 'Is_Event', 'Is_SchoolHoliday']].copy()
    enrich = _build_enrich_calendar_features(daily_df)
    target_occ = 'Occupancy Rate'
    drop_cols = ['Date', 'Year', target_occ]
    features_occ = [c for c in enrich.columns if c not in drop_cols]
    X_full = enrich[features_occ].copy()
    y_full = enrich[target_occ].astype(float).clip(1e-6, 1 - 1e-6)
    X_full = _clean_boolean_columns(X_full)
    rf_occ = RandomForestRegressor(n_estimators=400, random_state=0, min_samples_leaf=2, n_jobs=-1)
    rf_occ.fit(X_full, y_full)

    # Future calendar and occupancy prediction
    # Start from day after latest historical date to avoid overlap with history
    latest_hist_date = pd.to_datetime(enrich['Date'].max()) + pd.Timedelta(days=1)
    future = _future_calendar_2026(holidays_df, start_date=latest_hist_date)
    occ_feats = [
        'Is_NationalHoliday', 'Is_Weekend', 'Is_Event', 'Is_SchoolHoliday',
        'Is_Bridge', 'Is_Holiday', 'Holiday_Duration', 'Days_of_Holiday',
        'Distance_to_Holiday', 'Day_of_Week', 'Day_of_Month', 'Month'
    ]
    X_future_occ = future[occ_feats].copy()
    X_future_occ = _clean_boolean_columns(X_future_occ)
    future['Forecasted_Occ'] = rf_occ.predict(X_future_occ)

    # ARR RF
    arrtrain = hist_df.copy()
    if 'Occupancy Rate' in arrtrain.columns:
        arrtrain = arrtrain.drop(columns=['Occupancy Rate', 'Is_Holiday', 'Is_Weekend', 'Is_Event', 'Is_SchoolHoliday'])
    arrtrain = pd.merge(arrtrain, enrich.drop(columns=['Occupancy Rate']), on='Date', how='left')

    trainset = arrtrain.sort_values('Date').copy()
    target_arr = 'Average Room Rate'
    drop_arr = ['Date', 'Year', target_arr]
    features_arr = [c for c in trainset.columns if c not in drop_arr]

    # One-hot for categories
    cat_cols = []
    for c in ['Room Type', 'Arrangement']:
        if c in features_arr and trainset[c].dtype == object:
            cat_cols.append(c)
    X_train_raw = trainset[features_arr].copy()
    if len(cat_cols):
        X_train = pd.get_dummies(X_train_raw, columns=cat_cols, drop_first=False)
    else:
        X_train = X_train_raw
    X_train = _clean_boolean_columns(X_train)
    model_cols = X_train.columns.tolist()
    y_train = trainset[target_arr].astype(float)

    rf_arr = RandomForestRegressor(n_estimators=400, random_state=0, min_samples_leaf=2, n_jobs=-1)
    rf_arr.fit(X_train, y_train)

    # Build future cartesian for ARR
    pairs = hist_df[['Room Type', 'Arrangement']].dropna().drop_duplicates()
    future_pairs = future.copy()
    future_pairs['__k'] = 1
    pairs_ = pairs.copy(); pairs_['__k'] = 1
    arrfuture = future_pairs.merge(pairs_, on='__k', how='outer').drop(columns='__k')
    arrfuture = arrfuture.rename(columns={'Forecasted_Occ': 'Predicted_Occupancy'})

    # Features for inference must match model_cols
    base_feats = [
        'Predicted_Occupancy', 'Is_NationalHoliday', 'Is_Weekend', 'Is_Event', 'Is_SchoolHoliday',
        'Is_Bridge', 'Is_Holiday', 'Holiday_Duration', 'Days_of_Holiday', 'Distance_to_Holiday',
        'Day_of_Week', 'Day_of_Month', 'Month'
    ]
    base_feats = [c for c in base_feats if c in features_arr]
    infer_cols = base_feats + cat_cols
    X_future_arr_raw = arrfuture[infer_cols].copy()
    if len(cat_cols):
        X_future_arr = pd.get_dummies(X_future_arr_raw, columns=cat_cols, drop_first=False)
    else:
        X_future_arr = X_future_arr_raw
    # Always align features and predict regardless of categorical presence
    X_future_arr = _clean_boolean_columns(X_future_arr)
    X_future_arr = X_future_arr.reindex(columns=model_cols, fill_value=0)
    arrfuture['Forecasted_ARR'] = rf_arr.predict(X_future_arr)

    # Return in schemas used by combine_forecasts
    occ_out = future[['Date', 'Forecasted_Occ', 'Is_Holiday', 'Is_Weekend', 'Is_SchoolHoliday', 'Is_Event']].copy()
    # Map Is_Holiday here is the final holiday flag from engineered future
    arr_out = arrfuture[['Date', 'Room Type', 'Forecasted_ARR', 'Predicted_Occupancy', 'Is_Holiday', 'Is_Weekend', 'Is_SchoolHoliday', 'Is_Event', 'Is_Bridge']].copy()

    # Also emit flat predictions schema for transparency/debugging
    transparent = arrfuture.copy()
    transparent = transparent.rename(columns={
        'Predicted_Occupancy': 'Occupancy Rate',
        'Forecasted_ARR': 'ARR_pred'
    })
    keep_cols = [
        'Date','Is_NationalHoliday','Is_Weekend','Is_Event','Is_SchoolHoliday','Is_Bridge','Is_Holiday',
        'Holiday_Duration','Days_of_Holiday','Distance_to_Holiday','Day_of_Week','Day_of_Month','Month',
        'Occupancy Rate','Room Type','Arrangement','ARR_pred'
    ]
    keep_cols = [c for c in keep_cols if c in transparent.columns]
    transparent_out = transparent[keep_cols].copy()
    # Save to data/predictions.csv
    transparent_out.to_csv('data/predictions.csv', index=False)
    print('Saved transparent predictions: data/predictions.csv')
    return occ_out, arr_out

def combine_forecasts(occupancy_forecast: pd.DataFrame, arr_forecast: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
    """Compose enhanced_forecasting_2026-compatible CSV combining history and forecasts.

    - Historical (all rows in historical_df): use actuals as forecasted, zero error.
    - Forecast (based on occupancy_forecast dates, merged with arr_forecast per Room Type).
    """
    final_rows = []

    # Historical portion (retain original schema expectations)
    hist_df = historical_df.copy()
    hist_df['Date'] = pd.to_datetime(hist_df['Date'])
    for _, r in hist_df.iterrows():
        final_rows.append({
            'Date': r['Date'],
            'Room Type': r.get('Room Type'),
            'Average Room Rate': r.get('Average Room Rate'),
            'Occ': r.get('Occupancy Rate'),
            'Forecasted ARR': r.get('Average Room Rate'),
            'Forecasted Occ': r.get('Occupancy Rate'),
            'Error ARR': 0,
            'Error Occ': 0,
            'Is_Holiday': r.get('Is_Holiday', False),
            'Is_Weekend': r.get('Is_Weekend', False),
            'Is_SchoolHoliday': r.get('Is_SchoolHoliday', False),
            'Is_Event': r.get('Is_Event', False),
            'holiday_block_length': 0,
            'Is_Bridge': False,
        })

    # Forecast portion (2026): join occupancy and ARR
    occ = occupancy_forecast.copy()
    occ['Date'] = pd.to_datetime(occ['Date'])
    arr = arr_forecast.copy()
    arr['Date'] = pd.to_datetime(arr['Date'])

    # For each date in occupancy forecast, attach all ARR rows with same date
    merged = arr.merge(occ, on='Date', how='left', suffixes=('', '_occ'))
    for _, r in merged.iterrows():
        final_rows.append({
            'Date': r['Date'],
            'Room Type': r.get('Room Type'),
            'Average Room Rate': None,
            'Occ': None,
            'Forecasted ARR': r.get('Forecasted_ARR'),
            'Forecasted Occ': r.get('Forecasted_Occ'),
            'Error ARR': None,
            'Error Occ': None,
            'Is_Holiday': r.get('Is_Holiday'),
            'Is_Weekend': r.get('Is_Weekend'),
            'Is_SchoolHoliday': r.get('Is_SchoolHoliday'),
            'Is_Event': r.get('Is_Event'),
            'holiday_block_length': r.get('holiday_block_length', 0),
            'Is_Bridge': r.get('Is_Bridge', False),
        })

    final_df = pd.DataFrame(final_rows)
    final_df = final_df.sort_values(['Date', 'Room Type']).reset_index(drop=True)
    return final_df

def evaluate_forecast(final_df: pd.DataFrame, historical_df: pd.DataFrame) -> None:
    """Lightweight evaluation placeholder to keep pipeline stable without heavy metrics."""
    try:
        print(f"Forecast combined records: {len(final_df)}")
        print(f"Dates: {final_df['Date'].min()} → {final_df['Date'].max()}")
        print(f"Room types: {final_df['Room Type'].nunique()}")
    except Exception as e:
        print(f"Evaluation summary skipped: {e}")

if __name__ == "__main__":
    # Load historical data
    hist_df = pd.read_csv("data/dataset_processed.csv")
    hist_df["Date"] = pd.to_datetime(hist_df["Date"])
    
    # Load holidays (for building 2026 calendar)
    holidays_df = pd.read_csv("data/holidays_info.csv")
    holidays_df["Date"] = pd.to_datetime(holidays_df["Date"])
    
    # Train and predict using ML models (occupancy then ARR)
    occupancy_forecast, arr_forecast = ml_predict_occupancy_and_arr(hist_df, holidays_df)

    # Save ARR predictions for compatibility
    arr_forecast.to_csv("data/arr_forecast_2026.csv", index=False)
    print("Saved ARR forecast: data/arr_forecast_2026.csv")

    # Combine to enhanced_forecasting_2026.csv compatible with frontend
    final_df = combine_forecasts(occupancy_forecast, arr_forecast, hist_df)
    final_df.to_csv("data/enhanced_forecasting_2026.csv", index=False)
    print("Saved forecast: data/enhanced_forecasting_2026.csv")

    # Optional evaluation if historical overlap exists
    try:
        evaluate_forecast(final_df, hist_df)
    except Exception as e:
        print(f"Evaluation skipped: {e}")

    print("\n=== ML-BASED FORECASTING (Notebook-aligned) COMPLETED ===")
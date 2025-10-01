# data_extraction.py - Data extraction and processing
# ORGANIZED BACKEND STRUCTURE VERSION
import os
import pandas as pd
from sqlalchemy import create_engine, text
import json
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Create a .env with DATABASE_URL=... or export it in your shell.")

def holidays_from_csv(csv_path: str = "../data/holidays_info.csv", kind_filter: str = None) -> set:
    """Parse holidays from holidays_info.csv (UPDATED PATH)"""
    if not os.path.exists(csv_path):
        return set()
    try:
        df = pd.read_csv(csv_path)
        if kind_filter:
            df = df[df["Kind"] == kind_filter]
        dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
        return set(dates.dt.date)
    except Exception:
        return set()

def holidays_from_env_json(env_var: str = "HOLIDAYS_JSON") -> set:
    """Parse holidays from environment variable (fallback)"""
    try:
        raw = os.environ.get(env_var)
        if not raw:
            return set()
        arr = json.loads(raw)
        out = set()
        for s in arr:
            try:
                out.add(pd.Timestamp(pd.to_datetime(s).date()))
            except Exception:
                continue
        return out
    except Exception:
        return set()

def load_data(date_start: str = "2024-01-01", date_end: str = "2025-12-31") -> pd.DataFrame:
    """Load reservation data from database"""
    engine = create_engine(DATABASE_URL)
    
    typed_query = text("""
        SELECT *
        FROM public.reservasi_processed
        WHERE (
            (arrival_date ~ '^\\d{4}-\\d{2}-\\d{2}$' AND arrival_date::date BETWEEN :ds AND :de)
            OR (depart_date ~ '^\\d{4}-\\d{2}-\\d{2}$' AND depart_date::date BETWEEN :ds AND :de)
        )
    """)
    
    like_query = text("""
        SELECT *
        FROM public.reservasi_processed
        WHERE (
            arrival_date::text LIKE :y2024 OR arrival_date::text LIKE :y2025
            OR depart_date::text LIKE :y2024 OR depart_date::text LIKE :y2025
        )
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(typed_query, conn, params={"ds": date_start, "de": date_end})
            if df.empty:
                raise Exception("Empty result; will try LIKE fallback")
    except Exception:
        with engine.connect() as conn2:
            df = pd.read_sql(
                like_query,
                conn2,
                params={"y2024": "%2024%", "y2025": "%2025%"},
            )
    return df

def _map_room_type(raw):
    """Map raw room type to standardized room type"""
    if not isinstance(raw, str) or len(raw) == 0:
        return None
    first = raw.strip().upper()[:1]
    if first == "D":
        return "Deluxe"
    if first == "E":
        return "Executive Suite"
    if first == "S":
        return "Suite"
    if first == "B":
        return "Executive Suite"
    if first == "F":
        return "Family Suite"
    return None

def expand_stays_to_daily_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Expand reservations to daily rows"""
    if df.empty:
        return pd.DataFrame(columns=["date", "room_type", "arrangement", "room_number", "segment", "nightly_rate"])
    
    work = df.copy()
    work["arrival_date"] = pd.to_datetime(work["arrival_date"], errors="coerce")
    work["depart_date"] = pd.to_datetime(work["depart_date"], errors="coerce")
    work = work.dropna(subset=["arrival_date", "depart_date"])
    
    rows = []
    for _, row in work.iterrows():
        if row["depart_date"] <= row["arrival_date"]:
            continue
        d_range = pd.date_range(start=row["arrival_date"].normalize(), end=(row["depart_date"] - pd.Timedelta(days=1)).normalize(), freq="D")
        
        seg_val = row.get("segment") if "segment" in work.columns else None
        
        total_room_rate = None
        if "room_rate" in work.columns and pd.notna(row.get("room_rate")):
            try:
                total_room_rate = float(row.get("room_rate"))
            except Exception:
                total_room_rate = None
        
        nightly_rate = float(total_room_rate) if total_room_rate is not None else None
        
        raw_room = row.get("room_type")
        mapped_room = _map_room_type(raw_room) if "room_type" in work.columns else None
        final_room = mapped_room if mapped_room else (str(raw_room).strip() if pd.notna(raw_room) and str(raw_room).strip() != "" else None)
        
        for d in d_range:
            rows.append({
                "date": d.date(),
                "room_type": final_room,
                "arrangement": row.get("arrangement") if "arrangement" in work.columns else None,
                "room_number": row.get("room_number") if "room_number" in work.columns else None,
                "segment": seg_val,
                "nightly_rate": nightly_rate,
            })
    
    daily = pd.DataFrame(rows)
    if not daily.empty and "room_type" in daily.columns:
        daily = daily[daily["room_type"].notna()]
    return daily

def load_maintenance_data(maintenance_csv_path: str = "data/maintenance_cleaned.csv"):
    """Load maintenance data to get rooms out of order"""
    try:
        if not os.path.exists(maintenance_csv_path):
            print(f"Warning: Maintenance file not found: {maintenance_csv_path}")
            return pd.DataFrame(columns=["Date", "Room Type", "Quantity"])
        
        df_maintenance = pd.read_csv(maintenance_csv_path)
        df_maintenance["Date"] = pd.to_datetime(df_maintenance["Date"])
        print(f"Loaded maintenance data: {len(df_maintenance)} records")
        return df_maintenance
    except Exception as e:
        print(f"Error loading maintenance data: {e}")
        return pd.DataFrame(columns=["Date", "Room Type", "Quantity"])

def build_feature_dataset(source_df: pd.DataFrame, excluded_segments=None, inventory_per_room_type=None, holidays_set=None, events_set=None, fasting_set=None, maintenance_df=None):
    """Build feature dataset with daily occupancy calculation including maintenance"""
    excluded_segments = set([s.upper() for s in (excluded_segments or ["COMP", "HU"])])
    
    daily = expand_stays_to_daily_rows(source_df)
    if daily.empty:
        return pd.DataFrame(columns=["Date", "Room Type", "Average Room Rate", "Occupancy Rate", "Is_Holiday", "Is_Weekend", "Is_Event", "Is_Fasting"])
    
    daily["segment_up"] = daily["segment"].astype(str).str.upper()
    daily["paid_flag"] = ~daily["segment_up"].isin(excluded_segments)
    daily["valid_rate_flag"] = daily["nightly_rate"].notna() & daily["paid_flag"]
    
    # ADR calculation per room type and arrangement
    adr_paid = daily.loc[daily["valid_rate_flag"], ["date", "room_type", "arrangement", "nightly_rate"]]
    adr_agg = (
        adr_paid.groupby(["date", "room_type", "arrangement"], dropna=False)["nightly_rate"].mean()
        .rename("avg_room_rate").reset_index()
    )
    
    # DAILY OCCUPANCY CALCULATION (not per room type)
    # Calculate daily totals for occupancy including maintenance
    daily_occ_data = []
    
    for date in daily["date"].unique():
        date_data = daily[daily["date"] == date]
        
        # Total rooms sold (excluding excluded segments)
        total_rooms_sold = date_data[date_data["paid_flag"]].dropna(subset=["room_number"])["room_number"].nunique()
        
        # Total rooms blocked (excluded segments)
        total_rooms_blocked = date_data[~date_data["paid_flag"]].dropna(subset=["room_number"])["room_number"].nunique()
        
        # Total rooms under maintenance
        total_rooms_maintenance = 0
        if maintenance_df is not None and not maintenance_df.empty:
            maintenance_date = pd.to_datetime(date)
            maintenance_for_date = maintenance_df[maintenance_df["Date"].dt.date == maintenance_date.date()]
            total_rooms_maintenance = maintenance_for_date["Quantity"].sum()
        
        # Total available inventory
        if inventory_per_room_type:
            total_inventory = sum(inventory_per_room_type.values())
        else:
            # Infer total inventory
            total_inventory = date_data.dropna(subset=["room_number"])["room_number"].nunique()
        
        # Daily occupancy rate (subtract both blocked and maintenance rooms)
        available_inventory = max(1, total_inventory - total_rooms_blocked - total_rooms_maintenance)
        daily_occupancy_rate = min(1.0, total_rooms_sold / available_inventory)
        
        daily_occ_data.append({
            "date": date,
            "daily_occupancy_rate": daily_occupancy_rate,
            "total_rooms_sold": total_rooms_sold,
            "total_rooms_blocked": total_rooms_blocked,
            "total_rooms_maintenance": total_rooms_maintenance,
            "total_inventory": total_inventory,
            "available_inventory": available_inventory
        })
    
    daily_occ_df = pd.DataFrame(daily_occ_data)
    
    # Merge ADR data with daily occupancy
    agg = adr_agg.merge(daily_occ_df, on="date", how="left")
    agg["occ_numerator"] = agg["total_rooms_sold"]
    agg["blocked_rooms"] = agg["total_rooms_blocked"]
    agg["maintenance_rooms"] = agg["total_rooms_maintenance"]
    agg["inventory"] = agg["total_inventory"]
    agg["available_inventory"] = agg["available_inventory"]
    agg["occupancy_rate"] = agg["daily_occupancy_rate"]  # Use daily occupancy for all room types
    
    # Fill missing arrangement values with empty string
    agg["arrangement"] = agg["arrangement"].fillna("")
    
    # Add weekend & holiday flags
    agg["date"] = pd.to_datetime(agg["date"]).dt.date
    agg["is_weekend"] = pd.to_datetime(agg["date"]).dt.weekday >= 5
    
    if holidays_set is not None and len(holidays_set) > 0:
        agg["is_holiday"] = pd.to_datetime(agg["date"]).isin(list(holidays_set))
    else:
        agg["is_holiday"] = False
    
    # Add event flag
    if events_set is not None and len(events_set) > 0:
        agg["is_event"] = pd.to_datetime(agg["date"]).isin(list(events_set))
    else:
        agg["is_event"] = False
    
    # Add fasting flag
    if fasting_set is not None and len(fasting_set) > 0:
        agg["is_fasting"] = pd.to_datetime(agg["date"]).isin(list(fasting_set))
    else:
        agg["is_fasting"] = False
    
    
    # Final columns
    final = agg[["date", "room_type", "arrangement", "avg_room_rate", "occupancy_rate", "occ_numerator", "blocked_rooms", "maintenance_rooms", "inventory", "available_inventory", "is_holiday", "is_weekend", "is_event", "is_fasting"]].copy()
    final = final.rename(columns={
        "date": "Date",
        "room_type": "Room Type",
        "arrangement": "Arrangement",
        "avg_room_rate": "Average Room Rate",
        "occupancy_rate": "Occupancy Rate",
        "occ_numerator": "Rooms Sold",
        "blocked_rooms": "Rooms Excluded",
        "maintenance_rooms": "Rooms Maintenance",
        "inventory": "Room Inventory",
        "available_inventory": "Available Inventory",
        "is_holiday": "Is_Holiday",
        "is_weekend": "Is_Weekend",
        "is_event": "Is_Event",
        "is_fasting": "Is_Fasting",
    })
    final = final.sort_values(["Date", "Room Type"]).reset_index(drop=True)
    return final

def build_overall_occupancy_series(dataset_csv: str) -> pd.DataFrame:
    """Build overall occupancy series with CORRECTED calculation"""
    df = pd.read_csv(dataset_csv)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # CORRECTED: Use Available Inventory instead of Room Inventory
    daily_agg = df.groupby("Date", as_index=False).agg({
        "Rooms Sold": "sum",
        "Available Inventory": "sum",  # This already accounts for excluded rooms
    })
    
    daily_agg["Overall_Occupancy"] = (daily_agg["Rooms Sold"] / daily_agg["Available Inventory"]).clip(0.0, 1.0)
    
    return daily_agg[["Date", "Overall_Occupancy"]]

if __name__ == "__main__":
    print("=== DATA EXTRACTION (ORGANIZED BACKEND STRUCTURE) ===")
    
    # Load data
    df_raw = load_data()
    print(f"Loaded rows: {len(df_raw)}")
    
    # Default inventory
    inventory_map = {
        "Deluxe": 80,
        "Executive Suite": 11,
        "Suite": 2,
        "Family Suite": 1,
    }
    
    # Holidays (national + joint only) - ABSOLUTE PATH
    holidays_set = holidays_from_csv("data/holidays_info.csv", kind_filter="national")
    joint_holidays = holidays_from_csv("data/holidays_info.csv", kind_filter="joint")
    holidays_set.update(joint_holidays)
    
    if not holidays_set:
        holidays_set = holidays_from_env_json()
    
    # School holidays separately - ABSOLUTE PATH
    school_holidays_set = holidays_from_csv("data/holidays_info.csv", kind_filter="school")
    
    # Events separately - ABSOLUTE PATH
    events_set = holidays_from_csv("data/holidays_info.csv", kind_filter="event")

    # Fasting separately - ABSOLUTE PATH
    fasting_set = holidays_from_csv("data/holidays_info.csv", kind_filter="fasting")
    
    # Load maintenance data
    maintenance_df = load_maintenance_data("data/maintenance_cleaned.csv")
    
    # Build feature dataset
    features_df = build_feature_dataset(
        df_raw,
        excluded_segments=["COMP", "HU"],
        inventory_per_room_type=inventory_map,
        holidays_set=holidays_set,
        events_set=events_set,
        fasting_set=fasting_set,
        maintenance_df=maintenance_df,
    )
    
    # Add school holidays
    features_df['Date'] = pd.to_datetime(features_df['Date'])
    features_df['Is_SchoolHoliday'] = features_df['Date'].isin([pd.Timestamp(d) for d in school_holidays_set])
    
    # Save dataset - ABSOLUTE PATH
    features_path = "data/dataset_processed.csv"
    features_df.to_csv(features_path, index=False)
    print(f"Saved processed dataset: {features_path}")
    
    # Show sample
    print("\nSample data:")
    print(features_df.head())
    
    # Show overall occupancy calculation
    overall_occ = build_overall_occupancy_series(features_path)
    print(f"\nOverall occupancy range: {overall_occ['Overall_Occupancy'].min():.3f} - {overall_occ['Overall_Occupancy'].max():.3f}")
    
    print("✅ Data extraction completed with organized backend structure")